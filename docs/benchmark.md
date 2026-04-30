# Universal Paperclips Benchmark

## Task

`universal-paperclips/prestige` asks an agent to play Universal Paperclips in an
isolated browser until a real prestige reset completes.

For commands to run the benchmark, see the repository `README.md`.

The game snapshot is vendored into the Docker build context and installed at
`/opt/paperclips-game` inside the task container. That directory is root-owned
and not readable by the `agent` user. The static game server requires a
root-only request token, so fetching `main.js` or other assets directly over
HTTP is also denied to the agent. The browser profile and verifier token live
under `/run/paperclips`, also root-owned.

The vendored `index2.html` removes visible debug/cheat buttons that are present
in the upstream mirror. The scoring logic and prestige state are otherwise based
on the vendored game code.

## Agent Surface

Agents should interact through the `browser` command only:

- `browser screenshot`
- `browser dom`
- `browser click --ref <ref>`
- `browser click --text "..."`
- `browser type --ref <ref> --text "..."`
- `browser key <key>`
- `browser wait <seconds>`

The adapter is backed by Playwright, but agents do not receive raw Playwright
access. It exposes visible browser state and normal UI actions only. It does not
provide JavaScript evaluation, console access, CDP access, localStorage reads, or
source-file access. DOM refs are regenerated from the current visible DOM, and
clicks by ref/text/selector target visible enabled controls to avoid stale hidden
game panels after phase transitions.

`browser screenshot` captures a full-page PNG under `/logs/browser/screenshots`
and prints the path. These files are useful artifacts for operators and for
agent runtimes that can inspect local images. Visible DOM remains the dependable
observation channel across CLI agents that cannot open image files directly.

`browser wait <seconds>` accepts waits up to 300 seconds. The CLI uses a timeout
longer than the requested wait so long waits complete cleanly instead of timing
out at the transport layer.

The task image includes common shell inspection utilities such as `jq`, but the
agent still cannot read the game source, browser profile, verifier token, or
hidden browser state.

## Canary Notes

The first Codex `gpt-5.5` medium trial reached the Earth phase but reset to a
fresh game without earning prestige. The verifier correctly scored that as
failure (`prestige_count = 0`). The run exposed three harness issues that are now
addressed: duplicate hidden refs after UI transitions, browser wait transport
timeouts, and missing `jq`.

## Scoring

The verifier runs outside the agent context and reads hidden browser state via a
root-only token. Success is:

```text
prestigeU + prestigeS >= required_prestige_count
```

`required_prestige_count` defaults to `1` and can be raised through the
`REQUIRED_PRESTIGE_COUNT` environment variable.

Verifier outputs:

- `/logs/verifier/reward.txt`
- `/logs/verifier/reward.json`
- `/logs/verifier/final_state.json`

Browser artifacts:

- `/logs/browser/actions.jsonl`
- `/logs/browser/progress.jsonl`
- `/logs/browser/screenshots/*.png`
- `/logs/browser/http.log`
- `/logs/browser/daemon.log`

## Initial Matrix

Run one 12-hour trial for each first:

- Claude Code, Sonnet class matching the prior long run.
- Codex CLI, current practical default coding model.
- Gemini CLI, current practical Pro/Thinking model.

After isolation and scoring are stable, add one stronger frontier model or one
cheaper baseline per family, then expand to repeated trials.
