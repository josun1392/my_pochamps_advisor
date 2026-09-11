from copy import deepcopy

import pytest

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_baneful_bunker_reactive_poison_authority import freeze_runtime_d0_baneful_bunker_reactive_poison_authority
from llm.advisor_runtime_d0_burning_bulwark_reactive_burn_authority import freeze_runtime_d0_burning_bulwark_reactive_burn_authority
from llm.advisor_runtime_d0_reactive_shield_damage_status_applicability_resolution import freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution
from llm.advisor_runtime_d0_spiky_shield_reactive_damage_authority import freeze_runtime_d0_spiky_shield_reactive_damage_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_substitute import update_substitute_state_context
from tests.test_detached_immediate_protection_response_pair import _own_action
from tests.test_detached_opponent_response_profile import _inputs


def _refresh(state, d0):
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    return snapshot, freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["decision_owner"])


def _common(d0, action, family, *, contact_state="contact", bypassed=False):
    shield = d0["active_owners"]["opponent"]
    return {
        "status": "resolved", "schema_version": "runtime-d0-reactive-shield-common-block-context-v1",
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
        "shield_owner": shield, "shield_action_id": f"opponent_attack:{family.replace('_', '-')}", "shield_move_id": family.replace("_", "-"), "shield_family": family,
        "blocked_attacker": d0["active_owners"]["self"], "blocked_action_id": action["action_id"], "blocked_move_id": action["identity"],
        "outcome": "protection_not_applicable" if bypassed else f"protection_applies_{contact_state}",
        "protection_success_authority": {"schema_version": "branch-protection-success-v1", "owner": shield, "previous_successful_protection_count": 0, "provenance": "explicit_branch_nonconsecutive_protection"},
        "bypass_authority": {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "blocked_attacker": d0["active_owners"]["self"], "blocked_action_id": action["action_id"], "blocked_move_id": action["identity"], "bypassed": bypassed},
        "contact_authority": {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "action_id": action["action_id"], "move_id": action["identity"], "attacker": d0["active_owners"]["self"], "target": shield, "contact_state": contact_state},
    }


def _lower(family, d0, snapshot, action, resolved):
    kwargs = {"strategy_d0": d0, "runtime_snapshot": snapshot, "shield_owner": d0["active_owners"]["opponent"], "shield_action_id": resolved["shield_action_id"], "blocked_attacker": d0["active_owners"]["self"], "blocked_action": action, "contact_authority": resolved["contact_authority"], "protection_block_context": resolved["protection_block_context"], "applicability_resolution": resolved["applicability_resolution"]}
    return {"spiky_shield": freeze_runtime_d0_spiky_shield_reactive_damage_authority, "baneful_bunker": freeze_runtime_d0_baneful_bunker_reactive_poison_authority, "burning_bulwark": freeze_runtime_d0_burning_bulwark_reactive_burn_authority}[family](**kwargs)


@pytest.mark.parametrize("family", ("spiky_shield", "baneful_bunker", "burning_bulwark"))
def test_contact_common_context_materializes_lower_compatible_neutral_inputs(family):
    state, snapshot, d0, _unused, _responses, _orders = _inputs(); before = deepcopy(state); action = _own_action(d0, "tackle")
    resolved = freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=_common(d0, action, family))
    assert resolved["status"] == "resolved" and resolved["outcome"] == "applies"
    assert resolved["protection_block_context"]["action_blocked"] is True
    lower = _lower(family, d0, snapshot, action, resolved)
    assert lower["status"] == "resolved" and lower["outcome"] == "applies"
    assert state == before


@pytest.mark.parametrize(("family", "ability"), (("spiky_shield", "magic-guard"), ("baneful_bunker", "immunity"), ("burning_bulwark", "water-veil")))
def test_maintained_prevention_modifier_is_preserved_by_existing_lower_owner(family, ability):
    state, _snapshot, d0, _unused, _responses, _orders = _inputs(); state["self_side"]["pokemon"][0]["current_ability"] = ability
    snapshot, d0 = _refresh(state, d0); action = _own_action(d0, "tackle")
    resolved = freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=_common(d0, action, family))
    assert resolved["status"] == "resolved" and resolved["outcome"] == "prevented"
    assert _lower(family, d0, snapshot, action, resolved)["outcome"] == "not_applicable"


def test_substitute_and_common_outcomes_fail_closed_without_constructing_a_reactive_input():
    state, _snapshot, d0, _unused, _responses, _orders = _inputs(); action = _own_action(d0, "tackle")
    owner = d0["active_owners"]["self"]
    state["substitute_state_context"] = update_substitute_state_context(context=state.get("substitute_state_context"), session_id=state["session_id"], owner=owner, state="known_active", substitute_hp=25, provenance="test")
    snapshot, d0 = _refresh(state, d0)
    assert freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=_common(d0, action, "spiky_shield"))["status"] == "incomplete"
    state["substitute_state_context"] = None; snapshot, d0 = _refresh(state, d0)
    assert freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=_common(d0, action, "spiky_shield"))["status"] == "incomplete"
    assert freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=_common(d0, action, "spiky_shield", contact_state="non_contact"))["outcome"] == "not_applicable"
    assert freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=_common(d0, action, "spiky_shield", bypassed=True))["outcome"] == "not_applicable"


def test_unknown_or_unclassified_modifiers_and_foreign_context_fail_closed():
    state, _snapshot, d0, _unused, _responses, _orders = _inputs(); action = _own_action(d0, "tackle")
    state["self_side"]["pokemon"][0]["current_ability"] = "levitate"; snapshot, d0 = _refresh(state, d0)
    common = _common(d0, action, "baneful_bunker")
    assert freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=common)["status"] == "incomplete"
    foreign = deepcopy(common); foreign["blocked_action_id"] = "foreign"
    assert freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=foreign)["status"] == "rejected"


def test_baneful_adapter_preserves_corrosion_and_independent_poison_prevention():
    state, _snapshot, d0, _unused, _responses, _orders = _inputs(); action = _own_action(d0, "tackle")
    state["opponent_side"]["pokemon"][0]["current_ability"] = "corrosion"
    state["self_side"]["pokemon"][0]["current_type"] = ["poison"]
    snapshot, d0 = _refresh(state, d0)
    resolved = freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=_common(d0, action, "baneful_bunker"))
    assert resolved["outcome"] == "applies" and _lower("baneful_bunker", d0, snapshot, action, resolved)["outcome"] == "applies"

    state["self_side"]["pokemon"][0]["current_ability"] = "immunity"
    snapshot, d0 = _refresh(state, d0)
    resolved = freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=_common(d0, action, "baneful_bunker"))
    assert resolved["outcome"] == "prevented" and _lower("baneful_bunker", d0, snapshot, action, resolved)["outcome"] == "not_applicable"
