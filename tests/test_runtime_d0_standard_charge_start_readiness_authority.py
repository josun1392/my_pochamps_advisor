from __future__ import annotations

from copy import deepcopy

import pytest

import llm.advisor_runtime_d0_standard_charge_start_readiness_authority as readiness_module
from core.charge_move_repository import ChargeMoveRepository
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import (
    freeze_runtime_d0_standard_charge_start_readiness_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_action_order_authority import (
    _actions,
    _owner,
    _snapshot,
    _state,
)


SUPPORTED = ("sky-attack", "razor-wind", "freeze-shock", "ice-burn")


def _inputs(
    move_id: str,
    *,
    item: str | None | object = None,
    item_mode: str = "absent",
    actor_ability: str | None = "static",
    target_ability: str | None = "static",
    magic_room: str | None = "inactive",
):
    state = _state()
    actor_raw = state["self_side"]["pokemon"][0]
    target_raw = state["opponent_side"]["pokemon"][0]

    if item_mode == "unknown":
        actor_raw["known_item"] = {"knowledge": "unknown"}
        actor_raw["known_item_provenance"] = None
    elif item_mode == "absent":
        actor_raw["known_item"] = None
        actor_raw["known_item_provenance"] = {
            "event_kind": "current_item_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "status": "known_absent",
        }
    elif item_mode == "known":
        assert isinstance(item, str)
        actor_raw["known_item"] = item
        actor_raw["known_item_provenance"] = {
            "event_kind": "current_item_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "status": "known",
        }
    else:
        raise AssertionError(item_mode)

    if actor_ability is None:
        actor_raw["current_ability"] = {"knowledge": "unknown"}
        actor_raw["current_ability_provenance"] = None
    else:
        actor_raw["current_ability"] = actor_ability
        actor_raw["current_ability_provenance"] = {
            "event_kind": "current_ability_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
        }
    if target_ability is None:
        target_raw["current_ability"] = {"knowledge": "unknown"}
        target_raw["current_ability_provenance"] = None
    else:
        target_raw["current_ability"] = target_ability
        target_raw["current_ability_provenance"] = {
            "event_kind": "current_ability_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
        }

    if magic_room is None:
        state["field"]["magic_room_status"] = {"knowledge": "unknown"}
        state["field"].pop("magic_room_status_provenance", None)
    else:
        state["field"]["magic_room_status"] = magic_room
        state["field"]["magic_room_status_provenance"] = {
            "event_kind": "magic_room_field_observed",
            "trust": "user_confirmed_observation",
            "source_observation_id": "charge-readiness-magic-room",
            "source_sequence": 1,
        }

    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    action, _opponent = _actions(d0, own_move=move_id)
    actor = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    result = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
    )
    return state, snapshot, d0, action, actor, target, result


@pytest.mark.parametrize("move_id", SUPPORTED)
def test_supported_standard_charge_moves_resolve_with_exact_no_item(move_id):
    _state0, _snapshot0, _d0, _action, _actor, _target, result = _inputs(
        move_id, item_mode="absent",
    )
    assert result["status"] == "resolved"
    assert result["outcome"] == "charge_start_ready"
    assert result["move_id"] == move_id
    assert result["next_semantic_phase"] == "charge_turn_start"
    assert result["action_execution_confirmed"] is False
    assert result["immediate_damage_execution_grant"] is False
    assert result["charge_turn_state_materialized"] is False
    assert result["pp_consumed"] is False
    assert result["current_item_authority"]["status"] == "known_absent"
    assert result["power_herb_applicability_state"]["status"] == "not_required"


@pytest.mark.parametrize("move_id", ("razor-wind", "ice-burn"))
def test_known_non_power_herb_item_resolves_without_ability_or_field_knowledge(move_id):
    _state0, _snapshot0, _d0, _action, _actor, _target, result = _inputs(
        move_id,
        item="leftovers",
        item_mode="known",
        actor_ability=None,
        target_ability=None,
        magic_room=None,
    )
    assert result["status"] == "resolved"
    assert result["outcome"] == "charge_start_ready"
    assert result["current_item_authority"]["item_id"] == "leftovers"
    assert result["power_herb_applicability_state"] == {
        "status": "not_required",
        "reason": "current_item_not_power_herb",
        "item_id": "leftovers",
    }
    assert "power_herb_applicability_authority" not in result


