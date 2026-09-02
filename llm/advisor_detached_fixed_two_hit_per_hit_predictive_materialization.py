"""Exact detached leaves for the bounded fixed-two-hit execution family."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_predictive_critical_damage_context import materialize_predictive_critical_damage_contexts
from llm.advisor_predictive_damage_roll_uncertainty import project_predictive_damage_roll_uncertainty
from llm.advisor_predictive_normal_formula_post_hit import compose_predictive_normal_formula_post_hit
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fixed_two_hit_multi_hit_execution_authority import SCHEMA_VERSION as EXECUTION_SCHEMA
from llm.advisor_runtime_d0_contact_reactive_damage_authority import (
    freeze_runtime_d0_contact_reactive_damage_authority,
    materialize_detached_contact_reactive_damage,
)
from llm.advisor_runtime_d0_contact_reactive_status_authority import (
    condition_from_overlay,
    contact_reactive_status_branches,
    freeze_runtime_d0_contact_reactive_status_authority,
)
from llm.advisor_runtime_d0_life_orb_immediate_authority import apply_life_orb_recoil_to_consequences
from llm.advisor_focus_sash_survival import focus_sash_state
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    build_runtime_d0_strict_hit_probability_assessment,
    freeze_runtime_normal_formula_predictive_input,
    freeze_runtime_strategy_d0,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "detached-fixed-two-hit-per-hit-predictive-materialization-v1"
HORIZON = "immediate_action_consequence"


def materialize_detached_fixed_two_hit_per_hit_predictive_leaves(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any], execution_authority: Mapping[str, Any],
    sturdy_survival_authority: Mapping[str, Any] | None = None,
    focus_sash_survival_authority: Mapping[str, Any] | None = None,
    contact_reactive_contact_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize ordered hit leaves without mutating current D0/runtime.

    Accuracy is an action-level branch.  Each landed hit then receives its own
    strict crit and 16-roll branch, while the second hit is calculated from a
    private exact post-first-hit snapshot.
    """
    base = _base(strategy_d0, action, execution_authority)
    if base is None:
        return _result("rejected", "invalid_fixed_two_hit_materialization_request", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    metadata = execution_authority["move_metadata_authority"]["metadata"]
    single = _single_hit_metadata(metadata)
    if single is None:
        return _result("rejected", "fixed_two_hit_single_hit_metadata_adapter_invalid", base)
    hit = build_runtime_d0_strict_hit_probability_assessment(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=base["attacker"], target=base["target"], selected_move=single,
    )
    if hit.get("status") != "resolved":
        return _result(hit.get("status", "rejected"), hit.get("reason", "fixed_two_hit_action_accuracy_unavailable"), base)
    probability = hit.get("probability_percent")
    if not isinstance(probability, int) or isinstance(probability, bool) or not 0 <= probability <= 100:
        return _result("rejected", "fixed_two_hit_action_accuracy_invalid", base)
    leaves: list[dict[str, Any]] = []
    miss_probability = Fraction(100 - probability, 100)
    target_hp = strategy_d0["strategy_state"]["active"][base["target"]["side"]]["current_hp"]
    if miss_probability:
        leaves.append(_leaf(base, "miss", miss_probability, (), target_hp, _sturdy_state(sturdy_survival_authority, consumed=False), focus_sash_state(focus_sash_survival_authority, consumed=False)))
    hit_probability = Fraction(probability, 100)
    if hit_probability:
        first = _hit_events(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
            single_metadata=single, sturdy_survival_authority=sturdy_survival_authority,
            focus_sash_survival_authority=focus_sash_survival_authority,
            attacker_hp_authority=_path_attacker_hp_authority(runtime_snapshot, base["attacker"], base["own_current_hp"]),
            low_hp_source_hit={"hit_index": 1, "path_id": "fixed-two-hit:hit:1"},
            attacker_condition_authority=_guts_path_condition_authority(strategy_d0, base, base["attacker_condition"]),
        )
        if isinstance(first, Mapping):
            return _result(first["status"], first["reason"], base)
        for first_event in first:
            first_event = deepcopy(dict(first_event)); first_event["hit_index"] = 1
            first_probability = hit_probability * first_event["probability"]
            first_reactive = _apply_reactive(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base, action=action,
                contact_authority=contact_reactive_contact_authority, event=first_event,
                hit_index=1, attacker_hp=base["own_current_hp"],
            )
            if isinstance(first_reactive, Mapping) and first_reactive.get("status") != "resolved":
                return _result(first_reactive.get("status", "rejected"), first_reactive.get("reason", "fixed_two_hit_contact_reactive_damage_unavailable"), base)
            first_attacker_hp = first_reactive["post_hp"] if isinstance(first_reactive, Mapping) else base["own_current_hp"]
            first_event = _event_with_reactive(first_event, first_reactive)
            first_status_branches = _apply_reactive_status(
                strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base, action=action,
                contact_authority=contact_reactive_contact_authority, event=first_event,
                hit_index=1, condition_state="none", attacker_fainted=first_attacker_hp == 0,
            )
            if isinstance(first_status_branches, Mapping):
                return _result(first_status_branches.get("status", "rejected"), first_status_branches.get("reason", "fixed_two_hit_contact_reactive_status_unavailable"), base)
            for first_status in first_status_branches:
                first_status_probability = first_probability * first_status["factor"]
                first_event_with_status = _event_with_reactive_status(first_event, first_status)
                first_condition = first_status["post_condition"]
                if first_event["post_hp"] == 0 or first_attacker_hp == 0:
                    reason = "target_fainted" if first_event["post_hp"] == 0 else "attacker_fainted_from_contact_reactive_damage"
                    leaf = _leaf(base, "hit", first_status_probability, (first_event_with_status,), first_event["post_hp"], _sturdy_state(sturdy_survival_authority, consumed=first_event["sturdy_applied"]), focus_sash_state(focus_sash_survival_authority, consumed=first_event["focus_sash_applied"]), own_final_hp=first_attacker_hp, terminal_reason=reason)
                    if first_attacker_hp != 0:
                        leaf = _apply_life_orb_to_leaf(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base, action=action, move_metadata=metadata, leaf=leaf)
                        if leaf.get("status") in {"incomplete", "unsupported", "rejected"}:
                            return _result(leaf.get("status", "rejected"), leaf.get("reason", "fixed_two_hit_life_orb_recoil_unavailable"), base)
                    leaves.append(leaf)
                    continue
                second_d0, second_snapshot = _detached_target_hp_view(
                    runtime_snapshot=runtime_snapshot, decision_owner=base["attacker"],
                    target=base["target"], target_hp=first_event["post_hp"],
                    focus_sash_consumed=first_event["focus_sash_applied"],
                )
                if second_d0 is None:
                    return _result("rejected", "fixed_two_hit_intermediate_target_state_invalid", base)
                second_sturdy = sturdy_survival_authority if (
                    first_event["post_hp"] == first_event["target_max_hp"] and not first_event["sturdy_applied"]
                ) else None
                second_focus_sash = focus_sash_survival_authority if (
                    first_event["post_hp"] == first_event["target_max_hp"] and not first_event["focus_sash_applied"]
                ) else None
                second = _hit_events(
                    strategy_d0=second_d0, runtime_snapshot=second_snapshot, base=base,
                    single_metadata=single, sturdy_survival_authority=second_sturdy,
                    focus_sash_survival_authority=second_focus_sash,
                    attacker_hp_authority=_path_attacker_hp_authority(runtime_snapshot, base["attacker"], first_attacker_hp),
                    low_hp_source_hit={"hit_index": 2, "path_id": "fixed-two-hit:hit:2"},
                    attacker_condition_authority=_guts_path_condition_authority(second_d0, base, first_condition),
                )
                if isinstance(second, Mapping):
                    return _result(second["status"], second["reason"], base)
                for second_event in second:
                    second_event = deepcopy(dict(second_event)); second_event["hit_index"] = 2
                    second_reactive = _apply_reactive(
                        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base, action=action,
                        contact_authority=contact_reactive_contact_authority, event=second_event,
                        hit_index=2, attacker_hp=first_attacker_hp,
                    )
                    if isinstance(second_reactive, Mapping) and second_reactive.get("status") != "resolved":
                        return _result(second_reactive.get("status", "rejected"), second_reactive.get("reason", "fixed_two_hit_contact_reactive_damage_unavailable"), base)
                    second_attacker_hp = second_reactive["post_hp"] if isinstance(second_reactive, Mapping) else first_attacker_hp
                    second_event = _event_with_reactive(second_event, second_reactive)
                    second_status_branches = _apply_reactive_status(
                        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base, action=action,
                        contact_authority=contact_reactive_contact_authority, event=second_event,
                        hit_index=2, condition_state=first_condition, attacker_fainted=second_attacker_hp == 0,
                    )
                    if isinstance(second_status_branches, Mapping):
                        return _result(second_status_branches.get("status", "rejected"), second_status_branches.get("reason", "fixed_two_hit_contact_reactive_status_unavailable"), base)
                    for second_status in second_status_branches:
                        second_event_with_status = _event_with_reactive_status(second_event, second_status)
                        reason = "target_fainted" if second_event["post_hp"] == 0 else "attacker_fainted_from_contact_reactive_damage" if second_attacker_hp == 0 else "all_hits_landed"
                        leaf = _leaf(
                            base, "hit", first_status_probability * second_event["probability"] * second_status["factor"],
                            (first_event_with_status, second_event_with_status), second_event["post_hp"],
                            _sturdy_state(sturdy_survival_authority, consumed=first_event["sturdy_applied"] or second_event["sturdy_applied"]),
                            focus_sash_state(focus_sash_survival_authority, consumed=first_event["focus_sash_applied"] or second_event["focus_sash_applied"]),
                            own_final_hp=second_attacker_hp,
                            terminal_reason=reason,
                        )
                        if second_attacker_hp != 0:
                            leaf = _apply_life_orb_to_leaf(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base, action=action, move_metadata=metadata, leaf=leaf)
                            if leaf.get("status") in {"incomplete", "unsupported", "rejected"}:
                                return _result(leaf.get("status", "rejected"), leaf.get("reason", "fixed_two_hit_life_orb_recoil_unavailable"), base)
                        leaves.append(leaf)
            continue
    mass = sum((row["probability"] for row in leaves), Fraction())
    if mass != Fraction(1, 1):
        return _result("rejected", "fixed_two_hit_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        **base, "action_accuracy": deepcopy(hit), "single_hit_metadata_view": single,
        "terminal_leaves": tuple(_serialize_leaf(row) for row in leaves),
        "terminal_probability_mass": _fd(mass),
        "aggregation": "none_preserve_ordered_per_hit_critical_and_roll_identity",
        "provenance": "fixed_two_hit_execution_authority_to_detached_ordered_per_hit_leaves_v1",
    }


def _hit_events(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], single_metadata: Mapping[str, Any], sturdy_survival_authority: Mapping[str, Any] | None, focus_sash_survival_authority: Mapping[str, Any] | None = None, attacker_hp_authority: Mapping[str, Any] | None = None, low_hp_source_hit: Mapping[str, Any] | None = None, attacker_condition_authority: Mapping[str, Any] | None = None) -> list[dict[str, Any]] | dict[str, str]:
    if attacker_hp_authority is None:
        attacker_hp_authority = _path_attacker_hp_authority(runtime_snapshot, base["attacker"], base["own_current_hp"])
    if attacker_hp_authority is None:
        return {"status": "incomplete", "reason": "per_hit_attacker_hp_authority_unavailable"}
    native = build_runtime_d0_native_damage_context(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=base["attacker"], target=base["target"], move_metadata=single_metadata,
        attacker_hp_authority=attacker_hp_authority, low_hp_source_hit=low_hp_source_hit,
        attacker_condition_authority=attacker_condition_authority,
    )
    normal = freeze_runtime_normal_formula_predictive_input(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=base["attacker"], target=base["target"], move_metadata=single_metadata, native_damage_context=native)
    if normal.get("status") != "resolved":
        return {"status": normal.get("status", "rejected"), "reason": normal.get("reason", "fixed_two_hit_normal_formula_input_unavailable")}
    paired = materialize_predictive_critical_damage_contexts(
        branch_state=strategy_d0["strategy_state"], decision_owner=base["attacker"], target_owner=base["target"],
        snapshot_damage_input=normal["snapshot_damage_input"], stat_provenance=normal["stat_provenance"],
        trusted_level=normal["trusted_level"], source_runtime_fingerprint=strategy_d0["source_runtime_fingerprint"],
    )
    if paired.get("status") != "resolved":
        return {"status": paired.get("status", "rejected"), "reason": paired.get("reason", "fixed_two_hit_critical_damage_context_unavailable")}
    low_hp = native.get("native_evaluation", {}).get("low_hp_type_ability_evidence") if isinstance(native.get("native_evaluation"), Mapping) else None
    critical = base["per_hit_critical_execution"]["per_hit_critical_probability"]
    try:
        critical_probability = Fraction(critical["numerator"], critical["denominator"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return {"status": "rejected", "reason": "fixed_two_hit_critical_probability_invalid"}
    contexts = (("non_critical", Fraction(1, 1) - critical_probability, paired["non_critical_context"]), ("critical", critical_probability, paired["critical_context"]))
    events: list[dict[str, Any]] = []
    for critical_state, critical_factor, interval in contexts:
        if not critical_factor:
            continue
        post = compose_predictive_normal_formula_post_hit(
            interval=interval, move_metadata=single_metadata, attacker_hp=normal["post_hit_authority"]["attacker_hp"],
            attacker_item=None, attacker_ability=normal["post_hit_authority"]["attacker_ability"],
            target_ability=normal["post_hit_authority"]["target_ability"], attacker_item_known=normal["post_hit_authority"]["attacker_item_known"],
            target_sturdy_survival_authority=sturdy_survival_authority,
            target_focus_sash_survival_authority=focus_sash_survival_authority,
        )
        if post.get("status") != "resolved":
            return {"status": post.get("status", "rejected"), "reason": post.get("reason", "fixed_two_hit_post_hit_unavailable")}
        rolls = project_predictive_damage_roll_uncertainty(interval=interval, post_hit=post)
        if rolls.get("status") != "resolved":
            return {"status": rolls.get("status", "rejected"), "reason": rolls.get("reason", "fixed_two_hit_roll_authority_unavailable")}
        for roll in rolls["outcomes"]:
            post_row = roll.get("post_hit_consequence")
            if not isinstance(post_row, Mapping) or not isinstance(post_row.get("raw_damage"), int) or not isinstance(post_row.get("actual_damage"), int):
                return {"status": "rejected", "reason": "fixed_two_hit_post_hit_roll_binding_invalid"}
            before = interval.get("target_hp_before")
            actual = post_row["actual_damage"]
            if not isinstance(before, int) or isinstance(before, bool) or before < 0 or actual < 0 or actual > before:
                return {"status": "rejected", "reason": "fixed_two_hit_target_hp_transition_invalid"}
            sturdy = post_row.get("sturdy_survival")
            focus = post_row.get("focus_sash_survival")
            events.append({
                "probability": critical_factor * Fraction(1, 16), "critical_state": critical_state,
                "roll_index": roll["roll_index"], "random_factor_percent": roll["random_factor_percent"],
                "raw_damage": post_row["raw_damage"], "actual_damage": actual, "pre_hp": before,
                "post_hp": before - actual, "target_max_hp": before if sturdy_survival_authority is not None or focus_sash_survival_authority is not None else None,
                "target_routing": interval.get("target_routing", "target"),
                "sturdy_applied": isinstance(sturdy, Mapping) and sturdy.get("outcome") == "applied",
                "sturdy_survival": deepcopy(dict(sturdy)) if isinstance(sturdy, Mapping) else {"outcome": "not_applicable"},
                "focus_sash_applied": isinstance(focus, Mapping) and focus.get("outcome") == "applied",
                "focus_sash_survival": deepcopy(dict(focus)) if isinstance(focus, Mapping) else {"outcome": "not_applicable"},
                **({"low_hp_type_ability": deepcopy(dict(low_hp))} if isinstance(low_hp, Mapping) else {}),
                **({"guts_status_attack_ability": deepcopy(dict(native["native_evaluation"]["guts_status_attack_ability_evidence"]))} if isinstance(native.get("native_evaluation"), Mapping) and isinstance(native["native_evaluation"].get("guts_status_attack_ability_evidence"), Mapping) else {}),
            })
    if not events or sum((row["probability"] for row in events), Fraction()) != Fraction(1, 1):
        return {"status": "rejected", "reason": "fixed_two_hit_per_hit_probability_mass_invalid"}
    return events


def _base(d0: Any, action: Any, authority: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or not isinstance(action, Mapping) or not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != EXECUTION_SCHEMA:
        return None
    expected = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": d0.get("decision_owner"), "action_id": action.get("action_id")}
    attacker = d0.get("decision_owner")
    target = d0.get("active_owners", {}).get("opponent" if isinstance(attacker, Mapping) and attacker.get("side") == "self" else "self")
    if any(authority.get(key) != value for key, value in expected.items()) or authority.get("attacker") != attacker or authority.get("target") != target or authority.get("hit_count") != 2:
        return None
    metadata = authority.get("move_metadata_authority", {}).get("metadata") if isinstance(authority.get("move_metadata_authority"), Mapping) else None
    critical = authority.get("per_hit_critical_execution")
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != action.get("identity") or not isinstance(critical, Mapping) or critical.get("semantics") != "independent_canonical_critical_roll_per_hit" or not isinstance(critical.get("per_hit_critical_probability"), Mapping):
        return None
    attacker = authority["attacker"]
    own_hp = d0.get("strategy_state", {}).get("active", {}).get(attacker["side"], {}).get("current_hp")
    if not isinstance(own_hp, int) or isinstance(own_hp, bool) or own_hp < 0:
        return None
    condition = _snapshot_attacker_condition(d0)
    if condition is None:
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "action_id": action["action_id"], "move_id": metadata["move_id"], "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(authority["target"])), "own_current_hp": own_hp, "attacker_condition": condition, "attacker_ability": _execution_attacker_ability(critical), "per_hit_critical_execution": deepcopy(dict(critical)), "execution_authority": deepcopy(dict(authority))}


def _guts_path_condition_authority(d0: Mapping[str, Any], base: Mapping[str, Any], condition: str) -> dict[str, Any] | None:
    if base.get("attacker_ability") != "guts":
        return None
    return _path_condition_authority(d0, base["attacker"], condition)


def _execution_attacker_ability(critical: Mapping[str, Any]) -> str | None:
    source = _mapping(_mapping(_mapping(critical.get("critical_hit_authority")).get("critical_hit_authority")).get("source_authority"))
    ability = _mapping(source.get("attacker_ability")).get("value")
    return ability if isinstance(ability, str) and ability else None


def _snapshot_attacker_condition(d0: Mapping[str, Any]) -> str | None:
    owner = d0.get("decision_owner")
    side = owner.get("side") if isinstance(owner, Mapping) else None
    authorities = d0.get("current_condition_authority") if isinstance(d0.get("current_condition_authority"), Mapping) else {}
    authority = authorities.get(side) if isinstance(authorities, Mapping) else None
    condition_authority = authority.get("condition") if isinstance(authority, Mapping) and authority.get("status") == "resolved" else None
    if isinstance(condition_authority, Mapping):
        if condition_authority.get("status") == "known_none":
            return "none"
        condition = condition_authority.get("condition")
        if condition_authority.get("status") == "known_present" and condition in {"paralysis", "burn", "poison", "toxic", "sleep", "freeze"}:
            return condition
    return None


def _single_hit_metadata(metadata: Mapping[str, Any]) -> dict[str, Any] | None:
    value = deepcopy(dict(metadata)); value.pop("min_hits", None); value.pop("max_hits", None)
    return value if value.get("move_id") in {"double-hit", "double-kick"} else None


def _detached_target_hp_view(*, runtime_snapshot: Mapping[str, Any], decision_owner: Mapping[str, Any], target: Mapping[str, Any], target_hp: int, focus_sash_consumed: bool = False) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not isinstance(state, Mapping) or not isinstance(target_hp, int) or target_hp < 0:
        return None, None
    synthetic = deepcopy(dict(state)); side = synthetic.get(f"{target['side']}_side"); roster = side.get("pokemon") if isinstance(side, Mapping) else None; pokemon = roster.get(target["slot_index"]) if isinstance(roster, Mapping) else None
    if not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id") != target["pokemon_id"]:
        return None, None
    pokemon["current_hp"] = target_hp; pokemon["fainted"] = target_hp == 0
    if focus_sash_consumed:
        pokemon["known_item"] = None
        pokemon["known_item_provenance"] = {"event_kind": "item_consumption_observed", "turn_number": 1, "trust": "detached_hypothetical", "source": "exact_per_hit_focus_sash_consumption"}
    snapshot = {"status": "runtime_snapshot_ready", "session_id": decision_owner["session_id"], "state": synthetic, "state_fingerprint": state_fingerprint(synthetic)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=decision_owner)
    return (d0, snapshot) if d0.get("status") == "resolved" else (None, None)


def _has_life_orb(d0: Mapping[str, Any], snapshot: Mapping[str, Any], attacker: Mapping[str, Any]) -> bool:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None; side = state.get(f"{attacker['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; pokemon = roster.get(attacker["slot_index"]) if isinstance(roster, Mapping) else None
    return isinstance(pokemon, Mapping) and pokemon.get("pokemon_id") == attacker["pokemon_id"] and pokemon.get("known_item") == "life-orb"


def _path_attacker_hp_authority(snapshot: Mapping[str, Any], attacker: Mapping[str, Any], current_hp: Any) -> dict[str, Any] | None:
    maximum = _attacker_max_hp(snapshot, attacker)
    if maximum is None or not isinstance(current_hp, int) or isinstance(current_hp, bool) or not 0 <= current_hp <= maximum:
        return None
    return {
        "status": "resolved",
        "current_hp": current_hp,
        "maximum_hp": maximum,
        "fainted": current_hp == 0,
        "provenance": "detached_path_local_attacker_hp_v1",
    }


def _apply_life_orb_to_leaf(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], action: Mapping[str, Any], move_metadata: Mapping[str, Any], leaf: Mapping[str, Any]) -> dict[str, Any]:
    if not _has_life_orb(strategy_d0, runtime_snapshot, base["attacker"]):
        return deepcopy(dict(leaf))
    hits = leaf.get("ordered_hits")
    qualifying = isinstance(hits, tuple) and any(isinstance(row, Mapping) and isinstance(row.get("actual_damage"), int) and row["actual_damage"] > 0 for row in hits)
    result = apply_life_orb_recoil_to_consequences(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=base["attacker"], target=base["target"],
        source_action=action, move_metadata=move_metadata, qualifying_damage=qualifying,
        consequences=leaf.get("consequences", {}),
    )
    if result.get("status") != "resolved":
        return result
    updated = deepcopy(dict(leaf)); updated["consequences"] = result["consequences"]; return updated


def _sturdy_state(authority: Mapping[str, Any] | None, *, consumed: bool) -> dict[str, Any]:
    return {"state": "consumed" if consumed else "ready_or_not_applicable", "authority_present": isinstance(authority, Mapping)}


def _leaf(base: Mapping[str, Any], hit_state: str, probability: Fraction, events: tuple[Mapping[str, Any], ...], target_hp: int, sturdy: Mapping[str, Any], focus_sash: Mapping[str, Any] | None = None, *, own_final_hp: int | None = None, terminal_reason: str | None = None) -> dict[str, Any]:
    path = [hit_state]
    for index, event in enumerate(events, 1): path.extend((f"hit_{index}:{event['critical_state']}", f"hit_{index}:roll:{event['roll_index']}"))
    # The fixed-two-hit authority deliberately owns no recoil, drain, or
    # self-KO behavior.  The current attacker HP is therefore an exact
    # unchanged consequence, but it must still be exposed in the common
    # terminal-leaf shape used by detached pair composition.
    own_hp = base["own_current_hp"] if own_final_hp is None else own_final_hp
    return {
        "leaf_id": "/".join(path), "candidate_id": f"attack:{base['move_id']}",
        "action_type": "attack", "branch_path": tuple(path), "hit_state": hit_state,
        "critical_state": "per_hit_independent", "damage_roll": "per_hit_independent",
        "probability": probability, "ordered_hits": tuple(deepcopy(dict(event)) for event in events),
        "consequences": {
            "own_final_hp": own_hp, "self_fainted": own_hp == 0,
            "target_final_hp": target_hp, "target_ko": target_hp == 0,
            **({"terminal_reason": terminal_reason} if terminal_reason else {}),
            "deterministic_stage_effect": None, "secondary": None,
            "sturdy": deepcopy(dict(sturdy)),
            "focus_sash": deepcopy(dict(focus_sash)) if isinstance(focus_sash, Mapping) else {"state": "not_applicable", "authority_present": False},
            "focus_sash_survival": _applied_focus_sash_survival(events),
        },
        "provenance": {
            key: deepcopy(base[key])
            for key in (
                "session_id", "source_runtime_fingerprint", "source_branch_fingerprint",
                "decision_owner", "attacker", "target", "move_id",
            )
        },
    }


def _apply_reactive(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], action: Mapping[str, Any], contact_authority: Mapping[str, Any] | None, event: Mapping[str, Any], hit_index: int, attacker_hp: int) -> dict[str, Any] | None:
    if contact_authority is None:
        return None
    source_hit = {
        "source_action_id": action["action_id"], "source_move_id": action["identity"],
        "hit_index": hit_index, "critical_state": event.get("critical_state"),
        "roll_index": event.get("roll_index"), "raw_damage": event.get("raw_damage"),
        "actual_damage": event.get("actual_damage"), "target_routing": event.get("target_routing", "target"),
        "target_pre_hp": event.get("pre_hp"), "target_post_hp": event.get("post_hp"),
    }
    maximum = _attacker_max_hp(runtime_snapshot, base["attacker"])
    if maximum is None:
        return {"status": "incomplete", "reason": "fixed_two_hit_contact_reactive_attacker_max_hp_unknown"}
    authority = freeze_runtime_d0_contact_reactive_damage_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=base["attacker"], defender=base["target"],
        source_action=action, contact_authority=contact_authority, source_hit=source_hit,
        attacker_hp_authority={"status": "resolved", "current_hp": attacker_hp, "maximum_hp": maximum, "fainted": attacker_hp == 0, "provenance": "fixed_two_hit_path_attacker_hp_v1"},
    )
    if authority.get("status") != "resolved":
        return authority
    if authority.get("outcome") != "applies":
        return {"status": "resolved", "post_hp": attacker_hp, "fainted": attacker_hp == 0, "authority": authority, "overlay": None}
    overlay = materialize_detached_contact_reactive_damage(authority=authority)
    if overlay.get("status") != "resolved":
        return overlay
    return {"status": "resolved", "post_hp": overlay["hypothetical_hp_authority"]["current_hp"], "fainted": overlay["hypothetical_fainted_authority"]["value"], "authority": authority, "overlay": overlay}


def _event_with_reactive(event: Mapping[str, Any], reactive: Mapping[str, Any] | None) -> dict[str, Any]:
    result = deepcopy(dict(event))
    if isinstance(reactive, Mapping):
        result["contact_reactive_damage"] = {"outcome": reactive["authority"]["outcome"], "ordered_sources": deepcopy(reactive["authority"].get("ordered_sources", ())), "authority": deepcopy(dict(reactive["authority"])), "overlay": deepcopy(dict(reactive["overlay"])) if isinstance(reactive.get("overlay"), Mapping) else None}
        result["attacker_post_reactive_hp"] = reactive["post_hp"]
        result["attacker_fainted_from_reactive"] = reactive["fainted"]
    return result


def _apply_reactive_status(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], action: Mapping[str, Any], contact_authority: Mapping[str, Any] | None, event: Mapping[str, Any], hit_index: int, condition_state: str, attacker_fainted: bool) -> tuple[dict[str, Any], ...] | dict[str, Any]:
    if contact_authority is None:
        return ({"branch": "not_applicable", "factor": Fraction(1, 1), "post_condition": condition_state, "overlay": None, "authority": None},)
    authority = freeze_runtime_d0_contact_reactive_status_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=base["attacker"], defender=base["target"],
        source_action=action, contact_authority=contact_authority,
        source_hit={
            "source_action_id": action["action_id"], "source_move_id": action["identity"],
            "hit_index": hit_index, "critical_state": event.get("critical_state"),
            "roll_index": event.get("roll_index"), "raw_damage": event.get("raw_damage"),
            "actual_damage": event.get("actual_damage"), "target_routing": event.get("target_routing", "target"),
            "target_pre_hp": event.get("pre_hp"), "target_post_hp": event.get("post_hp"),
        },
        attacker_condition_authority=_path_condition_authority(strategy_d0, base["attacker"], condition_state),
        attacker_fainted_authority={"status": "known", "value": attacker_fainted},
    )
    if authority.get("status") != "resolved":
        return authority
    rows = []
    for branch in contact_reactive_status_branches(authority=authority):
        overlay = branch.get("overlay")
        if not isinstance(overlay, Mapping) and branch["branch"] != "not_applicable":
            return {"status": "rejected", "reason": "contact_reactive_status_overlay_invalid"}
        rows.append({
            "branch": branch["branch"], "factor": branch["factor"],
            "post_condition": condition_from_overlay(overlay if isinstance(overlay, Mapping) else None, condition_state),
            "authority": authority, "overlay": overlay,
        })
    return tuple(rows)


