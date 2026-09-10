from copy import deepcopy

from llm.advisor_live_secondary_manifest_authority import freeze_live_secondary_manifest_authority
from llm.advisor_ui_detached_strategy_bridge import _secondary_manifest_status


OWNER = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}
D0 = {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "branch", "decision_owner": OWNER, "active_owners": {"self": OWNER}}


def _action(move_id: str) -> dict:
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id}


def _metadata(move_id: str, **values) -> dict:
    return {
        "status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": f"attack:{move_id}", "move_id": move_id,
        "session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch",
        "decision_owner": deepcopy(OWNER), "active_attacker": deepcopy(OWNER),
        "metadata": {"move_id": move_id, "category": "physical", "power": 40, "type": "normal", "accuracy": 100, **values},
    }


def test_live_secondary_manifest_requires_explicit_canonical_neutral_fields() -> None:
    neutral = freeze_live_secondary_manifest_authority(
        strategy_d0=D0, action=_action("tackle"),
        metadata_authority=_metadata("tackle", effect_chance=None, ailment="none", stat_changes=[]),
    )
    assert neutral["status"] == "not_applicable"
    assert _secondary_manifest_status("attack:tackle", {"secondary_manifest_authorities": {"attack:tackle": neutral}}) == "not_applicable"

    unknown = freeze_live_secondary_manifest_authority(
        strategy_d0=D0, action=_action("tackle"), metadata_authority=_metadata("tackle"),
    )
    assert unknown["status"] == "incomplete" and unknown["reason"] == "canonical_secondary_metadata_unknown"


def test_live_secondary_manifest_requires_existing_family_authority_or_fails_closed() -> None:
    metal = freeze_live_secondary_manifest_authority(strategy_d0=D0, action=_action("metal-claw"), metadata_authority=_metadata("metal-claw"))
    shadow = freeze_live_secondary_manifest_authority(strategy_d0=D0, action=_action("shadow-ball"), metadata_authority=_metadata("shadow-ball"))
    thunderbolt = freeze_live_secondary_manifest_authority(strategy_d0=D0, action=_action("thunderbolt"), metadata_authority=_metadata("thunderbolt"))
    for authority, source in ((metal, "probabilistic_self_stage_effect_authorities"), (shadow, "probabilistic_target_stage_effect_authorities"), (thunderbolt, "thunderbolt_paralysis_authorities")):
        assert authority["status"] == "secondary_authority_required"
        assert _secondary_manifest_status(authority["action_id"], {"secondary_manifest_authorities": {authority["action_id"]: authority}, source: {authority["action_id"]: {"status": "resolved"}}}) == "resolved"
        assert _secondary_manifest_status(authority["action_id"], {"secondary_manifest_authorities": {authority["action_id"]: authority}}) == "incomplete"

    missing_iron_head = freeze_live_secondary_manifest_authority(strategy_d0=D0, action=_action("iron-head"), metadata_authority=_metadata("iron-head", effect_chance=30, ailment="flinch", stat_changes=[]))
    assert missing_iron_head["status"] == "incomplete"
    assert missing_iron_head["reason"] == "canonical_secondary_live_authority_unwired"


def test_live_secondary_manifest_rejects_foreign_metadata_binding() -> None:
    foreign = _metadata("tackle", effect_chance=None, ailment="none", stat_changes=[])
    foreign["source_branch_fingerprint"] = "foreign"
    rejected = freeze_live_secondary_manifest_authority(strategy_d0=D0, action=_action("tackle"), metadata_authority=foreign)
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "canonical_secondary_metadata_binding_mismatch"

    malformed = _metadata("tackle", effect_chance=None, ailment="none", stat_changes=[])
    malformed.pop("schema_version")
    rejected = freeze_live_secondary_manifest_authority(strategy_d0=D0, action=_action("tackle"), metadata_authority=malformed)
    assert rejected["status"] == "rejected" and rejected["reason"] == "canonical_secondary_metadata_schema_invalid"
