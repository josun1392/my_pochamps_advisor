from __future__ import annotations

from copy import deepcopy
from fractions import Fraction

from llm.advisor_flinch_causality_observation import admit_standard_charge_flinch_causality_observation
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_standard_charge_flinch_reconciliation_adapter import (
    materialize_standard_charge_flinch_prediction,
    reconcile_observed_standard_charge_flinch_rng,
    retain_standard_charge_flinch_prediction_from_strategy_result,
    validate_standard_charge_flinch_prediction,
)
from llm.advisor_standard_charge_terminal_execution import execute_standard_charge_terminal_attack
from llm.advisor_runtime_d0_standard_charge_power_herb_skip_execution import (
    execute_runtime_d0_standard_charge_power_herb_skip,
    freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority,
)
from tests.test_observed_full_paralysis_existing_path_reconciliation_adapters import (
    _binding_for,
    _owner,
    _own_action,
    _paralysis_runtime_binding,
    _ready,
    _refresh,
)
from tests.test_observed_full_paralysis_action_cancellation_reconciliation import _linked_damage
from tests.test_standard_charge_shared_terminal_execution_contract import _forced_case, _recontract


def _source(*, paralyzed=False):
    _state, _fingerprint, _authority, base = _forced_case(
        own_move="sky-attack", opponent_move="razor-wind",
    )
    contract=base
    if paralyzed:
        actor=deepcopy(base["actor_mechanics"])
        actor["condition"]={"status":"known_present","condition":"paralysis"}
        actor["direct_mechanics"]["combatant"]["status"]="paralysis"
        contract=_recontract(base,actor_mechanics=actor)
    terminal=execute_standard_charge_terminal_attack(execution_contract=contract)
    assert terminal["status"]=="resolved",terminal
    authority=terminal["execution_authority"]
    branch=terminal["terminal_leaves"][0].get("provenance",{}).get("source_branch_fingerprint","charge-flinch-branch")
    ledger,binding=_binding_for(
        session=contract["actor"]["session_id"],
        runtime=authority["source_next_decision_fingerprint"],
        branch=branch,
        actor=contract["actor"],target=contract["target"],move="sky-attack",turn=2,
    )
    prediction=materialize_standard_charge_flinch_prediction(
        terminal_execution=terminal,predictive_binding=binding,predictive_ledger=ledger,
    )
    assert prediction["status"]=="resolved",prediction
    return terminal,ledger,binding,prediction


def _manager(binding):
    state=create_unknown_bootstrap_battle_state(binding["session_id"],binding["actor"]["pokemon_id"],binding["target"]["pokemon_id"])["state"]
    return BattleObservationRuntimeSessionManager.create(binding["session_id"],state)["manager"]


def _history(manager,binding):
    cancelled=admit_previous_action_history_observation(
        runtime_session_manager=manager,captured_session_id=binding["session_id"],
        side=binding["target"]["side"],execution_move_id="tackle",selected_move_id="tackle",
        source_action_id=f"{binding['session_id']}:cancelled",result_class="flinch",turn_number=binding["turn_number"],
    )
    assert cancelled["status"]=="resolved",cancelled
    producer=admit_previous_action_history_observation(
        runtime_session_manager=manager,captured_session_id=binding["session_id"],
        side=binding["actor"]["side"],execution_move_id="sky-attack",selected_move_id="sky-attack",
        source_action_id=binding["source_action_id"],result_class=None,turn_number=binding["turn_number"],
    )
    assert producer["status"]=="resolved",producer
    return producer["observations"][0],cancelled["observations"][0],cancelled["observations"][1]


def _causal(manager,prediction,ledger,binding,producer,cancelled_execution,cancelled_result):
    row=admit_standard_charge_flinch_causality_observation(
        runtime_session_manager=manager,captured_session_id=binding["session_id"],
        prediction=prediction,predictive_binding=binding,predictive_ledger=ledger,
        producer_execution_observation=producer,cancelled_execution_observation=cancelled_execution,
        cancelled_result_observation=cancelled_result,
    )
    assert row["status"]=="resolved",row
    return row["observation"]


