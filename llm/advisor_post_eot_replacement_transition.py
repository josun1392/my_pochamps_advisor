"""Explicit trainer choices at the detached post-EOT replacement boundary.

Requests and cursors are value objects: every public consumer replays their
source ledger before using them. Entry steps reuse the switch-entry executor.
No operation writes reducer state, advances a committed turn, or ranks choices.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_end_of_turn_residual_phase import validate_end_of_turn_residual_phase_ledger
from llm.advisor_executable_switch_transition import (
    execute_materialized_switch_entry, execute_materialized_entry_abilities,
)
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_transition_preview import fingerprint_transition_preview_state as fingerprint

SCHEMA = "detached-post-eot-replacement-transition-v1"
SIDES = ("self", "opponent")
OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
BINDING_KEYS = ("session_id", "pair_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "terminal_leaf_id")


def post_eot_source_binding(eot_ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Identity used by external terminal-context and roster authority owners."""
    return {**{k: deepcopy(eot_ledger.get(k)) for k in BINDING_KEYS}, "source_eot_fingerprint": fingerprint(eot_ledger)}


def freeze_post_eot_transition(*, eot_ledger, source_eot_fingerprint, branch_authority, team_authorities):
    """Consume exact EOT HP and a separately bound terminal mechanics context."""
    try:
        return _freeze(eot_ledger, source_eot_fingerprint, branch_authority, team_authorities)
    except (KeyError, TypeError, ValueError, AttributeError):
        return _error("rejected", "malformed_post_eot_authority")


def _freeze(eot, source_fp, branch, teams):
    if not isinstance(eot, Mapping) or not isinstance(source_fp, str) or fingerprint(eot) != source_fp:
        return _error("rejected", "stale_or_foreign_eot_ledger")
    checked = validate_end_of_turn_residual_phase_ledger(ledger=eot)
    if checked.get("status") != "evaluable":
        return _error("rejected", "invalid_source_eot_ledger")
    # The existing EOT validator checks mechanics; this boundary also checks
    # the envelope against its embedded phase input.
    if any(eot.get(k) != eot["phase_input"].get(k) for k in BINDING_KEYS):
        return _error("rejected", "eot_envelope_binding_mismatch")
    binding = post_eot_source_binding(eot)
    if not isinstance(branch, Mapping) or branch.get("status") != "known" or branch.get("source_binding") != binding:
        return _error("incomplete" if branch is None else "rejected", "post_eot_branch_binding_unavailable")
    state = branch.get("state")
    if not isinstance(state, Mapping) or branch.get("state_fingerprint") != fingerprint(state):
        return _error("rejected", "post_eot_branch_fingerprint_mismatch")
    for side in SIDES:
        final = eot["post_end_of_turn_active_states"][side]
        active = state.get("active", {}).get(side)
        if not isinstance(active, Mapping) or not isinstance(active.get("fainted"), bool) or not _integer(active.get("current_hp")) or not _integer(active.get("max_hp")) or _owner(active) != final["owner"] or any(active.get(k) != final[v] for k, v in (("current_hp", "current_hp"), ("max_hp", "maximum_hp"), ("fainted", "fainted"))):
            return _error("rejected", "post_eot_active_state_mismatch")
        error = _check_current(state, side, final)
        if error: return _error("rejected", error)
    weather = eot["phase_input"].get("weather_authority", {})
    if weather.get("status") == "known" and state["current_state"].get("field_state_context", {}).get("current_field", {}).get("weather") != weather["weather"]:
        return _error("rejected", "post_eot_weather_mismatch")
    if not isinstance(teams, Mapping) or set(teams) - set(SIDES):
        return _error("rejected", "team_authorities_invalid")
    for side, team in teams.items():
        error = _check_team(team, side, binding, state)
        if error: return _error("rejected", error)
    source = {"eot_ledger": deepcopy(eot), "source_eot_fingerprint": source_fp,
              "branch_authority": deepcopy(branch), "team_authorities": deepcopy(teams)}
    projected = deepcopy(state)
    projected["post_eot_toxic_progression"] = {
        side: {"owner": deepcopy(eot["post_end_of_turn_active_states"][side]["owner"]),
               "authority": deepcopy(eot["post_end_of_turn_active_states"][side]["toxic_progression"])} for side in SIDES}
    return _request(source, projected, deepcopy(teams), (), 0)


