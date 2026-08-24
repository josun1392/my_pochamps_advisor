"""Runtime-D0-bound selection-only projection for detached strategy.

The recommendation cycle remains the owner of structured move and switch
selectability.  This module merely freezes those facts with the runtime D0
capture that existed when the cycle was prepared; it never derives legality
from UI text, roster membership, or execution-shaped payloads.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA = "runtime-d0-bound-selection-projection-v1"
MOVE_METADATA_SCHEMA = "runtime-d0-selectable-move-metadata-authority-v1"
CAPTURE_SCHEMA = "runtime-d0-selection-capture-v1"
_SELECTIONS = frozenset({"selectable", "not_selectable", "selection_unknown"})


def build_runtime_d0_selection_capture(*, strategy_d0: Mapping[str, Any]) -> dict[str, Any]:
    """Create the private capture token passed while a selection cycle is built."""
    if not _valid_d0_binding(strategy_d0):
        return _rejected("invalid_strategy_d0")
    owner = strategy_d0["decision_owner"]
    return {
        "schema_version": CAPTURE_SCHEMA,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "decision_owner": deepcopy(dict(owner)),
        "active_owner": deepcopy(dict(owner)),
    }


def freeze_runtime_d0_bound_selection_projection(*, strategy_d0: Mapping[str, Any], prepared_cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze one prepared structured selection cycle for the exact runtime D0.

    ``prepared_cycle`` must contain a capture token supplied while it was
    created.  Consequently an A-cycle cannot be attached post-hoc to D0 B.
    The returned value is directly consumable by
    ``freeze_runtime_strategy_selection_authority``.
    """
    if not _valid_d0_binding(strategy_d0) or not isinstance(prepared_cycle, Mapping):
        return _rejected("invalid_strategy_d0_or_prepared_cycle")
    if prepared_cycle.get("status") != "ready":
        return _rejected("selection_cycle_not_ready")
    capture = prepared_cycle.get("_runtime_d0_selection_capture")
    if capture != build_runtime_d0_selection_capture(strategy_d0=strategy_d0):
        return _rejected("selection_cycle_runtime_d0_mismatch")
    if not _capture_matches_turn_snapshot(capture=capture, turn_snapshot=prepared_cycle.get("_combined_action_turn_snapshot")):
        return _rejected("selection_cycle_active_identity_mismatch")
    try:
        request = _mapping(prepared_cycle.get("recommendation_request"))
        evidence = _mapping(prepared_cycle.get("evidence_bundle"))
        comparisons = request.get("candidate_comparisons")
        moves = _freeze_move_selection(comparisons)
        move_metadata_authorities = _freeze_selectable_move_metadata_authorities(
            rows=comparisons, candidates=evidence.get("candidates"), strategy_d0=strategy_d0,
        )
        switches = _freeze_switch_selection(evidence.get("switch_candidates"))
    except ValueError as error:
        return _rejected(str(error))
    return {
        "status": "resolved",
        "schema_version": SCHEMA,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "active_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "moves": moves,
        "move_metadata_authorities": move_metadata_authorities,
        "switches": switches,
        "selection_completeness": "partial" if any(row["selection"] == "selection_unknown" for row in [*moves, *switches]) else "complete",
        "provenance": "prepared_recommendation_selection_cycle_bound_to_runtime_d0_v1",
    }