def _fraction(value):
    return Fraction(value["numerator"],value["denominator"])


def _effect_secondary(leaf):
    secondary=leaf.get("consequences",{}).get("secondary")
    return secondary if isinstance(secondary,dict) and secondary.get("branch")=="effect" else None


def _effect_mass(terminal):
    return sum((_fraction(leaf["probability"]) for leaf in terminal["terminal_leaves"]
        if _effect_secondary(leaf) is not None
        and _effect_secondary(leaf).get("hypothetical_target_flinch",{}).get("state")=="flinched"),Fraction())


def test_charge_prediction_authenticates_terminal_lifecycle_and_exact_identity():
    terminal,ledger,binding,prediction=_source()
    assert prediction["terminal_prediction_fingerprint"]
    assert prediction["original_charge_action_id"]==binding["candidate_id"]
    assert prediction["terminal_action_identity"]=="attack:sky-attack:standard-charge-continuation"
    assert prediction["terminal_action_identity"]!=prediction["original_charge_action_id"]
    assert prediction["execution_mode"]=="forced_turn_two_continuation"
    assert prediction["caller_kind"]=="forced_turn_two_continuation"
    assert prediction["charge_lifecycle"]==terminal["execution_authority"]["original_charge_lifecycle"]
    assert validate_standard_charge_flinch_prediction(prediction=prediction,predictive_binding=binding,predictive_ledger=ledger)["status"]=="resolved"

    wrong=deepcopy(prediction); wrong["charge_lifecycle"]={}
    assert validate_standard_charge_flinch_prediction(prediction=wrong,predictive_binding=binding,predictive_ledger=ledger)["status"]=="rejected"
    wrong=deepcopy(prediction); wrong["terminal_prediction_fingerprint"]="0"*64
    assert validate_standard_charge_flinch_prediction(prediction=wrong,predictive_binding=binding,predictive_ledger=ledger)["status"]=="rejected"


def test_prediction_time_retention_uses_only_existing_terminal_artifacts_and_deduplicates_copies():
    terminal,ledger,binding,prediction=_source()
    strategy_result={
        "exact_outcome_ledgers":{"sky":ledger},
        "nested":{"first":deepcopy(terminal),"duplicate":deepcopy(terminal)},
    }
    retained=retain_standard_charge_flinch_prediction_from_strategy_result(
        strategy_result=strategy_result,predictive_binding=binding,predictive_ledger=ledger,
    )
    assert retained["status"]=="resolved",retained
    assert retained["prediction"]["terminal_prediction_fingerprint"]==prediction["terminal_prediction_fingerprint"]

    missing=retain_standard_charge_flinch_prediction_from_strategy_result(
        strategy_result={"exact_outcome_ledgers":{"sky":ledger}},
        predictive_binding=binding,predictive_ledger=ledger,
    )
    assert missing["status"]=="incomplete"

    foreign=deepcopy(terminal)
    foreign["retention_copy_marker"]="distinct-authenticated-artifact"
    ambiguous=retain_standard_charge_flinch_prediction_from_strategy_result(
        strategy_result={"a":terminal,"b":foreign},
        predictive_binding=binding,predictive_ledger=ledger,
    )
    assert ambiguous["status"]=="rejected"
    assert ambiguous["reason"]=="ambiguous_standard_charge_terminal_prediction"


def test_ui_historical_bundle_retains_charge_prediction_without_reconstruction():
    source=open("ui/main_window.py",encoding="utf-8").read()
    start=source.index("def _install_historical_predictive_action_bindings")
    end=source.index("def _runtime_owner_matches_predictive_binding",start)
    contract=source[start:end]
    assert "retain_standard_charge_flinch_prediction_from_strategy_result(" in contract
    assert 'bundle["standard_charge_flinch_prediction"]' in contract
    assert "execute_standard_charge_terminal_attack" not in contract


