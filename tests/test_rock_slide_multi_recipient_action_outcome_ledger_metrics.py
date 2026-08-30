from copy import deepcopy

from llm.advisor_detached_rock_slide_multi_recipient_predictive_graph_materialization import (
    materialize_detached_rock_slide_multi_recipient_predictive_graph,
)
from llm.advisor_rock_slide_multi_recipient_action_descriptive_metrics import (
    project_rock_slide_multi_recipient_action_descriptive_metrics,
)
from llm.advisor_rock_slide_multi_recipient_action_outcome_ledger import (
    normalize_rock_slide_multi_recipient_action_outcome_ledger,
)
from tests.test_detached_rock_slide_multi_recipient_predictive_graph_materialization import _inputs, _wide_guard_authority


def _graph(*, accuracy=100, target_hp=100):
    _state, snapshot, d0, action, scope = _inputs(accuracy=accuracy, target_hp=target_hp)
    graph = materialize_detached_rock_slide_multi_recipient_predictive_graph(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        execution_scope_authority=scope,
    )
    assert graph["status"] == "evaluable", graph.get("reason")
    return graph


def test_two_recipient_graph_normalizes_and_projects_exact_recipient_and_joint_metrics():
    ledger = normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=_graph())
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert "terminal_leaves" not in ledger

    metrics = project_rock_slide_multi_recipient_action_descriptive_metrics(ledger=ledger)
    assert metrics["status"] == "resolved", metrics.get("reason")
    assert metrics["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert [row["recipient"]["active_slot_index"] for row in metrics["recipients"]] == [0, 1]
    assert all(row["final_hp_distribution"]["probability_mass"] == {"numerator": 1, "denominator": 1} for row in metrics["recipients"])
    assert metrics["joint_terminal_states"]["probability_mass"] == {"numerator": 1, "denominator": 1}
    assert metrics["action"]["no_recipient_faints_probability"] == {"numerator": 1, "denominator": 1}


def test_low_hp_graph_reports_exact_joint_and_all_recipient_faint_mass():
    ledger = normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=_graph(target_hp=1))
    metrics = project_rock_slide_multi_recipient_action_descriptive_metrics(ledger=ledger)
    assert metrics["status"] == "resolved", metrics.get("reason")
    assert [row["faint_probability"] for row in metrics["recipients"]] == [
        {"numerator": 1, "denominator": 1},
        {"numerator": 1, "denominator": 1},
    ]
    assert metrics["action"]["at_least_one_recipient_faints_probability"] == {"numerator": 1, "denominator": 1}
    assert metrics["action"]["all_represented_recipients_faint_probability"] == {"numerator": 1, "denominator": 1}


def test_miss_paths_keep_not_applicable_critical_and_roll_identity():
    graph = _graph(accuracy=1)
    ledger = normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=graph)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    terminal = [edge for edge in graph["terminal_leaf_edges"] if edge["terminal"]]
    assert terminal
    missed = [
        outcome
        for edge in terminal
        for outcome in edge["terminal_consequences"]["ordered_recipient_outcomes"]
        if outcome["outcome"] == "miss"
    ]
    assert missed and all(
        outcome["critical_state"] == "not_applicable"
        and outcome["damage_roll"]["status"] == "not_applicable"
        for outcome in missed
    )
    metrics = project_rock_slide_multi_recipient_action_descriptive_metrics(ledger=ledger)
    assert all(row["miss_probability"] == {"numerator": 99, "denominator": 100} for row in metrics["recipients"])


def test_malformed_cycle_probability_cursor_and_terminal_outcome_graphs_reject():
    graph = _graph()

    cycle = deepcopy(graph)
    first = next(edge for edge in cycle["terminal_leaf_edges"] if not edge["terminal"])
    first["to_node_id"] = first["from_node_id"]
    assert normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=cycle)["status"] == "rejected"

    bad_mass = deepcopy(graph)
    bad_mass["terminal_leaf_edges"][0]["conditional_probability"] = {"numerator": 2, "denominator": 1}
    assert normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=bad_mass)["status"] == "rejected"

    missing_terminal_outcome = deepcopy(graph)
    terminal = next(edge for edge in missing_terminal_outcome["terminal_leaf_edges"] if edge["terminal"])
    terminal["terminal_consequences"]["ordered_recipient_outcomes"] = terminal["terminal_consequences"]["ordered_recipient_outcomes"][:1]
    assert normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=missing_terminal_outcome)["status"] == "rejected"

    bad_cursor = deepcopy(graph)
    bad_cursor["terminal_leaf_nodes"][0]["recipient_cursor"] = 1
    assert normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=bad_cursor)["status"] == "rejected"


def test_wide_guard_prevention_provenance_normalizes_and_malformed_damage_or_authority_rejects():
    _state, snapshot, d0, action, scope = _inputs(accuracy=100)
    authority = _wide_guard_authority(d0, snapshot, action, scope)
    graph = materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_scope_authority=scope, wide_guard_spread_applicability_authority=authority)
    ledger = normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=graph)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    metrics = project_rock_slide_multi_recipient_action_descriptive_metrics(ledger=ledger)
    assert all(row["wide_guard_prevention_probability"] == {"numerator": 1, "denominator": 1} and row["faint_probability"] == {"numerator": 0, "denominator": 1} for row in metrics["recipients"])

    malformed = deepcopy(graph)
    prevented = next(edge for edge in malformed["terminal_leaf_edges"] if edge["recipient_outcome"]["outcome"] == "prevented_by_wide_guard")
    prevented["recipient_outcome"]["actual_damage"] = 1
    assert normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=malformed)["status"] == "rejected"
    malformed_authority = deepcopy(graph)
    malformed_authority["terminal_leaf_edges"][0]["recipient_outcome"]["wide_guard_applicability_authority"] = {"status": "resolved"}
    assert normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=malformed_authority)["status"] == "rejected"
