"""Read-only mechanics evaluation for frozen opponent action candidates."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_q12_snapshot_adapter import invoke_existing_q12_from_snapshot
from llm.narrow_action_order import evaluate_action_order
from llm.q12_ko_interpretation import evaluate_q12_ko_interpretation
from llm.q12_ko_probability import evaluate_exact_q12_ko_probability


def evaluate_opponent_action_candidates(candidate_set: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate each frozen action independently; never aggregate a threat."""
    candidates = candidate_set.get("opponent_action_candidates") if isinstance(candidate_set, Mapping) else None
    rows = [evaluate_opponent_action_candidate(candidate) for candidate in candidates] if isinstance(candidates, list) else []
    complete = sum(row["mechanical_evaluation_status"] == "complete" for row in rows)
    insufficient = sum(row["mechanical_evaluation_status"] == "insufficient_context" for row in rows)
    unsupported = sum(row["mechanical_evaluation_status"] == "unsupported_mechanic" for row in rows)
    blocked = sum(row.get("move_success", {}).get("status") == "blocked" for row in rows if isinstance(row.get("move_success"), Mapping))
    return {
        **deepcopy(dict(candidate_set)), "opponent_action_evaluations": rows,
        "evaluated_complete_count": complete, "insufficient_count": insufficient,
        "unsupported_count": unsupported, "blocked_count": blocked,
        "mechanical_evaluation_complete": bool(rows) and complete == len(rows),
    }


def evaluate_opponent_action_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Consume only the candidate's frozen side-reversal snapshot."""
    result = {key: deepcopy(candidate.get(key)) for key in ("candidate_id", "role", "session_id", "pokemon_identity", "move_id", "moveset_state", "candidate_set_complete", "move_identity_authority", "metadata_supportability")}
    snapshot = candidate.get("mechanics_snapshot")
    metadata = candidate.get("move_metadata")
    if candidate.get("metadata_supportability") != "complete" or not isinstance(snapshot, Mapping) or not isinstance(metadata, Mapping):
        return {**result, "move_success": {"status": "not_applicable", "reason": "metadata_supportability"}, "action_order": {"status": "not_applicable", "reason": "metadata_supportability"}, "incoming_damage": {"status": "unsupported_mechanic", "reason": "move_metadata"}, "mechanical_evaluation_status": "unsupported_mechanic"}
    current = _mapping(_mapping(snapshot.get("battle_context")).get("current_state"))
    reversed_current = _side_reversed_current_state(current)
    action_order = _priority_probe(metadata, current)
    from llm.advisor_candidate_contract import _priority_block_gate
    move_success = _priority_block_gate(reversed_current, metadata, action_order) or {"status": "allowed", "move_success_status": "allowed"}
    result.update(action_order=action_order, move_success=move_success)
    if move_success.get("status") == "blocked":
        return {**result, "incoming_damage": {"status": "not_applicable", "reason": "move_success_blocked"}, "mechanical_evaluation_status": "complete"}
    if move_success.get("status") in {"insufficient_context", "unsupported_mechanic"}:
        return {**result, "incoming_damage": {"status": move_success["status"], "reason": "move_success"}, "mechanical_evaluation_status": move_success["status"]}
    if metadata.get("category") == "status":
        return {**result, "incoming_damage": {"status": "not_applicable", "reason": "status_move"}, "mechanical_evaluation_status": "complete"}
    damage_input = {"attacker": deepcopy(snapshot.get("attacker")), "defender": deepcopy(snapshot.get("defender")), "move": deepcopy(snapshot.get("move")), "battle_context": {"current_state": reversed_current}}
    provenance = _mapping(_mapping(snapshot.get("battle_context")).get("stat_provenance"))
    level = _opponent_level(current, _mapping(snapshot.get("attacker")))
    q12 = invoke_existing_q12_from_snapshot(damage_input, stat_provenance=provenance, trusted_level=level)
    mechanics = _formula_mechanics(q12)
    if isinstance(reversed_current.get("direct_mechanics_context"), Mapping):
        direct = evaluate_direct_damage_mechanics(damage_input, stat_provenance=provenance, trusted_level=level)
        mechanics = direct
    hp_context = current.get("current_hp_context")
    ko = evaluate_q12_ko_interpretation(mechanics_result=mechanics, current_hp_context=hp_context, defender_side="self")
    if ko is not None: mechanics = {**mechanics, "ko_interpretation": ko}
    probability = evaluate_exact_q12_ko_probability(mechanics_result=mechanics, current_hp_context=hp_context, defender_side="self", ko_interpretation=ko)
    if probability is not None: mechanics = {**mechanics, "ko_probability": probability}
    state = mechanics.get("status")
    evaluation = "complete" if state == "known" else state if state in {"insufficient_context", "unsupported_mechanic"} else "insufficient_context"
    return {**result, "incoming_q12": q12, "incoming_damage": mechanics, "mechanical_evaluation_status": evaluation}


