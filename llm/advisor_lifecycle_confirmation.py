"""Private trusted-lifecycle confirmation boundary; no reducer/store integration."""
from copy import deepcopy

PRODUCTION_SOURCE = "ui_observed_damage_confirmation"
USED_MOVE_SOURCE = "ui_used_move_confirmation"
HP_TRANSITION_SOURCE = "ui_exact_hp_transition_confirmation"
HP_RECOVERY_SOURCE = "ui_exact_hp_recovery_confirmation"
SWITCH_SOURCE = "ui_switch_confirmation"
FAINT_SOURCE = "ui_faint_confirmation"
CONDITION_APPLICATION_SOURCE = "ui_condition_application_confirmation"
STAT_STAGE_SOURCE = "ui_stat_stage_confirmation"
HAZARD_STATE_SOURCE = "ui_switch_hazard_state_confirmation"
TAILWIND_SOURCE = "ui_tailwind_side_condition_confirmation"
FIXTURE_SOURCE = "fixture_contract_confirmation"
USER_TRUST = "user_confirmed_observation"
FIXTURE_TRUST = "fixture_contract_only"
_KINDS = {"direct_move_damage_observed": "production_ready", "used_move_observed": "production_ready", "exact_hp_transition_observed": "production_ready", "exact_hp_recovery_observed": "production_ready", "pokemon_switch_observed": "production_ready", "pokemon_faint_observed": "production_ready", "condition_applied_observed": "production_ready", "stat_stage_observed": "production_ready", "switch_hazards_observed": "production_ready", "tailwind_side_condition_observed": "production_ready", "condition_removed_observed": "fixture_only", "item_consumption_observed": "fixture_only", "item_removed_observed": "fixture_only", "weather_started_observed": "fixture_only", "weather_ended_observed": "fixture_only", "terrain_started_observed": "fixture_only", "terrain_ended_observed": "fixture_only", "side_condition_started_observed": "fixture_only", "side_condition_ended_observed": "fixture_only"}


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
        if event_kind not in {"direct_move_damage_observed", "switch_hazards_observed", "tailwind_side_condition_observed"} and not _owner_matches(self._owners, side, slot_index, pokemon_id): return _result("invalid_provenance", "owner_mismatch", readiness)
        if event_kind in {"switch_hazards_observed", "tailwind_side_condition_observed"} and side not in {"self", "opponent"}: return _result("invalid_provenance", "side_owner_mismatch", readiness)
        oid = observation_id or f"{self._session_id}:obs:{self._next_sequence}"
        record = {"event_kind": event_kind, "observation_id": oid, "session_id": self._session_id, "turn_number": turn_number, "source": source, "trust": trust, "confirmed": True, "observed": True, "payload": deepcopy(payload), "reducer_eligibility": "candidate" if event_kind != "direct_move_damage_observed" else "evidence_only"}
        if side is not None: record.update(side=side, slot_index=slot_index, pokemon_id=pokemon_id)
        if event_kind == "pokemon_switch_observed": record.update(**{key: payload[key] for key in ("switch_out_slot_index", "switch_out_pokemon_id", "switch_in_slot_index", "switch_in_pokemon_id")}, switch_kind="unknown")
        if event_kind == "used_move_observed": record.update(move_id=payload["move_id"], move_slot=payload.get("move_slot"))
        if event_kind in {"exact_hp_transition_observed", "exact_hp_recovery_observed"}: record.update(hp_before=payload["hp_before"], hp_after=payload["hp_after"], hp_unit="exact")
        if related_observation_id is not None: record["related_observation_id"] = related_observation_id
        prior = self._records.get(oid)
        if prior is not None:
            same = _same_record(prior, record)
            return _result("duplicate" if same else "conflicting_confirmation", "duplicate" if same else "conflicting_observation_id", readiness, duplicate=oid, conflicts=[] if same else [{"observation_id": oid, "reason": "conflicting_confirmation"}])
        record["observation_sequence"] = self._next_sequence; self._next_sequence += 1; self._records[oid] = deepcopy(record)
        return {"status": "confirmed", "observation": deepcopy(record), "duplicate_observation_id": None, "conflicts": [], "excluded_reason": None, "production_readiness": readiness, "limitations": ["structured_only", "no_store_or_reducer_application", "no_ui_mutation", "provider_budget_0"]}


