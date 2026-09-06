"""Pure validation and dry-run projection for the private battle-state-v1 model."""
from copy import deepcopy
from hashlib import sha256
import json
from types import MappingProxyType
from llm.advisor_identity_groundedness import build_groundedness, normalize_groundedness
from llm.advisor_prospective_entry_authority import build_prospective_entry_interactions, build_prospective_offensive_stages, build_prospective_speed_stage
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from llm.advisor_switch_entry_intimidate_authority import build_switch_entry_intimidate_authority
from llm.advisor_switch_entry_download_authority import build_switch_entry_download_authority
from llm.advisor_battle_state_context import normalize_current_type_authority, normalize_user_confirmed_current_ability
from llm.advisor_ice_body_recovery_core import evaluate_ice_body_recovery, evaluate_weather_recovery
from llm.advisor_sandstorm_residual_core import evaluate_sandstorm_residual
from llm.advisor_solar_power_residual_core import evaluate_solar_power_residual
from llm.advisor_substitute import update_substitute_state_context

STATE_MODEL_VERSION = "battle-state-v1"
UNKNOWN_BATTLE_FACT = MappingProxyType({"knowledge": "unknown"})
_TARGETS = {"apply_exact_hp_transition": "pokemon.current_hp", "apply_exact_hp_recovery": "pokemon.current_hp", "set_current_type": "pokemon.current_type", "set_current_condition": "pokemon.condition", "set_pending_status_action_execution": "state.pending_status_action_execution_context", "set_doubles_active_topology": "state.doubles_active_topology_context", "set_selected_action_targeting": "state.selected_action_targeting_context", "set_current_ability": "pokemon.current_ability", "set_current_item": "pokemon.known_item", "set_current_level": "pokemon.current_level", "set_current_final_combat_stat": "pokemon.current_final_stats", "set_current_move_usability": "pokemon.current_move_usability", "set_current_substitute": "state.substitute_state_context", "set_condition": "pokemon.condition", "clear_condition": "pokemon.condition", "set_current_stat_stage": "pokemon.stat_stages", "set_current_crit_volatiles": "pokemon.current_crit_volatiles", "consume_item": "pokemon.known_item", "remove_item": "pokemon.known_item", "set_current_weather": "field.weather", "start_weather": "field.weather", "end_weather": "field.weather", "set_current_terrain": "field.terrain", "start_terrain": "field.terrain", "end_terrain": "field.terrain", "set_current_battle_format": "field.battle_format", "set_current_side_conditions": "side.side_conditions", "start_side_condition": "side.side_conditions", "end_side_condition": "side.side_conditions", "set_observed_tailwind": "side.tailwind_status", "set_observed_trick_room": "field.trick_room_status", "set_same_turn_event": "state.same_turn_event_context", "mark_first_end_of_turn_reached": "state.first_end_of_turn_context", "switch_active": "side.active_slot_index", "mark_fainted": "pokemon.fainted", "record_known_move": "pokemon.known_move_ids", "set_switch_permission": "side.switch_permission_context", "clear_switch_permission": "side.switch_permission_context", "set_ability_applicability": "state.ability_applicability_context", "clear_ability_applicability": "state.ability_applicability_context", "set_ability_interaction": "state.ability_interaction_context", "clear_ability_interaction": "state.ability_interaction_context", "set_identity_groundedness": "state.identity_groundedness_context", "clear_identity_groundedness": "state.identity_groundedness_context", "set_prospective_groundedness": "pokemon.prospective_groundedness_context", "clear_prospective_groundedness": "pokemon.prospective_groundedness_context", "set_prospective_speed_stage": "pokemon.prospective_speed_stage_context", "clear_prospective_speed_stage": "pokemon.prospective_speed_stage_context", "set_prospective_offensive_stages": "pokemon.prospective_offensive_stages_context", "clear_prospective_offensive_stages": "pokemon.prospective_offensive_stages_context", "set_prospective_entry_interactions": "pokemon.prospective_entry_interactions_context", "clear_prospective_entry_interactions": "pokemon.prospective_entry_interactions_context", "set_switch_hazards": "state.switch_hazard_context", "clear_switch_hazards": "state.switch_hazard_context", "set_switch_entry_intimidate": "state.switch_entry_intimidate_authority", "clear_switch_entry_intimidate": "state.switch_entry_intimidate_authority", "set_switch_entry_download": "state.switch_entry_download_authority", "clear_switch_entry_download": "state.switch_entry_download_authority"}
_TARGETS = {**_TARGETS, "set_current_opponent_response_set": "pokemon.current_opponent_response_set", "set_current_opponent_switch_response_set": "side.current_opponent_switch_response_set", "set_current_opponent_switch_target_combat": "pokemon.current_combat"}
_TARGETS["set_mat_block_active_entry_eligibility"] = "state.mat_block_active_entry_eligibility_context"
_TARGETS["set_fake_out_active_entry_eligibility"] = "state.fake_out_active_entry_eligibility_context"
_TARGETS["initialize_supreme_overlord_active_entry"] = "state.supreme_overlord_faint_history_context"
_TARGETS["apply_taunt_restriction"] = "state.current_taunt_restrictions"
_TARGETS["complete_restricted_active_turn"] = "state.current_taunt_restrictions"
_TARGETS["record_executed_move"] = "pokemon.last_executed_move"
_TARGETS["record_previous_action_result"] = "pokemon.previous_action_result"
_TARGETS["initialize_rage_fist_hit_count"] = "pokemon.rage_fist_hit_count"
_TARGETS["record_rage_fist_qualifying_hit"] = "pokemon.rage_fist_hit_count"
_TARGETS["apply_encore_restriction"] = "state.current_encore_restrictions"
_TARGETS["complete_encore_restricted_active_turn"] = "state.current_encore_restrictions"
_TARGETS["apply_disable_restriction"] = "state.current_disable_restrictions"
_TARGETS["complete_disable_restricted_active_turn"] = "state.current_disable_restrictions"


def make_unknown_battle_fact():
    """Return the detached canonical marker for an unconfirmed battle fact."""
    return {"knowledge": "unknown"}


def is_unknown_battle_fact(value):
    return isinstance(value, dict) and value == UNKNOWN_BATTLE_FACT


def validate_battle_state_unknown_markers(state):
    """Reject malformed canonical markers while preserving legacy concrete states."""
    if not isinstance(state, dict):
        return False
    for side_name in ("self_side", "opponent_side"):
        side = state.get(side_name)
        if not isinstance(side, dict):
            return False
        if not _valid_fact_marker(side.get("side_conditions")):
            return False
        if "tailwind_status" in side and not _valid_fact_marker(side.get("tailwind_status")):
            return False
        roster = side.get("pokemon")
        if not isinstance(roster, dict):
            return False
        if side_name == "self_side" and "switch_permission_context" in side and not _valid_switch_permission_context(state, side["switch_permission_context"]):
            return False
        if side_name == "opponent_side" and "current_opponent_switch_response_set" in side and not _valid_current_opponent_switch_response_set(state, side["current_opponent_switch_response_set"]):
            return False
        if any(_contains_marker(value) for key, value in side.items() if key not in {"pokemon", "side_conditions", "side_conditions_provenance", "tailwind_status", "switch_permission_context", "current_opponent_switch_response_set"}):
            return False
        for slot, pokemon in roster.items():
            if not isinstance(pokemon, dict):
                return False
            if any(not _valid_fact_marker(pokemon.get(field)) for field in ("current_level", "current_hp", "max_hp", "fainted", "condition", "known_item")) or not _valid_current_condition_state(pokemon.get("condition"), pokemon.get("condition_provenance")) or not _valid_current_item_state(pokemon.get("known_item"), pokemon.get("known_item_provenance")) or not _valid_current_level_state(pokemon.get("current_level"), pokemon.get("current_level_provenance")) or not _valid_current_final_stats(pokemon.get("current_final_stats")) or not _valid_current_type_state(pokemon.get("current_type"), pokemon.get("current_type_provenance")) or not _valid_current_ability_state(pokemon.get("current_ability"), pokemon.get("current_ability_provenance")) or not _valid_toxic_progression_state(pokemon.get("toxic_progression")):
                return False
            known_moves = pokemon.get("known_move_ids", [])
            if not isinstance(known_moves, list) or len(known_moves) > 4 or any(not _canonical_move_id(move) for move in known_moves) or len(set(known_moves)) != len(known_moves) or not _valid_known_move_provenance(pokemon.get("known_move_ids_provenance"), known_moves):
                return False
            if not _valid_current_move_usability(pokemon.get("current_move_usability"), known_moves) or not _valid_current_opponent_response_set(pokemon.get("current_opponent_response_set"), known_moves) or not _valid_current_crit_volatile_state(pokemon.get("current_crit_volatiles"), pokemon.get("current_crit_volatiles_provenance")):
                return False
            expected_owner = {"session_id": state.get("session_id"), "side": "self" if side_name == "self_side" else "opponent", "slot_index": slot, "pokemon_id": pokemon.get("pokemon_id", pokemon.get("name_en"))} if isinstance(slot, int) and not isinstance(slot, bool) else None
            if not _valid_last_executed_move(state, pokemon.get("last_executed_move"), expected_owner) or not _valid_previous_action_result(state, pokemon.get("previous_action_result"), expected_owner):
                return False
            if any(_contains_marker(value) for key, value in pokemon.items() if key not in {"current_level", "current_level_provenance", "current_final_stats", "current_hp", "max_hp", "fainted", "current_type", "current_type_provenance", "current_ability", "current_ability_provenance", "known_item", "known_item_provenance", "known_move_ids_provenance", "current_move_usability", "toxic_progression", "condition", "condition_provenance", "current_crit_volatiles", "current_crit_volatiles_provenance", "last_executed_move", "previous_action_result", "rage_fist_hit_count"}):
                return False
    field = state.get("field")
    if not isinstance(field, dict) or not all(_valid_fact_marker(field.get(name)) for name in ("weather", "terrain", "battle_format")) or not _valid_current_weather_state(field.get("weather"), field.get("weather_provenance")) or not _valid_current_terrain_state(field.get("terrain"), field.get("terrain_provenance")) or not _valid_current_battle_format_state(field.get("battle_format"), field.get("battle_format_provenance")):
        return False
    trick_room = field.get("trick_room_status", make_unknown_battle_fact())
    trick_room_provenance = field.get("trick_room_status_provenance")
    if not (is_unknown_battle_fact(trick_room) or (isinstance(trick_room, str) and trick_room in {"active", "inactive"})):
        return False
    if isinstance(trick_room, str) and trick_room in {"active", "inactive"} and not isinstance(trick_room_provenance, dict):
        return False
    if any(_contains_marker(value) for key, value in field.items() if key not in {"weather", "weather_provenance", "terrain", "terrain_provenance", "battle_format", "battle_format_provenance", "trick_room_status", "trick_room_status_provenance"}):
        return False
    events = state.get("same_turn_event_context", [])
    if not isinstance(events, list) or any(not _valid_same_turn_event(event, state.get("session_id")) for event in events): return False
    phases = state.get("first_end_of_turn_context", [])
    if not isinstance(phases, list) or any(not _valid_first_end_of_turn_phase(phase, state.get("session_id")) for phase in phases): return False
    leftovers = state.get("leftovers_end_of_turn_context", [])
    if not isinstance(leftovers, list) or any(not _valid_leftovers_end_of_turn_result(result, state.get("session_id")) for result in leftovers): return False
    black_sludge = state.get("black_sludge_end_of_turn_context", [])
    if not isinstance(black_sludge, list) or any(not _valid_black_sludge_end_of_turn_result(result, state.get("session_id")) for result in black_sludge): return False
    toxic_ticks = state.get("toxic_end_of_turn_context", [])
    if not isinstance(toxic_ticks, list) or any(not _valid_toxic_end_of_turn_result(result, state.get("session_id")) for result in toxic_ticks): return False
    sandstorm_ticks = state.get("sandstorm_end_of_turn_context", [])
    if not isinstance(sandstorm_ticks, list) or any(not _valid_sandstorm_end_of_turn_result(result, state.get("session_id")) for result in sandstorm_ticks): return False
    rain_dish = state.get("rain_dish_end_of_turn_context", [])
    if not isinstance(rain_dish, list) or any(not _valid_rain_dish_end_of_turn_result(result, state.get("session_id")) for result in rain_dish): return False
    ice_body = state.get("ice_body_end_of_turn_context", [])
    if not isinstance(ice_body, list) or any(not _valid_ice_body_end_of_turn_result(result, state.get("session_id")) for result in ice_body): return False
    solar_power = state.get("solar_power_end_of_turn_context", [])
    if not isinstance(solar_power, list) or any(not _valid_solar_power_end_of_turn_result(result, state.get("session_id")) for result in solar_power): return False
    dry_skin = state.get("dry_skin_end_of_turn_context", [])
    if not isinstance(dry_skin, list) or any(not _valid_dry_skin_end_of_turn_result(result, state.get("session_id")) for result in dry_skin): return False
    life_orb = state.get("life_orb_recoil_context", [])
    if not isinstance(life_orb, list) or any(not _valid_life_orb_recoil_result(result, state.get("session_id")) for result in life_orb): return False
    substitute = state.get("substitute_state_context")
    if substitute is not None and not _valid_substitute_state_context(state, substitute):
        return False
    pending = state.get("pending_status_action_execution_context")
    if pending is not None and not _valid_pending_status_action_execution_context(state, pending):
        return False
    mat_block = state.get("mat_block_active_entry_eligibility_context")
    if mat_block is not None and not _valid_mat_block_active_entry_eligibility_context(state, mat_block): return False
    fake_out = state.get("fake_out_active_entry_eligibility_context")
    if fake_out is not None and not _valid_fake_out_active_entry_eligibility_context(state, fake_out): return False
    history = state.get("supreme_overlord_faint_history_context")
    taunt = state.get("current_taunt_restrictions")
    encore = state.get("current_encore_restrictions")
    disable = state.get("current_disable_restrictions")
    snapshots = state.get("supreme_overlord_entry_snapshots")
    if history is not None and not _valid_supreme_overlord_history_context(state, history): return False
    if taunt is not None and not _valid_taunt_restrictions(state, taunt): return False
    if encore is not None and not _valid_encore_restrictions(state, encore): return False
    if disable is not None and not _valid_disable_restrictions(state, disable): return False
    if snapshots is not None and not _valid_supreme_overlord_snapshots(state, snapshots, history): return False
    topology = state.get("doubles_active_topology_context")
    targeting = state.get("selected_action_targeting_context")
    if topology is not None and not _valid_doubles_active_topology_context(state, topology): return False
    if targeting is not None and not _valid_selected_action_targeting_context(state, targeting): return False
    return not any(_contains_marker(value) for key, value in state.items() if key not in {"self_side", "opponent_side", "field", "substitute_state_context", "pending_status_action_execution_context", "mat_block_active_entry_eligibility_context", "fake_out_active_entry_eligibility_context", "doubles_active_topology_context", "selected_action_targeting_context", "same_turn_event_context", "first_end_of_turn_context", "leftovers_end_of_turn_context", "black_sludge_end_of_turn_context", "toxic_end_of_turn_context", "sandstorm_end_of_turn_context", "rain_dish_end_of_turn_context", "ice_body_end_of_turn_context", "solar_power_end_of_turn_context", "dry_skin_end_of_turn_context", "life_orb_recoil_context", "supreme_overlord_faint_history_context", "supreme_overlord_entry_snapshots", "current_taunt_restrictions", "current_encore_restrictions", "current_disable_restrictions"})


def _valid_fact_marker(value):
    return not (isinstance(value, dict) and "knowledge" in value) or is_unknown_battle_fact(value)


def _valid_taunt_restrictions(state, value):
    if not isinstance(value, dict) or set(value) - {"self", "opponent"}: return False
    for side, row in value.items():
        required = {"schema_version", "owner", "restriction", "activation_id", "source_action_id", "source_move_id", "state", "remaining_target_turns", "applied_turn", "last_completed_turn", "retired_reason", "application_provenance", "lifecycle_provenance"}
        if not isinstance(row, dict) or set(row) != required: return False
        owner, application, lifecycle = row.get("owner"), row.get("application_provenance"), row.get("lifecycle_provenance")
        if row.get("schema_version") != "reducer-action-restriction-lifecycle-v1" or not isinstance(owner, dict) or set(owner) != {"session_id", "side", "slot_index", "pokemon_id"} or owner.get("session_id") != state.get("session_id") or owner.get("side") != side or (row.get("state") == "active" and not _active_identity_matches(state, side, owner.get("slot_index"), owner.get("pokemon_id"))) or row.get("restriction") != "taunt" or not all(isinstance(row.get(key), str) and bool(row[key]) for key in ("activation_id", "source_action_id", "source_move_id")) or row.get("source_move_id") != "taunt" or row.get("state") not in {"active", "not_active"} or not isinstance(application, dict) or not isinstance(lifecycle, dict): return False
        if not all(application.get(key) is not None for key in ("source_observation_id", "source_sequence", "trust")) or application.get("trust") != "user_confirmed_observation" or not isinstance(application.get("source_sequence"), int) or isinstance(application.get("source_sequence"), bool) or application["source_sequence"] < 1: return False
        if not isinstance(row.get("applied_turn"), int) or isinstance(row.get("applied_turn"), bool) or row["applied_turn"] < 1: return False
        completed = row.get("last_completed_turn")
        if completed is not None and (not isinstance(completed, int) or isinstance(completed, bool) or completed <= row["applied_turn"]): return False
        active = row["state"] == "active"; remaining = row.get("remaining_target_turns")
        if active != (isinstance(remaining, int) and not isinstance(remaining, bool) and 1 <= remaining <= 3): return False
        if active != (row.get("retired_reason") is None): return False
        if lifecycle.get("trust") != "user_confirmed_observation" or not isinstance(lifecycle.get("source_sequence"), int) or isinstance(lifecycle.get("source_sequence"), bool) or lifecycle["source_sequence"] < 1: return False
    return True


def _valid_last_executed_move(state, value, expected_owner=None):
    if value is None: return True
    if not isinstance(value, dict) or set(value) != {"schema_version", "owner", "move_id", "source_action_id", "execution_id", "provenance"}: return False
    owner, provenance = value.get("owner"), value.get("provenance")
    return value.get("schema_version") == "reducer-last-executed-move-v1" and isinstance(owner, dict) and set(owner) == {"session_id", "side", "slot_index", "pokemon_id"} and owner.get("session_id") == state.get("session_id") and owner.get("side") in {"self", "opponent"} and isinstance(owner.get("slot_index"), int) and not isinstance(owner.get("slot_index"), bool) and isinstance(owner.get("pokemon_id"), str) and bool(owner["pokemon_id"]) and (expected_owner is None or owner == expected_owner) and all(isinstance(value.get(key), str) and bool(value[key]) for key in ("move_id", "source_action_id", "execution_id")) and isinstance(provenance, dict) and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool) and provenance["source_sequence"] > 0

def _valid_previous_action_result(state, value, expected_owner=None):
    if value is None: return True
    required = {"schema_version", "owner", "previous_action_id", "selected_move_id", "execution_move_id", "result_class", "source_turn", "provenance"}
    if not isinstance(value, dict) or set(value) != required: return False
    owner, provenance = value.get("owner"), value.get("provenance")
    return value.get("schema_version") == "reducer-previous-action-result-v1" and isinstance(owner, dict) and set(owner) == {"session_id", "side", "slot_index", "pokemon_id"} and owner.get("session_id") == state.get("session_id") and owner.get("side") in {"self", "opponent"} and isinstance(owner.get("slot_index"), int) and not isinstance(owner.get("slot_index"), bool) and isinstance(owner.get("pokemon_id"), str) and bool(owner["pokemon_id"]) and (expected_owner is None or owner == expected_owner) and all(isinstance(value.get(k), str) and bool(value[k]) for k in ("previous_action_id", "selected_move_id", "execution_move_id", "result_class")) and isinstance(value.get("source_turn"), int) and not isinstance(value.get("source_turn"), bool) and value["source_turn"] > 0 and isinstance(provenance, dict) and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool) and provenance["source_sequence"] > 0


def _valid_encore_restrictions(state, value):
    if not isinstance(value, dict) or set(value) - {"self", "opponent"}: return False
    for side, row in value.items():
        required = {"schema_version", "owner", "restriction", "activation_id", "source_action_id", "source_move_id", "locked_move_id", "last_used_execution_id", "state", "remaining_target_turns", "applied_turn", "last_completed_turn", "retired_reason", "application_provenance", "lifecycle_provenance"}
        if not isinstance(row, dict) or set(row) != required: return False
        owner, application, lifecycle = row.get("owner"), row.get("application_provenance"), row.get("lifecycle_provenance")
        if row.get("schema_version") != "reducer-action-restriction-lifecycle-v1" or row.get("restriction") != "encore" or row.get("source_move_id") != "encore" or not isinstance(owner, dict) or set(owner) != {"session_id", "side", "slot_index", "pokemon_id"} or owner.get("session_id") != state.get("session_id") or owner.get("side") != side or (row.get("state") == "active" and not _active_identity_matches(state, side, owner.get("slot_index"), owner.get("pokemon_id"))) or not all(isinstance(row.get(key), str) and bool(row[key]) for key in ("activation_id", "source_action_id", "source_move_id", "locked_move_id", "last_used_execution_id")) or row.get("state") not in {"active", "not_active"} or not isinstance(application, dict) or not isinstance(lifecycle, dict): return False
        if not isinstance(row.get("applied_turn"), int) or isinstance(row.get("applied_turn"), bool) or row["applied_turn"] < 1: return False
        completed = row.get("last_completed_turn")
        if completed is not None and (not isinstance(completed, int) or isinstance(completed, bool) or completed <= row["applied_turn"]): return False
        active, remaining = row["state"] == "active", row.get("remaining_target_turns")
        if active != (isinstance(remaining, int) and not isinstance(remaining, bool) and 1 <= remaining <= 3) or active != (row.get("retired_reason") is None): return False
        for provenance in (application, lifecycle):
            if provenance.get("trust") != "user_confirmed_observation" or not isinstance(provenance.get("source_sequence"), int) or isinstance(provenance.get("source_sequence"), bool) or provenance["source_sequence"] < 1: return False
    return True


def _valid_disable_restrictions(state, value):
    if not isinstance(value, dict) or set(value) - {"self", "opponent"}: return False
    for side, row in value.items():
        required = {"schema_version", "owner", "restriction", "activation_id", "source_action_id", "source_move_id", "disabled_move_id", "last_used_execution_id", "state", "remaining_target_turns", "applied_turn", "last_completed_turn", "retired_reason", "application_provenance", "lifecycle_provenance"}
        if not isinstance(row, dict) or set(row) != required: return False
        owner = row.get("owner")
        if row.get("schema_version") != "reducer-action-restriction-lifecycle-v1" or row.get("restriction") != "disable" or row.get("source_move_id") != "disable" or not isinstance(owner, dict) or set(owner) != {"session_id", "side", "slot_index", "pokemon_id"} or owner.get("session_id") != state.get("session_id") or owner.get("side") != side or (row.get("state") == "active" and not _active_identity_matches(state, side, owner.get("slot_index"), owner.get("pokemon_id"))) or not all(isinstance(row.get(key), str) and bool(row[key]) for key in ("activation_id", "source_action_id", "disabled_move_id", "last_used_execution_id")) or row.get("state") not in {"active", "not_active"}: return False
        active, remaining = row["state"] == "active", row.get("remaining_target_turns")
        if active != (isinstance(remaining, int) and not isinstance(remaining, bool) and 1 <= remaining <= 4) or active != (row.get("retired_reason") is None): return False
        if not isinstance(row.get("applied_turn"), int) or isinstance(row.get("applied_turn"), bool) or row["applied_turn"] < 1: return False
        for key in ("application_provenance", "lifecycle_provenance"):
            p = row.get(key)
            if not isinstance(p, dict) or p.get("trust") != "user_confirmed_observation" or not isinstance(p.get("source_sequence"), int) or isinstance(p.get("source_sequence"), bool) or p["source_sequence"] < 1: return False
    return True