def test_unknown_item_is_incomplete():
    *_rest, result = _inputs("sky-attack", item_mode="unknown")
    assert result["status"] == "incomplete"
    assert result["reason"] == "standard_charge_current_item_unknown"
    assert result["action_execution_confirmed"] is False
    assert result["immediate_damage_execution_grant"] is False


def test_active_power_herb_is_strict_same_turn_skip_readiness():
    *_rest, result = _inputs(
        "sky-attack",
        item="power-herb",
        item_mode="known",
        actor_ability="static",
        target_ability="static",
        magic_room="inactive",
    )
    assert result["status"] == "resolved"
    assert result["outcome"] == "power_herb_charge_skip_ready"
    assert result["next_semantic_phase"] == "current_turn_charge_skip_terminal_execution"
    assert result["power_herb_applicability_state"]["status"] == "active"
    assert result["power_herb_applicability_authority"]["item_effects_active"] is True
    assert result["action_execution_confirmed"] is False
    assert result["immediate_damage_execution_grant"] is False
    assert result["charge_turn_state_materialized"] is False
    assert "item_after" not in result


def test_power_herb_magic_room_suppression_allows_normal_charge_readiness():
    *_rest, result = _inputs(
        "razor-wind",
        item="power-herb",
        item_mode="known",
        actor_ability=None,
        target_ability=None,
        magic_room="active",
    )
    assert result["status"] == "resolved"
    assert result["outcome"] == "charge_start_ready"
    assert result["power_herb_applicability_state"]["status"] == "suppressed"
    assert result["power_herb_applicability_authority"]["reason"] == "magic_room_item_effects_suppressed"


def test_power_herb_unsuppressed_klutz_allows_normal_charge_readiness():
    *_rest, result = _inputs(
        "freeze-shock",
        item="power-herb",
        item_mode="known",
        actor_ability="klutz",
        target_ability="static",
        magic_room="inactive",
    )
    assert result["status"] == "resolved"
    assert result["outcome"] == "charge_start_ready"
    assert result["power_herb_applicability_state"]["status"] == "suppressed"
    assert result["power_herb_applicability_authority"]["reason"] == "klutz_item_effects_suppressed"


def test_power_herb_klutz_suppressed_by_neutralizing_gas_enables_skip_readiness():
    *_rest, result = _inputs(
        "ice-burn",
        item="power-herb",
        item_mode="known",
        actor_ability="klutz",
        target_ability="neutralizing-gas",
        magic_room="inactive",
    )
    assert result["status"] == "resolved"
    assert result["outcome"] == "power_herb_charge_skip_ready"
    assert result["power_herb_applicability_state"]["status"] == "active"
    assert result["power_herb_applicability_authority"]["reason"] == "klutz_suppressed_by_neutralizing_gas"
    assert result["power_herb_applicability_authority"]["item_effects_active"] is True


def test_geomancy_status_terminal_charge_family_is_admitted_narrowly():
    *_rest, result = _inputs("geomancy", item_mode="absent")
    assert result["status"] == "resolved", result
    assert result["outcome"] == "charge_start_ready"
    canonical = result["canonical_charge_lifecycle_authority"]
    assert canonical["lifecycle_family"] == "charge_then_status_terminal"
    assert canonical["execution_model"] == "other_two_turn"
    assert canonical["terminal_effect_class"] == "self_stat_change"
    assert canonical["semi_invulnerability_class"] is None
    assert canonical["protection_bypass_later_execution"] is False


def test_continuation_target_locator_is_position_only():
    *_prefix, target, result = _inputs("sky-attack", item_mode="absent")
    assert result["source_target_owner"] == target
    assert result["continuation_target_locator"] == {
        "session_id": target["session_id"],
        "side": target["side"],
        "slot_index": target["slot_index"],
    }
    assert "pokemon_id" not in result["continuation_target_locator"]


