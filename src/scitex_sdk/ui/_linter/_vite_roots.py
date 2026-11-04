"""Bind nested Vite outputs to a static, enumerated package build context.

This is deliberately a small static subset, never a JavaScript evaluator.
Unrecognized configuration leaves the output subject to ordinary inspection.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_TOKEN = re.compile(
    r"(?P<space>\s+)|(?P<comment>//[^\n]*|/\*.*?\*/)|"
    r"""(?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|"""
    r"(?P<template>`(?:\\.|[^`\\])*`)|"
    r"(?P<regex>/(?:\\.|\[(?:\\.|[^\]\\])*\]|[^/\n])+/[a-z]*)|"
    r"(?P<word>[A-Za-z_$][\w$]*)|(?P<other>\.\.\.|=>|.)",
    re.DOTALL,
)
_CONFIG_NAMES = {f"vite.config.{suffix}" for suffix in ("ts", "js", "mts", "mjs")}
_BUILD = re.compile(r"\s*(?:tsc\s*&&\s*)?vite\s+build\s*")


def _tokens(source):
    return [
        (match.lastgroup, match[0])
        for match in _TOKEN.finditer(source)
        if match.lastgroup not in {"space", "comment"}
    ]


def _object(tokens, start):
    """Read direct properties, retaining opaque balanced value token lists."""
    if start >= len(tokens) or tokens[start][1] != "{":
        return None
    properties = {}
    cursor = start + 1
    while cursor < len(tokens):
        if tokens[cursor][1] == "}":
            return properties, cursor + 1
        kind, key = tokens[cursor]
        if kind not in {"word", "string"} or "\\" in key:
            return None
        key = key[1:-1] if kind == "string" else key
        if key in properties or tokens[cursor + 1 : cursor + 2] != [("other", ":")]:
            return None
        cursor += 2
        begin = cursor
        stack = []
        while cursor < len(tokens):
            kind, value = tokens[cursor]
            if kind == "other":
                if not stack and value in {",", "}"}:
                    break
                if value in {"{", "[", "("}:
                    stack.append({"{": "}", "[": "]", "(": ")"}[value])
                elif value in {"}", "]", ")"}:
                    if not stack or stack.pop() != value:
                        return None
            cursor += 1
        if cursor == begin or cursor >= len(tokens) or stack:
            return None
        properties[key] = tokens[begin:cursor]
        if tokens[cursor][1] == ",":
            cursor += 1
    return None


def _literal(tokens):
    if len(tokens) != 1 or tokens[0][0] != "string" or "\\" in tokens[0][1]:
        return None
    return tokens[0][1][1:-1]


def _output_directory(source):
    tokens = _tokens(source)
    # Unsupported or unterminated literals must not expose fake configuration
    # text as code. Templates are outside this deliberately static subset.
    if any(
        kind == "template" or (kind == "other" and value in {"'", '"', "`"})
        for kind, value in tokens
    ):
        return None
    if any(
        tokens[i : i + 2] == [("other", "/"), ("other", "*")]
        for i in range(len(tokens) - 1)
    ):
        return None
    starts = []
    declarations = 0
    for cursor in range(len(tokens) - 2):
        if tokens[cursor : cursor + 2] != [("word", "export"), ("word", "default")]:
            continue
        declarations += 1
        begin = cursor + 2
        wrapped = tokens[begin : begin + 2] == [
            ("word", "defineConfig"),
            ("other", "("),
        ]
        if wrapped:
            imported = [
                ("word", "import"),
                ("other", "{"),
                ("word", "defineConfig"),
                ("other", "}"),
                ("word", "from"),
            ]
            if not any(
                tokens[i : i + 5] == imported
                and _literal(tokens[i + 5 : i + 6]) == "vite"
                for i in range(begin)
            ):
                return None
            begin += 2
        parsed = _object(tokens, begin)
        if parsed is not None:
            end = parsed[1]
            if wrapped:
                if tokens[end : end + 1] != [("other", ")")]:
                    return None
                end += 1
            if tokens[end:] not in ([], [("other", ";")]):
                return None
            starts.append(parsed[0])
    if declarations != 1 or len(starts) != 1:
        return None
    config = starts[0]
    # A custom root changes the cwd binding; unsupported roots stay inspected.
    if "root" in config or "build" not in config:
        return None
    build_tokens = config["build"]
    parsed = _object(build_tokens, 0)
    if parsed is None or parsed[1] != len(build_tokens):
        return None
    build = parsed[0]
    if build.get("manifest") != [("word", "true")]:
        return None
    return _literal(build.get("outDir", []))


def nested_vite_roots(root: Path, paths: set[Path], output: Path) -> set[Path]:
    """Return statically bound project roots, without importing consumer code."""
    candidates = set()
    for config in paths:
        if config.name not in _CONFIG_NAMES or not config.is_relative_to(root):
            continue
        package = config.parent / "package.json"
        if package not in paths:
            continue
        if any(
            not p.is_file() or p.resolve() != p.absolute() for p in (config, package)
        ):
            continue
        metadata = json.loads(package.read_text(encoding="utf-8"))
        scripts = metadata.get("scripts") if isinstance(metadata, dict) else None
        command = scripts.get("build") if isinstance(scripts, dict) else None
        if not isinstance(command, str) or _BUILD.fullmatch(command) is None:
            continue
        relative = _output_directory(config.read_text(encoding="utf-8"))
        if relative is None or Path(relative).is_absolute():
            continue
        base = (config.parent / relative).resolve()
        if base == output.resolve() and base.is_relative_to(root):
            candidates.add(config.parent)
    return candidates