def _request(source, state, teams, history, generation):
    request_id = fingerprint({"source": source, "state": state, "teams": teams, "generation": generation, "history": history})
    requirements = {}
    for side in SIDES:
        active, team = state["active"][side], teams.get(side)
        candidates = []
        if active["fainted"] is False:
            status = "no_replacement_needed"
        elif not isinstance(team, Mapping) or team.get("status") != "known" or team.get("completeness") != "complete":
            status = "incomplete"
        else:
            unknown = False
            for row in team["members"]:
                if row["owner"] == _owner(active): continue
                if row["hp"]["status"] != "known" or row["eligible"]["status"] != "known":
                    unknown = True
                elif row["hp"]["current_hp"] > 0 and row["eligible"]["value"] is True:
                    candidates.append(deepcopy(row["owner"]))
            status = "incomplete" if unknown else "replacement_required" if candidates else "battle_terminal_no_replacement"
        requirements[side] = {"state": status, "outgoing_owner": _owner(active), "candidates": tuple(sorted(candidates, key=lambda x: x["slot_index"]))}
    kinds = {side: requirements[side]["state"] for side in SIDES}
    terminal = tuple(side for side in SIDES if kinds[side] == "battle_terminal_no_replacement")
    status = "incomplete" if "incomplete" in kinds.values() else "battle_terminal" if terminal else "replacement_required" if "replacement_required" in kinds.values() else "next_decision_ready"
    result = {"status": status, "schema_version": SCHEMA, "source": deepcopy(source), "request_id": request_id,
              "generation": generation, "state": deepcopy(state), "teams": deepcopy(teams), "history": deepcopy(history),
              "requirements": requirements, "battle_terminal": {"unable_to_replace_sides": terminal} if terminal else None,
              "strategy_horizon": "immediate_action_consequence", "trainer_choice_semantics": "explicit_selection_required"}
    if status == "next_decision_ready":
        handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch={"status": "resolved", "boundary": {"phase": "end_of_turn"}, "next_state": state, "resulting_branch_fingerprint": fingerprint(state)})
        if handoff.get("status") != "resolved": return handoff
        next_state = handoff["next_state"]
        # The legacy handoff owns state sanitization. At this boundary its
        # input may already include replacement entry, so name the two source
        # domains independently instead of labeling post-entry as EOT.
        next_state["turn_engine_lifecycle"] = {
            "schema_version": "detached-post-eot-next-decision-v1",
            "source_end_of_turn_fingerprint": source["source_eot_fingerprint"],
            "source_post_eot_state_fingerprint": fingerprint(state),
            "source_replacement_request_id": request_id,
            "provenance": "detached_post_eot_replacement_handoff_v1"}
        result["detached_next_decision_state"] = next_state
        result["next_decision_fingerprint"] = fingerprint(next_state)
    return result


def freeze_replacement_intent(*, transition, side, incoming_owner):
    if validate_post_eot_transition(transition=transition).get("status") != "valid":
        return _error("rejected", "invalid_replacement_request")
    if transition["status"] != "replacement_required" or side not in SIDES:
        return _error("rejected", "replacement_not_requested")
    request = transition["requirements"][side]
    if incoming_owner not in request["candidates"]:
        return _error("rejected", "selected_replacement_not_eligible")
    return {"status": "resolved", "schema_version": "explicit-post-eot-replacement-intent-v1", "session_id": incoming_owner["session_id"],
            "request_id": transition["request_id"], "generation": transition["generation"], "side": side,
            "outgoing_owner": deepcopy(request["outgoing_owner"]), "incoming_owner": deepcopy(incoming_owner), "choice_kind": "trainer_selected_faint_replacement"}


