"""Detached, exact end-of-turn residual projection for one immediate-pair leaf.

This module deliberately owns no reducer state.  Its input is an immutable
terminal branch plus the two active Pokemon's *post-action* detached facts;
the returned ledger is therefore safe to use for explanation/debugging while
the strategy horizon remains ``immediate_action_consequence``.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_sandstorm_residual_core import evaluate_sandstorm_residual


PHASE_INPUT_SCHEMA = "detached-end-of-turn-phase-input-v1"
PHASE_LEDGER_SCHEMA = "exact-end-of-turn-residual-phase-ledger-v1"
HORIZON = "end_of_turn_residual_projection"

# This is a catalog, rather than incidental construction order.  Modern
# status residuals share a class and are followed by held-item recovery.  New
# residual families get an explicit class here when they are supported.
END_OF_TURN_EVENT_ORDER = {
    "sandstorm": 50,
    # Linked target drain plus recipient transfer is an atomic residual tier.
    "leech_seed": 80,
    "burn": 100,
    "poison": 100,
    "toxic": 100,
    "leftovers": 200,
}
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_CONDITIONS = {"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"}


def materialize_detached_weather_residual(*, weather_authority: Mapping[str, Any], active: Mapping[str, Any], active_abilities: Mapping[str, str]) -> dict[str, Any]:
    """Resolve the weather consumer from exact detached terminal authority only.

    This narrow helper is deliberately side-effect free; the phase ledger can
    consume its result once terminal weather/type adapters are materialized.
    Snow is exact non-damaging weather in the current ruleset.
    """
    if not isinstance(weather_authority, Mapping) or weather_authority.get("status") != "known":
        return {"status": "incomplete", "reason": "end_of_turn_weather_unknown"}
    weather = weather_authority.get("weather")
    if weather in {"none", "rain", "sun", "snow"}:
        return {"status": "resolved", "outcome": "non_damaging_weather", "weather": weather, "residual_damage": 0}
    if weather != "sandstorm" or not isinstance(active, Mapping):
        return {"status": "rejected", "reason": "end_of_turn_weather_authority_invalid"}
    result = evaluate_sandstorm_residual(current_type=active.get("types"), item=active.get("item"), active_abilities=active_abilities, target_side=active.get("side"), current_hp=active.get("current_hp"), maximum_hp=active.get("maximum_hp"))
    return {"status": result.get("status"), "weather": "sandstorm", "result": result, "provenance": "canonical_sandstorm_residual_core_v1"}


def materialize_detached_leech_seed_transfer(*, trace: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize the established tier-eight linked transfer trace for EOT use."""
    required = {"effect", "owner", "recipient", "source_slot", "target_pre_hp", "target_post_hp", "target_damage", "recipient_pre_hp", "recipient_post_hp", "recipient_modifier", "liquid_ooze", "attempted_recovery", "recipient_outcome", "execution_status", "provenance"}
    if not isinstance(trace, Mapping) or trace.get("effect") != "leech_seed" or trace.get("provenance") != "detached_branch_leech_seed_v1" or not required <= set(trace):
        return {"status": "rejected", "reason": "invalid_leech_seed_transfer_trace"}
    owner, recipient, slot = trace["owner"], trace["recipient"], trace["source_slot"]
    if not all(isinstance(value, Mapping) for value in (owner, recipient, slot)) or owner.get("side") not in {"self", "opponent"} or recipient.get("side") not in {"self", "opponent"} or owner.get("side") == recipient.get("side") or slot.get("side") != recipient.get("side") or slot.get("session_id") != recipient.get("session_id") or slot.get("slot_index") != recipient.get("slot_index"):
        return {"status": "rejected", "reason": "leech_seed_source_position_or_recipient_invalid"}
    integers = ("target_pre_hp", "target_post_hp", "target_damage", "recipient_pre_hp", "recipient_post_hp", "attempted_recovery")
    if any(not isinstance(trace[key], int) or isinstance(trace[key], bool) or trace[key] < 0 for key in integers):
        return {"status": "rejected", "reason": "leech_seed_transfer_numeric_authority_invalid"}
    if trace["target_post_hp"] != max(0, trace["target_pre_hp"] - trace["target_damage"]):
        return {"status": "rejected", "reason": "leech_seed_target_hp_continuity_invalid"}
    if trace["execution_status"] != "executed" or not isinstance(trace["liquid_ooze"], bool):
        return {"status": "rejected", "reason": "leech_seed_transfer_execution_invalid"}
    if trace["liquid_ooze"]:
        recipient_valid = trace["recipient_post_hp"] == max(0, trace["recipient_pre_hp"] - trace["attempted_recovery"])
    else:
        recipient_valid = trace["recipient_pre_hp"] <= trace["recipient_post_hp"] <= trace["recipient_pre_hp"] + trace["attempted_recovery"]
    if not recipient_valid:
        return {"status": "rejected", "reason": "leech_seed_recipient_hp_continuity_invalid"}
    return {"status": "resolved", "event_kind": "leech_seed", "order_class": END_OF_TURN_EVENT_ORDER["leech_seed"], "linked_transfer": deepcopy(dict(trace)), "provenance": "canonical_detached_leech_seed_transfer_adapter_v1"}


