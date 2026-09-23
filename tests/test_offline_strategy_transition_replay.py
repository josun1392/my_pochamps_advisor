from copy import deepcopy

import pytest

from llm.advisor_current_state_runtime_admission import admit_current_state_observation
from llm.advisor_detached_observed_rng_reconciliation import materialize_historical_predictive_action_binding
from llm.advisor_exact_outcome_descriptive_metrics import project_exact_outcome_descriptive_metrics
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_offline_learned_strategy_features import materialize_offline_learned_strategy_feature_rows
from llm.advisor_offline_strategy_transition_replay import materialize_offline_strategy_transition
from llm.advisor_pokemon_switch_observation import admit_pokemon_switch_observation
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_observed_scalar_attack_rng_reconciliation import _ledger as scalar_ledger
from tests.test_production_pokemon_switch_observation_wiring import _manager as switch_manager


def _features(snapshot, d0, candidate_id, action_type, ledger):
    candidate = {
        "schema_version": "deterministic-strategy-candidate-evidence-v1",
        "candidate_id": candidate_id, "action_type": action_type,
        "evidence_class": "exact_outcome", "execution_readiness": "complete",
    }
    strategy = {
        "status": "incomplete_comparison_set",
        "schema_version": "deterministic-strategy-orchestration-result-v1",
        "session_id": d0["session_id"],
        "decision_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "candidates": [candidate],
    }
    metrics = project_exact_outcome_descriptive_metrics(ledger=ledger)
    assert metrics["status"] == "resolved"
    result = materialize_offline_learned_strategy_feature_rows(
        strategy_d0=d0, runtime_snapshot=snapshot, strategy_result=strategy,
        exact_outcome_ledgers={candidate_id: ledger}, descriptive_metrics={candidate_id: metrics},
    )
    assert result["status"] == "resolved"
    return result


def _attack_case(turn=1):
    state = create_unknown_bootstrap_battle_state("replay", "self-a", "opponent-a")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    manager = BattleObservationRuntimeSessionManager.create("replay", state)["manager"]
    decision = manager.capture_runtime_state_snapshot("replay")
    owner = {"session_id": "replay", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    target = {"session_id": "replay", "side": "opponent", "slot_index": 0, "pokemon_id": "opponent-a"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=decision, decision_owner=owner)
    assert d0["status"] == "resolved"
    ledger = scalar_ledger(critical=False)
    bindings = {
        "session_id": "replay", "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": owner, "attacker": owner, "target": target, "move_id": "shadow-ball",
    }
    ledger["bindings"] = deepcopy(bindings)
    for leaf in ledger["terminal_leaves"]:
        leaf["provenance"] = deepcopy(bindings)
    features = _features(decision, d0, "attack:shadow-ball", "attack", ledger)
    binding = materialize_historical_predictive_action_binding(predictive_ledger=ledger, turn_number=turn)
    assert binding["status"] == "resolved"
    executed = admit_previous_action_history_observation(
        runtime_session_manager=manager, captured_session_id="replay", side="self",
        execution_move_id="shadow-ball", selected_move_id="shadow-ball",
        source_action_id=binding["source_action_id"], result_class="success", turn_number=turn,
    )
    assert executed["status"] == "resolved"
    hp = admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id="replay",
        event_kind="exact_hp_transition_observed",
        payload={"hp_before": 100, "hp_after": 80}, side="self", turn_number=turn,
    )
    assert hp["status"] == "resolved"
    kwargs = {
        "feature_contract": features, "candidate_id": "attack:shadow-ball",
        "decision_runtime_snapshot": decision, "decision_turn_number": turn,
        "observation_snapshot": manager.read_collection_snapshot(),
        "executed_observation_id": executed["observations"][0]["observation_id"],
        "next_runtime_snapshot": manager.capture_runtime_state_snapshot("replay"),
        "next_state_observation_id": hp["observation"]["observation_id"],
        "historical_binding": binding, "predictive_ledger": ledger,
    }
    return kwargs


def _switch_case():
    manager = switch_manager()
    decision = manager.capture_runtime_state_snapshot("s")
    owner = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "pikachu"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=decision, decision_owner=owner)
    assert d0["status"] == "resolved"
    bindings = {
        "session_id": "s", "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": owner,
    }
    candidate_id = "manual_switch:raichu"
    ledger = {
        "status": "evaluable", "schema_version": "exact-predictive-outcome-ledger-v1",
        "horizon": "immediate_action_consequence", "candidate_id": candidate_id,
        "action_type": "manual_switch", "bindings": deepcopy(bindings),
        "terminal_leaves": ({
            "leaf_id": "switch", "candidate_id": candidate_id, "action_type": "manual_switch",
            "probability": {"numerator": 1, "denominator": 1},
            "consequences": {"target_final_hp": None, "own_final_hp": None},
            "provenance": deepcopy(bindings),
        },),
        "terminal_probability_mass": {"numerator": 1, "denominator": 1},
    }
    features = _features(decision, d0, candidate_id, "manual_switch", ledger)
    switched = admit_pokemon_switch_observation(
        runtime_session_manager=manager, captured_session_id="s", side="self",
        switch_in_slot_index=1, switch_in_pokemon_id="raichu", turn_number=4,
    )
    assert switched["status"] == "resolved"
    rows = manager.read_collection_snapshot()["ordered_observations"]
    anchor = max(rows, key=lambda row: row["observation_sequence"])
    assert anchor["observation_id"] == switched["observation"]["observation_id"]
    return {
        "feature_contract": features, "candidate_id": candidate_id,
        "decision_runtime_snapshot": decision, "decision_turn_number": 4,
        "observation_snapshot": manager.read_collection_snapshot(),
        "executed_observation_id": switched["observation"]["observation_id"],
        "next_runtime_snapshot": manager.capture_runtime_state_snapshot("s"),
        "next_state_observation_id": anchor["observation_id"],
    }


