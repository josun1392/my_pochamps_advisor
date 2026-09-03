from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import project_atomic_transition


def _state():
    state = create_unknown_bootstrap_battle_state("supreme", "king", "foe")["state"]
    for side in ("self", "opponent"):
        active = state[f"{side}_side"]["pokemon"][0]
        active.update(current_hp=100, max_hp=100, fainted=False, current_ability="pressure")
        active["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "source_sequence": 1}
    bench = deepcopy(state["self_side"]["pokemon"][0]); bench["pokemon_id"] = "ally"
    state["self_side"]["pokemon"][1] = bench
    return state


def _step(oid, seq, effect, **values):
    return {"observation_id": oid, "observation_sequence": seq, "planned_effect": effect, "trust": "user_confirmed_observation", **values}


def _plan(*steps): return {"session_id": "supreme", "status": "planned", "conflicts": [], "ordered_steps": list(steps)}
def _owner(slot=0, pokemon="king"): return {"side": "self", "slot_index": slot, "pokemon_id": pokemon}


def _initial(seq=1, count=0): return _step("initial", seq, "initialize_supreme_overlord_active_entry", **_owner(), entry_token="initial:king", cumulative_allied_faint_count=count)
def _faint(oid, hp_seq, faint_seq, slot, pokemon): return (_step(f"{oid}-hp", hp_seq, "apply_exact_hp_transition", **_owner(slot, pokemon), hp_before=100, hp_after=0), _step(oid, faint_seq, "mark_fainted", **_owner(slot, pokemon)))


def test_initialized_counter_increments_once_per_confirmed_faint_and_is_side_bound():
    state = _state(); state["self_side"]["pokemon"][0]["current_ability"] = "supreme-overlord"
    first = _faint("ally-faint", 2, 3, 1, "ally")
    projected = project_atomic_transition(state, _plan(_initial(), *first), "supreme")
    assert projected["status"] == "ready_with_projected_state"
    history = projected["projected_state"]["supreme_overlord_faint_history_context"]
    assert history["side_counts"] == {"self": 1, "opponent": 0}
    assert project_atomic_transition(projected["projected_state"], _plan(first[1]), "supreme")["status"] == "blocked_by_semantic_conflict"


def test_entry_snapshot_is_frozen_and_reentry_captures_new_count():
    state = _state(); state["self_side"]["pokemon"][0]["current_ability"] = "supreme-overlord"
    state["self_side"]["pokemon"][1]["current_ability"] = "pressure"
    initial = project_atomic_transition(state, _plan(_initial()), "supreme")["projected_state"]
    snapshot = initial["supreme_overlord_entry_snapshots"][0]
    assert snapshot["raw_allied_faint_count"] == snapshot["fallen_allies_count"] == 0
    switched = project_atomic_transition(initial, _plan(_step("out", 2, "switch_active", side="self", switch_out_slot_index=0, switch_out_pokemon_id="king", switch_in_slot_index=1, switch_in_pokemon_id="ally")), "supreme")["projected_state"]
    assert switched["supreme_overlord_entry_snapshots"][0]["active"] is False
    fainted = project_atomic_transition(switched, _plan(*_faint("king-faint", 3, 4, 0, "king")), "supreme")["projected_state"]
    # A fresh test battle state permits the formerly active holder to re-enter
    # only after modelling an unfainted holder; use the surviving ally count
    # from history as the entry fact for a second Supreme Overlord activation.
    fresh = _state(); fresh["self_side"]["pokemon"][0]["current_ability"] = "pressure"; fresh["self_side"]["pokemon"][1]["current_ability"] = "supreme-overlord"
    seeded = project_atomic_transition(fresh, _plan(_step("seed", 1, "initialize_supreme_overlord_active_entry", **_owner(), entry_token="initial:king", cumulative_allied_faint_count=1)), "supreme")["projected_state"]
    reentered = project_atomic_transition(seeded, _plan(_step("enter", 2, "switch_active", side="self", switch_out_slot_index=0, switch_out_pokemon_id="king", switch_in_slot_index=1, switch_in_pokemon_id="ally")), "supreme")
    assert reentered["status"] == "ready_with_projected_state"
    active = [row for row in reentered["projected_state"]["supreme_overlord_entry_snapshots"] if row["active"]]
    assert len(active) == 1 and active[0]["owner"]["pokemon_id"] == "ally" and active[0]["raw_allied_faint_count"] == 1


def test_unknown_history_never_becomes_zero_and_caps_only_snapshot_value():
    state = _state(); state["self_side"]["pokemon"][0]["current_ability"] = "supreme-overlord"
    # Switching without explicit initialization cannot manufacture a snapshot.
    state["self_side"]["pokemon"][1]["current_ability"] = "supreme-overlord"
    unknown = project_atomic_transition(state, _plan(_step("switch", 1, "switch_active", side="self", switch_out_slot_index=0, switch_out_pokemon_id="king", switch_in_slot_index=1, switch_in_pokemon_id="ally")), "supreme")
    assert unknown["status"] == "ready_with_projected_state"
    assert "supreme_overlord_entry_snapshots" not in unknown["projected_state"]
    capped = project_atomic_transition(state, _plan(_initial(count=7)), "supreme")
    snapshot = capped["projected_state"]["supreme_overlord_entry_snapshots"][0]
    assert snapshot["raw_allied_faint_count"] == 7 and snapshot["fallen_allies_count"] == 5
