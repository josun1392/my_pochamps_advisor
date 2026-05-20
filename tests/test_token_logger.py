from __future__ import annotations

import json

import pytest

from llm.token_logger import (
    FREE_TIER_ZERO_COST,
    PAID_TIER_ESTIMATED_COST,
    PRICING,
    UNKNOWN_MODEL_OR_UNKNOWN_PRICING,
    TokenLogger,
    normalize_model,
    pricing_status_for_model,
)


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_log_call_creates_jsonl_record(tmp_path) -> None:
    log_path = tmp_path / "token_usage.jsonl"
    logger = TokenLogger(str(log_path))

    logger.log_call(
        model="gemini-3-flash",
        input_tokens=14_523,
        output_tokens=412,
        cached_tokens=8_000,
        tool_name="damage_calculator",
        turn_number=3,
        game_id="game_001",
    )

    records = _read_jsonl(log_path)
    assert len(records) == 1
    assert records[0]["game_id"] == "game_001"
    assert records[0]["turn"] == 3
    assert records[0]["model"] == "gemini-3-flash"
    assert records[0]["tool_name"] == "damage_calculator"
    assert records[0]["input_tokens"] == 14_523
    assert records[0]["output_tokens"] == 412
    assert records[0]["cached_tokens"] == 8_000
    assert records[0]["pricing_status"] == PAID_TIER_ESTIMATED_COST
    assert "timestamp" in records[0]


def test_estimate_cost_matches_pricing_table() -> None:
    logger = TokenLogger()
    expected = (
        1_000 * PRICING["gemini-3-flash"]["input"]
        + 200 * PRICING["gemini-3-flash"]["output"]
        + 500 * PRICING["gemini-3-flash"]["cache"]
    )

    assert logger.estimate_cost(1_000, 200, 500, model="gemini-3-flash") == pytest.approx(expected)


def test_session_summary_accumulates_totals_and_cost(tmp_path) -> None:
    logger = TokenLogger(str(tmp_path / "usage.jsonl"))

    logger.log_call("gemini-3-flash", 1_000, 100, 50, tool_name="damage_calculator")
    logger.log_call("gemini-3-flash", 2_000, 200, 100, tool_name="damage_calculator")

    expected_cost = logger.estimate_cost(3_000, 300, 150, model="gemini-3-flash")
    summary = logger.get_session_summary()
    assert summary["total_calls"] == 2
    assert summary["total_input_tokens"] == 3_000
    assert summary["total_output_tokens"] == 300
    assert summary["total_cached_tokens"] == 150
    assert summary["estimated_cost_usd"] == pytest.approx(expected_cost)
    assert summary["pricing_status"] == PAID_TIER_ESTIMATED_COST
    assert summary["pricing_status_counts"] == {PAID_TIER_ESTIMATED_COST: 2}


def test_session_summary_breaks_down_by_tool(tmp_path) -> None:
    logger = TokenLogger(str(tmp_path / "usage.jsonl"))

    logger.log_call("gemini-3-flash", 1_000, 100, tool_name="damage_calculator")
    logger.log_call("gemini-3-flash", 300, 30, tool_name="team_advisor")
    logger.log_call("gemini-3-flash", 200, 20)

    summary = logger.get_session_summary()
    assert summary["by_tool"]["damage_calculator"]["total_calls"] == 1
    assert summary["by_tool"]["damage_calculator"]["pricing_status"] == PAID_TIER_ESTIMATED_COST
    assert summary["by_tool"]["team_advisor"]["total_input_tokens"] == 300
    assert summary["by_tool"]["unknown"]["total_output_tokens"] == 20


def test_log_call_appends_multiple_jsonl_lines(tmp_path) -> None:
    log_path = tmp_path / "nested" / "usage.jsonl"
    logger = TokenLogger(str(log_path))

    logger.log_call("gemini-3-flash", 10, 1)
    logger.log_call("gemini-3-flash", 20, 2)

    records = _read_jsonl(log_path)
    assert [record["model"] for record in records] == ["gemini-3-flash", "gemini-3-flash"]


