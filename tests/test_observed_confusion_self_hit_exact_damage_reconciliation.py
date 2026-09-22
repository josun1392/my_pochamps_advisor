from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest

from llm.advisor_champions_confusion_action_gate import freeze_champions_confusion_action_gate
from llm.advisor_current_state_runtime_admission import admit_current_state_observation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_champions_confusion_self_hit import materialize_confusion_self_hit
from llm.advisor_confusion_self_hit_damage_runtime_admission import admit_observed_confusion_self_hit_damage_result
from llm.advisor_detached_observed_rng_reconciliation import (
    reconcile_observed_confusion_self_hit_damage_rng,
    retain_historical_confusion_action_gate,
    retain_historical_confusion_self_hit,
    validate_historical_confusion_self_hit,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_pending_confusion_action_runtime_admission import admit_pending_confusion_action_execution
from llm.advisor_production_confusion_integration import admit_current_confusion_state


def _manager_from_inputs(*, duration=None, hp=None, mimikyu=None):
    session="observed-confusion-self-hit-damage"
    self_id="mimikyu" if mimikyu is not None else "self-a"
    state=create_unknown_bootstrap_battle_state(session,self_id,"opponent-a")["state"]
    start_hp=100 if hp is None else hp
    for side in ("self","opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=start_hp if side=="self" else 100,max_hp=100,fainted=False)
    if mimikyu is not None:
        raw=state["self_side"]["pokemon"][0]
        raw["species_id"]="mimikyu"; raw["disguise_state"]=mimikyu
    manager=BattleObservationRuntimeSessionManager.create(session,state)["manager"]
    assert manager is not None
    established=admit_current_confusion_state(
        runtime_session_manager=manager,captured_session_id=session,side="self",
        state="confused",turn_number=1,newly_established=True)
    assert established["status"]=="resolved",established
    for side in ("self","opponent"):
        result=admit_current_state_observation(
            runtime_session_manager=manager,captured_session_id=session,
            event_kind="current_ability_observed",payload={"ability":"pressure"},
            side=side,turn_number=1)
        assert result["status"]=="resolved",result
    for event_kind,payload in (
        ("current_level_observed",{"level":50}),
        ("current_final_combat_stat_observed",{"stat":"attack","value":120}),
        ("current_final_combat_stat_observed",{"stat":"defense","value":100}),
        ("stat_stage_observed",{"stat":"attack","stage":0}),
        ("stat_stage_observed",{"stat":"defense","stage":0}),
    ):
        result=admit_current_state_observation(
            runtime_session_manager=manager,captured_session_id=session,
            event_kind=event_kind,payload=payload,side="self",turn_number=1)
        assert result["status"]=="resolved",result
    owner={"session_id":session,"side":"self","slot_index":0,"pokemon_id":self_id}
    return manager,owner


def _primary(manager, owner, *, action_id="attack:tackle", turn=2):
    return admit_pending_confusion_action_execution(
        runtime_session_manager=manager,
        captured_session_id=owner["session_id"],
        side=owner["side"],slot_index=owner["slot_index"],pokemon_id=owner["pokemon_id"],
        turn_number=turn,decision_point=f"decision:{turn}:self",
        action_id=action_id,move_id="tackle",outcome_class="confusion_self_hit")


def _mass(result):
    value=result["compatible_original_probability_mass"]
    return Fraction(value["numerator"],value["denominator"])


def test_canonical_roll_probabilities_are_single_source_and_mass_one():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner)
    assert primary["status"]=="resolved", primary
    retained=primary["retained_self_hit_prediction"]
    assert retained["status"]=="resolved", retained
    checked=validate_historical_confusion_self_hit(retained)
    assert checked["status"]=="resolved"
    rolls=checked["canonical_damage_rolls"]
    assert len(rolls)==16
    assert all(row["probability"]=={"numerator":1,"denominator":16} for row in rolls)
    assert sum((Fraction(row["probability"]["numerator"],row["probability"]["denominator"]) for row in rolls),Fraction())==1


def test_retention_is_pre_hp_immutable_and_bound_only_to_self_hit_branches():
    manager,owner=_manager_from_inputs()
    primary=_primary(manager,owner)
    retained=deepcopy(primary["retained_self_hit_prediction"])
    assert retained["status"]=="resolved"
    assert retained["source_confusion_self_hit_branch_ids"]
    assert all(":confusion:" in value for value in retained["source_confusion_self_hit_branch_ids"])
    assert all(hit["branch"]["kind"]=="confusion_self_hit" for hit in retained["predictive_self_hits"])
    before=deepcopy(retained)
    manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"]
    assert retained==before


def test_selected_action_and_snap_out_do_not_create_self_hit_retention():
    manager,owner=_manager_from_inputs(duration=3)
    selected=admit_pending_confusion_action_execution(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        side="self",slot_index=0,pokemon_id=owner["pokemon_id"],turn_number=2,
        decision_point="decision:2:self",action_id="attack:tackle:a",move_id="tackle",
        outcome_class="confusion_selected_action_executes")
    assert selected["status"]=="resolved" and selected["retained_self_hit_prediction"] is None


def test_no_damage_observation_preserves_all_roll_mass():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner)
    rec=reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=primary["retained_self_hit_prediction"],
        primary_confusion_observation=primary["observation"])
    assert rec["status"]=="incomplete"
    assert rec["reason"]=="insufficient_observation"
    assert _mass(rec)==1
    assert len(rec["compatible_roll_indices"])==16