def _valid_pending_status_action_execution_context(state, value):
    if not isinstance(value, dict) or set(value) != {"schema_version", "session_id", "decision_point", "actor", "action_id", "move_id", "condition", "execution_state", "blocker", "provenance"}:
        return False
    actor, provenance = value.get("actor"), value.get("provenance")
    if value.get("schema_version") != "pending-status-action-execution-context-v1" or value.get("session_id") != state.get("session_id") or not isinstance(actor, dict):
        return False
    if set(actor) != {"session_id", "side", "slot_index", "pokemon_id"} or actor.get("session_id") != state.get("session_id") or not _active_identity_matches(state, actor.get("side"), actor.get("slot_index"), actor.get("pokemon_id")):
        return False
    if not all(isinstance(value.get(key), str) and bool(value[key]) for key in ("decision_point", "action_id", "move_id")) or value.get("condition") not in {"sleep", "freeze"} or value.get("execution_state") not in {"executable", "blocked"}:
        return False
    if (value["execution_state"] == "executable" and value.get("blocker") is not None) or (value["execution_state"] == "blocked" and value.get("blocker") != value["condition"]):
        return False
    return isinstance(provenance, dict) and provenance.get("event_kind") == "pending_status_action_execution_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0 and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool) and provenance["source_sequence"] > 0


def _valid_mat_block_active_entry_eligibility_context(state, value):
    required = {"schema_version", "session_id", "decision_point", "actor", "action_id", "move_id", "active_entry_token", "eligibility", "provenance"}
    if not isinstance(value, dict) or set(value) != required: return False
    actor, provenance = value.get("actor"), value.get("provenance")
    return value.get("schema_version") == "mat-block-active-entry-eligibility-context-v1" and value.get("session_id") == state.get("session_id") and isinstance(actor, dict) and set(actor) == {"session_id", "side", "slot_index", "pokemon_id"} and actor.get("session_id") == state.get("session_id") and _active_identity_matches(state, actor.get("side"), actor.get("slot_index"), actor.get("pokemon_id")) and all(isinstance(value.get(key), str) and bool(value[key]) for key in ("decision_point", "action_id", "active_entry_token")) and value.get("move_id") == "mat-block" and value.get("eligibility") in {"eligible", "ineligible"} and isinstance(provenance, dict) and provenance.get("event_kind") == "mat_block_active_entry_eligibility_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool)


def _valid_fake_out_active_entry_eligibility_context(state, value):
    required = {"schema_version", "session_id", "decision_point", "actor", "action_id", "move_id", "active_entry_token", "eligibility", "provenance"}
    if not isinstance(value, dict) or set(value) != required: return False
    actor, provenance = value.get("actor"), value.get("provenance")
    return value.get("schema_version") == "fake-out-active-entry-eligibility-context-v1" and value.get("session_id") == state.get("session_id") and isinstance(actor, dict) and set(actor) == {"session_id", "side", "slot_index", "pokemon_id"} and actor.get("session_id") == state.get("session_id") and _active_identity_matches(state, actor.get("side"), actor.get("slot_index"), actor.get("pokemon_id")) and all(isinstance(value.get(key), str) and bool(value[key]) for key in ("decision_point", "action_id", "active_entry_token")) and value.get("move_id") == "fake-out" and value.get("eligibility") in {"eligible", "ineligible"} and isinstance(provenance, dict) and provenance.get("event_kind") == "fake_out_active_entry_eligibility_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool)


def _valid_supreme_overlord_history_context(state, value):
    if not isinstance(value, dict) or set(value) != {"schema_version", "session_id", "side_counts", "initialized_sides", "provenance"}:
        return False
    counts, initialized, provenance = value.get("side_counts"), value.get("initialized_sides"), value.get("provenance")
    return value.get("schema_version") == "supreme-overlord-faint-history-context-v1" and value.get("session_id") == state.get("session_id") and isinstance(counts, dict) and set(counts) == {"self", "opponent"} and all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in counts.values()) and isinstance(initialized, list) and set(initialized) <= {"self", "opponent"} and len(initialized) == len(set(initialized)) and isinstance(provenance, dict)


def _valid_supreme_overlord_snapshots(state, value, history):
    if not isinstance(value, list): return False
    seen = set()
    for row in value:
        owner = row.get("owner") if isinstance(row, dict) else None
        if not isinstance(row, dict) or set(row) != {"schema_version", "session_id", "owner", "entry_token", "entry_kind", "raw_allied_faint_count", "fallen_allies_count", "source_sequence", "source_state_fingerprint", "status", "active", "provenance"} or row.get("schema_version") != "supreme-overlord-entry-snapshot-v1" or row.get("session_id") != state.get("session_id") or not isinstance(owner, dict) or set(owner) != {"session_id", "side", "slot_index", "pokemon_id"} or owner.get("session_id") != state.get("session_id") or owner.get("side") not in {"self", "opponent"} or not isinstance(owner.get("slot_index"), int) or isinstance(owner.get("slot_index"), bool) or not isinstance(owner.get("pokemon_id"), str) or not owner["pokemon_id"] or not isinstance(row.get("entry_token"), str) or not row["entry_token"] or row.get("entry_kind") not in {"initial_active", "switch_active"} or not isinstance(row.get("raw_allied_faint_count"), int) or isinstance(row.get("raw_allied_faint_count"), bool) or row["raw_allied_faint_count"] < 0 or row.get("fallen_allies_count") != min(row["raw_allied_faint_count"], 5) or not isinstance(row.get("source_sequence"), int) or isinstance(row.get("source_sequence"), bool) or row["source_sequence"] < 1 or not isinstance(row.get("source_state_fingerprint"), str) or not row["source_state_fingerprint"] or row.get("status") != "resolved" or not isinstance(row.get("active"), bool) or not isinstance(row.get("provenance"), dict):
            return False
        key = (owner["side"], owner["slot_index"], owner["pokemon_id"], row["entry_token"])
        if key in seen: return False
        seen.add(key)
    active = [row for row in value if row["active"]]
    return all(_active_identity_matches(state, row["owner"]["side"], row["owner"]["slot_index"], row["owner"]["pokemon_id"]) for row in active)


def _valid_doubles_active_topology_context(state, value):
    rows, provenance = value.get("active_owners") if isinstance(value, dict) else None, value.get("provenance") if isinstance(value, dict) else None
    if not isinstance(value, dict) or set(value) != {"schema_version", "session_id", "active_owners", "provenance"} or value.get("schema_version") != "doubles-active-topology-context-v1" or value.get("session_id") != state.get("session_id") or not isinstance(rows, list) or len(rows) != 4:
        return False
    identities = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"session_id", "side", "slot_index", "pokemon_id", "active"} or row.get("session_id") != state.get("session_id") or row.get("side") not in {"self", "opponent"} or not isinstance(row.get("slot_index"), int) or isinstance(row.get("slot_index"), bool) or row["slot_index"] < 0 or not isinstance(row.get("pokemon_id"), str) or not row["pokemon_id"] or row.get("active") is not True or (row["side"], row["slot_index"]) in identities:
            return False
        identities.add((row["side"], row["slot_index"]))
        side = _side(state, row["side"]); roster = side.get("pokemon") if isinstance(side, dict) else None; pokemon = roster.get(row["slot_index"], roster.get(str(row["slot_index"]))) if isinstance(roster, dict) else None
        if not isinstance(pokemon, dict) or pokemon.get("pokemon_id", pokemon.get("name_en")) != row["pokemon_id"]: return False
    return all(sum(row["side"] == side for row in rows) == 2 for side in ("self", "opponent")) and isinstance(provenance, dict) and provenance.get("event_kind") == "doubles_active_topology_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool) and provenance["source_sequence"] > 0


def _valid_selected_action_targeting_context(state, value):
    if not isinstance(value, dict) or set(value) != {"schema_version", "session_id", "decision_point", "actor", "action_id", "move_id", "selected_target", "provenance"} or value.get("schema_version") != "selected-action-targeting-context-v1" or value.get("session_id") != state.get("session_id"):
        return False
    actor, target, provenance = value.get("actor"), value.get("selected_target"), value.get("provenance")
    owner_ok = lambda owner: isinstance(owner, dict) and set(owner) == {"session_id", "side", "slot_index", "pokemon_id"} and owner.get("session_id") == state.get("session_id") and owner.get("side") in {"self", "opponent"} and isinstance(owner.get("slot_index"), int) and not isinstance(owner.get("slot_index"), bool) and owner["slot_index"] >= 0 and isinstance(owner.get("pokemon_id"), str) and bool(owner["pokemon_id"])
    return owner_ok(actor) and (target is None or owner_ok(target)) and all(isinstance(value.get(key), str) and bool(value[key]) for key in ("decision_point", "action_id", "move_id")) and isinstance(provenance, dict) and provenance.get("event_kind") == "selected_action_targeting_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool) and provenance["source_sequence"] > 0


def _valid_current_type_state(value, provenance):
    if value is None:
        return provenance is None
    if is_unknown_battle_fact(value):
        return provenance is None
    try:
        normalize_current_type_authority({
            "side": "self", "state": "known", "types": value,
            "status": "user_confirmed", "source": "user_confirmed_current_type",
            "authority_provenance": "user_confirmed_current",
        })
    except ValueError:
        return False
    return isinstance(provenance, dict) and provenance.get("event_kind") in {"current_type_observed", "current_opponent_switch_target_combat_observed"} and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0


def _valid_known_move_observation(value):
    return (
        isinstance(value, dict)
        and value.get("event_kind") in {"used_move_observed", "current_opponent_response_set_observed"}
        and value.get("trust") == "user_confirmed_observation"
        and isinstance(value.get("source_observation_id"), str)
        and bool(value["source_observation_id"])
        and isinstance(value.get("source_sequence"), int)
        and not isinstance(value.get("source_sequence"), bool)
        and value["source_sequence"] >= 1
    )


def _valid_current_move_usability(value, known_moves):
    if value is None:
        return True
    if not isinstance(value, dict) or any(not _canonical_move_id(move) or move not in known_moves for move in value):
        return False
    for record in value.values():
        provenance = record.get("provenance") if isinstance(record, dict) else None
        if not isinstance(record, dict) or set(record) != {"status", "reason", "provenance"} or record.get("status") not in {"known_usable", "known_unusable"}:
            return False
        if record["status"] == "known_usable" and record["reason"] is not None:
            return False
        if record["status"] == "known_unusable" and record["reason"] not in {"no_pp", "disabled", "choice_lock", "encore_restriction", "other_supported_restriction", "observed_unclassified"}:
            return False
        if not isinstance(provenance, dict) or provenance.get("event_kind") not in {"current_move_usability_observed", "current_opponent_response_set_observed"} or provenance.get("trust") != "user_confirmed_observation" or not isinstance(provenance.get("turn_number"), int) or isinstance(provenance.get("turn_number"), bool) or provenance["turn_number"] < 1 or not isinstance(provenance.get("source_sequence"), int) or isinstance(provenance.get("source_sequence"), bool) or provenance["source_sequence"] < 1:
            return False
    return True


def _valid_current_opponent_response_set(value, known_moves):
    if value is None:
        return True
    if not isinstance(value, dict) or set(value) != {"moveset_completeness", "move_ids", "provenance"}:
        return False
    provenance = value.get("provenance")
    return (
        value.get("moveset_completeness") == "complete"
        and isinstance(value.get("move_ids"), list) and len(value["move_ids"]) == 4
        and value["move_ids"] == known_moves
        and isinstance(provenance, dict)
        and provenance.get("event_kind") == "current_opponent_response_set_observed"
        and provenance.get("trust") == "user_confirmed_observation"
        and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] >= 1
        and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool) and provenance["source_sequence"] >= 1
    )


def _valid_current_opponent_switch_response_set(state, value):
    side = state.get("opponent_side") if isinstance(state, dict) else None
    roster = side.get("pokemon") if isinstance(side, dict) else None
    active = side.get("active_slot_index") if isinstance(side, dict) else None
    if not isinstance(value, dict) or not isinstance(roster, dict) or set(value) != {"schema_version", "permission", "target_set_completeness", "targets", "active_owner", "provenance"}:
        return False
    owner, provenance, targets = value.get("active_owner"), value.get("provenance"), value.get("targets")
    if value.get("schema_version") != "current-opponent-switch-response-set-v1" or value.get("permission") not in {"permitted", "blocked", "unknown"} or value.get("target_set_completeness") != "complete" or not isinstance(owner, dict) or owner != {"session_id": state.get("session_id"), "side": "opponent", "slot_index": active, "pokemon_id": roster.get(active, {}).get("pokemon_id") if isinstance(roster.get(active), dict) else None} or not isinstance(targets, list):
        return False
    seen = set()
    for row in targets:
        slot = row.get("slot_index") if isinstance(row, dict) else None; pokemon_id = row.get("pokemon_id") if isinstance(row, dict) else None
        pokemon = roster.get(slot)
        if not isinstance(row, dict) or set(row) != {"slot_index", "pokemon_id", "availability"} or not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or slot == active or not isinstance(pokemon_id, str) or not pokemon_id or row.get("availability") not in {"alive", "fainted", "unknown"} or (slot, pokemon_id) in seen or not isinstance(pokemon, dict) or pokemon.get("pokemon_id") != pokemon_id:
            return False
        seen.add((slot, pokemon_id))
    return isinstance(provenance, dict) and provenance.get("event_kind") == "current_opponent_switch_response_set_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] >= 1 and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool) and provenance["source_sequence"] >= 1


def _valid_known_move_provenance(value, moves):
    if value is None:
        # Legacy snapshots retain their identity list but cannot become strict
        # opponent-action authority until every move has positive provenance.
        return True
    return (
        isinstance(value, dict)
        and set(value) == set(moves)
        and all(_valid_known_move_observation(item) for item in value.values())
    )


def _valid_current_level_state(value, provenance):
    if value is None or is_unknown_battle_fact(value):
        return provenance is None
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 100 and isinstance(provenance, dict) and provenance.get("event_kind") == "current_level_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0


def _valid_current_final_stats(value):
    if value is None:
        return True  # legacy runtime snapshots have no final-stat authority.
    if not isinstance(value, dict):
        return False
    for stat, entry in value.items():
        if stat not in {"attack", "defense", "special-attack", "special-defense", "speed"} or not isinstance(entry, dict):
            return False
        if set(entry) != {"value", "provenance"} or not isinstance(entry["value"], int) or isinstance(entry["value"], bool) or not 1 <= entry["value"] <= 9999:
            return False
        provenance = entry["provenance"]
        if not isinstance(provenance, dict) or provenance.get("event_kind") not in {"current_final_combat_stat_observed", "current_opponent_switch_target_combat_observed"} or provenance.get("trust") != "user_confirmed_observation" or not isinstance(provenance.get("turn_number"), int) or isinstance(provenance.get("turn_number"), bool) or provenance["turn_number"] < 1:
            return False
    return True


def _valid_substitute_state_context(state, value):
    if not isinstance(value, dict) or value.get("schema_version") != "detached-substitute-state-v1" or value.get("session_id") != state.get("session_id") or not isinstance(value.get("states"), list):
        return False
    owners, seen = set(), set()
    for row in value["states"]:
        owner = row.get("owner") if isinstance(row, dict) else None
        status, hp = row.get("state") if isinstance(row, dict) else None, row.get("substitute_hp") if isinstance(row, dict) else None
        if not isinstance(owner, dict) or set(owner) != {"session_id", "side", "slot_index", "pokemon_id"} or owner.get("session_id") != state.get("session_id") or owner.get("side") not in {"self", "opponent"} or not isinstance(owner.get("slot_index"), int) or isinstance(owner.get("slot_index"), bool) or not isinstance(owner.get("pokemon_id"), str) or not owner["pokemon_id"]:
            return False
        pokemon = _pokemon(state, owner)
        key = (owner["side"], owner["slot_index"], owner["pokemon_id"])
        if pokemon is None or key in seen or status not in {"known_active", "known_inactive", "unknown"} or (status == "known_active" and (not isinstance(hp, int) or isinstance(hp, bool) or hp <= 0)) or (status != "known_active" and hp is not None):
            return False
        owners.add(key); seen.add(key)
    return True


def _valid_current_ability_state(value, provenance):
    if value is None:
        return provenance is None
    if is_unknown_battle_fact(value):
        return provenance is None
    try:
        normalize_user_confirmed_current_ability({
            "side": "self", "ability": value, "status": "user_confirmed",
            "source": "user_confirmed_current_ability",
        })
    except ValueError:
        return False
    return isinstance(provenance, dict) and provenance.get("event_kind") in {"current_ability_observed", "current_opponent_switch_target_combat_observed"} and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0


