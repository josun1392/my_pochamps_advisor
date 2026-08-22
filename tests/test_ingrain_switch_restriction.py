"""Exact branch-bound voluntary-switch restriction from Ingrain."""
from copy import deepcopy

from llm.advisor_ingrain_switch_restriction import (
    derive_ingrain_manual_switch_block,
    finalize_ingrain_manual_switch_candidates,
)
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_persistent_action_result import materialize_observed_persistent_action_result
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_ingrain
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_ingrain_activation import _effect
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leftovers_end_of_turn import _owner_id, _pre
from tests.test_observed_persistent_action_result import _observed


def _with_switch_authority(state, *, types=("grass",), item=None):
    current = state["current_state"]
    current["current_type_context"] = {
        "current_types": [
            {"side": "self", "state": "known", "types": list(types), "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current", "confidence": "known"},
            {"side": "opponent", "state": "known", "types": ["normal"], "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current", "confidence": "known"},
        ]
    }
    current["direct_mechanics_context"]["attacker"]["item"] = {"status": "known", "value": item} if item is not None else {"status": "known_absent"}


def _permission(owner, status="permitted"):
    return {"schema_version": "switch-permission-context-v1", "session_id": owner["session_id"], "side": "self", "active_slot_index": owner["slot_index"], "active_pokemon_id": owner["pokemon_id"], "status": status, "supportability": "complete", "source": "user_confirmed_current_switch_permission", "trust": "user_confirmed_current", "block_reason": None}


def _candidate(owner):
    return {"candidate_id": "self-switch:test:1:incoming", "action_kind": "switch", "session_id": owner["session_id"], "target_pokemon_id": "incoming", "target_slot_index": 1, "identity_supportability": "complete", "availability_supportability": "complete", "legality_supportability": "complete", "selectable": True, "reason_code": "switch_available"}


def test_exact_active_ingrain_blocks_manual_switch_and_exceptions_remain_authority_bound():
    pre = _pre(self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="known_active"); state = pre["next_state"]
    _with_switch_authority(state)
    owner, fp = _owner_id(state, "self"), fingerprint_transition_preview_state(state)
    blocked = derive_ingrain_manual_switch_block(branch_state=state, source_branch_fingerprint=fp, owner=owner)
    assert blocked["block_state"] == "confirmed_blocked"
    final = finalize_ingrain_manual_switch_candidates(base_candidates=[_candidate(owner)], manual_permission=_permission(owner), branch_state=state, source_branch_fingerprint=fp, owner=owner)
    assert final["status"] == "resolved" and final["switch_candidates"][0]["reason_code"] == "switch_blocked"

    ghost = deepcopy(state); _with_switch_authority(ghost, types=("ghost",)); ghost_result = derive_ingrain_manual_switch_block(branch_state=ghost, source_branch_fingerprint=fingerprint_transition_preview_state(ghost), owner=_owner_id(ghost, "self"))
    assert ghost_result["block_state"] == "exception_applies" and ghost_result["exception"] == "ghost_type"
    ghost_final = finalize_ingrain_manual_switch_candidates(base_candidates=[_candidate(_owner_id(ghost, "self"))], manual_permission=_permission(_owner_id(ghost, "self")), branch_state=ghost, source_branch_fingerprint=fingerprint_transition_preview_state(ghost), owner=_owner_id(ghost, "self"))
    assert ghost_final["switch_candidates"][0]["reason_code"] == "switch_available"
    shell = deepcopy(state); _with_switch_authority(shell, item="shed-shell"); shell_result = derive_ingrain_manual_switch_block(branch_state=shell, source_branch_fingerprint=fingerprint_transition_preview_state(shell), owner=_owner_id(shell, "self"))
    assert shell_result["block_state"] == "exception_applies" and shell_result["exception"] == "shed_shell"


def test_inactive_unknown_and_stale_or_foreign_authority_never_fabricate_a_switch_result():
    inactive = _pre(self_item=None, self_condition="none"); _ingrain(inactive["next_state"], self_state="known_inactive"); _with_switch_authority(inactive["next_state"])
    state, owner = inactive["next_state"], _owner_id(inactive["next_state"], "self")
    assert derive_ingrain_manual_switch_block(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), owner=owner)["block_state"] == "not_established"
    unknown = _pre(self_item=None, self_condition="none"); _ingrain(unknown["next_state"], self_state="unknown"); _with_switch_authority(unknown["next_state"])
    unknown_state = unknown["next_state"]
    assert derive_ingrain_manual_switch_block(branch_state=unknown_state, source_branch_fingerprint=fingerprint_transition_preview_state(unknown_state), owner=_owner_id(unknown_state, "self")) == {"status": "incomplete", "reason": "ingrain_persistent_effect_unknown"}
    assert derive_ingrain_manual_switch_block(branch_state=state, source_branch_fingerprint="stale", owner=owner) == {"status": "rejected", "reason": "stale_or_foreign_ingrain_switch_authority"}
    assert derive_ingrain_manual_switch_block(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), owner={**owner, "pokemon_id": "foreign"}) == {"status": "rejected", "reason": "stale_or_foreign_ingrain_switch_authority"}
    no_types = _pre(self_item=None, self_condition="none"); _ingrain(no_types["next_state"], self_state="known_active"); no_types = no_types["next_state"]
    assert derive_ingrain_manual_switch_block(branch_state=no_types, source_branch_fingerprint=fingerprint_transition_preview_state(no_types), owner=_owner_id(no_types, "self")) == {"status": "incomplete", "reason": "ingrain_switch_current_type_authority"}


def test_application_observation_and_handoff_created_ingrain_all_restrict_current_manual_switch():
    pre = _pre(self_hp=50, self_item=None, self_condition="none"); _ingrain(pre["next_state"], self_state="unknown"); source = pre["next_state"]; _with_switch_authority(source)
    applied = apply_successful_ingrain(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), action_effect=_effect(source))
    active, fp = applied["next_state"], applied["resulting_branch_fingerprint"]
    assert derive_ingrain_manual_switch_block(branch_state=active, source_branch_fingerprint=fp, owner=_owner_id(active, "self"))["block_state"] == "confirmed_blocked"

    observed = _pre(self_hp=50, self_item=None, self_condition="none"); _ingrain(observed["next_state"], self_state="unknown"); observed_source = observed["next_state"]; _with_switch_authority(observed_source)
    action = materialize_observed_persistent_action_result(branch_state=observed_source, source_branch_fingerprint=fingerprint_transition_preview_state(observed_source), observed_result=_observed(observed_source, "ingrain"))
    observed_applied = apply_successful_ingrain(branch_state=observed_source, source_branch_fingerprint=fingerprint_transition_preview_state(observed_source), action_effect=action["successful_action_effect"])
    assert derive_ingrain_manual_switch_block(branch_state=observed_applied["next_state"], source_branch_fingerprint=observed_applied["resulting_branch_fingerprint"], owner=_owner_id(observed_applied["next_state"], "self"))["block_state"] == "confirmed_blocked"

    eot = project_per_owner_end_of_turn(pre_end_of_turn={"status": "resolved", "next_state": active, "boundary": {"phase": "pre_end_of_turn"}}, owner=_owner_id(active, "self"))
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot); turn_two = handoff["next_state"]
    assert derive_ingrain_manual_switch_block(branch_state=turn_two, source_branch_fingerprint=handoff["resulting_branch_fingerprint"], owner=_owner_id(turn_two, "self"))["block_state"] == "confirmed_blocked"