def test_exact_damage_filters_rolls_and_preserves_duplicate_integer_damage_ambiguity():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner)
    retained=primary["retained_self_hit_prediction"]
    rolls=retained["canonical_damage_rolls"]
    groups={}
    for row in rolls:
        key=(row["hp_before"],row["hp_after"],row["self_fainted"],row["disguise"]["status"])
        groups.setdefault(key,[]).append(row)
    key,rows=next((key,rows) for key,rows in groups.items() if len(rows)>1)
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=key[1],
        disguise_outcome="intact_to_broken" if key[3]=="broken" else key[3])
    assert result["status"]=="resolved",result
    rec=result["reconciliation"]
    assert rec["match_outcome"]=="multiple_compatible_branches"
    assert set(rec["compatible_roll_indices"])=={row["roll_index"] for row in rows}
    assert _mass(rec)==sum((Fraction(row["probability"]["numerator"],row["probability"]["denominator"]) for row in rows),Fraction())
    assert rec["probability_layer"]=="conditional_on_confusion_self_hit"
    assert rec["probability_normalization"]=="none_preserve_original_mass"


def test_low_hp_clamp_preserves_every_compatible_roll_and_self_ko():
    manager,owner=_manager_from_inputs(duration=3,hp=1)
    primary=_primary(manager,owner,action_id="attack:tackle:low")
    retained=primary["retained_self_hit_prediction"]
    assert all(row["hp_after"]==0 for row in retained["canonical_damage_rolls"])
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=0,disguise_outcome="not_applicable")
    assert result["status"]=="resolved",result
    rec=result["reconciliation"]
    assert rec["match_outcome"]=="multiple_compatible_branches"
    assert len(rec["compatible_roll_indices"])==16
    assert _mass(rec)==1
    assert result["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"]==0
    assert result["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["fainted"] is True


def test_non_mimikyu_disguise_requires_not_applicable():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:plain")
    retained=primary["retained_self_hit_prediction"]
    hp_after=retained["canonical_damage_rolls"][0]["hp_after"]
    rejected=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=hp_after,disguise_outcome="already_broken")
    assert rejected["status"]=="rejected"
    assert rejected["reason"]=="confusion_self_hit_damage_disguise_mismatch"


def test_intact_mimikyu_requires_explicit_break_and_zero_damage_alone_does_not_infer():
    manager,owner=_manager_from_inputs(duration=3,hp=10,mimikyu="intact")
    primary=_primary(manager,owner,action_id="attack:tackle:mimikyu")
    retained=primary["retained_self_hit_prediction"]
    assert all(row["hp_after"]==10 for row in retained["canonical_damage_rolls"])
    rejected=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=10,disguise_outcome="not_applicable")
    assert rejected["status"]=="rejected"
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=10,disguise_outcome="intact_to_broken")
    assert result["status"]=="resolved",result
    assert result["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"]==10
    assert result["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["disguise_state"]=="broken"


def test_already_broken_mimikyu_requires_already_broken():
    manager,owner=_manager_from_inputs(duration=3,mimikyu="broken")
    primary=_primary(manager,owner,action_id="attack:tackle:broken")
    retained=primary["retained_self_hit_prediction"]
    row=retained["canonical_damage_rolls"][0]
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="already_broken")
    assert result["status"]=="resolved",result


