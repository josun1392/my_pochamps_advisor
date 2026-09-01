from copy import deepcopy

from llm.advisor_detached_opponent_response_profile import materialize_detached_opponent_response_profile
from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair
from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_detached_variable_two_to_five_hit_graph_immediate_move_pair import _population_bomb_action, _variable_action
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order


def _graph_pair(*, move_id="bullet-seed", power=25, own_hp=100, opponent_hp=100, own_ability="pressure"):
    _state, snapshot, d0, _own, response_set, _orders = _inputs(own_hp=own_hp, opponent_hp=opponent_hp, own_ability=own_ability)
    own = _variable_action(d0, move_id, power)
    opponent = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "own_first"),
    )
    return snapshot, d0, own, opponent, response_set, pair


def test_bullet_seed_and_rock_blast_graph_pairs_normalize_and_project_exact_metrics():
    for move in ("bullet-seed", "rock-blast"):
        # This test owns graph-ledger/metric invariants, not a duplicate of
        # the surviving-second-action transition coverage below.  A forced
        # first-hit KO preserves each selected 2/3/4/5-count root and its
        # exact probability while avoiding a mechanically irrelevant full
        # second-action ledger for every distinct first-action HP state.
        _snapshot, _d0, _own, _opponent, _set, pair = _graph_pair(
            move_id=move, power=500, opponent_hp=1,
        )
        ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
        metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
        assert ledger["status"] == "evaluable", ledger.get("reason")
        assert ledger["terminal_leaf_representation"] == "exact_variable_multi_hit_graph_paths"
        assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert metrics["status"] == "resolved", metrics.get("reason")
        assert metrics["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert metrics["opponent"]["final_hp_distribution"]["probability_mass"] == {"numerator": 1, "denominator": 1}
        assert metrics["opponent"]["ko_probability"]["numerator"] + metrics["opponent"]["survival_probability"]["numerator"] == metrics["opponent"]["ko_probability"]["denominator"]


def test_graph_ko_cancellation_and_surviving_second_action_paths_are_exact_and_auditable():
    _snapshot, _d0, _own, _opponent, _set, pair = _graph_pair(power=500, opponent_hp=1)
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
    transitions = ledger["validated_order_graphs"][0]["terminal_transitions"]
    assert all(row["second_action"]["state"] == "cancelled_due_to_faint" for row in transitions)
    assert metrics["opponent"]["ko_probability"] == {"numerator": 1, "denominator": 1}
    assert all(row["ordered_terminal_hit"] is not None for row in transitions)

    _snapshot, _d0, _own, _opponent, _set, surviving = _graph_pair(power=25, opponent_hp=100)
    surviving_ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=surviving)
    assert any(row["second_action"]["state"] == "outcome_graph" for row in surviving_ledger["validated_order_graphs"][0]["terminal_transitions"])


def test_variable_graph_pair_ledger_rejects_forged_low_hp_type_evidence():
    _snapshot, _d0, _own, _opponent, _set, pair = _graph_pair(
        power=500,
        own_hp=33,
        opponent_hp=1,
        own_ability="overgrow",
    )
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger.get("reason")

    forged = deepcopy(pair)
    edge = forged["order_graphs"][0]["first_action_graph"]["terminal_leaf_edges"][0]
    evidence = edge["ordered_hit"]["low_hp_type_ability"]
    edge["ordered_hit"]["low_hp_type_ability"] = {
        **evidence,
        "threshold": {**evidence["threshold"], "active": False},
    }

    rejected = normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "variable_graph_low_hp_type_ability_consequence_invalid"


def test_response_profile_consumes_graph_derived_metrics_without_changing_profile_contract():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=1)
    # Response-profile completeness and multi-response dispatch are covered by
    # the profile owner tests.  This graph-specific contract needs one exact
    # surviving response coordinate, not the same expensive variable graph
    # twice with different ordinary opponent moves.
    response_set = {
        **response_set,
        "actions": tuple(
            row if row["action_id"] == "opponent_attack:tackle" else {
                **row, "selectability": "not_selectable",
                "usability": {"status": "known_unusable", "reason": "disabled"},
            }
            for row in response_set["actions"]
        ),
        "selectable_response_action_ids": ("opponent_attack:tackle",),
    }
    own = _variable_action(d0, "bullet-seed", power=500)
    orders = {row["action_id"]: _order(d0, own, row, "own_first") for row in response_set["actions"] if row["action_id"] in response_set["selectable_response_action_ids"]}
    profile = materialize_detached_opponent_response_profile(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own,
        response_set_authority=response_set, action_order_authorities=orders,
    )
    assert profile["status"] == "evaluable", profile.get("reason")
    assert all(row["pair"]["schema_version"] == "detached-variable-two-to-five-hit-graph-immediate-move-pair-v1" for row in profile["response_entries"])
    assert all(row["descriptive_metrics"]["status"] == "resolved" for row in profile["response_entries"])


def test_population_bomb_graph_normalizes_and_projects_exact_metrics():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=1)
    own = _population_bomb_action(d0, power=500, accuracy=50)
    opponent = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    pair = materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=_order(d0, own, opponent, "own_first"))
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert metrics["status"] == "resolved", metrics.get("reason")
    assert metrics["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_response_profile_consumes_population_bomb_graph_metrics():
    _state, snapshot, d0, _own, response_set, _orders = _inputs(opponent_hp=1)
    response_set = {**response_set, "actions": tuple(row if row["action_id"] == "opponent_attack:tackle" else {**row, "selectability": "not_selectable", "usability": {"status": "known_unusable"}} for row in response_set["actions"]), "selectable_response_action_ids": ("opponent_attack:tackle",)}
    own = _population_bomb_action(d0, power=500, accuracy=50)
    opponent = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    profile = materialize_detached_opponent_response_profile(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, response_set_authority=response_set, action_order_authorities={opponent["action_id"]: _order(d0, own, opponent, "own_first")})
    assert profile["status"] == "evaluable", profile.get("reason")
    assert profile["response_entries"][0]["descriptive_metrics"]["status"] == "resolved"
