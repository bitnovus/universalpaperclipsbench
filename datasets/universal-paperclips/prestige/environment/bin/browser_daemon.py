#!/usr/bin/env python3
import asyncio
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

PAPERCLIPS_URL = os.environ.get("PAPERCLIPS_URL", "http://127.0.0.1:8000/index2.html")
STATE_DIR = Path("/run/paperclips")
SCREENSHOT_DIR = Path("/logs/browser/screenshots")
ACTION_LOG = Path("/logs/browser/actions.jsonl")
PROGRESS_LOG = Path("/logs/browser/progress.jsonl")
TOKEN_PATH = STATE_DIR / "verifier.token"
GAME_TOKEN_PATH = STATE_DIR / "game.token"
FORBIDDEN_TARGET_TERMS = (
    "free",
    "cheat",
    "debug",
    "prestigeu",
    "prestiges",
    "destroyallhumans",
    "availmatterzero",
    "resetprestige",
)

state = {
    "playwright": None,
    "browser": None,
    "context": None,
    "page": None,
    "lock": asyncio.Lock(),
    "last_refs": {},
}


def write_jsonl(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


async def start_browser():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    profile = STATE_DIR / "chrome-profile"
    profile.mkdir(mode=0o700, exist_ok=True)

    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        str(profile),
        headless=True,
        viewport={"width": 1440, "height": 1000},
        args=[
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
        ],
    )
    game_token = GAME_TOKEN_PATH.read_text(encoding="utf-8").strip()
    await context.set_extra_http_headers({"X-Paperclips-Token": game_token})
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(PAPERCLIPS_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)

    state["playwright"] = pw
    state["context"] = context
    state["page"] = page
    write_jsonl(ACTION_LOG, {"ts": time.time(), "action": "start", "url": PAPERCLIPS_URL})


async def visible_dom():
    page = state["page"]
    items = await page.evaluate(
        """
() => {
  const out = [];
  let nextRef = 1;
  document.querySelectorAll('[data-bench-ref]').forEach(el => el.removeAttribute('data-bench-ref'));
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  function visible(el) {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style && style.visibility !== 'hidden' && style.display !== 'none' &&
      rect.width > 0 && rect.height > 0 && rect.bottom >= 0 && rect.right >= 0 &&
      rect.top <= window.innerHeight && rect.left <= window.innerWidth;
  }
  function label(el) {
    const aria = el.getAttribute('aria-label') || '';
    const text = (el.innerText || el.value || el.textContent || '').replace(/\\s+/g, ' ').trim();
    return (aria || text || el.id || el.name || el.tagName.toLowerCase()).slice(0, 240);
  }
  while (walker.nextNode()) {
    const el = walker.currentNode;
    if (!visible(el)) continue;
    const tag = el.tagName.toLowerCase();
    const interactive = ['button', 'input', 'select', 'textarea', 'a'].includes(tag) ||
      el.onclick || el.getAttribute('role');
    const hasUsefulText = (el.children.length === 0 && label(el)) || tag.match(/^h[1-6]$/);
    if (!interactive && !hasUsefulText) continue;
    const ref = String(nextRef++);
    el.setAttribute('data-bench-ref', ref);
    const rect = el.getBoundingClientRect();
    out.push({
      ref,
      tag,
      id: el.id || null,
      role: el.getAttribute('role'),
      text: label(el),
      value: typeof el.value === 'string' ? el.value : null,
      disabled: Boolean(el.disabled),
      bbox: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      }
    });
  }
  return out;
}
"""
    )
    state["last_refs"] = {item["ref"]: item for item in items}
    return {"url": page.url, "elements": items}