def test_tampered_primary_identity_and_wrong_source_reference_reject():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:id")
    retained=primary["retained_self_hit_prediction"]
    row=retained["canonical_damage_rolls"][0]
    # Build a valid receipt through lifecycle boundary by admitting once, then tamper detached copies.
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    assert result["status"]=="resolved"
    damage=deepcopy(result["observation"]); source=deepcopy(primary["observation"])
    damage["payload"]["source_confusion_observation_id"]="foreign"
    checked=reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=retained,primary_confusion_observation=source,damage_observation=damage)
    assert checked["status"]=="rejected"
    damage=deepcopy(result["observation"]); source["payload"]["action_id"]="foreign"
    checked=reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=retained,primary_confusion_observation=source,damage_observation=damage)
    assert checked["status"]=="rejected"


def test_ordering_and_actor_session_turn_origin_fail_closed():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:bind")
    retained=primary["retained_self_hit_prediction"]
    row=retained["canonical_damage_rolls"][0]
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    damage=deepcopy(result["observation"]); source=deepcopy(primary["observation"])
    damage["observation_sequence"]=source["observation_sequence"]
    assert reconcile_observed_confusion_self_hit_damage_rng(retained_prediction=retained,primary_confusion_observation=source,damage_observation=damage)["status"]=="rejected"
    for field,value in [("session_id","foreign"),("turn_number",99),("side","opponent")]:
        damage=deepcopy(result["observation"]); damage[field]=value
        assert reconcile_observed_confusion_self_hit_damage_rng(retained_prediction=retained,primary_confusion_observation=source,damage_observation=damage)["status"]=="rejected"
    damage=deepcopy(result["observation"]); damage["payload"]["confusion_origin_id"]="foreign"
    assert reconcile_observed_confusion_self_hit_damage_rng(retained_prediction=retained,primary_confusion_observation=source,damage_observation=damage)["status"]=="rejected"


def test_duplicate_same_damage_is_idempotent_and_conflicting_damage_rejects():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:dup")
    retained=primary["retained_self_hit_prediction"]
    row=retained["canonical_damage_rolls"][0]
    first=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    assert first["status"]=="resolved"
    second=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    assert second["status"]=="resolved" and second["idempotent"] is True
    conflict=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=max(0,row["hp_after"]-1),disguise_outcome="not_applicable")
    assert conflict["status"]=="rejected"


def test_generic_hp_or_primary_alone_never_becomes_roll_evidence():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:none")
    retained=primary["retained_self_hit_prediction"]
    generic={"event_kind":"exact_hp_transition_observed","payload":{"hp_before":100,"hp_after":90}}
    rec=reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=retained,primary_confusion_observation=primary["observation"],damage_observation=generic)
    assert rec["status"]=="rejected"
    rec=reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=retained,primary_confusion_observation=primary["observation"])
    assert rec["status"]=="incomplete" and _mass(rec)==1


def test_detached_reconciliation_does_not_mutate_inputs():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:immutable")
    retained=deepcopy(primary["retained_self_hit_prediction"])
    row=retained["canonical_damage_rolls"][0]
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    damage=deepcopy(result["observation"]); source=deepcopy(primary["observation"])
    baseline=deepcopy((retained,source,damage))
    reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=retained,primary_confusion_observation=source,damage_observation=damage)
    assert (retained,source,damage)==baseline


def test_self_fainted_mismatch_filters_to_incompatible_observation():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:faint-mismatch")
    retained=primary["retained_self_hit_prediction"]
    row=retained["canonical_damage_rolls"][0]
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    damage=deepcopy(result["observation"])
    damage["payload"]["self_fainted"]=not damage["payload"]["self_fainted"]
    rec=reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=retained,primary_confusion_observation=primary["observation"],damage_observation=damage)
    assert rec["status"]=="resolved"
    assert rec["match_outcome"]=="incompatible_observation"
    assert _mass(rec)==0


