# Universal Paperclips Benchmark

## Task

`universal-paperclips/prestige` asks an agent to play Universal Paperclips in an
isolated browser until a real prestige reset completes.

For commands to run the benchmark, see the repository `README.md`.

## Game and Motivation

Universal Paperclips, created by Frank Lantz, is an incremental browser game
about turning a tiny paperclip business into a world-consuming optimization
loop. The early game is a simple visible UI with a paperclip button, inventory,
pricing, and demand. Over time it expands into manufacturing, investment,
compute allocation, strategic modeling, drone swarms, space exploration, and a
final prestige reset after the universe has been converted.

That progression makes it a useful Harbor eval because the task is easy to state
but hard to complete robustly. A winning agent must operate a normal browser UI
for hours, track delayed resource effects, adapt as new systems unlock, recover
from local mistakes, and keep optimizing toward a distant objective. In other
words, it tests both long-running execution and long-horizon agency. The eval
does not depend on private domain knowledge or subjective judging: Harbor can
isolate the browser surface and score success by checking hidden prestige state
outside the agent context.

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

The task provides a restricted Playwright-shaped MCP server named `playwright`
when the agent runtime supports MCP. It exposes only:

- `browser_snapshot`
- `browser_take_screenshot`
- `browser_click`
- `browser_type`
- `browser_select_option`
- `browser_press_key`
- `browser_wait_for`

The MCP server wraps the same restricted browser daemon as the CLI below. It does
not expose JavaScript evaluation, Playwright code execution, browser console,
network logs, storage, CDP, tabs, or source inspection.

Agents without MCP support should interact through the `browser` command:

- `browser screenshot`
- `browser dom`
- `browser click --ref <ref>`
- `browser click --text "..."`
- `browser type --ref <ref> --text "..."`
- `browser select --ref <ref> --label "..."`
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

## Version History

- `v1.1.2`: Current baseline. Adds explicit fastest-success guidance and
  stalled-strategy reassessment to the v1.1.1 restricted MCP surface.
- `v1.1.1`: Adds the restricted Playwright-shaped MCP server while keeping the
  v1.1.0 success condition and timeout.
- `v1.1.0`: Generalized visible action instructions and a 16-hour agent timeout,
  before MCP support.
- `v1.0.0`: 12-hour prestige baseline after isolation and harness improvements.

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

Leaderboard result labels separate gameplay outcomes from runtime issues:

- `verified win`: the verifier scored reward 1.
- `game failure`: the agent completed without earning the required prestige.
- `timeout`: the agent reached the task time limit.
- `agent/runtime error`: the agent process or harness exited before a clean
  scored completion.

Browser artifacts:

- `/logs/browser/actions.jsonl`
- `/logs/browser/progress.jsonl`
- `/logs/browser/screenshots/*.png`
- `/logs/browser/http.log`
- `/logs/browser/daemon.log`

## Initial Matrix

Run one 16-hour trial for each first:

- Claude Code, Sonnet class matching the prior long run.
- Codex CLI, current practical default coding model.
- Gemini CLI, current practical Pro/Thinking model.

After isolation and scoring are stable, add one stronger frontier model or one
cheaper baseline per family, then expand to repeated trials.