def freeze_end_of_turn_phase_input(*, terminal_ledger: Mapping[str, Any], terminal_leaf_id: str, active_states: Mapping[str, Any], weather_authority: Mapping[str, Any] | None = None, leech_seed_transfers: tuple[Mapping[str, Any], ...] = ()) -> dict[str, Any]:
    """Bind two exact detached active states to one normalized pair leaf.

    ``terminal_ledger`` is intentionally the output of the immediate-pair
    normalizer.  The phase refuses an unnormalised source and checks that the
    supplied terminal HPs are exactly the selected leaf's final HPs.
    """
    base, leaf = _terminal_leaf(terminal_ledger, terminal_leaf_id)
    if base is None:
        return _result("rejected", "end_of_turn_terminal_branch_invalid")
    if not isinstance(active_states, Mapping) or set(active_states) != {"self", "opponent"}:
        return _result("rejected", "end_of_turn_active_states_invalid", base)
    rows: dict[str, dict[str, Any]] = {}
    for side, expected_hp in (("self", leaf["final_consequences"]["own_final_hp"]), ("opponent", leaf["final_consequences"]["opponent_final_hp"])):
        row = _active_state(active_states.get(side), base, side, expected_hp, terminal_leaf_id)
        if isinstance(row, str):
            return _result("incomplete" if row.endswith("_unknown") else "rejected", row, base)
        rows[side] = row
    weather = _weather_authority(weather_authority, base, terminal_leaf_id)
    if isinstance(weather, str): return _result("incomplete" if weather.endswith("_unknown") else "rejected", weather, base)
    transfers = tuple(materialize_detached_leech_seed_transfer(trace=row) for row in leech_seed_transfers)
    if any(row.get("status") != "resolved" for row in transfers): return _result("rejected", "end_of_turn_leech_seed_transfer_invalid", base)
    return {
        "status": "resolved", "schema_version": PHASE_INPUT_SCHEMA, "horizon": HORIZON,
        **base, "terminal_leaf_id": terminal_leaf_id,
        "terminal_probability_mass": deepcopy(terminal_ledger["terminal_probability_mass"]),
        "terminal_branch": deepcopy(dict(leaf)), "active_states": rows, "weather_authority": weather, "leech_seed_transfers": transfers,
        "provenance": "strict_detached_immediate_terminal_to_end_of_turn_phase_input_v1",
    }


