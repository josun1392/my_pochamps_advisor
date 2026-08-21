"""Rain-only detached Rain Dish EOT adapter for the deterministic Turn Engine."""
from __future__ import annotations

from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _project_weather_recovery_end_of_turn


def project_rain_dish_end_of_turn(*, pre_end_of_turn: Mapping[str, Any]) -> dict[str, Any]:
    """Apply exact Rain Dish recovery under branch-owned Rain without ordering residuals."""
    return _project_weather_recovery_end_of_turn(pre_end_of_turn=pre_end_of_turn, ability="rain-dish", weather="rain", label="rain_dish")
