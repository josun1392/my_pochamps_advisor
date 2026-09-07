"""Exact Champions current-action sleep/freeze authority and detached views."""
from copy import deepcopy
from fractions import Fraction
from typing import Mapping

from llm.advisor_champions_status_progression import valid_progression

SCHEMA = "champions-sleep-freeze-action-gate-v1"
SELF_THAW_MOVES = frozenset({"burn-up", "flame-wheel", "flare-blitz", "fusion-flare", "matcha-gotcha", "pyro-ball", "sacred-fire", "scald", "scorching-sands", "steam-eruption"})
SLEEP_EXCEPTIONS = frozenset({"sleep-talk", "snore"})


def fd(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def fraction(value):
    return Fraction(value["numerator"], value["denominator"])


def classify_status_move(move_id):
    if not isinstance(move_id, str) or not move_id:
        return {"status": "rejected", "reason": "status_gate_move_identity_missing"}
    return {"status": "resolved", "move_id": move_id, "self_thaw": move_id in SELF_THAW_MOVES,
            "sleep_exception": move_id in SLEEP_EXCEPTIONS, "target_thaw": "separate_effect_not_authorized_by_user_gate",
            "provenance": "t2_verified_champions_status_move_catalog_v1"}


def resolve_gate_branches(*, condition, progression, ability, move_authority):
    """Pure, replayable typed branch contract, with exact rational weights."""
    if condition not in {"sleep", "freeze"}:
        return [_branch("executes", Fraction(1), condition, None)]
    if not isinstance(progression, Mapping):
        return {"status": "incomplete", "reason": "champions_status_progression_missing"}
    if move_authority != classify_status_move(move_authority.get("move_id")):
        return {"status": "rejected", "reason": "forged_status_move_exception"}
    n = progression["prior_attempts"] + 1
    if condition == "freeze":
        if move_authority["self_thaw"]:
            return [_branch("self_thaw_move_executes", Fraction(1), "none", None, attempt=n)]
        if n == 3:
            return [_branch("thaws_and_executes", Fraction(1), "none", None, attempt=n)]
        after = {**deepcopy(progression), "prior_attempts": n}
        return [_branch("thaws_and_executes", Fraction(1, 4), "none", None, attempt=n),
                _branch("cancelled_freeze", Fraction(3, 4), "freeze", after, attempt=n)]
    if ability.get("status") != "resolved" or type(ability.get("early_bird_active")) is not bool:
        return {"status": "incomplete", "reason": "early_bird_applicability_unknown"}
    chosen = progression.get("sleep_duration")
    def adjusted(duration):
        return progression.get("adjusted_duration", duration // 2 if ability["early_bird_active"] else duration)
    choices = [(chosen, Fraction(1))] if chosen is not None else [(2, Fraction(1, 3)), (3, Fraction(2, 3))]
    # Conditioning on a known still-asleep history eliminates durations that
    # would already have woken; a selected branch duration is never rerolled.
    choices = [(d, p) for d, p in choices if adjusted(d) > progression["prior_attempts"]]
    if not choices:
        return {"status": "rejected", "reason": "sleep_progression_past_selected_duration"}
    mass = sum((p for _, p in choices), Fraction())
    rows = []
    for duration, weight in choices:
        effective = adjusted(duration)
        awake = n >= effective
        kind = "wakes_and_executes" if awake else "move_specific_sleep_exception_executes" if move_authority["sleep_exception"] else "cancelled_sleep"
        adjustment = deepcopy(progression.get("duration_adjustment", ability))
        after = None if awake else {**deepcopy(progression), "prior_attempts": n, "sleep_duration": duration,
                                   "adjusted_duration": effective, "duration_adjustment": adjustment}
        rows.append(_branch(kind, weight / mass, "none" if awake else "sleep", after, attempt=n,
                            sleep_duration=duration, adjusted_duration=effective, duration_adjustment=adjustment,
                            duration_identity=f"{progression['origin_id']}:duration:{duration}"))
    return rows


def _branch(kind, probability, condition, progression, **extra):
    return {"kind": kind, "executes": not kind.startswith("cancelled_"), "probability": fd(probability),
            "condition_after": condition, "progression_after": deepcopy(progression), **extra}


def freeze_champions_status_action_gate(*, strategy_d0, runtime_snapshot, actor, action_id, move_id, action_order, path=()):
    from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness, freeze_runtime_current_condition_authority
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return {"status": "rejected", "reason": "stale_champions_status_gate_d0"}
    if actor not in strategy_d0.get("active_owners", {}).values() or not isinstance(action_id, str) or not action_id:
        return {"status": "rejected", "reason": "champions_status_gate_actor_action_invalid"}
    status = freeze_runtime_current_condition_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=actor)
    known = status.get("condition", {})
    condition = "none" if known.get("status") == "known_none" else known.get("condition") if known.get("status") == "known_present" else None
    if condition is None:
        return {"status": "incomplete", "reason": "champions_status_gate_condition_unknown"}
    raw = runtime_snapshot["state"][f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]
    if raw.get("fainted") is True or raw.get("current_hp") == 0:
        return {"status": "rejected", "reason": "fainted_actor_has_no_status_attempt"}
    progression = raw.get("champions_status_progression") if condition in {"sleep", "freeze"} else None
    if condition in {"sleep", "freeze"}:
        if progression is None:
            return {"status": "incomplete", "reason": "champions_status_progression_missing"}
        if not valid_progression(progression, actor) or progression.get("condition") != condition or progression.get("condition_observation") != raw.get("condition_provenance"):
            return {"status": "rejected", "reason": "champions_status_progression_foreign_or_stale"}
    abilities = {}
    for side, owner in strategy_d0["active_owners"].items():
        member = runtime_snapshot["state"][f"{side}_side"]["pokemon"][owner["slot_index"]]
        abilities[side] = member.get("current_ability")
    exact = all(isinstance(a, str) and a for a in abilities.values())
    gas = "neutralizing-gas" in abilities.values()
    ability = {"status": "resolved" if exact else "incomplete", "holder": deepcopy(actor), "ability_id": abilities.get(actor["side"]),
               "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
               "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "path": deepcopy(tuple(path)),
               "abilities": deepcopy(abilities), "suppressed": gas, "early_bird_active": exact and abilities.get(actor["side"]) == "early-bird" and not gas}
    move = classify_status_move(move_id)
    if move.get("status") != "resolved": return move
    branches = resolve_gate_branches(condition=condition, progression=progression, ability=ability, move_authority=move)
    if isinstance(branches, Mapping): return dict(branches)
    for i, row in enumerate(branches): row["branch_id"] = f"{action_id}:status:{i}:{row['kind']}"
    return {"status": "resolved", "schema_version": SCHEMA, "session_id": strategy_d0["session_id"],
            "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
            "actor": deepcopy(actor), "action_id": action_id, "move_id": move_id, "condition": condition,
            "condition_authority": status, "progression": deepcopy(progression), "ability_authority": ability,
            "move_authority": move, "action_order": deepcopy(action_order), "path": deepcopy(tuple(path)),
            "branches": tuple(branches), "root_probability_mass": fd(Fraction(1)), "provenance": "champions_exact_status_action_gate_v1"}


def validate_status_gate(authority):
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA or authority.get("status") != "resolved":
        return False
    try:
        condition = authority["condition"]
        status = authority["condition_authority"]
        if status.get("owner") != authority["actor"] or any(status.get(k) != authority.get(k) for k in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")):
            return False
        known = status.get("condition", {})
        if condition != ("none" if known.get("status") == "known_none" else known.get("condition")):
            return False
        progression = authority["progression"]
        if condition in {"sleep", "freeze"} and (not valid_progression(progression, authority["actor"]) or progression["condition"] != condition): return False
        ability = authority["ability_authority"]
        if any(ability.get(key) != authority.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "path")): return False
        abilities = ability["abilities"]
        if not isinstance(abilities, Mapping) or set(abilities) != {"self", "opponent"}: return False
        if ability["status"] != ("resolved" if all(isinstance(value, str) and value for value in abilities.values()) else "incomplete"): return False
        if ability["holder"] != authority["actor"] or ability["ability_id"] != abilities[authority["actor"]["side"]] or ability["suppressed"] != ("neutralizing-gas" in abilities.values()): return False
        if ability["early_bird_active"] != (ability["status"] == "resolved" and ability["ability_id"] == "early-bird" and not ability["suppressed"]): return False
        expected = resolve_gate_branches(condition=condition, progression=progression, ability=ability, move_authority=authority["move_authority"])
        if isinstance(expected, Mapping) or authority["move_authority"] != classify_status_move(authority["move_id"]): return False
        for i, row in enumerate(expected): row["branch_id"] = f"{authority['action_id']}:status:{i}:{row['kind']}"
        return tuple(expected) == authority["branches"] and sum((fraction(r["probability"]) for r in expected), Fraction()) == 1 and authority["root_probability_mass"] == fd(Fraction(1))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False


def materialize_status_gate_branch(*, strategy_d0, runtime_snapshot, authority, branch):
    from llm.advisor_reducer_state_model import state_fingerprint
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
    if not validate_status_gate(authority) or branch not in authority["branches"]:
        return {"status": "rejected", "reason": "invalid_champions_status_gate_branch"}
    expected = freeze_champions_status_action_gate(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, actor=authority["actor"], action_id=authority["action_id"], move_id=authority["move_id"], action_order=authority["action_order"], path=authority["path"])
    if expected != authority: return {"status": "rejected", "reason": "foreign_champions_status_gate_branch"}
    state = deepcopy(runtime_snapshot["state"])
    actor = authority["actor"]
    raw = state[f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]
    if authority["condition"] in {"sleep", "freeze"}:
        raw["condition"] = branch["condition_after"]
        raw["champions_status_progression"] = deepcopy(branch["progression_after"])
        if branch["condition_after"] == "none":
            raw["condition_provenance"] = {**deepcopy(raw["condition_provenance"]), "condition": "none", "hypothetical_provenance": "champions_status_gate_clear_v1"}
    # Exact sleep/freeze is retained for status-sensitive reads on the target.
    # This tag only admits the absence of a direct damage modifier for them.
    for owner in strategy_d0["active_owners"].values():
        state[f"{owner['side']}_side"]["pokemon"][owner["slot_index"]]["detached_champions_status_gate_view"] = True
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    return {"status": "resolved", "hypothetical": True, "strategy_d0": d0, "runtime_snapshot": snapshot,
            "condition_before": authority["condition"], "condition_after": branch["condition_after"],
            "authority": deepcopy(authority), "branch": deepcopy(branch), "provenance": "detached_champions_status_gate_branch_v1"}