def _formula_mechanics(q12: Mapping[str, Any]) -> dict[str, Any]:
    if q12.get("status") != "resolved":
        return {"status": "unsupported_mechanic" if q12.get("status") == "unsupported_mechanic" else "insufficient_context", "reason": q12.get("limitations", ["q12_unavailable"])[0]}
    rolls = q12.get("damage_rolls")
    if not isinstance(rolls, list) or not rolls:
        return {"status": "unsupported_mechanic", "reason": "exact_damage_rolls"}
    return {"status": "known", "damage_model": "single_hit_formula", "damage_range": {"minimum": q12["min_damage"], "maximum": q12["max_damage"]}, "exact_damage_rolls": tuple(rolls), "type_damage_evidence": deepcopy(q12.get("type_damage_evidence"))}


def _priority_probe(metadata: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    action = {key: metadata.get(key) for key in ("move_id", "priority", "category", "type")}
    action["triage_healing"] = "eligible" if metadata.get("healing", 0) or metadata.get("drain", 0) else "non_eligible"
    ability = _known_ability(current, "opponent")
    probe = evaluate_action_order(self_action=action, opponent_action=action, self_final_speed=None, opponent_final_speed=None, self_priority_ability=ability)
    return {"status": probe.get("status"), "base_priority": probe.get("self_base_priority"), "effective_priority": probe.get("self_priority"), "priority_authority": "opponent_frozen_authority", "comparison": "not_performed", **{key: value for key, value in probe.items() if key in {"self_prankster_applied", "self_gale_wings_applied", "self_triage_applied", "missing_inputs", "unsupported_reason"}}}


def _known_ability(current: Mapping[str, Any], side: str) -> str:
    context = current.get("ability_context"); entries = context.get("current_abilities") if isinstance(context, Mapping) else None
    matches = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("side") == side] if isinstance(entries, list) else []
    return matches[0].get("ability", "omitted") if len(matches) == 1 and isinstance(matches[0].get("ability"), str) else "omitted"


def _opponent_level(current: Mapping[str, Any], attacker: Mapping[str, Any]) -> int | None:
    context = current.get("trusted_level_context"); entries = context.get("current_levels") if isinstance(context, Mapping) else None
    for entry in entries if isinstance(entries, list) else []:
        provenance = entry.get("provenance") if isinstance(entry, Mapping) else None
        if isinstance(entry, Mapping) and entry.get("side") == "opponent" and isinstance(entry.get("value"), int) and 1 <= entry["value"] <= 100 and isinstance(provenance, Mapping) and provenance.get("pokemon_id") == attacker.get("species_id") and provenance.get("slot_index") == attacker.get("slot_index"):
            return entry["value"]
    return None


def _side_reversed_current_state(current: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(current))
    def swap(item: Any) -> Any:
        if isinstance(item, list): return [swap(value) for value in item]
        if not isinstance(item, dict): return "opponent" if item == "self" else "self" if item == "opponent" else item
        return {("opponent" if key == "self" else "self" if key == "opponent" else key): swap(value) for key, value in item.items()}
    swapped = swap(value)
    direct = swapped.get("direct_mechanics_context") if isinstance(swapped, Mapping) else None
    if isinstance(direct, dict): direct["attacker"], direct["defender"] = direct.get("defender"), direct.get("attacker")
    return swapped


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