def test_forged_known_absent_item_provenance_rejects():
    state = _state()
    raw = state["self_side"]["pokemon"][0]
    raw["known_item"] = None
    raw["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": "known",
    }
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    action, _ = _actions(d0, own_move="sky-attack")
    result = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=d0["active_owners"]["self"],
        target=d0["active_owners"]["opponent"],
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "standard_charge_known_absent_item_provenance_invalid"


def test_stale_foreign_actor_target_and_action_metadata_mismatches_reject():
    state, snapshot, d0, action, actor, target, result = _inputs(
        "sky-attack", item_mode="absent",
    )
    assert result["status"] == "resolved"

    stale_state = deepcopy(state)
    stale_state["self_side"]["pokemon"][0]["current_hp"] = 99
    stale_snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": stale_state["session_id"],
        "state": stale_state,
        "state_fingerprint": state_fingerprint(stale_state),
    }
    stale = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=stale_snapshot,
        action=action,
        actor=actor,
        target=target,
    )
    assert stale["status"] == "rejected"

    foreign_actor = dict(actor)
    foreign_actor["pokemon_id"] = "foreign"
    assert freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=foreign_actor,
        target=target,
    )["status"] == "rejected"

    foreign_target = dict(target)
    foreign_target["pokemon_id"] = "foreign"
    assert freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=foreign_target,
    )["status"] == "rejected"

    forged_action = deepcopy(action)
    forged_action["move_metadata_authority"]["move_id"] = "razor-wind"
    assert freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=forged_action,
        actor=actor,
        target=target,
    )["status"] == "rejected"


def test_missing_move_metadata_and_explicit_target_mismatch_reject():
    _state0, snapshot, d0, action, actor, target, _result0 = _inputs(
        "sky-attack", item_mode="absent",
    )
    missing = deepcopy(action)
    missing.pop("move_metadata_authority")
    assert freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=missing,
        actor=actor,
        target=target,
    )["status"] == "rejected"

    wrong_target = deepcopy(action)
    wrong_target["target_owner"] = actor
    assert freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=wrong_target,
        actor=actor,
        target=target,
    )["status"] == "rejected"


def test_forged_canonical_lifecycle_metadata_rejects(monkeypatch):
    original = readiness_module.resolve_canonical_charge_move_lifecycle

    def forged(move_id):
        value = original(move_id)
        value["canonical_recognition_grants_immediate_execution"] = True
        return value

    monkeypatch.setattr(
        readiness_module,
        "resolve_canonical_charge_move_lifecycle",
        forged,
    )
    *_rest, result = _inputs("sky-attack", item_mode="absent")
    assert result["status"] == "rejected"
    assert result["reason"] == "standard_charge_canonical_lifecycle_mismatch"


def test_power_herb_applicability_binding_mismatch_rejects(monkeypatch):
    original = readiness_module.resolve_runtime_d0_held_item_effect_applicability_authority

    def forged(**kwargs):
        value = original(**kwargs)
        value["holder"] = dict(value["holder"])
        value["holder"]["pokemon_id"] = "forged"
        return value

    monkeypatch.setattr(
        readiness_module,
        "resolve_runtime_d0_held_item_effect_applicability_authority",
        forged,
    )
    *_rest, result = _inputs(
        "sky-attack",
        item="power-herb",
        item_mode="known",
        actor_ability="static",
        target_ability="static",
        magic_room="inactive",
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "power_herb_applicability_holder_mismatch"


def test_runtime_snapshot_and_d0_are_immutable():
    state = _state()
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    action, _ = _actions(d0, own_move="sky-attack")
    before_snapshot = deepcopy(snapshot)
    before_d0 = deepcopy(d0)
    result = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=d0["active_owners"]["self"],
        target=d0["active_owners"]["opponent"],
    )
    assert result["status"] == "resolved"
    assert snapshot == before_snapshot
    assert d0 == before_d0


def test_repository_guard_still_denies_immediate_execution_for_supported_family():
    repo = ChargeMoveRepository()
    for move_id in SUPPORTED:
        guard = repo.immediate_execution_guard(move_id)
        assert guard is not None
        assert guard["reason"] == "two_turn_execution_unrepresented"
        assert guard["canonical_recognition_grants_immediate_execution"] is False