def test_charge_prediction_retirement_inherits_existing_historical_bundle_lifecycle():
    source=open("ui/main_window.py",encoding="utf-8").read()
    install=source[source.index("def _install_historical_predictive_action_bindings"):source.index("def _runtime_owner_matches_predictive_binding")]
    assert "self._historical_predictive_action_bindings = {}" in install
    assert 'bundle["standard_charge_flinch_prediction"]' in install
    turn=source[source.index("def set_current_turn_number"):source.index("def advance_turn")]
    assert "self._historical_predictive_action_bindings = {}" in turn
    battle=source[source.index("def _begin_new_battle_session"):source.index("def begin_new_battle")]
    assert "self._historical_predictive_action_bindings = {}" in battle


def test_same_causal_event_kind_supports_charge_and_preserves_distinct_actions_and_entry_order():
    _terminal,ledger,binding,prediction=_source()
    manager=_manager(binding)
    producer,cancelled_execution,cancelled_result=_history(manager,binding)
    # cancelled history was admitted first; this is not battle-order authority.
    assert producer["observation_sequence"]>cancelled_result["observation_sequence"]
    causal=_causal(manager,prediction,ledger,binding,producer,cancelled_execution,cancelled_result)
    assert causal["event_kind"]=="flinch_causality_observed"
    assert causal["producer_prediction_kind"]=="standard_charge_terminal_execution"
    assert causal["producer_prediction_fingerprint"]==prediction["terminal_prediction_fingerprint"]
    assert causal["producer_source_action_id"]!=causal["cancelled_source_action_id"]
    assert causal["affected_owner"]==binding["target"]
    assert causal["observation_sequence"]>max(producer["observation_sequence"],cancelled_execution["observation_sequence"],cancelled_result["observation_sequence"])


def test_charge_causal_flinch_filters_original_terminal_leaves_and_preserves_mass():
    terminal,ledger,binding,prediction=_source()
    manager=_manager(binding); producer,ce,cr=_history(manager,binding); causal=_causal(manager,prediction,ledger,binding,producer,ce,cr)
    before=deepcopy((terminal,prediction,ledger,binding,producer,ce,cr,causal,manager.read_state()))
    result=reconcile_observed_standard_charge_flinch_rng(
        prediction=prediction,predictive_binding=binding,predictive_ledger=ledger,
        executed_move_observation=producer,flinch_causality_observation=causal,
    )
    expected=_effect_mass(terminal)
    assert result["status"]=="resolved"
    assert _fraction(result["compatible_original_probability_mass"])==expected
    assert result["probability_normalization"]=="none_preserve_original_mass"
    assert "damage_roll" in result["unresolved_hidden_dimensions"]
    kept=[leaf for leaf in terminal["terminal_leaves"] if leaf["leaf_id"] in result["compatible_leaf_ids"]]
    assert kept and all(leaf["hit_state"]=="hit" and leaf["consequences"]["secondary"]["branch"]=="effect" for leaf in kept)
    assert not any("secondary:none" in leaf["branch_path"] for leaf in kept)
    assert (terminal,prediction,ledger,binding,producer,ce,cr,causal,manager.read_state())==before


def test_charge_flinch_reconciliation_preserves_critical_ambiguity_when_source_has_it():
    terminal,ledger,binding,_prediction=_source()
    synthetic=deepcopy(terminal)
    leaves=list(synthetic["terminal_leaves"])
    index=next(i for i,leaf in enumerate(leaves) if _effect_secondary(leaf) is not None)
    original=leaves.pop(index)
    probability=_fraction(original["probability"])
    assert probability>0
    split=[]
    for suffix,state in (("noncrit","non_critical"),("crit","critical")):
        row=deepcopy(original)
        row["leaf_id"]=f"{original['leaf_id']}:{suffix}"
        row["critical_state"]=state
        half=probability/Fraction(2)
        row["probability"]={"numerator":half.numerator,"denominator":half.denominator}
        split.append(row)
    leaves[index:index]=split
    synthetic["terminal_leaves"]=tuple(leaves)
    prediction=materialize_standard_charge_flinch_prediction(
        terminal_execution=synthetic,predictive_binding=binding,predictive_ledger=ledger,
    )
    assert prediction["status"]=="resolved",prediction
    manager=_manager(binding); producer,ce,cr=_history(manager,binding)
    causal=_causal(manager,prediction,ledger,binding,producer,ce,cr)
    result=reconcile_observed_standard_charge_flinch_rng(
        prediction=prediction,predictive_binding=binding,predictive_ledger=ledger,
        executed_move_observation=producer,flinch_causality_observation=causal,
    )
    assert result["status"]=="resolved"
    assert "critical_state" in result["unresolved_hidden_dimensions"]


