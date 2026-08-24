"""Runtime-native damage context stays D0-bound and unknown-first."""

from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    freeze_runtime_strategy_d0,
    freeze_runtime_water_gun_predictive_input,
)


def _state(session: str = "runtime-native") -> dict:
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    for side, pokemon_id, types in (("self", "attacker", ["water"]), ("opponent", "target", ["fire"])):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=120, fainted=False, current_level=50, condition="none", stat_stages={key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed")})
        pokemon["current_level_provenance"] = {"event_kind": "current_level_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_type"] = types
        pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_final_stats"] = {
            stat: {"value": 90 + index, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": "user_confirmed_observation", "turn_number": 1}}
            for index, stat in enumerate(("attack", "defense", "special-attack", "special-defense", "speed"))
        }
    state["field"].update(weather="none", terrain="none")
    state["field"]["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    return state


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _owner(state: dict, side: str = "self") -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _context(state: dict):
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    return snapshot, d0, build_runtime_d0_native_damage_context(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"),
        move_metadata={"move_id": "water-gun", "category": "special", "power": 40, "type": "water"},
    )


def test_native_context_reuses_native_shapes_and_preserves_stage_unmodified_stats() -> None:
    state = _state(); snapshot, d0, context = _context(state)
    assert context["status"] == "incomplete"  # item/ability authority is deliberately still unknown.
    assert context["session_id"] == d0["session_id"]
    assert context["source_runtime_fingerprint"] == snapshot["state_fingerprint"]
    assert context["source_branch_fingerprint"] == d0["strategy_preview_fingerprint"]
    provenance = context["stat_provenance"]
    assert provenance["attacker"]["final_stats"]["value"]["special-attack"] == 92
    assert provenance["defender"]["final_stats"]["value"]["special-defense"] == 93
    assert provenance["attacker"]["final_stats"]["value"]["hp"] == 120
    current = context["snapshot_damage_input"]["battle_context"]["current_state"]
    assert current["stat_stage_context"]["current_stages"]
    assert current["field_state_context"]["current_field"]["side_effects"] == "unknown"
    assert context["native_evaluation"]["status"] == "insufficient_context"
    assert "attacker.item" in context["missing_authority"]


def test_native_context_rejects_stale_or_foreign_identity_and_is_detached() -> None:
    state = _state(); snapshot, d0, context = _context(state)
    advanced = deepcopy(state); advanced["last_applied_observation_sequence"] = 1
    stale = build_runtime_d0_native_damage_context(
        strategy_d0=d0, runtime_snapshot=_snapshot(advanced), attacker=_owner(state), target=_owner(state, "opponent"),
        move_metadata={"move_id": "water-gun", "category": "special", "power": 40, "type": "water"},
    )
    assert stale == {"status": "rejected", "schema_version": "runtime-d0-native-damage-context-v1", "reason": "runtime_fingerprint_changed"}
    foreign = build_runtime_d0_native_damage_context(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state),
        move_metadata={"move_id": "water-gun", "category": "special", "power": 40, "type": "water"},
    )
    assert foreign["status"] == "rejected"
    state["self_side"]["pokemon"][0]["current_final_stats"]["special-attack"]["value"] = 999
    assert context["stat_provenance"]["attacker"]["final_stats"]["value"]["special-attack"] == 92


def test_water_gun_boundary_accepts_only_matching_resolved_native_context() -> None:
    state = _state(); snapshot, d0, context = _context(state)
    water = freeze_runtime_water_gun_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"),
        move_id="water-gun", native_damage_context=context,
    )
    assert water["status"] == "incomplete"
    assert "attacker.item" in water["missing_authority"]
    mixed = deepcopy(context); mixed["source_branch_fingerprint"] = "foreign"
    rejected_context = freeze_runtime_water_gun_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"),
        move_id="water-gun", native_damage_context=mixed,
    )
    assert "runtime_native_damage_context_d0_mismatch" in rejected_context["missing_authority"]
