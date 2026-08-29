from copy import deepcopy

from llm.advisor_detached_rock_slide_multi_recipient_predictive_graph_materialization import materialize_detached_rock_slide_multi_recipient_predictive_graph
from llm.advisor_lifecycle_confirmation import DOUBLES_ACTIVE_TOPOLOGY_SOURCE, SELECTED_ACTION_TARGETING_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_doubles_action_target_set_authority import freeze_runtime_d0_doubles_action_target_set_authority
from llm.advisor_runtime_d0_multi_recipient_action_execution_scope_authority import freeze_runtime_d0_multi_recipient_action_execution_scope_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_substitute import update_substitute_state_context
from tests.test_immediate_attack_vs_opponent_switch_action_pair import _state as exact_state
from tests.test_runtime_d0_multi_recipient_action_execution_scope_authority import _state as scope_state


def _owner(state, side, slot=0):
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _inputs(*, accuracy=100, target_hp=100):
    state = scope_state()
    template = exact_state()["self_side"]["pokemon"][0]
    for side in ("self", "opponent"):
        roster = state[f"{side}_side"]["pokemon"]
        roster[1] = deepcopy(roster[0]); roster[1]["pokemon_id"] = f"{side}-b"
        for row in roster.values():
            identity = row["pokemon_id"]
            row.update(deepcopy(template)); row["pokemon_id"] = identity
    state["field"].update(weather="none", terrain="none", battle_format="doubles")
    state["field"]["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"]["terrain_provenance"] = {"event_kind": "current_terrain_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"]["battle_format_provenance"] = {"event_kind": "current_battle_format_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    for side in ("self", "opponent"):
        roster = state[f"{side}_side"]["pokemon"]
        roster[1]["current_hp"] = target_hp if side == "opponent" else 100
        roster[1]["max_hp"] = max(target_hp, 100) if side == "opponent" else 100
        roster[1]["fainted"] = False
        state[f"{side}_side"]["side_conditions"] = []
        state[f"{side}_side"]["side_conditions_provenance"] = {"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    for row in state["opponent_side"]["pokemon"].values():
        row.update(current_hp=target_hp, max_hp=max(target_hp, 100), fainted=False)
    for side in ("self", "opponent"):
        for slot in (0, 1):
            state["substitute_state_context"] = update_substitute_state_context(context=state.get("substitute_state_context"), session_id=state["session_id"], owner=_owner(state, side, slot), state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1")
    boundary = LifecycleConfirmationBoundary(state["session_id"], {side: _owner(state, side) for side in ("self", "opponent")})
    topology = boundary.confirm(event_kind="doubles_active_topology_observed", payload={"active_owners": [{"side": side, "active_slot_index": slot, "pokemon_id": _owner(state, side, slot)["pokemon_id"], "active": True} for side in ("self", "opponent") for slot in (0, 1)]}, session_id=state["session_id"], source=DOUBLES_ACTIVE_TOPOLOGY_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=1)["observation"]
    targeting = boundary.confirm(event_kind="selected_action_targeting_observed", payload={"decision_point": "turn:1", "action_id": "attack:rock-slide", "move_id": "rock-slide", "selected_target": None}, session_id=state["session_id"], source=SELECTED_ACTION_TARGETING_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id=state["self_side"]["pokemon"][0]["pokemon_id"], turn_number=1)["observation"]
    projected = project_atomic_transition(state, build_replay_plan(state, [topology, targeting]), state["session_id"])
    assert projected["status"] == "ready_with_projected_state"
    state = projected["projected_state"]
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    assert d0["status"] == "resolved", d0
    metadata = {"move_id": "rock-slide", "category": "physical", "power": 75, "type": "rock", "accuracy": accuracy, "priority": 0, "target": "all-opponents"}
    move = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": "attack:rock-slide", "move_id": "rock-slide", "metadata": metadata, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "active_attacker": deepcopy(d0["decision_owner"])}
    action = {"action_id": "attack:rock-slide", "action_type": "attack", "identity": "rock-slide", "move_metadata_authority": move}
    target_set = freeze_runtime_d0_doubles_action_target_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, acting_owner=_owner(state, "self"), decision_point="turn:1")
    scope = freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, decision_point="turn:1", target_set_authority=target_set)
    return state, snapshot, d0, action, scope


def test_rock_slide_graph_keeps_ordered_recipient_local_branches_and_exact_mass():
    state, snapshot, d0, action, scope = _inputs(accuracy=100)
    before = deepcopy(snapshot)
    graph = materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_scope_authority=scope)
    assert graph["status"] == "evaluable", graph.get("reason")
    assert graph["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert graph["spread_damage_modifier_authority"]["numerator"] == 3
    first = [edge for edge in graph["terminal_leaf_edges"] if edge["from_node_id"].startswith("recipient:0/")]
    assert first and {edge["recipient_outcome"]["recipient_index"] for edge in first} == {1}
    assert {edge["recipient_outcome"]["critical_state"] for edge in first if edge["recipient_outcome"]["outcome"] == "hit"} == {"non_critical", "critical"}
    assert all(edge["recipient_outcome"]["raw_damage"] <= edge["recipient_outcome"]["raw_pre_spread_damage"] for edge in first if edge["recipient_outcome"]["outcome"] == "hit")
    second = [edge for edge in graph["terminal_leaf_edges"] if edge["recipient_outcome"]["recipient_index"] == 2]
    assert second and {edge["recipient_outcome"]["damage_roll"]["roll_index"] for edge in second if edge["recipient_outcome"]["outcome"] == "hit"} == set(range(16))
    assert snapshot == before and state["opponent_side"]["pokemon"][0]["current_hp"] == 100


def test_recipient_local_miss_advances_and_early_ko_does_not_remove_later_recipient():
    _state, snapshot, d0, action, scope = _inputs(accuracy=50, target_hp=1)
    graph = materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_scope_authority=scope)
    assert graph["status"] == "evaluable", graph.get("reason")
    first_miss = next(edge for edge in graph["terminal_leaf_edges"] if edge["recipient_outcome"]["recipient_index"] == 1 and edge["recipient_outcome"]["outcome"] == "miss")
    assert first_miss["to_node_id"]
    assert any(edge["from_node_id"] == first_miss["to_node_id"] and edge["recipient_outcome"]["recipient_index"] == 2 for edge in graph["terminal_leaf_edges"])
    assert any(edge["recipient_outcome"]["recipient_index"] == 1 and edge["recipient_outcome"]["fainted"] for edge in graph["terminal_leaf_edges"])
    assert all(len(edge["terminal_consequences"]["ordered_recipient_outcomes"]) == 2 for edge in graph["terminal_leaf_edges"] if edge["terminal"])


def test_scope_mismatch_and_stale_d0_fail_closed():
    _state, snapshot, d0, action, scope = _inputs()
    bad = deepcopy(scope); bad["damage_roll_uncertainty_scope"] = "action_shared"
    assert materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0, runtime_snapshot=snapshot, action=action, execution_scope_authority=bad)["status"] == "rejected"
    stale = deepcopy(snapshot); stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 99; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0, runtime_snapshot=stale, action=action, execution_scope_authority=scope)["status"] == "rejected"
