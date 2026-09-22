from copy import deepcopy
from fractions import Fraction

import pytest

from llm.advisor_current_state_runtime_admission import admit_current_state_observation
from llm.advisor_detached_observed_rng_reconciliation import (
    reconcile_observed_confusion_action_gate_rng,
    validate_historical_confusion_action_gate,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_pending_confusion_action_runtime_admission import (
    admit_observed_confusion_action_result,
    admit_pending_confusion_action_execution,
    resolve_pending_confusion_action_identity,
)
from llm.advisor_production_confusion_integration import admit_current_confusion_state


SESSION="observed-confusion-c5"


def _manager():
    state=create_unknown_bootstrap_battle_state(SESSION,"self-a","opponent-a")["state"]
    for side in ("self","opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100,max_hp=100,fainted=False)
    manager=BattleObservationRuntimeSessionManager.create(SESSION,state)["manager"]
    established=admit_current_confusion_state(
        runtime_session_manager=manager,captured_session_id=SESSION,side="self",
        state="confused",turn_number=1,newly_established=True)
    assert established["status"]=="resolved",established
    for side in ("self","opponent"):
        result=admit_current_state_observation(
            runtime_session_manager=manager,captured_session_id=SESSION,
            event_kind="current_ability_observed",payload={"ability":"pressure"},
            side=side,turn_number=1)
        assert result["status"]=="resolved",result
    return manager


def _submit(manager,outcome,*,turn=2,action="attack:tackle",move="tackle",decision="decision:2:self",side="self"):
    state=manager.read_state()["state"]
    slot=state[f"{side}_side"]["active_slot_index"]
    pokemon=state[f"{side}_side"]["pokemon"][slot]
    return admit_pending_confusion_action_execution(
        runtime_session_manager=manager,captured_session_id=manager.session_id,side=side,
        slot_index=slot,pokemon_id=pokemon["pokemon_id"],turn_number=turn,
        decision_point=decision,action_id=action,move_id=move,outcome_class=outcome)


def _mass(result):
    value=result["compatible_original_probability_mass"]
    return Fraction(value["numerator"],value["denominator"])


def test_self_hit_retains_pre_observation_gate_and_preserves_duration_ambiguity():
    manager=_manager()
    before=manager.capture_runtime_state_snapshot(SESSION)
    result=_submit(manager,"confusion_self_hit")
    assert result["status"]=="resolved",result
    retained=result["retained_prediction"]
    reconciliation=result["rng_reconciliation"]
    origin=before["state"]["self_side"]["pokemon"][0]["champions_confusion_progression"]["origin_id"]
    assert retained["confusion_origin_id"]==origin
    assert result["observation"]["payload"]["confusion_origin_id"]==origin
    assert result["derived_observations"][0]["payload"]["confusion_origin_id"]==origin
    assert retained["source_runtime_fingerprint"]==before["state_fingerprint"]
    assert retained["predictive_gate"]["source_runtime_fingerprint"]==before["state_fingerprint"]
    assert result["runtime_snapshot"]["state_fingerprint"]!=before["state_fingerprint"]
    assert reconciliation["source_prediction_kind"]=="confusion_action_gate"
    assert reconciliation["match_outcome"]=="multiple_compatible_branches"
    assert _mass(reconciliation)==Fraction(1,3)
    assert "duration" in reconciliation["unresolved_hidden_dimensions"]
    assert "duration_identity" in reconciliation["unresolved_hidden_dimensions"]
    assert all("confusion_self_hit" in branch_id for branch_id in reconciliation["compatible_branch_ids"])
    assert "source_action_id" not in retained and "source_action_id" not in reconciliation


def test_selected_action_execution_filters_only_selected_execution_branches():
    manager=_manager()
    result=_submit(manager,"confusion_selected_action_executes")
    reconciliation=result["rng_reconciliation"]
    assert result["status"]=="resolved"
    assert reconciliation["match_outcome"]=="multiple_compatible_branches"
    assert _mass(reconciliation)==Fraction(2,3)
    assert all("confusion_selected_action_executes" in branch_id for branch_id in reconciliation["compatible_branch_ids"])
    pokemon=result["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]
    assert pokemon["current_confusion"]=="confused"
    assert pokemon["champions_confusion_progression"]["prior_opportunities"]==1


def test_snap_out_filters_only_snap_branch_after_prior_opportunity():
    manager=_manager()
    first=_submit(manager,"confusion_selected_action_executes",turn=2,action="attack:tackle:1",decision="decision:2:self")
    assert first["status"]=="resolved",first
    result=_submit(manager,"confusion_snaps_out_and_executes",turn=3,action="attack:tackle:2",decision="decision:3:self")
    assert result["status"]=="resolved",result
    rec=result["rng_reconciliation"]
    assert rec["match_outcome"]=="uniquely_matched"
    assert _mass(rec)==Fraction(1,4)
    source_origin=result["retained_prediction"]["confusion_origin_id"]
    assert result["observation"]["payload"]["confusion_origin_id"]==source_origin
    assert result["derived_observations"][0]["payload"]["confusion_origin_id"]==source_origin
    pokemon=result["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]
    assert pokemon["current_confusion"]=="none"
    assert pokemon["champions_confusion_progression"] is None


def test_no_exact_pending_observation_preserves_full_mass_and_state_snapshots_are_not_evidence():
    manager=_manager()
    # Produce a retained source through an admitted action, then reuse its immutable historical prediction.
    result=_submit(manager,"confusion_self_hit")
    retained=result["retained_prediction"]
    absent=reconcile_observed_confusion_action_gate_rng(retained_prediction=retained)
    current_only=reconcile_observed_confusion_action_gate_rng(
        retained_prediction=retained,
        pending_confusion_action_observation={"event_kind":"current_confusion_state_observed"})
    progression_only=reconcile_observed_confusion_action_gate_rng(
        retained_prediction=retained,
        pending_confusion_action_observation={"event_kind":"champions_confusion_progression_observed"})
    for row in (absent,current_only,progression_only):
        assert row["status"]=="incomplete"
        assert row["reason"]=="insufficient_observation"
        assert _mass(row)==1
        assert row["source_observations"]==()


@pytest.mark.parametrize("field,value,reason",[
    ("session_id","foreign","pending_confusion_action_observation_provenance_mismatch"),
    ("turn_number",99,"pending_confusion_action_observation_provenance_mismatch"),
    ("side","opponent","pending_confusion_action_actor_mismatch"),
])
def test_foreign_observation_envelope_rejects(field,value,reason):
    manager=_manager(); result=_submit(manager,"confusion_self_hit")
    retained=result["retained_prediction"]; obs=deepcopy(result["observation"]); obs[field]=value
    checked=reconcile_observed_confusion_action_gate_rng(
        retained_prediction=retained,pending_confusion_action_observation=obs)
    assert checked["status"]=="rejected" and checked["reason"]==reason


@pytest.mark.parametrize("field,value,reason",[
    ("decision_point","foreign","pending_confusion_action_decision_point_mismatch"),
    ("action_id","foreign","pending_confusion_action_action_id_mismatch"),
    ("move_id","thunderbolt","pending_confusion_action_move_mismatch"),
    ("confusion_origin_id","foreign-origin","pending_confusion_action_origin_mismatch"),
])
def test_foreign_observation_payload_identity_rejects(field,value,reason):
    manager=_manager(); result=_submit(manager,"confusion_self_hit")
    retained=result["retained_prediction"]; obs=deepcopy(result["observation"]); obs["payload"][field]=value
    checked=reconcile_observed_confusion_action_gate_rng(
        retained_prediction=retained,pending_confusion_action_observation=obs)
    assert checked["status"]=="rejected" and checked["reason"]==reason


def test_foreign_old_confusion_episode_origin_rejects_even_when_action_identity_matches():
    manager=_manager(); result=_submit(manager,"confusion_self_hit")
    retained=result["retained_prediction"]
    obs=deepcopy(result["observation"])
    obs["payload"]["confusion_origin_id"]="old-confusion-origin"
    assert obs["payload"]["decision_point"]==retained["decision_point"]
    assert obs["payload"]["action_id"]==retained["action_id"]
    assert obs["payload"]["move_id"]==retained["move_id"]
    checked=reconcile_observed_confusion_action_gate_rng(
        retained_prediction=retained,pending_confusion_action_observation=obs)
    assert checked["status"]=="rejected"
    assert checked["reason"]=="pending_confusion_action_origin_mismatch"


def test_tampered_historical_prediction_fingerprint_and_gate_reject():
    manager=_manager(); result=_submit(manager,"confusion_self_hit")
    retained=deepcopy(result["retained_prediction"])
    retained["prediction_fingerprint"]="0"*64
    assert validate_historical_confusion_action_gate(retained)["status"]=="rejected"
    retained=deepcopy(result["retained_prediction"])
    retained["predictive_gate"]["branches"][0]["probability"]={"numerator":9,"denominator":10}
    assert validate_historical_confusion_action_gate(retained)["status"]=="rejected"


def test_reconciliation_uses_only_primary_rng_observation_not_derived_lifecycle():
    manager=_manager(); result=_submit(manager,"confusion_self_hit")
    rec=result["rng_reconciliation"]
    assert len(rec["source_observations"])==1
    assert rec["source_observations"][0]["event_kind"]=="pending_confusion_action_execution_observed"
    assert [row["event_kind"] for row in result["derived_observations"]]==["champions_confusion_progression_derived"]
    assert result["derived_observations"][0]["payload"]["confusion_origin_id"]==result["retained_prediction"]["confusion_origin_id"]
    assert result["observation"]["payload"]["outcome_class"]=="confusion_self_hit"
    assert "executed_move_observed" not in [row["event_kind"] for row in result["derived_observations"]]


def test_canonical_identity_is_derived_without_user_entered_internal_fields():
    manager=_manager()
    snapshot=manager.capture_runtime_state_snapshot(SESSION)
    first=resolve_pending_confusion_action_identity(
        runtime_snapshot=snapshot,side="self",move_id="tackle",turn_number=2)
    second=resolve_pending_confusion_action_identity(
        runtime_snapshot=snapshot,side="self",move_id="tackle",turn_number=2)
    assert first==second
    assert first["status"]=="resolved"
    result=admit_observed_confusion_action_result(
        runtime_session_manager=manager,captured_session_id=SESSION,side="self",
        turn_number=2,move_id="tackle",outcome_class="confusion_self_hit")
    assert result["status"]=="resolved",result
    payload=result["observation"]["payload"]
    assert payload["action_id"]==first["action_id"]
    assert payload["decision_point"]==first["decision_point"]


def test_identity_reuses_exact_existing_executed_action_when_available():
    manager=_manager()
    snapshot=manager.capture_runtime_state_snapshot(SESSION)
    state=snapshot["state"]
    owner=state["self_side"]["pokemon"][0]
    observed={
        "status":"ready",
        "session_id":SESSION,
        "ordered_observations":[{
            "event_kind":"executed_move_observed",
            "session_id":SESSION,
            "turn_number":2,
            "side":"self",
            "slot_index":0,
            "pokemon_id":owner["pokemon_id"],
            "source":"ui_executed_move_confirmation",
            "trust":"user_confirmed_observation",
            "observation_id":"executed:1",
            "observation_sequence":9,
            "payload":{"move_id":"tackle","source_action_id":"exact-action:2:self"},
        }],
    }
    resolved=resolve_pending_confusion_action_identity(
        runtime_snapshot=snapshot,side="self",move_id="tackle",turn_number=2,
        observation_snapshot=observed)
    assert resolved["status"]=="resolved"
    assert resolved["reason"]=="existing_execution_reuse"
    assert resolved["action_id"]=="exact-action:2:self"


def test_duplicate_same_opportunity_does_not_advance_twice():
    manager=_manager()
    first=_submit(manager,"confusion_self_hit")
    assert first["status"]=="resolved"
    before=deepcopy(manager.read_state())
    second=_submit(manager,"confusion_self_hit")
    assert second["status"]=="resolved"
    assert second["reason"]=="duplicate_pending_confusion_action"
    assert second["runtime_committed"] is False
    assert manager.read_state()==before

    conflict=_submit(manager,"confusion_selected_action_executes")
    assert conflict["status"]=="rejected"
    assert conflict["reason"]=="conflicting_pending_confusion_action_retry"
    assert manager.read_state()==before


def test_ui_source_contract_derives_identity_internally_and_retires_historical_storage():
    source=open("ui/main_window.py",encoding="utf-8").read()
    start=source.index("def _open_confusion_action_result_confirmation")
    end=source.index("def _open_previous_action_confirmation",start)
    block=source[start:end]
    assert "_resolve_pending_confusion_action_identity(" in block
    assert "admit_pending_confusion_action_execution(" in block
    assert "_historical_confusion_action_gates" in block
    assert "QInputDialog.getText(self, \"Confirm Confusion Action Result\", \"Selected move id\")" in block
    assert "action_id" not in block[:block.index("_resolve_pending_confusion_action_identity(")]
    turn_start=source.index("def set_current_turn_number")
    turn_end=source.index("def advance_turn",turn_start)
    assert "self._historical_confusion_action_gates = {}" in source[turn_start:turn_end]
    battle_start=source.index("def _begin_new_battle_session")
    battle_end=source.index("def begin_new_battle",battle_start)
    assert "self._historical_confusion_action_gates = {}" in source[battle_start:battle_end]
    confusion_start=source.index("def _open_confusion_state_confirmation")
    confusion_end=source.index("def _open_paralysis_result_confirmation",confusion_start)
    assert "self._historical_confusion_action_gates = {}" in source[confusion_start:confusion_end]
    switch_start=source.index("def _confirm_pokemon_switch")
    switch_end=source.index("def _confirm_previous_action_history",switch_start)
    assert "self._historical_confusion_action_gates = {}" in source[switch_start:switch_end]


def test_retained_prediction_and_observation_are_immutable_under_reconciliation():
    manager=_manager(); result=_submit(manager,"confusion_self_hit")
    retained=deepcopy(result["retained_prediction"]); obs=deepcopy(result["observation"])
    baseline=deepcopy((retained,obs))
    reconcile_observed_confusion_action_gate_rng(
        retained_prediction=retained,pending_confusion_action_observation=obs)
    assert (retained,obs)==baseline


def test_self_hit_contract_does_not_claim_selected_move_execution_or_damage_roll_reconciliation():
    manager=_manager(); result=_submit(manager,"confusion_self_hit")
    assert result["observation"]["payload"]["outcome_class"]=="confusion_self_hit"
    assert "damage" not in result["observation"]["payload"]
    assert "hp_before" not in result["observation"]["payload"]
    assert "hp_after" not in result["observation"]["payload"]
    assert result["rng_reconciliation"]["matched_observable_facts"]=={"outcome_class":"confusion_self_hit"}

