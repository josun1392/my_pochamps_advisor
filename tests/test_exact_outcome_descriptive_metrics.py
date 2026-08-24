from copy import deepcopy

from llm.advisor_exact_outcome_descriptive_metrics import project_exact_outcome_descriptive_metrics
from llm.advisor_guaranteed_fact_comparison import rank_guaranteed_candidates


OWNER = {"side": "self", "session_id": "metrics", "slot_index": 0, "pokemon_id": "self"}
TARGET = {"side": "opponent", "session_id": "metrics", "slot_index": 0, "pokemon_id": "target"}
BINDINGS = {"session_id": "metrics", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": OWNER, "attacker": OWNER, "target": TARGET, "move_id": "shadow-ball"}


def _leaf(name, numerator, denominator, *, target_hp=20, own_hp=100, secondary=None):
    return {"leaf_id": name, "candidate_id": "attack:shadow-ball", "action_type": "attack", "probability": {"numerator": numerator, "denominator": denominator}, "consequences": {"target_final_hp": target_hp, "own_final_hp": own_hp, "secondary": secondary}, "provenance": deepcopy(BINDINGS)}


def _ledger(leaves, *, action_type="attack"):
    bindings = deepcopy(BINDINGS)
    candidate_id = "attack:shadow-ball"
    if action_type == "manual_switch":
        candidate_id = "switch:incoming"; bindings.pop("attacker"); bindings.pop("target"); bindings.pop("move_id")
        leaves = tuple({**leaf, "candidate_id": candidate_id, "action_type": action_type, "provenance": deepcopy(bindings)} for leaf in leaves)
    return {"status": "evaluable", "schema_version": "exact-predictive-outcome-ledger-v1", "horizon": "immediate_action_consequence", "candidate_id": candidate_id, "action_type": action_type, "bindings": bindings, "terminal_leaves": tuple(leaves), "terminal_probability_mass": {"numerator": 1, "denominator": 1}}


def test_mixed_ko_and_duplicate_hp_leaves_aggregate_exactly_without_losing_leaf_ids():
    ledger = _ledger((_leaf("miss", 1, 5, target_hp=20), _leaf("roll:0", 2, 5, target_hp=0), _leaf("roll:1", 2, 5, target_hp=0)))
    result = project_exact_outcome_descriptive_metrics(ledger=ledger)
    assert result["status"] == "resolved"
    assert result["target"]["ko_probability"] == {"numerator": 4, "denominator": 5}
    assert result["target"]["survival_probability"] == {"numerator": 1, "denominator": 5}
    assert result["target"]["final_hp_distribution"]["outcomes"][0] == {"final_hp": 0, "probability": {"numerator": 4, "denominator": 5}, "leaf_ids": ("roll:0", "roll:1")}
    assert result["target"]["final_hp_distribution"]["probability_mass"] == {"numerator": 1, "denominator": 1}


def test_self_faint_and_intersection_safe_guaranteed_facts_are_exact():
    ledger = _ledger((_leaf("a", 1, 2, target_hp=0, own_hp=0), _leaf("b", 1, 2, target_hp=0, own_hp=0)))
    result = project_exact_outcome_descriptive_metrics(ledger=ledger)
    assert result["own"]["self_faint_probability"] == {"numerator": 1, "denominator": 1}
    assert result["guaranteed_facts"]["target_ko"] is True
    assert result["guaranteed_facts"]["self_faint"] is True
    assert result["guaranteed_facts"]["exact_own_final_hp"] == 0


def test_supported_secondary_probabilities_are_derived_from_global_leaf_mass():
    self_effect = {"branch": "effect", "hypothetical_stage_effect": {"owner": "self", "stat": "attack", "resulting_stage": 1}}
    target_effect = {"branch": "effect", "hypothetical_stage_effect": {"owner": "target", "stat": "special-defense", "resulting_stage": -1}}
    paralysis = {"branch": "effect", "hypothetical_target_condition": {"resulting_condition": "paralysis"}}
    ledger = _ledger((_leaf("metal", 1, 10, secondary=self_effect), _leaf("shadow", 1, 5, secondary=target_effect), _leaf("bolt", 1, 16, secondary=paralysis), _leaf("none", 51, 80)))
    result = project_exact_outcome_descriptive_metrics(ledger=ledger)
    stages = result["hypothetical_stage_outcomes"]["outcomes"]
    assert stages[0]["probability"] == {"numerator": 1, "denominator": 10}
    assert stages[1]["probability"] == {"numerator": 1, "denominator": 5}
    assert result["hypothetical_target_conditions"]["outcomes"] == ({"condition": "paralysis", "probability": {"numerator": 1, "denominator": 16}, "leaf_ids": ("bolt",)},)


def test_manual_switch_has_only_not_applicable_target_and_own_metrics():
    ledger = _ledger((_leaf("switch", 1, 1, target_hp=None, own_hp=None),), action_type="manual_switch")
    result = project_exact_outcome_descriptive_metrics(ledger=ledger)
    assert result["status"] == "resolved"
    assert result["target"] == {"status": "not_applicable"}
    assert result["own"] == {"status": "not_applicable"}
    assert result["ranking_influence"] == "none"


def test_unavailable_or_partial_ledgers_fail_closed_without_renormalization():
    for status in ("incomplete", "unsupported", "rejected"):
        result = project_exact_outcome_descriptive_metrics(ledger={"status": status, "schema_version": "exact-predictive-outcome-ledger-v1", "reason": "upstream"})
        assert result["status"] == status
    partial = _ledger((_leaf("only", 1, 2),))
    result = project_exact_outcome_descriptive_metrics(ledger=partial)
    assert result["status"] == "rejected" and result["reason"] == "ledger_probability_mass_mismatch"


def test_metrics_do_not_change_guaranteed_ranking_inputs_or_output():
    first = {"status": "resolved", "schema_version": "deterministic-guaranteed-candidate-facts-v1", "candidate_id": "attack:a", "session_id": "metrics", "source_branch_fingerprint": "preview", "decision_owner": OWNER, "horizon": "immediate_action_consequence", "guaranteed_own_fainted": False, "guaranteed_opponent_fainted": False, "exact_own_hp": 80}
    second = {**first, "candidate_id": "attack:b", "exact_own_hp": 70}
    before = rank_guaranteed_candidates(candidates=[deepcopy(first), deepcopy(second)])
    metrics = project_exact_outcome_descriptive_metrics(ledger=_ledger((_leaf("only", 1, 1),)))
    after = rank_guaranteed_candidates(candidates=[first, second])
    assert metrics["ranking_influence"] == "none"
    assert before == after
