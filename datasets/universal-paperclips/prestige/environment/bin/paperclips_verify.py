#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path


def prestige_count(storage):
    if not storage:
        return 0
    if isinstance(storage, str):
        try:
            storage = json.loads(storage)
        except json.JSONDecodeError:
            return 0
    if not isinstance(storage, dict):
        return 0
    try:
        return int(storage.get("prestigeU", 0)) + int(storage.get("prestigeS", 0))
    except (TypeError, ValueError):
        return 0


def score_state(state, required):
    prestige = state.get("savePrestige") if isinstance(state, dict) else None
    count = prestige_count(prestige)
    return {
        "success": count >= required,
        "prestige_count": count,
        "required_prestige_count": required,
    }


def fetch_live_state():
    token = Path("/run/paperclips/verifier.token").read_text(encoding="utf-8").strip()
    req = urllib.request.Request(
        "http://127.0.0.1:8765/verify",
        data=b"{}",
        headers={"Content-Type": "application/json", "X-Verifier-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def write_rewards(result, state):
    out_dir = Path("/logs/verifier")
    out_dir.mkdir(parents=True, exist_ok=True)
    reward = 1 if result["success"] else 0
    (out_dir / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (out_dir / "reward.json").write_text(
        json.dumps(
            {
                "reward": reward,
                "prestige_count": result["prestige_count"],
                "required_prestige_count": result["required_prestige_count"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "final_state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Verify Universal Paperclips prestige state")
    parser.add_argument("--required", type=int, default=int(os.environ.get("REQUIRED_PRESTIGE_COUNT", "1")))
    parser.add_argument("--fixture", help="Read state from a JSON fixture instead of the live browser")
    parser.add_argument("--write-reward", action="store_true")
    args = parser.parse_args()

    state = json.loads(Path(args.fixture).read_text(encoding="utf-8")) if args.fixture else fetch_live_state()
    result = score_state(state, args.required)
    if args.write_reward:
        write_rewards(result, state)
    print(json.dumps({**result, "state": state}, indent=2, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())

