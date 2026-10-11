"""One-way runtime snapshot to detached, conditional Showdown simulations.

No store, reducer, UI, provider, or ranking entry point is changed by this module.
Complete teams, seeds, histories and choices must be supplied explicitly.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any

from advisor.showdown_bridge import FORMAT_ID, SCHEMA_VERSION, ShowdownBridge, ShowdownBridgeError
from llm.advisor_showdown_compatibility import OBSERVATION_SCHEMA, confirmed_absence, legacy_status_projection
from llm.advisor_switch_hazard_authority import normalize_switch_hazard_context
from llm.advisor_battle_decision_phase import KEY as PHASE_KEY
from llm.advisor_reducer_state_model import (
    STATE_MODEL_VERSION, is_unknown_battle_fact, state_fingerprint,
    validate_battle_state_unknown_markers,
)

_STATS = {"attack": "atk", "defense": "def", "special-attack": "spa",
          "special-defense": "spd", "speed": "spe", "accuracy": "accuracy", "evasion": "evasion"}
_CONDITIONS = {None: "", "none": "", "burn": "brn", "poison": "psn", "toxic": "tox",
               "paralysis": "par", "sleep": "slp", "freeze": "frz"}
LIMITATIONS = [
    "known_roster_hp_stages_overlaid_other_known_mechanics_verified_against_native_root",
    "teams_unobserved_state_counters_pp_and_history_are_explicit_hypotheses",
    "unmapped_known_runtime_mechanics_are_rejected",
    "seeded_samples_are_not_exact_probabilities",
    "native_requests_may_pause_for_switch_or_pivot_before_turn_advances",
    "no_live_state_or_ranking_writeback",
]


def simulate_detached_showdown(*, runtime_snapshot: dict, scenarios: list[dict], bridge: ShowdownBridge, _operation: str = "simulate") -> dict:
    """Simulate one explicit choice pair at a native move or switch boundary."""
    try:
        state = _state(runtime_snapshot)
        unmapped = _unmapped_observations(state)
        if unmapped:
            return {"status": "rejected", "reason": "unmapped_runtime_mechanics", "fields": unmapped}
        observed, roster, sides = {}, {}, {}
        for side in ("self", "opponent"):
            container = state[f"{side}_side"]
            active = container["pokemon"].get(container["active_slot_index"], container["pokemon"].get(str(container["active_slot_index"])))
            hp, maximum = active["current_hp"], active["max_hp"]
            alive = _int(hp, 1, 9999) and _int(maximum, hp, 9999) and active.get("fainted") is False
            fainted = hp == 0 and type(hp) is int and _int(maximum, 1, 9999) and active.get("fainted") is True
            if not (alive or fainted):
                # Unknown HP stays unknown in the runtime. Every eligible set
                # must explicitly supply the hypothetical active HP instead.
                if (not isinstance(scenarios, list) or not scenarios or
                    not all(isinstance(s, dict) and isinstance(s.get("hypothetical_active_hp"), dict) and
                        _int(s["hypothetical_active_hp"].get(side), 1, 9999) for s in scenarios) or
                    any(value is not None and not is_unknown_battle_fact(value) and not _int(value, 1, 9999) for value in (hp, maximum)) or
                    active.get("fainted") is True):
                    raise ValueError("observed_active_hp_required")
            row = _pokemon_observation(active, container["active_slot_index"], side=side, session_id=state["session_id"])
            roster[side] = [_pokemon_observation(pokemon, slot, side=side, session_id=state["session_id"]) for slot, pokemon in container["pokemon"].items()]
            sides[side] = {}
            conditions = container.get("side_conditions")
            if isinstance(conditions, list): sides[side]["side_conditions"] = deepcopy(conditions)
            tailwind = container.get("tailwind_status")
            if tailwind in ("active", "inactive"): sides[side]["tailwind"] = tailwind == "active"
            permission = container.get("switch_permission_context") or {}
            if permission.get("status") in ("permitted", "blocked"):
                sides[side]["switch_permitted"] = permission["status"] == "permitted"
            observed[side] = row
        hazards = state.get("switch_hazard_context")
        if hazards:
            side = hazards.get("affected_side")
            if side not in {"self", "opponent"} or hazards.get("session_id") != state["session_id"]:
                raise ValueError("invalid_observed_hazard_context")
            normalized = normalize_switch_hazard_context(hazards, session_id=state["session_id"], affected_side=side)
            keys = set(normalized) if hazards.get("schema_version") == "switch-hazard-context-v2" else {"schema_version", "session_id", "affected_side", "stealth_rock", "spikes_layers"}
            if set(hazards) != keys or any(hazards[k] != normalized[k] for k in keys - {"schema_version"}):
                raise ValueError("invalid_observed_hazard_context")
            sides[side]["hazards"] = {k: v for k, v in normalized.items()
                if k not in {"schema_version", "session_id", "affected_side"} and v != "unknown"}
        def owner_row(owner):
            rows = [p for p in roster[owner["side"]] if p["slot_index"] == owner["slot_index"] and p["pokemon_id"] == owner["pokemon_id"]]
            if len(rows) != 1 or owner["session_id"] != state["session_id"]: raise ValueError("observed_effect_owner_mismatch")
            return rows[0]
        for fact in (state.get("current_persistent_effect_context") or {}).get("rows", []):
            row = owner_row(fact["owner"])
            identifier = {"aqua_ring": "aquaring", "ingrain": "ingrain", "leech_seed": "leechseed"}[fact["family"]]
            row["volatiles"][identifier] = fact["state"] == "active"
            if identifier == "leechseed" and fact["state"] == "active": row["leech_source"] = deepcopy(fact["source_slot"])
        for restriction in ("taunt", "encore", "disable"):
            for fact in (state.get(f"current_{restriction}_restrictions") or {}).values():
                owner_row(fact["owner"]).setdefault("restrictions", {})[restriction] = deepcopy(fact)
        for fact in (state.get("substitute_state_context") or {}).get("states", []):
            owner = fact["owner"]
            rows = [p for p in roster[owner["side"]] if p["slot_index"] == owner["slot_index"] and p["pokemon_id"] == owner["pokemon_id"]]
            if len(rows) != 1: raise ValueError("observed_substitute_owner_mismatch")
            if fact["state"] != "unknown":
                rows[0]["substitute"] = {"active": fact["state"] == "known_active", "hp": fact["substitute_hp"]}
        field = {}
        for key, values in (
            ("weather", {None: "", "none": "", "sun": "sunnyday", "rain": "raindance", "sandstorm": "sandstorm", "snow": "snowscape"}),
            ("terrain", {None: "", "none": "", "electric": "electricterrain", "grassy": "grassyterrain", "misty": "mistyterrain", "psychic": "psychicterrain"}),
        ):
            value = state["field"].get(key)
            if key in state["field"] and not is_unknown_battle_fact(value) and (
                    value not in (None, "none") or confirmed_absence(value, state["field"].get(key + "_provenance"), key)):
                field[key] = values[value]
        for key, native in (("trick_room_status", "trickroom"), ("magic_room_status", "magicroom"), ("gravity_status", "gravity")):
            value = state["field"].get(key)
            if value in ("active", "inactive"):
                field.setdefault("pseudo_weather", {})[native] = value == "active"
        if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 16 or not all(isinstance(s, dict) for s in scenarios):
            raise ValueError("invalid_scenarios")
        ids = [s.get("scenario_id") for s in scenarios]
        if not all(isinstance(value, str) and value for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("invalid_scenario_identity")
        request = {**_binding(runtime_snapshot), "operation": _operation, "observed_active": observed,
                   "observed_roster": roster, "observed_sides": sides,
                   "observed_field": field, "scenarios": deepcopy(scenarios)}
        phase = state.get(PHASE_KEY)
        if phase:
            if phase["provenance"]["source_sequence"] != state.get("last_applied_observation_sequence"):
                raise ValueError("stale_observed_decision_phase")
            request["observed_phase"] = deepcopy(phase)
        for scenario in request["scenarios"]:
            if not isinstance(scenario.get("assumptions"), list) or not scenario["assumptions"] or not all(isinstance(v, str) and v for v in scenario["assumptions"]):
                raise ValueError("explicit_scenario_assumptions_required")
        return _run(bridge, request)
    except (ValueError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "invalid_simulation_input"
        return {"status": "rejected", "reason": reason}


def _pokemon_observation(active: dict, slot: int, *, side: str, session_id: str) -> dict:
    if isinstance(slot, str) and slot.isdecimal(): slot = int(slot)
    if type(slot) is not int or slot < 0: raise ValueError("invalid_observed_slot")
    row = {"pokemon_id": active["pokemon_id"], "slot_index": slot, "boosts": {}}
    for key, dest in (("current_hp", "hp"), ("max_hp", "max_hp"), ("fainted", "fainted")):
        value = active.get(key)
        if value is not None and not is_unknown_battle_fact(value): row[dest] = value
    if active.get("known_move_ids"):
        row["known_moves"] = list(active["known_move_ids"])
    for key, dest in (("known_item", "item"), ("current_ability", "ability"),
                      ("current_type", "types"), ("current_level", "level")):
        value = active.get(key)
        if key == "known_item" and confirmed_absence(value, active.get("known_item_provenance"), "item"):
            row[dest] = ""
        elif value is not None and not is_unknown_battle_fact(value):
            row[dest] = deepcopy(value)
    condition = active.get("condition")
    if "condition" in active and not is_unknown_battle_fact(condition) and (
            condition not in (None, "none") or confirmed_absence(condition, active.get("condition_provenance"), "condition")):
        row["condition"] = _CONDITIONS[condition]
    for stat, stage in active.get("stat_stages", {}).items():
        if stat not in _STATS or not _int(stage, -6, 6):
            raise ValueError("invalid_observed_stage")
        row["boosts"][_STATS[stat]] = stage
    row["stats"] = {_STATS[stat]: value["value"] for stat, value in (active.get("current_final_stats") or {}).items()}
    row["move_usability"] = {move: value["status"] == "known_usable" for move, value in (active.get("current_move_usability") or {}).items()}
    response_set = active.get("current_opponent_response_set")
    if response_set:
        row["complete_moves"] = deepcopy(response_set["move_ids"])
        if "move_pp_slots" in response_set: row["pp_slots"] = deepcopy(response_set["move_pp_slots"])
    volatile = {}
    if isinstance(active.get("current_crit_volatiles"), list):
        row["crit_volatiles"] = sorted({"focus-energy" if v == "lansat" else v for v in active["current_crit_volatiles"]})
    healing = active.get("healing_prevented_status")
    if healing in ("active", "inactive"): volatile["healblock"] = healing == "active"
    confusion = active.get("current_confusion")
    if confusion in ("confused", "none"): volatile["confusion"] = confusion == "confused"
    elif confusion is not None and not is_unknown_battle_fact(confusion): raise ValueError("invalid_observed_confusion")
    row["volatiles"] = volatile
    progression = active.get("champions_status_progression")
    if progression:
        owner = {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": active["pokemon_id"]}
        row["status_progression"] = legacy_status_projection(progression, owner=owner, condition=condition,
            condition_provenance=active.get("condition_provenance"))
    toxic = active.get("toxic_progression")
    if isinstance(toxic, dict) and not is_unknown_battle_fact(toxic): row["toxic_next_stage"] = toxic["next_stage"]
    berry = active.get("berry_eaten_state")
    if berry in ("known_true", "known_false"): row["berry_eaten"] = berry == "known_true"
    history = active.get("last_executed_move")
    if history: row["last_executed_move"] = history["move_id"]
    counter = active.get("rage_fist_hit_count")
    if counter and not is_unknown_battle_fact(counter):
        owner = {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": active["pokemon_id"]}
        if counter.get("owner") != owner or not _int(counter.get("count"), 0, 9999): raise ValueError("invalid_observed_rage_fist_counter")
        row["received_hit_count"] = counter["count"]
    return row


def resume_detached_showdown(*, runtime_snapshot: dict, checkpoint: dict, choices: dict, bridge: ShowdownBridge) -> dict:
    """Branch from a native checkpoint only while its source runtime is current."""
    try:
        _state(runtime_snapshot)
        if not isinstance(checkpoint, dict):
            raise ValueError("invalid_checkpoint")
        saved = deepcopy(checkpoint)
        digest = saved.pop("checkpoint_fingerprint", None)
        if not isinstance(digest, str) or digest != _checkpoint_fingerprint(saved):
            raise ValueError("checkpoint_fingerprint_mismatch")
        for key in ("session_id", "source_runtime_fingerprint"):
            if saved.get(key) != _binding(runtime_snapshot)[key]:
                raise ValueError("checkpoint_runtime_mismatch")
        request = {**_binding(runtime_snapshot), "operation": "resume", "scenarios": [{
            "scenario_id": saved["scenario_id"], "assumptions": saved["assumptions"],
            "checkpoint": saved, "choices": deepcopy(choices),
        }]}
        return _run(bridge, request)
    except (ValueError, KeyError, TypeError):
        return {"status": "rejected", "reason": "invalid_or_stale_checkpoint"}


def evaluate_native_status_gate(*, runtime_snapshot: dict, checkpoint: dict, side: str, move: str, bridge: ShowdownBridge) -> dict:
    """Exact native callback enumeration, conditional on one hypothetical root.

    It excludes other action gates, PP, accuracy, targets and ranking authority.
    This is a new representation; the legacy v1 consumer is not changed.
    """
    try:
        _state(runtime_snapshot)
        saved = deepcopy(checkpoint)
        digest = saved.pop("checkpoint_fingerprint", None)
        if (digest != _checkpoint_fingerprint(saved) or side not in {"self", "opponent"} or not isinstance(move, str) or
                any(saved.get(key) != _binding(runtime_snapshot)[key] for key in
                    ("session_id", "source_runtime_fingerprint", "observation_schema_version"))):
            raise ValueError("invalid_status_gate_binding")
        return _run(bridge, {**_binding(runtime_snapshot), "operation": "status_gate", "scenarios": [{
            "scenario_id": saved["scenario_id"], "assumptions": saved["assumptions"], "checkpoint": saved,
            "status_query": {"side": side, "move": move}}]})
    except (ValueError, KeyError, TypeError, AttributeError):
        return {"status": "rejected", "reason": "invalid_or_stale_native_status_gate"}


def evaluate_native_damage_rolls(*, runtime_snapshot: dict, checkpoint: dict, side: str, move: str, critical: bool, bridge: ShowdownBridge) -> dict:
    """Native conditional single-hit rolls, never full action/KO probabilities.

    Fixed crit, explicit hypothetical root. Unsupported move/RNG fails closed.
    No live writeback or legacy exact ledger/ranking substitution.
    """
    try:
        _state(runtime_snapshot)
        saved = deepcopy(checkpoint)
        digest = saved.pop("checkpoint_fingerprint", None)
        if (digest != _checkpoint_fingerprint(saved) or side not in {"self", "opponent"} or not isinstance(move, str) or type(critical) is not bool or
                any(saved.get(key) != _binding(runtime_snapshot)[key] for key in
                    ("session_id", "source_runtime_fingerprint", "observation_schema_version"))):
            raise ValueError("invalid_damage_roll_binding")
        return _run(bridge, {**_binding(runtime_snapshot), "operation": "damage_rolls", "scenarios": [{
            "scenario_id": saved["scenario_id"], "assumptions": saved["assumptions"], "checkpoint": saved,
            "damage_query": {"side": side, "move": move, "critical": critical}}]})
    except (ValueError, KeyError, TypeError, AttributeError):
        return {"status": "rejected", "reason": "invalid_or_stale_native_damage_query"}


def evaluate_detached_showdown(*, runtime_snapshot: dict, scenarios: list[dict], candidates: list[dict], seeds: list[list[int]], bridge: ShowdownBridge) -> dict:
    """Compare explicit action plans on common future seeds, separately per set.

    No opponent weighting, rollout policy, exact ledger, or ranking is inferred.
    A choice entry is one native decision boundary, which may be a forced switch
    rather than a whole turn. An illegal plan is rejected for all its samples.
    """
    if not isinstance(scenarios, list) or not all(isinstance(s, dict) for s in scenarios):
        return {"status": "rejected", "reason": "invalid_scenarios"}
    modeled = deepcopy(scenarios)
    for scenario in modeled:
        scenario["evaluation"] = {"candidates": deepcopy(candidates), "seeds": deepcopy(seeds)}
    return simulate_detached_showdown(runtime_snapshot=runtime_snapshot, scenarios=modeled, bridge=bridge)


def reconcile_detached_showdown(*, runtime_snapshot: dict, checkpoint: dict, scenario: dict, observed_history: list[dict], bridge: ShowdownBridge) -> dict:
    """Condition an old hypothetical native root on a newer actual observation.

    ``observed_history`` is an explicit modeled sequence since the checkpoint,
    including any replacement choices. It is never applied to the runtime.
    The old fingerprint is retained as lineage, while the new root binds to the
    current capture. Known unsupported mechanics still reject the request.
    """
    try:
        _state(runtime_snapshot)
        saved = deepcopy(checkpoint)
        digest = saved.pop("checkpoint_fingerprint", None)
        if (digest != _checkpoint_fingerprint(saved) or saved.get("session_id") != runtime_snapshot["session_id"] or
                saved.get("scenario_id") != scenario.get("scenario_id")):
            raise ValueError("checkpoint_binding_mismatch")
        model = {"teams": scenario["teams"], "preview": scenario["preview"], "slot_mapping": scenario.get("slot_mapping", {
            "self": list(range(6)), "opponent": list(range(6))}), "initial_conditioning": scenario.get("initial_conditioning", [])}
        if saved.get("model_definition") != model or saved.get("assumptions") != scenario.get("assumptions"):
            raise ValueError("checkpoint_model_binding_mismatch")
        modeled = {**deepcopy(scenario), "checkpoint": saved, "history": deepcopy(observed_history)}
        result = simulate_detached_showdown(runtime_snapshot=runtime_snapshot, scenarios=[modeled], bridge=bridge, _operation="reconcile")
        result["reconciled_from_runtime_fingerprint"] = saved["source_runtime_fingerprint"]
        return result
    except (ValueError, KeyError, TypeError, AttributeError):
        return {"status": "rejected", "reason": "invalid_or_foreign_reconciliation_checkpoint"}


def _run(bridge: ShowdownBridge, request: dict) -> dict:
    try:
        response = bridge.run(request)
    except ShowdownBridgeError as exc:
        return {"status": "unavailable", "reason": str(exc)}
    for scenario in response["scenarios"]:
        for key in ("root_checkpoint", "checkpoint"):
            if key in scenario:
                scenario[key]["checkpoint_fingerprint"] = _checkpoint_fingerprint(scenario[key])
    response["status"] = "simulated" if any(s.get("status") == "simulated" for s in response["scenarios"]) else "rejected"
    response["limitations"] = list(LIMITATIONS)
    return response


def _state(snapshot: Any) -> dict:
    if not isinstance(snapshot, dict) or snapshot.get("status") != "runtime_snapshot_ready":
        raise ValueError("invalid_runtime_snapshot")
    state = snapshot.get("state")
    if (not isinstance(state, dict) or state.get("state_version") != STATE_MODEL_VERSION or
        not isinstance(snapshot.get("session_id"), str) or not snapshot["session_id"] or
        state.get("session_id") != snapshot["session_id"] or
        not validate_battle_state_unknown_markers(state) or
        snapshot.get("state_fingerprint") != state_fingerprint(state)):
        raise ValueError("invalid_runtime_snapshot_binding")
    battle_format = state["field"].get("battle_format")
    if battle_format != "singles":
        raise ValueError("observed_singles_format_required")
    return deepcopy(state)


def _binding(snapshot: dict) -> dict:
    return {"schema_version": SCHEMA_VERSION, "format_id": FORMAT_ID,
            "observation_schema_version": OBSERVATION_SCHEMA,
            "session_id": snapshot["session_id"], "source_runtime_fingerprint": snapshot["state_fingerprint"]}


def _int(value: Any, minimum: int, maximum: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum


def _checkpoint_fingerprint(checkpoint: dict) -> str:
    """Hash all native fields; reducer fingerprint exclusions do not apply here."""
    encoded = json.dumps(checkpoint, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _unmapped_observations(state: dict) -> list[str]:
    """Fail closed on concrete mechanics for which this slice has no adapter."""
    paths = []
    root_keys = {"state_version", "session_id", "self_side", "opponent_side", "field",
                 "last_applied_observation_sequence", "last_applied_batch_fingerprint",
                 "source_replay_policy_version", "last_commit_provenance", "substitute_state_context"}
    root_keys.update({"switch_hazard_context", "current_persistent_effect_context",
        "current_taunt_restrictions", "current_encore_restrictions", "current_disable_restrictions"})
    root_keys.add(PHASE_KEY)
    active_keys = {"pokemon_id", "current_hp", "max_hp", "fainted", "current_type", "current_ability",
                   "current_level", "current_final_stats", "condition", "known_item", "known_move_ids", "stat_stages",
                   "current_move_usability", "champions_status_progression", "toxic_progression", "current_crit_volatiles",
                   "healing_prevented_status", "current_confusion"}
    active_keys.add("current_opponent_response_set")
    active_keys.update({"berry_eaten_state", "last_executed_move", "rage_fist_hit_count"})
    def scan(container, supported, prefix):
        for key, value in container.items():
            if key not in supported and not key.endswith("_provenance") and value is not None and not is_unknown_battle_fact(value):
                paths.append(f"{prefix}{key}")
    scan(state, root_keys, "")
    scan(state["field"], {"battle_format", "weather", "terrain", "trick_room_status", "magic_room_status", "gravity_status"}, "field.")
    for side in ("self", "opponent"):
        container = state[f"{side}_side"]
        scan(container, {"active_slot_index", "pokemon", "side_conditions", "tailwind_status", "switch_permission_context"}, f"{side}_side.")
        active = container["pokemon"].get(container["active_slot_index"], container["pokemon"].get(str(container["active_slot_index"])))
        scan(active, active_keys, f"{side}_side.active.")
        for slot, pokemon in container["pokemon"].items():
            if str(slot) == str(container["active_slot_index"]):
                continue
            scan(pokemon, active_keys, f"{side}_side.pokemon.{slot}.")
    return sorted(paths)
