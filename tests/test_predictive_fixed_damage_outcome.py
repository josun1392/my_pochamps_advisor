from copy import deepcopy

from llm.advisor_candidate_outcome_materialization import materialize_candidates
from llm.advisor_current_action_authority import freeze_current_action_authority
from llm.advisor_current_execution_authority import enrich_discovered_candidates, freeze_current_execution_authority
from llm.advisor_current_state_candidate_discovery import discover_candidates
from llm.advisor_deterministic_candidate_ranking import rank_candidates
from llm.advisor_predictive_attack_authority import build_predictive_fixed_damage_attack_authority
from llm.advisor_predictive_fixed_damage_outcome import enrich_predictive_attack_candidate, materialize_predictive_fixed_damage_outcome
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_executable_switch_transition import _incoming
from tests.test_forced_switch_execution import _owner, _state


def _tracked_substitute(state, *, status="known_inactive", hp=None):
    state["substitute_state_context"] = {"schema_version": "detached-substitute-state-v1", "states": [{"owner": _owner(state, "self"), "state": "known_inactive", "substitute_hp": None}, {"owner": _owner(state, "opponent"), "state": status, "substitute_hp": hp}]}


def _predictive_input(state):
    owner, target = _owner(state, "self"), _owner(state, "opponent")
    return {"schema_version": "current-predictive-fixed-damage-input-v1", "provenance": "trusted_current_predictive_fixed_damage_input_v1", "session_id": owner["session_id"], "source_branch_fingerprint": fingerprint_transition_preview_state(state), "decision_owner": owner, "attacker": owner, "target": target, "move_id": "seismic-toss", "attacker_level_authority": {"status": "known", "value": 50}, "target_type_authority": {"status": "known", "value": ["water"]}}


def _candidate(state):
    owner = _owner(state, "self")
    return {"schema_version": "deterministic-action-candidate-v1", "candidate_id": "attack:seismic-toss", "decision_owner": owner, "source_branch_fingerprint": fingerprint_transition_preview_state(state), "action_type": "attack", "action_authority": None}


def _authority(state):
    return build_predictive_fixed_damage_attack_authority(branch_state=state, decision_owner=_owner(state, "self"), target_owner=_owner(state, "opponent"), move_id="seismic-toss", predictive_input=_predictive_input(state))


def test_predictive_adapter_materializes_survival_ko_immunity_and_is_pure():
    state, _ = _state(); _tracked_substitute(state); candidate, authority = _candidate(state), _authority(state)
    first = materialize_predictive_fixed_damage_outcome(decision_state=state, decision_owner=_owner(state, "self"), candidate=candidate, predictive_authority=authority)
    second = materialize_predictive_fixed_damage_outcome(decision_state=state, decision_owner=_owner(state, "self"), candidate=candidate, predictive_authority=authority)
    assert first == second and first["outcome"]["outcome_state"]["active"]["opponent"]["current_hp"] == 50 and state["active"]["opponent"]["current_hp"] == 100
    ko_state = deepcopy(state); ko_state["active"]["opponent"]["current_hp"] = 40
    ko = materialize_predictive_fixed_damage_outcome(decision_state=ko_state, decision_owner=_owner(ko_state, "self"), candidate=_candidate(ko_state), predictive_authority=_authority(ko_state))
    assert ko["outcome"]["outcome_state"]["active"]["opponent"]["fainted"] is True
    immune_state = deepcopy(state); immune = _authority(immune_state); immune["predicted_result"] = {"damage": 0, "damage_route": "target", "target_hp_before": 100, "target_hp_after": 100, "target_fainted": False}
    assert materialize_predictive_fixed_damage_outcome(decision_state=immune_state, decision_owner=_owner(immune_state, "self"), candidate=_candidate(immune_state), predictive_authority=immune)["outcome"]["outcome_state"]["active"]["opponent"]["current_hp"] == 100


def test_predictive_adapter_routes_to_substitute_and_rejects_incomplete_or_historical_authority():
    state, _ = _state(); _tracked_substitute(state, status="known_active", hp=60); candidate, authority = _candidate(state), _authority(state)
    resolved = materialize_predictive_fixed_damage_outcome(decision_state=state, decision_owner=_owner(state, "self"), candidate=candidate, predictive_authority=authority)
    target = resolved["outcome"]["outcome_state"]["active"]["opponent"]
    assert target["current_hp"] == 100 and resolved["outcome"]["outcome_state"]["substitute_state_context"]["states"][1]["substitute_hp"] == 10
    incomplete = {**authority, "completeness": "exact_incomplete"}
    assert materialize_predictive_fixed_damage_outcome(decision_state=state, decision_owner=_owner(state, "self"), candidate=candidate, predictive_authority=incomplete)["status"] == "incomplete"
    historical = {"schema_version": "observed-direct-damage-result-v1"}
    assert materialize_predictive_fixed_damage_outcome(decision_state=state, decision_owner=_owner(state, "self"), candidate=candidate, predictive_authority=historical)["status"] == "rejected"


def test_end_to_end_predictive_attack_and_switch_rank_without_observed_attack_authority():
    state, _ = _state(); _tracked_substitute(state); state["active"]["opponent"]["current_hp"] = 40
    owner, fingerprint = _owner(state, "self"), fingerprint_transition_preview_state(state)
    selection = freeze_current_action_authority(decision_state=state, decision_owner=owner, moves=[{"owner": owner, "source_branch_fingerprint": fingerprint, "move_id": "seismic-toss", "selection": "selectable"}], switches=[{"owner": owner, "source_branch_fingerprint": fingerprint, "pokemon_id": "incoming", "selection": "selectable"}])
    incoming = _incoming(); incoming["source_branch_fingerprint"] = fingerprint
    execution = freeze_current_execution_authority(selection_snapshot=selection, switch_incoming=[incoming])
    discovered = discover_candidates(snapshot=selection)["candidates"]
    enriched = enrich_discovered_candidates(selection_snapshot=selection, execution_bundle=execution, candidates=discovered)["candidates"]
    attack = next(row for row in enriched if row["action_type"] == "attack")
    attack = enrich_predictive_attack_candidate(candidate=attack, predictive_authority=_authority(state))["candidate"]
    switch = next(row for row in enriched if row["action_type"] == "manual_switch")
    attack_outcome = materialize_predictive_fixed_damage_outcome(decision_state=state, decision_owner=owner, candidate=attack, predictive_authority=attack["action_authority"])["outcome"]
    switch_outcome = materialize_candidates(decision_state=state, decision_owner=owner, candidates=[switch])["outcomes"][0]["outcome"]
    ranked = rank_candidates(decision_owner=owner, candidates=[attack_outcome, switch_outcome])
    assert attack["execution_readiness"] == "predictive_execution_ready" and ranked["preferred_frontier"] == ["attack:seismic-toss"]
