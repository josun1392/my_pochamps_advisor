from advisor.canonical_mat_block_protection import canonical_mat_block_protection_metadata
from llm.advisor_runtime_d0_mat_block_direct_damage_applicability_authority import (
    freeze_runtime_d0_mat_block_direct_damage_applicability_authority,
)


def _eligibility(value="eligible"):
    return {"status":"resolved","schema_version":"runtime-d0-mat-block-active-entry-eligibility-authority-v1","session_id":"s","source_runtime_fingerprint":"r","source_branch_fingerprint":"b","decision_owner":{"session_id":"s","side":"opponent","slot_index":1,"pokemon_id":"guard"},"mat_block_user":{"session_id":"s","side":"opponent","slot_index":1,"pokemon_id":"guard"},"mat_block_action_id":"guard-action","mat_block_move_id":"mat-block","active_entry_token":"entry-1","eligibility":value}


def _request(category="physical", eligibility="eligible", success=True, bypass=False):
    return freeze_runtime_d0_mat_block_direct_damage_applicability_authority(
        eligibility_authority=_eligibility(eligibility),
        protection_success_authority={"status":"resolved","success":success},
        bypass_authority={"status":"resolved","bypassed":bypass},
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
    assert _request(success=False)["outcome"] == "not_applicable"
    assert _request(bypass=True)["outcome"] == "not_applicable"
    assert _request("status")["outcome"] == "not_applicable"