def materialize_end_of_turn_residual_phase(*, phase_input: Mapping[str, Any]) -> dict[str, Any]:
    """Project ordered supported residual events without mutating D0/reducer."""
    error = _valid_input(phase_input)
    if error is not None:
        return _result("rejected", error)
    candidates: list[dict[str, Any]] = []
    for side in ("self", "opponent"):
        row = phase_input["active_states"][side]
        candidate = _candidate_for(row, phase_input)
        if isinstance(candidate, str):
            return _result("incomplete", candidate, _base_from_input(phase_input))
        candidates.extend(candidate)
    weather_candidates = _weather_candidates(phase_input)
    if isinstance(weather_candidates, str): return _result("incomplete", weather_candidates, _base_from_input(phase_input))
    candidates.extend(weather_candidates)
    order_error = _require_residual_speed_authority(candidates)
    if order_error is not None:
        return _result("incomplete", order_error, _base_from_input(phase_input))
    candidates.sort(key=_event_sort_key)
    mutable = {side: {"hp": phase_input["active_states"][side]["hp"]["current_hp"], "fainted": phase_input["active_states"][side]["fainted"]["value"]} for side in ("self", "opponent")}
    events = []
    transfers_applied = False
    for candidate in candidates:
        # Tier eight is intentionally between weather and status residuals.
        # The transfer is one atomic record: no unrelated event can split its
        # target drain from its recipient consequence.
        if not transfers_applied and END_OF_TURN_EVENT_ORDER[candidate["kind"]] > END_OF_TURN_EVENT_ORDER["leech_seed"]:
            transfer_error = _apply_leech_seed_transfers(phase_input, mutable, events)
            if transfer_error is not None:
                return _result("incomplete", transfer_error, _base_from_input(phase_input))
            transfers_applied = True
        side, row = candidate["side"], phase_input["active_states"][candidate["side"]]
        before, fainted = mutable[side]["hp"], mutable[side]["fainted"]
        # A normal residual/healing effect cannot revive or continue to affect
        # an identity that fainted earlier in this detached phase.
        if fainted:
            continue
        delta = candidate["delta"](before, row["hp"]["maximum_hp"])
        after = min(row["hp"]["maximum_hp"], max(0, before + delta))
        mutable[side] = {"hp": after, "fainted": after == 0}
        events.append({
            "event_id": f"{phase_input['terminal_leaf_id']}:eot:{len(events)+1}:{candidate['kind']}:{side}",
            "event_kind": candidate["kind"], "order_class": END_OF_TURN_EVENT_ORDER[candidate["kind"]],
            "ordinal": len(events)+1, "affected_owner": deepcopy(row["owner"]),
            "source_authority": deepcopy(candidate["source_authority"]),
            "source_terminal_leaf_id": phase_input["terminal_leaf_id"],
            "pre_hp": before, "max_hp": row["hp"]["maximum_hp"], "hp_delta": delta,
            "post_hp": after, "fainted": after == 0,
            "terminal_reason": "residual_ko" if after == 0 and delta < 0 else ("already_full_hp" if delta == 0 and candidate["kind"] == "leftovers" else None),
            "ordering_authority": _ordering_authority(candidate, row),
        })
    if not transfers_applied:
        transfer_error = _apply_leech_seed_transfers(phase_input, mutable, events)
        if transfer_error is not None:
            return _result("incomplete", transfer_error, _base_from_input(phase_input))
    final_states = {
        side: {"owner": deepcopy(phase_input["active_states"][side]["owner"]), "current_hp": mutable[side]["hp"], "maximum_hp": phase_input["active_states"][side]["hp"]["maximum_hp"], "fainted": mutable[side]["fainted"], "condition": deepcopy(phase_input["active_states"][side]["condition"]), "item": deepcopy(phase_input["active_states"][side]["item"]), "toxic_progression": _post_toxic(phase_input["active_states"][side], events, side), "replacement_after_end_of_turn_faint": "deferred" if mutable[side]["fainted"] and not phase_input["active_states"][side]["fainted"]["value"] else None}
        for side in ("self", "opponent")
    }
    result = {"status": "evaluable", "schema_version": PHASE_LEDGER_SCHEMA, "horizon": HORIZON, **_base_from_input(phase_input), "terminal_leaf_id": phase_input["terminal_leaf_id"], "phase_input": deepcopy(dict(phase_input)), "events": tuple(events), "post_end_of_turn_active_states": final_states, "provenance": "deterministic_detached_end_of_turn_residual_phase_v1"}
    return validate_end_of_turn_residual_phase_ledger(ledger=result)