async def click_visible_ref(page, ref):
    handle = await page.evaluate_handle(
        """
ref => {
  function visible(el) {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style && style.visibility !== 'hidden' && style.display !== 'none' &&
      rect.width > 0 && rect.height > 0 && rect.bottom >= 0 && rect.right >= 0 &&
      rect.top <= window.innerHeight && rect.left <= window.innerWidth;
  }
  const matches = Array.from(document.querySelectorAll(`[data-bench-ref="${CSS.escape(String(ref))}"]`))
    .filter(visible);
  return matches.find(el => !el.disabled) || matches[0] || null;
}
""",
        str(ref),
    )
    element = handle.as_element()
    if element is None:
        raise LookupError(f"visible ref not found: {ref}")
    await element.click(timeout=10000)


async def click_visible_text(page, text):
    handle = await page.evaluate_handle(
        """
needle => {
  const wanted = String(needle).toLowerCase();
  function visible(el) {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style && style.visibility !== 'hidden' && style.display !== 'none' &&
      rect.width > 0 && rect.height > 0 && rect.bottom >= 0 && rect.right >= 0 &&
      rect.top <= window.innerHeight && rect.left <= window.innerWidth;
  }
  function label(el) {
    return (el.innerText || el.value || el.textContent || '').replace(/\\s+/g, ' ').trim();
  }
  const interactive = Array.from(document.querySelectorAll('button,input,select,textarea,a,[role]'))
    .filter(el => visible(el) && !el.disabled && label(el).toLowerCase().includes(wanted));
  return interactive[0] || null;
}
""",
        text,
    )
    element = handle.as_element()
    if element is None:
        raise LookupError(f"visible enabled text target not found: {text}")
    await element.click(timeout=10000)


async def click_visible_selector(page, selector):
    locator = page.locator(f"{selector}:visible")
    count = await locator.count()
    if count == 0:
        raise LookupError(f"visible selector target not found: {selector}")
    for index in range(count):
        candidate = locator.nth(index)
        try:
            if not await candidate.is_disabled(timeout=1000):
                await candidate.click(timeout=10000)
                return
        except Exception:
            continue
    await locator.first.click(timeout=10000)


async def screenshot():
    page = state["page"]
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"screenshot-{int(time.time() * 1000)}.png"
    await page.screenshot(path=str(path), full_page=True)
    write_jsonl(ACTION_LOG, {"ts": time.time(), "action": "screenshot", "path": str(path)})
    return {"path": str(path)}


async def click(payload):
    page = state["page"]
    joined = " ".join(str(payload.get(key) or "") for key in ("ref", "text", "selector")).lower()
    compact = "".join(ch for ch in joined if ch.isalnum())
    if any(term in compact for term in FORBIDDEN_TARGET_TERMS):
        raise PermissionError("debug or hidden-state controls are not valid browser actions")
    if payload.get("ref"):
        known = state["last_refs"].get(str(payload["ref"]), {})
        known_text = " ".join(str(known.get(key) or "") for key in ("id", "text")).lower()
        known_compact = "".join(ch for ch in known_text if ch.isalnum())
        if any(term in known_compact for term in FORBIDDEN_TARGET_TERMS):
            raise PermissionError("debug or hidden-state controls are not valid browser actions")
        await click_visible_ref(page, payload["ref"])
        target = {"ref": payload["ref"]}
    elif payload.get("selector"):
        await click_visible_selector(page, payload["selector"])
        target = {"selector": payload["selector"]}
    else:
        await click_visible_text(page, payload["text"])
        target = {"text": payload["text"]}
    await page.wait_for_timeout(100)
    write_jsonl(ACTION_LOG, {"ts": time.time(), "action": "click", **target})
    await log_visible_progress()
    return {"ok": True}


async def type_text(payload):
    page = state["page"]
    selector = f'[data-bench-ref="{payload["ref"]}"]:visible'
    locator = page.locator(selector)
    if payload.get("clear"):
        await locator.fill("", timeout=10000)
    await locator.type(payload["text"], timeout=10000)
    write_jsonl(
        ACTION_LOG,
        {"ts": time.time(), "action": "type", "ref": payload["ref"], "chars": len(payload["text"])},
    )
    return {"ok": True}