def _valid_current_condition_state(value, provenance):
    """Accept legacy condition records while validating strict observations."""
    if is_unknown_battle_fact(value):
        return provenance is None
    if provenance is None:
        return value is None or value in {"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
    if not isinstance(provenance, dict):
        return False
    if provenance.get("event_kind") in {"current_condition_observed", "current_opponent_switch_target_combat_observed"}:
        return provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0 and provenance.get("condition") in {"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"} and ((provenance["condition"] == "none" and value is None) or value == provenance["condition"])
    if provenance.get("event_kind") == "condition_applied_observed":
        return isinstance(value, str) and value in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
    return provenance.get("event_kind") == "condition_removed_observed" and value is None


def _valid_current_crit_volatile_state(value, provenance):
    if value is None or is_unknown_battle_fact(value):
        return provenance is None
    return isinstance(value, list) and len(value) == len(set(value)) and all(item in {"focus-energy", "lansat", "dragon-cheer"} for item in value) and isinstance(provenance, dict) and provenance.get("event_kind") == "current_crit_volatiles_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0


def _valid_current_weather_state(value, provenance):
    if provenance is None:
        return True
    return value in {"none", "sun", "rain", "sandstorm", "snow"} and isinstance(provenance, dict) and provenance.get("event_kind") == "current_weather_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0


def _valid_current_terrain_state(value, provenance):
    if provenance is None:
        return True
    return value in {"none", "electric", "grassy", "misty", "psychic"} and isinstance(provenance, dict) and provenance.get("event_kind") == "current_terrain_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0


def _valid_current_battle_format_state(value, provenance):
    if value is None or is_unknown_battle_fact(value):
        return provenance is None
    if value not in {"singles", "doubles"} or not isinstance(provenance, dict):
        return False
    return (provenance.get("event_kind") == "session_battle_format_initialized" and provenance.get("source") == "user_confirmed_battle_format" and provenance.get("trust") == "user_confirmed_observation") or (provenance.get("event_kind") == "current_battle_format_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] > 0)


def _valid_current_item_state(value, provenance):
    if provenance is None:
        return not is_unknown_battle_fact(value) or value == UNKNOWN_BATTLE_FACT
    if not isinstance(provenance, dict) or not isinstance(provenance.get("turn_number"), int) or isinstance(provenance.get("turn_number"), bool) or provenance["turn_number"] < 1:
        return False
    return (provenance.get("event_kind") in {"current_item_observed", "current_opponent_switch_target_combat_observed"} and provenance.get("trust") == "user_confirmed_observation" and (value is None or isinstance(value, str) and bool(value))) or (provenance.get("event_kind") in {"item_consumption_observed", "item_removed_observed"} and value is None)


def _valid_toxic_progression_state(value):
    if value is None or is_unknown_battle_fact(value):
        return True
    provenance = value.get("provenance") if isinstance(value, dict) else None
    return isinstance(value, dict) and set(value) == {"next_stage", "initialized_turn", "last_processed_turn", "condition_observation_id", "provenance"} and isinstance(value.get("next_stage"), int) and not isinstance(value.get("next_stage"), bool) and 1 <= value["next_stage"] <= 15 and isinstance(value.get("initialized_turn"), int) and not isinstance(value.get("initialized_turn"), bool) and value["initialized_turn"] > 0 and (value.get("last_processed_turn") is None or isinstance(value.get("last_processed_turn"), int) and not isinstance(value.get("last_processed_turn"), bool) and value["last_processed_turn"] >= value["initialized_turn"]) and isinstance(value.get("condition_observation_id"), str) and bool(value["condition_observation_id"]) and isinstance(provenance, dict) and provenance.get("event_kind") == "condition_applied_observed" and provenance.get("trust") == "user_confirmed_observation"


def _contains_marker(value):
    if isinstance(value, dict):
        return "knowledge" in value or any(_contains_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_marker(item) for item in value)
    return False


def _unknown(value):
    """Accept legacy string unknown while new bootstrap state uses the marker."""
    return value == "unknown" or is_unknown_battle_fact(value)


def validate_atomic_transition(base_state, replay_plan, expected_session_id):
    """v15.21 schema-only guard; it intentionally does not project state."""
    base = deepcopy(base_state) if isinstance(base_state, dict) else {}
    plan = deepcopy(replay_plan) if isinstance(replay_plan, dict) else {}
    if base.get("state_version") != STATE_MODEL_VERSION:
        return _legacy_result("unsupported_state_version", base, plan)
    if base.get("session_id") != expected_session_id or plan.get("session_id") != expected_session_id:
        return _legacy_result("invalid_base_state", base, plan)
    if plan.get("status") != "planned":
        return _legacy_result("blocked_by_conflict" if plan.get("conflicts") else "invalid_replay_plan", base, plan)
    steps = plan.get("ordered_steps", [])
    if not steps:
        return _legacy_result("no_reducer_steps", base, plan)
    targets = []
    for step in steps:
        effect = step.get("planned_effect") if isinstance(step, dict) else None
        target = _TARGETS.get(effect)
        if target is None:
            return _legacy_result("invalid_replay_plan", base, plan)
        targets.append({"observation_id": step.get("observation_id"), "target_state_field": target, "planned_effect": effect})
    return {"status": "ready_for_atomic_transition", "base_state": base, "planned_next_state_schema": targets, "accepted_step_ids": [x.get("observation_id") for x in steps], "rejected_step_ids": [], "conflicts": [], "limitations": ["dry_run_only", "no_state_mutation", "unknown_values_not_overwritten"]}


def project_atomic_transition(base_state, replay_plan, expected_session_id=None, state_model_version=STATE_MODEL_VERSION):
    """Validate an entire plan and return a detached projected state only on success.

    This is deliberately a private reducer-time dry run: it never touches UI/runtime
    state, makes no provider calls, and never returns a prefix after a conflict.
    """
    base = deepcopy(base_state) if isinstance(base_state, dict) else None
    plan = deepcopy(replay_plan) if isinstance(replay_plan, dict) else None
    if state_model_version != STATE_MODEL_VERSION or not isinstance(base, dict) or base.get("state_version") != STATE_MODEL_VERSION:
        return _projection_result("unsupported_state_version", base, None)
    session = base.get("session_id")
    if not isinstance(session, str) or not session or (expected_session_id is not None and session != expected_session_id):
        return _projection_result("invalid_base_state", base, None)
    if not isinstance(plan, dict) or plan.get("session_id") != session:
        return _projection_result("invalid_replay_plan", base, plan)
    if plan.get("status") != "planned" or plan.get("conflicts"):
        return _projection_result("blocked_by_semantic_conflict" if plan.get("conflicts") else "invalid_replay_plan", base, plan)
    steps = plan.get("ordered_steps")
    if steps is None or not isinstance(steps, list):
        return _projection_result("invalid_replay_plan", base, plan)
    if not steps:
        return _projection_result("no_reducer_steps", base, plan)
    normalized, error = _normalize_steps(steps, plan)
    if error:
        return _projection_result("invalid_replay_plan", base, plan, rejected=_step_ids(steps), conflicts=[{"reason": error}])
    same_sequence = _same_sequence_conflicts(normalized)
    if same_sequence:
        return _projection_result("blocked_by_semantic_conflict", base, plan, rejected=_step_ids(steps), conflicts=same_sequence)
    projected = deepcopy(base)
    applied = []
    for item in normalized:
        conflict = _apply(projected, item)
        if conflict:
            return _projection_result("blocked_by_semantic_conflict", base, plan, rejected=_step_ids(steps), conflicts=[conflict])
        if item["planned_effect"] != "set_switch_permission":
            _invalidate_switch_permission(projected)
        if item["planned_effect"] not in {"set_ability_applicability", "set_ability_interaction"}:
            _invalidate_ability_interaction_authorities(projected)
        if item["planned_effect"] not in {"set_identity_groundedness", "clear_identity_groundedness"}:
            context=projected.get("identity_groundedness_context")
            if isinstance(context, dict):
                projected["identity_groundedness_context"]=normalize_groundedness(None,session_id=projected["session_id"],side=context.get("side"),slot_index=context.get("slot_index"),pokemon_id=context.get("pokemon_id"))
        if item["planned_effect"] not in {"set_switch_entry_intimidate", "clear_switch_entry_intimidate"}:
            projected.pop("switch_entry_intimidate_authority", None)
        if item["planned_effect"] not in {"set_switch_entry_download", "clear_switch_entry_download"}:
            projected.pop("switch_entry_download_authority", None)
        applied.append(item["observation_id"])
    sequences = [item["observation_sequence"] for item in normalized]
    projected["last_applied_observation_sequence"] = max(sequences)
    return {"status": "ready_with_projected_state", "base_state": deepcopy(base), "projected_state": deepcopy(projected), "applied_step_ids": applied, "rejected_step_ids": [], "conflicts": [], "limitations": ["dry_run_only", "no_runtime_state_mutation", "no_ui_state_mutation", "no_persistence", "no_q12_or_modifier_application", "provider_budget_0"]}


def state_fingerprint(state):
    """Stable private digest of battle-state semantics; never a public schema field."""
    if not isinstance(state, dict): return None
    return sha256(_canonical_json(_fingerprint_state(state)).encode("utf-8")).hexdigest()


def replay_batch_fingerprint(replay_plan):
    """Stable identity for a replay occurrence, independent of runtime object identity."""
    if not isinstance(replay_plan, dict): return None
    steps = replay_plan.get("ordered_steps")
    if not isinstance(steps, list): return None
    batch = {"session_id": replay_plan.get("session_id"), "replay_policy_version": replay_plan.get("replay_policy_version"), "ordered_steps": deepcopy(steps)}
    return sha256(_canonical_json(batch).encode("utf-8")).hexdigest()


def execute_atomic_transition(base_state, replay_plan, *, expected_session_id=None, expected_state_version=STATE_MODEL_VERSION, expected_base_fingerprint=None):
    """Pure optimistic-concurrency executor built on the canonical v15.22 projection."""
    base = deepcopy(base_state) if isinstance(base_state, dict) else None
    plan = deepcopy(replay_plan) if isinstance(replay_plan, dict) else None
    if expected_state_version != STATE_MODEL_VERSION or not isinstance(base, dict) or base.get("state_version") != STATE_MODEL_VERSION:
        return _execution_result("unsupported_state_version", None, None, None, plan)
    session = base.get("session_id")
    if not isinstance(session, str) or not session:
        return _execution_result("invalid_base_state", None, None, None, plan)
    if expected_session_id is not None and session != expected_session_id:
        return _execution_result("session_mismatch", None, None, None, plan)
    if not isinstance(plan, dict): return _execution_result("invalid_replay_plan", None, None, None, plan)
    if plan.get("session_id") != session: return _execution_result("session_mismatch", None, None, None, plan)
    base_digest, batch_digest = state_fingerprint(base), replay_batch_fingerprint(plan)
    if expected_base_fingerprint is not None and expected_base_fingerprint != base_digest:
        return _execution_result("stale_base_state", base_digest, None, batch_digest, plan)
    steps = plan.get("ordered_steps")
    if not isinstance(steps, list): return _execution_result("invalid_replay_plan", base_digest, None, batch_digest, plan)
    if not steps: return _execution_result("no_reducer_steps", base_digest, None, batch_digest, plan)
    sequences = [item.get("observation_sequence") for item in steps if isinstance(item, dict)]
    if len(sequences) != len(steps) or any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in sequences):
        return _execution_result("invalid_replay_plan", base_digest, None, batch_digest, plan)
    last = base.get("last_applied_observation_sequence")
    if isinstance(last, int) and not isinstance(last, bool):
        if all(sequence <= last for sequence in sequences):
            status = "already_applied" if base.get("last_applied_batch_fingerprint") == batch_digest else "blocked_by_semantic_conflict"
            conflict = [] if status == "already_applied" else [{"reason": "duplicate_or_overlapping_batch"}]
            return _execution_result(status, base_digest, None, batch_digest, plan, conflicts=conflict)
        if any(sequence <= last for sequence in sequences):
            return _execution_result("blocked_by_semantic_conflict", base_digest, None, batch_digest, plan, conflicts=[{"reason": "partial_sequence_overlap"}])
    projection = project_atomic_transition(base, plan, expected_session_id=session, state_model_version=expected_state_version)
    if projection["status"] != "ready_with_projected_state":
        return _execution_result(projection["status"], base_digest, None, batch_digest, plan, rejected=projection.get("rejected_step_ids"), conflicts=projection.get("conflicts"))
    committed = deepcopy(projection["projected_state"])
    committed["last_applied_batch_fingerprint"] = batch_digest
    committed["source_replay_policy_version"] = plan.get("replay_policy_version")
    committed["last_commit_provenance"] = {"base_state_fingerprint": base_digest, "replay_batch_fingerprint": batch_digest, "applied_step_ids": deepcopy(projection["applied_step_ids"])}
    committed_digest = state_fingerprint(committed)
    return {"status": "committed", "committed_state": deepcopy(committed), "base_state_fingerprint": base_digest, "committed_state_fingerprint": committed_digest, "replay_batch_fingerprint": batch_digest, "applied_step_ids": deepcopy(projection["applied_step_ids"]), "rejected_step_ids": [], "conflicts": [], "limitations": ["pure_detached_execution", "no_runtime_state_mutation", "no_ui_state_mutation", "no_persistence", "no_q12_or_modifier_application", "provider_budget_0"]}


def _normalize_steps(steps, plan):
    events = {e.get("observation_id"): e for e in plan.get("accepted_events", []) if isinstance(e, dict) and isinstance(e.get("observation_id"), str)}
    result, seen, previous = [], set(), None
    for raw in steps:
        if not isinstance(raw, dict): return [], "invalid_step"
        oid, seq, effect = raw.get("observation_id"), raw.get("observation_sequence"), raw.get("planned_effect")
        if not isinstance(oid, str) or not oid or oid in seen or not isinstance(seq, int) or isinstance(seq, bool) or seq < 1 or effect not in _TARGETS:
            return [], "invalid_step_identity_or_effect"
        if previous is not None and (seq, oid) < previous: return [], "invalid_step_order"
        previous, seen = (seq, oid), seen | {oid}
        event = deepcopy(events.get(oid, {})); event.update(deepcopy(raw))
        event["observation_id"], event["observation_sequence"], event["planned_effect"] = oid, seq, effect
        if not _has_target_identity(event): return [], "missing_required_target_identity"
        result.append(event)
    return result, None


def _value(event, name):
    if name in event: return event[name]
    payload = event.get("payload")
    return payload.get(name) if isinstance(payload, dict) else None


def _has_target_identity(event):
    effect = event["planned_effect"]
    if effect in {"apply_taunt_restriction", "complete_restricted_active_turn", "record_executed_move", "record_previous_action_result", "initialize_rage_fist_hit_count", "record_rage_fist_qualifying_hit", "apply_encore_restriction", "complete_encore_restricted_active_turn", "apply_disable_restriction", "complete_disable_restricted_active_turn"}:
        return _identity_values(event, "side", "slot_index", "pokemon_id") and isinstance(_value(event, "turn_number"), int) and not isinstance(_value(event, "turn_number"), bool) and _value(event, "turn_number") > 0
    if effect in {"apply_exact_hp_transition", "apply_exact_hp_recovery", "set_current_type", "set_current_condition", "set_pending_status_action_execution", "set_current_ability", "set_current_item", "set_current_level", "set_current_final_combat_stat", "set_current_move_usability", "set_current_opponent_response_set", "set_current_opponent_switch_response_set", "set_current_opponent_switch_target_combat", "set_current_substitute", "set_condition", "clear_condition", "set_current_stat_stage", "set_current_crit_volatiles", "consume_item", "remove_item", "mark_fainted", "record_known_move", "set_prospective_groundedness", "clear_prospective_groundedness", "set_prospective_speed_stage", "clear_prospective_speed_stage", "set_prospective_offensive_stages", "clear_prospective_offensive_stages", "set_prospective_entry_interactions", "clear_prospective_entry_interactions", "initialize_supreme_overlord_active_entry"}:
        return isinstance(_value(event, "side"), str) and isinstance(_value(event, "slot_index"), int) and not isinstance(_value(event, "slot_index"), bool) and isinstance(_value(event, "pokemon_id"), str) and bool(_value(event, "pokemon_id"))
    if effect == "switch_active":
        return isinstance(_value(event, "side"), str) and all(_value(event, key) is not None for key in ("switch_out_slot_index", "switch_out_pokemon_id", "switch_in_slot_index", "switch_in_pokemon_id"))
    if effect in {"set_switch_permission", "clear_switch_permission"}:
        return _value(event, "side") == "self" and isinstance(_value(event, "slot_index"), int) and not isinstance(_value(event, "slot_index"), bool) and isinstance(_value(event, "pokemon_id"), str) and bool(_value(event, "pokemon_id"))
    if effect == "set_observed_tailwind":
        return _value(event, "side") in {"self", "opponent"} and _value(event, "tailwind_status") in {"active", "inactive"}
    if effect == "set_observed_trick_room":
        return _value(event, "trick_room_status") in {"active", "inactive"}
    if effect == "set_same_turn_event":
        return _identity_values(event, "side", "slot_index", "pokemon_id") and _identity_values(event, "target_side", "target_slot_index", "target_pokemon_id") and (_value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")) != (_value(event, "target_side"), _value(event, "target_slot_index"), _value(event, "target_pokemon_id")) and _value(event, "predicate") in {"received_qualifying_direct_damage", "acted_earlier_this_turn", "lost_hp_this_turn", "qualifying_direct_damage_dealt"} and isinstance(_value(event, "occurred"), bool) and isinstance(_value(event, "turn_number"), int) and not isinstance(_value(event, "turn_number"), bool) and _value(event, "turn_number") > 0
    if effect == "mark_first_end_of_turn_reached":
        return isinstance(_value(event, "turn_number"), int) and not isinstance(_value(event, "turn_number"), bool) and _value(event, "turn_number") > 0
    if effect == "set_doubles_active_topology":
        return isinstance(_value(event, "active_owners"), list)
    if effect == "set_selected_action_targeting":
        return _identity_values(event, "side", "slot_index", "pokemon_id") and all(isinstance(_value(event, key), str) and bool(_value(event, key)) for key in ("decision_point", "action_id", "move_id"))
    if effect in {"set_ability_applicability", "clear_ability_applicability"}:
        return _identity_values(event, "side", "slot_index", "pokemon_id") and isinstance(_value(event, "ability_id"), str) and bool(_value(event, "ability_id"))
    if effect in {"set_ability_interaction", "clear_ability_interaction"}:
        return _identity_values(event, "source_side", "source_slot_index", "source_pokemon_id") and _identity_values(event, "target_side", "target_slot_index", "target_pokemon_id")
    if effect in {"set_switch_entry_intimidate", "clear_switch_entry_intimidate"}:
        return _identity_values(event, "source_side", "source_slot_index", "source_pokemon_id") and _identity_values(event, "target_side", "target_slot_index", "target_pokemon_id")
    if effect in {"set_switch_entry_download", "clear_switch_entry_download"}:
        return _identity_values(event, "source_side", "source_slot_index", "source_pokemon_id") and _identity_values(event, "target_side", "target_slot_index", "target_pokemon_id")
    if effect in {"set_identity_groundedness", "clear_identity_groundedness"}: return _identity_values(event,"side","slot_index","pokemon_id")
    if effect in {"set_switch_hazards", "clear_switch_hazards"}: return _value(event,"side") in {"self","opponent"}
    if effect in {"set_current_weather", "start_weather", "end_weather"}: return isinstance(_value(event, "weather"), str) and _value(event, "weather") in {"none", "sun", "rain", "sandstorm", "snow"}
    if effect == "set_current_terrain": return _value(event, "terrain") in {"none", "electric", "grassy", "misty", "psychic"}
    if effect == "set_current_battle_format": return _value(event, "battle_format") in {"singles", "doubles"}
    if effect == "set_current_side_conditions": return _value(event, "side") in {"self", "opponent"} and isinstance(_value(event, "side_conditions"), list)
    if effect in {"start_terrain", "end_terrain"}: return isinstance(_value(event, "terrain"), str) and bool(_value(event, "terrain"))
    return isinstance(_value(event, "side"), str) and isinstance(_value(event, "side_condition") or _value(event, "effect"), str)


def _side(state, side):
    if side not in {"self", "opponent"}: return None
    value = state.get(f"{side}_side")
    return value if isinstance(value, dict) else None


def _identity_values(event, side_key, slot_key, pokemon_key):
    return _value(event, side_key) in {"self", "opponent"} and isinstance(_value(event, slot_key), int) and not isinstance(_value(event, slot_key), bool) and isinstance(_value(event, pokemon_key), str) and bool(_value(event, pokemon_key))


def _active_identity_matches(state, side_name, slot, pokemon_id):
    side = _side(state, side_name)
    roster = side.get("pokemon") if isinstance(side, dict) else None
    active = side.get("active_slot_index") if isinstance(side, dict) else None
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, dict) else None
    return active == slot and isinstance(pokemon, dict) and pokemon.get("pokemon_id", pokemon.get("name_en")) == pokemon_id


def _pokemon(state, event):
    side = _side(state, _value(event, "side")); slot, pid = _value(event, "slot_index"), _value(event, "pokemon_id")
    if side is None or not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pid, str) or not pid: return None
    roster = side.get("pokemon")
    if not isinstance(roster, dict): return None
    pokemon = roster.get(slot, roster.get(str(slot)))
    if not isinstance(pokemon, dict) or pokemon.get("pokemon_id", pokemon.get("name_en")) != pid: return None
    return pokemon


def _provenance(event):
    return {key: deepcopy(_value(event, key)) for key in ("source_observation_id", "source_sequence", "trust") if _value(event, key) is not None} | {"source_observation_id": event["observation_id"], "source_sequence": event["observation_sequence"]}


def _mark(container, field, event):
    container[f"{field}_provenance"] = _provenance(event)