def _check_team(team, side, binding, state):
    if not isinstance(team, Mapping) or team.get("source_binding") != binding or team.get("side") != side:
        return "foreign_team_authority"
    if team.get("status") == "unknown": return None
    if team.get("status") != "known" or team.get("completeness") not in {"complete", "incomplete"} or not isinstance(team.get("members"), (tuple, list)):
        return "invalid_team_authority"
    owners, slots, ids = [], set(), set()
    for row in team["members"]:
        if not isinstance(row, Mapping) or not _valid_owner(row.get("owner"), binding["session_id"], side): return "invalid_team_member_identity"
        owner = row["owner"]
        if owner["slot_index"] in slots or owner["pokemon_id"] in ids: return "duplicate_team_member"
        slots.add(owner["slot_index"]); ids.add(owner["pokemon_id"]); owners.append(owner)
        hp, eligible = row.get("hp"), row.get("eligible")
        if not isinstance(hp, Mapping) or hp.get("status") not in {"known", "unknown"}: return "invalid_team_hp"
        if hp["status"] == "known" and (not _integer(hp.get("current_hp")) or not _integer(hp.get("maximum_hp")) or not 0 <= hp["current_hp"] <= hp["maximum_hp"] or hp["maximum_hp"] == 0): return "invalid_team_hp"
        if not isinstance(eligible, Mapping) or eligible.get("status") not in {"known", "unknown"} or (eligible["status"] == "known" and not isinstance(eligible.get("value"), bool)): return "invalid_team_eligibility"
        if owner == _owner(state["active"][side]) and (hp.get("status") != "known" or hp["current_hp"] != state["active"][side]["current_hp"] or hp["maximum_hp"] != state["active"][side]["max_hp"]): return "team_active_hp_mismatch"
    if team["completeness"] == "complete" and _owner(state["active"][side]) not in owners: return "complete_team_missing_active"
    return None


def _check_current(state, side, final):
    current = state.get("current_state")
    if not isinstance(current, Mapping) or current.get("current_state_session_id") != final["owner"]["session_id"]: return "post_eot_current_context_invalid"
    hp = [r for r in current.get("current_hp_context", {}).get("current_hp", ()) if r.get("side") == side]
    if len(hp) != 1 or hp[0].get("current_hp") != final["current_hp"] or hp[0].get("maximum_hp") != final["maximum_hp"]: return "post_eot_current_hp_mismatch"
    conditions = [r for r in current.get("condition_context", {}).get("current_conditions", ()) if r.get("side") == side]
    condition = final["condition"]
    expected = "none" if condition["status"] == "known_none" else condition.get("condition")
    if len(conditions) != 1 or conditions[0].get("condition_type") != expected: return "post_eot_condition_mismatch"
    role = "attacker" if side == "self" else "defender"
    direct = current.get("direct_mechanics_context", {}).get(role)
    if isinstance(direct, Mapping) and any(k in direct and direct[k] != final[v] for k, v in (("current_hp", "current_hp"), ("max_hp", "maximum_hp"))):
        return "post_eot_calculator_hp_mismatch"
    return None


def _valid_owner(owner, session, side):
    return isinstance(owner, Mapping) and set(owner) == set(OWNER_KEYS) and owner["session_id"] == session and owner["side"] == side and _integer(owner["slot_index"]) and owner["slot_index"] >= 0 and isinstance(owner["pokemon_id"], str) and bool(owner["pokemon_id"])


def _owner(value): return {k: value[k] for k in OWNER_KEYS}
def _integer(value): return isinstance(value, int) and not isinstance(value, bool)
def _error(status, reason): return {"status": status, "schema_version": SCHEMA, "reason": reason}


def validate_post_eot_transition(*, transition):
    """Replay the source and each explicit mechanics step; never trust post-state."""
    try:
        source = transition["source"]
        expected = freeze_post_eot_transition(**source)
        if expected.get("schema_version") != SCHEMA or "request_id" not in expected:
            return _error("rejected", "invalid_transition_source")
        for command in transition["history"]:
            expected = _replay_command(expected, command)
        if expected != transition: return _error("rejected", "transition_replay_mismatch")
        return {"status": "valid", "request_id": transition["request_id"]}
    except (KeyError, TypeError, ValueError, AttributeError):
        return _error("rejected", "malformed_transition_ledger")


def _replay_command(transition, command):
    if command.get("kind") == "select":
        return _prepare(transition, command["intents"], command.get("tie_order_authority"), command)
    if command.get("kind") == "entry":
        return _advance(transition, command["entry_authority"], command)
    return _error("rejected", "unsupported_transition_command")


def prepare_post_eot_replacements(*, transition, intents, tie_order_authority=None):
    """Establish every selected entrant before any switch-in interaction runs."""
    if validate_post_eot_transition(transition=transition).get("status") != "valid":
        return _error("rejected", "invalid_replacement_request")
    command = {"kind": "select", "intents": deepcopy(intents), "tie_order_authority": deepcopy(tie_order_authority)}
    try: return _prepare(transition, intents, tie_order_authority, command)
    except (KeyError, TypeError, ValueError, AttributeError): return _error("rejected", "malformed_replacement_selection")


