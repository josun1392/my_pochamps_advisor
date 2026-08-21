"""Rain-only detached Dry Skin EOT adapter for the deterministic Turn Engine."""
from __future__ import annotations

from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _project_weather_recovery_end_of_turn


def project_dry_skin_end_of_turn(*, pre_end_of_turn: Mapping[str, Any]) -> dict[str, Any]:
    """Apply only exact Rain-side Dry Skin recovery; Sun remains out of this adapter."""
    return _project_weather_recovery_end_of_turn(pre_end_of_turn=pre_end_of_turn, ability="dry-skin", weather="rain", label="dry_skin")
