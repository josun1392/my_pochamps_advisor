import pytest

from llm.advisor_ability_interaction_authority import (
    ability_mechanic_prerequisite,
    build_ability_interaction_authority,
    normalize_ability_interaction_authority,
)


SOURCE = {"side": "opponent", "slot_index": 0, "pokemon_id": "gengar-a"}
TARGET = {"side": "self", "slot_index": 0, "pokemon_id": "pikachu-a"}


def _authority(**overrides):
    return build_ability_interaction_authority(
        session_id="session-1",
        source=SOURCE,
        target=TARGET,
        ability_id="shadow-tag",
        **overrides,
    )


def test_unknown_bootstrap_and_complete_prerequisite_are_detached():
    unknown = _authority()
    assert unknown["applicability"] == "unknown"
    assert unknown["interaction"] == "unknown"
    assert ability_mechanic_prerequisite(unknown) == {"status": "insufficient_context"}

    complete = _authority(applicability="applicable", interaction="affecting")
    complete["source"]["pokemon_id"] = "mutated"
    assert SOURCE["pokemon_id"] == "gengar-a"
    assert ability_mechanic_prerequisite(_authority(applicability="applicable", interaction="affecting")) == {"status": "complete"}


@pytest.mark.parametrize(
    ("applicability", "interaction", "status"),
    [
        ("not_applicable", "affecting", "not_applicable"),
        ("applicable", "not_affecting", "not_applicable"),
        ("unknown", "affecting", "insufficient_context"),
        ("applicable", "unknown", "insufficient_context"),
    ],
)
def test_explicit_negative_and_unknown_states_never_assert_an_effect(applicability, interaction, status):
    assert ability_mechanic_prerequisite(_authority(applicability=applicability, interaction=interaction)) == {"status": status}


@pytest.mark.parametrize(
    "forged",
    [
        {"session_id": "other"},
        {"source": {**SOURCE, "pokemon_id": "forged-source"}},
        {"target": {**TARGET, "pokemon_id": "forged-target"}},
        {"ability_id": "forged-ability"},
        {"interaction": "invalid"},
    ],
)
def test_stale_malformed_and_source_target_mismatches_normalize_to_unknown(forged):
    value = {**_authority(applicability="applicable", interaction="affecting"), **forged}
    normalized = normalize_ability_interaction_authority(
        value, session_id="session-1", source=SOURCE, target=TARGET, ability_id="shadow-tag",
    )
    assert normalized["applicability"] == "unknown"
    assert normalized["interaction"] == "unknown"


def test_duplicate_species_do_not_share_source_target_authority_or_snapshot_data():
    other_target = {"side": "self", "slot_index": 1, "pokemon_id": "pikachu-b"}
    frozen = _authority(applicability="applicable", interaction="affecting")
    normalized = normalize_ability_interaction_authority(
        frozen, session_id="session-1", source=SOURCE, target=other_target, ability_id="shadow-tag",
    )
    assert normalized["target"] == other_target
    assert normalized["applicability"] == "unknown"
    frozen["target"]["pokemon_id"] = "live-update"
    assert normalized["target"]["pokemon_id"] == "pikachu-b"


def test_invalid_identity_and_same_side_relationship_are_rejected():
    with pytest.raises(ValueError, match="invalid_ability_interaction"):
        build_ability_interaction_authority(
            session_id="session-1", source=SOURCE, target={**TARGET, "side": "opponent"}, ability_id="shadow-tag",
        )
    with pytest.raises(ValueError, match="invalid_ability_interaction"):
        build_ability_interaction_authority(
            session_id="session-1", source={**SOURCE, "slot_index": True}, target=TARGET, ability_id="shadow-tag",
        )


def test_malformed_authority_cannot_claim_a_complete_mechanics_prerequisite():
    malformed = {"schema_version": "ability-interaction-authority-v1", "applicability": "applicable", "interaction": "affecting"}
    assert ability_mechanic_prerequisite(malformed) == {"status": "insufficient_context"}
