from copy import deepcopy

from advisor.probabilistic_target_flinch_effect_capabilities import resolve_probabilistic_target_flinch_effect_capability
from llm.advisor_predictive_iron_head_flinch_uncertainty import compose_predictive_iron_head_flinch_uncertainty
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fake_out_active_entry_eligibility_authority import freeze_runtime_d0_fake_out_active_entry_eligibility_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_d0_fake_out_flinch_authority, freeze_runtime_strategy_d0
from tests.test_runtime_d0_iron_head_flinch_authority import _state as base_state, _owner


MOVE = {"move_id": "fake-out", "category": "physical", "power": 40, "target": "selected-pokemon", "effect_chance": 100, "ailment": "flinch"}


def _action(**overrides):
    value = {"decision_point": "d0", "action_id": "self:fake-out", "move_id": "fake-out"}; value.update(overrides); return value


def _state(eligibility="eligible", token="entry-1"):
    state = base_state("fake-out")
    state["fake_out_active_entry_eligibility_context"] = {"schema_version": "fake-out-active-entry-eligibility-context-v1", "session_id": state["session_id"], "decision_point": "d0", "actor": _owner(state), "action_id": "self:fake-out", "move_id": "fake-out", "active_entry_token": token, "eligibility": eligibility, "provenance": {"event_kind": "fake_out_active_entry_eligibility_observed", "trust": "user_confirmed_observation", "source_sequence": 1, "turn_number": 1}}
    state["last_applied_observation_sequence"] = 1
    return state


def _resolved(state):
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    return snapshot, d0


def test_current_stint_eligible_and_later_stint_ineligible_are_distinct():
    state = _state(); snapshot, d0 = _resolved(state)
    resolved = freeze_runtime_d0_fake_out_active_entry_eligibility_authority(strategy_d0=d0, runtime_snapshot=snapshot, fake_out_user=_owner(state), fake_out_action=_action(), target=_owner(state, "opponent"))
    assert resolved["status"] == "resolved" and resolved["eligibility"] == "eligible" and resolved["active_entry_token"] == "entry-1"
    state = _state("ineligible", "entry-2"); snapshot, d0 = _resolved(state)
    assert freeze_runtime_d0_fake_out_active_entry_eligibility_authority(strategy_d0=d0, runtime_snapshot=snapshot, fake_out_user=_owner(state), fake_out_action=_action(), target=_owner(state, "opponent"))["eligibility"] == "ineligible"


def test_missing_stale_reentry_and_wrong_bindings_fail_closed():
    state = _state(); state.pop("fake_out_active_entry_eligibility_context"); snapshot, d0 = _resolved(state)
    assert freeze_runtime_d0_fake_out_active_entry_eligibility_authority(strategy_d0=d0, runtime_snapshot=snapshot, fake_out_user=_owner(state), fake_out_action=_action(), target=_owner(state, "opponent"))["status"] == "incomplete"
    state = _state(); state["last_applied_observation_sequence"] = 2; snapshot, d0 = _resolved(state)
    assert freeze_runtime_d0_fake_out_active_entry_eligibility_authority(strategy_d0=d0, runtime_snapshot=snapshot, fake_out_user=_owner(state), fake_out_action=_action(), target=_owner(state, "opponent"))["status"] == "rejected"
    state = _state(); snapshot, d0 = _resolved(state)
    assert freeze_runtime_d0_fake_out_active_entry_eligibility_authority(strategy_d0=d0, runtime_snapshot=snapshot, fake_out_user=_owner(state), fake_out_action=_action(action_id="other"), target=_owner(state, "opponent"))["status"] == "rejected"


def test_fake_out_flinch_is_deterministic_only_for_surviving_unsubstituted_eligible_target():
    state = _state(); snapshot, d0 = _resolved(state)
    authority = freeze_runtime_d0_fake_out_flinch_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=MOVE, fake_out_action=_action())
    assert authority["status"] == "resolved"
    candidate = {"candidate_id": "attack:fake-out", "action_type": "attack", "session_id": state["session_id"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": _owner(state)}
    interval = {"completeness": "exact_complete", "move_id": "fake-out", "session_id": state["session_id"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": _owner(state), "target_routing": "target", "target_hp_before": 100, "exact_damage_rolls": tuple(10 for _ in range(16))}
    result = compose_predictive_iron_head_flinch_uncertainty(candidate=candidate, interval=interval, runtime_authority=authority)
    assert result["status"] == "resolved" and all(row["secondary_branches"] == ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 0, "denominator": 100}}, {"branch": "effect", "conditional_secondary_probability": {"numerator": 100, "denominator": 100}, "hypothetical_target_flinch": {"schema_version": "detached-hypothetical-immediate-flinch-v1", "state": "flinched", "provenance": "fake_out_successful_damage_roll_secondary_v1"}}) for row in result["damage_roll_leaves"])


def test_ineligible_fake_out_has_no_eligible_only_flinch_and_catalog_keeps_iron_head():
    state = _state("ineligible"); snapshot, d0 = _resolved(state)
    assert freeze_runtime_d0_fake_out_flinch_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata=MOVE, fake_out_action=_action())["status"] == "ineligible"
    iron = {"move_id": "iron-head", "category": "physical", "power": 80, "target": "selected-pokemon", "effect_chance": 30, "ailment": "flinch"}
    source = {"attacker_ability": {"status": "known", "value": "pressure"}, "target_ability": {"status": "known", "value": "pressure"}, "target_item": {"status": "known_absent"}}
    assert resolve_probabilistic_target_flinch_effect_capability(move=iron, source_authority=source)["probability"] == {"numerator": 30, "denominator": 100}