def _prepare(transition, intents, tie_order, command):
    if transition["status"] != "replacement_required" or not isinstance(intents, Mapping):
        return _error("rejected", "replacement_selection_not_requested")
    needed = {s for s in SIDES if transition["requirements"][s]["state"] == "replacement_required"}
    if set(intents) - needed: return _error("rejected", "unrequested_replacement_intent")
    if set(intents) != needed: return _error("incomplete", "all_required_trainer_intents_needed")
    entrants = {}
    for side in sorted(needed):
        intent = intents[side]
        selected = intent.get("incoming_owner")
        expected = {"status": "resolved", "schema_version": "explicit-post-eot-replacement-intent-v1",
                    "session_id": transition["state"]["active"][side]["session_id"], "request_id": transition["request_id"],
                    "generation": transition["generation"], "side": side, "outgoing_owner": transition["requirements"][side]["outgoing_owner"],
                    "incoming_owner": selected, "choice_kind": "trainer_selected_faint_replacement"}
        if intent != expected or selected not in transition["requirements"][side]["candidates"]:
            return _error("rejected", "stale_or_foreign_replacement_intent")
        member = next(row for row in transition["teams"][side]["members"] if row["owner"] == selected)
        incoming = member.get("incoming_authority")
        if not isinstance(incoming, Mapping): return _error("incomplete", "incoming_mechanics_authority_missing")
        if incoming.get("owner") != selected or incoming.get("hp_authority") != member["hp"] or incoming.get("fainted_authority") != {"status": "known", "value": False}:
            return _error("rejected", "incoming_roster_binding_mismatch")
        if _check_incoming(member): return _error("rejected", "incoming_current_mechanics_mismatch")
        entrants[side] = deepcopy(member)
    order = sorted(needed)
    if len(order) == 2:
        speeds = {s: entrants[s].get("entry_speed") for s in order}
        if any(not isinstance(v, Mapping) or v.get("status") != "known" or not _integer(v.get("value")) or v["value"] < 0 for v in speeds.values()):
            return _error("incomplete", "simultaneous_entry_speed_unknown")
        if speeds[order[0]]["value"] == speeds[order[1]]["value"]:
            if not isinstance(tie_order, Mapping): return _error("incomplete", "simultaneous_entry_speed_tie_unresolved")
            if tie_order.get("request_id") != transition["request_id"] or tie_order.get("basis") != "resolved_switch_in_speed_tie" or tie_order.get("selected_owners") != {s: entrants[s]["owner"] for s in order} or sorted(tie_order.get("ordered_sides", ())) != order:
                return _error("rejected", "invalid_switch_in_tie_order")
            order = list(tie_order["ordered_sides"])
        else:
            if tie_order is not None: return _error("rejected", "unrequested_switch_in_tie_order")
            order.sort(key=lambda s: -speeds[s]["value"])
    state = deepcopy(transition["state"])
    retired = []
    for side in sorted(needed):
        outgoing = deepcopy(state["active"][side])
        incoming = deepcopy(entrants[side]["incoming_authority"])
        incoming["current_state"] = _merge_current(state["current_state"], incoming["current_state"], side)
        materialized = materialize_incoming_active_branch(source_branch=state, source_branch_fingerprint=fingerprint(state), incoming_authority=incoming)
        if materialized.get("status") != "resolved": return materialized
        next_state = materialized["next_state"]
        _carry_lifecycle(state, next_state, side, incoming["owner"])
        retired.append({"outgoing_active": outgoing, "condition_context": deepcopy(state["current_state"].get("condition_context")),
                        "historical_toxic_lifecycle": deepcopy(state.get("predicted_toxic_lifecycle")),
                        "toxic_progression": {"status": "unknown", "reason": "switch_retirement"},
                        "replacement_kind": "faint_replacement"})
        next_state.setdefault("post_eot_bench_records", []).append(deepcopy(retired[-1]))
        state = next_state
    result = deepcopy(transition)
    result.update(status="entry_pending", state=state, entrants=entrants, entry_order=tuple(order),
                  entry_queue=tuple((phase, s) for phase in ("hazards", "abilities") for s in order), entry_results=(), retired_actives=tuple(retired),
                  history=(*transition["history"], deepcopy(command)))
    result["entry_state_fingerprint"] = fingerprint(state)
    return result


