from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import (
    USER_CONFIRMED_CURRENT_ABILITY_FORBIDDEN_FIELDS,
    USER_CONFIRMED_CURRENT_ABILITY_FUTURE_UNSUPPORTED_SOURCES,
    normalize_user_confirmed_current_ability,
)


def _ability(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "side": "self",
        "ability": "intimidate",
        "status": "user_confirmed",
        "source": "user_confirmed_current_ability",
    }
    candidate.update(overrides)
    return candidate


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        (_ability(), "intimidate"),
        (_ability(side="opponent", ability="levitate"), "levitate"),
        (_ability(ability="Quark Drive"), "quark-drive"),
        (_ability(ability="Neutralizing_Gas", confidence="known"), "neutralizing-gas"),
        (_ability(ability="unknown"), "unknown"),
    ],
)
def test_user_confirmed_current_ability_normalizes_only_current_identity(
    candidate: dict[str, object], expected: str
) -> None:
    assert normalize_user_confirmed_current_ability(candidate) == {
        "side": candidate["side"],
        "ability": expected,
        "status": "user_confirmed",
        "source": "user_confirmed_current_ability",
        "confidence": "known",
    }


@pytest.mark.parametrize(
    "candidate",
    [
        {},
        _ability(side="ally"),
        _ability(ability=""),
        _ability(ability="none"),
        _ability(ability="levitate, heatproof"),
        _ability(ability="levitate / heatproof"),
        _ability(status="observed"),
        _ability(source="species_common_meta"),
        _ability(source="battle_log"),
        _ability(confidence="observed"),
        _ability(possible_abilities=["levitate", "heatproof"]),
        _ability(candidate_ability="levitate"),
        _ability(ability_revealed_by_inference=True),
    ],
)
def test_invalid_current_ability_source_status_and_candidate_shapes_are_rejected(candidate: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        normalize_user_confirmed_current_ability(candidate)


@pytest.mark.parametrize("source", sorted(USER_CONFIRMED_CURRENT_ABILITY_FUTURE_UNSUPPORTED_SOURCES))
def test_future_source_names_do_not_become_trusted_current_ability(source: str) -> None:
    with pytest.raises(ValueError):
        normalize_user_confirmed_current_ability(_ability(source=source))


@pytest.mark.parametrize("field_name", sorted(USER_CONFIRMED_CURRENT_ABILITY_FORBIDDEN_FIELDS))
def test_forbidden_current_ability_fields_are_rejected_recursively(field_name: str) -> None:
    direct = _ability(**{field_name: True})
    nested = _ability(metadata={"nested": {field_name: True}})

    with pytest.raises(ValueError, match=field_name):
        normalize_user_confirmed_current_ability(direct)
    with pytest.raises(ValueError, match=field_name):
        normalize_user_confirmed_current_ability(nested)


@pytest.mark.parametrize(
    "source",
    [
        "species_ability_list",
        "hidden_ability_metadata",
        "common_competitive_set",
        "opponent_species_default_ability",
        "move_interaction_inference",
        "damage_reverse_inference",
        "speed_reverse_inference",
        "item_interaction_inference",
        "llm_guess",
    ],
)
def test_possible_species_and_inference_sources_cannot_claim_current_ability(source: str) -> None:
    with pytest.raises(ValueError):
        normalize_user_confirmed_current_ability(_ability(source=source, ability="levitate"))


def test_suppression_replacement_activation_and_resolved_state_are_not_current_identity() -> None:
    for field_name in (
        "ability_activated_this_turn",
        "ability_suppressed",
        "ability_replaced",
        "ability_copied",
        "resolved_ability_effect",
        "post_turn_ability_state",
        "immunity_resolved",
    ):
        with pytest.raises(ValueError, match=field_name):
            normalize_user_confirmed_current_ability(_ability(**{field_name: True}))
