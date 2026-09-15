"""Production persistent-effect confirmations route losslessly to the reducer."""
from copy import deepcopy

import pytest

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    PERSISTENT_EFFECT_SOURCE, USER_TRUST, LifecycleConfirmationBoundary,
)
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_replay_policy import build_replay_plan


def _state():
    state = create_unknown_bootstrap_battle_state("persistent-observations", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        active = state[f"{side}_side"]["pokemon"][0]
        active.update(current_hp=80, max_hp=100, fainted=False)
        bench = deepcopy(active)
        bench["pokemon_id"] = f"{side}-b"
        state[f"{side}_side"]["pokemon"][1] = bench
    return state


def _boundary(state):
    return LifecycleConfirmationBoundary(state["session_id"], {side: {"slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]} for side in ("self", "opponent")})


def _confirm(boundary, state, kind, payload, *, side="self", observation_id=None, turn=1, **changes):
    values = dict(
        event_kind=kind, payload=payload, session_id=state["session_id"], source=PERSISTENT_EFFECT_SOURCE,
        trust=USER_TRUST, confirmed=True, side=side, slot_index=0,
        pokemon_id=state[f"{side}_side"]["pokemon"][0]["pokemon_id"], observation_id=observation_id,
        turn_number=turn,
    )
    values.update(changes)
    return boundary.confirm(**values)


def _project(state, observations):
    plan = build_replay_plan(state, observations)
    assert plan["status"] == "planned", plan
    result = project_atomic_transition(state, plan, state["session_id"])
    assert result["status"] == "ready_with_projected_state", result
    return plan, result["projected_state"]


def _row(state, family, side="self"):
    return next(row for row in state["current_persistent_effect_context"]["rows"] if row["family"] == family and row["owner"]["side"] == side)


@pytest.mark.parametrize(("kind", "payload"), [
    ("current_aqua_ring_state_observed", {"persistent_state": "active"}),
    ("current_aqua_ring_state_observed", {"persistent_state": "inactive"}),
    ("current_ingrain_state_observed", {"persistent_state": "active"}),
    ("current_ingrain_state_observed", {"persistent_state": "inactive"}),
    ("current_leech_seed_state_observed", {"persistent_state": "active", "source_side": "opponent", "source_slot_index": 0}),
    ("current_leech_seed_state_observed", {"persistent_state": "inactive"}),
])
def test_lifecycle_confirms_exact_production_persistent_effect_payloads(kind, payload):
    state = _state()
    result = _confirm(_boundary(state), state, kind, payload)
    assert result["status"] == "confirmed"
    assert result["observation"]["payload"] == payload
    assert result["production_readiness"] == "production_ready"


@pytest.mark.parametrize(("kind", "payload"), [
    ("current_aqua_ring_state_observed", {"persistent_state": "unknown"}),
    ("current_aqua_ring_state_observed", {"persistent_state": "active", "source_side": "opponent", "source_slot_index": 0}),
    ("current_ingrain_state_observed", {"persistent_state": "active", "source_side": "opponent", "source_slot_index": 0}),
    ("current_leech_seed_state_observed", {"persistent_state": "inactive", "source_side": "opponent", "source_slot_index": 0}),
    ("current_leech_seed_state_observed", {"persistent_state": "active"}),
    ("current_leech_seed_state_observed", {"persistent_state": "active", "source_side": "self", "source_slot_index": 0}),
    ("current_leech_seed_state_observed", {"persistent_state": "active", "source_side": "opponent", "source_slot_index": -1}),
])
def test_lifecycle_rejects_invalid_persistent_effect_payloads(kind, payload):
    state = _state()
    assert _confirm(_boundary(state), state, kind, payload)["status"] == "invalid_provenance"


def test_lifecycle_rejects_stale_owner_turn_and_provenance_mismatches():
    state = _state(); boundary = _boundary(state); base = dict(kind="current_aqua_ring_state_observed", payload={"persistent_state": "active"})
    assert _confirm(boundary, state, **base, session_id="stale")["status"] == "stale_session"
    assert _confirm(boundary, state, **base, pokemon_id="wrong")["status"] == "invalid_provenance"
    assert _confirm(boundary, state, **base, turn=None)["status"] == "invalid_provenance"
    assert _confirm(boundary, state, **base, turn=0)["status"] == "invalid_provenance"
    assert _confirm(boundary, state, **base, source="wrong")["status"] == "invalid_provenance"
    assert _confirm(boundary, state, **base, trust="wrong")["status"] == "invalid_provenance"


@pytest.mark.parametrize(("kind", "family", "payload"), [
    ("current_aqua_ring_state_observed", "aqua_ring", {"persistent_state": "active"}),
    ("current_ingrain_state_observed", "ingrain", {"persistent_state": "active"}),
    ("current_leech_seed_state_observed", "leech_seed", {"persistent_state": "active", "source_side": "opponent", "source_slot_index": 0}),
])
def test_replay_maps_each_persistent_observation_and_preserves_leech_source(kind, family, payload):
    state = _state(); result = _confirm(_boundary(state), state, kind, payload)
    plan = build_replay_plan(state, [result["observation"]])
    step = plan["ordered_steps"][0]
    assert step["planned_effect"] == f"set_current_{family}_state"
    assert step["persistent_state"] == "active"
    if family == "leech_seed": assert (step["source_side"], step["source_slot_index"]) == ("opponent", 0)


def test_inactive_leech_replay_has_no_fabricated_source_fields():
    state = _state(); observation = _confirm(_boundary(state), state, "current_leech_seed_state_observed", {"persistent_state": "inactive"})["observation"]
    step = build_replay_plan(state, [observation])["ordered_steps"][0]
    assert step["persistent_state"] == "inactive" and "source_side" not in step and "source_slot_index" not in step


def test_end_to_end_unknown_vs_explicit_inactive_and_all_effect_rows():
    state = _state()
    assert "current_persistent_effect_context" not in state
    boundary = _boundary(state); collection = ObservationCollection(state["session_id"])
    confirmations = [
        _confirm(boundary, state, "current_aqua_ring_state_observed", {"persistent_state": "inactive"}, observation_id="a", turn=1),
        _confirm(boundary, state, "current_ingrain_state_observed", {"persistent_state": "active"}, observation_id="i", turn=2),
        _confirm(boundary, state, "current_leech_seed_state_observed", {"persistent_state": "active", "source_side": "opponent", "source_slot_index": 0}, observation_id="l", turn=3),
    ]
    assert collection.add_confirmation_results(confirmations)["status"] == "added"
    _, projected = _project(state, collection.snapshot()["ordered_observations"])
    assert _row(projected, "aqua_ring")["state"] == "inactive"
    assert _row(projected, "ingrain")["state"] == "active"
    assert _row(projected, "leech_seed")["source_slot"] == {"session_id": state["session_id"], "side": "opponent", "slot_index": 0}
    assert "current_persistent_effect_context" not in _state()


def test_reducer_fails_closed_for_invalid_source_slot_and_bench_target():
    state = _state(); boundary = _boundary(state)
    observation = _confirm(boundary, state, "current_leech_seed_state_observed", {"persistent_state": "active", "source_side": "opponent", "source_slot_index": 99})["observation"]
    plan = build_replay_plan(state, [observation])
    assert project_atomic_transition(state, plan, state["session_id"])["status"] == "blocked_by_semantic_conflict"
    assert _confirm(boundary, state, "current_aqua_ring_state_observed", {"persistent_state": "active"}, slot_index=1, pokemon_id="self-b")["status"] == "invalid_provenance"


def test_duplicates_ordered_updates_owner_isolation_and_switch_lifecycle():
    state = _state(); boundary = _boundary(state); collection = ObservationCollection(state["session_id"])
    aqua = _confirm(boundary, state, "current_aqua_ring_state_observed", {"persistent_state": "active"}, observation_id="a", turn=1)
    assert _confirm(boundary, state, "current_aqua_ring_state_observed", {"persistent_state": "active"}, observation_id="a", turn=1)["status"] == "duplicate"
    assert _confirm(boundary, state, "current_aqua_ring_state_observed", {"persistent_state": "inactive"}, observation_id="a", turn=1)["status"] == "conflicting_confirmation"
    ingrain = _confirm(boundary, state, "current_ingrain_state_observed", {"persistent_state": "active"}, observation_id="i", turn=2)
    opponent = _confirm(boundary, state, "current_aqua_ring_state_observed", {"persistent_state": "active"}, side="opponent", observation_id="o", turn=3)
    assert collection.add_confirmation_results([aqua, ingrain, opponent])["status"] == "added"
    _, projected = _project(state, collection.snapshot()["ordered_observations"])
    update = _confirm(boundary, state, "current_aqua_ring_state_observed", {"persistent_state": "active"}, observation_id="a2", turn=4)
    _, updated = _project(projected, [update["observation"]])
    assert _row(updated, "aqua_ring")["state"] == "active" and _row(updated, "ingrain")["state"] == "active" and _row(updated, "aqua_ring", "opponent")["state"] == "active"
    switch = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{"observation_id": "switch", "observation_sequence": 5, "planned_effect": "switch_active", "trust": USER_TRUST, "side": "self", "switch_out_slot_index": 0, "switch_out_pokemon_id": "self-a", "switch_in_slot_index": 1, "switch_in_pokemon_id": "self-b"}]}
    switched = project_atomic_transition(updated, switch, state["session_id"])["projected_state"]
    assert _row(switched, "aqua_ring")["state"] == "inactive" and _row(switched, "ingrain")["state"] == "inactive" and _row(switched, "aqua_ring", "opponent")["state"] == "active"


def test_observation_applied_leech_seed_retires_on_target_switch_and_survives_source_switch():
    state = _state(); boundary = _boundary(state)
    seed = _confirm(boundary, state, "current_leech_seed_state_observed", {"persistent_state": "active", "source_side": "opponent", "source_slot_index": 0})["observation"]
    _, seeded = _project(state, [seed])
    def switch(side, oid):
        roster = seeded[f"{side}_side"]["pokemon"]
        return {"session_id": seeded["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{"observation_id": oid, "observation_sequence": 2, "planned_effect": "switch_active", "trust": USER_TRUST, "side": side, "switch_out_slot_index": 0, "switch_out_pokemon_id": roster[0]["pokemon_id"], "switch_in_slot_index": 1, "switch_in_pokemon_id": roster[1]["pokemon_id"]}]}
    target_switched = project_atomic_transition(seeded, switch("self", "target-switch"), seeded["session_id"])["projected_state"]
    assert _row(target_switched, "leech_seed")["state"] == "inactive" and "source_slot" not in _row(target_switched, "leech_seed")
    source_switched = project_atomic_transition(seeded, switch("opponent", "source-switch"), seeded["session_id"])["projected_state"]
    assert _row(source_switched, "leech_seed")["state"] == "active" and _row(source_switched, "leech_seed")["source_slot"] == {"session_id": seeded["session_id"], "side": "opponent", "slot_index": 0}
