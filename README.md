# Universal Paperclips Harbor Benchmark

This repository contains a Harbor benchmark task for Universal Paperclips.

The canonical task is `datasets/universal-paperclips/prestige`. It runs a
vendored Universal Paperclips snapshot in a browser and scores success when the
verifier observes at least one completed prestige reset.

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
.venv/bin/harbor run -p datasets/universal-paperclips -a codex -m gpt-5.3-codex --artifact /logs/browser
.venv/bin/harbor run -p datasets/universal-paperclips -a claude-code -m claude-sonnet-4-5 --artifact /logs/browser
.venv/bin/harbor run -p datasets/universal-paperclips -a gemini-cli -m gemini-2.5-pro --artifact /logs/browser
```

You can also run the single task path directly:

```bash
.venv/bin/harbor run -p datasets/universal-paperclips/prestige -a codex -m <model> --artifact /logs/browser
```

The default task timeout is 12 hours. The verifier writes Harbor rewards to
`/logs/verifier/reward.txt` and richer metrics to `/logs/verifier/reward.json`.

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

The GitHub Pages site lives in `docs/` and renders `docs/leaderboard.json`.
Raw Harbor `jobs/` artifacts are ignored because they can contain transcripts,
SQLite state, and local auth/cache files.

After a run finishes, refresh the public leaderboard data from local Harbor
results:

```bash
python3 scripts/update_leaderboard.py
```

Then commit the updated `docs/leaderboard.json`. Dry-run jobs are excluded by
default; pass `--include-dry-runs` only for local debugging. Benchmark versions
are assigned in `docs/leaderboard-versions.json`; jobs not listed there default
to the current version.

The included workflow publishes `docs/` through GitHub Actions. In the GitHub
repository settings, configure Pages to use GitHub Actions as the source.

## Inspect

An Inspect compatibility wrapper is provided under `inspect/`. It is intentionally
thin: Harbor remains the source of truth.
