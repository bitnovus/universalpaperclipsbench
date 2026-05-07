#!/usr/bin/env python3
"""Build the public leaderboard data file from local Harbor job results."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def seconds_between(start: datetime | None, finish: datetime | None) -> int | None:
    if start is None or finish is None:
        return None
    return max(0, round((finish - start).total_seconds()))


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_version_config(
    config_path: Path | None,
) -> tuple[str, list[dict[str, Any]], dict[str, str], dict[str, dict[str, Any]], set[str]]:
    default_version = "v1.1.1"
    if config_path is None:
        return default_version, [], {}, {}, set()

    data = read_json(config_path)
    if not data:
        return default_version, [], {}, {}, set()

    current_version = data.get("current_version")
    if not isinstance(current_version, str):
        current_version = default_version

    excluded_jobs = {
        job_name
        for job_name in data.get("exclude_jobs", [])
        if isinstance(job_name, str)
    }

    versions = data.get("versions") or []
    normalized_versions: list[dict[str, Any]] = []
    job_versions: dict[str, str] = {}
    version_details: dict[str, dict[str, Any]] = {}
    for item in versions:
        if not isinstance(item, dict) or not isinstance(item.get("version"), str):
            continue
        version = item["version"]
        jobs = [job for job in item.get("jobs", []) if isinstance(job, str)]
        normalized = {
            "version": version,
            "label": item.get("label") if isinstance(item.get("label"), str) else version,
            "description": item.get("description") if isinstance(item.get("description"), str) else "",
            "jobs": jobs,
        }
        for key in ("timeout_seconds", "browser_surface", "comparison_note"):
            if key in item:
                normalized[key] = item[key]
        normalized_versions.append(normalized)
        version_details[version] = normalized
        for job_name in jobs:
            job_versions[job_name] = version

    if current_version not in {item["version"] for item in normalized_versions}:
        current = {
            "version": current_version,
            "label": current_version,
            "description": "Current benchmark baseline.",
            "jobs": [],
        }
        normalized_versions.insert(0, current)
        version_details[current_version] = current

    return current_version, normalized_versions, job_versions, version_details, excluded_jobs


def reward_from(result: dict[str, Any]) -> float | None:
    rewards = (result.get("verifier_result") or {}).get("rewards") or {}
    reward = rewards.get("reward")
    if isinstance(reward, int | float):
        return float(reward)
    return None


def effort_from(kwargs: dict[str, Any]) -> str | None:
    effort = kwargs.get("reasoning_effort") or kwargs.get("model_reasoning_effort")
    if isinstance(effort, str):
        return effort
    return None


def effort_from_job_name(job_name: str) -> str | None:
    for effort in ("xhigh", "high", "medium", "auto"):
        if f"-{effort}-" in job_name:
            return effort
    return None


def ralph_loops_from(trial_dir: Path) -> int | None:
    sessions_dir = trial_dir / "agent" / "sessions" / "projects" / "-app"
    if not sessions_dir.exists():
        return None

    max_iteration: int | None = None
    for jsonl_path in sessions_dir.glob("*.jsonl"):
        try:
            lines = jsonl_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            marker = "Ralph iteration "
            index = line.find(marker)
            if index < 0:
                continue
            start = index + len(marker)
            end = start
            while end < len(line) and line[end].isdigit():
                end += 1
            if end == start:
                continue
            max_iteration = max(max_iteration or 0, int(line[start:end]))

    if max_iteration is None:
        return None
    return max(0, max_iteration - 1)


def run_notes_from(job_name: str, ralph_loops: int | None) -> list[str]:
    notes: list[str] = []
    if "ralph" in job_name:
        if ralph_loops is None:
            notes.append("Ralph loop persistence")
        else:
            notes.append(f"Ralph loop persistence ({ralph_loops} loops)")
    return notes


def status_for(reward: float | None, exception_type: str | None) -> str:
    if reward is not None and reward >= 1:
        return "success"
    if exception_type == "AgentTimeoutError":
        return "timeout"
    if exception_type:
        return "agent_error"
    return "game_failure"


def load_trial(job_dir: Path, trial_path: Path) -> dict[str, Any] | None:
    result = read_json(trial_path)
    if not result:
        return None

    config = result.get("config") or {}
    agent = config.get("agent") or {}
    kwargs = agent.get("kwargs") or {}
    agent_result = result.get("agent_result") or {}
    exception = result.get("exception_info") or {}

    started_at = parse_time(result.get("started_at"))
    finished_at = parse_time(result.get("finished_at"))
    agent_execution = result.get("agent_execution") or {}
    agent_started_at = parse_time(agent_execution.get("started_at"))
    agent_finished_at = parse_time(agent_execution.get("finished_at"))

    reward = reward_from(result)
    exception_type = exception.get("exception_type")
    if not isinstance(exception_type, str):
        exception_type = None

    ralph_loops = ralph_loops_from(trial_path.parent)
    run_notes = run_notes_from(job_dir.name, ralph_loops)

    entry = {
        "job_name": job_dir.name,
        "harbor_job_id": config.get("job_id"),
        "trial_name": result.get("trial_name"),
        "task": result.get("task_name"),
        "task_path": (result.get("task_id") or {}).get("path"),
        "task_checksum": result.get("task_checksum"),
        "agent": agent.get("name"),
        "agent_version": (result.get("agent_info") or {}).get("version"),
        "model": agent.get("model_name"),
        "reasoning_effort": effort_from(kwargs) or effort_from_job_name(job_dir.name),
        "reward": reward,
        "status": status_for(reward, exception_type),
        "exception_type": exception_type,
        "started_at": isoformat(started_at),
        "finished_at": isoformat(finished_at),
        "duration_seconds": seconds_between(started_at, finished_at),
        "agent_duration_seconds": seconds_between(agent_started_at, agent_finished_at),
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
    }
    if ralph_loops is not None:
        entry["ralph_loops"] = ralph_loops
    if run_notes:
        entry["run_notes"] = run_notes
    return entry


def load_entries(
    jobs_dir: Path,
    include_dry_runs: bool,
    current_version: str,
    job_versions: dict[str, str],
    version_details: dict[str, dict[str, Any]],
    excluded_jobs: set[str],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not jobs_dir.exists():
        return entries

    for job_dir in sorted(path for path in jobs_dir.iterdir() if path.is_dir()):
        if job_dir.name in excluded_jobs:
            continue
        if not include_dry_runs and job_dir.name.startswith("dry-run"):
            continue
        for trial_path in sorted(job_dir.glob("*/result.json")):
            entry = load_trial(job_dir, trial_path)
            if entry:
                benchmark_version = job_versions.get(job_dir.name, current_version)
                version_detail = version_details.get(benchmark_version, {})
                entry["benchmark_version"] = benchmark_version
                entry["timeout_seconds"] = version_detail.get("timeout_seconds")
                entry["browser_surface"] = version_detail.get("browser_surface")
                entries.append(entry)

    def sort_key(entry: dict[str, Any]) -> tuple[float, int, int, str]:
        reward = entry.get("reward")
        duration = entry.get("agent_duration_seconds") or entry.get("duration_seconds")
        status_rank = {
            "success": 0,
            "game_failure": 1,
            "timeout": 2,
            "agent_error": 3,
        }.get(entry.get("status"), 4)
        finished = entry.get("finished_at") or ""
        return (
            -(reward if isinstance(reward, int | float) else -1),
            status_rank,
            duration or 10**12,
            finished,
        )

    return sorted(entries, key=sort_key)


def build_payload(
    entries: list[dict[str, Any]],
    current_version: str,
    versions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generated_at": isoformat(datetime.now(timezone.utc)),
        "source": "local Harbor job result.json files",
        "benchmark": {
            "name": "Universal Paperclips Prestige",
            "task": "universal-paperclips/prestige",
            "current_version": current_version,
            "default_required_prestige_count": 1,
            "success_condition": "verifier reward equals 1 after a completed prestige reset",
        },
        "versions": versions,
        "summary": {
            "runs": len(entries),
            "successes": sum(1 for entry in entries if entry.get("status") == "success"),
            "game_failures": sum(1 for entry in entries if entry.get("status") == "game_failure"),
            "timeouts": sum(1 for entry in entries if entry.get("status") == "timeout"),
            "agent_errors": sum(1 for entry in entries if entry.get("status") == "agent_error"),
            "errors": sum(1 for entry in entries if entry.get("status") == "agent_error"),
            "failures": sum(1 for entry in entries if entry.get("status") == "game_failure"),
        },
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-dir", default="jobs", type=Path)
    parser.add_argument("--output", default="docs/leaderboard.json", type=Path)
    parser.add_argument("--versions", default="docs/leaderboard-versions.json", type=Path)
    parser.add_argument("--include-dry-runs", action="store_true")
    args = parser.parse_args()

    current_version, versions, job_versions, version_details, excluded_jobs = load_version_config(args.versions)
    entries = load_entries(
        args.jobs_dir,
        args.include_dry_runs,
        current_version,
        job_versions,
        version_details,
        excluded_jobs,
    )
    payload = build_payload(entries, current_version, versions)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} with {len(entries)} run(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