def _run(kwargs):
    return materialize_offline_strategy_transition(**kwargs)


def test_observed_attack_replay_uses_later_hp_truth_without_reward():
    kwargs = _attack_case()
    result = _run(kwargs)
    assert result["status"] == "resolved", result
    assert result["decision_feature_row"]["candidate_id"] == "attack:shadow-ball"
    assert result["executed_action"]["execution_identity"] == {
        "kind": "historical_action_link", "id": kwargs["historical_binding"]["source_action_id"],
    }
    assert result["next_state"]["state_fingerprint"] == kwargs["next_runtime_snapshot"]["state_fingerprint"]
    assert result["next_state"]["observed_summary"]["decision_actor_current_hp"] == {"availability": "available", "value": 80}
    assert result["next_state"]["observed_summary"]["battle_terminal"]["availability"] == "unavailable"
    assert "reward" not in result and "policy" not in result


def test_observed_manual_switch_replay_links_exact_incoming_identity():
    result = _run(_switch_case())
    assert result["status"] == "resolved", result
    assert result["executed_action"]["candidate_id"] == "manual_switch:raichu"
    assert result["executed_action"]["execution_identity"]["kind"] == "switch_observation"
    assert result["next_state"]["observed_summary"]["decision_side_active_owner"]["value"]["pokemon_id"] == "raichu"
    assert result["next_state"]["turn_number"] == 4


def test_missing_execution_or_historical_binding_is_explicitly_incomplete():
    kwargs = _attack_case()
    kwargs["executed_observation_id"] = "predicted-only"
    assert _run(kwargs)["status"] == "incomplete"
    kwargs = _attack_case()
    kwargs["historical_binding"] = None
    assert _run(kwargs)["status"] == "incomplete"


@pytest.mark.parametrize("change", [
    lambda x: x["next_runtime_snapshot"].update(session_id="foreign"),
    lambda x: x.update(feature_contract={
        **x["feature_contract"],
        "provenance": {**x["feature_contract"]["provenance"], "decision_owner": {"side": "opponent"}},
    }),
    lambda x: x.update(candidate_id="attack:foreign"),
    lambda x: x["historical_binding"].update(source_runtime_fingerprint="stale"),
    lambda x: x["historical_binding"].update(source_branch_fingerprint="stale"),
    lambda x: x["historical_binding"].update(turn_number=2),
    lambda x: x["historical_binding"].update(actor={"side": "opponent"}),
    lambda x: x["observation_snapshot"]["ordered_observations"][0]["payload"].update(move_id="tackle"),
    lambda x: x["observation_snapshot"]["ordered_observations"][0]["payload"].update(source_action_id="foreign-action"),
    lambda x: x["observation_snapshot"]["ordered_observations"][0].update(source="foreign"),
    lambda x: x["observation_snapshot"]["ordered_observations"][0].update(side="opponent"),
    lambda x: x.update(next_runtime_snapshot=x["decision_runtime_snapshot"]),
    lambda x: x["next_runtime_snapshot"].update(state_fingerprint="malformed"),
    lambda x: x["next_runtime_snapshot"]["state"]["last_commit_provenance"].update(applied_step_ids=["foreign"]),
    lambda x: x["observation_snapshot"]["ordered_observations"][-1].update(turn_number=0),
    lambda x: x["observation_snapshot"]["ordered_observations"][-1].update(observation_sequence=1),
])
def test_stale_foreign_or_temporally_invalid_attack_fails_closed(change):
    kwargs = _attack_case()
    change(kwargs)
    assert _run(kwargs)["status"] == "rejected"


def test_wrong_switch_identity_or_actor_fails_closed():
    kwargs = _switch_case()
    kwargs["observation_snapshot"]["ordered_observations"][0]["payload"]["switch_in_pokemon_id"] = "vaporeon"
    assert _run(kwargs)["status"] == "rejected"
    kwargs = _switch_case()
    kwargs["observation_snapshot"]["ordered_observations"][0]["side"] = "opponent"
    assert _run(kwargs)["status"] == "rejected"
    kwargs = _switch_case()
    kwargs["observation_snapshot"]["ordered_observations"][0]["observation_id"] = "s:phazing-switch-1"
    kwargs["executed_observation_id"] = "s:phazing-switch-1"
    kwargs["next_state_observation_id"] = "s:phazing-switch-1"
    assert _run(kwargs)["status"] == "rejected"


def test_older_next_observation_turn_is_rejected():
    kwargs = _attack_case(turn=2)
    kwargs["observation_snapshot"]["ordered_observations"][-1]["turn_number"] = 1
    assert _run(kwargs)["status"] == "rejected"


def test_transition_is_deterministic_and_sources_remain_unchanged():
    kwargs = _attack_case()
    before = deepcopy({key: value for key, value in kwargs.items() if key != "feature_contract"})
    first = _run(kwargs)
    assert first["status"] == "resolved"
    assert {key: value for key, value in kwargs.items() if key != "feature_contract"} == before
    kwargs["observation_snapshot"]["ordered_observations"].reverse()
    second = _run(kwargs)
    assert first == second
    with pytest.raises(TypeError):
        first["next_state"]["observed_summary"]["decision_actor_current_hp"]["value"] = 0
    kwargs["next_runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    assert first["next_state"]["observed_summary"]["decision_actor_current_hp"]["value"] == 80