def advance_post_eot_entry(*, transition, entry_authority):
    """Run one bound mechanics step; return the next cursor/request/boundary."""
    if validate_post_eot_transition(transition=transition).get("status") != "valid":
        return _error("rejected", "invalid_entry_cursor")
    command = {"kind": "entry", "entry_authority": deepcopy(entry_authority)}
    try: return _advance(transition, entry_authority, command)
    except (KeyError, TypeError, ValueError, AttributeError): return _error("rejected", "malformed_entry_step")


def post_eot_entry_binding(transition):
    phase, side = transition["entry_queue"][0]
    return {"request_id": transition["request_id"], "source_branch_fingerprint": fingerprint(transition["state"]),
            "phase": phase, "side": side, "owner": _owner(transition["state"]["active"][side])}


def _advance(transition, authority, command):
    if transition["status"] != "entry_pending" or not transition["entry_queue"]:
        return _error("rejected", "entry_step_not_requested")
    binding = post_eot_entry_binding(transition)
    if not isinstance(authority, Mapping) or authority.get("source_binding") != binding:
        return _error("rejected", "stale_or_foreign_entry_step")
    state = transition["state"]
    phase, side = transition["entry_queue"][0]
    mechanics = authority.get("mechanics")
    if not isinstance(mechanics, Mapping): return _error("incomplete", "entry_mechanics_missing")
    error = _check_entry(mechanics, state, side, transition["entrants"][side])
    if error: return _error("rejected", error)
    if phase == "hazards":
        materialized = {"status": "resolved", "next_state": state, "resulting_branch_fingerprint": fingerprint(state)}
        executed = execute_materialized_switch_entry(materialized_switch=materialized, entry_authority=mechanics, defer_abilities=True)
    else:
        executed = execute_materialized_entry_abilities(branch_state=state, source_branch_fingerprint=fingerprint(state), entry_authority=mechanics)
    if executed.get("status") != "resolved" and executed.get("reason") != "replacement_required_after_entry_hazard_ko":
        return executed
    result = deepcopy(transition)
    result["state"] = executed["next_state"]
    # Preserve both sides' hazards; the legacy single-side context is also
    # retained for existing consumers and updated after absorption.
    if phase == "hazards":
        result["state"].setdefault("post_eot_side_hazards", {})[side] = deepcopy(executed["next_state"]["branch_side_hazard_context"])
        previous = result["state"].get("post_eot_hazard_authorities", {}).get(side)
        if isinstance(previous, dict):
            previous.update(executed["next_state"]["branch_side_hazard_context"]["hazards"])
        toxic = executed.get("entry_effect_result", {}).get("toxic_spikes_result", {})
        overlay = result["state"].get("predicted_condition_context")
        if toxic.get("outcome") == "status_applied" and isinstance(overlay, Mapping) and overlay.get("owner") == _owner(result["state"]["active"][side]):
            result["state"].setdefault("post_eot_condition_overlays", {})[side] = deepcopy(overlay)
            if toxic.get("post_condition") == "toxic":
                result["state"].setdefault("post_eot_toxic_lifecycles", {})[side] = deepcopy(result["state"].get("predicted_toxic_lifecycle"))
                lifecycle = result["state"]["predicted_toxic_lifecycle"]
                result["state"]["post_eot_toxic_progression"][side] = {
                    "owner": deepcopy(overlay["owner"]), "authority": {"status": "known", "next_stage": lifecycle["current_stage"],
                    "source_entry_fingerprint": fingerprint(executed["next_state"]), "provenance": "canonical_predicted_toxic_spikes_lifecycle"}}
            for row in result["state"]["current_state"]["condition_context"]["current_conditions"]:
                if row.get("side") == side:
                    row.update(condition_type=toxic["post_condition"], status="predicted", source="detached_post_eot_entry_projection")
    result["entry_state_fingerprint"] = fingerprint(result["state"])
    _sync_direct_projection(result["state"])
    result["entry_state_fingerprint"] = fingerprint(result["state"])
    result["entry_queue"] = transition["entry_queue"][1:]
    result["entry_results"] = (*transition["entry_results"], {"phase": phase, "side": side, "result": deepcopy(executed)})
    result["history"] = (*transition["history"], deepcopy(command))
    if result["entry_queue"]: return result
    teams = deepcopy(result["teams"])
    for side in SIDES:
        if not isinstance(teams.get(side), Mapping) or teams[side].get("status") != "known": continue
        teams[side]["detached_entry_projection"] = {"source_request_id": transition["request_id"],
                                                    "source_entry_fingerprint": fingerprint(result["state"]),
                                                    "provenance": "replayed_post_eot_entry_roster_hp_v1"}
        for member in teams[side]["members"]:
            active = result["state"]["active"][side]
            if member["owner"] == _owner(active):
                member["hp"] = {"status": "known", "current_hp": active["current_hp"], "maximum_hp": active["max_hp"]}
    return _request(result["source"], result["state"], teams, result["history"], result["generation"] + 1)