async def select_option(payload):
    page = state["page"]
    selector = f'[data-bench-ref="{payload["ref"]}"]:visible'
    locator = page.locator(selector)
    if payload.get("label"):
        await locator.select_option(label=payload["label"], timeout=10000)
        target = {"ref": payload["ref"], "label": payload["label"]}
    elif payload.get("value"):
        await locator.select_option(value=payload["value"], timeout=10000)
        target = {"ref": payload["ref"], "value": payload["value"]}
    elif payload.get("index") is not None:
        await locator.select_option(index=int(payload["index"]), timeout=10000)
        target = {"ref": payload["ref"], "index": int(payload["index"])}
    else:
        raise ValueError("select requires label, value, or index")
    write_jsonl(ACTION_LOG, {"ts": time.time(), "action": "select", **target})
    await log_visible_progress()
    return {"ok": True}


async def key(payload):
    await state["page"].keyboard.press(payload["key"])
    write_jsonl(ACTION_LOG, {"ts": time.time(), "action": "key", "key": payload["key"]})
    await log_visible_progress()
    return {"ok": True}


async def wait(payload):
    seconds = max(0.0, min(float(payload.get("seconds", 1)), 300.0))
    await state["page"].wait_for_timeout(int(seconds * 1000))
    write_jsonl(ACTION_LOG, {"ts": time.time(), "action": "wait", "seconds": seconds})
    await log_visible_progress()
    return {"ok": True}


async def log_visible_progress():
    page = state["page"]
    progress = await page.evaluate(
        """
() => {
  const text = id => {
    const el = document.getElementById(id);
    return el ? (el.innerText || el.textContent || '').trim() : null;
  };
  return {
    clips: text('clips'),
    readout: text('readout1'),
    visibleButtons: Array.from(document.querySelectorAll('button'))
      .filter(b => {
        const s = getComputedStyle(b);
        const r = b.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width && r.height;
      })
      .slice(0, 30)
      .map(b => (b.innerText || b.textContent || b.id || '').trim())
  };
}
"""
    )
    progress["ts"] = time.time()
    write_jsonl(PROGRESS_LOG, progress)


async def verify_state():
    page = state["page"]
    return await page.evaluate(
        """
() => {
  const raw = window.localStorage.getItem('savePrestige');
  let parsed = null;
  try { parsed = raw ? JSON.parse(raw) : null; } catch (err) { parsed = { parseError: String(err) }; }
  return {
    url: window.location.href,
    savePrestigeRaw: raw,
    savePrestige: parsed,
    visiblePrestigeU: document.getElementById('prestigeUcounter')?.innerText || null,
    visiblePrestigeS: document.getElementById('prestigeScounter')?.innerText || null
  };
}
"""
    )


async def route(path, payload, headers):
    async with state["lock"]:
        if path == "/screenshot":
            return await screenshot()
        if path == "/dom":
            return await visible_dom()
        if path == "/click":
            return await click(payload)
        if path == "/type":
            return await type_text(payload)
        if path == "/select":
            return await select_option(payload)
        if path == "/key":
            return await key(payload)
        if path == "/wait":
            return await wait(payload)
        if path == "/verify":
            token = TOKEN_PATH.read_text(encoding="utf-8").strip()
            if headers.get("X-Verifier-Token") != token:
                raise PermissionError("invalid verifier token")
            return await verify_state()
        raise FileNotFoundError(path)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if urlparse(self.path).path == "/healthz":
            self.respond(200, {"ok": True})
            return
        self.respond(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw) if raw else {}
            result = asyncio.run_coroutine_threadsafe(route(path, payload, self.headers), loop).result()
            self.respond(200, result)
        except PermissionError as exc:
            self.respond(403, {"error": str(exc)})
        except FileNotFoundError as exc:
            self.respond(404, {"error": str(exc)})
        except Exception as exc:
            self.respond(500, {"error": type(exc).__name__, "message": str(exc)})

    def respond(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def main():
    await start_browser()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    await asyncio.to_thread(server.serve_forever)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(main())
