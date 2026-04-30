#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "environment" / "bin" / "paperclips_verify.py"

spec = importlib.util.spec_from_file_location("paperclips_verify", VERIFY_PATH)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def fixture(name):
    return json.loads((ROOT / "tests" / "fixtures" / name / "state.json").read_text(encoding="utf-8"))


def test_fresh_game_fails():
    result = verify.score_state(fixture("fresh"), required=1)
    assert result == {"success": False, "prestige_count": 0, "required_prestige_count": 1}


def test_midgame_fails():
    result = verify.score_state(fixture("midgame"), required=1)
    assert result["success"] is False
    assert result["prestige_count"] == 0


def test_one_prestige_succeeds_for_default():
    result = verify.score_state(fixture("one-prestige"), required=1)
    assert result["success"] is True
    assert result["prestige_count"] == 1


def test_one_prestige_fails_for_higher_threshold():
    result = verify.score_state(fixture("one-prestige"), required=2)
    assert result["success"] is False
    assert result["prestige_count"] == 1


def test_two_prestige_succeeds_for_higher_threshold():
    result = verify.score_state(fixture("two-prestige"), required=2)
    assert result["success"] is True
    assert result["prestige_count"] == 2


if __name__ == "__main__":
    tests = [
        test_fresh_game_fails,
        test_midgame_fails,
        test_one_prestige_succeeds_for_default,
        test_one_prestige_fails_for_higher_threshold,
        test_two_prestige_succeeds_for_higher_threshold,
    ]
    for test in tests:
        test()
        print(f"ok {test.__name__}")