_SIDE_CONTEXTS = {"current_hp_context": "current_hp", "condition_context": "current_conditions", "ability_context": "current_abilities",
                  "item_context": "current_items", "stat_stage_context": "current_stages", "current_type_context": "current_types"}


def _merge_current(current, incoming, side):
    """Splice only the selected identity's facts; retain opposing/shared state."""
    retained_keys = {*_SIDE_CONTEXTS, "current_state_session_id", "field_state_context", "direct_mechanics_context",
                     "current_taunt_restrictions", "current_encore_restrictions", "current_disable_restrictions"}
    result = {k: deepcopy(v) for k, v in current.items() if k in retained_keys}
    for key, rows_key in _SIDE_CONTEXTS.items():
        supplied = incoming.get(key, {}).get(rows_key, ())
        retained = current.get(key, {}).get(rows_key, ())
        rows = [deepcopy(row) for row in retained if row.get("side") != side]
        rows += [deepcopy(row) for row in supplied if row.get("side") == side]
        result[key] = {rows_key: rows}
    direct = result.get("direct_mechanics_context")
    if isinstance(direct, dict):
        role = "attacker" if side == "self" else "defender"
        candidate = incoming.get("direct_mechanics_context", {}).get(role)
        if candidate is None: direct.pop(role, None)
        else: direct[role] = deepcopy(candidate)
    # Other incoming fields are not promoted into shared battle authority.
    for key in ("current_taunt_restrictions", "current_encore_restrictions", "current_disable_restrictions"):
        rows = result.get(key)
        if isinstance(rows, dict): rows.pop(side, None)
    return result


def _carry_lifecycle(source, destination, side, incoming_owner):
    for key in ("branch_field_weather_context", "branch_side_hazard_context", "post_eot_side_hazards", "post_eot_hazard_authorities", "post_eot_bench_records"):
        if key in source: destination[key] = deepcopy(source[key])
    for key in ("post_eot_condition_overlays", "post_eot_toxic_lifecycles"):
        if isinstance(source.get(key), Mapping):
            destination[key] = {s: deepcopy(row) for s, row in source[key].items() if s != side}
    if isinstance(source.get("post_eot_toxic_progression"), Mapping):
        destination["post_eot_toxic_progression"] = deepcopy(source["post_eot_toxic_progression"])
        destination["post_eot_toxic_progression"][side] = {"owner": deepcopy(incoming_owner), "authority": {"status": "unknown", "reason": "switch_lifecycle_invalidates_counter"}}
    for key in ("predicted_condition_context", "predicted_toxic_lifecycle"):
        value = source.get(key)
        if isinstance(value, Mapping) and value.get("owner", {}).get("side") != side:
            destination[key] = deepcopy(value)
    for key in ("branch_persistent_effect_authority", "leech_seed_persistent_effect_context"):
        context = source.get(key)
        if not isinstance(context, Mapping): continue
        copied = deepcopy(context)
        for row in copied.get("states", ()):
            if row.get("owner", {}).get("side") == side:
                row["owner"] = deepcopy(incoming_owner)
                row["state"] = "known_inactive" if row.get("state") in {"known_active", "known_inactive"} else "unknown"
                row.pop("source_slot", None)
            elif row.get("source_slot", {}).get("side") == side:
                # A source slot names the current occupant of the same singles
                # field position. Keep the historical binding as provenance.
                row.setdefault("historical_source_slot", deepcopy(row["source_slot"]))
                row["source_slot"] = {k: incoming_owner[k] for k in ("session_id", "side", "slot_index")}
        copied["source_branch_fingerprint"] = fingerprint(source)
        destination[key] = copied