def _event_with_reactive_status(event: Mapping[str, Any], status: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(event))
    authority, overlay = status.get("authority"), status.get("overlay")
    if isinstance(authority, Mapping):
        result["contact_reactive_status"] = {
            "outcome": authority.get("outcome"), "branch": status.get("branch"),
            "post_condition": status.get("post_condition"),
            "authority": deepcopy(dict(authority)),
            "overlay": deepcopy(dict(overlay)) if isinstance(overlay, Mapping) else None,
        }
        result["attacker_post_reactive_condition"] = status.get("post_condition")
    return result


def _path_condition_authority(d0: Mapping[str, Any], owner: Mapping[str, Any], condition: str) -> dict[str, Any]:
    base = {
        "status": "resolved", "schema_version": "runtime-current-condition-authority-v1",
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "owner": deepcopy(dict(owner)),
    }
    if condition == "none":
        return {**base, "condition": {"status": "known_none", "provenance": "detached_contact_reactive_status_path_state_v1"}}
    return {**base, "condition": {"status": "known_present", "condition": condition, "provenance": "detached_contact_reactive_status_path_state_v1"}}


def _attacker_max_hp(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> int | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None; side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; pokemon = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    maximum = pokemon.get("max_hp") if isinstance(pokemon, Mapping) and pokemon.get("pokemon_id") == owner.get("pokemon_id") else None
    return maximum if isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0 else None


def _applied_focus_sash_survival(events: tuple[Mapping[str, Any], ...]) -> dict[str, Any] | None:
    for event in events:
        focus = event.get("focus_sash_survival")
        if isinstance(focus, Mapping) and focus.get("outcome") == "applied":
            return deepcopy(dict(focus))
    return None


def _serialize_leaf(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["probability"] = _fd(result["probability"])
    for event in result["ordered_hits"]:
        event["probability"] = _fd(event["probability"])
    return result

def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _mapping(value: Any) -> Mapping[str, Any]: return value if isinstance(value, Mapping) else {}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
