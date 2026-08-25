"""Detached, conditional immediate move-vs-move pair materialization."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_intermediate_predictive_authority import (
    detached_intermediate_builder_inputs, freeze_detached_intermediate_predictive_authority,
)
from llm.advisor_detached_predictive_intermediate_state import (
    freeze_detached_actor_neutral_root_predictive_authority,
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_detached_strategy_orchestration import _normal_formula_facts
from llm.advisor_exact_predictive_outcome_ledger import normalize_exact_predictive_outcome_ledger
from llm.advisor_predictive_critical_damage_context import materialize_predictive_critical_damage_contexts
from llm.advisor_predictive_critical_hit_uncertainty import compose_predictive_critical_hit_uncertainty
from llm.advisor_predictive_hit_miss_uncertainty import compose_predictive_hit_miss_uncertainty
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment,
    freeze_runtime_normal_formula_predictive_input,
    resolve_runtime_d0_selectable_move_metadata_authority,
)


SCHEMA_VERSION = "immediate-move-vs-move-action-pair-v1"
HORIZON = "immediate_action_pair"
_STATUSES = {"incomplete", "unsupported", "rejected"}


def materialize_immediate_move_vs_move_action_pair(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    own_action: Mapping[str, Any], opponent_action: Mapping[str, Any],
    action_order_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one known-usable opponent move conditional on its selection."""
    base = _base(strategy_d0, own_action, opponent_action)
    if base is None: return _result("rejected", "invalid_pair_request", {})
    order = _order(action_order_authority, base)
    if isinstance(order, tuple): return _result(*order, base)
    opponent_meta = _opponent_metadata(opponent_action, base)
    own_meta = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=own_action)
    if own_meta.get("status") != "resolved": return _result(_status(own_meta), own_meta.get("reason", "own_move_metadata_unavailable"), base)
    if isinstance(opponent_meta, tuple): return _result(*opponent_meta, base)
    first_actor = base["own_actor"] if order == "own_first" else base["opponent_actor"]
    first_meta = own_meta if order == "own_first" else opponent_meta
    first_d0, first_snapshot, root = strategy_d0, runtime_snapshot, None
    if order == "opponent_first":
        root = freeze_detached_actor_neutral_root_predictive_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, opponent_action=opponent_action)
        if root.get("status") != "resolved": return _result(_status(root), root.get("reason", "opponent_root_predictive_authority_unavailable"), base)
        first_d0, first_snapshot = root["predictive_strategy_d0"], root["predictive_runtime_snapshot"]
    first = _normal_formula_ledger(strategy_d0=first_d0, runtime_snapshot=first_snapshot, actor=first_actor,
                                   target=base["opponent_actor"] if first_actor == base["own_actor"] else base["own_actor"],
                                   metadata_authority=first_meta)
    if first.get("status") != "evaluable": return _result(_status(first), f"first_action_{first.get('reason', 'ledger_unavailable')}", base, first_action_ledger=first)
    branches: list[dict[str, Any]] = []
    second_actor = base["opponent_actor"] if order == "own_first" else base["own_actor"]
    second_meta = opponent_meta if order == "own_first" else own_meta
    for leaf in first["terminal_leaves"]:
        intermediate = materialize_detached_predictive_intermediate_state(strategy_d0=strategy_d0, terminal_leaf=leaf, root_predictive_authority=root)
        if intermediate.get("status") != "resolved": return _result(_status(intermediate), intermediate.get("reason", "intermediate_state_unavailable"), base)
        if _fainted(intermediate, second_actor):
            branches.append(_branch(base, order, leaf, intermediate, None, second_actor)); continue
        authority = freeze_detached_intermediate_predictive_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            intermediate_state=intermediate, actor=second_actor,
            target=base["opponent_actor"] if second_actor == base["own_actor"] else base["own_actor"],
            move_metadata_authority=second_meta)
        inputs = detached_intermediate_builder_inputs(authority)
        if inputs.get("status") != "resolved": return _result(_status(inputs), inputs.get("reason", "second_action_intermediate_authority_unavailable"), base, first_leaf_id=leaf["leaf_id"])
        second = _normal_formula_ledger(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"],
            actor=inputs["attacker"], target=inputs["target"], metadata_authority=_metadata_for_inputs(second_meta, inputs))
        if second.get("status") != "evaluable": return _result(_status(second), f"second_action_{second.get('reason', 'ledger_unavailable')}", base, first_leaf_id=leaf["leaf_id"])
        for second_leaf in second["terminal_leaves"]: branches.append(_branch(base, order, leaf, intermediate, second_leaf, second_actor))
    mass = sum((_fraction(row["probability"]) for row in branches), Fraction())
    if mass != Fraction(1, 1): return _result("rejected", "pair_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {"status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
            "action_order": deepcopy(dict(action_order_authority)), "conditional_on": "opponent_selected_exact_known_usable_move",
            "terminal_branches": tuple(branches), "terminal_probability_mass": _fd(mass),
            "aggregation": "none_preserve_first_and_second_leaf_identity",
            "provenance": "strict_detached_immediate_move_vs_move_pair_materialization_v1"}