def _check_entry(mechanics, state, side, member):
    target = mechanics.get("target_roster_mechanics")
    active = state["active"][side]
    if not isinstance(target, Mapping) or _owner(target) != _owner(active): return "entry_target_identity_mismatch"
    hp = target.get("hp_authority", {})
    if hp.get("status") != "known" or hp.get("current_hp") != active["current_hp"] or hp.get("maximum_hp") != active["max_hp"]: return "entry_target_hp_mismatch"
    for key in ("item_authority", "ability_authority", "current_type_authority", "prospective_groundedness_authority"):
        if target.get(key) != member.get("entry_mechanics", {}).get(key): return "entry_candidate_facts_mismatch"
    expected = deepcopy(member.get("entry_mechanics"))
    if not isinstance(expected, dict): return "entry_candidate_facts_missing"
    expected["hp_authority"] = {"status": "known", "current_hp": active["current_hp"], "maximum_hp": active["max_hp"]}
    stages = {r["stat"]: r["stage"] for r in state["current_state"].get("stat_stage_context", {}).get("current_stages", ()) if r.get("side") == side}
    if "speed" in stages: expected["prospective_speed_stage_authority"] = {"status": "known", "value": stages["speed"]}
    if all(s in stages for s in ("attack", "special-attack")):
        expected["prospective_offensive_stages_authority"] = {s: stages[s] for s in ("attack", "special-attack")}
    conditions = [r.get("condition_type") for r in state["current_state"].get("condition_context", {}).get("current_conditions", ()) if r.get("side") == side]
    if len(conditions) == 1: expected["persistent_condition_authority"] = {"status": "known", "value": conditions[0]}
    if target != expected: return "entry_candidate_dynamic_facts_mismatch"
    hazards = mechanics.get("hazards")
    if not isinstance(hazards, Mapping) or hazards.get("session_id") != active["session_id"] or hazards.get("affected_side") != side: return "entry_hazard_side_mismatch"
    if hazards != state.get("post_eot_hazard_authorities", {}).get(side): return "entry_hazard_generation_mismatch"
    field = state["current_state"].get("field_state_context")
    if mechanics.get("field_state_context") != field: return "entry_field_generation_mismatch"
    other = "opponent" if side == "self" else "self"
    for key in ("intimidate_authority", "download_authority"):
        authority = mechanics.get(key)
        if authority is not None and authority.get("target") != {k: state["active"][other][k] for k in ("side", "slot_index", "pokemon_id")}:
            return "entry_opponent_identity_mismatch"
    return None


def _check_incoming(member):
    incoming, mechanics = member["incoming_authority"], member.get("entry_mechanics")
    if not isinstance(mechanics, Mapping) or _owner(mechanics) != member["owner"]: return True
    current = incoming.get("current_state", {})
    side = member["owner"]["side"]
    hp = [r for r in current.get("current_hp_context", {}).get("current_hp", ()) if r.get("side") == side]
    if len(hp) != 1 or any(hp[0].get(k) != member["hp"].get(k) for k in ("current_hp", "maximum_hp")): return True
    direct = current.get("direct_mechanics_context", {}).get("attacker" if side == "self" else "defender")
    if isinstance(direct, Mapping) and any(k in direct and direct[k] != member["hp"][v] for k, v in (("current_hp", "current_hp"), ("max_hp", "maximum_hp"))): return True
    conditions = [r for r in current.get("condition_context", {}).get("current_conditions", ()) if r.get("side") == side]
    if len(conditions) != 1 or conditions[0].get("condition_type") != mechanics.get("persistent_condition_authority", {}).get("value"): return True
    abilities = [r for r in current.get("ability_context", {}).get("current_abilities", ()) if r.get("side") == side]
    if len(abilities) != 1 or abilities[0].get("ability") != mechanics.get("ability_authority", {}).get("value"): return True
    stages = [r for r in current.get("stat_stage_context", {}).get("current_stages", ()) if r.get("side") == side]
    if len({r.get("stat") for r in stages}) != len(stages): return True
    return False


def _sync_direct_projection(state):
    """Keep an optional private calculator view consistent with entry effects."""
    current = state["current_state"]
    direct = current.get("direct_mechanics_context")
    if not isinstance(direct, dict): return
    for side, role in (("self", "attacker"), ("opponent", "defender")):
        combatant = direct.get(role)
        if not isinstance(combatant, dict): continue
        active = state["active"][side]
        combatant.update(current_hp=active["current_hp"], max_hp=active["max_hp"])
        boosts = combatant.get("boosts")
        if isinstance(boosts, dict):
            for row in current.get("stat_stage_context", {}).get("current_stages", ()):
                if row.get("side") == side and row.get("stat") in boosts:
                    boosts[row["stat"]] = row["stage"]
