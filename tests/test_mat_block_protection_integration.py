from advisor.canonical_mat_block_protection import canonical_mat_block_protection_metadata
from llm.advisor_runtime_d0_mat_block_direct_damage_applicability_authority import (
    freeze_runtime_d0_mat_block_incoming_bypass_authority,
    freeze_runtime_d0_mat_block_direct_damage_applicability_authority,
)


def _eligibility(value="eligible"):
    return {"status":"resolved","schema_version":"runtime-d0-mat-block-active-entry-eligibility-authority-v1","session_id":"s","source_runtime_fingerprint":"r","source_branch_fingerprint":"b","decision_owner":{"session_id":"s","side":"self","slot_index":0,"pokemon_id":"attacker"},"mat_block_user":{"session_id":"s","side":"opponent","slot_index":1,"pokemon_id":"guard"},"mat_block_action_id":"guard-action","mat_block_move_id":"mat-block","active_entry_token":"entry-1","eligibility":value}


def _bypass(bypassed=False):
    return {"status":"resolved","schema_version":"runtime-d0-mat-block-incoming-bypass-authority-v1","session_id":"s","source_runtime_fingerprint":"r","source_branch_fingerprint":"b","decision_owner":{"session_id":"s","side":"self","slot_index":0,"pokemon_id":"attacker"},"incoming_actor":{"session_id":"s","side":"self","slot_index":0,"pokemon_id":"attacker"},"incoming_action_id":"attack-action","incoming_move_id":"tackle","bypassed":bypassed}


def _request(category="physical", eligibility="eligible", bypass=False):
    return freeze_runtime_d0_mat_block_direct_damage_applicability_authority(
        eligibility_authority=_eligibility(eligibility),
        bypass_authority=_bypass(bypass),
        incoming_action={"action_id":"attack-action","move_id":"tackle","category":category},
        protected_recipients=({"session_id":"s","side":"opponent","slot_index":1,"pokemon_id":"guard"},),
    )


def test_canonical_mat_block_metadata_is_strict():
    assert canonical_mat_block_protection_metadata("mat-block")["supported_incoming_categories"] == ["physical", "special"]
    assert canonical_mat_block_protection_metadata("protect") is None


def test_mat_block_applies_to_physical_and_special_direct_damage():
    assert _request("physical")["outcome"] == "applies"
    assert _request("special")["outcome"] == "applies"


def test_mat_block_exact_no_effect_cases_are_not_applicable():
    assert _request(eligibility="ineligible")["outcome"] == "not_applicable"
    assert _request(bypass=True)["outcome"] == "not_applicable"
    assert _request("status")["outcome"] == "not_applicable"


def test_mat_block_requires_a_bound_frozen_bypass_fact_without_success_synthesis():
    result = freeze_runtime_d0_mat_block_direct_damage_applicability_authority(
        eligibility_authority=_eligibility(), bypass_authority={"status": "resolved", "bypassed": False},
        incoming_action={"action_id": "attack-action", "move_id": "tackle", "category": "physical"},
        protected_recipients=({"session_id": "s", "side": "opponent", "slot_index": 1, "pokemon_id": "guard"},),
    )
    assert result["status"] == "rejected"
    assert "protection_success_authority" not in _request()


def test_ineligible_mat_block_needs_no_bypass_fact_and_unknown_bypass_fails_closed_when_eligible():
    ineligible = freeze_runtime_d0_mat_block_direct_damage_applicability_authority(
        eligibility_authority=_eligibility("ineligible"), bypass_authority=None,
        incoming_action={"action_id": "attack-action", "move_id": "tackle", "category": "physical"},
        protected_recipients=({"session_id": "s", "side": "opponent", "slot_index": 1, "pokemon_id": "guard"},),
    )
    assert ineligible["outcome"] == "not_applicable"
    unknown = _bypass()
    unknown["status"] = "incomplete"
    assert freeze_runtime_d0_mat_block_direct_damage_applicability_authority(
        eligibility_authority=_eligibility(), bypass_authority=unknown,
        incoming_action={"action_id": "attack-action", "move_id": "tackle", "category": "physical"},
        protected_recipients=({"session_id": "s", "side": "opponent", "slot_index": 1, "pokemon_id": "guard"},),
    )["status"] == "incomplete"


def test_frozen_bypass_authority_requires_explicit_canonical_metadata():
    d0 = {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "r", "strategy_preview_fingerprint": "b", "decision_owner": {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}, "active_owners": {"self": {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}}}
    result = freeze_runtime_d0_mat_block_incoming_bypass_authority(
        strategy_d0=d0, incoming_actor=d0["decision_owner"], incoming_action={"action_id": "attack-action", "identity": "tackle"},
        frozen_move_metadata={"move_id": "tackle"},
    )
    assert result["status"] == "incomplete"


def test_foreign_protected_recipient_is_rejected():
    result = freeze_runtime_d0_mat_block_direct_damage_applicability_authority(
        eligibility_authority=_eligibility(), bypass_authority=_bypass(),
        incoming_action={"action_id": "attack-action", "move_id": "tackle", "category": "physical"},
        protected_recipients=({"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "foreign"},),
    )
    assert result["status"] == "rejected"
