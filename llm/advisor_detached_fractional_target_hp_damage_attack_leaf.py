"""Exact hit/miss leaves for current-HP fractional special damage."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_detached_fractional_target_hp_damage import materialize_detached_fractional_target_hp_damage

SCHEMA_VERSION = "detached-fractional-target-hp-damage-attack-leaf-v1"


def materialize_detached_fractional_target_hp_damage_attack_leaves(*, strategy_d0: Mapping[str, Any], execution_authority: Mapping[str, Any], strict_hit_probability: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, execution_authority)
    if base is None:
        return _result("rejected", "fractional_execution_authority_invalid", {})
    hit = _hit(strict_hit_probability, base)
    if isinstance(hit, str):
        return _result("rejected", hit, base)
    hp = execution_authority.get("execution_target_hp")
    route = execution_authority.get("target_route")
    if route not in {"target", "substitute"} or not isinstance(hp, int) or isinstance(hp, bool) or hp < 1:
        return _result("incomplete", "fractional_execution_route_or_hp_unknown", base)
    active_target = strategy_d0.get("strategy_state", {}).get("active", {}).get(base["target"]["side"])
    substitute = execution_authority.get("substitute_authority")
    expected_hp = substitute.get("substitute_hp") if route == "substitute" and isinstance(substitute, Mapping) else active_target.get("current_hp") if isinstance(active_target, Mapping) else None
    if hp != expected_hp:
        return _result("rejected", "fractional_execution_target_hp_binding_mismatch", base)
    result = materialize_detached_fractional_target_hp_damage(move=execution_authority["canonical_move_metadata"], target_hp={"current_hp": hp, "max_hp": hp, "fainted": False}, hit_state="hit", applicability=execution_authority["applicability"])
    if result.get("status") != "resolved":
        return _result(result.get("status", "rejected"), result.get("reason", "fractional_damage_materialization_unavailable"), base)
    target_hp = strategy_d0["strategy_state"]["active"][base["target"]["side"]]["current_hp"]
    own_hp = strategy_d0["strategy_state"]["active"][base["attacker"]["side"]]["current_hp"]
    leaves = []
    for state, percent in (("hit", hit), ("miss", 100 - hit)):
        if percent == 0: continue
        success = state == "hit" and execution_authority["applicability"] == "applicable"
        damage = result["damage"] if success else 0
        post = result["target_post_hp"] if success and route == "target" else target_hp
        route_post = result["target_post_hp"] if success else hp
        leaves.append({"leaf_id": f"fractional_target_hp:{state}", "candidate_id": f"attack:{base['move_id']}", "action_type": "attack", "branch_path": ((state, {"numerator": percent, "denominator": 100}),), "probability": {"numerator": percent, "denominator": 100}, "hit_state": state, "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": damage, "own_final_hp": own_hp, "target_final_hp": post, "target_ko": post == 0, "self_fainted": False, "secondary": None, "contact": "successful_contact_eligible" if success else "not_applicable", "source_hit_context": {"move_id": base["move_id"], "damage_route": route, "successful_damaging_hit": success}, "fractional_target_hp_damage": {"family": deepcopy(execution_authority["special_damage_rule_authority"]), "target_route": route, "execution_target_hp": hp, "route_post_hp": route_post, "hit_state": state, "applicability": execution_authority["applicability"], "derived_damage": damage, "target_post_hp": post}}, "provenance": {**base, "execution_authority": deepcopy(dict(execution_authority)), "provenance": "strict_d0_fractional_special_damage_execution_envelope_v1"}})
    return {"status": "evaluable", "schema_version": SCHEMA_VERSION, "terminal_leaves": tuple(leaves), "terminal_probability_mass": {"numerator": 1, "denominator": 1}, "component_manifest": {"accuracy": {"status": "resolved"}, "critical": {"status": "not_applicable"}, "damage_roll": {"status": "not_applicable"}, "secondary": {"status": "not_applicable"}}, **base, "provenance": "strict_fractional_special_damage_execution_to_terminal_leaves_v1"}


def _base(d0: Any, authority: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != "runtime-d0-special-damage-execution-authority-v1" or authority.get("special_damage_family") != "current_hp_fraction_damage": return None
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")
    expected = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": d0.get("decision_owner")}
    if any(authority.get(key) != expected.get(key) for key in expected) or authority.get("attacker") != d0.get("decision_owner") or authority.get("move_id") not in {"super-fang", "natures-madness", "ruination"}: return None
    return {key: deepcopy(authority[key]) for key in keys}


def _hit(value: Any, base: Mapping[str, Any]) -> int | str:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "strict-deterministic-hit-probability-v1": return "fractional_strict_hit_probability_invalid"
    if any(value.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")): return "fractional_strict_hit_probability_binding_mismatch"
    p = 100 if value.get("result") == "always_hit" else value.get("probability_percent")
    return p if isinstance(p, int) and not isinstance(p, bool) and 0 <= p <= 100 else "fractional_strict_hit_probability_invalid"


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