def _apply(state, event):
    effect = event["planned_effect"]
    if effect != "mark_first_end_of_turn_reached" and _phase_already_reached(state, _value(event, "turn_number")):
        return _conflict(event, "post_first_end_of_turn_transition_unsupported")
    if effect == "mark_first_end_of_turn_reached":
        return _mark_first_end_of_turn_reached(state, event)
    if effect == "set_current_type":
        return _set_current_type(state, event)
    if effect == "set_current_condition":
        return _set_current_condition(state, event)
    if effect == "set_pending_status_action_execution":
        return _set_pending_status_action_execution(state, event)
    if effect == "set_mat_block_active_entry_eligibility":
        return _set_mat_block_active_entry_eligibility(state, event)
    if effect == "set_fake_out_active_entry_eligibility":
        return _set_fake_out_active_entry_eligibility(state, event)
    if effect == "set_doubles_active_topology":
        return _set_doubles_active_topology(state, event)
    if effect == "set_selected_action_targeting":
        return _set_selected_action_targeting(state, event)
    if effect == "set_current_level":
        return _set_current_level(state, event)
    if effect == "set_current_final_combat_stat":
        return _set_current_final_combat_stat(state, event)
    if effect == "set_current_substitute":
        return _set_current_substitute(state, event)
    if effect == "initialize_supreme_overlord_active_entry":
        return _initialize_supreme_overlord_active_entry(state, event)
    if effect == "set_current_weather":
        return _set_current_weather(state, event)
    if effect == "set_current_ability":
        return _set_current_ability(state, event)
    if effect == "set_current_item":
        return _set_current_item(state, event)
    if effect == "set_current_move_usability":
        return _set_current_move_usability(state, event)
    if effect == "apply_taunt_restriction": return _apply_taunt_restriction(state, event)
    if effect == "complete_restricted_active_turn": return _complete_taunt_turn(state, event)
    if effect == "record_executed_move": return _record_executed_move(state, event)
    if effect == "record_previous_action_result": return _record_previous_action_result(state, event)
    if effect == "initialize_rage_fist_hit_count": return _initialize_rage_fist_hit_count(state,event)
    if effect == "record_rage_fist_qualifying_hit": return _record_rage_fist_qualifying_hit(state,event)
    if effect == "apply_encore_restriction": return _apply_encore_restriction(state, event)
    if effect == "complete_encore_restricted_active_turn": return _complete_encore_turn(state, event)
    if effect == "apply_disable_restriction": return _apply_disable_restriction(state, event)
    if effect == "complete_disable_restricted_active_turn": return _complete_disable_turn(state, event)
    if effect == "set_current_opponent_response_set":
        return _set_current_opponent_response_set(state, event)
    if effect == "set_current_opponent_switch_response_set":
        return _set_current_opponent_switch_response_set(state, event)
    if effect == "set_current_opponent_switch_target_combat":
        return _set_current_opponent_switch_target_combat(state, event)
    if effect == "set_current_terrain":
        return _set_current_terrain(state, event)
    if effect == "set_current_battle_format":
        return _set_current_battle_format(state, event)
    if effect == "set_current_side_conditions":
        return _set_current_side_conditions(state, event)
    if effect in {"apply_exact_hp_transition", "apply_exact_hp_recovery"}:
        pokemon = _pokemon(state, event); before, after = _value(event, "hp_before"), _value(event, "hp_after")
        if pokemon is None or not _exact(before) or not _exact(after) or (effect == "apply_exact_hp_transition" and before < after) or (effect == "apply_exact_hp_recovery" and after < before): return _conflict(event, "invalid_exact_hp_transition")
        if pokemon.get("fainted") is True: return _conflict(event, "post_faint_hp_transition_unsupported")
        if effect == "apply_exact_hp_recovery" and (before == 0 or pokemon.get("fainted") is True): return _conflict(event, "recovery_after_faint_unsupported")
        current, maximum = pokemon.get("current_hp", "unknown"), pokemon.get("max_hp", "unknown")
        if current is not None and not _unknown(current) and current != before: return _conflict(event, "current_hp_mismatch")
        if not _unknown(maximum) and _exact(maximum) and after > maximum: return _conflict(event, "hp_after_exceeds_max")
        pokemon["current_hp"] = after; _mark(pokemon, "current_hp", event); return None
    if effect == "switch_active": return _switch(state, event)
    if effect == "set_switch_permission": return _set_switch_permission(state, event)
    if effect == "clear_switch_permission": return _clear_switch_permission(state, event)
    if effect == "set_ability_applicability": return _set_ability_applicability(state, event)
    if effect == "clear_ability_applicability": return _clear_ability_applicability(state, event)
    if effect == "set_ability_interaction": return _set_ability_interaction(state, event)
    if effect == "clear_ability_interaction": return _clear_ability_interaction(state, event)
    if effect in {"set_switch_entry_intimidate", "clear_switch_entry_intimidate"}:
        source = {"side": _value(event, "source_side"), "slot_index": _value(event, "source_slot_index"), "pokemon_id": _value(event, "source_pokemon_id")}
        target = {"side": _value(event, "target_side"), "slot_index": _value(event, "target_slot_index"), "pokemon_id": _value(event, "target_pokemon_id")}
        if _pokemon(state, {"side": source["side"], "slot_index": source["slot_index"], "pokemon_id": source["pokemon_id"]}) is None or not _active_identity_matches(state, "opponent", target["slot_index"], target["pokemon_id"]):
            return _conflict(event, "invalid_switch_entry_intimidate")
        try:
            state["switch_entry_intimidate_authority"] = build_switch_entry_intimidate_authority(session_id=state["session_id"], source=source, target=target, interaction="unknown" if effect.startswith("clear") else _value(event, "interaction"), target_attack_stage="unknown" if effect.startswith("clear") else _value(event, "target_attack_stage"))
        except ValueError:
            return _conflict(event, "invalid_switch_entry_intimidate")
        return None
    if effect in {"set_switch_entry_download", "clear_switch_entry_download"}:
        source = {"side": _value(event, "source_side"), "slot_index": _value(event, "source_slot_index"), "pokemon_id": _value(event, "source_pokemon_id")}
        target = {"side": _value(event, "target_side"), "slot_index": _value(event, "target_slot_index"), "pokemon_id": _value(event, "target_pokemon_id")}
        if _pokemon(state, {"side": source["side"], "slot_index": source["slot_index"], "pokemon_id": source["pokemon_id"]}) is None or not _active_identity_matches(state, "opponent", target["slot_index"], target["pokemon_id"]):
            return _conflict(event, "invalid_switch_entry_download")
        try:
            state["switch_entry_download_authority"] = build_switch_entry_download_authority(session_id=state["session_id"], source=source, target=target, applicability="unknown" if effect.startswith("clear") else _value(event, "applicability"), target_defense="unknown" if effect.startswith("clear") else _value(event, "target_defense"), target_special_defense="unknown" if effect.startswith("clear") else _value(event, "target_special_defense"))
        except ValueError:
            return _conflict(event, "invalid_switch_entry_download")
        return None
    if effect in {"set_identity_groundedness","clear_identity_groundedness"}:
        side,slot,pid=_value(event,"side"),_value(event,"slot_index"),_value(event,"pokemon_id")
        if not _active_identity_matches(state,side,slot,pid): return _conflict(event,"invalid_identity_groundedness")
        status="unknown" if effect.startswith("clear") else _value(event,"groundedness_status")
        try: state["identity_groundedness_context"]=build_groundedness(session_id=state["session_id"],side=side,slot_index=slot,pokemon_id=pid,status=status)
        except ValueError: return _conflict(event,"invalid_identity_groundedness")
        return None
    if effect in {"set_prospective_groundedness", "clear_prospective_groundedness"}:
        pokemon = _pokemon(state, event)
        if pokemon is None:
            return _conflict(event, "invalid_prospective_groundedness")
        side, slot, pid = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")
        status = "unknown" if effect.startswith("clear") else _value(event, "groundedness_status")
        try:
            pokemon["prospective_groundedness_context"] = build_groundedness(
                session_id=state["session_id"], side=side, slot_index=slot, pokemon_id=pid, status=status,
            )
        except ValueError:
            return _conflict(event, "invalid_prospective_groundedness")
        return None
    if effect in {"set_prospective_speed_stage", "clear_prospective_speed_stage"}:
        pokemon = _pokemon(state, event)
        if pokemon is None:
            return _conflict(event, "invalid_prospective_speed_stage")
        try:
            pokemon["prospective_speed_stage_context"] = build_prospective_speed_stage(session_id=state["session_id"], side=_value(event, "side"), slot_index=_value(event, "slot_index"), pokemon_id=_value(event, "pokemon_id"), stage="unknown" if effect.startswith("clear") else _value(event, "speed_stage"))
        except ValueError:
            return _conflict(event, "invalid_prospective_speed_stage")
        return None
    if effect in {"set_prospective_offensive_stages", "clear_prospective_offensive_stages"}:
        pokemon = _pokemon(state, event)
        if pokemon is None:
            return _conflict(event, "invalid_prospective_offensive_stages")
        try:
            pokemon["prospective_offensive_stages_context"] = build_prospective_offensive_stages(session_id=state["session_id"], side=_value(event, "side"), slot_index=_value(event, "slot_index"), pokemon_id=_value(event, "pokemon_id"), attack="unknown" if effect.startswith("clear") else _value(event, "attack_stage"), special_attack="unknown" if effect.startswith("clear") else _value(event, "special_attack_stage"))
        except ValueError:
            return _conflict(event, "invalid_prospective_offensive_stages")
        return None
    if effect in {"set_prospective_entry_interactions", "clear_prospective_entry_interactions"}:
        pokemon = _pokemon(state, event)
        if pokemon is None:
            return _conflict(event, "invalid_prospective_entry_interactions")
        try:
            pokemon["prospective_entry_interactions_context"] = build_prospective_entry_interactions(session_id=state["session_id"], side=_value(event, "side"), slot_index=_value(event, "slot_index"), pokemon_id=_value(event, "pokemon_id"), toxic_spikes="unknown" if effect.startswith("clear") else _value(event, "toxic_spikes_interaction"), sticky_web="unknown" if effect.startswith("clear") else _value(event, "sticky_web_interaction"))
        except ValueError:
            return _conflict(event, "invalid_prospective_entry_interactions")
        return None
    if effect in {"set_switch_hazards","clear_switch_hazards"}:
        side=_value(event,"side")
        try: state["switch_hazard_context"]=build_switch_hazard_context(session_id=state["session_id"],affected_side=side,stealth_rock="unknown" if effect.startswith("clear") else _value(event,"stealth_rock"),spikes_layers="unknown" if effect.startswith("clear") else _value(event,"spikes_layers"),toxic_spikes_layers="unknown" if effect.startswith("clear") else _value(event,"toxic_spikes_layers"),sticky_web="unknown" if effect.startswith("clear") else _value(event,"sticky_web"))
        except ValueError: return _conflict(event,"invalid_switch_hazard_context")
        return None
    if effect == "set_observed_tailwind":
        return _observed_tailwind(state, event)
    if effect == "set_observed_trick_room":
        return _observed_trick_room(state, event)
    if effect == "set_same_turn_event":
        return _same_turn_event(state, event)
    if effect == "set_current_crit_volatiles":
        return _set_current_crit_volatiles(state, event)
    if effect == "mark_fainted":
        pokemon = _pokemon(state, event)
        if pokemon is None: return _conflict(event, "missing_faint_target")
        if pokemon.get("fainted") is True: return _conflict(event, "already_fainted")
        if pokemon.get("current_hp") != 0: return _conflict(event, "faint_requires_exact_zero_hp")
        pokemon["fainted"] = True; _mark(pokemon, "fainted", event)
        _increment_supreme_overlord_faint_history(state, _value(event, "side"), event)
        pokemon["toxic_progression"] = make_unknown_battle_fact()
        _invalidate_current_crit_volatiles(pokemon)
        context = state.get("substitute_state_context")
        if isinstance(context, dict):
            owner = {"session_id": state["session_id"], "side": _value(event, "side"), "slot_index": _value(event, "slot_index"), "pokemon_id": _value(event, "pokemon_id")}
            context = update_substitute_state_context(context=context, session_id=state["session_id"], owner=owner, state="known_inactive", substitute_hp=None, provenance="runtime_faint_lifecycle_v1")
            if context is None:
                return _conflict(event, "invalid_substitute_faint_lifecycle")
            state["substitute_state_context"] = context
        _invalidate_same_turn_events(state, _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id"))
        return None
    if effect == "set_current_stat_stage":
        pokemon = _pokemon(state, event); stat, stage = _value(event, "stat"), _value(event, "stage")
        if pokemon is None or stat not in {"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"} or not isinstance(stage, int) or isinstance(stage, bool) or not -6 <= stage <= 6:
            return _conflict(event, "invalid_current_stat_stage")
        if pokemon.get("fainted") is True: return _conflict(event, "post_faint_stat_stage_unsupported")
        stages = pokemon.get("stat_stages", {})
        if not isinstance(stages, dict) or any(key not in {"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"} or not isinstance(value, int) or isinstance(value, bool) or not -6 <= value <= 6 for key, value in stages.items()):
            return _conflict(event, "invalid_current_stat_stage_state")
        pokemon["stat_stages"] = {**stages, stat: stage}; _mark(pokemon, "stat_stages", event); return None
    if effect == "record_known_move":
        pokemon = _pokemon(state, event); move_id = _value(event, "canonical_move_id")
        if pokemon is None or not _canonical_move_id(move_id): return _conflict(event, "invalid_canonical_move_id")
        if pokemon.get("fainted") is True: return _conflict(event, "post_faint_known_move_transition_unsupported")
        known_moves = pokemon.get("known_move_ids", [])
        if not isinstance(known_moves, list) or len(set(known_moves)) != len(known_moves) or any(not _canonical_move_id(move) for move in known_moves):
            return _conflict(event, "invalid_known_move_state")
        if move_id in known_moves: return None
        if len(known_moves) >= 4: return _conflict(event, "known_move_capacity_exceeded")
        pokemon["known_move_ids"] = [*known_moves, move_id]
        provenance = pokemon.get("known_move_ids_provenance")
        if provenance is None:
            provenance = {}
        if not isinstance(provenance, dict) or any(key not in known_moves or not _valid_known_move_observation(value) for key, value in provenance.items()):
            return _conflict(event, "invalid_known_move_provenance")
        provenance[move_id] = _provenance(event) | {"event_kind": "used_move_observed"}
        pokemon["known_move_ids_provenance"] = provenance
        return None
    if effect in {"set_condition", "clear_condition", "consume_item", "remove_item"}: return _pokemon_effect(state, event)
    if effect in {"start_weather", "end_weather", "start_terrain", "end_terrain"}: return _field_effect(state, event)
    if effect in {"start_side_condition", "end_side_condition"}: return _side_condition(state, event)
    return _conflict(event, "unsupported_effect")


def _valid_same_turn_event(value, session_id):
    return isinstance(value, dict) and value.get("session_id") == session_id and value.get("predicate") in {"received_qualifying_direct_damage", "acted_earlier_this_turn", "lost_hp_this_turn", "qualifying_direct_damage_dealt"} and isinstance(value.get("occurred"), bool) and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and all(_identity_values(value, *names) for names in (("side", "slot_index", "pokemon_id"), ("target_side", "target_slot_index", "target_pokemon_id"))) and (value.get("side"), value.get("slot_index"), value.get("pokemon_id")) != (value.get("target_side"), value.get("target_slot_index"), value.get("target_pokemon_id")) and isinstance(value.get("provenance"), dict)


def _valid_first_end_of_turn_phase(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    return isinstance(value, dict) and value.get("session_id") == session_id and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"


def _phase_already_reached(state, turn_number):
    phases = state.get("first_end_of_turn_context", [])
    return isinstance(turn_number, int) and not isinstance(turn_number, bool) and isinstance(phases, list) and any(
        isinstance(phase, dict) and phase.get("turn_number") == turn_number for phase in phases
    )


def _mark_first_end_of_turn_reached(state, event):
    turn_number = _value(event, "turn_number")
    phases = state.setdefault("first_end_of_turn_context", [])
    if not isinstance(phases, list):
        return _conflict(event, "invalid_first_end_of_turn_state")
    existing = next((phase for phase in phases if isinstance(phase, dict) and phase.get("turn_number") == turn_number), None)
    if existing is not None:
        return None
    phases.append({"session_id": state["session_id"], "turn_number": turn_number, "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}})
    _apply_leftovers_end_of_turn_recovery(state, event)
    _apply_black_sludge_end_of_turn(state, event)
    _apply_toxic_end_of_turn(state, event)
    _apply_rain_dish_end_of_turn(state, event)
    _apply_ice_body_end_of_turn(state, event)
    _apply_solar_power_end_of_turn(state, event)
    _apply_dry_skin_end_of_turn(state, event)
    _apply_sandstorm_end_of_turn(state, event)
    return None


def _set_current_type(state, event):
    """Replace one identity-owned current type from an explicit observation only."""
    pokemon = _pokemon(state, event)
    turn_number = _value(event, "turn_number")
    if pokemon is None or pokemon.get("fainted") is True:
        return _conflict(event, "invalid_current_type_owner")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_type_turn")
    try:
        normalized = normalize_current_type_authority({
            "side": _value(event, "side"), "state": "known", "types": _value(event, "types"),
            "status": "user_confirmed", "source": "user_confirmed_current_type",
            "authority_provenance": "user_confirmed_current",
        })
    except ValueError:
        return _conflict(event, "invalid_current_type")
    prior = pokemon.get("current_type_provenance")
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_type_observation")
    pokemon["current_type"] = deepcopy(normalized["types"])
    pokemon["current_type_provenance"] = _provenance(event) | {
        "event_kind": "current_type_observed", "trust": _value(event, "trust"), "turn_number": turn_number,
    }
    return None


def _set_current_condition(state, event):
    """Replace one current major condition from a production observation."""
    pokemon, turn_number, condition = _pokemon(state, event), _value(event, "turn_number"), _value(event, "condition")
    if pokemon is None or not _active_identity_matches(state, _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")) or pokemon.get("fainted") is True:
        return _conflict(event, "invalid_current_condition_owner")
    if condition not in {"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"} or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_condition")
    prior = pokemon.get("condition_provenance")
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) and prior.get("event_kind") == "current_condition_observed" else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_condition_observation")
    pokemon["condition"] = None if condition == "none" else condition
    pokemon["condition_provenance"] = _provenance(event) | {
        "event_kind": "current_condition_observed", "trust": _value(event, "trust"),
        "turn_number": turn_number, "condition": condition,
    }
    pokemon["toxic_progression"] = make_unknown_battle_fact()
    return None


def _set_pending_status_action_execution(state, event):
    """Store one explicit present-tense sleep/freeze action outcome.

    This is deliberately an observation of the already-resolved action result,
    not a sleep-duration or freeze-thaw mechanics model.
    """
    pokemon = _pokemon(state, event)
    side, slot, pokemon_id = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")
    decision_point, action_id, move_id = _value(event, "decision_point"), _value(event, "action_id"), _value(event, "move_id")
    condition, execution_state, blocker, turn = _value(event, "condition"), _value(event, "execution_state"), _value(event, "blocker"), _value(event, "turn_number")
    provenance = pokemon.get("condition_provenance") if isinstance(pokemon, dict) else None
    if (
        pokemon is None or not _active_identity_matches(state, side, slot, pokemon_id)
        or not all(isinstance(value, str) and bool(value) for value in (decision_point, action_id, move_id))
        or condition not in {"sleep", "freeze"} or execution_state not in {"executable", "blocked"}
        or (execution_state == "executable" and blocker is not None)
        or (execution_state == "blocked" and blocker != condition)
        or _value(event, "trust") != "user_confirmed_observation"
        or not isinstance(turn, int) or isinstance(turn, bool) or turn < 1
        or pokemon.get("condition") != condition
        or not isinstance(provenance, dict) or provenance.get("event_kind") != "current_condition_observed"
        or provenance.get("trust") != "user_confirmed_observation" or provenance.get("condition") != condition
    ):
        return _conflict(event, "invalid_pending_status_action_execution_observation")
    candidate = {
        "schema_version": "pending-status-action-execution-context-v1", "session_id": state["session_id"],
        "decision_point": decision_point, "actor": {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon_id},
        "action_id": action_id, "move_id": move_id, "condition": condition,
        "execution_state": execution_state, "blocker": blocker,
        "provenance": _provenance(event) | {"event_kind": "pending_status_action_execution_observed", "trust": "user_confirmed_observation", "turn_number": turn},
    }
    prior = state.get("pending_status_action_execution_context")
    if prior is not None:
        prior_sequence = prior.get("provenance", {}).get("source_sequence") if isinstance(prior, dict) else None
        if prior_sequence == candidate["provenance"]["source_sequence"] and prior != candidate:
            return _conflict(event, "conflicting_pending_status_action_execution_sequence")
        if isinstance(prior_sequence, int) and prior_sequence > candidate["provenance"]["source_sequence"]:
            return _conflict(event, "stale_pending_status_action_execution_observation")
    state["pending_status_action_execution_context"] = candidate
    return None


def _set_mat_block_active_entry_eligibility(state, event):
    pokemon = _pokemon(state, event)
    side, slot, pokemon_id = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")
    decision_point, action_id, move_id = _value(event, "decision_point"), _value(event, "action_id"), _value(event, "move_id")
    token, eligibility, turn = _value(event, "active_entry_token"), _value(event, "eligibility"), _value(event, "turn_number")
    if pokemon is None or not _active_identity_matches(state, side, slot, pokemon_id) or not all(isinstance(v, str) and v for v in (decision_point, action_id, token)) or move_id != "mat-block" or eligibility not in {"eligible", "ineligible"} or _value(event, "trust") != "user_confirmed_observation" or not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
        return _conflict(event, "invalid_mat_block_active_entry_eligibility_observation")
    candidate = {"schema_version": "mat-block-active-entry-eligibility-context-v1", "session_id": state["session_id"], "decision_point": decision_point, "actor": {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon_id}, "action_id": action_id, "move_id": move_id, "active_entry_token": token, "eligibility": eligibility, "provenance": _provenance(event) | {"event_kind": "mat_block_active_entry_eligibility_observed", "trust": "user_confirmed_observation", "turn_number": turn}}
    prior = state.get("mat_block_active_entry_eligibility_context")
    if isinstance(prior, dict):
        prior_sequence = prior.get("provenance", {}).get("source_sequence")
        if prior_sequence == candidate["provenance"]["source_sequence"] and prior != candidate: return _conflict(event, "conflicting_mat_block_active_entry_eligibility_sequence")
        if isinstance(prior_sequence, int) and prior_sequence > candidate["provenance"]["source_sequence"]: return _conflict(event, "stale_mat_block_active_entry_eligibility_observation")
    state["mat_block_active_entry_eligibility_context"] = candidate
    return None


def _set_fake_out_active_entry_eligibility(state, event):
    pokemon = _pokemon(state, event)
    side, slot, pokemon_id = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")
    decision_point, action_id, move_id = _value(event, "decision_point"), _value(event, "action_id"), _value(event, "move_id")
    token, eligibility, turn = _value(event, "active_entry_token"), _value(event, "eligibility"), _value(event, "turn_number")
    if pokemon is None or not _active_identity_matches(state, side, slot, pokemon_id) or not all(isinstance(v, str) and v for v in (decision_point, action_id, token)) or move_id != "fake-out" or eligibility not in {"eligible", "ineligible"} or _value(event, "trust") != "user_confirmed_observation" or not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
        return _conflict(event, "invalid_fake_out_active_entry_eligibility_observation")
    candidate = {"schema_version": "fake-out-active-entry-eligibility-context-v1", "session_id": state["session_id"], "decision_point": decision_point, "actor": {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon_id}, "action_id": action_id, "move_id": move_id, "active_entry_token": token, "eligibility": eligibility, "provenance": _provenance(event) | {"event_kind": "fake_out_active_entry_eligibility_observed", "trust": "user_confirmed_observation", "turn_number": turn}}
    prior = state.get("fake_out_active_entry_eligibility_context")
    if isinstance(prior, dict):
        prior_sequence = prior.get("provenance", {}).get("source_sequence")
        if prior_sequence == candidate["provenance"]["source_sequence"] and prior != candidate: return _conflict(event, "conflicting_fake_out_active_entry_eligibility_sequence")
        if isinstance(prior_sequence, int) and prior_sequence > candidate["provenance"]["source_sequence"]: return _conflict(event, "stale_fake_out_active_entry_eligibility_observation")
    state["fake_out_active_entry_eligibility_context"] = candidate
    return None


def _set_doubles_active_topology(state, event):
    """Store exact current doubles occupants without changing legacy active slots."""
    rows, turn = _value(event, "active_owners"), _value(event, "turn_number")
    if state.get("field", {}).get("battle_format") != "doubles" or not isinstance(rows, list) or len(rows) != 4 or not isinstance(turn, int) or isinstance(turn, bool) or turn < 1 or _value(event, "trust") != "user_confirmed_observation":
        return _conflict(event, "invalid_doubles_active_topology_observation")
    owners = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"side", "active_slot_index", "pokemon_id", "active"} or row.get("side") not in {"self", "opponent"} or not isinstance(row.get("active_slot_index"), int) or isinstance(row.get("active_slot_index"), bool) or row["active_slot_index"] < 0 or not isinstance(row.get("pokemon_id"), str) or not row["pokemon_id"] or row.get("active") is not True:
            return _conflict(event, "invalid_doubles_active_topology_observation")
        side = _side(state, row["side"]); roster = side.get("pokemon") if isinstance(side, dict) else None; pokemon = roster.get(row["active_slot_index"], roster.get(str(row["active_slot_index"]))) if isinstance(roster, dict) else None
        if not isinstance(pokemon, dict) or pokemon.get("pokemon_id", pokemon.get("name_en")) != row["pokemon_id"]:
            return _conflict(event, "doubles_active_topology_identity_mismatch")
        owners.append({"session_id": state["session_id"], "side": row["side"], "slot_index": row["active_slot_index"], "pokemon_id": row["pokemon_id"], "active": True})
    if len({(row["side"], row["slot_index"]) for row in owners}) != 4 or any(sum(row["side"] == side for row in owners) != 2 for side in ("self", "opponent")):
        return _conflict(event, "conflicting_doubles_active_topology")
    candidate = {"schema_version": "doubles-active-topology-context-v1", "session_id": state["session_id"], "active_owners": owners, "provenance": _provenance(event) | {"event_kind": "doubles_active_topology_observed", "trust": "user_confirmed_observation", "turn_number": turn}}
    prior = state.get("doubles_active_topology_context")
    if isinstance(prior, dict):
        sequence = prior.get("provenance", {}).get("source_sequence")
        if sequence == candidate["provenance"]["source_sequence"] and prior != candidate: return _conflict(event, "conflicting_doubles_active_topology_sequence")
        if isinstance(sequence, int) and sequence > candidate["provenance"]["source_sequence"]: return _conflict(event, "stale_doubles_active_topology_observation")
    state["doubles_active_topology_context"] = candidate
    return None


def _set_selected_action_targeting(state, event):
    """Store a selected target only as an exact action-bound current observation."""
    pokemon = _pokemon(state, event)
    side, slot, pokemon_id = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")
    decision_point, action_id, move_id, selected, turn = _value(event, "decision_point"), _value(event, "action_id"), _value(event, "move_id"), _value(event, "selected_target"), _value(event, "turn_number")
    if pokemon is None or not _active_identity_matches(state, side, slot, pokemon_id) or not all(isinstance(value, str) and bool(value) for value in (decision_point, action_id, move_id)) or not isinstance(turn, int) or isinstance(turn, bool) or turn < 1 or _value(event, "trust") != "user_confirmed_observation":
        return _conflict(event, "invalid_selected_action_targeting_observation")
    target = None
    if selected is not None:
        if not isinstance(selected, dict) or set(selected) != {"side", "active_slot_index", "pokemon_id"} or selected.get("side") not in {"self", "opponent"} or isinstance(selected.get("active_slot_index"), bool) or not isinstance(selected.get("active_slot_index"), int) or selected["active_slot_index"] < 0 or not isinstance(selected.get("pokemon_id"), str) or not selected["pokemon_id"]:
            return _conflict(event, "invalid_selected_action_target")
        target = {"session_id": state["session_id"], "side": selected["side"], "slot_index": selected["active_slot_index"], "pokemon_id": selected["pokemon_id"]}
    candidate = {"schema_version": "selected-action-targeting-context-v1", "session_id": state["session_id"], "decision_point": decision_point, "actor": {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon_id}, "action_id": action_id, "move_id": move_id, "selected_target": target, "provenance": _provenance(event) | {"event_kind": "selected_action_targeting_observed", "trust": "user_confirmed_observation", "turn_number": turn}}
    prior = state.get("selected_action_targeting_context")
    if isinstance(prior, dict):
        sequence = prior.get("provenance", {}).get("source_sequence")
        if sequence == candidate["provenance"]["source_sequence"] and prior != candidate: return _conflict(event, "conflicting_selected_action_targeting_sequence")
        if isinstance(sequence, int) and sequence > candidate["provenance"]["source_sequence"]: return _conflict(event, "stale_selected_action_targeting_observation")
    state["selected_action_targeting_context"] = candidate
    return None


def _set_current_level(state, event):
    """Capture an exact identity-bound level from a current observation."""
    pokemon, turn_number, level = _pokemon(state, event), _value(event, "turn_number"), _value(event, "level")
    if pokemon is None or not _active_identity_matches(state, _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")) or pokemon.get("fainted") is True:
        return _conflict(event, "invalid_current_level_owner")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1 or not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 100:
        return _conflict(event, "invalid_current_level")
    pokemon["current_level"] = level
    pokemon["current_level_provenance"] = _provenance(event) | {
        "event_kind": "current_level_observed", "trust": _value(event, "trust"), "turn_number": turn_number,
    }
    return None


def _set_current_final_combat_stat(state, event):
    """Capture a stage-unmodified final stat; stage remains separate authority."""
    pokemon, turn_number = _pokemon(state, event), _value(event, "turn_number")
    stat, value = _value(event, "stat"), _value(event, "value")
    if pokemon is None or not _active_identity_matches(state, _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")) or pokemon.get("fainted") is True:
        return _conflict(event, "invalid_current_final_combat_stat_owner")
    if stat not in {"attack", "defense", "special-attack", "special-defense", "speed"} or not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 9999 or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_final_combat_stat")
    stats = pokemon.get("current_final_stats")
    if stats is None:
        stats = {}
    if not isinstance(stats, dict) or not _valid_current_final_stats(stats):
        return _conflict(event, "invalid_current_final_combat_stat_state")
    stats[stat] = {"value": value, "provenance": _provenance(event) | {"event_kind": "current_final_combat_stat_observed", "trust": _value(event, "trust"), "turn_number": turn_number}}
    pokemon["current_final_stats"] = stats
    return None


def _set_current_opponent_switch_target_combat(state, event):
    """Set one explicitly confirmed bench target without making it active."""
    pokemon, turn = _pokemon(state, event), _value(event, "turn_number")
    payload = {key: _value(event, key) for key in ("current_hp", "max_hp", "fainted", "types", "final_stats", "stages", "condition", "item", "ability")}
    if pokemon is None or _value(event, "side") != "opponent" or not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
        return _conflict(event, "invalid_switch_target_combat_owner")
    hp, maximum, fainted = payload["current_hp"], payload["max_hp"], payload["fainted"]
    stats, stages = payload["final_stats"], payload["stages"]
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1 or not 0 <= hp <= maximum or not isinstance(fainted, bool) or fainted is not (hp == 0) or not isinstance(stats, dict) or not isinstance(stages, dict):
        return _conflict(event, "invalid_switch_target_combat_payload")
    pokemon["current_hp"], pokemon["max_hp"], pokemon["fainted"] = hp, maximum, fainted
    pokemon["current_type"] = deepcopy(payload["types"])
    pokemon["current_final_stats"] = {stat: {"value": value, "provenance": _provenance(event) | {"event_kind": "current_opponent_switch_target_combat_observed", "trust": _value(event, "trust"), "turn_number": turn}} for stat, value in stats.items()}
    pokemon["stat_stages"] = deepcopy(stages)
    pokemon["condition"] = None if payload["condition"] == "none" else payload["condition"]
    item = payload["item"]; pokemon["known_item"] = item.get("item") if item.get("status") == "known" else None
    pokemon["current_ability"] = payload["ability"]
    for field in ("current_hp", "max_hp", "fainted", "current_type", "stat_stages", "condition", "known_item", "current_ability"):
        _mark(pokemon, field, event)
    for field in ("current_hp", "max_hp", "fainted", "stat_stages"):
        pokemon[f"{field}_provenance"] |= {"event_kind": "current_opponent_switch_target_combat_observed", "trust": _value(event, "trust"), "turn_number": turn}
    pokemon["current_type_provenance"] |= {"event_kind": "current_opponent_switch_target_combat_observed", "trust": _value(event, "trust"), "turn_number": turn}
    pokemon["condition_provenance"] |= {"event_kind": "current_opponent_switch_target_combat_observed", "trust": _value(event, "trust"), "turn_number": turn, "condition": payload["condition"]}
    pokemon["known_item_provenance"] |= {"event_kind": "current_opponent_switch_target_combat_observed", "trust": _value(event, "trust"), "turn_number": turn, "status": item.get("status")}
    pokemon["current_ability_provenance"] |= {"event_kind": "current_opponent_switch_target_combat_observed", "trust": _value(event, "trust"), "turn_number": turn}
    return None


def _set_current_substitute(state, event):
    """Record observed Substitute state; this never predicts cost or damage."""
    pokemon, turn_number = _pokemon(state, event), _value(event, "turn_number")
    status, hp = _value(event, "state"), _value(event, "substitute_hp")
    if pokemon is None or not _active_identity_matches(state, _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")) or pokemon.get("fainted") is True:
        return _conflict(event, "invalid_current_substitute_owner")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1 or status not in {"known_active", "known_inactive"} or (status == "known_active" and (not isinstance(hp, int) or isinstance(hp, bool) or hp <= 0)) or (status == "known_inactive" and hp is not None):
        return _conflict(event, "invalid_current_substitute")
    owner = {"session_id": state["session_id"], "side": _value(event, "side"), "slot_index": _value(event, "slot_index"), "pokemon_id": _value(event, "pokemon_id")}
    context = update_substitute_state_context(
        context=state.get("substitute_state_context"), session_id=state["session_id"], owner=owner,
        state=status, substitute_hp=hp, provenance="runtime_observed_substitute_state_v1",
    )
    if context is None:
        return _conflict(event, "invalid_current_substitute")
    context["runtime_provenance"] = _provenance(event) | {
        "event_kind": "substitute_state_observed", "trust": _value(event, "trust"), "turn_number": turn_number,
    }
    state["substitute_state_context"] = context
    return None


def _set_current_weather(state, event):
    """Replace global weather from an explicit current-weather observation."""
    field, weather, turn_number = state.get("field"), _value(event, "weather"), _value(event, "turn_number")
    if not isinstance(field, dict) or weather not in {"none", "sun", "rain", "sandstorm", "snow"} or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_weather")
    prior = field.get("weather_provenance")
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_weather_observation")
    field["weather"] = weather
    field["weather_provenance"] = _provenance(event) | {
        "event_kind": "current_weather_observed", "trust": _value(event, "trust"), "turn_number": turn_number,
    }
    return None


def _set_current_ability(state, event):
    """Replace one identity-owned ability from an explicit current observation."""
    pokemon, turn_number = _pokemon(state, event), _value(event, "turn_number")
    if pokemon is None or pokemon.get("fainted") is True or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_ability_owner")
    try:
        ability = normalize_user_confirmed_current_ability({
            "side": _value(event, "side"), "ability": _value(event, "ability"),
            "status": "user_confirmed", "source": "user_confirmed_current_ability",
        })["ability"]
    except ValueError:
        return _conflict(event, "invalid_current_ability")
    prior = pokemon.get("current_ability_provenance")
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_ability_observation")
    pokemon["current_ability"] = ability
    pokemon["current_ability_provenance"] = _provenance(event) | {
        "event_kind": "current_ability_observed", "trust": _value(event, "trust"), "turn_number": turn_number,
    }
    return None


def _set_current_item(state, event):
    """Replace one identity-bound held-item authority without inferring absence."""
    pokemon, turn_number = _pokemon(state, event), _value(event, "turn_number")
    status, item = _value(event, "status"), _value(event, "item")
    if pokemon is None or pokemon.get("fainted") is True or status not in {"known", "known_absent"} or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_item_owner")
    if (status == "known" and (not isinstance(item, str) or not item)) or (status == "known_absent" and item is not None):
        return _conflict(event, "invalid_current_item")
    prior = pokemon.get("known_item_provenance")
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_item_observation")
    pokemon["known_item"] = item if status == "known" else None
    pokemon["known_item_provenance"] = _provenance(event) | {"event_kind": "current_item_observed", "trust": _value(event, "trust"), "turn_number": turn_number, "status": status}
    return None


def _set_current_move_usability(state, event):
    """Record a single explicit, current selectability observation.

    This deliberately has no PP or lock-mechanics inference path.  A later
    D0 authority may use the fact only while it remains the newest reducer
    observation for this exact active opponent identity.
    """
    pokemon, side = _pokemon(state, event), _value(event, "side")
    move_id, status, reason, turn_number = (
        _value(event, "canonical_move_id"), _value(event, "usability"),
        _value(event, "reason"), _value(event, "turn_number"),
    )
    if (
        side != "opponent" or pokemon is None
        or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id"))
        or pokemon.get("fainted") is True or not _canonical_move_id(move_id)
        or status not in {"known_usable", "known_unusable"}
        or _value(event, "trust") != "user_confirmed_observation"
        or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1
    ):
        return _conflict(event, "invalid_current_move_usability_observation")
    allowed_reasons = {"no_pp", "disabled", "choice_lock", "encore_restriction", "other_supported_restriction", "observed_unclassified"}
    if (status == "known_usable" and reason is not None) or (status == "known_unusable" and reason not in allowed_reasons):
        return _conflict(event, "invalid_current_move_usability_reason")
    known_moves = pokemon.get("known_move_ids", [])
    if not isinstance(known_moves, list) or move_id not in known_moves:
        return _conflict(event, "current_move_usability_requires_known_move")
    current = pokemon.get("current_move_usability")
    if current is None:
        current = {}
    if not _valid_current_move_usability(current, known_moves):
        return _conflict(event, "invalid_current_move_usability_state")
    prior = current.get(move_id, {}).get("provenance") if isinstance(current.get(move_id), dict) else None
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_move_usability_observation")
    pokemon["current_move_usability"] = {
        **current,
        move_id: {
            "status": status, "reason": reason,
            "provenance": _provenance(event) | {
                "event_kind": "current_move_usability_observed",
                "trust": "user_confirmed_observation", "turn_number": turn_number,
            },
        },
    }
    return None


def _set_current_opponent_response_set(state, event):
    """Apply one explicit current complete opponent move-response snapshot."""
    pokemon, side = _pokemon(state, event), _value(event, "side")
    moves, usability, turn_number = _value(event, "move_ids"), _value(event, "move_usability"), _value(event, "turn_number")
    if (
        side != "opponent" or pokemon is None
        or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id"))
        or pokemon.get("fainted") is True or not isinstance(moves, list) or len(moves) != 4
        or len(set(moves)) != 4 or any(not _canonical_move_id(move) for move in moves)
        or not isinstance(usability, dict) or set(usability) != set(moves)
        or _value(event, "trust") != "user_confirmed_observation"
        or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1
    ):
        return _conflict(event, "invalid_current_opponent_response_set_observation")
    allowed_reasons = {"no_pp", "disabled", "choice_lock", "encore_restriction", "other_supported_restriction", "observed_unclassified"}
    normalized = {}
    for move in moves:
        row = usability.get(move)
        if not isinstance(row, dict) or set(row) != {"status", "reason"} or row.get("status") not in {"known_usable", "known_unusable"}:
            return _conflict(event, "invalid_current_opponent_response_set_usability")
        if (row["status"] == "known_usable" and row["reason"] is not None) or (row["status"] == "known_unusable" and row["reason"] not in allowed_reasons):
            return _conflict(event, "invalid_current_opponent_response_set_usability")
        normalized[move] = {"status": row["status"], "reason": row["reason"]}
    provenance = _provenance(event) | {"event_kind": "current_opponent_response_set_observed", "trust": "user_confirmed_observation", "turn_number": turn_number}
    pokemon["known_move_ids"] = list(moves)
    pokemon["known_move_ids_provenance"] = {move: deepcopy(provenance) for move in moves}
    pokemon["current_move_usability"] = {move: {**row, "provenance": deepcopy(provenance)} for move, row in normalized.items()}
    pokemon["current_opponent_response_set"] = {"moveset_completeness": "complete", "move_ids": list(moves), "provenance": deepcopy(provenance)}
    return None


def _set_current_opponent_switch_response_set(state, event):
    """Store only an explicit present-tense opponent switch-response snapshot."""
    side = _side(state, "opponent")
    if side is None or _value(event, "side") != "opponent" or not _active_identity_matches(state, "opponent", _value(event, "slot_index"), _value(event, "pokemon_id")):
        return _conflict(event, "invalid_current_opponent_switch_response_owner")
    permission, targets, turn = _value(event, "permission"), _value(event, "targets"), _value(event, "turn_number")
    if permission not in {"permitted", "blocked", "unknown"} or not isinstance(targets, list) or not isinstance(turn, int) or isinstance(turn, bool) or turn < 1 or _value(event, "trust") != "user_confirmed_observation":
        return _conflict(event, "invalid_current_opponent_switch_response_observation")
    roster, active, normalized = side.get("pokemon"), side.get("active_slot_index"), []
    seen = set()
    if not isinstance(roster, dict): return _conflict(event, "invalid_current_opponent_switch_response_roster")
    for row in targets:
        slot = row.get("slot_index") if isinstance(row, dict) else None
        pokemon_id = row.get("pokemon_id") if isinstance(row, dict) else None
        availability = row.get("availability") if isinstance(row, dict) else None
        pokemon = roster.get(slot)
        if (not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or slot == active or not isinstance(pokemon_id, str) or not pokemon_id or availability not in {"alive", "fainted", "unknown"} or (slot, pokemon_id) in seen or not isinstance(pokemon, dict) or pokemon.get("pokemon_id") != pokemon_id):
            return _conflict(event, "invalid_current_opponent_switch_response_target")
        seen.add((slot, pokemon_id)); normalized.append({"slot_index": slot, "pokemon_id": pokemon_id, "availability": availability})
    side["current_opponent_switch_response_set"] = {
        "schema_version": "current-opponent-switch-response-set-v1", "permission": permission,
        "target_set_completeness": "complete", "targets": normalized,
        "active_owner": {"session_id": state["session_id"], "side": "opponent", "slot_index": _value(event, "slot_index"), "pokemon_id": _value(event, "pokemon_id")},
        "provenance": _provenance(event) | {"event_kind": "current_opponent_switch_response_set_observed", "trust": "user_confirmed_observation", "turn_number": turn},
    }
    return None


def _set_current_terrain(state, event):
    field, terrain, turn_number = state.get("field"), _value(event, "terrain"), _value(event, "turn_number")
    if not isinstance(field, dict) or terrain not in {"none", "electric", "grassy", "misty", "psychic"} or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_terrain")
    prior = field.get("terrain_provenance")
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_terrain_observation")
    field["terrain"] = terrain
    field["terrain_provenance"] = _provenance(event) | {"event_kind": "current_terrain_observed", "trust": _value(event, "trust"), "turn_number": turn_number}
    return None


def _set_current_battle_format(state, event):
    """Capture session-stable format once; conflicting observations are rejected."""
    field, value, turn_number = state.get("field"), _value(event, "battle_format"), _value(event, "turn_number")
    if not isinstance(field, dict) or value not in {"singles", "doubles"} or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_battle_format")
    current = field.get("battle_format")
    if isinstance(current, str) and current != value:
        return _conflict(event, "conflicting_session_battle_format")
    field["battle_format"] = value
    field["battle_format_provenance"] = _provenance(event) | {"event_kind": "current_battle_format_observed", "trust": _value(event, "trust"), "turn_number": turn_number}
    return None


def _set_current_side_conditions(state, event):
    side, values, turn_number = _side(state, _value(event, "side")), _value(event, "side_conditions"), _value(event, "turn_number")
    allowed = {"reflect", "light-screen", "aurora-veil", "tailwind", "lucky-chant"}
    if side is None or not isinstance(values, list) or len(values) != len(set(values)) or any(value not in allowed for value in values) or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_side_conditions")
    prior = side.get("side_conditions_provenance")
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_side_conditions_observation")
    side["side_conditions"] = list(values)
    side["side_conditions_provenance"] = _provenance(event) | {"event_kind": "current_side_conditions_observed", "trust": _value(event, "trust"), "turn_number": turn_number}
    return None


def _set_current_crit_volatiles(state, event):
    pokemon, values, turn_number = _pokemon(state, event), _value(event, "crit_volatiles"), _value(event, "turn_number")
    if pokemon is None or not _active_identity_matches(state, _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")) or pokemon.get("fainted") is True or not isinstance(values, list) or len(values) != len(set(values)) or any(value not in {"focus-energy", "lansat", "dragon-cheer"} for value in values) or _value(event, "trust") != "user_confirmed_observation" or not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _conflict(event, "invalid_current_crit_volatiles")
    prior = pokemon.get("current_crit_volatiles_provenance")
    prior_turn = prior.get("turn_number") if isinstance(prior, dict) else None
    if isinstance(prior_turn, int) and not isinstance(prior_turn, bool) and turn_number < prior_turn:
        return _conflict(event, "stale_current_crit_volatile_observation")
    pokemon["current_crit_volatiles"] = list(values)
    pokemon["current_crit_volatiles_provenance"] = _provenance(event) | {"event_kind": "current_crit_volatiles_observed", "trust": _value(event, "trust"), "turn_number": turn_number}
    return None


def _invalidate_current_crit_volatiles(pokemon):
    if isinstance(pokemon, dict):
        pokemon["current_crit_volatiles"] = make_unknown_battle_fact()
        pokemon.pop("current_crit_volatiles_provenance", None)


def _apply_leftovers_end_of_turn_recovery(state, event):
    """Apply only exact held Leftovers for the living active owner at this phase."""
    results = state.setdefault("leftovers_end_of_turn_context", [])
    if not isinstance(results, list):
        return
    for side_name in ("self", "opponent"):
        side = _side(state, side_name)
        slot_index = side.get("active_slot_index") if isinstance(side, dict) else None
        roster = side.get("pokemon") if isinstance(side, dict) else None
        pokemon = roster.get(slot_index, roster.get(str(slot_index))) if isinstance(roster, dict) else None
        if not isinstance(slot_index, int) or isinstance(slot_index, bool) or not isinstance(pokemon, dict):
            continue
        pokemon_id = pokemon.get("pokemon_id", pokemon.get("name_en"))
        current_hp, maximum_hp = pokemon.get("current_hp"), pokemon.get("max_hp")
        if pokemon.get("known_item") != "leftovers" or pokemon.get("fainted") is not False or not isinstance(pokemon_id, str) or not pokemon_id or not _exact(current_hp) or not _exact(maximum_hp) or maximum_hp < 1 or current_hp > maximum_hp:
            continue
        recovery = maximum_hp // 16 if current_hp < maximum_hp else 0
        post_hp = min(maximum_hp, current_hp + recovery)
        result = {"session_id": state["session_id"], "turn_number": _value(event, "turn_number"), "side": side_name, "slot_index": slot_index, "pokemon_id": pokemon_id, "item": "leftovers", "pre_hp": current_hp, "max_hp": maximum_hp, "recovery": recovery, "post_hp": post_hp, "outcome": "recovered" if recovery else "already_full_hp", "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}}
        results.append(result)
        if post_hp != current_hp:
            pokemon["current_hp"] = post_hp
            _mark(pokemon, "current_hp", event)


def _valid_leftovers_end_of_turn_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    return isinstance(value, dict) and value.get("session_id") == session_id and value.get("item") == "leftovers" and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("pre_hp", "max_hp", "recovery", "post_hp")) and value["pre_hp"] <= value["max_hp"] and value["post_hp"] <= value["max_hp"] and value["post_hp"] == min(value["max_hp"], value["pre_hp"] + value["recovery"]) and value.get("outcome") in {"recovered", "already_full_hp"} and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"


def _apply_black_sludge_end_of_turn(state, event):
    """Resolve only exact Black Sludge at a confirmed first end-of-turn phase."""
    results = state.setdefault("black_sludge_end_of_turn_context", [])
    if not isinstance(results, list):
        return
    for side_name in ("self", "opponent"):
        side = _side(state, side_name)
        slot_index = side.get("active_slot_index") if isinstance(side, dict) else None
        roster = side.get("pokemon") if isinstance(side, dict) else None
        pokemon = roster.get(slot_index, roster.get(str(slot_index))) if isinstance(roster, dict) else None
        if not isinstance(slot_index, int) or isinstance(slot_index, bool) or not isinstance(pokemon, dict):
            continue
        pokemon_id = pokemon.get("pokemon_id", pokemon.get("name_en"))
        if pokemon.get("known_item") != "black-sludge" or pokemon.get("fainted") is not False or not isinstance(pokemon_id, str) or not pokemon_id:
            continue
        current_hp, maximum_hp, current_type = pokemon.get("current_hp"), pokemon.get("max_hp"), pokemon.get("current_type")
        base = {"session_id": state["session_id"], "turn_number": _value(event, "turn_number"), "side": side_name, "slot_index": slot_index, "pokemon_id": pokemon_id, "item": "black-sludge", "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}}
        if is_unknown_battle_fact(current_type) or current_type is None:
            results.append({**base, "status": "incomplete", "reason": "current_type_unknown"})
            continue
        if not _exact(current_hp) or not _exact(maximum_hp) or maximum_hp < 1 or current_hp > maximum_hp:
            results.append({**base, "status": "incomplete", "reason": "hp_unknown"})
            continue
        if not isinstance(current_type, list) or not current_type:
            results.append({**base, "status": "incomplete", "reason": "current_type_unknown"})
            continue
        if "poison" in current_type:
            recovery = maximum_hp // 16 if current_hp < maximum_hp else 0
            post_hp = min(maximum_hp, current_hp + recovery)
            result = {**base, "status": "complete", "current_type": deepcopy(current_type), "pre_hp": current_hp, "max_hp": maximum_hp, "recovery": recovery, "post_hp": post_hp, "outcome": "recovered" if recovery else "already_full_hp", "guaranteed_ko": False}
        else:
            damage = maximum_hp // 8
            post_hp = max(0, current_hp - damage)
            result = {**base, "status": "complete", "current_type": deepcopy(current_type), "pre_hp": current_hp, "max_hp": maximum_hp, "damage": damage, "post_hp": post_hp, "outcome": "damaged", "guaranteed_ko": post_hp == 0}
        results.append(result)
        if post_hp != current_hp:
            pokemon["current_hp"] = post_hp
            _mark(pokemon, "current_hp", event)


def _valid_black_sludge_end_of_turn_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    common = isinstance(value, dict) and value.get("session_id") == session_id and value.get("item") == "black-sludge" and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"
    if not common:
        return False
    if value.get("status") == "incomplete":
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "item", "provenance", "status", "reason"} and value.get("reason") in {"current_type_unknown", "hp_unknown"}
    if value.get("status") != "complete" or not isinstance(value.get("current_type"), list) or not value["current_type"]:
        return False
    numeric = ("pre_hp", "max_hp", "post_hp")
    if not all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in numeric) or value["pre_hp"] > value["max_hp"] or value["post_hp"] > value["max_hp"] or not isinstance(value.get("guaranteed_ko"), bool):
        return False
    if "poison" in value["current_type"]:
        return isinstance(value.get("recovery"), int) and not isinstance(value.get("recovery"), bool) and value["recovery"] >= 0 and value["post_hp"] == min(value["max_hp"], value["pre_hp"] + value["recovery"]) and value.get("outcome") in {"recovered", "already_full_hp"} and value["guaranteed_ko"] is False
    return isinstance(value.get("damage"), int) and not isinstance(value.get("damage"), bool) and value["damage"] >= 0 and value["post_hp"] == max(0, value["pre_hp"] - value["damage"]) and value.get("outcome") == "damaged" and value["guaranteed_ko"] == (value["post_hp"] == 0)


def _apply_toxic_end_of_turn(state, event):
    """Apply only an exact identity-owned next toxic stage at this phase."""
    results = state.setdefault("toxic_end_of_turn_context", [])
    if not isinstance(results, list):
        return
    turn_number = _value(event, "turn_number")
    for side_name in ("self", "opponent"):
        side = _side(state, side_name); slot = side.get("active_slot_index") if isinstance(side, dict) else None
        roster = side.get("pokemon") if isinstance(side, dict) else None
        pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, dict) else None
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pokemon, dict) or pokemon.get("condition") != "toxic" or pokemon.get("fainted") is not False:
            continue
        progress = pokemon.get("toxic_progression")
        if not _valid_toxic_progression_state(progress):
            continue
        pid, hp, maximum = pokemon.get("pokemon_id", pokemon.get("name_en")), pokemon.get("current_hp"), pokemon.get("max_hp")
        if not isinstance(pid, str) or not pid or not _exact(hp) or not _exact(maximum) or maximum < 1 or hp > maximum:
            continue
        stage, prior_turn = progress["next_stage"], progress["last_processed_turn"]
        if progress["initialized_turn"] > turn_number or isinstance(prior_turn, int) and turn_number <= prior_turn:
            continue
        damage = (maximum * stage) // 16
        post_hp = max(0, hp - damage)
        result = {"session_id": state["session_id"], "turn_number": turn_number, "side": side_name, "slot_index": slot, "pokemon_id": pid, "condition": "toxic", "stage": stage, "pre_hp": hp, "max_hp": maximum, "damage": damage, "post_hp": post_hp, "guaranteed_ko": post_hp == 0, "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}}
        results.append(result)
        pokemon["current_hp"] = post_hp
        _mark(pokemon, "current_hp", event)
        pokemon["toxic_progression"] = {**deepcopy(progress), "next_stage": min(stage + 1, 15), "last_processed_turn": turn_number}


def _valid_toxic_end_of_turn_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    return isinstance(value, dict) and value.get("session_id") == session_id and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and value.get("condition") == "toxic" and all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("turn_number", "stage", "pre_hp", "max_hp", "damage", "post_hp")) and 1 <= value["stage"] <= 15 and value["pre_hp"] <= value["max_hp"] and value["post_hp"] == max(0, value["pre_hp"] - value["damage"]) and value["damage"] == (value["max_hp"] * value["stage"]) // 16 and value.get("guaranteed_ko") == (value["post_hp"] == 0) and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"


def _apply_rain_dish_end_of_turn(state, event):
    """Resolve only exact Rain Dish under exact current weather authority."""
    results = state.setdefault("rain_dish_end_of_turn_context", [])
    if not isinstance(results, list):
        return
    weather = state.get("field", {}).get("weather") if isinstance(state.get("field"), dict) else None
    weather_provenance = state.get("field", {}).get("weather_provenance") if isinstance(state.get("field"), dict) else None
    rows = _active_sandstorm_rows(state)
    for row in rows:
        pokemon = row["pokemon"]
        if pokemon.get("fainted") is not False:
            continue
        ability = pokemon.get("current_ability")
        if ability != "rain-dish":
            if is_unknown_battle_fact(ability) and _trusted_current_weather(weather, weather_provenance) and weather == "rain":
                results.append(_rain_dish_base(state, event, row) | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        base = _rain_dish_base(state, event, row)
        if not _trusted_current_weather(weather, weather_provenance):
            results.append(base | {"status": "incomplete", "reason": "current_weather_unknown"})
            continue
        if weather != "rain":
            continue
        if not _trusted_current_ability(pokemon):
            results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        if any(not _trusted_current_ability(active["pokemon"]) for active in rows):
            results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        if _rain_dish_has_order_dependency(state, row, event):
            results.append(base | {"status": "incomplete", "reason": "same_owner_end_of_turn_order_unknown"})
            continue
        hp, maximum = pokemon.get("current_hp"), pokemon.get("max_hp")
        if not _exact(hp) or not _exact(maximum) or maximum < 1 or hp > maximum:
            results.append(base | {"status": "incomplete", "reason": "hp_unknown"})
            continue
        abilities = {active["side"]: active["pokemon"]["current_ability"] for active in rows}
        recovery = evaluate_weather_recovery(active_abilities=abilities, target_side=row["side"], required_ability="rain-dish", current_hp=hp, maximum_hp=maximum)
        if recovery.get("status") != "complete":
            results.append(base | {"status": "incomplete", "reason": "canonical_rain_dish_authority"})
            continue
        results.append(base | recovery)
        if "post_hp" in recovery and recovery["post_hp"] != hp:
            pokemon["current_hp"] = recovery["post_hp"]
            _mark(pokemon, "current_hp", event)


def _rain_dish_base(state, event, row):
    return {"session_id": state["session_id"], "turn_number": _value(event, "turn_number"), "side": row["side"], "slot_index": row["slot_index"], "pokemon_id": row["pokemon_id"], "ability": "rain-dish", "weather": "rain", "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}}


def _rain_dish_has_order_dependency(state, row, event):
    turn, identity = _value(event, "turn_number"), (row["side"], row["slot_index"], row["pokemon_id"])
    for key in ("leftovers_end_of_turn_context", "black_sludge_end_of_turn_context", "toxic_end_of_turn_context"):
        for result in state.get(key, []) if isinstance(state.get(key), list) else []:
            if isinstance(result, dict) and result.get("turn_number") == turn and (result.get("side"), result.get("slot_index"), result.get("pokemon_id")) == identity and result.get("post_hp") != result.get("pre_hp"):
                return True
    return isinstance(row["pokemon"].get("condition"), str) and row["pokemon"]["condition"] in {"burn", "poison", "toxic"}


def _valid_rain_dish_end_of_turn_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    base = isinstance(value, dict) and value.get("session_id") == session_id and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and value.get("ability") == "rain-dish" and value.get("weather") == "rain" and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"
    if not base:
        return False
    if value.get("status") == "incomplete":
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "ability", "weather", "provenance", "status", "reason"} and value.get("reason") in {"current_weather_unknown", "current_ability_unknown", "same_owner_end_of_turn_order_unknown", "hp_unknown"}
    if value.get("status") != "complete":
        return False
    if value.get("outcome") in {"suppressed_by_neutralizing_gas", "suppressed_by_weather_ability"}:
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "ability", "weather", "provenance", "status", "outcome"}
    return all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("pre_hp", "max_hp", "recovery", "post_hp")) and value["max_hp"] >= 1 and value["pre_hp"] <= value["max_hp"] and value["post_hp"] == min(value["max_hp"], value["pre_hp"] + value["recovery"]) and value.get("outcome") in {"recovered", "already_full_hp"}


def _apply_ice_body_end_of_turn(state, event):
    """Resolve only exact Ice Body under exact current Snow authority."""
    results = state.setdefault("ice_body_end_of_turn_context", [])
    if not isinstance(results, list):
        return
    weather = state.get("field", {}).get("weather") if isinstance(state.get("field"), dict) else None
    weather_provenance = state.get("field", {}).get("weather_provenance") if isinstance(state.get("field"), dict) else None
    rows = _active_sandstorm_rows(state)
    for row in rows:
        pokemon = row["pokemon"]
        if pokemon.get("fainted") is not False:
            continue
        ability = pokemon.get("current_ability")
        if ability != "ice-body":
            if is_unknown_battle_fact(ability) and _trusted_current_weather(weather, weather_provenance) and weather == "snow":
                results.append(_ice_body_base(state, event, row) | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        base = _ice_body_base(state, event, row)
        if not _trusted_current_weather(weather, weather_provenance):
            results.append(base | {"status": "incomplete", "reason": "current_weather_unknown"})
            continue
        if weather != "snow":
            continue
        if not _trusted_current_ability(pokemon):
            results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        if any(not _trusted_current_ability(active["pokemon"]) for active in rows):
            results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        if _ice_body_has_order_dependency(state, row, event):
            results.append(base | {"status": "incomplete", "reason": "same_owner_end_of_turn_order_unknown"})
            continue
        hp, maximum = pokemon.get("current_hp"), pokemon.get("max_hp")
        if not _exact(hp) or not _exact(maximum) or maximum < 1 or hp > maximum:
            results.append(base | {"status": "incomplete", "reason": "hp_unknown"})
            continue
        abilities = {active["side"]: active["pokemon"]["current_ability"] for active in rows}
        recovery = evaluate_ice_body_recovery(active_abilities=abilities, target_side=row["side"], current_hp=hp, maximum_hp=maximum)
        if recovery.get("status") != "complete":
            results.append(base | {"status": "incomplete", "reason": "canonical_ice_body_authority"})
            continue
        results.append(base | recovery)
        if "post_hp" in recovery and recovery["post_hp"] != hp:
            pokemon["current_hp"] = recovery["post_hp"]
            _mark(pokemon, "current_hp", event)


def _ice_body_base(state, event, row):
    return {"session_id": state["session_id"], "turn_number": _value(event, "turn_number"), "side": row["side"], "slot_index": row["slot_index"], "pokemon_id": row["pokemon_id"], "ability": "ice-body", "weather": "snow", "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}}


def _ice_body_has_order_dependency(state, row, event):
    turn, identity = _value(event, "turn_number"), (row["side"], row["slot_index"], row["pokemon_id"])
    for key in ("leftovers_end_of_turn_context", "black_sludge_end_of_turn_context", "toxic_end_of_turn_context"):
        for result in state.get(key, []) if isinstance(state.get(key), list) else []:
            if isinstance(result, dict) and result.get("turn_number") == turn and (result.get("side"), result.get("slot_index"), result.get("pokemon_id")) == identity and result.get("post_hp") != result.get("pre_hp"):
                return True
    return isinstance(row["pokemon"].get("condition"), str) and row["pokemon"]["condition"] in {"burn", "poison", "toxic"}


def _valid_ice_body_end_of_turn_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    base = isinstance(value, dict) and value.get("session_id") == session_id and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and value.get("ability") == "ice-body" and value.get("weather") == "snow" and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"
    if not base:
        return False
    if value.get("status") == "incomplete":
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "ability", "weather", "provenance", "status", "reason"} and value.get("reason") in {"current_weather_unknown", "current_ability_unknown", "same_owner_end_of_turn_order_unknown", "hp_unknown"}
    if value.get("status") != "complete":
        return False
    if value.get("outcome") in {"suppressed_by_neutralizing_gas", "suppressed_by_weather_ability"}:
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "ability", "weather", "provenance", "status", "outcome"}
    return all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("pre_hp", "max_hp", "recovery", "post_hp")) and value["max_hp"] >= 1 and value["pre_hp"] <= value["max_hp"] and value["post_hp"] == min(value["max_hp"], value["pre_hp"] + value["recovery"]) and value.get("outcome") in {"recovered", "already_full_hp"}


def _apply_solar_power_end_of_turn(state, event):
    """Resolve only exact Solar Power under exact current Sun authority."""
    results = state.setdefault("solar_power_end_of_turn_context", [])
    if not isinstance(results, list):
        return
    weather = state.get("field", {}).get("weather") if isinstance(state.get("field"), dict) else None
    weather_provenance = state.get("field", {}).get("weather_provenance") if isinstance(state.get("field"), dict) else None
    rows = _active_sandstorm_rows(state)
    for row in rows:
        pokemon = row["pokemon"]
        if pokemon.get("fainted") is not False:
            continue
        ability = pokemon.get("current_ability")
        if ability != "solar-power":
            if is_unknown_battle_fact(ability) and _trusted_current_weather(weather, weather_provenance) and weather == "sun":
                results.append(_solar_power_base(state, event, row) | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        base = _solar_power_base(state, event, row)
        if not _trusted_current_weather(weather, weather_provenance):
            results.append(base | {"status": "incomplete", "reason": "current_weather_unknown"})
            continue
        if weather != "sun":
            continue
        if not _trusted_current_ability(pokemon):
            results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        if any(not _trusted_current_ability(active["pokemon"]) for active in rows):
            results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        if _solar_power_has_order_dependency(state, row, event):
            results.append(base | {"status": "incomplete", "reason": "same_owner_end_of_turn_order_unknown"})
            continue
        hp, maximum = pokemon.get("current_hp"), pokemon.get("max_hp")
        if not _exact(hp) or not _exact(maximum) or maximum < 1 or hp > maximum:
            results.append(base | {"status": "incomplete", "reason": "hp_unknown"})
            continue
        abilities = {active["side"]: active["pokemon"]["current_ability"] for active in rows}
        residual = evaluate_solar_power_residual(active_abilities=abilities, target_side=row["side"], current_hp=hp, maximum_hp=maximum)
        if residual.get("status") != "complete":
            results.append(base | {"status": "incomplete", "reason": "canonical_solar_power_authority"}); continue
        results.append(base | residual)
        if "post_hp" in residual and residual["post_hp"] != hp:
            pokemon["current_hp"] = residual["post_hp"]
            _mark(pokemon, "current_hp", event)


def _solar_power_base(state, event, row):
    return {"session_id": state["session_id"], "turn_number": _value(event, "turn_number"), "side": row["side"], "slot_index": row["slot_index"], "pokemon_id": row["pokemon_id"], "ability": "solar-power", "weather": "sun", "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}}


def _solar_power_has_order_dependency(state, row, event):
    turn, identity = _value(event, "turn_number"), (row["side"], row["slot_index"], row["pokemon_id"])
    for key in ("leftovers_end_of_turn_context", "black_sludge_end_of_turn_context", "toxic_end_of_turn_context"):
        for result in state.get(key, []) if isinstance(state.get(key), list) else []:
            if isinstance(result, dict) and result.get("turn_number") == turn and (result.get("side"), result.get("slot_index"), result.get("pokemon_id")) == identity and result.get("post_hp") != result.get("pre_hp"):
                return True
    return isinstance(row["pokemon"].get("condition"), str) and row["pokemon"]["condition"] in {"burn", "poison", "toxic"}


def _valid_solar_power_end_of_turn_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    base = isinstance(value, dict) and value.get("session_id") == session_id and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and value.get("ability") == "solar-power" and value.get("weather") == "sun" and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"
    if not base:
        return False
    if value.get("status") == "incomplete":
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "ability", "weather", "provenance", "status", "reason"} and value.get("reason") in {"current_weather_unknown", "current_ability_unknown", "same_owner_end_of_turn_order_unknown", "hp_unknown"}
    if value.get("status") != "complete":
        return False
    if value.get("outcome") in {"suppressed_by_neutralizing_gas", "suppressed_by_weather_ability"}:
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "ability", "weather", "provenance", "status", "outcome"}
    return all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("pre_hp", "max_hp", "damage", "post_hp")) and value["max_hp"] >= 1 and value["pre_hp"] <= value["max_hp"] and value["post_hp"] == max(0, value["pre_hp"] - value["damage"]) and value["damage"] == value["max_hp"] // 8 and value.get("outcome") == "damaged" and value.get("guaranteed_ko") == (value["post_hp"] == 0)


def _apply_dry_skin_end_of_turn(state, event):
    """Resolve only exact Dry Skin Rain/Sun HP effects at the confirmed phase."""
    results = state.setdefault("dry_skin_end_of_turn_context", [])
    if not isinstance(results, list): return
    weather = state.get("field", {}).get("weather") if isinstance(state.get("field"), dict) else None
    provenance = state.get("field", {}).get("weather_provenance") if isinstance(state.get("field"), dict) else None
    rows = _active_sandstorm_rows(state)
    for row in rows:
        pokemon = row["pokemon"]
        if pokemon.get("fainted") is not False: continue
        ability = pokemon.get("current_ability")
        if ability != "dry-skin":
            if is_unknown_battle_fact(ability) and _trusted_current_weather(weather, provenance) and weather in {"rain", "sun"}:
                results.append(_dry_skin_base(state, event, row, weather) | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        base = _dry_skin_base(state, event, row, weather)
        if not _trusted_current_weather(weather, provenance):
            results.append(base | {"status": "incomplete", "reason": "current_weather_unknown"}); continue
        if weather not in {"rain", "sun"}: continue
        if not _trusted_current_ability(pokemon) or any(not _trusted_current_ability(active["pokemon"]) for active in rows):
            results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"}); continue
        abilities = {active["pokemon"]["current_ability"] for active in rows}
        if "neutralizing-gas" in abilities:
            results.append(base | {"status": "complete", "outcome": "suppressed_by_neutralizing_gas"}); continue
        if abilities & {"cloud-nine", "air-lock"}:
            results.append(base | {"status": "complete", "outcome": "suppressed_by_weather_ability"}); continue
        if _dry_skin_has_order_dependency(state, row, event):
            results.append(base | {"status": "incomplete", "reason": "same_owner_end_of_turn_order_unknown"}); continue
        hp, maximum = pokemon.get("current_hp"), pokemon.get("max_hp")
        if not _exact(hp) or not _exact(maximum) or maximum < 1 or hp > maximum:
            results.append(base | {"status": "incomplete", "reason": "hp_unknown"}); continue
        if weather == "rain":
            ability_by_side = {active["side"]: active["pokemon"]["current_ability"] for active in rows}
            recovery_result = evaluate_weather_recovery(active_abilities=ability_by_side, target_side=row["side"], required_ability="dry-skin", current_hp=hp, maximum_hp=maximum)
            if recovery_result.get("status") != "complete":
                results.append(base | {"status": "incomplete", "reason": "canonical_dry_skin_authority"}); continue
            post_hp = recovery_result.get("post_hp", hp)
            result = base | recovery_result | ({"guaranteed_ko": False} if "post_hp" in recovery_result else {})
        else:
            amount = maximum // 8
            post_hp = max(0, hp - amount)
            result = base | {"status": "complete", "pre_hp": hp, "max_hp": maximum, "damage": amount, "post_hp": post_hp, "outcome": "damaged", "guaranteed_ko": post_hp == 0}
        results.append(result)
        if post_hp != hp:
            pokemon["current_hp"] = post_hp; _mark(pokemon, "current_hp", event)


def _dry_skin_base(state, event, row, weather):
    result_weather = weather if isinstance(weather, str) and weather in {"rain", "sun"} else "unknown"
    return {"session_id": state["session_id"], "turn_number": _value(event, "turn_number"), "side": row["side"], "slot_index": row["slot_index"], "pokemon_id": row["pokemon_id"], "ability": "dry-skin", "weather": result_weather, "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}}


def _dry_skin_has_order_dependency(state, row, event):
    turn, identity = _value(event, "turn_number"), (row["side"], row["slot_index"], row["pokemon_id"])
    for key in ("leftovers_end_of_turn_context", "black_sludge_end_of_turn_context", "toxic_end_of_turn_context"):
        for result in state.get(key, []) if isinstance(state.get(key), list) else []:
            if isinstance(result, dict) and result.get("turn_number") == turn and (result.get("side"), result.get("slot_index"), result.get("pokemon_id")) == identity and result.get("post_hp") != result.get("pre_hp"): return True
    return isinstance(row["pokemon"].get("condition"), str) and row["pokemon"]["condition"] in {"burn", "poison", "toxic"}


def _valid_dry_skin_end_of_turn_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    base = isinstance(value, dict) and value.get("session_id") == session_id and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and value.get("ability") == "dry-skin" and value.get("weather") in {"rain", "sun", "unknown"} and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"
    if not base: return False
    if value.get("status") == "incomplete": return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "ability", "weather", "provenance", "status", "reason"} and value.get("reason") in {"current_weather_unknown", "current_ability_unknown", "same_owner_end_of_turn_order_unknown", "hp_unknown"}
    if value.get("status") != "complete": return False
    if value.get("outcome") in {"suppressed_by_neutralizing_gas", "suppressed_by_weather_ability"}: return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "ability", "weather", "provenance", "status", "outcome"}
    numeric = all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("pre_hp", "max_hp", "post_hp")) and value["max_hp"] >= 1 and value["pre_hp"] <= value["max_hp"] and isinstance(value.get("guaranteed_ko"), bool)
    if not numeric: return False
    if value["weather"] == "rain": return isinstance(value.get("recovery"), int) and not isinstance(value.get("recovery"), bool) and value["recovery"] >= 0 and value["post_hp"] == min(value["max_hp"], value["pre_hp"] + value["recovery"]) and value.get("outcome") in {"recovered", "already_full_hp"} and value["guaranteed_ko"] is False
    return value["weather"] == "sun" and isinstance(value.get("damage"), int) and not isinstance(value.get("damage"), bool) and value["damage"] == value["max_hp"] // 8 and value["post_hp"] == max(0, value["pre_hp"] - value["damage"]) and value.get("outcome") == "damaged" and value["guaranteed_ko"] == (value["post_hp"] == 0)


