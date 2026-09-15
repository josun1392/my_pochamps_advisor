"""Reducer-owned current persistent-effect context lifecycle."""
from copy import deepcopy

import pytest

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import project_atomic_transition, validate_battle_state_unknown_markers


def _state():
    state = create_unknown_bootstrap_battle_state("persistent-context", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        active = state[f"{side}_side"]["pokemon"][0]
        active.update(current_hp=70, max_hp=100, fainted=False)
        bench = deepcopy(active)
        bench["pokemon_id"] = f"{side}-b"
        state[f"{side}_side"]["pokemon"][1] = bench
    return state


def _plan(state, steps):
    return {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": steps}


def _effect(state, family, *, side="self", slot=0, persistent_state="active", sequence=1, source_side=None, source_slot=None, trust="user_confirmed_observation", pokemon_id=None):
    event = {"observation_id": f"{family}-{sequence}", "observation_sequence": sequence, "planned_effect": f"set_current_{family}_state", "side": side, "slot_index": slot, "pokemon_id": pokemon_id or state[f"{side}_side"]["pokemon"][slot]["pokemon_id"], "persistent_state": persistent_state, "trust": trust, "turn_number": 1}
    if source_side is not None: event.update(source_side=source_side, source_slot_index=source_slot)
    return event


def _switch(state, side="self", sequence=10):
    roster = state[f"{side}_side"]["pokemon"]
    return {"observation_id": f"switch-{side}-{sequence}", "observation_sequence": sequence, "planned_effect": "switch_active", "trust": "user_confirmed_observation", "side": side, "switch_out_slot_index": 0, "switch_out_pokemon_id": roster[0]["pokemon_id"], "switch_in_slot_index": 1, "switch_in_pokemon_id": roster[1]["pokemon_id"]}


def _apply(state, *steps):
    result = project_atomic_transition(state, _plan(state, list(steps)), state["session_id"])
    assert result["status"] == "ready_with_projected_state", result
    return result["projected_state"]


def _rejected(state, *steps):
    result = project_atomic_transition(state, _plan(state, list(steps)), state["session_id"])
    assert result["status"] in {"blocked_by_semantic_conflict", "invalid_replay_plan"}


def _rows(state):
    return state["current_persistent_effect_context"]["rows"]


def _row(state, family, side="self", slot=0):
    return next(row for row in _rows(state) if row["family"] == family and row["owner"]["side"] == side and row["owner"]["slot_index"] == slot)


def test_absence_and_missing_rows_are_unknown_not_inactive():
    state = _state()
    assert validate_battle_state_unknown_markers(state)
    state = _apply(state, _effect(state, "aqua_ring", persistent_state="inactive"))
    assert _row(state, "aqua_ring")["state"] == "inactive"
    assert not any(row["family"] == "ingrain" for row in _rows(state))


@pytest.mark.parametrize("mutate", [
    lambda context: context.update(schema_version="wrong"),
    lambda context: context.update(session_id="foreign"),
    lambda context: context["rows"].append(deepcopy(context["rows"][0])),
    lambda context: context["rows"][0].update(family="unsupported"),
])
def test_context_validation_rejects_malformed_schema_session_duplicates_and_family(mutate):
    state = _apply(_state(), _effect(_state(), "aqua_ring"))
    mutate(state["current_persistent_effect_context"])
    assert not validate_battle_state_unknown_markers(state)


@pytest.mark.parametrize("family", ["aqua_ring", "ingrain"])
def test_aqua_ring_and_ingrain_active_inactive_and_bench_rejection(family):
    state = _state()
    active = _apply(state, _effect(state, family))
    assert _row(active, family)["state"] == "active"
    inactive = _apply(active, _effect(active, family, persistent_state="inactive", sequence=2))
    assert _row(inactive, family)["state"] == "inactive"
    _rejected(state, _effect(state, family, slot=1))


@pytest.mark.parametrize("changes", [
    {"pokemon_id": "wrong-id"},
    {"slot_index": "not-a-slot"},
    {"persistent_state": "unknown"},
    {"trust": "unconfirmed"},
])
def test_persistent_effect_set_rejects_wrong_identity_malformed_slot_state_and_trust(changes):
    state = _state()
    event = _effect(state, "aqua_ring")
    event.update(changes)
    _rejected(state, event)


@pytest.mark.parametrize("family", ["aqua_ring", "ingrain"])
def test_aqua_ring_and_ingrain_retire_on_owner_switch_but_opposite_survives_and_replacement_inherits_none(family):
    state = _state()
    state = _apply(state, _effect(state, family, side="self"), _effect(state, family, side="opponent", sequence=2))
    switched = _apply(state, _switch(state, "self"))
    assert _row(switched, family, "self", 0)["state"] == "inactive"
    assert _row(switched, family, "self", 0)["retired_reason"] == "switch_out"
    assert _row(switched, family, "opponent", 0)["state"] == "active"
    assert not any(row["family"] == family and row["owner"]["side"] == "self" and row["owner"]["slot_index"] == 1 for row in _rows(switched))


def test_leech_seed_active_source_validation_and_inactive_has_no_source_slot():
    state = _state()
    seeded = _apply(state, _effect(state, "leech_seed", source_side="opponent", source_slot=0))
    row = _row(seeded, "leech_seed")
    assert row["state"] == "active" and row["source_slot"] == {"session_id": state["session_id"], "side": "opponent", "slot_index": 0}
    _rejected(state, _effect(state, "leech_seed", source_side="self", source_slot=0))
    _rejected(state, _effect(state, "leech_seed", source_side="opponent", source_slot=99))
    inactive = _apply(seeded, _effect(seeded, "leech_seed", persistent_state="inactive", sequence=2))
    assert "source_slot" not in _row(inactive, "leech_seed")


def test_leech_seed_target_switch_retires_but_source_switch_preserves_source_slot_and_no_replacement_inheritance():
    state = _state()
    seeded = _apply(state, _effect(state, "leech_seed", source_side="opponent", source_slot=0))
    retired = _apply(seeded, _switch(seeded, "self"))
    assert _row(retired, "leech_seed")["state"] == "inactive"
    assert _row(retired, "leech_seed")["retired_reason"] == "switch_out"
    assert "source_slot" not in _row(retired, "leech_seed")
    assert not any(row["family"] == "leech_seed" and row["owner"]["side"] == "self" and row["owner"]["slot_index"] == 1 for row in _rows(retired))

    retained = _apply(seeded, _switch(seeded, "opponent"))
    row = _row(retained, "leech_seed")
    assert row["state"] == "active" and row["source_slot"] == {"session_id": state["session_id"], "side": "opponent", "slot_index": 0}


def test_upserts_preserve_other_families_owners_and_source_input_and_are_deterministic():
    state = _state()
    source = deepcopy(state)
    first = _apply(state, _effect(state, "aqua_ring"), _effect(state, "ingrain", sequence=2), _effect(state, "leech_seed", side="opponent", sequence=3, source_side="self", source_slot=0))
    assert state == source
    updated = _apply(first, _effect(first, "aqua_ring", persistent_state="inactive", sequence=4))
    assert _row(updated, "aqua_ring")["state"] == "inactive"
    assert _row(updated, "ingrain")["state"] == "active"
    assert _row(updated, "leech_seed", "opponent")["state"] == "active"
    assert _row(updated, "leech_seed", "opponent")["source_slot"]["side"] == "self"
    replay_one = _apply(state, _effect(state, "aqua_ring"))
    replay_two = _apply(state, _effect(state, "aqua_ring"))
    assert replay_one == replay_two
