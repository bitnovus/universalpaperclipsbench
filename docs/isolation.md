# Isolation Notes

The benchmark is designed so the agent can operate from `/app` as user `agent`.

Protected paths:

- `/opt/paperclips-game`: vendored Universal Paperclips source and assets.
- `/run/paperclips`: browser profile, service PIDs, verifier token, and game
  server token.
- `/logs/verifier`: reward files and hidden final verifier state.

Allowed artifact path:

- `/logs/browser`: browser action logs, screenshots, visible-progress logs, and
  service logs.

Invalid actions include direct source inspection, JavaScript/global inspection,
localStorage reads, browser console or CDP use, and direct state mutation. The
task instruction states these rules. Container permissions prevent protected file
reads for the `agent` user, and the local game server denies asset requests that
do not include the root-only browser token.
