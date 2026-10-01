#!/usr/bin/env python3
"""Element Inspector MCP handlers — inspect DOM elements via playwright-cli.

Standalone: works on ANY website open in playwright-cli browser.
No dependency on scitex-hub or API keys.

These handlers are consumed by the scitex MCP server (scitex-python)
via `register_ui_tools()`.
"""

from __future__ import annotations

import json
import subprocess


def _run_playwright_eval(js_code: str, timeout: int = 10) -> dict:
    """Execute JavaScript in the playwright-cli browser and return parsed result."""
    try:
        result = subprocess.run(
            ["playwright-cli", "eval", js_code],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        stdout = result.stdout.strip()

        # playwright-cli eval output format: "### Result\n<value>\n### Ran Playwright code\n..."
        # Extract the value between "### Result" and the next "###"
        raw = ""
        in_result = False
        for line in stdout.split("\n"):
            if line.strip() == "### Result":
                in_result = True
                continue
            if in_result and line.startswith("###"):
                break
            if in_result:
                raw += line + "\n"

        raw = raw.strip()
        # playwright-cli wraps string results in quotes: "{\\"key\\":val}"
        # Parse as JSON string first to unescape, then parse the inner JSON
        if raw.startswith('"') and raw.endswith('"'):
            try:
                raw = json.loads(raw)  # unquote + unescape
            except json.JSONDecodeError:
                raw = raw[1:-1]  # just strip quotes
        if not raw:
            return {
                "success": False,
                "error": f"No output from playwright-cli eval. stderr: {result.stderr[:300]}",
            }

        try:
            data = json.loads(raw)
            return {"success": True, "data": data}
        except json.JSONDecodeError:
            return {"success": True, "data": raw}

    except FileNotFoundError:
        return {
            "success": False,
            "error": "playwright-cli not found. Install: npm install -g playwright-cli",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"playwright-cli eval timed out after {timeout}s",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


_INSPECT_ONE_JS = """JSON.stringify((() => {
  const el = document.querySelector(SELECTOR);
  if (!el) return {error: "Element not found: " + SELECTOR};
  const cs = getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  const info = {
    url: location.href,
    element: { tag: el.tagName.toLowerCase(), id: el.id || null, classes: (typeof el.className === "string" ? el.className : "").split(/\\s+/).filter(c => c) },
    attributes: {},
    computed: { display: cs.display, position: cs.position, width: cs.width, height: cs.height, margin: cs.margin, padding: cs.padding, cursor: cs.cursor, flexDirection: cs.flexDirection, flexGrow: cs.flexGrow, flexShrink: cs.flexShrink, flex: cs.flex, zIndex: cs.zIndex, visibility: cs.visibility, overflow: cs.overflow, backgroundColor: cs.backgroundColor },
    inline: el.style.cssText || "",
    dimensions: { width: rect.width, height: rect.height, top: rect.top, left: rect.left },
    parentChain: [],
    matchingRules: []
  };
  for (let i = 0; i < el.attributes.length; i++) { const a = el.attributes[i]; info.attributes[a.name] = a.value; }
  let p = el.parentElement;
  for (let d = 0; d < 5 && p; d++) { let s = p.tagName.toLowerCase(); if (p.id) s += "#" + p.id; if (p.className && typeof p.className === "string") s += "." + p.className.split(" ").filter(c=>c).join("."); info.parentChain.push(s); p = p.parentElement; }
  try { for (let i = 0; i < document.styleSheets.length; i++) { try { const sheet = document.styleSheets[i]; if (!sheet.cssRules) continue; for (let j = 0; j < sheet.cssRules.length; j++) { const rule = sheet.cssRules[j]; if (rule instanceof CSSStyleRule) { try { if (el.matches(rule.selectorText)) { info.matchingRules.push({ selector: rule.selectorText, css: rule.cssText.substring(0, 300), source: sheet.href || "<inline>" }); } } catch(e) {} } } } catch(e) {} } } catch(e) {}
  return info;
})())"""

_INSPECT_MULTI_JS = """JSON.stringify((() => {
  const els = document.querySelectorAll(SELECTOR);
  const results = [];
  const limit = LIMIT;
  for (let i = 0; i < Math.min(els.length, limit); i++) {
    const el = els[i];
    const cs = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    results.push({ index: i, tag: el.tagName.toLowerCase(), id: el.id || null, classes: typeof el.className === "string" ? el.className : "", computed: { display: cs.display, position: cs.position, width: cs.width, height: cs.height, cursor: cs.cursor, flexDirection: cs.flexDirection }, inline: el.style.cssText || "", rect: { width: rect.width, height: rect.height, top: rect.top, left: rect.left }, parent: el.parentElement ? (el.parentElement.tagName.toLowerCase() + (el.parentElement.id ? "#" + el.parentElement.id : "")) : null });
  }
  return { total: els.length, elements: results };
})())"""


def inspect_element_handler(
    selector: str,
    timeout: int = 10,
) -> dict:
    """Inspect a single DOM element by CSS selector via playwright-cli.

    Standalone — works on any website open in playwright-cli browser.

    Parameters
    ----------
    selector : str
        CSS selector (e.g., '#ws-worktree-resizer', '.panel-resizer').
    timeout : int
        Evaluation timeout in seconds.
    """
    js = _INSPECT_ONE_JS.replace("SELECTOR", json.dumps(selector))
    result = _run_playwright_eval(js, timeout)

    if not result.get("success"):
        return result

    data = result["data"]
    if isinstance(data, dict) and "error" in data:
        return {"success": False, "error": data["error"]}
    return {"success": True, "data": data}


def inspect_elements_handler(
    selector: str,
    limit: int = 10,
    timeout: int = 10,
) -> dict:
    """Inspect multiple DOM elements matching a CSS selector via playwright-cli.

    Standalone — works on any website open in playwright-cli browser.

    Parameters
    ----------
    selector : str
        CSS selector (e.g., '.panel-resizer', '.stx-shell-sidebar').
    limit : int
        Maximum number of elements to return.
    timeout : int
        Evaluation timeout in seconds.
    """
    js = _INSPECT_MULTI_JS.replace("SELECTOR", json.dumps(selector)).replace(
        "LIMIT", str(limit)
    )
    result = _run_playwright_eval(js, timeout)

    if not result.get("success"):
        return result

    data = result["data"]
    return {
        "success": True,
        "selector": selector,
        **(data if isinstance(data, dict) else {"raw": data}),
    }


# EOF