def _apply_sandstorm_end_of_turn(state, event):
    """Resolve only one exact, non-order-dependent Sandstorm residual tick."""
    results = state.setdefault("sandstorm_end_of_turn_context", [])
    if not isinstance(results, list):
        return
    weather = state.get("field", {}).get("weather") if isinstance(state.get("field"), dict) else None
    weather_provenance = state.get("field", {}).get("weather_provenance") if isinstance(state.get("field"), dict) else None
    active_rows = _active_sandstorm_rows(state)
    if not _trusted_current_weather(weather, weather_provenance):
        if is_unknown_battle_fact(weather) or weather is None:
            for row in active_rows:
                results.append(_sandstorm_base(state, event, row) | {"status": "incomplete", "reason": "current_weather_unknown"})
        return
    if weather != "sandstorm":
        return
    abilities = {row["side"]: row["pokemon"].get("current_ability") for row in active_rows}
    for row in active_rows:
        pokemon = row["pokemon"]
        if pokemon.get("fainted") is not False:
            continue
        base = _sandstorm_base(state, event, row)
        current_type = pokemon.get("current_type")
        if not _trusted_current_type(pokemon):
            results.append(base | {"status": "incomplete", "reason": "current_type_unknown"})
            continue
        item = pokemon.get("known_item")
        early = evaluate_sandstorm_residual(current_type=current_type, item=item, active_abilities=abilities if all(isinstance(value, str) and value for value in abilities.values()) else {}, target_side=row["side"], current_hp=pokemon.get("current_hp"), maximum_hp=pokemon.get("max_hp"))
        if early.get("status") == "complete" and early.get("outcome") in {"immune_by_type", "prevented_by_safety_goggles"}:
            results.append(base | early)
            continue
        if any(not _trusted_current_ability(active["pokemon"]) for active in active_rows):
            results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"})
            continue
        if _unknown(item) or not (item is None or isinstance(item, str)):
            results.append(base | {"status": "incomplete", "reason": "current_item_unknown"})
            continue
        if _sandstorm_has_order_dependency(state, row, event):
            results.append(base | {"status": "incomplete", "reason": "same_owner_end_of_turn_order_unknown"})
            continue
        resolved = evaluate_sandstorm_residual(current_type=current_type, item=item, active_abilities=abilities, target_side=row["side"], current_hp=pokemon.get("current_hp"), maximum_hp=pokemon.get("max_hp"))
        if resolved.get("status") != "complete":
            results.append(base | {"status": "incomplete", "reason": "hp_unknown"})
            continue
        results.append(base | resolved)
        if resolved["residual_damage"]:
            pokemon["current_hp"] = resolved["post_hp"]
            _mark(pokemon, "current_hp", event)