def _owner_matches(owners, side, slot, pokemon):
    value = owners.get(side) if isinstance(owners, dict) else None
    return isinstance(value, dict) and value.get("slot_index") == slot and value.get("pokemon_id") == pokemon
def _production_source_matches(kind, source): return {"direct_move_damage_observed": PRODUCTION_SOURCE, "used_move_observed": USED_MOVE_SOURCE, "exact_hp_transition_observed": HP_TRANSITION_SOURCE, "exact_hp_recovery_observed": HP_RECOVERY_SOURCE, "pokemon_switch_observed": SWITCH_SOURCE, "pokemon_faint_observed": FAINT_SOURCE, "condition_applied_observed": CONDITION_APPLICATION_SOURCE, "stat_stage_observed": STAT_STAGE_SOURCE, "switch_hazards_observed": HAZARD_STATE_SOURCE, "tailwind_side_condition_observed": TAILWIND_SOURCE}.get(kind) == source
def _valid_turn_number(value): return value is None or (isinstance(value, int) and not isinstance(value, bool) and value > 0)
def _same_record(prior, candidate):
    left, right = deepcopy(prior), deepcopy(candidate); left.pop("observation_sequence", None); return left == right

def _valid_payload(kind, payload):
    if kind == "direct_move_damage_observed": return isinstance(payload.get("damage_amount"), int) and not isinstance(payload.get("damage_amount"), bool) and payload["damage_amount"] >= 0 and payload.get("hp_unit") == "exact"
    if kind == "exact_hp_transition_observed": return all(isinstance(payload.get(key), int) and not isinstance(payload.get(key), bool) and payload[key] >= 0 for key in ("hp_before", "hp_after")) and payload["hp_after"] <= payload["hp_before"]
    if kind == "exact_hp_recovery_observed": return all(isinstance(payload.get(key), int) and not isinstance(payload.get(key), bool) and payload[key] >= 0 for key in ("hp_before", "hp_after")) and payload["hp_before"] > 0 and payload["hp_after"] >= payload["hp_before"]
    if kind == "used_move_observed": return isinstance(payload.get("move_id"), str) and bool(payload["move_id"]) and (payload.get("move_slot") is None or isinstance(payload.get("move_slot"), int))
    if kind == "pokemon_switch_observed": return all(isinstance(payload.get(key), int) and not isinstance(payload.get(key), bool) and payload[key] >= 0 for key in ("switch_out_slot_index", "switch_in_slot_index")) and all(isinstance(payload.get(key), str) and payload[key] for key in ("switch_out_pokemon_id", "switch_in_pokemon_id")) and (payload["switch_out_slot_index"], payload["switch_out_pokemon_id"]) != (payload["switch_in_slot_index"], payload["switch_in_pokemon_id"])
    if kind == "condition_applied_observed": return payload.get("condition") in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}
    if kind == "stat_stage_observed": return payload.get("stat") in {"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"} and isinstance(payload.get("stage"), int) and not isinstance(payload.get("stage"), bool) and -6 <= payload["stage"] <= 6
    if kind == "switch_hazards_observed": return set(payload) == {"stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web"} and payload.get("stealth_rock") in {"present", "absent"} and isinstance(payload.get("spikes_layers"), int) and not isinstance(payload.get("spikes_layers"), bool) and payload["spikes_layers"] in {0,1,2,3} and isinstance(payload.get("toxic_spikes_layers"), int) and not isinstance(payload.get("toxic_spikes_layers"), bool) and payload["toxic_spikes_layers"] in {0,1,2} and payload.get("sticky_web") in {"present", "absent"}
    if kind == "tailwind_side_condition_observed": return set(payload) == {"status"} and payload.get("status") in {"active", "inactive"}
    return bool(payload)
def _result(status, reason, readiness=None, duplicate=None, conflicts=None): return {"status": status, "observation": None, "duplicate_observation_id": duplicate, "conflicts": conflicts or [], "excluded_reason": reason, "production_readiness": readiness, "limitations": ["structured_only", "no_store_or_reducer_application", "no_ui_mutation", "provider_budget_0"]}