def test_all_primary_identity_axes_fail_closed_when_tampered():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:axes")
    retained=primary["retained_self_hit_prediction"]
    row=retained["canonical_damage_rolls"][0]
    result=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    original_primary=deepcopy(primary["observation"])
    original_damage=deepcopy(result["observation"])
    for field,value in (
        ("decision_point","foreign-decision"),
        ("action_id","foreign-action"),
        ("move_id","thunderbolt"),
        ("confusion_origin_id","foreign-origin"),
    ):
        source=deepcopy(original_primary)
        source["payload"][field]=value
        checked=reconcile_observed_confusion_self_hit_damage_rng(
            retained_prediction=retained,primary_confusion_observation=source,damage_observation=deepcopy(original_damage))
        assert checked["status"]=="rejected", (field,checked)
    source=deepcopy(original_primary)
    source["payload"]["outcome_class"]="confusion_selected_action_executes"
    checked=reconcile_observed_confusion_self_hit_damage_rng(
        retained_prediction=retained,primary_confusion_observation=source,damage_observation=deepcopy(original_damage))
    assert checked["status"]=="rejected"
    assert checked["reason"]=="confusion_self_hit_primary_outcome_mismatch"


def test_historical_retention_outer_identity_tamper_rejects():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:retained-tamper")
    retained=deepcopy(primary["retained_self_hit_prediction"])
    retained["action_id"]="foreign-action"
    checked=validate_historical_confusion_self_hit(retained)
    assert checked["status"]=="rejected"
    assert checked["reason"]=="historical_confusion_self_hit_identity_mismatch"


def test_stale_turn_and_confusion_episode_retire_damage_admission():
    manager,owner=_manager_from_inputs(duration=3)
    primary=_primary(manager,owner,action_id="attack:tackle:stale")
    retained=primary["retained_self_hit_prediction"]
    row=retained["canonical_damage_rolls"][0]
    stale_turn=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=3,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    assert stale_turn["status"]=="rejected"
    assert stale_turn["reason"]=="confusion_self_hit_damage_stale_turn"
    cleared=admit_current_confusion_state(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        side="self",state="none",turn_number=3,newly_established=False)
    assert cleared["status"]=="resolved"
    stale_episode=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    assert stale_episode["status"]=="rejected"
    assert stale_episode["reason"]=="confusion_self_hit_damage_confusion_episode_stale"


def test_different_action_context_retires_old_self_hit_retention():
    manager,owner=_manager_from_inputs(duration=3)
    first=_primary(manager,owner,action_id="attack:tackle:old",turn=2)
    retained=first["retained_self_hit_prediction"]
    second=_primary(manager,owner,action_id="attack:tackle:new",turn=3)
    assert second["status"]=="resolved"
    row=retained["canonical_damage_rolls"][0]
    stale=admit_observed_confusion_self_hit_damage_result(
        runtime_session_manager=manager,captured_session_id=owner["session_id"],
        retained_prediction=retained,turn_number=2,hp_after=row["hp_after"],disguise_outcome="not_applicable")
    assert stale["status"]=="rejected"
    assert stale["reason"]=="confusion_self_hit_damage_action_context_stale"


def test_pair_consumes_canonical_roll_probability_without_local_one_sixteenth_owner():
    source=Path("llm/advisor_champions_status_confusion_gated_pair.py").read_text(encoding="utf-8")
    assert 'fraction(roll["probability"])' in source
    assert "Fraction(1,16)" not in source
    assert "Fraction(1, 16)" not in source


def test_ui_damage_confirmation_exposes_only_observed_hp_and_disguise_inputs():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    start=source.index("def _open_confusion_self_hit_damage_confirmation")
    end=source.index("def _resolve_pending_confusion_actor",start)
    method=source[start:end]
    assert "QInputDialog.getInt" in method
    assert "Observed Disguise result" in method
    assert "QInputDialog.getText" not in method
    assert "retained_prediction=retained" in method
    assert "turn_number=turn_number" in method


def test_ui_self_hit_retention_retires_where_confusion_gate_retention_retires():
    source=Path("ui/main_window.py").read_text(encoding="utf-8")
    gate_clear=source.count("self._historical_confusion_action_gates = {}")
    self_hit_clear=source.count("self._historical_confusion_self_hit_predictions = {}")
    assert gate_clear>=6
    assert self_hit_clear>=gate_clear
