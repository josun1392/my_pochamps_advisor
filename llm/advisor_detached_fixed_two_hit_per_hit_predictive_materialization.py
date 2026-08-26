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
    if _has_life_orb(strategy_d0, runtime_snapshot, base["attacker"]):
        return _result("unsupported", "fixed_two_hit_item_consumption_unsupported", base)

    leaves: list[dict[str, Any]] = []
    miss_probability = Fraction(100 - probability, 100)
    target_hp = strategy_d0["strategy_state"]["active"][base["target"]["side"]]["current_hp"]
    if miss_probability:
        leaves.append(_leaf(base, "miss", miss_probability, (), target_hp, _sturdy_state(sturdy_survival_authority, consumed=False)))
    hit_probability = Fraction(probability, 100)
    if hit_probability:
        first = _hit_events(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, base=base,
            single_metadata=single, sturdy_survival_authority=sturdy_survival_authority,
        )
        if isinstance(first, Mapping):
            return _result(first["status"], first["reason"], base)
        for first_event in first:
            first_probability = hit_probability * first_event["probability"]
            if first_event["post_hp"] == 0:
                leaves.append(_leaf(base, "hit", first_probability, (first_event,), 0, _sturdy_state(sturdy_survival_authority, consumed=first_event["sturdy_applied"])))
                continue
            second_d0, second_snapshot = _detached_target_hp_view(
                runtime_snapshot=runtime_snapshot, decision_owner=base["attacker"],
                target=base["target"], target_hp=first_event["post_hp"],
            )
            if second_d0 is None:
                return _result("rejected", "fixed_two_hit_intermediate_target_state_invalid", base)
            second_sturdy = sturdy_survival_authority if (
                first_event["post_hp"] == first_event["target_max_hp"] and not first_event["sturdy_applied"]
            ) else None
            second = _hit_events(
                strategy_d0=second_d0, runtime_snapshot=second_snapshot, base=base,
                single_metadata=single, sturdy_survival_authority=second_sturdy,
            )
            if isinstance(second, Mapping):
                return _result(second["status"], second["reason"], base)
            for second_event in second:
                leaves.append(_leaf(
                    base, "hit", first_probability * second_event["probability"],
                    (first_event, second_event), second_event["post_hp"],
                    _sturdy_state(sturdy_survival_authority, consumed=first_event["sturdy_applied"] or second_event["sturdy_applied"]),
                ))
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


def _hit_events(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], base: Mapping[str, Any], single_metadata: Mapping[str, Any], sturdy_survival_authority: Mapping[str, Any] | None) -> list[dict[str, Any]] | dict[str, str]:
    native = build_runtime_d0_native_damage_context(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=base["attacker"], target=base["target"], move_metadata=single_metadata)
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
            attacker_item=normal["post_hit_authority"]["attacker_item"], attacker_ability=normal["post_hit_authority"]["attacker_ability"],
            target_ability=normal["post_hit_authority"]["target_ability"], attacker_item_known=normal["post_hit_authority"]["attacker_item_known"],
            target_sturdy_survival_authority=sturdy_survival_authority,
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
            events.append({
                "probability": critical_factor * Fraction(1, 16), "critical_state": critical_state,
                "roll_index": roll["roll_index"], "random_factor_percent": roll["random_factor_percent"],
                "raw_damage": post_row["raw_damage"], "actual_damage": actual, "pre_hp": before,
                "post_hp": before - actual, "target_max_hp": before if sturdy_survival_authority is not None else None,
                "sturdy_applied": isinstance(sturdy, Mapping) and sturdy.get("outcome") == "applied",
                "sturdy_survival": deepcopy(dict(sturdy)) if isinstance(sturdy, Mapping) else {"outcome": "not_applicable"},
            })
    if not events or sum((row["probability"] for row in events), Fraction()) != Fraction(1, 1):
        return {"status": "rejected", "reason": "fixed_two_hit_per_hit_probability_mass_invalid"}
    return events


