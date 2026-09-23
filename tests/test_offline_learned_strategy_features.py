from copy import deepcopy

import pytest

from llm.advisor_exact_outcome_descriptive_metrics import project_exact_outcome_descriptive_metrics
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_offline_learned_strategy_features import (
    materialize_offline_learned_strategy_feature_rows,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _inputs():
    state = create_unknown_bootstrap_battle_state("offline", "self-a", "opponent-a")["state"]
    snapshot = {
        "status": "runtime_snapshot_ready", "session_id": "offline",
        "state": state, "state_fingerprint": state_fingerprint(state),
    }
    owner = {"session_id": "offline", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    assert d0["status"] == "resolved"
    result = {
        "schema_version": "deterministic-strategy-orchestration-result-v1",
        "status": "resolved", "session_id": "offline",
        "decision_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(owner),
        "candidates": [
            {"schema_version": "deterministic-strategy-candidate-evidence-v1", "candidate_id": "attack:tackle", "action_type": "attack", "evidence_class": "exact_outcome", "execution_readiness": "complete"},
            {"schema_version": "deterministic-strategy-candidate-evidence-v1", "candidate_id": "switch:incoming", "action_type": "manual_switch", "evidence_class": "exact_outcome", "execution_readiness": None},
        ],
    }
    bindings = {
        "session_id": "offline", "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(owner),
    }
    attack_bindings = {
        **bindings, "attacker": deepcopy(owner),
        "target": {"session_id": "offline", "side": "opponent", "slot_index": 0, "pokemon_id": "opponent-a"},
        "move_id": "tackle",
    }
    def ledger(candidate_id, action_type, source, leaves):
        return {
            "status": "evaluable", "schema_version": "exact-predictive-outcome-ledger-v1",
            "horizon": "immediate_action_consequence", "candidate_id": candidate_id,
            "action_type": action_type, "bindings": deepcopy(source),
            "terminal_leaves": tuple({
                "leaf_id": name, "candidate_id": candidate_id, "action_type": action_type,
                "probability": probability, "consequences": consequences,
                "provenance": deepcopy(source),
            } for name, probability, consequences in leaves),
            "terminal_probability_mass": {"numerator": 1, "denominator": 1},
        }
    attack = ledger("attack:tackle", "attack", attack_bindings, (
        ("survive", {"numerator": 1, "denominator": 3}, {"target_final_hp": 40, "own_final_hp": 80}),
        ("ko", {"numerator": 2, "denominator": 3}, {"target_final_hp": 0, "own_final_hp": 80}),
    ))
    switch = ledger("switch:incoming", "manual_switch", bindings, (
        ("switch", {"numerator": 1, "denominator": 1}, {"target_final_hp": None, "own_final_hp": None}),
    ))
    ledgers = {"attack:tackle": attack, "switch:incoming": switch}
    metrics = {key: project_exact_outcome_descriptive_metrics(ledger=value) for key, value in ledgers.items()}
    assert all(value["status"] == "resolved" for value in metrics.values())
    return {
        "strategy_d0": d0, "runtime_snapshot": snapshot, "strategy_result": result,
        "exact_outcome_ledgers": ledgers, "descriptive_metrics": metrics,
    }


def _run(inputs):
    return materialize_offline_learned_strategy_feature_rows(**inputs)


def test_attack_and_switch_features_keep_exact_rationals_and_explicit_unavailable():
    result = _run(_inputs())
    assert result["status"] == "resolved"
    attack, switch = result["rows"]
    assert (attack["candidate_id"], switch["candidate_id"]) == ("attack:tackle", "switch:incoming")
    assert attack["status"] == switch["status"] == "complete"
    assert attack["features"]["target_ko_probability"] == {
        "availability": "available", "value": {"numerator": 2, "denominator": 3},
    }
    assert attack["features"]["own_faint_probability"]["value"] == {"numerator": 0, "denominator": 1}
    assert attack["features"]["terminal_probability_mass"]["value"] == {"numerator": 1, "denominator": 1}
    assert attack["features"]["guaranteed_target_ko"]["value"] is False
    assert switch["features"]["target_ko_probability"] == {
        "availability": "unavailable", "reason": "not_applicable",
    }
    assert switch["features"]["own_faint_probability"]["availability"] == "unavailable"
    assert switch["features"]["execution_readiness"]["availability"] == "unavailable"
    assert attack["provenance"]["candidate_id"] == "attack:tackle"
    assert attack["provenance"]["source_runtime_fingerprint"] == result["provenance"]["source_runtime_fingerprint"]


def test_missing_or_incomplete_metrics_remain_unavailable_without_zero_defaults():
    inputs = _inputs()
    inputs["descriptive_metrics"].pop("attack:tackle")
    result = _run(inputs)
    attack = result["rows"][0]
    assert attack["status"] == "incomplete"
    assert attack["features"]["terminal_probability_mass"]["availability"] == "available"
    assert attack["features"]["target_ko_probability"]["availability"] == "unavailable"
    assert "value" not in attack["features"]["target_ko_probability"]
    inputs["descriptive_metrics"]["attack:tackle"] = {
        "status": "incomplete", "schema_version": "exact-outcome-descriptive-metrics-v1",
        "candidate_id": "attack:tackle", "action_type": "attack",
        "bindings": deepcopy(inputs["exact_outcome_ledgers"]["attack:tackle"]["bindings"]),
    }
    assert _run(inputs)["rows"][0]["status"] == "incomplete"
    inputs["exact_outcome_ledgers"].pop("attack:tackle")
    inputs["descriptive_metrics"].pop("attack:tackle")
    assert _run(inputs)["rows"][0]["features"]["terminal_probability_mass"]["availability"] == "unavailable"


def test_bound_unsupported_ledger_and_incomplete_candidate_stay_incomplete():
    inputs = _inputs()
    inputs["exact_outcome_ledgers"]["attack:tackle"] = {
        "status": "unsupported", "candidate_id": "attack:tackle", "action_type": "attack",
        "bindings": deepcopy(inputs["exact_outcome_ledgers"]["attack:tackle"]["bindings"]),
    }
    inputs["descriptive_metrics"].pop("attack:tackle")
    assert _run(inputs)["rows"][0]["features"]["target_ko_probability"]["availability"] == "unavailable"
    assert _run(inputs)["rows"][0]["status"] == "incomplete"
    inputs = _inputs()
    inputs["strategy_result"]["candidates"][0]["evidence_class"] = "incomplete"
    assert _run(inputs)["rows"][0]["status"] == "incomplete"


@pytest.mark.parametrize("change", [
    lambda x: x["strategy_result"].update(session_id="foreign"),
    lambda x: x["runtime_snapshot"].update(state_fingerprint="stale"),
    lambda x: x["strategy_result"].update(decision_branch_fingerprint="other"),
    lambda x: x["strategy_result"].update(decision_owner={"side": "opponent"}),
    lambda x: x["exact_outcome_ledgers"]["attack:tackle"]["bindings"].update(candidate_id="forged", source_runtime_fingerprint="old"),
    lambda x: x["exact_outcome_ledgers"]["attack:tackle"]["bindings"]["target"].update(session_id="foreign"),
    lambda x: x["exact_outcome_ledgers"]["attack:tackle"]["bindings"]["target"].update(side="self"),
    lambda x: x["exact_outcome_ledgers"]["attack:tackle"].update(candidate_id="attack:other"),
    lambda x: x["descriptive_metrics"]["attack:tackle"].update(candidate_id="attack:other"),
    lambda x: x["exact_outcome_ledgers"].update({"attack:foreign": x["exact_outcome_ledgers"]["attack:tackle"]}),
    lambda x: x["strategy_result"]["candidates"][0].update(candidate_id="attack:foreign"),
    lambda x: x["strategy_result"]["candidates"].append(deepcopy(x["strategy_result"]["candidates"][0])),
    lambda x: x["exact_outcome_ledgers"]["attack:tackle"]["terminal_leaves"][0]["probability"].update(denominator=0),
    lambda x: x["exact_outcome_ledgers"]["attack:tackle"]["terminal_leaves"][0]["probability"].update(numerator=2),
    lambda x: x["exact_outcome_ledgers"]["attack:tackle"].update(terminal_probability_mass={"numerator": 1, "denominator": 2}),
    lambda x: x["descriptive_metrics"]["attack:tackle"]["target"].update(ko_probability={"numerator": 1, "denominator": 1}),
    lambda x: x["descriptive_metrics"]["attack:tackle"]["target"].update(ko_probability={"numerator": 2, "denominator": 0}),
])
def test_stale_foreign_malformed_or_mismatched_evidence_fails_closed(change):
    inputs = _inputs()
    change(inputs)
    assert _run(inputs)["status"] == "rejected"


def test_repeated_extraction_is_order_stable_deeply_read_only_and_source_pure():
    inputs = _inputs()
    before = deepcopy(inputs)
    first = _run(inputs)
    assert inputs == before
    inputs["strategy_result"]["candidates"].reverse()
    inputs["exact_outcome_ledgers"] = dict(reversed(list(inputs["exact_outcome_ledgers"].items())))
    second = _run(inputs)
    assert first == second
    with pytest.raises(TypeError):
        first["rows"][0]["features"]["target_ko_probability"]["value"]["numerator"] = 0
    inputs["descriptive_metrics"]["attack:tackle"]["target"]["ko_probability"]["numerator"] = 0
    assert first["rows"][0]["features"]["target_ko_probability"]["value"]["numerator"] == 2
