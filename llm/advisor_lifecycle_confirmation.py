"""Private trusted-lifecycle confirmation boundary; no reducer/store integration."""
from copy import deepcopy
from llm.advisor_switch_entry_mechanics_derived_observation import (
    DERIVED_KINDS, MECHANICS_DERIVED_TRUST, SWITCH_ENTRY_MECHANICS_SOURCE,
)
from llm.advisor_champions_sleep_freeze_action_gate import SELF_THAW_MOVES, SLEEP_EXCEPTIONS

PRODUCTION_SOURCE = "ui_observed_damage_confirmation"
USED_MOVE_SOURCE = "ui_used_move_confirmation"
RESTRICTION_SOURCE = "ui_action_restriction_confirmation"
EXECUTED_MOVE_SOURCE = "ui_executed_move_confirmation"
PREVIOUS_ACTION_RESULT_SOURCE = "ui_previous_action_result_confirmation"
FLINCH_CAUSALITY_SOURCE = "ui_flinch_causality_confirmation"
HP_TRANSITION_SOURCE = "ui_exact_hp_transition_confirmation"
HP_RECOVERY_SOURCE = "ui_exact_hp_recovery_confirmation"
SWITCH_SOURCE = "ui_switch_confirmation"
FAINT_SOURCE = "ui_faint_confirmation"
CONDITION_APPLICATION_SOURCE = "ui_condition_application_confirmation"
CURRENT_CONDITION_SOURCE = "ui_current_condition_confirmation"
CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE = "runtime_observed_contact_reactive_status_application"
CONTACT_REACTIVE_STATUS_RESULT_SOURCE = "runtime_observed_contact_reactive_status_result"
CONTACT_REACTIVE_DAMAGE_RESULT_SOURCE = "runtime_observed_contact_reactive_damage_result"
PARALYSIS_APPLICATION_SOURCE = "runtime_champions_paralysis_application"
CURRENT_HEALING_PREVENTED_SOURCE = "ui_current_healing_prevented_confirmation"
STAT_STAGE_SOURCE = "ui_stat_stage_confirmation"
HAZARD_STATE_SOURCE = "ui_switch_hazard_state_confirmation"
TAILWIND_SOURCE = "ui_tailwind_side_condition_confirmation"
TRICK_ROOM_SOURCE = "ui_trick_room_field_confirmation"
MAGIC_ROOM_SOURCE = "ui_magic_room_field_confirmation"
GRAVITY_SOURCE = "ui_gravity_field_confirmation"
LOCKED_ON_SOURCE = "ui_current_locked_on_state_confirmation"
SAME_TURN_EVENT_SOURCE = "ui_same_turn_event_confirmation"
FIRST_END_OF_TURN_SOURCE = "ui_first_end_of_turn_phase_confirmation"
CURRENT_TYPE_SOURCE = "ui_current_type_confirmation"
CURRENT_WEATHER_SOURCE = "ui_current_weather_confirmation"
CURRENT_ABILITY_SOURCE = "ui_current_ability_confirmation"
CURRENT_ITEM_SOURCE = "ui_current_item_confirmation"
BERRY_EATEN_STATE_SOURCE = "ui_berry_eaten_state_confirmation"
CURRENT_TERRAIN_SOURCE = "ui_current_terrain_confirmation"
CURRENT_SIDE_CONDITIONS_SOURCE = "ui_current_side_conditions_confirmation"
CURRENT_BATTLE_FORMAT_SOURCE = "ui_current_battle_format_confirmation"
CURRENT_LEVEL_SOURCE = "ui_current_level_confirmation"
SUBSTITUTE_STATE_SOURCE = "ui_substitute_state_confirmation"
FINAL_COMBAT_STAT_SOURCE = "ui_current_final_combat_stat_confirmation"
OPPONENT_RESPONSE_SET_SOURCE = "ui_current_opponent_response_set_confirmation"
OPPONENT_SWITCH_RESPONSE_SET_SOURCE = "ui_current_opponent_switch_response_set_confirmation"
OPPONENT_SWITCH_TARGET_COMBAT_SOURCE = "ui_current_opponent_switch_target_combat_confirmation"
PENDING_STATUS_ACTION_EXECUTION_SOURCE = "ui_pending_status_action_execution_confirmation"
MAT_BLOCK_ACTIVE_ENTRY_ELIGIBILITY_SOURCE = "ui_mat_block_active_entry_eligibility_confirmation"
FAKE_OUT_ACTIVE_ENTRY_ELIGIBILITY_SOURCE = "ui_fake_out_active_entry_eligibility_confirmation"
SUPREME_OVERLORD_INITIAL_ACTIVE_SOURCE = "ui_supreme_overlord_initial_active_confirmation"
DOUBLES_ACTIVE_TOPOLOGY_SOURCE = "ui_doubles_active_topology_confirmation"
SELECTED_ACTION_TARGETING_SOURCE = "ui_selected_action_targeting_confirmation"
PERSISTENT_EFFECT_SOURCE = "ui_persistent_effect_state_confirmation"
CONFUSION_SOURCE = "ui_confusion_state_confirmation"
STATUS_PROGRESSION_SOURCE = "ui_sleep_freeze_progression_confirmation"
FIXTURE_SOURCE = "fixture_contract_confirmation"
USER_TRUST = "user_confirmed_observation"
FIXTURE_TRUST = "fixture_contract_only"
_KINDS = {"direct_move_damage_observed": "production_ready", "used_move_observed": "production_ready", "exact_hp_transition_observed": "production_ready", "exact_hp_recovery_observed": "production_ready", "current_type_observed": "production_ready", "current_condition_observed": "production_ready", "current_healing_prevented_observed": "production_ready", "pending_status_action_execution_observed": "production_ready", "doubles_active_topology_observed": "production_ready", "selected_action_targeting_observed": "production_ready", "current_weather_observed": "production_ready", "current_ability_observed": "production_ready", "current_item_observed": "production_ready", "current_terrain_observed": "production_ready", "current_side_conditions_observed": "production_ready", "current_battle_format_observed": "production_ready", "current_level_observed": "production_ready", "current_final_combat_stat_observed": "production_ready", "current_opponent_response_set_observed": "production_ready", "current_opponent_switch_response_set_observed": "production_ready", "current_opponent_switch_target_combat_observed": "production_ready", "substitute_state_observed": "production_ready", "pokemon_switch_observed": "production_ready", "pokemon_faint_observed": "production_ready", "condition_applied_observed": "production_ready", "stat_stage_observed": "production_ready", "switch_hazards_observed": "production_ready", "tailwind_side_condition_observed": "production_ready", "trick_room_field_observed": "production_ready", "magic_room_field_observed": "production_ready", "gravity_field_observed": "production_ready", "current_locked_on_state_observed": "production_ready", "same_turn_event_observed": "production_ready", "first_end_of_turn_reached_observed": "production_ready", "condition_removed_observed": "fixture_only", "item_consumption_observed": "fixture_only", "item_removed_observed": "fixture_only", "weather_started_observed": "fixture_only", "weather_ended_observed": "fixture_only", "terrain_started_observed": "fixture_only", "side_condition_started_observed": "fixture_only", "side_condition_ended_observed": "fixture_only"}
_KINDS["mat_block_active_entry_eligibility_observed"] = "production_ready"
_KINDS["fake_out_active_entry_eligibility_observed"] = "production_ready"
_KINDS["supreme_overlord_initial_active_observed"] = "production_ready"
_KINDS["berry_eaten_state_observed"] = "production_ready"
_KINDS["executed_move_observed"] = "production_ready"
_KINDS["previous_action_result_observed"] = "production_ready"
_KINDS["flinch_causality_observed"] = "production_ready"
_KINDS["contact_reactive_status_result_observed"] = "production_ready"
_KINDS["contact_reactive_damage_result_observed"] = "production_ready"
for _kind in {"current_aqua_ring_state_observed", "current_ingrain_state_observed", "current_leech_seed_state_observed"}: _KINDS[_kind] = "production_ready"
for _kind in {"current_confusion_state_observed", "champions_confusion_progression_observed"}: _KINDS[_kind] = "production_ready"
_KINDS["champions_status_progression_observed"] = "production_ready"
for _kind in {"taunt_restriction_applied_observed", "encore_restriction_applied_observed", "disable_restriction_applied_observed", "taunt_restricted_turn_completed_observed", "encore_restricted_turn_completed_observed", "disable_restricted_turn_completed_observed"}: _KINDS[_kind] = "production_ready"


