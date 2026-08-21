"""Intrinsic Poison Heal replacement adapter for detached poison/Toxic EOT."""
from typing import Any, Mapping
from llm.advisor_end_of_turn_preview import project_poison_end_of_turn


def project_poison_heal_end_of_turn(*, pre_end_of_turn: Mapping[str, Any]) -> dict[str, Any]:
    """Delegate to the canonical poison/Toxic path, which owns lifecycle validation."""
    return project_poison_end_of_turn(pre_end_of_turn=pre_end_of_turn)
