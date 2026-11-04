"""Bounded AST reader for API declarations; never imports consumer modules."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from . import api_plugin

_CONSTRUCTORS = {
    name: getattr(api_plugin, name)
    for name in (
        "ApiPlugin",
        "ApiRoute",
        "ApiField",
        "ApiSchema",
        "ApiError",
        "AuthScope",
        "Idempotency",
        "Pagination",
        "RateLimit",
        "Audit",
        "Deprecation",
        "OAuthProvider",
    )
}
_SDK_MODULE = "scitex_sdk.app.api_plugin"


class UnprovenApi(ValueError):
    """Source cannot prove the declaration without executing consumer code."""


@dataclass(frozen=True)
class Binding:
    """An inert imported name, not an imported Python object."""

    module: str
    name: str = ""


class SourceReader:
    """Read only owned regular source with bounded recursion and allocation."""

    def __init__(self, root, overlays=None):
        self.root = Path(root).resolve()
        self.overlays = {
            Path(p).resolve(): text for p, text in (overlays or {}).items()
        }
        self.modules = {}
        self.visiting = set()
        self.steps = 0

    def module(self, name):
        if name in self.modules:
            return self.modules[name]
        if not name or any(not p.isidentifier() for p in name.split(".")):
            raise UnprovenApi("invalid owned module reference")
        if len(self.modules) >= 32:
            raise UnprovenApi("owned module limit exceeded")
        paths = []
        for base in (self.root / "src", self.root):
            stem = base.joinpath(*name.split("."))
            paths.extend((stem.with_suffix(".py"), stem / "__init__.py"))
        for path in paths:
            if path.resolve() != path or not path.is_relative_to(self.root):
                continue
            if path in self.overlays or path.is_file():
                text = self.overlays.get(path)
                if text is None:
                    if path.stat().st_size > 1_000_000:
                        raise UnprovenApi("source byte limit exceeded")
                    text = path.read_text(encoding="utf-8")
                if len(text.encode()) > 1_000_000:
                    raise UnprovenApi("source byte limit exceeded")
                tree = ast.parse(text, filename=str(path))
                if sum(1 for _ in ast.walk(tree)) > 30_000:
                    raise UnprovenApi("source AST limit exceeded")
                bindings = {}
                for node in tree.body:
                    pairs = self._bindings(node, name, path.name == "__init__.py")
                    for key, value in pairs:
                        if key in bindings:
                            raise UnprovenApi(f"overwritten source binding {key}")
                        bindings[key] = value
                value = (path, bindings)
                self.modules[name] = value
                return value
        raise UnprovenApi(f"no readable owned source for {name}")

    @staticmethod
    def _bindings(node, module, package):
        if isinstance(node, ast.ImportFrom):
            if any(a.name == "*" for a in node.names):
                raise UnprovenApi("star imports obscure API binding provenance")
            prefix = module.split(".") if package else module.split(".")[:-1]
            if node.level:
                if node.level > len(prefix):
                    raise UnprovenApi("relative import escapes owned package")
                target = ".".join(prefix[: len(prefix) - node.level + 1])
                target += ("." + node.module) if node.module else ""
            else:
                target = node.module or ""
            return [(a.asname or a.name, Binding(target, a.name)) for a in node.names]
        if isinstance(node, ast.Import):
            return [
                (
                    a.asname or a.name.split(".")[0],
                    Binding(a.name if a.asname else a.name.split(".")[0]),
                )
                for a in node.names
            ]
        if isinstance(node, ast.Assign):
            return [
                (item.id, node.value if isinstance(target, ast.Name) else node)
                for target in node.targets
                for item in ast.walk(target)
                if isinstance(item, ast.Name)
            ]
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            return [(node.target.id, node.value)]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return [(node.name, node)]
        # A dependency guard that only imports canonical SDK constructors and
        # always raises when absent does not introduce a fallback implementation.
        if (
            isinstance(node, ast.Try)
            and not node.orelse
            and not node.finalbody
            and node.body
            and node.handlers
            and all(
                isinstance(n, ast.ImportFrom)
                and n.module == _SDK_MODULE
                and n.level == 0
                for n in node.body
            )
            and all(
                isinstance(h.type, ast.Name)
                and h.type.id == "ImportError"
                and len(h.body) == 1
                and isinstance(h.body[0], ast.Raise)
                for h in node.handlers
            )
        ):
            return [
                pair
                for statement in node.body
                for pair in SourceReader._bindings(statement, module, package)
            ]
        # Conditional/loop/exception assignments cannot be treated as absent.
        # Descend only statement containers; function-local names stay local.
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.Match)):
            names = set()
            pending = [node]
            while pending:
                current = pending.pop()
                if isinstance(
                    current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    names.add(current.name)
                    continue
                if isinstance(current, ast.Name) and isinstance(current.ctx, ast.Store):
                    names.add(current.id)
                if (
                    isinstance(current, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar))
                    and current.name
                ):
                    names.add(current.name)
                if isinstance(current, ast.MatchMapping) and current.rest:
                    names.add(current.rest)
                if isinstance(current, (ast.Import, ast.ImportFrom)):
                    names.update(
                        a.asname or a.name.split(".")[0] for a in current.names
                    )
                pending.extend(ast.iter_child_nodes(current))
            return [(name, node) for name in names]
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            return [(node.target.id, node)]
        if isinstance(node, (ast.Delete, ast.Expr)):
            return [
                (item.id, node)
                for item in ast.walk(node)
                if isinstance(item, ast.Name)
                and isinstance(item.ctx, (ast.Store, ast.Del))
            ]
        return []

    def binding(self, module, name, depth=0):
        key = (module, name)
        if key in self.visiting or depth > 40:
            raise UnprovenApi("cyclic or deeply nested source binding")
        self.visiting.add(key)
        try:
            _, bindings = self.module(module)
            if name not in bindings:
                raise UnprovenApi(f"owned binding {module}:{name} not found")
            return self.value(module, bindings[name], depth + 1)
        finally:
            self.visiting.remove(key)

    def value(self, module, node, depth=0):
        self.steps += 1
        if depth > 40 or self.steps > 20_000:
            raise UnprovenApi("declaration evaluation budget exceeded")
        if isinstance(node, Binding):
            if node.module == _SDK_MODULE and node.name in _CONSTRUCTORS:
                return _CONSTRUCTORS[node.name]
            if node.name:
                return self.binding(node.module, node.name, depth + 1)
            return node
        if isinstance(node, ast.Constant) and isinstance(
            node.value, (str, int, float, bool, type(None))
        ):
            return node.value
        if isinstance(node, ast.Name):
            return self.binding(module, node.id, depth + 1)
        if isinstance(node, ast.Attribute):
            owner = self.value(module, node.value, depth + 1)
            if isinstance(owner, Binding):
                target = owner.module + ("." + owner.name if owner.name else "")
                if target == _SDK_MODULE and node.attr in _CONSTRUCTORS:
                    return _CONSTRUCTORS[node.attr]
                # A dotted import may name intermediate modules, not values.
                if _SDK_MODULE.startswith(target + "."):
                    return Binding(target + "." + node.attr)
                return self.binding(target, node.attr, depth + 1)
        if isinstance(node, (ast.Tuple, ast.List)):
            return tuple(self.value(module, item, depth + 1) for item in node.elts)
        if isinstance(node, ast.Dict) and all(key is not None for key in node.keys):
            return {
                self.value(module, key, depth + 1): self.value(module, val, depth + 1)
                for key, val in zip(node.keys, node.values)
            }
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = self.value(module, node.operand, depth + 1)
            if type(value) in (int, float):
                return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.Call):
            constructor = self.value(module, node.func, depth + 1)
            if constructor not in _CONSTRUCTORS.values() or any(
                k.arg is None for k in node.keywords
            ):
                raise UnprovenApi(
                    "only explicit SDK descriptor constructors are allowed"
                )
            return constructor(
                *(self.value(module, arg, depth + 1) for arg in node.args),
                **{
                    k.arg: self.value(module, k.value, depth + 1) for k in node.keywords
                },
            )
        raise UnprovenApi("dynamic or unsupported API declaration expression")

    def handler(self, target):
        """Prove a named function/method exists; never promise runtime behavior."""
        module, sep, attributes = target.partition(":")
        if not sep:
            raise UnprovenApi("invalid handler binding")
        path, bindings = self.module(module)
        parts = attributes.split(".")
        node = bindings.get(parts[0])
        seen = set()
        while isinstance(node, Binding):
            key = (node.module, node.name)
            if key in seen or len(seen) >= 32:
                raise UnprovenApi("cyclic handler reexport")
            seen.add(key)
            path, bindings = self.module(node.module)
            node = bindings.get(node.name)
        for part in parts[1:]:
            if not isinstance(node, ast.ClassDef):
                raise UnprovenApi("handler attribute is not an owned class method")
            matches = [
                value
                for statement in node.body
                for key, value in self._bindings(statement, module, False)
                if key == part
            ]
            if len(matches) != 1:
                raise UnprovenApi("missing or overwritten handler method")
            node = matches[0]
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise UnprovenApi("handler is not an owned function or method")
        return path, node.lineno