def test_file_io_failure_warns_but_keeps_session_totals(tmp_path, capsys) -> None:
    logger = TokenLogger(str(tmp_path))

    logger.log_call("gemini-3-flash", 10, 2, tool_name="damage_calculator")

    captured = capsys.readouterr()
    assert "warning: failed to write token usage log" in captured.err
    summary = logger.get_session_summary()
    assert summary["total_calls"] == 1
    assert summary["total_input_tokens"] == 10


def test_unknown_model_cost_warns_and_returns_zero(capsys) -> None:
    logger = TokenLogger()

    assert logger.estimate_cost(100, 100, model="unknown-model") == 0.0
    warning = capsys.readouterr().err
    assert "warning: unknown model pricing" in warning
    assert "normalized: 'unknown-model'" in warning


def test_unknown_model_summary_is_pricing_unknown(tmp_path) -> None:
    logger = TokenLogger(str(tmp_path / "usage.jsonl"))

    logger.log_call("unknown-model", 100, 100)

    summary = logger.get_session_summary()
    records = _read_jsonl(tmp_path / "usage.jsonl")
    assert summary["pricing_status"] == UNKNOWN_MODEL_OR_UNKNOWN_PRICING
    assert summary["pricing_status_counts"] == {UNKNOWN_MODEL_OR_UNKNOWN_PRICING: 1}
    assert records[0]["pricing_status"] == UNKNOWN_MODEL_OR_UNKNOWN_PRICING


def test_negative_token_counts_warn_and_return_zero(capsys) -> None:
    logger = TokenLogger()

    assert logger.estimate_cost(-1, 100, model="gemini-3-flash") == 0.0
    assert "warning: token counts must be non-negative" in capsys.readouterr().err


def test_gemini_pro_pricing_warns_that_it_is_unverified(capsys) -> None:
    logger = TokenLogger()

    assert logger.estimate_cost(100, 10, model="gemini-3-pro") > 0
    assert "warning: gemini-3-pro pricing is an unverified estimate" in capsys.readouterr().err


def test_pricing_alias_resolution() -> None:
    assert normalize_model("gemini-3-flash-preview") == "gemini-3-flash"
    assert normalize_model("gemini-2.5-flash-latest") == "gemini-2.5-flash"


def test_gemini_25_flash_free_tier_zero_cost(tmp_path, capsys) -> None:
    logger = TokenLogger(str(tmp_path / "usage.jsonl"))

    logger.log_call("gemini-2.5-flash", 4_031, 52, tool_name="damage_calculator")

    summary = logger.get_session_summary()
    records = _read_jsonl(tmp_path / "usage.jsonl")
    assert logger.estimate_cost(4_031, 52, model="gemini-2.5-flash") == 0.0
    assert capsys.readouterr().err == ""
    assert summary["estimated_cost_usd"] == 0.0
    assert summary["pricing_status"] == FREE_TIER_ZERO_COST
    assert summary["pricing_status_counts"] == {FREE_TIER_ZERO_COST: 1}
    assert summary["by_tool"]["damage_calculator"]["pricing_status"] == FREE_TIER_ZERO_COST
    assert records[0]["pricing_status"] == FREE_TIER_ZERO_COST


def test_pricing_status_for_model() -> None:
    assert pricing_status_for_model("gemini-2.5-flash") == FREE_TIER_ZERO_COST
    assert pricing_status_for_model("gemini-3-flash-preview") == PAID_TIER_ESTIMATED_COST
    assert pricing_status_for_model("unknown-model") == UNKNOWN_MODEL_OR_UNKNOWN_PRICING


def test_pricing_normal_calculation() -> None:
    logger = TokenLogger()
    expected = (
        1_960 * PRICING["gemini-3-flash"]["input"]
        + 122 * PRICING["gemini-3-flash"]["output"]
    )

    assert logger.estimate_cost(1_960, 122, model="gemini-3-flash-preview") == pytest.approx(expected)