def test_pre_action_paralysis_cancellation_leaves_cannot_match_successful_flinch():
    terminal,ledger,binding,prediction=_source(paralyzed=True)
    assert any(leaf.get("hit_state")=="not_applicable" for leaf in terminal["terminal_leaves"])
    manager=_manager(binding); producer,ce,cr=_history(manager,binding); causal=_causal(manager,prediction,ledger,binding,producer,ce,cr)
    result=reconcile_observed_standard_charge_flinch_rng(
        prediction=prediction,predictive_binding=binding,predictive_ledger=ledger,
        executed_move_observation=producer,flinch_causality_observation=causal,
    )
    kept=[leaf for leaf in terminal["terminal_leaves"] if leaf["leaf_id"] in result["compatible_leaf_ids"]]
    assert kept and all(leaf.get("hit_state")=="hit" for leaf in kept)


def test_direct_damage_and_charge_flinch_compose_while_crit_roll_ambiguity_survives():
    terminal,ledger,binding,prediction=_source()
    manager=_manager(binding); producer,ce,cr=_history(manager,binding); causal=_causal(manager,prediction,ledger,binding,producer,ce,cr)
    effects=[leaf for leaf in terminal["terminal_leaves"] if _effect_secondary(leaf) is not None]
    damage=effects[0]["consequences"]["source_hit_context"]["actual_damage"]
    linked=_linked_damage(ledger,binding,producer)
    linked["damage_amount"]=damage
    linked["payload"]={**linked.get("payload",{}),"damage_amount":damage}
    linked["observation_sequence"]=producer["observation_sequence"]+1
    result=reconcile_observed_standard_charge_flinch_rng(
        prediction=prediction,predictive_binding=binding,predictive_ledger=ledger,
        executed_move_observation=producer,flinch_causality_observation=causal,direct_damage_observation=linked,
    )
    assert result["status"]=="resolved",result
    assert result["matched_observable_facts"]["direct_damage"]==damage
    assert all(leaf["consequences"]["source_hit_context"]["actual_damage"]==damage for leaf in effects if leaf["leaf_id"] in result["compatible_leaf_ids"])


def test_no_causal_observation_preserves_full_original_mass_and_does_not_imply_no_effect():
    terminal,ledger,binding,prediction=_source()
    manager=_manager(binding); producer,_ce,_cr=_history(manager,binding)
    result=reconcile_observed_standard_charge_flinch_rng(
        prediction=prediction,predictive_binding=binding,predictive_ledger=ledger,executed_move_observation=producer,
    )
    assert result["status"]=="incomplete"
    assert result["compatible_original_probability_mass"]=={"numerator":1,"denominator":1}
    assert len(result["compatible_leaf_ids"])==len(terminal["terminal_leaves"])


def test_power_herb_same_turn_sky_attack_uses_same_authenticated_terminal_adapter():
    state,_s0,_d0=_ready()
    state["self_side"]["pokemon"][0]["known_item"]="power-herb"
    state["self_side"]["pokemon"][0]["condition"]="none"
    target_raw=state["opponent_side"]["pokemon"][0]
    target_raw["known_item"]=None
    target_raw["known_item_provenance"]={
        "event_kind":"current_item_observed","trust":"user_confirmed_observation",
        "turn_number":1,"status":"known_absent",
    }
    snapshot,d0=_refresh(state)
    actor,target=_owner(state,"self"),_owner(state,"opponent")
    action=_own_action(d0,actor,"sky-attack")
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,
        move_metadata={"move_id":"sky-attack"},
    )
    assert authority["status"]=="resolved",authority
    terminal=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert terminal["status"]=="resolved",terminal
    ledger,binding=_paralysis_runtime_binding(
        snapshot=snapshot,d0=d0,actor=actor,target=target,move="sky-attack",
    )
    prediction=materialize_standard_charge_flinch_prediction(
        terminal_execution=terminal,predictive_binding=binding,predictive_ledger=ledger,
    )
    assert prediction["status"]=="resolved",prediction
    assert prediction["execution_mode"]=="power_herb_current_turn_skip"
    assert prediction["caller_kind"]=="power_herb_current_turn_skip"
    assert prediction["original_charge_action_id"]==binding["candidate_id"]
    assert _effect_mass(terminal)>0