def _normal_formula_ledger(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata_authority: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _metadata_for_inputs(metadata_authority, None)
    if metadata is None: return _result("rejected", "predictive_move_metadata_authority_invalid", {})
    native = build_runtime_d0_native_damage_context(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, move_metadata=metadata)
    normal = freeze_runtime_normal_formula_predictive_input(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, move_metadata=metadata, native_damage_context=native)
    hit = build_runtime_d0_strict_hit_probability_assessment(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, selected_move=metadata)
    crit = build_runtime_d0_strict_critical_hit_probability_assessment(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, attacker=actor, target=target, move_metadata=metadata)
    if any(row.get("status") != "resolved" for row in (normal, hit, crit)):
        row = next(row for row in (normal, hit, crit) if row.get("status") != "resolved")
        return _result(_status(row), row.get("reason", "normal_formula_predictive_authority_unavailable"), {})
    candidate = {"candidate_id": f"attack:{metadata['move_id']}", "action_type": "attack", "session_id": strategy_d0["session_id"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"]))}
    own_hp = strategy_d0["strategy_state"]["active"][actor["side"]]["current_hp"]
    interval_input = {"snapshot_damage_input": normal["snapshot_damage_input"], "stat_provenance": normal["stat_provenance"], "trusted_level": normal["trusted_level"]}
    paired = materialize_predictive_critical_damage_contexts(branch_state=strategy_d0["strategy_state"], decision_owner=actor, target_owner=target, **interval_input)
    if paired.get("status") != "resolved": return _result(_status(paired), paired.get("reason", "critical_damage_context_unavailable"), {})
    post_input = {"move_metadata": metadata, **normal["post_hit_authority"]}
    non = _normal_formula_facts(candidate, paired["non_critical_context"], own_hp, post_input, normal)
    critical = _normal_formula_facts(candidate, paired["critical_context"], own_hp, post_input, normal)
    non_consequences = _consequences(paired["non_critical_context"], non)
    critical_consequences = _consequences(paired["critical_context"], critical)
    critical = compose_predictive_critical_hit_uncertainty(candidate=candidate, strict_critical_hit_probability=crit, paired_damage_contexts=paired, non_critical_consequences=non_consequences, critical_consequences=critical_consequences)
    if critical.get("status") != "resolved": return _result(_status(critical), critical.get("reason", "critical_uncertainty_unavailable"), {})
    hit_consequences = {"critical_hit_uncertainty": critical, "guaranteed_facts": critical["guaranteed_facts"]}
    uncertainty = compose_predictive_hit_miss_uncertainty(candidate=candidate, strict_hit_probability=hit, hit_consequences=hit_consequences,
        miss_baseline={"attacker_current_hp": own_hp, "target_current_hp": strategy_d0["strategy_state"]["active"][target["side"]]["current_hp"]})
    if uncertainty.get("status") != "resolved": return _result(_status(uncertainty), uncertainty.get("reason", "hit_miss_uncertainty_unavailable"), {})
    bindings = {"session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])), "attacker": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "move_id": metadata["move_id"]}
    return normalize_exact_predictive_outcome_ledger(candidate=candidate, predictive_consequence=uncertainty,
        component_manifest={"accuracy": {"status": "resolved"}, "critical": {"status": "resolved"}, "damage_roll": {"status": "resolved"}, "secondary": {"status": "not_applicable"}}, bindings=bindings)


def _consequences(interval: Mapping[str, Any], facts: Mapping[str, Any]) -> dict[str, Any]:
    return {"interval": interval, "post_hit": facts.get("post_hit"), "stage_effects": facts.get("stage_effects"), "damage_roll_uncertainty": facts.get("damage_roll_uncertainty"), "guaranteed_facts": facts}

def _base(d0: Any, own: Any, opponent: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(own, Mapping) or own.get("action_type") != "attack" or not isinstance(own.get("action_id"), str): return None
    self_owner, opp_owner = d0.get("active_owners", {}).get("self"), d0.get("active_owners", {}).get("opponent")
    if not isinstance(self_owner, Mapping) or not isinstance(opp_owner, Mapping) or d0.get("decision_owner") != self_owner: return None
    return {"pair_id": f"pair:{own['action_id']}:{opponent.get('action_id') if isinstance(opponent, Mapping) else None}", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "own_action_id": own["action_id"], "opponent_action_id": opponent.get("action_id") if isinstance(opponent, Mapping) else None, "own_actor": deepcopy(dict(self_owner)), "opponent_actor": deepcopy(dict(opp_owner))}
def _order(value: Any, base: Mapping[str, Any]) -> str | tuple[str, str]:
    if not isinstance(value, Mapping) or value.get("schema_version") != "runtime-d0-action-order-authority-v1": return ("rejected", "action_order_authority_invalid")
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor"):
        if value.get(key) != base.get(key): return ("rejected", "action_order_binding_mismatch")
    if value.get("status") != "resolved": return (_status(value), value.get("reason", "action_order_unavailable"))
    return value["order"] if value.get("order") in {"own_first", "opponent_first"} else ("incomplete", "action_order_unresolved_tie")
def _opponent_metadata(action: Any, base: Mapping[str, Any]) -> Mapping[str, Any] | tuple[str, str]:
    if not isinstance(action, Mapping) or action.get("status") != "resolved": return (_status(action) if isinstance(action, Mapping) else "rejected", action.get("reason", "opponent_action_invalid") if isinstance(action, Mapping) else "opponent_action_invalid")
    if action.get("selectability") != "selectable" or action.get("usability", {}).get("status") != "known_usable": return ("incomplete", "opponent_action_not_known_usable")
    if any(action.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")) or action.get("action_id") != base.get("opponent_action_id"): return ("rejected", "opponent_action_binding_mismatch")
    meta = action.get("metadata_authority")
    if not isinstance(meta, Mapping) or meta.get("status") != "resolved": return (_status(meta) if isinstance(meta, Mapping) else "rejected", "opponent_move_metadata_unavailable")
    return {"status": "resolved", "move_id": action.get("move_id"), "metadata": deepcopy(meta.get("metadata")), "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": deepcopy(dict(base["decision_owner"]))}
def _metadata_for_inputs(authority: Any, inputs: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if isinstance(authority, Mapping) and isinstance(authority.get("move_id"), str) and authority.get("category") in {"physical", "special"}:
        metadata = authority
        if inputs is not None and metadata.get("move_id") != inputs.get("move_metadata", {}).get("move_id"): return None
        return deepcopy(dict(metadata))
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or not isinstance(authority.get("metadata"), Mapping): return None
    metadata = authority["metadata"]
    if inputs is not None and metadata.get("move_id") != inputs.get("move_metadata", {}).get("move_id"): return None
    return deepcopy(dict(metadata))
def _fainted(state: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    row = state.get("active", {}).get(owner.get("side"), {}) if isinstance(state.get("active"), Mapping) else {}; return isinstance(row, Mapping) and row.get("hypothetical_fainted", {}).get("value") is True
def _branch(base: Mapping[str, Any], order: str, first: Mapping[str, Any], intermediate: Mapping[str, Any], second: Mapping[str, Any] | None, second_actor: Mapping[str, Any]) -> dict[str, Any]:
    first_p = _fraction(first["probability"]); second_p = Fraction(1, 1) if second is None else _fraction(second["probability"])
    return {"pair_leaf_id": f"{first['leaf_id']}/" + ("second_cancelled_due_to_faint" if second is None else f"{second['leaf_id']}"), "action_order": order, "first_action_leaf": deepcopy(dict(first)), "intermediate_state_id": f"intermediate:{first['candidate_id']}:{first['leaf_id']}", "second_action": {"state": "cancelled_due_to_faint" if second is None else "executed", "actor": deepcopy(dict(second_actor)), "conditional_probability": _fd(second_p), **({"reason": "second_action_cancelled_due_to_faint"} if second is None else {"leaf": deepcopy(dict(second))})}, "probability": _fd(first_p * second_p), "provenance": deepcopy(dict(base))}
def _fraction(value: Mapping[str, Any]) -> Fraction: return Fraction(value["numerator"], value["denominator"])
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _status(value: Mapping[str, Any]) -> str: return value.get("status") if isinstance(value, Mapping) and value.get("status") in _STATUSES else "rejected"
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