def _active_sandstorm_rows(state):
    rows = []
    for side_name in ("self", "opponent"):
        side = _side(state, side_name); slot = side.get("active_slot_index") if isinstance(side, dict) else None
        roster = side.get("pokemon") if isinstance(side, dict) else None
        pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, dict) else None
        pokemon_id = pokemon.get("pokemon_id", pokemon.get("name_en")) if isinstance(pokemon, dict) else None
        if isinstance(slot, int) and not isinstance(slot, bool) and isinstance(pokemon, dict) and isinstance(pokemon_id, str) and pokemon_id:
            rows.append({"side": side_name, "slot_index": slot, "pokemon_id": pokemon_id, "pokemon": pokemon})
    return rows


def _trusted_current_weather(value, provenance):
    return isinstance(value, str) and value in {"none", "sun", "rain", "sandstorm", "snow"} and isinstance(provenance, dict) and provenance.get("event_kind") == "current_weather_observed" and provenance.get("trust") == "user_confirmed_observation"


def _trusted_current_type(pokemon):
    return isinstance(pokemon.get("current_type"), list) and bool(pokemon["current_type"]) and _valid_current_type_state(pokemon["current_type"], pokemon.get("current_type_provenance"))


def _trusted_current_ability(pokemon):
    return _valid_current_ability_state(pokemon.get("current_ability"), pokemon.get("current_ability_provenance")) and isinstance(pokemon.get("current_ability"), str)


def _sandstorm_base(state, event, row):
    return {"session_id": state["session_id"], "turn_number": _value(event, "turn_number"), "side": row["side"], "slot_index": row["slot_index"], "pokemon_id": row["pokemon_id"], "weather": "sandstorm", "provenance": _provenance(event) | {"event_kind": "first_end_of_turn_reached_observed", "trust": _value(event, "trust")}}