class LifecycleConfirmationBoundary:
    """Session-local canonical observation registry; callers own collection/use."""
    def __init__(self, session_id, owners):
        self._session_id = session_id if isinstance(session_id, str) else ""
        self._owners = deepcopy(owners) if isinstance(owners, dict) else {}
        self._next_sequence = 1
        self._records = {}

    def confirm(self, *, event_kind, payload, session_id, source, trust, confirmed, side=None, slot_index=None, pokemon_id=None, observation_id=None, related_observation_id=None, turn_number=None, production=True):
        if not confirmed: return _result("not_confirmed", "not_confirmed")
        readiness = _KINDS.get(event_kind)
        if readiness is None: return _result("unsupported_event_kind", "unsupported_event_kind")
        if session_id != self._session_id: return _result("stale_session", "stale_session", readiness)
        if production and (not _production_source_matches(event_kind, source) or trust != USER_TRUST or readiness != "production_ready"):
            return _result("fixture_only_source" if source == FIXTURE_SOURCE or readiness == "fixture_only" else "invalid_provenance", "source_or_trust_not_production_allowed", readiness)
        if not production and (source != FIXTURE_SOURCE or trust != FIXTURE_TRUST): return _result("invalid_provenance", "fixture_source_or_trust_required", readiness)
        if not isinstance(payload, dict) or not _valid_payload(event_kind, payload): return _result("invalid_provenance", "invalid_payload", readiness)
        if not _valid_turn_number(turn_number): return _result("invalid_provenance", "invalid_turn_number", readiness)
        if event_kind not in {"direct_move_damage_observed", "switch_hazards_observed", "tailwind_side_condition_observed", "trick_room_field_observed", "magic_room_field_observed", "gravity_field_observed", "first_end_of_turn_reached_observed", "current_weather_observed", "current_terrain_observed", "current_side_conditions_observed", "current_battle_format_observed", "doubles_active_topology_observed"} and not _owner_matches(self._owners, side, slot_index, pokemon_id): return _result("invalid_provenance", "owner_mismatch", readiness)
        if event_kind == "same_turn_event_observed" and (not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1): return _result("invalid_provenance", "missing_turn_number", readiness)
        if event_kind in {"executed_move_observed", "previous_action_result_observed", "flinch_causality_observed", "contact_reactive_status_result_observed", "contact_reactive_damage_result_observed"} and (not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1): return _result("invalid_provenance", "missing_turn_number", readiness)
        if event_kind.endswith("restriction_applied_observed") or event_kind.endswith("restricted_turn_completed_observed"):
            if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1: return _result("invalid_provenance", "missing_turn_number", readiness)
        if event_kind == "first_end_of_turn_reached_observed" and (not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1): return _result("invalid_provenance", "missing_turn_number", readiness)
        if event_kind in {"current_type_observed", "current_condition_observed", "current_locked_on_state_observed", "current_healing_prevented_observed", "pending_status_action_execution_observed", "mat_block_active_entry_eligibility_observed", "fake_out_active_entry_eligibility_observed", "supreme_overlord_initial_active_observed", "doubles_active_topology_observed", "selected_action_targeting_observed", "current_level_observed", "current_final_combat_stat_observed", "current_opponent_response_set_observed", "current_opponent_switch_response_set_observed", "substitute_state_observed", "current_aqua_ring_state_observed", "current_ingrain_state_observed", "current_leech_seed_state_observed", "current_confusion_state_observed", "champions_confusion_progression_observed", "champions_status_progression_observed"} and (not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1): return _result("invalid_provenance", "missing_turn_number", readiness)
        if event_kind in {"current_weather_observed", "current_ability_observed", "current_item_observed", "current_terrain_observed", "current_side_conditions_observed", "current_battle_format_observed", "gravity_field_observed"} and (not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1): return _result("invalid_provenance", "missing_turn_number", readiness)
        if event_kind == "condition_applied_observed" and payload.get("condition") == "toxic" and (not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1): return _result("invalid_provenance", "missing_turn_number", readiness)
        if event_kind == "berry_eaten_state_observed" and (not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1): return _result("invalid_provenance", "missing_turn_number", readiness)
        if event_kind == "berry_eaten_state_observed" and payload.get("state") == "known_false" and turn_number != 1: return _result("invalid_provenance", "fresh_battle_berry_eaten_false_requires_turn_one", readiness)
        if event_kind == "current_locked_on_state_observed" and payload.get("status") == "active":
            target = payload.get("bound_target")
            if not isinstance(target, dict) or target.get("session_id") != self._session_id or not _owner_matches(self._owners, target.get("side"), target.get("slot_index"), target.get("pokemon_id")):
                return _result("invalid_provenance", "locked_on_bound_target_mismatch", readiness)
        if event_kind == "same_turn_event_observed" and not _owner_matches(self._owners, payload.get("target_side"), payload.get("target_slot_index"), payload.get("target_pokemon_id")): return _result("invalid_provenance", "target_owner_mismatch", readiness)
        if event_kind == "contact_reactive_status_result_observed":
            defender = (payload.get("defender_side"), payload.get("defender_slot_index"), payload.get("defender_pokemon_id"))
            attacker = (payload.get("attacker_side"), payload.get("attacker_slot_index"), payload.get("attacker_pokemon_id"))
            if defender != (side, slot_index, pokemon_id): return _result("invalid_provenance", "defender_owner_mismatch", readiness)
            opposite = self._owners.get(payload.get("attacker_side")) if isinstance(self._owners, dict) else None
            if isinstance(opposite, dict) and attacker != (opposite.get("side"), opposite.get("slot_index"), opposite.get("pokemon_id")): return _result("invalid_provenance", "attacker_owner_mismatch", readiness)
        if event_kind == "contact_reactive_damage_result_observed":
            attacker = (payload.get("attacker_side"), payload.get("attacker_slot_index"), payload.get("attacker_pokemon_id"))
            defender = (payload.get("defender_side"), payload.get("defender_slot_index"), payload.get("defender_pokemon_id"))
            if attacker != (side, slot_index, pokemon_id): return _result("invalid_provenance", "attacker_owner_mismatch", readiness)
            opposite = self._owners.get(payload.get("defender_side")) if isinstance(self._owners, dict) else None
            if isinstance(opposite, dict) and defender != (opposite.get("side"), opposite.get("slot_index"), opposite.get("pokemon_id")): return _result("invalid_provenance", "defender_owner_mismatch", readiness)
        if event_kind == "same_turn_event_observed" and (side, slot_index, pokemon_id) == (payload.get("target_side"), payload.get("target_slot_index"), payload.get("target_pokemon_id")):
            return _result("invalid_provenance", "target_must_differ_from_subject", readiness)
        if event_kind in {"switch_hazards_observed", "tailwind_side_condition_observed"} and side not in {"self", "opponent"}: return _result("invalid_provenance", "side_owner_mismatch", readiness)
        if event_kind == "current_leech_seed_state_observed" and payload.get("persistent_state") == "active" and payload.get("source_side") == side: return _result("invalid_provenance", "leech_seed_source_must_be_opposite_side", readiness)
        oid = observation_id or f"{self._session_id}:obs:{self._next_sequence}"
        record = {"event_kind": event_kind, "observation_id": oid, "session_id": self._session_id, "turn_number": turn_number, "source": source, "trust": trust, "confirmed": True, "observed": True, "payload": deepcopy(payload), "reducer_eligibility": "evidence_only" if event_kind in {"direct_move_damage_observed", "flinch_causality_observed", "contact_reactive_status_result_observed", "contact_reactive_damage_result_observed"} else "candidate"}
        if side is not None: record.update(side=side, slot_index=slot_index, pokemon_id=pokemon_id)
        if event_kind == "pokemon_switch_observed": record.update(**{key: payload[key] for key in ("switch_out_slot_index", "switch_out_pokemon_id", "switch_in_slot_index", "switch_in_pokemon_id")}, switch_kind="unknown")
        if event_kind == "used_move_observed": record.update(move_id=payload["move_id"], move_slot=payload.get("move_slot"))
        if event_kind == "executed_move_observed": record.update(move_id=payload["move_id"], source_action_id=payload["source_action_id"])
        if event_kind == "previous_action_result_observed": record.update(**deepcopy(payload))
        if event_kind.endswith("restriction_applied_observed") or event_kind.endswith("restricted_turn_completed_observed"): record.update(**deepcopy(payload))
        if event_kind == "same_turn_event_observed": record.update(predicate=payload["predicate"], occurred=payload["occurred"], target_side=payload["target_side"], target_slot_index=payload["target_slot_index"], target_pokemon_id=payload["target_pokemon_id"])
        if event_kind in {"exact_hp_transition_observed", "exact_hp_recovery_observed"}: record.update(hp_before=payload["hp_before"], hp_after=payload["hp_after"], hp_unit="exact")
        if related_observation_id is not None: record["related_observation_id"] = related_observation_id
        prior = self._records.get(oid)
        if prior is not None:
            same = _same_record(prior, record)
            return _result("duplicate" if same else "conflicting_confirmation", "duplicate" if same else "conflicting_observation_id", readiness, duplicate=oid, conflicts=[] if same else [{"observation_id": oid, "reason": "conflicting_confirmation"}])
        record["observation_sequence"] = self._next_sequence; self._next_sequence += 1; self._records[oid] = deepcopy(record)
        return {"status": "confirmed", "observation": deepcopy(record), "duplicate_observation_id": None, "conflicts": [], "excluded_reason": None, "production_readiness": readiness, "limitations": ["structured_only", "no_store_or_reducer_application", "no_ui_mutation", "provider_budget_0"]}

    def accept_switch_entry_derived(self, result):
        """Admit only the explicit mechanics-derived family after its source switch.

        This is intentionally separate from ``confirm`` so USER_TRUST production
        confirmation rules remain unchanged.
        """
        observation = result.get("observation") if isinstance(result, dict) and result.get("status") == "confirmed" else None
        if not isinstance(observation, dict) or observation.get("event_kind") not in DERIVED_KINDS:
            return _result("invalid_provenance", "unsupported_switch_entry_derived_event")
        payload = observation.get("payload")
        source_id = payload.get("source_switch_observation_id") if isinstance(payload, dict) else None
        source = self._records.get(source_id)
        if (observation.get("session_id") != self._session_id
                or observation.get("trust") != MECHANICS_DERIVED_TRUST
                or observation.get("source") != SWITCH_ENTRY_MECHANICS_SOURCE
                or not isinstance(source, dict)
                or source.get("event_kind") != "pokemon_switch_observed"
                or source.get("turn_number") != observation.get("turn_number")
                or source.get("observation_sequence", 0) >= observation.get("observation_sequence", 0)
                or observation.get("observation_sequence") != self._next_sequence):
            return _result("invalid_provenance", "invalid_switch_entry_derived_binding")
        oid = observation.get("observation_id")
        if not isinstance(oid, str) or not oid:
            return _result("invalid_provenance", "invalid_switch_entry_derived_id")
        prior = self._records.get(oid)
        if prior is not None:
            return _result("duplicate" if prior == observation else "conflicting_confirmation", "duplicate" if prior == observation else "conflicting_observation_id")
        self._records[oid] = deepcopy(observation)
        self._next_sequence += 1
        return {"status": "confirmed", "observation": deepcopy(observation), "duplicate_observation_id": None, "conflicts": [], "excluded_reason": None, "production_readiness": "mechanics_derived", "limitations": ["structured_only", "no_store_or_reducer_application", "no_ui_mutation", "provider_budget_0"]}


