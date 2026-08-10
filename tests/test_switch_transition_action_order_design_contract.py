"""Design-only contract for manual-switch precedence and detached transition state."""
from __future__ import annotations

from copy import deepcopy


def _switch_vs_move(*, move_priority=0, speed_context="present", trick_room="active"):
    """Fixture-only action-class policy; deliberately never calls move order mechanics."""
    return {
        "self_action_kind": "switch",
        "opponent_action_kind": "move",
        "action_order_supportability": "complete",
        "order_result": "self_switch_first",
        "action_class_precedence": "manual_switch_before_move",
        "move_priority_considered": False,
        "speed_context": "not_applicable",
        "trick_room": "not_applicable",
        "switch_execution_status": "executed",
        "opponent_execution_status": "queued",
        "move_priority_fixture": move_priority,
        "source_speed_fixture": speed_context,
        "source_trick_room_fixture": trick_room,
    }


def _transition(*, pre, target, target_scope="selected-pokemon"):
    """Fixture-only detached transition model; no hazards, effects, or damage."""
    if target_scope != "selected-pokemon":
        return {"status": "unsupported_mechanic", "reason": "unsupported_queued_move_target"}
    old = deepcopy(pre["self_roster"][pre["self_active"]])
    incoming = deepcopy(pre["self_roster"][target])
    return {
        "status": "transition_ready",
        "pre_active": pre["self_active"],
        "post_active": target,
        "self_roster": deepcopy(pre["self_roster"]),
        "post_active_pokemon": incoming,
        "old_active_pokemon": old,
        "self_side": deepcopy(pre["self_side"]),
        "field": deepcopy(pre["field"]),
        "queued_move_target": target,
        "target_redirection_supportability": "complete",
        "post_switch_entry_effects": "unsupported_not_applied",
        "outgoing_stat_stage_reset": "unsupported_mechanic",
        "outgoing_volatile_clear": "unsupported_mechanic",
    }


def _pre_state():
    return {
        "self_active": "A",
        "self_roster": {
            "A": {"identity": "A", "current_type": ["fire"], "current_hp": 42, "condition": "burn", "ability": "blaze", "item": "leftovers", "stat_stages": {"attack": 2}},
            "B": {"identity": "B", "current_type": {"knowledge": "unknown"}, "current_hp": {"knowledge": "unknown"}, "condition": "paralysis", "ability": {"knowledge": "unknown"}, "item": {"knowledge": "unknown"}},
        },
        "self_side": {"screens": ["reflect"], "tailwind": "active", "hazards": ["stealth-rock"]},
        "field": {"weather": "rain", "terrain": "electric", "trick_room": "active"},
    }


def test_switch_is_a_distinct_action_class_and_precedes_all_supported_move_priorities():
    for priority in (-1, 0, 1, 4):
        order = _switch_vs_move(move_priority=priority)
        assert order["order_result"] == "self_switch_first"
        assert order["action_class_precedence"] == "manual_switch_before_move"
        assert order["move_priority_considered"] is False
        assert order["speed_context"] == order["trick_room"] == "not_applicable"
    assert "priority" not in {"action_kind": "switch"}


def test_switch_vs_switch_is_explicitly_unsupported_and_switch_preemption_is_not_move_ohko_preemption():
    switch_vs_switch = {"self_action_kind": "switch", "opponent_action_kind": "switch", "action_order_supportability": "unsupported_mechanic", "reason": "opponent_switch_action_not_modeled"}
    order = _switch_vs_move()
    assert switch_vs_switch["action_order_supportability"] == "unsupported_mechanic"
    assert order["switch_execution_status"] == "executed"
    assert order["opponent_execution_status"] == "queued"
    assert "preempted" not in order.values()


def test_detached_transition_replaces_active_identity_but_never_copies_old_pokemon_authority():
    pre = _pre_state()
    result = _transition(pre=pre, target="B")
    assert result["pre_active"] == "A" and result["post_active"] == result["queued_move_target"] == "B"
    assert result["self_roster"]["A"]["identity"] == "A"
    assert result["post_active_pokemon"] == pre["self_roster"]["B"]
    assert result["post_active_pokemon"]["condition"] == "paralysis"
    assert result["post_active_pokemon"]["current_type"] == {"knowledge": "unknown"}
    assert result["post_active_pokemon"].get("stat_stages") is None


def test_side_and_shared_authority_are_preserved_without_applying_entry_effects_or_hazard_hp_changes():
    pre = _pre_state()
    result = _transition(pre=pre, target="B")
    assert result["self_side"] == pre["self_side"]
    assert result["field"] == pre["field"]
    assert result["post_switch_entry_effects"] == "unsupported_not_applied"
    assert result["post_active_pokemon"]["current_hp"] == {"knowledge": "unknown"}


def test_stat_stage_and_volatile_semantics_are_reset_clear_contracts_but_unsupported_until_owned():
    result = _transition(pre=_pre_state(), target="B")
    assert result["outgoing_stat_stage_reset"] == "unsupported_mechanic"
    assert result["outgoing_volatile_clear"] == "unsupported_mechanic"
    assert result["old_active_pokemon"]["stat_stages"] == {"attack": 2}
    assert "volatile_conditions" not in result["post_active_pokemon"]


def test_target_redirection_is_limited_to_supported_opposing_single_target_and_transition_is_detached():
    pre = _pre_state()
    result = _transition(pre=pre, target="B")
    pre["self_roster"]["B"]["condition"] = "sleep"
    result["self_side"]["screens"].append("light-screen")
    assert result["post_active_pokemon"]["condition"] == "paralysis"
    assert pre["self_side"]["screens"] == ["reflect"]
    assert _transition(pre=_pre_state(), target="B", target_scope="all-opponents") == {"status": "unsupported_mechanic", "reason": "unsupported_queued_move_target"}
