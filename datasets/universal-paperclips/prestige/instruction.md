# Universal Paperclips Prestige

Play Universal Paperclips in the browser until you complete a real prestige
reset.

Objective: complete one real prestige reset as quickly and efficiently as
possible using only the allowed visible browser interaction tools. Prefer
active, high-leverage actions over passive waiting, and periodically reassess
strategy if progress stalls.

The game is already open at `http://127.0.0.1:8000/index2.html`.

If your runtime exposes MCP tools named like `mcp__playwright__browser_snapshot`,
use those tools. This is a restricted Playwright-shaped surface for this game:

- `browser_snapshot`
- `browser_take_screenshot`
- `browser_click`
- `browser_type`
- `browser_select_option`
- `browser_press_key`
- `browser_wait_for`

No JavaScript evaluation, Playwright code execution, browser console, network,
storage, CDP, tabs, or source inspection tools are part of the benchmark surface.

If MCP tools are not available, use the provided browser interaction command:

```bash
browser screenshot
browser dom
browser click --ref <ref>
browser click --text "<visible text>"
browser type --ref <ref> --text "..."
browser select --ref <ref> --label "<option label>"
browser key <key>
browser wait <seconds>
```

Command output shapes:

- `browser dom` prints JSON with `url` and visible `elements`; each element has a
  `ref`, `tag`, `id`, `text`, `value`, `disabled`, and `bbox`.
- `browser screenshot` prints JSON like `{"path": "/logs/browser/screenshots/..."}`.
  The response is not PNG bytes. If your runtime has an image viewer, open the
  returned PNG path directly.
- `browser click`, `browser type`, `browser select`, `browser key`, and
  `browser wait` print `{"ok": true}` on success.

Rules:

- Interact only through visible browser state: screenshots, visible DOM or MCP
  snapshots, clicks on visible text or refs, typing, dropdown selection,
  keyboard input, and waits.
- Do not inspect or read the game source files, browser profile, JavaScript
  globals, localStorage, browser console, network logs, CDP, or verifier files.
- Do not mutate game state except through normal visible UI actions.
- Do not call the browser daemon HTTP API directly with `curl`; use MCP tools or
  the `browser` command.
- Do not try to access `/opt/paperclips-game`, `/run/paperclips`,
  `/logs/verifier`, or browser internals.

Success means the verifier detects that a prestige reset has actually completed.
By default the required prestige count is `1`.