def validate_end_of_turn_residual_phase_ledger(*, ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Reject forged order, deltas, terminal bindings, or continuity."""
    if not isinstance(ledger, Mapping) or ledger.get("status") != "evaluable" or ledger.get("schema_version") != PHASE_LEDGER_SCHEMA:
        return _result("rejected", "end_of_turn_phase_ledger_invalid")
    phase_input = ledger.get("phase_input")
    expected = materialize_end_of_turn_residual_phase_unvalidated(phase_input)
    if isinstance(expected, str):
        return _result("rejected", expected)
    comparable = {key: deepcopy(ledger.get(key)) for key in ("terminal_leaf_id", "events", "post_end_of_turn_active_states")}
    wanted = {key: deepcopy(expected.get(key)) for key in comparable}
    if comparable != wanted:
        return _result("rejected", "end_of_turn_phase_ledger_mechanics_or_provenance_mismatch", _base_from_input(phase_input))
    return deepcopy(dict(ledger))


def materialize_end_of_turn_residual_phase_unvalidated(phase_input: Any) -> dict[str, Any] | str:
    """Internal non-recursive implementation used by the ledger validator."""
    if not isinstance(phase_input, Mapping) or _valid_input(phase_input) is not None:
        return "end_of_turn_phase_input_invalid"
    # Call the public mechanics body with validation temporarily bypassed by
    # duplicating its small projection through a sentinel-free local wrapper.
    # The public call is kept separate so validation never trusts caller rows.
    candidates: list[dict[str, Any]] = []
    for side in ("self", "opponent"):
        candidate = _candidate_for(phase_input["active_states"][side], phase_input)
        if isinstance(candidate, str): return candidate
        candidates.extend(candidate)
    weather_candidates = _weather_candidates(phase_input)
    if isinstance(weather_candidates, str): return weather_candidates
    candidates.extend(weather_candidates)
    if _require_residual_speed_authority(candidates) is not None: return "end_of_turn_residual_speed_unknown"
    candidates.sort(key=_event_sort_key)
    mutable = {s: {"hp": phase_input["active_states"][s]["hp"]["current_hp"], "fainted": phase_input["active_states"][s]["fainted"]["value"]} for s in ("self", "opponent")}
    events = []
    transfers_applied = False
    for candidate in candidates:
        if not transfers_applied and END_OF_TURN_EVENT_ORDER[candidate["kind"]] > END_OF_TURN_EVENT_ORDER["leech_seed"]:
            transfer_error = _apply_leech_seed_transfers(phase_input, mutable, events)
            if transfer_error is not None: return transfer_error
            transfers_applied = True
        side, row = candidate["side"], phase_input["active_states"][candidate["side"]]
        if mutable[side]["fainted"]: continue
        before = mutable[side]["hp"]; delta = candidate["delta"](before, row["hp"]["maximum_hp"]); after = min(row["hp"]["maximum_hp"], max(0, before + delta)); mutable[side] = {"hp": after, "fainted": after == 0}
        events.append({"event_id": f"{phase_input['terminal_leaf_id']}:eot:{len(events)+1}:{candidate['kind']}:{side}", "event_kind": candidate["kind"], "order_class": END_OF_TURN_EVENT_ORDER[candidate["kind"]], "ordinal": len(events)+1, "affected_owner": deepcopy(row["owner"]), "source_authority": deepcopy(candidate["source_authority"]), "source_terminal_leaf_id": phase_input["terminal_leaf_id"], "pre_hp": before, "max_hp": row["hp"]["maximum_hp"], "hp_delta": delta, "post_hp": after, "fainted": after == 0, "terminal_reason": "residual_ko" if after == 0 and delta < 0 else ("already_full_hp" if delta == 0 and candidate["kind"] == "leftovers" else None), "ordering_authority": _ordering_authority(candidate, row)})
    if not transfers_applied:
        transfer_error = _apply_leech_seed_transfers(phase_input, mutable, events)
        if transfer_error is not None: return transfer_error
    final = {s: {"owner": deepcopy(phase_input["active_states"][s]["owner"]), "current_hp": mutable[s]["hp"], "maximum_hp": phase_input["active_states"][s]["hp"]["maximum_hp"], "fainted": mutable[s]["fainted"], "condition": deepcopy(phase_input["active_states"][s]["condition"]), "item": deepcopy(phase_input["active_states"][s]["item"]), "toxic_progression": _post_toxic(phase_input["active_states"][s], events, s), "replacement_after_end_of_turn_faint": "deferred" if mutable[s]["fainted"] and not phase_input["active_states"][s]["fainted"]["value"] else None} for s in ("self", "opponent")}
    return {"terminal_leaf_id": phase_input["terminal_leaf_id"], "events": tuple(events), "post_end_of_turn_active_states": final}


def _apply_leech_seed_transfers(phase_input: Mapping[str, Any], mutable: dict[str, dict[str, Any]], events: list[dict[str, Any]]) -> str | None:
    """Apply the already-materialized linked tier without splitting it.

    The trace is produced by the reducer-owned Leech Seed lifecycle.  This
    phase additionally binds both ends to the terminal active identities and
    consumes the current mutable HPs, so a historical source identity can
    never be used as the recipient after a position change.
    """
    for transfer in phase_input.get("leech_seed_transfers", ()):
        trace = transfer["linked_transfer"]
        target_side, recipient_side = trace["owner"]["side"], trace["recipient"]["side"]
        target_row, recipient_row = phase_input["active_states"][target_side], phase_input["active_states"][recipient_side]
        if trace["owner"] != target_row["owner"] or trace["recipient"] != recipient_row["owner"]:
            return "leech_seed_transfer_terminal_identity_mismatch"
        if mutable[target_side]["fainted"]:
            # An earlier canonical residual KO prevents this later tier.
            continue
        if mutable[target_side]["hp"] != trace["target_pre_hp"]:
            return "leech_seed_transfer_hp_continuity_unavailable"
        # A fainted recipient remains fainted and is never revived.  The
        # target drain still has its own resolved consequence.
        if mutable[recipient_side]["fainted"]:
            if trace["recipient_pre_hp"] != 0 or trace["recipient_post_hp"] != 0:
                return "leech_seed_fainted_recipient_continuity_invalid"
        elif mutable[recipient_side]["hp"] != trace["recipient_pre_hp"]:
            return "leech_seed_transfer_hp_continuity_unavailable"
        mutable[target_side] = {"hp": trace["target_post_hp"], "fainted": trace["target_post_hp"] == 0}
        mutable[recipient_side] = {"hp": trace["recipient_post_hp"], "fainted": trace["recipient_post_hp"] == 0}
        events.append({
            "event_id": f"{phase_input['terminal_leaf_id']}:eot:{len(events)+1}:leech_seed:{target_side}",
            "event_kind": "leech_seed", "order_class": END_OF_TURN_EVENT_ORDER["leech_seed"],
            "ordinal": len(events)+1, "affected_owner": deepcopy(trace["owner"]),
            "source_authority": deepcopy(transfer), "source_terminal_leaf_id": phase_input["terminal_leaf_id"],
            "pre_hp": trace["target_pre_hp"], "max_hp": target_row["hp"]["maximum_hp"],
            "hp_delta": -trace["target_damage"], "post_hp": trace["target_post_hp"],
            "fainted": trace["target_post_hp"] == 0, "linked_recipient": deepcopy(trace["recipient"]),
            "recipient_pre_hp": trace["recipient_pre_hp"], "recipient_post_hp": trace["recipient_post_hp"],
            "recipient_fainted": trace["recipient_post_hp"] == 0,
            "ordering_authority": {"catalog": "canonical_end_of_turn_residual_order_v1", "order_class": END_OF_TURN_EVENT_ORDER["leech_seed"]},
        })
    return None


def _terminal_leaf(ledger: Any, leaf_id: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(ledger, Mapping) or ledger.get("status") != "evaluable" or ledger.get("schema_version") != "exact-immediate-action-pair-outcome-ledger-v1" or not isinstance(leaf_id, str) or not leaf_id:
        return None, None
    required = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_actor", "opponent_actor")
    if any(key not in ledger for key in required) or ledger.get("terminal_probability_mass") != {"numerator": 1, "denominator": 1}: return None, None
    leaf = next((x for x in ledger.get("terminal_leaves", ()) if isinstance(x, Mapping) and x.get("pair_leaf_id") == leaf_id), None)
    consequences = leaf.get("final_consequences") if isinstance(leaf, Mapping) else None
    if not isinstance(consequences, Mapping) or not _hp(consequences.get("own_final_hp")) or not _hp(consequences.get("opponent_final_hp")): return None, None
    return ({key: deepcopy(ledger[key]) for key in required}, deepcopy(dict(leaf)))


def _active_state(value: Any, base: Mapping[str, Any], side: str, expected_hp: int, leaf_id: str) -> dict[str, Any] | str:
    allowed = {"owner", "hp", "fainted", "condition", "item", "toxic_progression", "speed", "ability", "types"}
    if not isinstance(value, Mapping) or set(value) not in (allowed - {"types"}, allowed): return "end_of_turn_active_state_invalid"
    owner = value["owner"]
    expected_owner = base["own_actor"] if side == "self" else base["opponent_actor"]
    if not _owner(owner, base["session_id"]) or owner != expected_owner: return "end_of_turn_active_identity_mismatch"
    hp, fainted = value["hp"], value["fainted"]
    if not isinstance(hp, Mapping) or hp.get("status") != "known" or hp.get("source_terminal_leaf_id") != leaf_id or not _hp(hp.get("current_hp")) or not _positive(hp.get("maximum_hp")) or hp["current_hp"] > hp["maximum_hp"]: return "end_of_turn_hp_unknown"
    if hp["current_hp"] != expected_hp: return "end_of_turn_terminal_hp_binding_mismatch"
    if not isinstance(fainted, Mapping) or fainted.get("status") != "known" or fainted.get("source_terminal_leaf_id") != leaf_id or fainted.get("value") is not (hp["current_hp"] == 0): return "end_of_turn_faint_authority_invalid"
    condition = _condition(value["condition"], base, owner, leaf_id)
    if isinstance(condition, str): return condition
    item = value["item"]
    if not isinstance(item, Mapping) or item.get("status") not in {"known", "known_absent", "unknown"} or not _bound_to_base(item, base, owner) or (item.get("status") == "known" and not isinstance(item.get("value"), str)): return "end_of_turn_item_authority_invalid"
    toxic = value["toxic_progression"]
    if not isinstance(toxic, Mapping) or toxic.get("status") not in {"known", "unknown"} or not _bound_to_base(toxic, base, owner): return "end_of_turn_toxic_authority_invalid"
    if toxic.get("status") == "known" and (not isinstance(toxic.get("next_stage"), int) or isinstance(toxic["next_stage"], bool) or not 1 <= toxic["next_stage"] <= 15): return "end_of_turn_toxic_authority_invalid"
    speed = value["speed"]
    if not isinstance(speed, Mapping) or speed.get("status") not in {"known", "unknown"} or not _bound_to_base(speed, base, owner) or (speed.get("status") == "known" and (not isinstance(speed.get("value"), int) or isinstance(speed["value"], bool) or speed["value"] < 0)): return "end_of_turn_speed_authority_invalid"
    ability = value["ability"]
    if not isinstance(ability, Mapping) or ability.get("status") not in {"known", "known_absent", "unknown"} or not _bound_to_base(ability, base, owner): return "end_of_turn_ability_authority_invalid"
    types = value.get("types")
    if types is not None and (not isinstance(types, Mapping) or types.get("status") not in {"known", "unknown"} or not _bound_to_base(types, base, owner) or (types.get("status") == "known" and (not isinstance(types.get("value"), list) or not types["value"]))): return "end_of_turn_type_authority_invalid"
    return {"owner": deepcopy(dict(owner)), "hp": deepcopy(dict(hp)), "fainted": deepcopy(dict(fainted)), "condition": condition, "item": deepcopy(dict(item)), "toxic_progression": deepcopy(dict(toxic)), "speed": deepcopy(dict(speed)), "ability": deepcopy(dict(ability)), **({"types": deepcopy(dict(types))} if types is not None else {})}


def _condition(value: Any, base: Mapping[str, Any], owner: Mapping[str, Any], leaf_id: str) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("status") not in {"known_none", "known_present", "unknown"} or not _bound_to_base(value, base, owner): return "end_of_turn_condition_authority_invalid"
    if value["status"] == "unknown": return "end_of_turn_condition_unknown"
    if value["status"] == "known_none": return {"status": "known_none", "provenance": deepcopy(value.get("provenance")), "source_binding": deepcopy(value["source_binding"])}
    if value.get("condition") not in _CONDITIONS - {"none"}: return "end_of_turn_condition_authority_invalid"
    source = value.get("source_terminal_leaf_id")
    # A source leaf is mandatory only for path-local hypothetical transitions;
    # committed current-condition authority has its own strict provenance.
    if source is not None and source != leaf_id: return "end_of_turn_condition_terminal_binding_mismatch"
    if source is not None:
        transition = value.get("hypothetical_condition_authority")
        if not isinstance(transition, Mapping) or transition.get("status") != "known_present" or transition.get("condition") != value["condition"]:
            return "end_of_turn_hypothetical_condition_transition_unproven"
    return {"status": "known_present", "condition": value["condition"], "provenance": deepcopy(value.get("provenance")), "source_binding": deepcopy(value["source_binding"]), **({"source_terminal_leaf_id": source, "hypothetical_condition_authority": deepcopy(value["hypothetical_condition_authority"])} if source is not None else {})}


def _candidate_for(row: Mapping[str, Any], phase_input: Mapping[str, Any]) -> list[dict[str, Any]] | str:
    if row["fainted"]["value"]: return []
    if row["item"]["status"] == "unknown": return "end_of_turn_item_unknown"
    condition = row["condition"]
    if condition["status"] == "known_present" and row["ability"].get("status") == "known" and row["ability"].get("value") == "magic-guard": return "end_of_turn_magic_guard_residual_consumer_unimplemented"
    out: list[dict[str, Any]] = []
    if condition["status"] == "known_present":
        kind = condition["condition"]
        if kind == "toxic":
            toxic = row["toxic_progression"]
            if toxic["status"] != "known": return "end_of_turn_toxic_counter_unknown"
            stage = toxic["next_stage"]
            out.append(_candidate("toxic", row, phase_input, lambda _hp, maximum, n=stage: -((maximum * n) // 16), {"condition": deepcopy(condition), "toxic_stage": stage, "toxic_next_stage": min(stage + 1, 15)}))
        elif kind in {"burn", "poison"}:
            divisor = 16 if kind == "burn" else 8
            out.append(_candidate(kind, row, phase_input, lambda _hp, maximum, d=divisor: -(maximum // d), {"condition": deepcopy(condition), "divisor": divisor}))
    if row["item"].get("status") == "known" and row["item"].get("value") == "leftovers":
        out.append(_candidate("leftovers", row, phase_input, lambda hp, maximum: min(maximum, hp + maximum // 16) - hp, {"item": deepcopy(row["item"]), "divisor": 16}))
    return out


def _weather_authority(value: Any, base: Mapping[str, Any], leaf_id: str) -> dict[str, Any] | str:
    if value is None: return {"status": "unknown"}
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}: return "end_of_turn_weather_authority_invalid"
    if value["status"] == "unknown": return {"status": "unknown"}
    binding = value.get("source_binding")
    expected = {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"]}
    if binding != expected or value.get("weather") not in {"none", "rain", "sun", "snow", "sandstorm"}: return "end_of_turn_weather_authority_invalid"
    if value.get("source_terminal_leaf_id") not in {None, leaf_id}: return "end_of_turn_weather_terminal_binding_mismatch"
    return deepcopy(dict(value))


def _weather_candidates(phase_input: Mapping[str, Any]) -> list[dict[str, Any]] | str:
    weather = phase_input.get("weather_authority", {"status": "unknown"})
    if weather.get("status") == "unknown": return []
    if weather.get("weather") != "sandstorm": return []
    abilities = {}
    for side in ("self", "opponent"):
        ability = phase_input["active_states"][side]["ability"]
        if ability.get("status") != "known": return "end_of_turn_weather_ability_unknown"
        abilities[side] = ability.get("value")
    out = []
    for side in ("self", "opponent"):
        row = phase_input["active_states"][side]
        if row["fainted"]["value"]: continue
        types = row.get("types")
        if not isinstance(types, Mapping) or types.get("status") != "known": return "end_of_turn_weather_type_unknown"
        item = row["item"]
        if item.get("status") == "unknown": return "end_of_turn_weather_item_unknown"
        active = {"side": side, "types": types["value"], "item": item.get("value") if item.get("status") == "known" else None, "current_hp": row["hp"]["current_hp"], "maximum_hp": row["hp"]["maximum_hp"]}
        resolved = materialize_detached_weather_residual(weather_authority=weather, active=active, active_abilities=abilities)
        if resolved.get("status") != "complete": return "end_of_turn_weather_residual_unavailable"
        result = resolved["result"]
        if result["residual_damage"]:
            out.append(_candidate("sandstorm", row, phase_input, lambda _hp, maximum: -(maximum // 16), {"weather": deepcopy(weather), "weather_residual": deepcopy(result), "types": deepcopy(types), "ability": deepcopy(row["ability"]), "item": deepcopy(item)}))
    return out


def _candidate(kind, row, phase_input, delta, source):
    return {"kind": kind, "side": row["owner"]["side"], "speed": deepcopy(row["speed"]), "delta": delta, "source_authority": {**source, "phase_input_binding": {"session_id": phase_input["session_id"], "pair_id": phase_input["pair_id"], "terminal_leaf_id": phase_input["terminal_leaf_id"]}}}


def _require_residual_speed_authority(candidates: list[dict[str, Any]]) -> str | None:
    for order in set(END_OF_TURN_EVENT_ORDER[c["kind"]] for c in candidates):
        group = [c for c in candidates if END_OF_TURN_EVENT_ORDER[c["kind"]] == order]
        if len({c["side"] for c in group}) > 1:
            if any(c["speed"].get("status") != "known" for c in group): return "end_of_turn_residual_speed_unknown"
    return None


def _event_sort_key(candidate: Mapping[str, Any]) -> tuple[int, int, str, int]:
    # Same residual class resolves by exact effective speed; equal speed has
    # an explicit non-RNG identity tiebreak because no supported event depends
    # on the other active's post-event HP.
    kind = candidate["kind"]
    side = candidate["side"]
    speed = candidate["speed"].get("value", 0)
    return (END_OF_TURN_EVENT_ORDER[kind], -speed, side, 0)


def _ordering_authority(candidate: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    return {"catalog": "canonical_end_of_turn_residual_order_v1", "order_class": END_OF_TURN_EVENT_ORDER[candidate["kind"]], "speed_authority": deepcopy(row["speed"]), "equal_speed_tie_break": "canonical_owner_identity_non_rng_v1"}


def _post_toxic(row: Mapping[str, Any], events: list[Mapping[str, Any]], side: str) -> dict[str, Any]:
    toxic = deepcopy(row["toxic_progression"])
    event = next((x for x in events if x["affected_owner"]["side"] == side and x["event_kind"] == "toxic"), None)
    if event is not None and toxic.get("status") == "known": toxic["next_stage"] = min(toxic["next_stage"] + 1, 15); toxic["source_event_id"] = event["event_id"]
    return toxic


def _valid_input(value: Any) -> str | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != PHASE_INPUT_SCHEMA or value.get("horizon") != HORIZON: return "end_of_turn_phase_input_invalid"
    base, leaf = _terminal_leaf({"status": "evaluable", "schema_version": "exact-immediate-action-pair-outcome-ledger-v1", **{key: value.get(key) for key in ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_actor", "opponent_actor", "terminal_probability_mass")}, "terminal_leaves": (value.get("terminal_branch"),)}, value.get("terminal_leaf_id"))
    if base is None or not isinstance(value.get("active_states"), Mapping): return "end_of_turn_phase_input_invalid"
    for side, hp in (("self", leaf["final_consequences"]["own_final_hp"]), ("opponent", leaf["final_consequences"]["opponent_final_hp"])):
        if isinstance(_active_state(value["active_states"].get(side), base, side, hp, value["terminal_leaf_id"]), str): return "end_of_turn_phase_input_invalid"
    return None


def _base_from_input(value: Mapping[str, Any]) -> dict[str, Any]: return {key: deepcopy(value[key]) for key in ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_actor", "opponent_actor") if key in value}
def _bound_to_base(value: Mapping[str, Any], base: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    binding = value.get("source_binding")
    return isinstance(binding, Mapping) and binding == {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "owner": dict(owner)}
def _owner(value: Any, session: str) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and value.get("session_id") == session and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _positive(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value > 0
def _result(status: str, reason: str, base: Mapping[str, Any] | None = None) -> dict[str, Any]: return {"status": status, "schema_version": PHASE_LEDGER_SCHEMA, **(deepcopy(dict(base)) if base else {}), "reason": reason}
