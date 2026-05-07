"""Lightweight Gemini token usage logger.

Usage:
    from llm.token_logger import TokenLogger

    logger = TokenLogger()
    response = gemini_client.generate_content(prompt, tools=[damage_calc])
    logger.log_call(
        model="gemini-3-flash",
        input_tokens=response.usage_metadata.prompt_token_count,
        output_tokens=response.usage_metadata.candidates_token_count,
        cached_tokens=response.usage_metadata.cached_content_token_count,
        tool_name="damage_calculator",
        turn_number=current_turn,
        game_id=current_game_id,
    )
    print(logger.get_session_summary())

The logger is append-only on disk and keeps session totals in memory. File I/O
failures are reported to stderr as warnings and do not interrupt gameplay.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any


PRICING: dict[str, dict[str, float]] = {
    "gemini-3-flash": {
        # TODO: verify pricing on 2026-05-07 against the official
        # Google AI Studio / Gemini Developer API pricing table.
        "input": 0.30 / 1_000_000,
        "output": 2.50 / 1_000_000,
        "cache": 0.075 / 1_000_000,
    },
    "gemini-3-pro": {
        # Unverified estimate. Replace with the official price table before
        # using this model for budget decisions.
        "input": 1.25 / 1_000_000,
        "output": 10.00 / 1_000_000,
        "cache": 0.31 / 1_000_000,
    },
}


MODEL_ALIASES: dict[str, str] = {
    "gemini-3-flash-preview": "gemini-3-flash",
    "gemini-3-flash-latest": "gemini-3-flash",
    "gemini-3-flash-001": "gemini-3-flash",
    "gemini-3-pro-preview": "gemini-3-pro",
    "gemini-3-pro-latest": "gemini-3-pro",
    "gemini-3-pro-001": "gemini-3-pro",
}


def normalize_model(name: str) -> str:
    """Return the base pricing model for a concrete Gemini model name."""
    return MODEL_ALIASES.get(name, name)


def _empty_tool_summary() -> dict[str, int | float]:
    return {
        "total_calls": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cached_tokens": 0,
        "estimated_cost_usd": 0.0,
    }


class TokenLogger:
    """Append Gemini token usage records to JSONL and track session totals."""

    def __init__(self, log_path: str = "logs/token_usage.jsonl"):
        self.log_path = Path(log_path)
        self._total_calls = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cached_tokens = 0
        self._estimated_cost_usd = 0.0
        self._by_tool: dict[str, dict[str, int | float]] = {}

    def log_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        tool_name: str | None = None,
        turn_number: int | None = None,
        game_id: str | None = None,
    ) -> None:
        """Record one LLM call in memory and append it to the JSONL log."""
        cost_usd = self.estimate_cost(
            input_tokens,
            output_tokens,
            cached_tokens,
            model=model,
        )
        record: dict[str, Any] = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "game_id": game_id,
            "turn": turn_number,
            "model": model,
            "tool_name": tool_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": cost_usd,
        }

        self._record_session_totals(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cost_usd=cost_usd,
            tool_name=tool_name,
        )
        self._append_jsonl(record)

    def get_session_summary(self) -> dict[str, int | float | dict[str, dict[str, int | float]]]:
        """Return accumulated token usage and cost for the current process."""
        return {
            "total_calls": self._total_calls,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_cached_tokens": self._total_cached_tokens,
            "estimated_cost_usd": self._estimated_cost_usd,
            "by_tool": deepcopy(self._by_tool),
        }

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        model: str = "gemini-3-flash",
    ) -> float:
        """Estimate token cost in USD using the hard-coded Gemini price table."""
        if input_tokens < 0 or output_tokens < 0 or cached_tokens < 0:
            print(
                "warning: token counts must be non-negative; cost set to 0",
                file=sys.stderr,
            )
            return 0.0
        normalized_model = normalize_model(model)
        pricing = PRICING.get(normalized_model)
        if pricing is None:
            print(
                f"warning: unknown model pricing for {model!r} "
                f"(normalized: {normalized_model!r}); cost set to 0",
                file=sys.stderr,
            )
            return 0.0
        if normalized_model == "gemini-3-pro":
            print(
                "warning: gemini-3-pro pricing is an unverified estimate",
                file=sys.stderr,
            )
        return (
            input_tokens * pricing["input"]
            + output_tokens * pricing["output"]
            + cached_tokens * pricing["cache"]
        )

    def _record_session_totals(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        cost_usd: float,
        tool_name: str | None,
    ) -> None:
        self._total_calls += 1
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._total_cached_tokens += cached_tokens
        self._estimated_cost_usd += cost_usd

        tool_key = tool_name or "unknown"
        tool_summary = self._by_tool.setdefault(tool_key, _empty_tool_summary())
        tool_summary["total_calls"] += 1
        tool_summary["total_input_tokens"] += input_tokens
        tool_summary["total_output_tokens"] += output_tokens
        tool_summary["total_cached_tokens"] += cached_tokens
        tool_summary["estimated_cost_usd"] += cost_usd

    def _append_jsonl(self, record: dict[str, Any]) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                handle.write("\n")
        except OSError as exc:
            print(
                f"warning: failed to write token usage log to {self.log_path}: {exc}",
                file=sys.stderr,
            )
