from copy import deepcopy

from llm.advisor_runtime_d0_held_item_effect_applicability_authority import (
    resolve_runtime_d0_held_item_effect_applicability_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_action_order_authority import _owner, _snapshot, _state


def _inputs(*, item="choice-scarf", holder_ability="static", other_ability="static", magic_room="inactive", include_field_provenance=True):
    state = _state()
    holder = state["self_side"]["pokemon"][0]
    other = state["opponent_side"]["pokemon"][0]
    holder["known_item"] = item
    holder["known_item_provenance"]["status"] = "known"
    holder["current_ability"] = holder_ability
    other["current_ability"] = other_ability
    if include_field_provenance:
        state["field"]["magic_room_status"] = magic_room
        state["field"]["magic_room_status_provenance"] = {
            "event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation",
            "source_observation_id": "test-magic-room", "source_sequence": 1,
        }
    else:
        state["field"]["magic_room_status"] = {"knowledge": "unknown"}
        state["field"].pop("magic_room_status_provenance", None)
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return state, snapshot, d0, _owner(state, "self")


def test_held_item_effect_authority_composes_magic_room_and_klutz_exactly():
    _state0, snapshot, d0, holder = _inputs(magic_room="active")
    magic = resolve_runtime_d0_held_item_effect_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, holder=holder)
    assert (magic["status"], magic["outcome"], magic["item_effects_active"]) == ("resolved", "suppressed", False)

    _state0, snapshot, d0, holder = _inputs(holder_ability="klutz")
    klutz = resolve_runtime_d0_held_item_effect_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, holder=holder)
    assert (klutz["status"], klutz["outcome"], klutz["item_effects_active"]) == ("resolved", "suppressed", False)

    _state0, snapshot, d0, holder = _inputs(holder_ability="klutz", other_ability="neutralizing-gas")
    gas = resolve_runtime_d0_held_item_effect_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, holder=holder)
    assert (gas["status"], gas["outcome"], gas["item_effects_active"]) == ("resolved", "active", True)


def test_held_item_effect_authority_fails_closed_for_missing_or_stale_material_evidence():
    _state0, snapshot, d0, holder = _inputs(include_field_provenance=False)
    missing = resolve_runtime_d0_held_item_effect_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, holder=holder)
    assert (missing["status"], missing["reason"]) == ("incomplete", "held_item_suppression_field_authority_unknown")

    state, _snapshot0, d0, holder = _inputs()
    stale = deepcopy(state)
    stale["self_side"]["pokemon"][0]["current_hp"] = 99
    result = resolve_runtime_d0_held_item_effect_applicability_authority(strategy_d0=d0, runtime_snapshot=_snapshot(stale), holder=holder)
    assert result["status"] == "rejected"
