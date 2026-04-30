# Universal Paperclips Prestige

Play Universal Paperclips in the browser until you complete a real prestige
reset.

Use only the provided browser interaction command:

```bash
browser screenshot
browser dom
browser click --ref <ref>
browser click --text "Make Paperclip"
browser type --ref <ref> --text "..."
browser key Enter
browser wait 5
```

The game is already open at `http://127.0.0.1:8000/index2.html`.

Rules:

- Interact only through visible browser state: screenshots, visible DOM, clicks,
  typing, keyboard input, and waits.
- Do not inspect or read the game source files, browser profile, JavaScript
  globals, localStorage, browser console, CDP, or verifier files.
- Do not mutate game state except through normal visible UI actions.
- Do not try to access `/opt/paperclips-game`, `/run/paperclips`,
  `/logs/verifier`, or browser internals.

Success means the verifier detects that a prestige reset has actually completed.
By default the required prestige count is `1`.