def test_unsupported_non_flinch_charge_move_rejects_without_move_name_only_bridge():
    _state,_fingerprint,_authority,contract=_forced_case(own_move="razor-wind",opponent_move="ice-burn")
    terminal=execute_standard_charge_terminal_attack(execution_contract=contract)
    authority=terminal["execution_authority"]
    ledger,binding=_binding_for(session=contract["actor"]["session_id"],runtime=authority["source_next_decision_fingerprint"],branch=terminal["terminal_leaves"][0].get("provenance",{}).get("source_branch_fingerprint","x"),actor=contract["actor"],target=contract["target"],move="razor-wind",turn=2)
    result=materialize_standard_charge_flinch_prediction(terminal_execution=terminal,predictive_binding=binding,predictive_ledger=ledger)
    assert result["status"]=="rejected"


def test_malformed_scalar_charge_hybrid_causal_payload_rejects_at_lifecycle_boundary():
    terminal,ledger,binding,prediction=_source()
    manager=_manager(binding); producer,ce,cr=_history(manager,binding); causal=_causal(manager,prediction,ledger,binding,producer,ce,cr)
    forged=deepcopy(causal)
    forged["payload"]=deepcopy(forged["payload"])
    forged["payload"].pop("caller_kind")
    forged["payload"].pop("charge_lifecycle")
    from llm.advisor_lifecycle_confirmation import FLINCH_CAUSALITY_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
    owners={"self":binding["actor"],"opponent":binding["target"]}
    boundary=LifecycleConfirmationBoundary(binding["session_id"],owners)
    result=boundary.confirm(
        event_kind="flinch_causality_observed",payload=forged["payload"],
        session_id=binding["session_id"],source=FLINCH_CAUSALITY_SOURCE,trust=USER_TRUST,
        confirmed=True,side=binding["actor"]["side"],slot_index=binding["actor"]["slot_index"],
        pokemon_id=binding["actor"]["pokemon_id"],turn_number=binding["turn_number"],
    )
    assert result["status"]!="confirmed"


def test_charge_causal_tamper_wrong_caller_action_target_and_result_fail_closed():
    terminal,ledger,binding,prediction=_source()
    manager=_manager(binding); producer,ce,cr=_history(manager,binding)
    forged=deepcopy(prediction)
    forged["terminal_execution"]["execution_authority"]["original_charge_action_id"]="attack:forged"
    assert validate_standard_charge_flinch_prediction(prediction=forged,predictive_binding=binding,predictive_ledger=ledger)["status"]=="rejected"

    bad_cr=deepcopy(cr); bad_cr["payload"]["result_class"]="success"
    result=admit_standard_charge_flinch_causality_observation(
        runtime_session_manager=manager,captured_session_id=binding["session_id"],prediction=prediction,
        predictive_binding=binding,predictive_ledger=ledger,producer_execution_observation=producer,
        cancelled_execution_observation=ce,cancelled_result_observation=bad_cr,
    )
    assert result["status"]=="rejected"


def test_cancelled_action_probability_remains_conditional_one_without_double_counting():
    source=open("llm/advisor_immediate_move_vs_move_action_pair.py",encoding="utf-8").read()
    fragment=source[source.index('"execution_branch_id": "second_action:flinched"'):]
    fragment=fragment[:500]
    assert '"conditional_probability": _fd(Fraction(1, 1))' in fragment
    assert "Fraction(3, 10)" not in fragment
