from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "debug_opponent_assumptions.py"


def _run_debug_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def test_debug_opponent_assumptions_cli_exists() -> None:
    assert SCRIPT.exists()


def test_debug_opponent_assumptions_cli_known_species_outputs_safe_json() -> None:
    result = _run_debug_cli("--species", "rotom-wash")

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)

    assert payload["opponent_species_id"] == "rotom-wash"
    assert payload["opponent_assumptions_available"] is True
    assert payload["schema_version"] == "opponent_assumptions_v0.47"
    assert payload["metadata_version"] == "minimal_metadata_v1"
    assert payload["payload_features"] == {
        "possible_samples": True,
        "minimal_metadata": True,
        "debug_summary_supported": True,
        "full_stats_excluded": True,
        "damage_speed_integration": False,
    }
    assert payload["possible_sample_count"] >= 1
    assert payload["included_top_k"] >= 1

    sample = payload["possible_samples"][0]
    assert sample["sample_id"] == "rotom_wash_defensive_pivot_repo_v42"
    assert sample["species_id"] == "rotom-wash"
    assert sample["role"] == "defensive_pivot"
    assert sample["archetype_id"] == "rotom_wash_defensive_pivot_repo_v42"
    assert sample["confidence"] == "estimated"
    assert sample["possible_items"] == ["leftovers", "sitrus-berry"]
    assert sample["is_user_confirmed"] is False
    assert sample["used_for_damage"] is False
    assert sample["used_for_speed"] is False

    guardrails = payload["guardrails"]
    assert guardrails["context_only"] is True
    assert guardrails["not_confirmed"] is True
    assert guardrails["not_damage_input"] is True
    assert guardrails["not_speed_input"] is True
    assert guardrails["not_final_turn_order"] is True

    forbidden_fragments = (
        '"pokemon"',
        '"stat_profiles"',
        '"item_profiles"',
        '"moves"',
        '"stats"',
        "possible_stats",
        "sp_distribution",
        "source_url",
        "source_note",
        "reviewer_notes",
        "api_key",
        "secret",
        '"env"',
        "token_usage",
        "GEMINI",
    )
    for fragment in forbidden_fragments:
        assert fragment not in result.stdout


def test_debug_opponent_assumptions_cli_unknown_species_is_safe_unavailable_json() -> None:
    result = _run_debug_cli("--species", "missingno")

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)

    assert payload["opponent_species_id"] == "missingno"
    assert payload["opponent_assumptions_available"] is False
    assert payload["reason"] == "no_samples_for_species"
    assert payload["calculation_usage"] == "context_only"
    assert payload["possible_sample_count"] == 0
    assert payload["possible_samples"] == []
    assert payload["guardrails"]["context_only"] is True
    assert '"stats"' not in result.stdout
    assert "possible_stats" not in result.stdout
    assert "sp_distribution" not in result.stdout
    assert "api_key" not in result.stdout
    assert "token_usage" not in result.stdout


def test_debug_opponent_assumptions_cli_top_k_limits_output() -> None:
    result = _run_debug_cli("--species", "garchomp", "--top-k", "1")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["opponent_assumptions_available"] is True
    assert payload["possible_sample_count"] == 1
    assert payload["included_top_k"] == 1
