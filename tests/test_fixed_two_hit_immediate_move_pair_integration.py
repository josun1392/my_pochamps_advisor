"""Integration coverage for fixed-two-hit leaves in immediate move pairs."""
from __future__ import annotations

from copy import deepcopy

from llm.advisor_exact_action_pair_descriptive_metrics import (
    project_exact_immediate_action_pair_descriptive_metrics,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_immediate_move_vs_move_action_pair import (
    materialize_immediate_move_vs_move_action_pair,
)
from tests.test_detached_opponent_response_profile import _equal_speed_order, _inputs, _metadata, _owner


def _fixed_two_action(d0, *, move_id: str) -> dict:
    metadata = deepcopy(_metadata(move_id))
    metadata["metadata"].update({"min_hits": 2, "max_hits": 2})
    metadata.update({
        "candidate_id": f"attack:{move_id}", "active_attacker": d0["decision_owner"],
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": d0["decision_owner"],
    })
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": metadata}


def _order(d0, own_action, opponent_action, value: str) -> dict:
    return {
        "status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": value,
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
        "own_action_id": own_action["action_id"], "opponent_action_id": opponent_action["action_id"],
        "own_actor": d0["active_owners"]["self"], "opponent_actor": d0["active_owners"]["opponent"],
    }


def test_double_hit_own_first_survival_reuses_pair_ledger_and_metrics_without_losing_hit_identity():
    state, snapshot, d0, _own_action, response_set, _orders = _inputs(opponent_hp=100)
    own_action = _fixed_two_action(d0, move_id="double-hit")
    opponent_action = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    before = deepcopy(snapshot)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action,
        action_order_authority=_order(d0, own_action, opponent_action, "own_first"),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all(row["second_action"]["state"] == "executed" for row in pair["terminal_branches"])
    assert all(len(row["first_action_leaf"]["ordered_hits"]) == 2 for row in pair["terminal_branches"])
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all(len(row["first_action"]["ordered_hits"]) == 2 for row in ledger["terminal_leaves"])
    assert project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)["status"] == "resolved"
    assert snapshot == before and state["opponent_side"]["pokemon"][0]["current_hp"] == 100


def test_double_kick_own_first_ko_cancels_and_opponent_first_fixed_two_hit_is_actor_neutral():
    _state, snapshot, d0, _own_action, response_set, _orders = _inputs(own_hp=1, opponent_hp=1)
    own_action = _fixed_two_action(d0, move_id="double-kick")
    opponent_action = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    cancelled = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action,
        action_order_authority=_order(d0, own_action, opponent_action, "own_first"),
    )
    assert cancelled["status"] == "evaluable", cancelled.get("reason")
    assert all(row["second_action"]["state"] == "cancelled_due_to_faint" for row in cancelled["terminal_branches"])

    opponent_fixed = deepcopy(opponent_action)
    opponent_fixed["action_id"] = "opponent_attack:double-hit"; opponent_fixed["move_id"] = "double-hit"
    opponent_fixed["metadata_authority"] = _metadata("double-hit")
    opponent_fixed["metadata_authority"]["metadata"].update({"min_hits": 2, "max_hits": 2})
    own_tackle = _fixed_two_action(d0, move_id="double-kick")
    opponent_first = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_tackle, opponent_action=opponent_fixed,
        action_order_authority=_order(d0, own_tackle, opponent_fixed, "opponent_first"),
    )
    assert opponent_first["status"] == "evaluable", opponent_first.get("reason")
    assert opponent_first["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all(len(row["first_action_leaf"]["ordered_hits"]) == 1 for row in opponent_first["terminal_branches"])
    assert all(row["second_action"]["state"] == "cancelled_due_to_faint" for row in opponent_first["terminal_branches"])


def test_fixed_two_hit_composes_the_existing_exact_equal_speed_order_branches():
    _state, snapshot, d0, _own_action, response_set, _orders = _inputs(equal_speed=True, opponent_hp=1)
    own_action = _fixed_two_action(d0, move_id="double-kick")
    opponent_action = next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:tackle")
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action,
        action_order_authority=_equal_speed_order(d0, own_action, opponent_action),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert {row["action_order"] for row in pair["terminal_branches"]} == {"own_first", "opponent_first"}
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