def _owner_matches(owners, side, slot, pokemon):
    value = owners.get(side) if isinstance(owners, dict) else None
    if isinstance(value, dict) and value.get("slot_index") == slot and value.get("pokemon_id") == pokemon:
        return True
    targets = owners.get(f"{side}_targets") if isinstance(owners, dict) else None
    return isinstance(targets, (tuple, list)) and any(isinstance(row, dict) and row.get("slot_index") == slot and row.get("pokemon_id") == pokemon for row in targets)
def _production_source_matches(kind, source):
    if kind == "current_locked_on_state_observed": return source == LOCKED_ON_SOURCE
    if kind == "gravity_field_observed": return source == GRAVITY_SOURCE
    if kind == "current_condition_observed" and source == CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE: return True
    if kind == "current_condition_observed" and source == PARALYSIS_APPLICATION_SOURCE: return True
    if kind == "mat_block_active_entry_eligibility_observed": return source == MAT_BLOCK_ACTIVE_ENTRY_ELIGIBILITY_SOURCE
    if kind == "fake_out_active_entry_eligibility_observed": return source == FAKE_OUT_ACTIVE_ENTRY_ELIGIBILITY_SOURCE
    if kind == "supreme_overlord_initial_active_observed": return source == SUPREME_OVERLORD_INITIAL_ACTIVE_SOURCE
    if kind == "berry_eaten_state_observed": return source == BERRY_EATEN_STATE_SOURCE
    if kind == "executed_move_observed": return source == EXECUTED_MOVE_SOURCE
    if kind == "previous_action_result_observed": return source == PREVIOUS_ACTION_RESULT_SOURCE
    if kind == "flinch_causality_observed": return source == FLINCH_CAUSALITY_SOURCE
    if kind == "contact_reactive_status_result_observed": return source == CONTACT_REACTIVE_STATUS_RESULT_SOURCE
    if kind == "contact_reactive_damage_result_observed": return source == CONTACT_REACTIVE_DAMAGE_RESULT_SOURCE
    if kind in {"current_aqua_ring_state_observed", "current_ingrain_state_observed", "current_leech_seed_state_observed"}: return source == PERSISTENT_EFFECT_SOURCE
    if kind in {"current_confusion_state_observed", "champions_confusion_progression_observed"}: return source == CONFUSION_SOURCE
    if kind == "champions_status_progression_observed": return source == STATUS_PROGRESSION_SOURCE
    if kind.endswith("restriction_applied_observed") or kind.endswith("restricted_turn_completed_observed"): return source == RESTRICTION_SOURCE
    return {"direct_move_damage_observed": PRODUCTION_SOURCE, "used_move_observed": USED_MOVE_SOURCE, "exact_hp_transition_observed": HP_TRANSITION_SOURCE, "exact_hp_recovery_observed": HP_RECOVERY_SOURCE, "current_type_observed": CURRENT_TYPE_SOURCE, "current_condition_observed": CURRENT_CONDITION_SOURCE, "current_healing_prevented_observed": CURRENT_HEALING_PREVENTED_SOURCE, "pending_status_action_execution_observed": PENDING_STATUS_ACTION_EXECUTION_SOURCE, "doubles_active_topology_observed": DOUBLES_ACTIVE_TOPOLOGY_SOURCE, "selected_action_targeting_observed": SELECTED_ACTION_TARGETING_SOURCE, "current_weather_observed": CURRENT_WEATHER_SOURCE, "current_ability_observed": CURRENT_ABILITY_SOURCE, "current_item_observed": CURRENT_ITEM_SOURCE, "current_terrain_observed": CURRENT_TERRAIN_SOURCE, "current_side_conditions_observed": CURRENT_SIDE_CONDITIONS_SOURCE, "current_battle_format_observed": CURRENT_BATTLE_FORMAT_SOURCE, "current_level_observed": CURRENT_LEVEL_SOURCE, "current_final_combat_stat_observed": FINAL_COMBAT_STAT_SOURCE, "current_opponent_response_set_observed": OPPONENT_RESPONSE_SET_SOURCE, "current_opponent_switch_response_set_observed": OPPONENT_SWITCH_RESPONSE_SET_SOURCE, "current_opponent_switch_target_combat_observed": OPPONENT_SWITCH_TARGET_COMBAT_SOURCE, "substitute_state_observed": SUBSTITUTE_STATE_SOURCE, "pokemon_switch_observed": SWITCH_SOURCE, "pokemon_faint_observed": FAINT_SOURCE, "condition_applied_observed": CONDITION_APPLICATION_SOURCE, "stat_stage_observed": STAT_STAGE_SOURCE, "switch_hazards_observed": HAZARD_STATE_SOURCE, "tailwind_side_condition_observed": TAILWIND_SOURCE, "trick_room_field_observed": TRICK_ROOM_SOURCE, "magic_room_field_observed": MAGIC_ROOM_SOURCE, "gravity_field_observed": GRAVITY_SOURCE, "current_locked_on_state_observed": LOCKED_ON_SOURCE, "same_turn_event_observed": SAME_TURN_EVENT_SOURCE, "first_end_of_turn_reached_observed": FIRST_END_OF_TURN_SOURCE}.get(kind) == source