def _sandstorm_has_order_dependency(state, row, event):
    turn, identity = _value(event, "turn_number"), (row["side"], row["slot_index"], row["pokemon_id"])
    for key in ("leftovers_end_of_turn_context", "black_sludge_end_of_turn_context", "toxic_end_of_turn_context"):
        for result in state.get(key, []) if isinstance(state.get(key), list) else []:
            if isinstance(result, dict) and result.get("turn_number") == turn and (result.get("side"), result.get("slot_index"), result.get("pokemon_id")) == identity and result.get("post_hp") != result.get("pre_hp"):
                return True
    condition = row["pokemon"].get("condition")
    return isinstance(condition, str) and condition in {"burn", "poison", "toxic"}


def _valid_sandstorm_end_of_turn_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    base = isinstance(value, dict) and value.get("session_id") == session_id and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and value.get("weather") == "sandstorm" and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "first_end_of_turn_reached_observed" and provenance.get("trust") == "user_confirmed_observation"
    if not base:
        return False
    if value.get("status") == "incomplete":
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "weather", "provenance", "status", "reason"} and value.get("reason") in {"current_weather_unknown", "current_type_unknown", "current_ability_unknown", "current_item_unknown", "same_owner_end_of_turn_order_unknown", "hp_unknown"}
    return value.get("status") == "complete" and isinstance(value.get("current_type"), list) and bool(value["current_type"]) and all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("pre_hp", "max_hp", "residual_damage", "post_hp")) and value["pre_hp"] <= value["max_hp"] and value["post_hp"] == max(0, value["pre_hp"] - value["residual_damage"]) and value.get("outcome") in {"immune_by_type", "prevented_by_safety_goggles", "suppressed_by_ability", "immune_by_ability", "damaged"} and value.get("guaranteed_ko") == (value["post_hp"] == 0)


def _same_turn_event(state, event):
    subject = {key: _value(event, key) for key in ("side", "slot_index", "pokemon_id")}
    target = {key: _value(event, key) for key in ("target_side", "target_slot_index", "target_pokemon_id")}
    if _pokemon(state, subject) is None or _pokemon(state, {"side": target["target_side"], "slot_index": target["target_slot_index"], "pokemon_id": target["target_pokemon_id"]}) is None:
        return _conflict(event, "same_turn_event_identity_mismatch")
    if _value(event, "predicate") == "qualifying_direct_damage_dealt" and (not _active_identity_matches(state, subject["side"], subject["slot_index"], subject["pokemon_id"]) or not _active_identity_matches(state, target["target_side"], target["target_slot_index"], target["target_pokemon_id"])):
        return _conflict(event, "qualifying_damage_event_active_identity_mismatch")
    record = {"session_id": state["session_id"], "turn_number": _value(event, "turn_number"), "predicate": _value(event, "predicate"), "occurred": _value(event, "occurred"), **subject, **target, "provenance": _provenance(event) | {"event_kind": "same_turn_event_observed", "trust": _value(event, "trust")}}
    events = state.setdefault("same_turn_event_context", [])
    if not isinstance(events, list): return _conflict(event, "invalid_same_turn_event_state")
    key = (record["turn_number"], record["predicate"], record["side"], record["slot_index"], record["pokemon_id"], record["target_side"], record["target_slot_index"], record["target_pokemon_id"])
    existing = next((item for item in events if isinstance(item, dict) and (item.get("turn_number"), item.get("predicate"), item.get("side"), item.get("slot_index"), item.get("pokemon_id"), item.get("target_side"), item.get("target_slot_index"), item.get("target_pokemon_id")) == key), None)
    if existing is not None:
        return None if existing.get("occurred") == record["occurred"] else _conflict(event, "conflicting_same_turn_event")
    events.append(record)
    if record["predicate"] == "qualifying_direct_damage_dealt":
        _apply_life_orb_recoil(state, event, record)
    return None


def _apply_life_orb_recoil(state, event, record):
    """Apply one observed qualifying-hit Life Orb consequence, never infer it."""
    results = state.setdefault("life_orb_recoil_context", [])
    if not isinstance(results, list):
        return
    owner = _pokemon(state, record)
    base = {"session_id": state["session_id"], "turn_number": record["turn_number"], "side": record["side"], "slot_index": record["slot_index"], "pokemon_id": record["pokemon_id"], "target_side": record["target_side"], "target_slot_index": record["target_slot_index"], "target_pokemon_id": record["target_pokemon_id"], "item": "life-orb", "provenance": deepcopy(record["provenance"])}
    if owner is None:
        return
    item = owner.get("known_item")
    if is_unknown_battle_fact(item):
        results.append(base | {"status": "incomplete", "reason": "current_item_unknown"})
        return
    if item != "life-orb":
        return
    if record["occurred"] is False:
        results.append(base | {"status": "complete", "outcome": "not_triggered"})
        return
    hp, maximum = owner.get("current_hp"), owner.get("max_hp")
    if not _exact(hp) or not _exact(maximum) or maximum < 1 or hp > maximum:
        results.append(base | {"status": "incomplete", "reason": "hp_unknown"})
        return
    if owner.get("fainted") is True or hp == 0:
        results.append(base | {"status": "complete", "outcome": "fainted_before_recoil", "pre_hp": hp, "max_hp": maximum, "recoil": 0, "post_hp": hp, "guaranteed_faint": hp == 0})
        return
    ability = owner.get("current_ability")
    if not _trusted_current_ability(owner):
        results.append(base | {"status": "incomplete", "reason": "current_ability_unknown"})
        return
    target = _pokemon(state, {"side": record["target_side"], "slot_index": record["target_slot_index"], "pokemon_id": record["target_pokemon_id"]})
    target_ability = target.get("current_ability") if isinstance(target, dict) else None
    target_known = isinstance(target, dict) and _trusted_current_ability(target)
    if ability in {"magic-guard", "sheer-force"} and not target_known:
        results.append(base | {"status": "incomplete", "reason": "target_current_ability_unknown"})
        return
    target_neutralizing_gas = target_ability == "neutralizing-gas"
    if ability == "magic-guard" and not target_neutralizing_gas:
        results.append(base | {"status": "complete", "outcome": "prevented_by_magic_guard", "pre_hp": hp, "max_hp": maximum, "recoil": 0, "post_hp": hp, "guaranteed_faint": False})
        return
    if ability == "sheer-force" and not target_neutralizing_gas:
        results.append(base | {"status": "incomplete", "reason": "sheer_force_move_applicability_unknown"})
        return
    recoil = max(1, maximum // 10)
    post_hp = max(0, hp - recoil)
    owner["current_hp"] = post_hp
    _mark(owner, "current_hp", event)
    results.append(base | {"status": "complete", "outcome": "recoiled", "pre_hp": hp, "max_hp": maximum, "recoil": recoil, "post_hp": post_hp, "guaranteed_faint": post_hp == 0})


def _valid_life_orb_recoil_result(value, session_id):
    provenance = value.get("provenance") if isinstance(value, dict) else None
    base = isinstance(value, dict) and value.get("session_id") == session_id and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and value.get("target_side") in {"self", "opponent"} and isinstance(value.get("target_slot_index"), int) and not isinstance(value.get("target_slot_index"), bool) and value["target_slot_index"] >= 0 and isinstance(value.get("target_pokemon_id"), str) and bool(value["target_pokemon_id"]) and value.get("item") == "life-orb" and isinstance(value.get("turn_number"), int) and not isinstance(value.get("turn_number"), bool) and value["turn_number"] > 0 and isinstance(provenance, dict) and provenance.get("event_kind") == "same_turn_event_observed" and provenance.get("trust") == "user_confirmed_observation"
    if not base:
        return False
    if value.get("status") == "incomplete":
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "target_side", "target_slot_index", "target_pokemon_id", "item", "provenance", "status", "reason"} and value.get("reason") in {"current_item_unknown", "hp_unknown", "current_ability_unknown", "target_current_ability_unknown", "sheer_force_move_applicability_unknown"}
    if value.get("status") != "complete":
        return False
    if value.get("outcome") == "not_triggered":
        return set(value) == {"session_id", "turn_number", "side", "slot_index", "pokemon_id", "target_side", "target_slot_index", "target_pokemon_id", "item", "provenance", "status", "outcome"}
    return all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("pre_hp", "max_hp", "recoil", "post_hp")) and value["max_hp"] >= 1 and value["pre_hp"] <= value["max_hp"] and value["post_hp"] == max(0, value["pre_hp"] - value["recoil"]) and value.get("outcome") in {"fainted_before_recoil", "prevented_by_magic_guard", "recoiled"} and value.get("guaranteed_faint") == (value["post_hp"] == 0)


def _pokemon_effect(state, event):
    pokemon = _pokemon(state, event); effect = event["planned_effect"]
    if pokemon is None: return _conflict(event, "missing_pokemon_target")
    if effect in {"set_condition", "clear_condition"} and pokemon.get("fainted") is True: return _conflict(event, "post_faint_condition_transition_unsupported")
    if effect in {"consume_item", "remove_item"} and pokemon.get("fainted") is True: return _conflict(event, "post_faint_item_transition_unsupported")
    field, expected = ("condition", _value(event, "condition")) if "condition" in effect else ("known_item", _value(event, "item"))
    current = pokemon.get(field, "unknown")
    if not isinstance(expected, str) or not expected: return _conflict(event, "missing_effect_identity")
    if effect in {"set_condition", "consume_item", "remove_item"}:
        if current == expected and effect == "set_condition": return None
        if (current is None or _unknown(current)) and effect == "set_condition":
            pokemon[field] = expected; _mark(pokemon, field, event)
            if field == "condition": pokemon["condition_provenance"] |= {"event_kind": "condition_applied_observed", "trust": _value(event, "trust")}
            _initialize_toxic_progression(pokemon, event, expected); return None
        if effect != "set_condition" and current == expected:
            pokemon[field] = None; _mark(pokemon, field, event)
            if field == "condition":
                pokemon["condition_provenance"] |= {"event_kind": "condition_removed_observed", "trust": _value(event, "trust")}
                pokemon["toxic_progression"] = make_unknown_battle_fact()
            return None
        return _conflict(event, "known_value_mismatch_or_unknown")
    if current == expected:
        pokemon[field] = None; _mark(pokemon, field, event)
        if field == "condition":
            pokemon["condition_provenance"] |= {"event_kind": "condition_removed_observed", "trust": _value(event, "trust")}
            pokemon["toxic_progression"] = make_unknown_battle_fact()
        return None
    return _conflict(event, "condition_clear_requires_exact_known_match")


def _initialize_toxic_progression(pokemon, event, condition):
    """Only a trusted ordered newly applied toxic condition starts at stage one."""
    if condition != "toxic":
        pokemon["toxic_progression"] = make_unknown_battle_fact()
        return
    turn_number = _value(event, "turn_number")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        pokemon["toxic_progression"] = make_unknown_battle_fact()
        return
    pokemon["toxic_progression"] = {"next_stage": 1, "initialized_turn": turn_number, "last_processed_turn": None, "condition_observation_id": event["observation_id"], "provenance": _provenance(event) | {"event_kind": "condition_applied_observed", "trust": _value(event, "trust")}}


def _field_effect(state, event):
    field = "weather" if "weather" in event["planned_effect"] else "terrain"; desired = _value(event, field); current_field = state.get("field")
    if not isinstance(current_field, dict) or not isinstance(desired, str) or not desired: return _conflict(event, "missing_field_effect_identity")
    current, start = current_field.get(field, "unknown"), event["planned_effect"].startswith("start_")
    if start and current == desired: return None
    if start and (current is None or _unknown(current)): current_field[field] = desired; _mark(current_field, field, event); return None
    if not start and current == desired: current_field[field] = None; _mark(current_field, field, event); return None
    return _conflict(event, "field_effect_requires_compatible_known_state")


def _side_condition(state, event):
    side = _side(state, _value(event, "side")); effect = _value(event, "side_condition") or _value(event, "effect")
    if side is None or not isinstance(effect, str) or not effect: return _conflict(event, "missing_side_condition_identity")
    conditions = side.get("side_conditions")
    if is_unknown_battle_fact(conditions): return _conflict(event, "side_condition_set_unknown")
    if not isinstance(conditions, list): return _conflict(event, "unsupported_side_condition_state")
    start = event["planned_effect"] == "start_side_condition"
    if start and effect in conditions: return None
    if start: conditions.append(effect); _mark(side, "side_conditions", event); return None
    if not start and effect in conditions: conditions.remove(effect); _mark(side, "side_conditions", event); return None
    return _conflict(event, "side_condition_missing_or_unknown")


def _observed_tailwind(state, event):
    side = _side(state, _value(event, "side")); status = _value(event, "tailwind_status")
    if side is None or status not in {"active", "inactive"}: return _conflict(event, "invalid_observed_tailwind")
    current = side.get("tailwind_status", "unknown")
    if not (isinstance(current, str) and current in {"active", "inactive", "unknown"}) and not is_unknown_battle_fact(current): return _conflict(event, "invalid_observed_tailwind_state")
    side["tailwind_status"] = status
    side["tailwind_status_provenance"] = {**_provenance(event), "event_kind": event.get("event_kind")}
    conditions = side.get("side_conditions")
    if isinstance(conditions, list) and all(isinstance(value, str) for value in conditions):
        present = "tailwind" in conditions
        if status == "active" and not present: conditions.append("tailwind")
        elif status == "inactive" and present: conditions.remove("tailwind")
        _mark(side, "side_conditions", event)
    return None


def _observed_trick_room(state, event):
    field = state.get("field"); status = _value(event, "trick_room_status")
    if not isinstance(field, dict) or status not in {"active", "inactive"}:
        return _conflict(event, "invalid_observed_trick_room")
    current = field.get("trick_room_status", "unknown")
    if not (isinstance(current, str) and current in {"active", "inactive", "unknown"}) and not is_unknown_battle_fact(current):
        return _conflict(event, "invalid_observed_trick_room_state")
    field["trick_room_status"] = status
    field["trick_room_status_provenance"] = {**_provenance(event), "event_kind": event.get("event_kind")}
    return None


def _apply_taunt_restriction(state, event):
    side, pokemon, turn = _value(event, "side"), _pokemon(state, event), _value(event, "turn_number")
    if side not in {"self", "opponent"} or pokemon is None or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id")) or _value(event, "trust") != "user_confirmed_observation" or not all(isinstance(_value(event, key), str) and bool(_value(event, key)) for key in ("source_action_id", "source_move_id")) or _value(event, "source_move_id") != "taunt": return _conflict(event, "invalid_taunt_restriction_application")
    owner={"session_id":state["session_id"],"side":side,"slot_index":_value(event,"slot_index"),"pokemon_id":_value(event,"pokemon_id")}; rows=deepcopy(state.get("current_taunt_restrictions",{}))
    existing = rows.get(side)
    if isinstance(existing, dict) and existing.get("state") == "active": return _conflict(event, "taunt_restriction_already_active")
    provenance = _provenance(event)
    rows[side]={"schema_version":"reducer-action-restriction-lifecycle-v1","owner":owner,"restriction":"taunt","activation_id":event["observation_id"],"source_action_id":_value(event,"source_action_id"),"source_move_id":"taunt","state":"active","remaining_target_turns":3,"applied_turn":turn,"last_completed_turn":None,"retired_reason":None,"application_provenance":provenance,"lifecycle_provenance":provenance}; state["current_taunt_restrictions"]=rows; return None


def _complete_taunt_turn(state, event):
    side, turn, rows = _value(event,"side"), _value(event,"turn_number"), state.get("current_taunt_restrictions")
    row=rows.get(side) if isinstance(rows,dict) else None
    if not isinstance(row,dict) or row.get("state")!="active" or row.get("owner",{}).get("slot_index")!=_value(event,"slot_index") or row.get("owner",{}).get("pokemon_id")!=_value(event,"pokemon_id") or not _active_identity_matches(state, side, _value(event,"slot_index"), _value(event,"pokemon_id")) or _value(event,"trust")!="user_confirmed_observation" or _value(event,"completion_kind") != "affected_active_turn_completed" or turn <= row.get("applied_turn", turn): return _conflict(event,"invalid_taunt_restriction_turn_completion")
    if row.get("last_completed_turn")==turn:return None
    if row.get("last_completed_turn") is not None and row["last_completed_turn"]>=turn:return _conflict(event,"stale_taunt_restriction_turn_completion")
    rows=deepcopy(rows); row=rows[side]; remaining=row["remaining_target_turns"]-1; row["last_completed_turn"]=turn; row["lifecycle_provenance"]=_provenance(event)
    if remaining==0:row.update(state="not_active",remaining_target_turns=None,retired_reason="expired")
    else:row["remaining_target_turns"]=remaining
    state["current_taunt_restrictions"]=rows; return None


def _record_executed_move(state, event):
    side, pokemon = _value(event, "side"), _pokemon(state, event)
    if side not in {"self", "opponent"} or pokemon is None or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id")) or _value(event, "trust") != "user_confirmed_observation" or not all(isinstance(_value(event, key), str) and bool(_value(event, key)) for key in ("move_id", "source_action_id")):
        return _conflict(event, "invalid_executed_move_history_observation")
    owner = {"session_id": state["session_id"], "side": side, "slot_index": _value(event, "slot_index"), "pokemon_id": _value(event, "pokemon_id")}
    pokemon["last_executed_move"] = {"schema_version": "reducer-last-executed-move-v1", "owner": owner, "move_id": _value(event, "move_id"), "source_action_id": _value(event, "source_action_id"), "execution_id": event["observation_id"], "provenance": _provenance(event)}
    return None

def _record_previous_action_result(state, event):
    """Replace, never append: this is the same-Pokémon immediate action slot."""
    side, pokemon, turn = _value(event, "side"), _pokemon(state, event), _value(event, "turn_number")
    fields = ("previous_action_id", "selected_move_id", "execution_move_id", "result_class")
    if side not in {"self", "opponent"} or pokemon is None or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id")) or _value(event, "trust") != "user_confirmed_observation" or not all(isinstance(_value(event, key), str) and _value(event, key) for key in fields): return _conflict(event, "invalid_previous_action_result_observation")
    owner = {"session_id": state["session_id"], "side": side, "slot_index": _value(event, "slot_index"), "pokemon_id": _value(event, "pokemon_id")}
    pokemon["previous_action_result"] = {"schema_version": "reducer-previous-action-result-v1", "owner": owner, "previous_action_id": _value(event, "previous_action_id"), "selected_move_id": _value(event, "selected_move_id"), "execution_move_id": _value(event, "execution_move_id"), "result_class": _value(event, "result_class"), "source_turn": turn, "provenance": _provenance(event)}
    return None

def _initialize_rage_fist_hit_count(state,event):
    side,pokemon=_value(event,"side"),_pokemon(state,event)
    if side not in {"self","opponent"} or pokemon is None or not _active_identity_matches(state,side,_value(event,"slot_index"),_value(event,"pokemon_id")) or _value(event,"trust")!="user_confirmed_observation" or pokemon.get("rage_fist_hit_count") is not None:return _conflict(event,"invalid_rage_fist_hit_count_initialization")
    owner={"session_id":state["session_id"],"side":side,"slot_index":_value(event,"slot_index"),"pokemon_id":_value(event,"pokemon_id")};pokemon["rage_fist_hit_count"]={"owner":owner,"count":0,"provenance":_provenance(event)};return None

def _record_rage_fist_qualifying_hit(state,event):
    side,pokemon=_value(event,"side"),_pokemon(state,event);row=pokemon.get("rage_fist_hit_count") if isinstance(pokemon,dict) else None
    if side not in {"self","opponent"} or pokemon is None or not _active_identity_matches(state,side,_value(event,"slot_index"),_value(event,"pokemon_id")) or _value(event,"trust")!="user_confirmed_observation" or not isinstance(row,dict) or row.get("owner",{}).get("pokemon_id")!=_value(event,"pokemon_id") or _value(event,"hit_outcome")!="successful_direct_hit":return _conflict(event,"invalid_rage_fist_qualifying_hit")
    row=deepcopy(row);row["count"]+=1;row["provenance"]=_provenance(event);pokemon["rage_fist_hit_count"]=row;return None


def _apply_encore_restriction(state, event):
    side, pokemon, turn = _value(event, "side"), _pokemon(state, event), _value(event, "turn_number")
    if side not in {"self", "opponent"} or pokemon is None or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id")) or _value(event, "trust") != "user_confirmed_observation" or _value(event, "source_move_id") != "encore" or not all(isinstance(_value(event, key), str) and bool(_value(event, key)) for key in ("source_action_id", "locked_move_id", "last_used_execution_id")):
        return _conflict(event, "invalid_encore_restriction_application")
    history = pokemon.get("last_executed_move")
    if not _valid_last_executed_move(state, history) or history.get("owner") != {"session_id": state["session_id"], "side": side, "slot_index": _value(event, "slot_index"), "pokemon_id": _value(event, "pokemon_id")} or history.get("move_id") != _value(event, "locked_move_id") or history.get("execution_id") != _value(event, "last_used_execution_id"):
        return _conflict(event, "encore_last_executed_move_binding_invalid")
    rows = deepcopy(state.get("current_encore_restrictions", {})); existing = rows.get(side)
    if isinstance(existing, dict) and existing.get("state") == "active": return _conflict(event, "encore_restriction_already_active")
    owner = {"session_id": state["session_id"], "side": side, "slot_index": _value(event, "slot_index"), "pokemon_id": _value(event, "pokemon_id")}; provenance = _provenance(event)
    rows[side] = {"schema_version": "reducer-action-restriction-lifecycle-v1", "owner": owner, "restriction": "encore", "activation_id": event["observation_id"], "source_action_id": _value(event, "source_action_id"), "source_move_id": "encore", "locked_move_id": _value(event, "locked_move_id"), "last_used_execution_id": _value(event, "last_used_execution_id"), "state": "active", "remaining_target_turns": 3, "applied_turn": turn, "last_completed_turn": None, "retired_reason": None, "application_provenance": provenance, "lifecycle_provenance": provenance}
    state["current_encore_restrictions"] = rows
    return None


def _complete_encore_turn(state, event):
    side, turn, rows = _value(event, "side"), _value(event, "turn_number"), state.get("current_encore_restrictions")
    row = rows.get(side) if isinstance(rows, dict) else None
    if not isinstance(row, dict) or row.get("state") != "active" or row.get("owner", {}).get("slot_index") != _value(event, "slot_index") or row.get("owner", {}).get("pokemon_id") != _value(event, "pokemon_id") or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id")) or _value(event, "trust") != "user_confirmed_observation" or _value(event, "completion_kind") != "affected_active_turn_completed" or turn <= row.get("applied_turn", turn):
        return _conflict(event, "invalid_encore_restriction_turn_completion")
    if row.get("last_completed_turn") == turn: return None
    if row.get("last_completed_turn") is not None and row["last_completed_turn"] >= turn: return _conflict(event, "stale_encore_restriction_turn_completion")
    rows = deepcopy(rows); row = rows[side]; remaining = row["remaining_target_turns"] - 1; row["last_completed_turn"] = turn; row["lifecycle_provenance"] = _provenance(event)
    if remaining == 0: row.update(state="not_active", remaining_target_turns=None, retired_reason="expired")
    else: row["remaining_target_turns"] = remaining
    state["current_encore_restrictions"] = rows
    return None


