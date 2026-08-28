from copy import deepcopy
from llm.advisor_hypothetical_protection_effects import canonical_protection_metadata, prevent_supported_direct_damage, project_protection_direct_transition, project_self_protection

OWNER = {"session_id": "p", "side": "self", "slot_index": 0, "pokemon_id": "pikachu"}

def _branch(): return {"schema_version": "deterministic-transition-preview-v1", "active": {"self": {**OWNER, "current_hp": 50, "max_hp": 100, "fainted": False}, "opponent": {"session_id": "p", "side": "opponent", "slot_index": 0, "pokemon_id": "a", "current_hp": 100, "max_hp": 100, "fainted": False}}, "current_state": {}}
def _action(move="protect"): return {"owner": OWNER, "move": {"move_id": move, "slot_index": 0, "category": "status", "target": "user", "accuracy": None}}
def _success(n=0): return {"schema_version": "branch-protection-success-v1", "owner": OWNER, "previous_successful_protection_count": n, "provenance": "explicit_branch_nonconsecutive_protection"}

def test_checked_in_metadata_not_name_or_broad_category_inference_and_success_is_explicit():
    branch = _branch(); before = deepcopy(branch)
    assert canonical_protection_metadata("protect")["blocks_supported_direct_damage"] is True
    assert canonical_protection_metadata("detect") == {
        "move_id": "detect", "protects_self": True,
        "blocks_supported_direct_damage": True,
        "protection_kind": "ordinary_self_protection",
        "has_additional_material_effects": False,
    }
    assert canonical_protection_metadata("fake-protect") is None
    assert project_self_protection(branch_state=branch, action=_action("fake-protect"), expected_owner=OWNER, success_authority=_success())["status"] == "unsupported"
    assert project_self_protection(branch_state=branch, action=_action(), expected_owner=OWNER, success_authority=_success())["status"] == "resolved"
    assert project_self_protection(branch_state=branch, action=_action(), expected_owner=OWNER, success_authority={})["reason"] == "protection_chain_authority"
    assert project_self_protection(branch_state=branch, action=_action(), expected_owner=OWNER, success_authority=_success(1))["reason"] == "protection_chain_authority"
    assert branch == before


def test_detect_uses_the_same_strict_ordinary_protection_resolver():
    effect = project_self_protection(
        branch_state=_branch(), action=_action("detect"), expected_owner=OWNER,
        success_authority=_success(),
    )
    assert effect["status"] == "resolved"
    assert effect["metadata"]["move_id"] == "detect"
    assert prevent_supported_direct_damage(
        effect=effect, protected_owner=OWNER,
        opponent_action={"move": {"category": "physical", "protection_bypass": False}},
    )["execution_status"] == "prevented"
    assert prevent_supported_direct_damage(
        effect=effect, protected_owner=OWNER,
        opponent_action={"move": {"category": "physical", "protection_bypass": True}},
    )["reason"] == "protection_bypass_authority"
    conflicting = _action("detect")
    conflicting["move"]["target"] = "normal"
    assert project_self_protection(
        branch_state=_branch(), action=conflicting, expected_owner=OWNER,
        success_authority=_success(),
    )["status"] == "unsupported"
    foreign = {**OWNER, "pokemon_id": "foreign"}
    assert project_self_protection(
        branch_state=_branch(), action=_action("detect"), expected_owner=foreign,
        success_authority=_success(),
    )["status"] == "rejected"

def test_protection_prevents_only_explicitly_non_bypassing_direct_damage():
    effect = project_self_protection(branch_state=_branch(), action=_action(), expected_owner=OWNER, success_authority=_success())
    prevented = prevent_supported_direct_damage(effect=effect, protected_owner=OWNER, opponent_action={"move": {"category": "special", "protection_bypass": False}})
    assert prevented["execution_status"] == "prevented"
    assert prevent_supported_direct_damage(effect=effect, protected_owner=OWNER, opponent_action={"move": {"category": "special"}})["reason"] == "protection_bypass_authority"
    branch = _branch(); result = project_protection_direct_transition(branch_state=branch, self_action=_action(), opponent_action={"move": {"category": "special", "protection_bypass": False}}, owner=OWNER, success_authority=_success(), action_order={"status": "acts_first"})
    assert result["status"] == "resolved" and result["next_state"]["active"]["self"]["current_hp"] == 50
