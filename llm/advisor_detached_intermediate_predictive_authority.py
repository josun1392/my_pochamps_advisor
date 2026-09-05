"""Actor-neutral, hypothetical authority view for one second selected move.

This adapter owns no mechanics.  It converts an exact detached intermediate
state into a separately tagged D0-shaped input accepted by the existing strict
predictive builders.  The nested view is intentionally never returned as
current runtime authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0, runtime_strategy_d0_freshness


SCHEMA_VERSION = "detached-intermediate-predictive-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_STAGES = ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")


def freeze_detached_intermediate_predictive_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    intermediate_state: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any],
    move_metadata_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a strictly hypothetical, role-explicit predictive authority.

    Only exact HP and stage overlays are installed into the nested predictive
    view.  A changed major condition remains represented here but deliberately
    prevents a builder from silently rereading the old current condition.
    """
    base = _base(strategy_d0)
    metadata = _metadata_authority(move_metadata_authority, base)
    if base is None or not _owner(actor) or not _owner(target) or metadata is None:
        return _result("rejected", "invalid_detached_intermediate_predictive_request", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    parsed = _intermediate(intermediate_state, strategy_d0, actor, target)
    if isinstance(parsed, str):
        return _result("rejected", parsed, base)
    if parsed["actor"]["fainted"]:
        return _result("incomplete", "intermediate_predictive_actor_fainted", {**base, **parsed["binding"]})
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not isinstance(state, Mapping):
        return _result("rejected", "runtime_snapshot_state_missing", {**base, **parsed["binding"]})
    synthetic = deepcopy(dict(state))
    for owner, values in ((actor, parsed["actor"]), (target, parsed["target"])):
        raw = _pokemon(synthetic, owner)
        if raw is None:
            return _result("rejected", "intermediate_predictive_owner_identity_mismatch", {**base, **parsed["binding"]})
        raw["current_hp"] = values["hp"]
        raw["fainted"] = values["fainted"]
        raw["stat_stages"] = deepcopy(values["stages"])
        if values["item"].get("source") == "exact_terminal_leaf_focus_sash_consumption":
            raw["known_item"] = None
            raw["known_item_provenance"] = {
                "event_kind": "item_consumption_observed",
                "turn_number": 1,
                "trust": "detached_hypothetical",
                "source": "exact_terminal_leaf_focus_sash_consumption",
            }
        raw["detached_intermediate_predictive_authority"] = True
    # A status change has exact hypothetical provenance but cannot be written
    # into a runtime-shaped snapshot as if it were an observed condition.
    # Later status-aware second-action support must consume this field directly.
    condition_changed = any(parsed[name]["condition_changed"] for name in ("actor", "target"))
    synthetic_snapshot = {
        "status": "runtime_snapshot_ready", "session_id": strategy_d0["session_id"],
        "state": synthetic, "state_fingerprint": state_fingerprint(synthetic),
    }
    predictive_d0 = freeze_runtime_strategy_d0(runtime_snapshot=synthetic_snapshot, decision_owner=actor)
    if predictive_d0.get("status") != "resolved":
        return _result("incomplete", predictive_d0.get("reason", "intermediate_predictive_d0_unavailable"), {**base, **parsed["binding"]})
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "hypothetical": True, "horizon": "immediate_action_pair",
        **base, **parsed["binding"], "intermediate_state_id": parsed["intermediate_state_id"],
        "source_first_action_leaf_id": parsed["source_leaf_id"],
        "predictive_actor": deepcopy(dict(actor)), "predictive_target": deepcopy(dict(target)),
        "move_id": metadata["move_id"], "move_metadata": deepcopy(metadata),
        "intermediate_overrides": {
            "actor": deepcopy(parsed["actor"]), "target": deepcopy(parsed["target"]),
            "condition_override_requires_direct_consumer": condition_changed,
        },
        "unchanged_authority": deepcopy(intermediate_state.get("unchanged_authority", {})),
        "predictive_runtime_snapshot": synthetic_snapshot,
        "predictive_strategy_d0": predictive_d0,
        "provenance": "exact_intermediate_state_to_actor_neutral_predictive_authority_v1",
    }


def detached_intermediate_builder_inputs(authority: Mapping[str, Any]) -> dict[str, Any]:
    """Return the only builder inputs exposed by this hypothetical owner."""
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != SCHEMA_VERSION or authority.get("hypothetical") is not True:
        return {"status": "rejected", "reason": "invalid_detached_intermediate_predictive_authority"}
    if authority.get("intermediate_overrides", {}).get("condition_override_requires_direct_consumer") is True:
        return {"status": "incomplete", "reason": "changed_intermediate_condition_requires_status_aware_predictive_adapter"}
    d0, snapshot = authority.get("predictive_strategy_d0"), authority.get("predictive_runtime_snapshot")
    actor, target = authority.get("predictive_actor"), authority.get("predictive_target")
    if not isinstance(d0, Mapping) or not isinstance(snapshot, Mapping) or not _owner(actor) or not _owner(target):
        return {"status": "rejected", "reason": "detached_intermediate_builder_view_invalid"}
    return {"status": "resolved", "strategy_d0": deepcopy(dict(d0)), "runtime_snapshot": deepcopy(dict(snapshot)), "attacker": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "move_metadata": deepcopy(dict(authority["move_metadata"]),), "provenance": "detached_intermediate_predictive_authority_builder_view_v1"}