def _apply_disable_restriction(state, event):
    side, pokemon, turn = _value(event, "side"), _pokemon(state, event), _value(event, "turn_number")
    if side not in {"self", "opponent"} or pokemon is None or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id")) or _value(event, "trust") != "user_confirmed_observation" or _value(event, "source_move_id") != "disable" or not all(isinstance(_value(event, key), str) and bool(_value(event, key)) for key in ("source_action_id", "disabled_move_id", "last_used_execution_id")):
        return _conflict(event, "invalid_disable_restriction_application")
    history = pokemon.get("last_executed_move")
    owner = {"session_id": state["session_id"], "side": side, "slot_index": _value(event, "slot_index"), "pokemon_id": _value(event, "pokemon_id")}
    if not _valid_last_executed_move(state, history, owner) or history.get("move_id") != _value(event, "disabled_move_id") or history.get("execution_id") != _value(event, "last_used_execution_id"):
        return _conflict(event, "disable_last_executed_move_binding_invalid")
    rows = deepcopy(state.get("current_disable_restrictions", {})); existing = rows.get(side)
    if isinstance(existing, dict) and existing.get("state") == "active": return _conflict(event, "disable_restriction_already_active")
    provenance = _provenance(event)
    rows[side] = {"schema_version": "reducer-action-restriction-lifecycle-v1", "owner": owner, "restriction": "disable", "activation_id": event["observation_id"], "source_action_id": _value(event, "source_action_id"), "source_move_id": "disable", "disabled_move_id": _value(event, "disabled_move_id"), "last_used_execution_id": _value(event, "last_used_execution_id"), "state": "active", "remaining_target_turns": 4, "applied_turn": turn, "last_completed_turn": None, "retired_reason": None, "application_provenance": provenance, "lifecycle_provenance": provenance}
    state["current_disable_restrictions"] = rows
    return None


def _complete_disable_turn(state, event):
    side, turn, rows = _value(event, "side"), _value(event, "turn_number"), state.get("current_disable_restrictions")
    row = rows.get(side) if isinstance(rows, dict) else None
    if not isinstance(row, dict) or row.get("state") != "active" or row.get("owner", {}).get("slot_index") != _value(event, "slot_index") or row.get("owner", {}).get("pokemon_id") != _value(event, "pokemon_id") or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id")) or _value(event, "trust") != "user_confirmed_observation" or _value(event, "completion_kind") != "affected_active_turn_completed" or turn <= row.get("applied_turn", turn): return _conflict(event, "invalid_disable_restriction_turn_completion")
    if row.get("last_completed_turn") == turn: return None
    if row.get("last_completed_turn") is not None and row["last_completed_turn"] >= turn: return _conflict(event, "stale_disable_restriction_turn_completion")
    rows = deepcopy(rows); row = rows[side]; remaining = row["remaining_target_turns"] - 1; row["last_completed_turn"] = turn; row["lifecycle_provenance"] = _provenance(event)
    if remaining == 0: row.update(state="not_active", remaining_target_turns=None, retired_reason="expired")
    else: row["remaining_target_turns"] = remaining
    state["current_disable_restrictions"] = rows
    return None


def _switch(state, event):
    side = _side(state, _value(event, "side")); out_slot, out_id = _value(event, "switch_out_slot_index"), _value(event, "switch_out_pokemon_id"); in_slot, in_id = _value(event, "switch_in_slot_index"), _value(event, "switch_in_pokemon_id")
    if side is None or not all(isinstance(v, int) and not isinstance(v, bool) for v in (out_slot, in_slot)) or not all(isinstance(v, str) and v for v in (out_id, in_id)) or (out_slot, out_id) == (in_slot, in_id): return _conflict(event, "invalid_switch_identity")
    active = side.get("active_slot_index")
    if active in (None, "unknown") or active != out_slot: return _conflict(event, "switch_out_not_projected_active")
    roster = side.get("pokemon", {}); incoming = roster.get(in_slot, roster.get(str(in_slot))) if isinstance(roster, dict) else None
    if not isinstance(incoming, dict) or incoming.get("pokemon_id", incoming.get("name_en")) != in_id: return _conflict(event, "missing_switch_in_target")
    if incoming.get("fainted") is True: return _conflict(event, "switch_in_fainted")
    side["active_slot_index"] = in_slot; _mark(side, "active_slot_index", event)
    outgoing = roster.get(out_slot, roster.get(str(out_slot))) if isinstance(roster, dict) else None
    if isinstance(outgoing, dict):
        outgoing["toxic_progression"] = make_unknown_battle_fact()
        _invalidate_current_crit_volatiles(outgoing)
    _invalidate_current_crit_volatiles(incoming)
    rows=state.get("current_taunt_restrictions"); row=rows.get(_value(event,"side")) if isinstance(rows,dict) else None
    if isinstance(row,dict) and row.get("state")=="active" and row.get("owner",{}).get("slot_index")==out_slot and row.get("owner",{}).get("pokemon_id")==out_id:
        rows=deepcopy(rows); rows[_value(event,"side")]={**row,"state":"not_active","remaining_target_turns":None,"retired_reason":"switch_out","lifecycle_provenance":_provenance(event)}; state["current_taunt_restrictions"]=rows
    encore_rows=state.get("current_encore_restrictions"); encore=encore_rows.get(_value(event,"side")) if isinstance(encore_rows,dict) else None
    if isinstance(encore,dict) and encore.get("state")=="active" and encore.get("owner",{}).get("slot_index")==out_slot and encore.get("owner",{}).get("pokemon_id")==out_id:
        encore_rows=deepcopy(encore_rows); encore_rows[_value(event,"side")]={**encore,"state":"not_active","remaining_target_turns":None,"retired_reason":"switch_out","lifecycle_provenance":_provenance(event)}; state["current_encore_restrictions"]=encore_rows
    disable_rows=state.get("current_disable_restrictions"); disable=disable_rows.get(_value(event,"side")) if isinstance(disable_rows,dict) else None
    if isinstance(disable,dict) and disable.get("state")=="active" and disable.get("owner",{}).get("slot_index")==out_slot and disable.get("owner",{}).get("pokemon_id")==out_id:
        disable_rows=deepcopy(disable_rows); disable_rows[_value(event,"side")]={**disable,"state":"not_active","remaining_target_turns":None,"retired_reason":"switch_out","lifecycle_provenance":_provenance(event)}; state["current_disable_restrictions"]=disable_rows
    context = state.get("substitute_state_context")
    if isinstance(context, dict):
        outgoing_owner = {"session_id": state["session_id"], "side": _value(event, "side"), "slot_index": out_slot, "pokemon_id": out_id}
        incoming_owner = {"session_id": state["session_id"], "side": _value(event, "side"), "slot_index": in_slot, "pokemon_id": in_id}
        context = update_substitute_state_context(context=context, session_id=state["session_id"], owner=outgoing_owner, state="known_inactive", substitute_hp=None, provenance="runtime_switch_lifecycle_v1")
        context = update_substitute_state_context(context=context, session_id=state["session_id"], owner=incoming_owner, state="unknown", substitute_hp=None, provenance="runtime_switch_lifecycle_v1")
        if context is None:
            return _conflict(event, "invalid_substitute_switch_lifecycle")
        state["substitute_state_context"] = context
    _invalidate_same_turn_events(state, _value(event, "side"), out_slot, out_id)
    _supreme_overlord_switch_entry(state, event, incoming)
    context = state.get("mat_block_active_entry_eligibility_context")
    if isinstance(context, dict) and context.get("actor", {}).get("side") == _value(event, "side"):
        state.pop("mat_block_active_entry_eligibility_context", None)
    context = state.get("fake_out_active_entry_eligibility_context")
    if isinstance(context, dict) and context.get("actor", {}).get("side") == _value(event, "side"):
        state.pop("fake_out_active_entry_eligibility_context", None)
    return None


def _initialize_supreme_overlord_active_entry(state, event):
    side, pokemon = _value(event, "side"), _pokemon(state, event)
    count, token = _value(event, "cumulative_allied_faint_count"), _value(event, "entry_token")
    if side not in {"self", "opponent"} or pokemon is None or not isinstance(count, int) or isinstance(count, bool) or count < 0 or not isinstance(token, str) or not token or not _active_identity_matches(state, side, _value(event, "slot_index"), _value(event, "pokemon_id")):
        return _conflict(event, "invalid_supreme_overlord_initial_entry")
    history = state.get("supreme_overlord_faint_history_context")
    if history is None:
        history = {"schema_version": "supreme-overlord-faint-history-context-v1", "session_id": state["session_id"], "side_counts": {"self": 0, "opponent": 0}, "initialized_sides": [], "provenance": {"event_kind": "supreme_overlord_initial_active_observed", "source_sequence": event["observation_sequence"]}}
    if not _valid_supreme_overlord_history_context(state, history) or side in history["initialized_sides"]:
        return _conflict(event, "supreme_overlord_faint_history_already_initialized")
    history = deepcopy(history); history["side_counts"][side] = count; history["initialized_sides"].append(side); state["supreme_overlord_faint_history_context"] = history
    _capture_supreme_overlord_snapshot(state, side, pokemon, token, "initial_active", event)
    return None


def _increment_supreme_overlord_faint_history(state, side, event):
    history = state.get("supreme_overlord_faint_history_context")
    if not _valid_supreme_overlord_history_context(state, history) or side not in history["initialized_sides"]:
        return
    history = deepcopy(history); history["side_counts"][side] += 1; history["provenance"] = {"event_kind": "pokemon_faint_observed", "source_sequence": event["observation_sequence"]}; state["supreme_overlord_faint_history_context"] = history


def _supreme_overlord_switch_entry(state, event, incoming):
    side = _value(event, "side"); history = state.get("supreme_overlord_faint_history_context")
    if not _valid_supreme_overlord_history_context(state, history) or side not in history["initialized_sides"]:
        return
    snapshots = state.get("supreme_overlord_entry_snapshots")
    if isinstance(snapshots, list):
        retired = deepcopy(snapshots)
        for row in retired:
            if row.get("active") is True and isinstance(row.get("owner"), dict) and row["owner"].get("side") == side:
                row["active"] = False
        state["supreme_overlord_entry_snapshots"] = retired
    _capture_supreme_overlord_snapshot(state, side, incoming, f"switch:{event['observation_id']}", "switch_active", event)


def _capture_supreme_overlord_snapshot(state, side, pokemon, token, kind, event):
    if not isinstance(pokemon, dict) or pokemon.get("current_ability") != "supreme-overlord": return
    history = state.get("supreme_overlord_faint_history_context")
    if not _valid_supreme_overlord_history_context(state, history): return
    snapshots = deepcopy(state.get("supreme_overlord_entry_snapshots", []))
    for row in snapshots:
        if row.get("active") is True and isinstance(row.get("owner"), dict) and row["owner"].get("side") == side:
            row["active"] = False
    raw = history["side_counts"][side]
    owner = {"session_id": state["session_id"], "side": side, "slot_index": next((slot for slot, row in state[f"{side}_side"]["pokemon"].items() if row is pokemon), None), "pokemon_id": pokemon["pokemon_id"]}
    if not isinstance(owner["slot_index"], int): return
    snapshots.append({"schema_version": "supreme-overlord-entry-snapshot-v1", "session_id": state["session_id"], "owner": owner, "entry_token": token, "entry_kind": kind, "raw_allied_faint_count": raw, "fallen_allies_count": min(raw, 5), "source_sequence": event["observation_sequence"], "source_state_fingerprint": state_fingerprint(state), "status": "resolved", "active": True, "provenance": {"event_kind": event.get("event_kind"), "source_sequence": event["observation_sequence"]}})
    state["supreme_overlord_entry_snapshots"] = snapshots


def _invalidate_same_turn_events(state, side, slot_index, pokemon_id):
    """Discard facts whose identity owner has left supported current state."""
    events = state.get("same_turn_event_context")
    if not isinstance(events, list):
        return
    state["same_turn_event_context"] = [
        event for event in events
        if not (isinstance(event, dict) and (
            (event.get("side"), event.get("slot_index"), event.get("pokemon_id")) == (side, slot_index, pokemon_id)
            or (event.get("target_side"), event.get("target_slot_index"), event.get("target_pokemon_id")) == (side, slot_index, pokemon_id)
        ))
    ]


def _set_switch_permission(state, event):
    side = _side(state, "self")
    pokemon = _pokemon(state, event)
    status = _value(event, "permission_status")
    if side is None or pokemon is None or side.get("active_slot_index") != _value(event, "slot_index"):
        return _conflict(event, "switch_permission_owner_mismatch")
    if status not in {"permitted", "blocked"} or _value(event, "source") != "user_confirmed_current_switch_permission" or _value(event, "trust") != "user_confirmed_current":
        return _conflict(event, "invalid_switch_permission_authority")
    reason = _value(event, "block_reason")
    if status == "permitted" and reason is not None:
        return _conflict(event, "invalid_switch_permission_reason")
    if status == "blocked" and reason not in (None, "trapped", "switch_lock", "other_confirmed_block"):
        return _conflict(event, "invalid_switch_permission_reason")
    context = {"schema_version": "switch-permission-context-v1", "session_id": state.get("session_id"), "side": "self", "active_slot_index": _value(event, "slot_index"), "active_pokemon_id": _value(event, "pokemon_id"), "status": status, "supportability": "complete", "source": "user_confirmed_current_switch_permission", "trust": "user_confirmed_current"}
    if reason is not None: context["block_reason"] = reason
    side["switch_permission_context"] = context
    return None


def _clear_switch_permission(state, event):
    side = _side(state, "self"); pokemon = _pokemon(state, event)
    if side is None or pokemon is None or side.get("active_slot_index") != _value(event, "slot_index") or _value(event, "source") != "user_confirmed_current_switch_permission" or _value(event, "trust") != "user_confirmed_current":
        return _conflict(event, "invalid_switch_permission_authority")
    _invalidate_switch_permission(state)
    return None


def _invalidate_switch_permission(state):
    side = _side(state, "self")
    roster = side.get("pokemon") if isinstance(side, dict) else None
    slot = side.get("active_slot_index") if isinstance(side, dict) else None
    active = roster.get(slot, roster.get(str(slot))) if isinstance(roster, dict) else None
    pokemon_id = active.get("pokemon_id", active.get("name_en")) if isinstance(active, dict) else None
    if isinstance(side, dict) and isinstance(slot, int) and not isinstance(slot, bool) and isinstance(pokemon_id, str) and pokemon_id:
        side["switch_permission_context"] = {"schema_version": "switch-permission-context-v1", "session_id": state.get("session_id"), "side": "self", "active_slot_index": slot, "active_pokemon_id": pokemon_id, "status": "unknown", "supportability": "insufficient_context"}


def _set_ability_applicability(state, event):
    side, slot, pokemon_id = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id")
    status, ability_id = _value(event, "applicability_status"), _value(event, "ability_id")
    if not _active_identity_matches(state, side, slot, pokemon_id) or status not in {"applicable", "not_applicable"}:
        return _conflict(event, "invalid_ability_applicability_authority")
    state["ability_applicability_context"] = {"schema_version": "ability-applicability-context-v1", "session_id": state.get("session_id"), "source": {"side": side, "slot_index": slot, "pokemon_id": pokemon_id}, "ability_id": ability_id, "status": status}
    return None


def _clear_ability_applicability(state, event):
    side, slot, pokemon_id, ability_id = _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id"), _value(event, "ability_id")
    if not _active_identity_matches(state, side, slot, pokemon_id):
        return _conflict(event, "invalid_ability_applicability_authority")
    state["ability_applicability_context"] = {"schema_version": "ability-applicability-context-v1", "session_id": state.get("session_id"), "source": {"side": side, "slot_index": slot, "pokemon_id": pokemon_id}, "ability_id": ability_id, "status": "unknown"}
    return None


def _set_ability_interaction(state, event):
    source = (_value(event, "source_side"), _value(event, "source_slot_index"), _value(event, "source_pokemon_id"))
    target = (_value(event, "target_side"), _value(event, "target_slot_index"), _value(event, "target_pokemon_id"))
    status = _value(event, "interaction_status")
    if source[0] == target[0] or not _active_identity_matches(state, *source) or not _active_identity_matches(state, *target) or status not in {"affecting", "not_affecting"}:
        return _conflict(event, "invalid_ability_interaction_authority")
    state["ability_interaction_context"] = {"schema_version": "ability-interaction-context-v1", "session_id": state.get("session_id"), "source": {"side": source[0], "slot_index": source[1], "pokemon_id": source[2]}, "target": {"side": target[0], "slot_index": target[1], "pokemon_id": target[2]}, "status": status}
    return None


def _clear_ability_interaction(state, event):
    source = (_value(event, "source_side"), _value(event, "source_slot_index"), _value(event, "source_pokemon_id"))
    target = (_value(event, "target_side"), _value(event, "target_slot_index"), _value(event, "target_pokemon_id"))
    if source[0] == target[0] or not _active_identity_matches(state, *source) or not _active_identity_matches(state, *target):
        return _conflict(event, "invalid_ability_interaction_authority")
    state["ability_interaction_context"] = {"schema_version": "ability-interaction-context-v1", "session_id": state.get("session_id"), "source": {"side": source[0], "slot_index": source[1], "pokemon_id": source[2]}, "target": {"side": target[0], "slot_index": target[1], "pokemon_id": target[2]}, "status": "unknown"}
    return None


def _invalidate_ability_interaction_authorities(state):
    """Conservatively drop positive authority when any unrelated state changes."""
    applicability = state.get("ability_applicability_context")
    if isinstance(applicability, dict):
        source, ability_id = applicability.get("source"), applicability.get("ability_id")
        if isinstance(source, dict) and isinstance(ability_id, str) and ability_id:
            state["ability_applicability_context"] = {"schema_version": "ability-applicability-context-v1", "session_id": state.get("session_id"), "source": deepcopy(source), "ability_id": ability_id, "status": "unknown"}
    interaction = state.get("ability_interaction_context")
    if isinstance(interaction, dict):
        source, target = interaction.get("source"), interaction.get("target")
        if isinstance(source, dict) and isinstance(target, dict):
            state["ability_interaction_context"] = {"schema_version": "ability-interaction-context-v1", "session_id": state.get("session_id"), "source": deepcopy(source), "target": deepcopy(target), "status": "unknown"}


def _valid_switch_permission_context(state, value):
    if not isinstance(value, dict): return False
    side = state.get("self_side", {}); roster = side.get("pokemon", {}) if isinstance(side, dict) else {}
    slot = side.get("active_slot_index") if isinstance(side, dict) else None
    active = roster.get(slot, roster.get(str(slot))) if isinstance(roster, dict) else None
    pid = active.get("pokemon_id", active.get("name_en")) if isinstance(active, dict) else None
    common = {"schema_version": "switch-permission-context-v1", "session_id": state.get("session_id"), "side": "self", "active_slot_index": slot, "active_pokemon_id": pid}
    if any(value.get(key) != expected for key, expected in common.items()): return False
    if value.get("status") == "unknown": return set(value) == {*common, "status", "supportability"} and value.get("supportability") == "insufficient_context"
    return value.get("status") in {"permitted", "blocked"} and value.get("supportability") == "complete" and value.get("source") == "user_confirmed_current_switch_permission" and value.get("trust") == "user_confirmed_current" and set(value) <= {*common, "status", "supportability", "source", "trust", "block_reason"}


def _same_sequence_conflicts(steps):
    groups = {}
    for item in steps: groups.setdefault(item["observation_sequence"], []).append(item)
    conflicts = []
    for sequence, group in groups.items():
        if len(group) < 2: continue
        keys = {}
        for item in group:
            key = _semantic_key(item)
            if key in keys and not _explicitly_related(item, keys[key]): conflicts.append({"reason": "same_sequence_dependency_ambiguous", "observation_sequence": sequence, "observation_ids": [keys[key]["observation_id"], item["observation_id"]]})
            keys[key] = item
        switches = [x for x in group if x["planned_effect"] == "switch_active"]
        faints = [x for x in group if x["planned_effect"] == "mark_fainted"]
        for switch in switches:
            for faint in faints:
                if _value(switch, "side") == _value(faint, "side") and not _explicitly_related(switch, faint): conflicts.append({"reason": "same_sequence_switch_faint_dependency", "observation_sequence": sequence, "observation_ids": [switch["observation_id"], faint["observation_id"]]})
    return conflicts


def _semantic_key(event):
    effect = event["planned_effect"]
    if effect in {"set_current_weather", "start_weather", "end_weather"}: return ("field", "weather")
    if effect in {"start_terrain", "end_terrain"}: return ("field", "terrain")
    if effect in {"start_side_condition", "end_side_condition"}: return ("side", _value(event, "side"), _value(event, "side_condition") or _value(event, "effect"))
    if effect == "switch_active": return ("active", _value(event, "side"))
    return ("pokemon", _value(event, "side"), _value(event, "slot_index"), _value(event, "pokemon_id"), _TARGETS[effect])


def _explicitly_related(left, right):
    return left.get("depends_on_observation_id") == right["observation_id"] or right.get("depends_on_observation_id") == left["observation_id"]


def _fingerprint_state(state):
    """Exclude executor receipts so a committed replay remains identifiable."""
    excluded = {"last_applied_batch_fingerprint", "source_replay_policy_version", "last_commit_provenance"}
    return {key: _fingerprint_state(value) if isinstance(value, dict) else [_fingerprint_state(item) if isinstance(item, dict) else item for item in value] if isinstance(value, list) else value for key, value in state.items() if key not in excluded}


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=lambda item: {"__type__": type(item).__name__, "value": str(item)})


def _exact(value): return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _canonical_move_id(value): return isinstance(value, str) and bool(value) and value == value.strip() and value == value.lower() and " " not in value and "_" not in value
def _conflict(event, reason): return {"observation_id": event["observation_id"], "reason": reason}
def _step_ids(steps): return [x.get("observation_id") for x in steps if isinstance(x, dict)]
def _projection_result(status, base, plan, rejected=None, conflicts=None): return {"status": status, "base_state": deepcopy(base) if isinstance(base, dict) else None, "projected_state": None, "applied_step_ids": [], "rejected_step_ids": rejected or [], "conflicts": deepcopy(conflicts or []), "limitations": ["dry_run_only", "no_runtime_state_mutation", "provider_budget_0"]}
def _execution_result(status, base_digest, committed_digest, batch_digest, plan, rejected=None, conflicts=None): return {"status": status, "committed_state": None, "base_state_fingerprint": base_digest, "committed_state_fingerprint": committed_digest, "replay_batch_fingerprint": batch_digest, "applied_step_ids": [], "rejected_step_ids": deepcopy(rejected if rejected is not None else _step_ids(plan.get("ordered_steps", []) if isinstance(plan, dict) else [])), "conflicts": deepcopy(conflicts or []), "limitations": ["pure_detached_execution", "no_runtime_state_mutation", "no_ui_state_mutation", "no_persistence", "provider_budget_0"]}
def _legacy_result(status, base, plan): return {"status": status, "base_state": base, "planned_next_state_schema": [], "accepted_step_ids": [], "rejected_step_ids": [x.get("observation_id") for x in plan.get("ordered_steps", []) if isinstance(x, dict)], "conflicts": deepcopy(plan.get("conflicts", [])), "limitations": ["dry_run_only", "no_state_mutation"]}
