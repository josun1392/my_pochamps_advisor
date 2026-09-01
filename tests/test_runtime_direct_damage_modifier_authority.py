"""Unknown-first modifier ownership through runtime D0 into the native evaluator."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CURRENT_ABILITY_SOURCE, CURRENT_ITEM_SOURCE, CURRENT_SIDE_CONDITIONS_SOURCE,
    CURRENT_BATTLE_FORMAT_SOURCE, CURRENT_TERRAIN_SOURCE, CURRENT_WEATHER_SOURCE, LifecycleConfirmationBoundary,
    USER_TRUST,
)
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_strategy_d0 import build_runtime_d0_native_damage_context, freeze_runtime_normal_formula_predictive_input, freeze_runtime_strategy_d0


def _base() -> dict:
    state = create_unknown_bootstrap_battle_state("modifiers", "attacker", "target")["state"]
    for side, types in (("self", ["water"]), ("opponent", ["fire"])):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=120, fainted=False, current_level=50, condition="none", stat_stages={key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed")})
        pokemon["current_level_provenance"] = {"event_kind": "current_level_observed", "trust": USER_TRUST, "turn_number": 1}
        pokemon["current_type"] = types
        pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": USER_TRUST, "turn_number": 1}
        pokemon["current_final_stats"] = {stat: {"value": 90 + index, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": USER_TRUST, "turn_number": 1}} for index, stat in enumerate(("attack", "defense", "special-attack", "special-defense", "speed"))}
    state["field"]["weather"] = "none"
    state["field"]["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": USER_TRUST, "turn_number": 1}
    return state


def _owner(state: dict, side: str) -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _confirmations(state: dict, *, attacker_item: dict, target_item: dict, terrain: str = "none", sides: tuple[list[str], list[str]] = ([], []), attacker_ability: str = "adaptability", target_ability: str = "ice-scales") -> list[dict]:
    owners = {side: {"slot_index": 0, "pokemon_id": _owner(state, side)["pokemon_id"]} for side in ("self", "opponent")}
    boundary = LifecycleConfirmationBoundary(state["session_id"], owners)
    values = [
        boundary.confirm(event_kind="current_item_observed", payload=attacker_item, session_id=state["session_id"], source=CURRENT_ITEM_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="attacker", turn_number=2),
        boundary.confirm(event_kind="current_item_observed", payload=target_item, session_id=state["session_id"], source=CURRENT_ITEM_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=0, pokemon_id="target", turn_number=2),
        boundary.confirm(event_kind="current_ability_observed", payload={"ability": attacker_ability}, session_id=state["session_id"], source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="attacker", turn_number=2),
        boundary.confirm(event_kind="current_ability_observed", payload={"ability": target_ability}, session_id=state["session_id"], source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=0, pokemon_id="target", turn_number=2),
        boundary.confirm(event_kind="current_terrain_observed", payload={"terrain": terrain}, session_id=state["session_id"], source=CURRENT_TERRAIN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=2),
        boundary.confirm(event_kind="current_side_conditions_observed", payload={"side_conditions": sides[0]}, session_id=state["session_id"], source=CURRENT_SIDE_CONDITIONS_SOURCE, trust=USER_TRUST, confirmed=True, side="self", turn_number=2),
        boundary.confirm(event_kind="current_side_conditions_observed", payload={"side_conditions": sides[1]}, session_id=state["session_id"], source=CURRENT_SIDE_CONDITIONS_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", turn_number=2),
    ]
    assert all(value["status"] == "confirmed" for value in values)
    return [value["observation"] for value in values]


def _apply(state: dict, events: list[dict]) -> dict:
    projected = project_atomic_transition(state, build_replay_plan(state, events), state["session_id"])
    assert projected["status"] == "ready_with_projected_state"
    return projected["projected_state"]


def _context(state: dict, move_metadata: dict | None = None) -> dict:
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    metadata = move_metadata or {"move_id": "water-gun", "category": "special", "power": 40, "type": "water"}
    return build_runtime_d0_native_damage_context(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata=metadata)


def test_known_item_absence_and_complete_modifier_authority_reach_native_water_gun() -> None:
    state = _apply(_base(), _confirmations(_base(), attacker_item={"status": "known", "item": "life-orb"}, target_item={"status": "known_absent"}))
    context = _context(state)
    authority = context["modifier_authority"]
    assert context["status"] == "resolved"
    assert context["native_evaluation"]["exact_damage_rolls"] and len(context["native_evaluation"]["exact_damage_rolls"]) == 16
    assert "item_life_orb_boost" in context["native_evaluation"]["applied_damage_modifiers"]
    assert authority["attacker"]["item"]["status"] == "known"
    assert authority["defender"]["item"]["status"] == "known_absent"
    assert authority["field"]["terrain"] == {"status": "known", "value": "none"}
    assert authority["defender"]["side_conditions"] == {"status": "known", "value": []}


def test_pressure_is_catalogued_as_known_neutral_for_both_direct_damage_roles() -> None:
    base = _base()
    state = _apply(
        base,
        _confirmations(
            base, attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"},
            attacker_ability="pressure", target_ability="pressure",
        ),
    )
    context = _context(state)
    assert context["status"] == "resolved"
    assert context["native_evaluation"]["applied_damage_modifiers"] == []


def test_runtime_d0_move_flag_damage_abilities_reach_native_direct_modifier_path() -> None:
    cases = [
        ("tough-claws", {"move_id": "dragon-claw", "category": "physical", "power": 80, "type": "dragon"}, "ability_tough_claws_boost"),
        ("reckless", {"move_id": "double-edge", "category": "physical", "power": 120, "type": "normal"}, "ability_reckless_boost"),
        ("punk-rock", {"move_id": "boomburst", "category": "special", "power": 140, "type": "normal"}, "ability_punk_rock_sound_boost"),
        ("sheer-force", {"move_id": "iron-head", "category": "physical", "power": 80, "type": "steel"}, "ability_sheer_force_secondary_boost"),
    ]
    for ability, metadata, tag in cases:
        base = _base()
        state = _apply(
            base,
            _confirmations(
                base, attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"},
                attacker_ability=ability, target_ability="pressure",
            ),
        )
        context = _context(state, metadata)
        assert context["status"] == "resolved", context
        assert tag in context["native_evaluation"]["applied_damage_modifiers"]
        assert context["modifier_authority"]["attacker"]["ability"]["value"] == ability


def test_unknown_item_and_partial_side_knowledge_stay_incomplete() -> None:
    state = _apply(_base(), _confirmations(_base(), attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"})[:-1])
    context = _context(state)
    assert context["status"] == "incomplete"
    assert "target_side_conditions" in context["missing_authority"]
    unknown_item = _apply(_base(), _confirmations(_base(), attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"})[2:])
    assert "attacker.item" in _context(unknown_item)["missing_authority"]


def test_exact_side_condition_is_bound_and_source_mutation_is_detached() -> None:
    state = _apply(_base(), _confirmations(_base(), attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"}, sides=([], ["light-screen"])))
    context = _context(state)
    # Screen presence reaches the native evaluator.  It correctly remains
    # incomplete because runtime D0 does not yet own battle-format authority.
    assert context["status"] == "incomplete"
    assert "battle_format" in context["missing_authority"]
    state["opponent_side"]["side_conditions"].clear()
    assert context["modifier_authority"]["defender"]["side_conditions"]["value"] == ["light-screen"]


def test_session_bound_singles_format_resolves_screen_and_unknown_format_does_not() -> None:
    events = _confirmations(_base(), attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"}, sides=([], ["light-screen"]))
    state = _apply(_base(), events)
    assert "battle_format" in _context(state)["missing_authority"]
    boundary = LifecycleConfirmationBoundary(state["session_id"], {side: {"slot_index": 0, "pokemon_id": _owner(state, side)["pokemon_id"]} for side in ("self", "opponent")})
    known = boundary.confirm(event_kind="current_battle_format_observed", payload={"battle_format": "singles"}, session_id=state["session_id"], source=CURRENT_BATTLE_FORMAT_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=3)
    resolved = _context(_apply(state, [known["observation"]]))
    assert resolved["status"] == "resolved"
    assert "light_screen_reduction" in resolved["native_evaluation"]["applied_damage_modifiers"]
    assert resolved["modifier_authority"]["field"]["battle_format"] == {"status": "known", "value": "singles"}


def test_doubles_format_is_exact_but_keeps_native_direct_evaluator_boundary() -> None:
    state = _apply(_base(), _confirmations(_base(), attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"}, sides=([], ["light-screen"])))
    boundary = LifecycleConfirmationBoundary(state["session_id"], {side: {"slot_index": 0, "pokemon_id": _owner(state, side)["pokemon_id"]} for side in ("self", "opponent")})
    observed = boundary.confirm(event_kind="current_battle_format_observed", payload={"battle_format": "doubles"}, session_id=state["session_id"], source=CURRENT_BATTLE_FORMAT_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=3)
    context = _context(_apply(state, [observed["observation"]]))
    assert context["status"] == "incomplete"
    assert context["reason"] == "battle_format"


def test_conflicting_format_is_rejected_and_new_session_is_unknown() -> None:
    state = _base()
    boundary = LifecycleConfirmationBoundary(state["session_id"], {side: {"slot_index": 0, "pokemon_id": _owner(state, side)["pokemon_id"]} for side in ("self", "opponent")})
    singles = boundary.confirm(event_kind="current_battle_format_observed", payload={"battle_format": "singles"}, session_id=state["session_id"], source=CURRENT_BATTLE_FORMAT_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=2)
    state = _apply(state, [singles["observation"]])
    doubles = boundary.confirm(event_kind="current_battle_format_observed", payload={"battle_format": "doubles"}, session_id=state["session_id"], source=CURRENT_BATTLE_FORMAT_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=3)
    assert project_atomic_transition(state, build_replay_plan(state, [doubles["observation"]]), state["session_id"])["status"] == "blocked_by_semantic_conflict"
    assert create_unknown_bootstrap_battle_state("new-session", "attacker", "target")["state"]["field"]["battle_format"] == {"knowledge": "unknown"}


def test_generic_runtime_input_binds_move_metadata_and_rejects_foreign_context() -> None:
    state = _apply(_base(), _confirmations(_base(), attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"}))
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    metadata = {"move_id": "surf", "category": "special", "power": 90, "type": "water"}
    native = build_runtime_d0_native_damage_context(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata=metadata)
    generic = freeze_runtime_normal_formula_predictive_input(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata=metadata, native_damage_context=native)
    assert generic["status"] == "resolved" and generic["move_id"] == "surf"
    assert generic["post_hit_authority"]["attacker_item_known"] is True
    assert generic["post_hit_authority"]["attacker_hp"]["current_hp"] == 100
    assert generic["post_hit_authority"]["attacker_hp"]["max_hp"] == 120
    assert freeze_runtime_normal_formula_predictive_input(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata={**metadata, "move_id": "tackle"}, native_damage_context=native)["reason"] == "runtime_native_damage_context_d0_mismatch"