def _freeze_move_selection(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise ValueError("invalid_structured_move_selection")
    result: list[dict[str, str]] = []
    identities: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("invalid_structured_move_selection")
        move = row.get("move")
        eligibility = row.get("eligibility")
        if not isinstance(move, str) or not move or move in identities:
            raise ValueError("duplicate_or_invalid_move_selection_identity")
        if eligibility in {"eligible", "eligible_with_warnings"}:
            selection = "selectable"
        elif eligibility == "not_selectable":
            selection = "not_selectable"
        elif row.get("selection") == "selection_unknown":
            selection = "selection_unknown"
        else:
            raise ValueError("unknown_move_selection_authority")
        identities.add(move)
        result.append({"move_id": move, "selection": selection})
    return sorted(result, key=lambda row: row["move_id"])


def _freeze_selectable_move_metadata_authorities(
    *, rows: Any, candidates: Any, strategy_d0: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Bind repository-normalized candidate metadata without promoting UI data.

    The prepared-cycle evidence is the only source accepted here.  A missing
    internal canonical payload remains candidate-local ``incomplete`` rather
    than changing selection legality or being backfilled from the UI bridge.
    """
    if not isinstance(rows, list):
        raise ValueError("invalid_structured_move_selection")
    evidence_by_key: dict[tuple[int, str], Mapping[str, Any]] = {}
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            slot, move = candidate.get("slot_index"), candidate.get("move")
            if isinstance(slot, int) and not isinstance(slot, bool) and isinstance(move, str) and move:
                key = (slot, move)
                if key in evidence_by_key:
                    raise ValueError("duplicate_canonical_move_metadata_identity")
                evidence_by_key[key] = candidate
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("invalid_structured_move_selection")
        move, slot = row.get("move"), row.get("slot_index")
        if not isinstance(move, str) or not move:
            raise ValueError("duplicate_or_invalid_move_selection_identity")
        candidate = evidence_by_key.get((slot, move)) if isinstance(slot, int) and not isinstance(slot, bool) else None
        result[move] = _move_metadata_authority(move=move, candidate=candidate, strategy_d0=strategy_d0)
    return dict(sorted(result.items()))


def _move_metadata_authority(*, move: str, candidate: Mapping[str, Any] | None, strategy_d0: Mapping[str, Any]) -> dict[str, Any]:
    base = {
        "schema_version": MOVE_METADATA_SCHEMA,
        "candidate_id": f"attack:{move}", "move_id": move,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "active_attacker": deepcopy(dict(strategy_d0["decision_owner"])),
        "provenance": "prepared_cycle_repository_normalized_move_metadata_bound_to_runtime_d0_v1",
    }
    metadata = candidate.get("canonical_move_metadata") if isinstance(candidate, Mapping) else None
    if not isinstance(metadata, Mapping):
        return {"status": "incomplete", **base, "reason": "canonical_move_metadata_missing"}
    normalized = deepcopy(dict(metadata))
    if normalized.get("move_id") != move:
        return {"status": "rejected", **base, "reason": "canonical_move_metadata_move_id_conflict"}
    category, power, move_type = normalized.get("category"), normalized.get("power"), normalized.get("type")
    if category not in {"physical", "special", "status"}:
        return {"status": "unsupported", **base, "reason": "canonical_move_category_unsupported"}
    if not isinstance(move_type, str) or not move_type:
        return {"status": "incomplete", **base, "reason": "canonical_move_type_missing"}
    if category in {"physical", "special"} and (not isinstance(power, int) or isinstance(power, bool) or power < 1):
        return {"status": "incomplete", **base, "reason": "canonical_move_power_missing"}
    always_hit, accuracy = normalized.get("always_hit"), normalized.get("accuracy")
    if always_hit is not True and (not isinstance(accuracy, int) or isinstance(accuracy, bool) or not 1 <= accuracy <= 100):
        return {"status": "incomplete", **base, "reason": "canonical_move_accuracy_missing"}
    return {"status": "resolved", **base, "metadata": normalized}


def _freeze_switch_selection(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise ValueError("invalid_structured_switch_selection")
    result: list[dict[str, str]] = []
    identities: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("invalid_structured_switch_selection")
        pokemon_id = row.get("target_pokemon_id")
        if not isinstance(pokemon_id, str) or not pokemon_id or pokemon_id in identities:
            raise ValueError("duplicate_or_invalid_switch_selection_identity")
        if row.get("selectable") is True:
            selection = "selectable"
        elif row.get("availability_supportability") == "insufficient_context" or row.get("legality_supportability") == "insufficient_context":
            selection = "selection_unknown"
        elif row.get("selectable") is False and row.get("availability_supportability") == "complete":
            selection = "not_selectable"
        else:
            raise ValueError("unknown_switch_selection_authority")
        identities.add(pokemon_id)
        result.append({"pokemon_id": pokemon_id, "selection": selection})
    return sorted(result, key=lambda row: row["pokemon_id"])


def _capture_matches_turn_snapshot(*, capture: Any, turn_snapshot: Any) -> bool:
    if not isinstance(capture, Mapping) or not isinstance(turn_snapshot, Mapping):
        return False
    owner = capture.get("active_owner")
    current = turn_snapshot.get("current_state")
    battle_state = turn_snapshot.get("battle_state")
    active = battle_state.get("active_player") if isinstance(battle_state, Mapping) else None
    if not isinstance(owner, Mapping) or not isinstance(active, Mapping):
        return False
    return (
        (not isinstance(current, Mapping) or current.get("current_state_session_id") == capture.get("session_id"))
        and owner.get("side") == "self"
        and active.get("slot_index") == owner.get("slot_index")
        and active.get("species_id") == owner.get("pokemon_id")
    )


def _valid_d0_binding(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "deterministic-runtime-strategy-d0-v1":
        return False
    owner = value.get("decision_owner")
    return (
        isinstance(owner, Mapping) and value.get("session_id") == owner.get("session_id")
        and isinstance(value.get("source_runtime_fingerprint"), str) and bool(value["source_runtime_fingerprint"])
        and isinstance(owner.get("side"), str) and isinstance(owner.get("slot_index"), int)
        and isinstance(owner.get("pokemon_id"), str) and bool(owner["pokemon_id"])
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_prepared_selection_sources")
    return value


def _rejected(reason: str) -> dict[str, str]:
    return {"status": "rejected", "reason": reason}
