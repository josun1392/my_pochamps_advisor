from copy import deepcopy

from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state() -> dict:
    state = create_unknown_bootstrap_battle_state("intermediate", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["stat_stages"] = {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0, "accuracy": 0, "evasion": 0}
        pokemon["condition"] = None
        pokemon["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
    return state


def _d0(state: dict) -> dict:
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    owner = {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": state["self_side"]["pokemon"][0]["pokemon_id"]}
    return freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)


def _leaf(d0: dict, *, own_hp: int = 90, target_hp: int = 40, damage: int = 60, secondary=None, deterministic=None) -> dict:
    bound = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "attacker": d0["active_owners"]["self"], "target": d0["active_owners"]["opponent"], "move_id": "shadow-ball"}
    return {"leaf_id": "hit/damage_roll:0", "candidate_id": "attack:shadow-ball", "action_type": "attack", "branch_path": ({"branch": "hit", "conditional_probability": {"numerator": 1, "denominator": 1}},), "probability": {"numerator": 1, "denominator": 16}, "hit_state": "hit", "critical_state": "non_critical", "damage_roll": {"roll_index": 0, "random_factor_percent": 85, "damage": damage}, "consequences": {"damage": damage, "own_final_hp": own_hp, "target_final_hp": target_hp, "target_ko": target_hp == 0, "self_fainted": own_hp == 0, "secondary": secondary, "deterministic_stage_effect": deterministic}, "provenance": bound}


def test_exact_hp_and_faint_state_are_leaf_local_and_detached() -> None:
    state = _state(); d0 = _d0(state); leaf = _leaf(d0, own_hp=0, target_hp=0)
    result = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf)
    assert result["status"] == "resolved"
    assert result["active"]["self"]["hypothetical_fainted"]["value"] is True
    assert result["active"]["opponent"]["hypothetical_hp"]["value"] == 0
    assert result["second_action_compatibility"]["faint_cancellation"] == {"status": "resolved", "actor_can_act": False, "target_can_act": False, "rule": "second_selected_action_cancelled_if_its_actor_is_fainted"}
    assert state["self_side"]["pokemon"][0].get("current_hp") != 0


def test_roll_identity_can_materialize_distinct_exact_hp_states_without_merging() -> None:
    d0 = _d0(_state())
    leaves = [_leaf(d0, target_hp=100 - index, damage=index) for index in range(16)]
    states = [materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf) for leaf in leaves]
    assert [row["active"]["opponent"]["hypothetical_hp"]["value"] for row in states] == list(range(100, 84, -1))
    assert [row["first_action"]["probability"] for row in states] == [{"numerator": 1, "denominator": 16}] * 16


def test_stage_and_condition_effects_overlay_only_their_effect_leaf() -> None:
    d0 = _d0(_state())
    metal = _leaf(d0, secondary={"branch": "effect", "hypothetical_stage_effect": {"owner": "self", "stat": "attack", "previous_stage": 0, "delta": 1, "resulting_stage": 1}})
    shadow = _leaf(d0, secondary={"branch": "effect", "hypothetical_stage_effect": {"owner": "target", "stat": "special-defense", "previous_stage": 0, "delta": -1, "resulting_stage": -1}})
    bolt = _leaf(d0, secondary={"branch": "effect", "hypothetical_target_condition": {"resulting_condition": "paralysis"}})
    assert materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=metal)["active"]["self"]["hypothetical_stages"]["attack"]["value"] == 1
    assert materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=shadow)["active"]["opponent"]["hypothetical_stages"]["special-defense"]["value"] == -1
    assert materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=bolt)["active"]["opponent"]["hypothetical_condition"]["condition"] == "paralysis"


def test_deterministic_stage_effect_is_matched_to_exact_roll_and_no_effect_keeps_current_state() -> None:
    d0 = _d0(_state())
    deterministic = {"branches": ({"raw_damage": 60, "effects": ({"owner": "target", "stat": "special-defense", "previous_stage": 0, "delta": -2, "resulting_stage": -2},)},)}
    result = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=_leaf(d0, deterministic=deterministic))
    assert result["active"]["opponent"]["hypothetical_stages"]["special-defense"]["value"] == -2
    no_effect = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=_leaf(d0, secondary={"branch": "no_effect"}))
    assert no_effect["active"]["self"]["hypothetical_stages"]["attack"]["value"] == 0
    assert no_effect["active"]["opponent"]["hypothetical_condition"]["status"] == "known_none"


def test_missing_exact_hp_is_incomplete_and_stale_leaf_binding_rejects() -> None:
    d0 = _d0(_state()); missing = _leaf(d0); missing["consequences"]["own_final_hp"] = None
    assert materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=missing)["status"] == "incomplete"
    stale = _leaf(d0); stale["provenance"]["source_runtime_fingerprint"] = "stale"
    assert materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=stale)["status"] == "rejected"