def _base(d0: Any, action: Any, authority: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or not isinstance(action, Mapping) or not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != EXECUTION_SCHEMA:
        return None
    expected = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": d0.get("decision_owner"), "action_id": action.get("action_id")}
    if any(authority.get(key) != value for key, value in expected.items()) or authority.get("attacker") != d0.get("active_owners", {}).get("self") or authority.get("target") != d0.get("active_owners", {}).get("opponent") or authority.get("hit_count") != 2:
        return None
    metadata = authority.get("move_metadata_authority", {}).get("metadata") if isinstance(authority.get("move_metadata_authority"), Mapping) else None
    critical = authority.get("per_hit_critical_execution")
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != action.get("identity") or not isinstance(critical, Mapping) or critical.get("semantics") != "independent_canonical_critical_roll_per_hit" or not isinstance(critical.get("per_hit_critical_probability"), Mapping):
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "action_id": action["action_id"], "move_id": metadata["move_id"], "attacker": deepcopy(dict(authority["attacker"])), "target": deepcopy(dict(authority["target"])), "per_hit_critical_execution": deepcopy(dict(critical)), "execution_authority": deepcopy(dict(authority))}


def _single_hit_metadata(metadata: Mapping[str, Any]) -> dict[str, Any] | None:
    value = deepcopy(dict(metadata)); value.pop("min_hits", None); value.pop("max_hits", None)
    return value if value.get("move_id") in {"double-hit", "double-kick"} else None


def _detached_target_hp_view(*, runtime_snapshot: Mapping[str, Any], decision_owner: Mapping[str, Any], target: Mapping[str, Any], target_hp: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not isinstance(state, Mapping) or not isinstance(target_hp, int) or target_hp < 0:
        return None, None
    synthetic = deepcopy(dict(state)); side = synthetic.get(f"{target['side']}_side"); roster = side.get("pokemon") if isinstance(side, Mapping) else None; pokemon = roster.get(target["slot_index"]) if isinstance(roster, Mapping) else None
    if not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id") != target["pokemon_id"]:
        return None, None
    pokemon["current_hp"] = target_hp; pokemon["fainted"] = target_hp == 0
    snapshot = {"status": "runtime_snapshot_ready", "session_id": decision_owner["session_id"], "state": synthetic, "state_fingerprint": state_fingerprint(synthetic)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=decision_owner)
    return (d0, snapshot) if d0.get("status") == "resolved" else (None, None)


def _has_life_orb(d0: Mapping[str, Any], snapshot: Mapping[str, Any], attacker: Mapping[str, Any]) -> bool:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None; side = state.get(f"{attacker['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; pokemon = roster.get(attacker["slot_index"]) if isinstance(roster, Mapping) else None
    return isinstance(pokemon, Mapping) and pokemon.get("pokemon_id") == attacker["pokemon_id"] and pokemon.get("known_item") == "life-orb"


def _sturdy_state(authority: Mapping[str, Any] | None, *, consumed: bool) -> dict[str, Any]:
    return {"state": "consumed" if consumed else "ready_or_not_applicable", "authority_present": isinstance(authority, Mapping)}


def _leaf(base: Mapping[str, Any], hit_state: str, probability: Fraction, events: tuple[Mapping[str, Any], ...], target_hp: int, sturdy: Mapping[str, Any]) -> dict[str, Any]:
    path = [hit_state]
    for index, event in enumerate(events, 1): path.extend((f"hit_{index}:{event['critical_state']}", f"hit_{index}:roll:{event['roll_index']}"))
    return {"leaf_id": "/".join(path), "hit_state": hit_state, "probability": probability, "ordered_hits": tuple(deepcopy(dict(event)) for event in events), "consequences": {"target_final_hp": target_hp, "target_ko": target_hp == 0, "sturdy": deepcopy(dict(sturdy))}, "provenance": deepcopy(dict(base))}


def _serialize_leaf(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value)); result["probability"] = _fd(result["probability"]); return result

def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
