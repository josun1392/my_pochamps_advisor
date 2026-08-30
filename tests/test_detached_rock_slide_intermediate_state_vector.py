from copy import deepcopy

from llm.advisor_detached_rock_slide_intermediate_state_vector import (
    build_detached_rock_slide_vector_predictive_builder_view,
    extract_detached_rock_slide_pending_actor_scalar_view,
    freeze_detached_rock_slide_frozen_scope_graph_consumer_adapter,
    freeze_detached_rock_slide_execution_scope_consumer_view,
    materialize_detached_rock_slide_intermediate_state_vector,
)
from llm.advisor_detached_rock_slide_multi_recipient_predictive_graph_materialization import (
    materialize_detached_rock_slide_multi_recipient_predictive_graph,
)
from llm.advisor_rock_slide_multi_recipient_action_outcome_ledger import (
    graph_terminal_rows,
    normalize_rock_slide_multi_recipient_action_outcome_ledger,
)
from tests.test_detached_rock_slide_multi_recipient_predictive_graph_materialization import _inputs


def _base(*, target_hp=100):
    _state, snapshot, d0, action, scope = _inputs(target_hp=target_hp)
    return snapshot, d0, action, scope


def _overlay(d0, owner, hp):
    stages = {stat: {"status": "known", "value": 0} for stat in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}
    return {
        "status": "resolved", "schema_version": "detached-predictive-intermediate-state-v1",
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]),
        "first_action": {"leaf_id": "source:leaf", "provenance": {"target": deepcopy(owner)}},
        "active": {owner["side"]: {"owner": deepcopy(owner), "hypothetical_hp": {"status": "known", "value": hp}, "hypothetical_fainted": {"status": "known", "value": hp == 0}, "hypothetical_stages": stages, "hypothetical_condition": {"status": "known_none"}}},
    }


def test_frozen_vector_preserves_exact_recipient_order_and_scope_consumer_view():
    snapshot, d0, _action, scope = _base()
    vector = materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0, runtime_snapshot=snapshot, execution_scope_authority=scope)
    assert vector["status"] == "resolved", vector.get("reason")
    assert [row["owner"]["pokemon_id"] for row in vector["ordered_recipient_states"]] == ["opponent-a", "opponent-b"]
    assert [row["hp"] for row in vector["ordered_recipient_states"]] == [100, 100]
    consumer = freeze_detached_rock_slide_execution_scope_consumer_view(vector=vector)
    assert consumer["status"] == "resolved"
    assert consumer["frozen_execution_scope_authority"] == scope


def test_terminal_path_and_scalar_overlay_change_only_exact_recipient_and_keep_fainted_row():
    snapshot, d0, action, scope = _base(target_hp=1)
    graph = materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_scope_authority=scope)
    ledger = normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=graph)
    path = next(row for row in graph_terminal_rows(ledger=ledger) if all(outcome["fainted"] for outcome in row["ordered_recipient_outcomes"]))
    vector = materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0, runtime_snapshot=snapshot, execution_scope_authority=scope, source_terminal_path=path)
    assert vector["status"] == "resolved", vector.get("reason")
    assert [row["fainted"] for row in vector["ordered_recipient_states"]] == [True, True]
    assert len(vector["ordered_recipient_states"]) == 2

    snapshot, d0, _action, scope = _base()
    first, second = scope["recipients"]
    vector = materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0, runtime_snapshot=snapshot, execution_scope_authority=scope, scalar_intermediate_overlay=_overlay(d0, first["owner"], 0))
    assert vector["status"] == "resolved", vector.get("reason")
    assert vector["ordered_recipient_states"][0]["hp"] == 0
    assert vector["ordered_recipient_states"][0]["fainted"] is True
    assert vector["ordered_recipient_states"][1]["hp"] == 100
    assert vector["ordered_recipient_states"][1]["owner"] == second["owner"]
    view = extract_detached_rock_slide_pending_actor_scalar_view(vector=vector, pending_actor=first["owner"], pending_target=d0["decision_owner"])
    assert view["status"] == "resolved" and view["actor_can_act"] is False


def test_surviving_pending_actor_extracts_and_stale_duplicate_or_source_mismatch_fail_closed():
    snapshot, d0, _action, scope = _base()
    vector = materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0, runtime_snapshot=snapshot, execution_scope_authority=scope)
    view = extract_detached_rock_slide_pending_actor_scalar_view(vector=vector, pending_actor=scope["recipients"][0]["owner"], pending_target=d0["decision_owner"])
    assert view["status"] == "resolved" and view["actor_can_act"] is True

    stale = deepcopy(scope); stale["source_runtime_fingerprint"] = "stale"
    assert materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0, runtime_snapshot=snapshot, execution_scope_authority=stale)["status"] == "rejected"
    duplicate = deepcopy(scope); duplicate["recipients"] = (duplicate["recipients"][0], duplicate["recipients"][0])
    assert materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0, runtime_snapshot=snapshot, execution_scope_authority=duplicate)["status"] == "rejected"
    bad_path = {"terminal_edge_id": "foreign", "source_path_reference": {}, "ordered_recipient_outcomes": ()}
    assert materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0, runtime_snapshot=snapshot, execution_scope_authority=scope, source_terminal_path=bad_path)["status"] == "rejected"


def test_private_builder_and_frozen_scope_graph_adapter_are_non_current_and_exact():
    snapshot, d0, action, scope = _base()
    vector = materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0, runtime_snapshot=snapshot, execution_scope_authority=scope)
    recipient = scope["recipients"][0]["owner"]
    builder = build_detached_rock_slide_vector_predictive_builder_view(vector=vector, runtime_snapshot=snapshot, pending_actor=recipient, pending_target=d0["decision_owner"])
    assert builder["status"] == "resolved" and builder["hypothetical"] is True and builder["current_authority"] is False
    assert builder["actor_state"]["hp"] == vector["ordered_recipient_states"][0]["hp"]
    adapter = freeze_detached_rock_slide_frozen_scope_graph_consumer_adapter(vector=vector, runtime_snapshot=snapshot)
    assert adapter["status"] == "resolved" and adapter["frozen_execution_scope_authority"] == scope
    graph = materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_scope_authority=scope, frozen_scope_consumer_adapter=adapter)
    assert graph["status"] == "evaluable", graph.get("reason")
    bad = deepcopy(adapter); bad["ordered_recipient_states"] = (bad["ordered_recipient_states"][1], bad["ordered_recipient_states"][0])
    assert materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_scope_authority=scope, frozen_scope_consumer_adapter=bad)["status"] == "rejected"