def _intermediate(value: Any, d0: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "detached-predictive-intermediate-state-v1":
        return "invalid_detached_intermediate_state"
    expected = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        return "detached_intermediate_state_binding_mismatch"
    active = value.get("active")
    if not isinstance(active, Mapping) or active.get(actor["side"], {}).get("owner") != dict(actor) or active.get(target["side"], {}).get("owner") != dict(target) or actor["side"] == target["side"]:
        return "detached_intermediate_role_mapping_mismatch"
    def participant(owner: Mapping[str, Any]) -> dict[str, Any] | str:
        row = active[owner["side"]]
        hp = row.get("hypothetical_hp", {})
        fainted = row.get("hypothetical_fainted", {})
        stages = row.get("hypothetical_stages")
        if hp.get("status") != "known" or not isinstance(hp.get("value"), int) or hp["value"] < 0 or fainted.get("status") != "known" or fainted.get("value") is not (hp["value"] == 0): return "intermediate_exact_hp_or_faint_missing"
        if not isinstance(stages, Mapping) or any(stages.get(stat, {}).get("status") != "known" or not isinstance(stages[stat].get("value"), int) or not -6 <= stages[stat]["value"] <= 6 for stat in _STAGES): return "intermediate_exact_stage_missing"
        condition = row.get("hypothetical_condition")
        if not isinstance(condition, Mapping): condition = {"status": "unknown", "reason": "intermediate_condition_missing"}
        item = row.get("hypothetical_item")
        if not isinstance(item, Mapping): item = {"status": "unknown", "reason": "intermediate_item_missing"}
        return {"hp": hp["value"], "fainted": fainted["value"], "stages": {stat: stages[stat]["value"] for stat in _STAGES}, "condition": deepcopy(dict(condition)), "item": deepcopy(dict(item)), "condition_changed": condition.get("source") in {"exact_terminal_leaf_condition_effect", "exact_terminal_leaf_condition_removal"}}
    parsed_actor, parsed_target = participant(actor), participant(target)
    if isinstance(parsed_actor, str) or isinstance(parsed_target, str): return parsed_actor if isinstance(parsed_actor, str) else parsed_target
    first = value.get("first_action")
    if not isinstance(first, Mapping) or not isinstance(first.get("leaf_id"), str): return "intermediate_source_leaf_missing"
    return {"binding": {}, "intermediate_state_id": f"intermediate:{first['candidate_id']}:{first['leaf_id']}", "source_leaf_id": first["leaf_id"], "actor": parsed_actor, "target": parsed_target}


def _base(d0: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(d0.get("decision_owner")):
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"]))}


def _pokemon(state: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any] | None:
    side = state.get(f"{owner['side']}_side"); roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return value if isinstance(value, dict) and value.get("pokemon_id") == owner["pokemon_id"] else None


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _move(value: Any) -> bool:
    if not isinstance(value, Mapping) or not isinstance(value.get("move_id"), str) or not value["move_id"] or value.get("category") not in {"physical", "special"} or not isinstance(value.get("type"), str) or not value["type"]: return False
    if value.get("move_id") == "endeavor": return value.get("type") == "normal" and value.get("category") == "physical" and value.get("accuracy") == 100
    if value.get("move_id") == "final-gambit": return value.get("type") == "fighting" and value.get("category") == "special" and value.get("accuracy") == 100
    if value.get("move_id") == "counter": return value.get("type") == "fighting" and value.get("category") == "physical" and value.get("accuracy") == 100 and value.get("priority") == -5
    if value.get("move_id") == "mirror-coat": return value.get("type") == "psychic" and value.get("category") == "special" and value.get("accuracy") == 100 and value.get("priority") == -5
    return isinstance(value.get("power"), int) and not isinstance(value.get("power"), bool) and value["power"] > 0


def _metadata_authority(value: Any, base: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if base is None or not isinstance(value, Mapping) or value.get("status") != "resolved": return None
    metadata = value.get("metadata")
    if not _move(metadata): return None
    expected = {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": base["decision_owner"], "move_id": metadata["move_id"]}
    if any(value.get(key) != expected_value for key, expected_value in expected.items()): return None
    return deepcopy(dict(metadata))


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
