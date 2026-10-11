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
from llm.advisor_reducer_state_model import (
    STATE_MODEL_VERSION, is_unknown_battle_fact, state_fingerprint,
    validate_battle_state_unknown_markers,
)

_STATS = {"attack": "atk", "defense": "def", "special-attack": "spa",
          "special-defense": "spd", "speed": "spe", "accuracy": "accuracy", "evasion": "evasion"}
_CONDITIONS = {None: "", "none": "", "burn": "brn", "poison": "psn", "toxic": "tox",
               "paralysis": "par", "sleep": "slp", "freeze": "frz"}
LIMITATIONS = [
    "partial_observation_reconstruction_only_active_hp_and_known_stages_overlaid",
    "teams_unobserved_state_counters_pp_and_history_are_explicit_hypotheses",
    "unmapped_known_runtime_mechanics_are_rejected",
    "seeded_samples_are_not_exact_probabilities",
    "native_requests_may_pause_for_switch_or_pivot_before_turn_advances",
    "no_live_state_or_ranking_writeback",
]


def simulate_detached_showdown(*, runtime_snapshot: dict, scenarios: list[dict], bridge: ShowdownBridge) -> dict:
    """Simulate one explicit choice pair per scenario from a partial observed root."""
    try:
        state = _state(runtime_snapshot)
        unmapped = _unmapped_observations(state)
        if unmapped:
            return {"status": "rejected", "reason": "unmapped_runtime_mechanics", "fields": unmapped}
        observed = {}
        for side in ("self", "opponent"):
            container = state[f"{side}_side"]
            active = container["pokemon"][container["active_slot_index"]]
            hp, maximum = active["current_hp"], active["max_hp"]
            if not (_int(hp, 1, 9999) and _int(maximum, hp, 9999) and active.get("fainted") is False):
                raise ValueError("observed_active_hp_required")
            row = {"pokemon_id": active["pokemon_id"], "hp": hp, "max_hp": maximum, "boosts": {}}
            if active.get("known_move_ids"):
                row["known_moves"] = list(active["known_move_ids"])
            for key, dest in (("known_item", "item"), ("current_ability", "ability"),
                              ("current_type", "types"), ("current_level", "level")):
                value = active.get(key)
                if key in active and key == "known_item" and value is None:
                    row[dest] = ""
                elif value is not None and not is_unknown_battle_fact(value):
                    row[dest] = deepcopy(value)
            condition = active.get("condition")
            if "condition" in active and not is_unknown_battle_fact(condition):
                row["condition"] = _CONDITIONS[condition]
            for stat, stage in active.get("stat_stages", {}).items():
                if stat not in _STATS or not _int(stage, -6, 6):
                    raise ValueError("invalid_observed_stage")
                row["boosts"][_STATS[stat]] = stage
            # A final combat stat cannot safely be reverse-engineered to a set.
            if active.get("current_final_stats"):
                raise ValueError("observed_final_stats_adapter_required")
            observed[side] = row
        field = {}
        for key, values in (
            ("weather", {None: "", "none": "", "sun": "sunnyday", "rain": "raindance", "sandstorm": "sandstorm", "snow": "snowscape"}),
            ("terrain", {None: "", "none": "", "electric": "electricterrain", "grassy": "grassyterrain", "misty": "mistyterrain", "psychic": "psychicterrain"}),
        ):
            value = state["field"].get(key)
            if key in state["field"] and not is_unknown_battle_fact(value):
                field[key] = values[value]
        if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 16 or not all(isinstance(s, dict) for s in scenarios):
            raise ValueError("invalid_scenarios")
        ids = [s.get("scenario_id") for s in scenarios]
        if not all(isinstance(value, str) and value for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("invalid_scenario_identity")
        request = {**_binding(runtime_snapshot), "operation": "simulate", "observed_active": observed,
                   "observed_field": field, "scenarios": deepcopy(scenarios)}
        for scenario in request["scenarios"]:
            if not isinstance(scenario.get("assumptions"), list) or not scenario["assumptions"] or not all(isinstance(v, str) and v for v in scenario["assumptions"]):
                raise ValueError("explicit_scenario_assumptions_required")
        return _run(bridge, request)
    except (ValueError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "invalid_simulation_input"
        return {"status": "rejected", "reason": reason}


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
                 "source_replay_policy_version", "last_commit_provenance"}
    active_keys = {"pokemon_id", "current_hp", "max_hp", "fainted", "current_type", "current_ability",
                   "current_level", "current_final_stats", "condition", "known_item", "known_move_ids", "stat_stages"}
    def scan(container, supported, prefix):
        for key, value in container.items():
            if key not in supported and not key.endswith("_provenance") and value is not None and not is_unknown_battle_fact(value):
                paths.append(f"{prefix}{key}")
    scan(state, root_keys, "")
    scan(state["field"], {"battle_format", "weather", "terrain"}, "field.")
    for side in ("self", "opponent"):
        container = state[f"{side}_side"]
        scan(container, {"active_slot_index", "pokemon"}, f"{side}_side.")
        active = container["pokemon"][container["active_slot_index"]]
        scan(active, active_keys, f"{side}_side.active.")
        for slot, pokemon in container["pokemon"].items():
            if slot == container["active_slot_index"]:
                continue
            # This slice does not reconcile any observed bench mechanics.
            for key, value in pokemon.items():
                if (key != "pokemon_id" and not key.endswith("_provenance") and
                    not is_unknown_battle_fact(value) and
                    (value is not None or key == "known_item") and
                    not (key == "current_final_stats" and value == {})):
                    paths.append(f"{side}_side.pokemon.{slot}.{key}")
    return sorted(paths)