def _valid_turn_number(value): return value is None or (isinstance(value, int) and not isinstance(value, bool) and value > 0)
def _same_record(prior, candidate):
    left, right = deepcopy(prior), deepcopy(candidate); left.pop("observation_sequence", None); return left == right

def _valid_payload(kind, payload):
    if kind == "direct_move_damage_observed": return isinstance(payload.get("damage_amount"), int) and not isinstance(payload.get("damage_amount"), bool) and payload["damage_amount"] >= 0 and payload.get("hp_unit") == "exact"
    if kind == "exact_hp_transition_observed": return all(isinstance(payload.get(key), int) and not isinstance(payload.get(key), bool) and payload[key] >= 0 for key in ("hp_before", "hp_after")) and payload["hp_after"] <= payload["hp_before"]
    if kind == "exact_hp_recovery_observed": return all(isinstance(payload.get(key), int) and not isinstance(payload.get(key), bool) and payload[key] >= 0 for key in ("hp_before", "hp_after")) and payload["hp_before"] > 0 and payload["hp_after"] >= payload["hp_before"]
    if kind == "current_type_observed":
        types = payload.get("types")
        normalized = {value.strip().lower().replace("_", "-") for value in types} if isinstance(types, list) and all(isinstance(value, str) for value in types) else set()
        return set(payload) == {"types"} and isinstance(types, list) and 1 <= len(types) <= 2 and len(normalized) == len(types) and normalized <= {"normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison", "ground", "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy"}
    if kind == "current_condition_observed": return set(payload) == {"condition"} and payload.get("condition") in {"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
    if kind == "current_locked_on_state_observed":
        status = payload.get("status")
        if status == "inactive": return set(payload) == {"status"}
        target = payload.get("bound_target")
        return (set(payload) == {"status", "bound_target"} and status == "active" and isinstance(target, dict)
                and set(target) == {"session_id", "side", "slot_index", "pokemon_id"}
                and isinstance(target.get("session_id"), str) and bool(target["session_id"])
                and target.get("side") in {"self", "opponent"}
                and isinstance(target.get("slot_index"), int) and not isinstance(target.get("slot_index"), bool) and target["slot_index"] >= 0
                and isinstance(target.get("pokemon_id"), str) and bool(target["pokemon_id"]))
    if kind == "current_healing_prevented_observed": return set(payload) == {"status"} and payload.get("status") in {"active", "inactive"}
    if kind in {"current_aqua_ring_state_observed", "current_ingrain_state_observed"}: return set(payload) == {"persistent_state"} and payload.get("persistent_state") in {"active", "inactive"}
    if kind == "current_leech_seed_state_observed":
        if payload.get("persistent_state") == "inactive": return set(payload) == {"persistent_state"}
        return set(payload) == {"persistent_state", "source_side", "source_slot_index"} and payload.get("persistent_state") == "active" and payload.get("source_side") in {"self", "opponent"} and isinstance(payload.get("source_slot_index"), int) and not isinstance(payload.get("source_slot_index"), bool) and payload["source_slot_index"] >= 0
    if kind == "current_confusion_state_observed": return set(payload) == {"state"} and payload.get("state") in {"confused", "none"}
    if kind == "champions_confusion_progression_observed":
        return (set(payload) == {"state", "origin_id", "established_turn", "prior_opportunities", "duration"}
                and payload.get("state") == "confused" and isinstance(payload.get("origin_id"), str) and bool(payload["origin_id"])
                and isinstance(payload.get("established_turn"), int) and not isinstance(payload.get("established_turn"), bool) and payload["established_turn"] >= 1
                and payload.get("prior_opportunities") == 0 and payload.get("duration") is None)
    if kind == "champions_status_progression_observed":
        condition, established, attempts, duration = payload.get("condition"), payload.get("established_turn"), payload.get("prior_attempts"), payload.get("sleep_duration")
        return (set(payload) == {"condition", "origin_id", "established_turn", "prior_attempts", "sleep_duration"}
                and condition in {"sleep", "freeze"} and isinstance(payload.get("origin_id"), str) and bool(payload["origin_id"])
                and isinstance(established, int) and not isinstance(established, bool) and established >= 1
                and isinstance(attempts, int) and not isinstance(attempts, bool) and 0 <= attempts <= 2
                and (duration is None or type(duration) is int and duration in {2, 3})
                and (condition == "sleep" or duration is None))
    if kind == "pending_status_action_execution_observed":
        condition, state, blocker, outcome = (payload.get("condition"), payload.get("execution_state"),
                                               payload.get("blocker"), payload.get("outcome_class"))
        if set(payload) != {"decision_point", "action_id", "move_id", "condition", "execution_state", "blocker", "outcome_class"} or not all(isinstance(payload.get(key), str) and bool(payload[key]) for key in ("decision_point", "action_id", "move_id", "outcome_class")):
            return False
        if outcome == "blocked_sleep": return condition == "sleep" and state == "blocked" and blocker == "sleep"
        if outcome == "blocked_freeze": return condition == "freeze" and state == "blocked" and blocker == "freeze"
        if outcome == "wake_and_execute": return condition == "sleep" and state == "executable" and blocker is None
        if outcome == "sleep_exception_execute": return condition == "sleep" and state == "executable" and blocker is None and payload.get("move_id") in SLEEP_EXCEPTIONS
        if outcome == "natural_thaw_and_execute": return condition == "freeze" and state == "executable" and blocker is None
        if outcome == "self_thaw_move_execute": return condition == "freeze" and state == "executable" and blocker is None and payload.get("move_id") in SELF_THAW_MOVES
        return False
    if kind == "mat_block_active_entry_eligibility_observed": return set(payload) == {"decision_point", "action_id", "move_id", "active_entry_token", "eligibility"} and all(isinstance(payload.get(key), str) and bool(payload[key]) for key in ("decision_point", "action_id", "active_entry_token")) and payload.get("move_id") == "mat-block" and payload.get("eligibility") in {"eligible", "ineligible"}
    if kind == "fake_out_active_entry_eligibility_observed": return set(payload) == {"decision_point", "action_id", "move_id", "active_entry_token", "eligibility"} and all(isinstance(payload.get(key), str) and bool(payload[key]) for key in ("decision_point", "action_id", "active_entry_token")) and payload.get("move_id") == "fake-out" and payload.get("eligibility") in {"eligible", "ineligible"}
    if kind == "supreme_overlord_initial_active_observed": return set(payload) == {"entry_token", "cumulative_allied_faint_count"} and isinstance(payload.get("entry_token"), str) and bool(payload["entry_token"]) and isinstance(payload.get("cumulative_allied_faint_count"), int) and not isinstance(payload.get("cumulative_allied_faint_count"), bool) and payload["cumulative_allied_faint_count"] >= 0
    if kind == "doubles_active_topology_observed":
        rows = payload.get("active_owners")
        return set(payload) == {"active_owners"} and isinstance(rows, list) and len(rows) == 4 and len({(row.get("side"), row.get("active_slot_index")) for row in rows if isinstance(row, dict)}) == 4 and all(isinstance(row, dict) and set(row) == {"side", "active_slot_index", "pokemon_id", "active"} and row.get("side") in {"self", "opponent"} and isinstance(row.get("active_slot_index"), int) and not isinstance(row.get("active_slot_index"), bool) and row["active_slot_index"] >= 0 and isinstance(row.get("pokemon_id"), str) and bool(row["pokemon_id"]) and row.get("active") is True for row in rows) and {row["side"] for row in rows} == {"self", "opponent"} and all(sum(row["side"] == side for row in rows) == 2 for side in ("self", "opponent"))
    if kind == "selected_action_targeting_observed":
        target = payload.get("selected_target")
        target_ok = target is None or (isinstance(target, dict) and set(target) == {"side", "active_slot_index", "pokemon_id"} and target.get("side") in {"self", "opponent"} and isinstance(target.get("active_slot_index"), int) and not isinstance(target.get("active_slot_index"), bool) and target["active_slot_index"] >= 0 and isinstance(target.get("pokemon_id"), str) and bool(target["pokemon_id"]))
        return set(payload) == {"decision_point", "action_id", "move_id", "selected_target"} and all(isinstance(payload.get(key), str) and bool(payload[key]) for key in ("decision_point", "action_id", "move_id")) and target_ok
    if kind == "current_level_observed": return set(payload) == {"level"} and isinstance(payload.get("level"), int) and not isinstance(payload.get("level"), bool) and 1 <= payload["level"] <= 100
    if kind == "current_final_combat_stat_observed": return set(payload) == {"stat", "value"} and payload.get("stat") in {"attack", "defense", "special-attack", "special-defense", "speed"} and isinstance(payload.get("value"), int) and not isinstance(payload.get("value"), bool) and 1 <= payload["value"] <= 9999
    if kind == "current_opponent_response_set_observed":
        moves, usability, pp = payload.get("move_ids"), payload.get("move_usability"), payload.get("move_pp_slots")
        reasons = {"no_pp", "disabled", "choice_lock", "encore_restriction", "other_supported_restriction", "observed_unclassified"}
        keys_ok = set(payload) in ({"move_ids", "move_usability"}, {"move_ids", "move_usability", "move_pp_slots"})
        base_ok = keys_ok and isinstance(moves, list) and len(moves) == 4 and len(set(moves)) == 4 and all(isinstance(move, str) and move and move == move.lower() and " " not in move and "_" not in move for move in moves) and isinstance(usability, dict) and set(usability) == set(moves) and all(isinstance(row, dict) and set(row) == {"status", "reason"} and row.get("status") in {"known_usable", "known_unusable"} and ((row["status"] == "known_usable" and row["reason"] is None) or (row["status"] == "known_unusable" and row["reason"] in reasons)) for row in usability.values())
        if not base_ok or "move_pp_slots" not in payload:
            return base_ok
        if not isinstance(pp, list) or len(pp) != 4:
            return False
        for index, move in enumerate(moves):
            row = pp[index]
            if not isinstance(row, dict) or set(row) != {"slot_index", "move_id", "current_pp", "max_pp"}:
                return False
            current_pp, max_pp = row.get("current_pp"), row.get("max_pp")
            if row.get("slot_index") != index or row.get("move_id") != move or not isinstance(current_pp, int) or isinstance(current_pp, bool) or current_pp < 0 or not isinstance(max_pp, int) or isinstance(max_pp, bool) or max_pp <= 0 or current_pp > max_pp:
                return False
            u = usability[move]
            if u["status"] == "known_usable" and current_pp == 0:
                return False
            if u["status"] == "known_unusable" and u["reason"] == "no_pp" and current_pp > 0:
                return False
        return True
    if kind == "current_opponent_switch_response_set_observed":
        targets = payload.get("targets")
        return set(payload) == {"permission", "targets"} and payload.get("permission") in {"permitted", "blocked", "unknown"} and isinstance(targets, list) and all(isinstance(row, dict) and set(row) == {"slot_index", "pokemon_id", "availability"} and isinstance(row.get("slot_index"), int) and not isinstance(row.get("slot_index"), bool) and row["slot_index"] >= 0 and isinstance(row.get("pokemon_id"), str) and bool(row["pokemon_id"]) and row.get("availability") in {"alive", "fainted", "unknown"} for row in targets) and len({(row["slot_index"], row["pokemon_id"]) for row in targets}) == len(targets)
    if kind == "current_opponent_switch_target_combat_observed":
        stats, stages, types = payload.get("final_stats"), payload.get("stages"), payload.get("types")
        return set(payload) == {"current_hp", "max_hp", "fainted", "types", "final_stats", "stages", "condition", "item", "ability"} and isinstance(payload.get("current_hp"), int) and not isinstance(payload.get("current_hp"), bool) and isinstance(payload.get("max_hp"), int) and not isinstance(payload.get("max_hp"), bool) and payload["max_hp"] > 0 and 0 <= payload["current_hp"] <= payload["max_hp"] and isinstance(payload.get("fainted"), bool) and payload["fainted"] is (payload["current_hp"] == 0) and isinstance(types, list) and 1 <= len(types) <= 2 and all(isinstance(value, str) and value for value in types) and isinstance(stats, dict) and set(stats) == {"attack", "defense", "special-attack", "special-defense", "speed"} and all(isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 9999 for value in stats.values()) and isinstance(stages, dict) and set(stages) == {"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"} and all(isinstance(value, int) and not isinstance(value, bool) and -6 <= value <= 6 for value in stages.values()) and payload.get("condition") in {"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"} and ((payload.get("item") == {"status": "known_absent"}) or (isinstance(payload.get("item"), dict) and set(payload["item"]) == {"status", "item"} and payload["item"].get("status") == "known" and isinstance(payload["item"].get("item"), str) and bool(payload["item"]["item"]))) and isinstance(payload.get("ability"), str) and bool(payload["ability"])
    if kind == "substitute_state_observed":
        return (set(payload) == {"state", "substitute_hp"} and ((payload.get("state") == "known_active" and isinstance(payload.get("substitute_hp"), int) and not isinstance(payload.get("substitute_hp"), bool) and payload["substitute_hp"] > 0) or (payload.get("state") == "known_inactive" and payload.get("substitute_hp") is None)))
    if kind == "current_weather_observed": return set(payload) == {"weather"} and payload.get("weather") in {"none", "sun", "rain", "sandstorm", "snow"}
    if kind == "current_ability_observed":
        ability = payload.get("ability")
        return set(payload) == {"ability"} and isinstance(ability, str) and bool(ability.strip()) and all(token not in ability for token in (",", "/", ";", "|"))
    if kind == "current_item_observed":
        return (set(payload) == {"status", "item"} and payload.get("status") == "known" and isinstance(payload.get("item"), str) and bool(payload["item"].strip())) or (payload == {"status": "known_absent"})
    if kind == "berry_eaten_state_observed":
        state, basis = payload.get("state"), payload.get("basis")
        if state == "known_false":
            return set(payload) == {"state", "basis"} and basis == "fresh_battle_initialization"
        if state == "known_true":
            return set(payload) == {"state", "basis", "item_id"} and basis == "observed_berry_consumption" and isinstance(payload.get("item_id"), str) and bool(payload["item_id"])
        return False
    if kind == "current_terrain_observed": return set(payload) == {"terrain"} and payload.get("terrain") in {"none", "electric", "grassy", "misty", "psychic"}
    if kind == "current_side_conditions_observed":
        values = payload.get("side_conditions")
        return set(payload) == {"side_conditions"} and isinstance(values, list) and len(values) == len(set(values)) and all(value in {"reflect", "light-screen", "aurora-veil", "tailwind"} for value in values)
    if kind == "current_battle_format_observed": return set(payload) == {"battle_format"} and payload.get("battle_format") in {"singles", "doubles"}
    if kind == "used_move_observed": return isinstance(payload.get("move_id"), str) and bool(payload["move_id"]) and (payload.get("move_slot") is None or isinstance(payload.get("move_slot"), int))
    if kind == "executed_move_observed": return set(payload) == {"move_id", "source_action_id"} and all(isinstance(payload.get(key), str) and bool(payload[key]) and payload[key] == payload[key].lower() and " " not in payload[key] and "_" not in payload[key] for key in ("move_id", "source_action_id"))
    if kind == "previous_action_result_observed": return set(payload) == {"previous_action_id", "selected_move_id", "execution_move_id", "result_class"} and all(isinstance(payload.get(key), str) and bool(payload[key]) and payload[key] == payload[key].lower() and " " not in payload[key] and "_" not in payload[key] for key in ("previous_action_id", "selected_move_id", "execution_move_id")) and payload.get("result_class") in {"accuracy_miss", "type_or_ability_immunity", "move_specific_failure", "full_paralysis", "flinch", "sleep", "freeze", "success", "protection_block", "recharge", "sky_drop"}
    if kind == "flinch_causality_observed":
        keys = {"producer_source_action_id", "producer_move_id", "producer_owner", "producer_execution_observation_id", "affected_owner", "cancelled_source_action_id", "cancelled_move_id", "cancelled_execution_observation_id", "cancelled_result_observation_id", "producer_predictive_ledger_fingerprint"}
        if set(payload) != keys or payload.get("producer_source_action_id") == payload.get("cancelled_source_action_id"): return False
        if not all(isinstance(payload.get(key), str) and bool(payload[key]) for key in ("producer_source_action_id", "producer_move_id", "producer_execution_observation_id", "cancelled_source_action_id", "cancelled_move_id", "cancelled_execution_observation_id", "cancelled_result_observation_id", "producer_predictive_ledger_fingerprint")): return False
        for owner_key in ("producer_owner", "affected_owner"):
            owner = payload.get(owner_key)
            if not isinstance(owner, dict) or set(owner) != {"session_id", "side", "slot_index", "pokemon_id"} or owner.get("session_id") is None or owner.get("side") not in {"self", "opponent"} or not isinstance(owner.get("slot_index"), int) or isinstance(owner.get("slot_index"), bool) or owner["slot_index"] < 0 or not isinstance(owner.get("pokemon_id"), str) or not owner["pokemon_id"]: return False
        return payload["producer_owner"]["side"] != payload["affected_owner"]["side"]
    if kind == "contact_reactive_status_result_observed":
        keys = {"source_action_id", "move_id", "reactive_ability", "outcome", "attacker_side", "attacker_slot_index", "attacker_pokemon_id", "defender_side", "defender_slot_index", "defender_pokemon_id", "hp_before", "hp_after"}
        ability, outcome = payload.get("reactive_ability"), payload.get("outcome")
        valid_outcome = (ability in {"static", "flame-body", "poison-point"} and outcome in {"activation", "no_activation"}) or (ability == "effect-spore" and outcome in {"sleep", "paralysis", "poison", "none"})
        return set(payload) == keys and all(isinstance(payload.get(key), str) and bool(payload[key]) and payload[key] == payload[key].lower() and " " not in payload[key] and "_" not in payload[key] for key in ("source_action_id", "move_id")) and valid_outcome and payload.get("attacker_side") in {"self", "opponent"} and payload.get("defender_side") in {"self", "opponent"} and payload["attacker_side"] != payload["defender_side"] and all(isinstance(payload.get(key), int) and not isinstance(payload[key], bool) and payload[key] >= 0 for key in ("attacker_slot_index", "defender_slot_index", "hp_before", "hp_after")) and payload["hp_before"] > payload["hp_after"] and all(isinstance(payload.get(key), str) and bool(payload[key]) for key in ("attacker_pokemon_id", "defender_pokemon_id"))
    if kind == "contact_reactive_damage_result_observed":
        keys = {"source_action_id", "move_id", "attacker_side", "attacker_slot_index", "attacker_pokemon_id", "defender_side", "defender_slot_index", "defender_pokemon_id", "hp_before", "hp_after", "source_hit_actual_damage", "source_hit_target_routing", "ordered_sources"}
        ordered = payload.get("ordered_sources")
        if set(payload) != keys or not all(isinstance(payload.get(key), str) and bool(payload[key]) and payload[key] == payload[key].lower() and " " not in payload[key] and "_" not in payload[key] for key in ("source_action_id", "move_id")): return False
        if payload.get("attacker_side") not in {"self", "opponent"} or payload.get("defender_side") not in {"self", "opponent"} or payload["attacker_side"] == payload["defender_side"]: return False
        if not all(isinstance(payload.get(key), int) and not isinstance(payload[key], bool) and payload[key] >= 0 for key in ("attacker_slot_index", "defender_slot_index", "hp_before", "hp_after")) or payload["hp_before"] <= payload["hp_after"]: return False
        if not all(isinstance(payload.get(key), str) and bool(payload[key]) for key in ("attacker_pokemon_id", "defender_pokemon_id")) or not isinstance(payload.get("source_hit_actual_damage"), int) or isinstance(payload["source_hit_actual_damage"], bool) or payload["source_hit_actual_damage"] <= 0 or payload.get("source_hit_target_routing") != "target" or not isinstance(ordered, list) or not ordered: return False
        current = payload["hp_before"]
        for index, row in enumerate(ordered, 1):
            if not isinstance(row, dict) or row.get("order_index") != index or row.get("source_kind") not in {"rough-skin", "iron-barbs", "rocky-helmet"}: return False
            damage, pre_hp, post_hp = row.get("reactive_damage"), row.get("pre_hp"), row.get("post_hp")
            if not isinstance(damage, int) or isinstance(damage, bool) or damage < 0 or pre_hp != current or not isinstance(post_hp, int) or isinstance(post_hp, bool) or post_hp < 0 or post_hp != max(0, pre_hp - damage): return False
            current = post_hp
        return current == payload["hp_after"]
    if kind == "taunt_restriction_applied_observed": return set(payload) == {"source_action_id", "source_move_id"} and isinstance(payload.get("source_action_id"), str) and bool(payload["source_action_id"]) and payload.get("source_move_id") == "taunt"
    if kind in {"encore_restriction_applied_observed", "disable_restriction_applied_observed"}: return set(payload) == {"source_action_id", "source_move_id", "locked_move_id" if kind.startswith("encore") else "disabled_move_id", "last_used_execution_id"} and all(isinstance(value, str) and bool(value) for value in payload.values()) and payload.get("source_move_id") == ("encore" if kind.startswith("encore") else "disable")
    if kind.endswith("restricted_turn_completed_observed"): return payload == {"completion_kind": "affected_active_turn_completed"}
    if kind == "pokemon_switch_observed": return all(isinstance(payload.get(key), int) and not isinstance(payload.get(key), bool) and payload[key] >= 0 for key in ("switch_out_slot_index", "switch_in_slot_index")) and all(isinstance(payload.get(key), str) and payload[key] for key in ("switch_out_pokemon_id", "switch_in_pokemon_id")) and (payload["switch_out_slot_index"], payload["switch_out_pokemon_id"]) != (payload["switch_in_slot_index"], payload["switch_in_pokemon_id"])
    if kind == "condition_applied_observed": return payload.get("condition") in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
    if kind == "stat_stage_observed": return payload.get("stat") in {"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"} and isinstance(payload.get("stage"), int) and not isinstance(payload.get("stage"), bool) and -6 <= payload["stage"] <= 6
    if kind == "switch_hazards_observed": return set(payload) == {"stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web"} and payload.get("stealth_rock") in {"present", "absent"} and isinstance(payload.get("spikes_layers"), int) and not isinstance(payload.get("spikes_layers"), bool) and payload["spikes_layers"] in {0,1,2,3} and isinstance(payload.get("toxic_spikes_layers"), int) and not isinstance(payload.get("toxic_spikes_layers"), bool) and payload["toxic_spikes_layers"] in {0,1,2} and payload.get("sticky_web") in {"present", "absent"}
    if kind == "tailwind_side_condition_observed": return set(payload) == {"status"} and payload.get("status") in {"active", "inactive"}
    if kind == "trick_room_field_observed": return set(payload) == {"status"} and payload.get("status") in {"active", "inactive"}
    if kind == "magic_room_field_observed": return set(payload) == {"status"} and payload.get("status") in {"active", "inactive"}
    if kind == "gravity_field_observed": return set(payload) == {"status"} and payload.get("status") in {"active", "inactive"}
    if kind == "same_turn_event_observed": return payload.get("predicate") in {"received_qualifying_direct_damage", "acted_earlier_this_turn", "lost_hp_this_turn", "qualifying_direct_damage_dealt"} and isinstance(payload.get("occurred"), bool) and payload.get("target_side") in {"self", "opponent"} and isinstance(payload.get("target_slot_index"), int) and not isinstance(payload.get("target_slot_index"), bool) and payload["target_slot_index"] >= 0 and isinstance(payload.get("target_pokemon_id"), str) and bool(payload["target_pokemon_id"])
    if kind == "first_end_of_turn_reached_observed": return payload == {}
    return bool(payload)
def _result(status, reason, readiness=None, duplicate=None, conflicts=None): return {"status": status, "observation": None, "duplicate_observation_id": duplicate, "conflicts": conflicts or [], "excluded_reason": reason, "production_readiness": readiness, "limitations": ["structured_only", "no_store_or_reducer_application", "no_ui_mutation", "provider_budget_0"]}
