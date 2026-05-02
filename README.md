# Universal Paperclips Harbor Benchmark

This repository contains a Harbor benchmark task for Universal Paperclips.

The canonical task is `datasets/universal-paperclips/prestige`. It runs a
vendored Universal Paperclips snapshot in a browser and scores success when the
verifier observes at least one completed prestige reset.

Universal Paperclips, created by Frank Lantz, is a compact incremental browser
game whose simple early UI expands into pricing, manufacturing, compute
allocation, strategic modeling, drone swarms, space exploration, and a final
prestige reset. It is a motivating Harbor eval because the goal is objective,
the interface is ordinary browser UI, and success tests long-running,
long-horizon planning over hours rather than a single tool call or short
interaction.

## Run

Install Harbor first if it is not already available:

```bash
asdf exec python -m venv .venv
.venv/bin/python -m pip install --upgrade pip harbor
```

From the repository root:

```bash
.venv/bin/harbor run -p datasets/universal-paperclips -a codex -m <model> --artifact /logs/browser
```

Examples:

```bash
.venv/bin/harbor run -p datasets/universal-paperclips -a codex -m gpt-5.5 --artifact /logs/browser
.venv/bin/harbor run -p datasets/universal-paperclips -a claude-code -m claude-sonnet-4-6 --artifact /logs/browser
.venv/bin/harbor run -p datasets/universal-paperclips -a gemini-cli -m gemini-2.5-pro --artifact /logs/browser
```

You can also run the single task path directly:

```bash
.venv/bin/harbor run -p datasets/universal-paperclips/prestige -a codex -m <model> --artifact /logs/browser
```

The default task timeout is 16 hours. The verifier writes Harbor rewards to
`/logs/verifier/reward.txt` and richer metrics to `/logs/verifier/reward.json`.

The task also registers a restricted Playwright-shaped MCP server named
`playwright` for agents that support MCP. It exposes snapshot, screenshot,
click, type, dropdown select, key, and wait tools only; JavaScript evaluation,
Playwright code execution, console, network, storage, CDP, and tab tools are not
part of the benchmark surface.

## Local Checks

```bash
bash tests/local_validate.sh
```

This validates task files, verifier fixtures, and vendored-game provenance
without needing Harbor.

## Docker Smoke Test

Use this to verify the browser harness and verifier manually:

```bash
docker build -t universal-paperclips-prestige:local datasets/universal-paperclips/prestige/environment
docker run --rm -d --name up-smoke universal-paperclips-prestige:local
docker exec -u agent up-smoke browser dom
docker exec -u agent up-smoke browser click --text "Make Paperclip"
docker exec -u agent up-smoke browser screenshot
docker exec up-smoke /usr/local/bin/paperclips_verify.py --write-reward
docker exec up-smoke cat /logs/verifier/reward.txt
docker stop up-smoke
```

A fresh smoke run should write reward `0`. A benchmark trial scores reward `1`
only after the verifier observes a completed prestige reset.

## Outputs

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

## Leaderboard

The public leaderboard is published at:

```text
https://bitnovus.github.io/universalpaperclipsbench/
```

The static site lives in `docs/` and renders `docs/leaderboard.json`. Raw
Harbor `jobs/` artifacts are ignored because they can contain transcripts,
SQLite state, and local auth/cache files.

Serve the leaderboard locally with `docs/` as the web root:

```bash
python3 -m http.server 8765 --directory docs
```

Then open `http://localhost:8765/`.

After a run finishes, refresh the public leaderboard data from local Harbor
results:

```bash
python3 scripts/update_leaderboard.py
```

Then commit the updated `docs/leaderboard.json`. Dry-run jobs are excluded by
default; pass `--include-dry-runs` only for local debugging. Benchmark versions
are assigned in `docs/leaderboard-versions.json`; jobs not listed there default
to the current version. The v1 line uses semver-style labels: `v1.0.0` for the
12-hour isolated browser baseline, `v1.1.0` for the 16-hour instruction update,
and `v1.1.1` for the restricted Playwright-shaped MCP surface.

The included workflow publishes `docs/` through GitHub Actions and configures
GitHub Pages for the repository.

## License

The benchmark harness, verifier, documentation, leaderboard, and related tooling
in this repository are licensed under the MIT License. See `LICENSE`.

The vendored Universal Paperclips game source and assets under
`datasets/universal-paperclips/prestige/environment/vendor/` are third-party
materials by their original authors and rights holders. They are included for
benchmark reproducibility and are not covered by this repository's MIT License.
See `THIRD_PARTY_NOTICES.md`.

## Inspect

An Inspect compatibility wrapper is provided under `inspect/`. It is intentionally
thin: Harbor remains the source of truth.
