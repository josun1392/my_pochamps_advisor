"""Detached terminal execution for authenticated standard charge continuations.

This module deliberately has no runtime-D0 or reducer dependency.  A charge
move remains blocked by the generic immediate path; this owner is the sole
place where a continuation already authenticated at the next decision may be
represented as a terminal attack attempt.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from advisor.damage.crit import crit_probability, resolve_crit_stage
from advisor.damage.crit import is_crit_blocked, select_critical_damage_stages
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.field import Field, SideField
from advisor.damage.stats import apply_boosts
from advisor.damage.abilities import get_ability
from advisor.damage.items import get_item
from advisor.probabilistic_target_flinch_effect_capabilities import resolve_probabilistic_target_flinch_effect_capability
from advisor.probabilistic_target_status_effect_capabilities import resolve_probabilistic_target_status_effect_capability
from llm.advisor_next_turn_predictive_mechanics_authority import validate_forced_continuation_predictive_mechanics_binding
from llm.advisor_champions_sleep_freeze_action_gate import classify_status_move, resolve_gate_branches
from llm.advisor_champions_confusion_action_gate import resolve_confusion_branches
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_detached_next_turn_held_item_effect_applicability import materialize_detached_next_turn_held_item_effect_applicability
from llm.advisor_detached_next_turn_sturdy_survival_authority import materialize_detached_next_turn_sturdy_survival_authority
from llm.advisor_detached_next_turn_focus_sash_survival_authority import materialize_detached_next_turn_focus_sash_survival_authority, apply_detached_focus_sash_single_hit
from llm.advisor_detached_next_turn_life_orb_immediate_authority import materialize_detached_next_turn_life_orb_immediate_authority


AUTHORITY_SCHEMA_VERSION = "detached-standard-charge-turn-two-execution-authority-v1"
SCHEMA_VERSION = "detached-standard-charge-turn-two-attack-execution-v1"
_SIDES = ("self", "opponent")


def materialize_detached_standard_charge_turn_two_execution_authority(*, next_decision_state: Mapping[str, Any], next_decision_fingerprint: str, forced_continuation: Mapping[str, Any], predictive_mechanics: Mapping[str, Any]) -> dict[str, Any]:
    """Authenticate all forced actions without granting a generic charge bypass."""
    if not isinstance(next_decision_state, Mapping) or not isinstance(next_decision_fingerprint, str) or fingerprint_transition_preview_state(next_decision_state) != next_decision_fingerprint:
        return _result("rejected", "stale_or_invalid_next_decision_fingerprint")
    binding = validate_forced_continuation_predictive_mechanics_binding(forced_continuation=forced_continuation, predictive_mechanics=predictive_mechanics, next_decision_state=next_decision_state)
    if binding.get("status") != "resolved":
        return _result(binding.get("status", "rejected"), binding.get("reason", "forced_predictive_mechanics_binding_unavailable"))
    actions = forced_continuation.get("forced_continuation_actions", {})
    rows: dict[str, Any] = {}
    for side in _SIDES:
        action = actions.get(side)
        if not isinstance(action, Mapping) or action.get("status") == "known_none":
            rows[side] = {"status": "not_applicable", "reason": "no_forced_standard_charge_continuation"}
            continue
        if action.get("status") != "resolved" or side not in binding.get("bindings", {}):
            return _result("rejected", "forced_continuation_action_untrusted")
        row = _authority_row(side, action, binding["bindings"][side], next_decision_fingerprint)
        if isinstance(row, str):
            return _result("rejected", row)
        rows[side] = row
    return {"status": "resolved", "schema_version": AUTHORITY_SCHEMA_VERSION, "source_next_decision_fingerprint": next_decision_fingerprint, "next_decision_state": deepcopy(dict(next_decision_state)), "forced_continuation": deepcopy(dict(forced_continuation)), "predictive_mechanics": deepcopy(dict(predictive_mechanics)), "actions": rows, "provenance": "authenticated_forced_continuation_to_detached_turn_two_execution_authority_v1"}


def execute_detached_standard_charge_turn_two_attacks(*, execution_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize independent, unordered turn-two attack ledgers.

    The first vertical slice intentionally accepts only exact neutral detached
    mechanics.  Missing mechanics are represented as incomplete, never as a
    fabricated runtime snapshot or neutral default.
    """
    if not isinstance(execution_authority, Mapping) or execution_authority.get("status") != "resolved" or execution_authority.get("schema_version") != AUTHORITY_SCHEMA_VERSION:
        return _result("rejected", "standard_charge_turn_two_execution_authority_invalid")
    if not _authority_is_self_consistent(execution_authority):
        return _result("rejected", "standard_charge_turn_two_execution_authority_tampered")
    out: dict[str, Any] = {}
    for side, row in execution_authority.get("actions", {}).items():
        if row.get("status") == "not_applicable":
            out[side] = deepcopy(dict(row)); continue
        out[side] = _execute_one(row, execution_authority)
    return {"status": "resolved" if all(x.get("status") in {"resolved", "not_applicable"} for x in out.values()) else "incomplete", "schema_version": SCHEMA_VERSION, "source_next_decision_fingerprint": execution_authority["source_next_decision_fingerprint"], "execution_authority": deepcopy(dict(execution_authority)), "actions": out, "unordered": True, "provenance": "detached_standard_charge_turn_two_attack_attempt_v1"}


def _authority_row(side: str, action: Mapping[str, Any], bound: Mapping[str, Any], fingerprint: str) -> dict[str, Any] | str:
    if action.get("side") != side or action.get("lifecycle_state") != "turn_two_continuation_forced" or action.get("continuation_forced") is not True or action.get("execution_grant") is not False:
        return "forced_continuation_lifecycle_invalid"
    effect = resolve_canonical_standard_charge_turn_two_effect(action.get("move_id"))
    if effect.get("status") != "resolved": return "canonical_terminal_effect_unavailable"
    lifecycle = effect["lifecycle"]
    if lifecycle.get("lifecycle_family") != "ordinary_charge_then_damage" or action.get("actor") != bound.get("actor") or action.get("resolved_target_owner") != bound.get("target"):
        return "forced_continuation_execution_identity_mismatch"
    return {"status": "resolved", "schema_version": AUTHORITY_SCHEMA_VERSION, "side": side, "source_next_decision_fingerprint": fingerprint, "actor": deepcopy(action["actor"]), "target": deepcopy(action["resolved_target_owner"]), "move_id": action["move_id"], "continuation_action_id": action["continuation_action_id"], "original_charge_action_id": action["original_charge_action_id"], "continuation_target_locator": deepcopy(action["continuation_target_locator"]), "original_charge_lifecycle": deepcopy(action["original_charge_provenance"]), "canonical_terminal_effect": effect, "predictive_actor_mechanics": deepcopy(bound["actor_mechanics"]), "predictive_target_mechanics": deepcopy(bound["target_mechanics"]), "execution_grant": "authenticated_standard_charge_turn_two_only", "provenance": "forced_continuation_and_predictive_mechanics_bound_execution_authority_v1"}


def _execute_one(row: Mapping[str, Any], execution_authority: Mapping[str, Any]) -> dict[str, Any]:
    actor, target = row["predictive_actor_mechanics"], row["predictive_target_mechanics"]
    missing = _required_missing(actor) + _required_missing(target)
    if missing:
        return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": "detached_damage_mechanics_incomplete", "missing_authority": tuple(sorted(set(missing))), "execution_authority": deepcopy(dict(row))}
    effect = row["canonical_terminal_effect"]; move = effect["move"]
    terminal = _terminal_authorities(row, execution_authority, move)
    if terminal.get("status") != "resolved":
        return _incomplete(row, terminal.get("reason", "detached_terminal_authority_unavailable"))
    gate = _pre_action_gate(actor, target, row["move_id"])
    if gate["status"] == "incomplete":
        return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": gate["reason"], "execution_authority": deepcopy(dict(row)), "pre_action_gate": gate}
    if gate["outcome"] == "cancelled": return _cancelled(row, gate)
    # Status gates are composed before the ordinary attack tree.  The pure
    # Champions owners supply exact fractions; no runtime snapshot is made.
    opportunities = gate.get("branches", ({"kind": "executes", "executes": True, "probability": _fd(Fraction(1))},))
    actor_stages, target_stages = actor["current_stages"]["values"], target["current_stages"]["values"]
    accuracy = _accuracy(move["accuracy"], actor_stages["accuracy"], target_stages["evasion"])
    if accuracy is None:
        return _incomplete(row, "detached_accuracy_stage_adapter_unavailable")
    crit_stage = resolve_crit_stage(
        {"ability": _value(actor["ability"]), "item": _value(actor["item"]), "types": tuple(actor["types"]["value"]), "volatiles": _volatiles(actor["critical_hit_volatiles"])},
        {"move_id": move["move_id"]},
        {"ability": _value(target["ability"]), "status": _condition(target["condition"])},
    )
    crit = Fraction(0, 1) if is_crit_blocked({"ability": _value(target["ability"])}, {"lucky_chant": target["lucky_chant"].get("status") == "known_active"}) else crit_probability(crit_stage)
    leaves = []
    for opportunity in opportunities:
      root = _fraction(opportunity["probability"])
      if not opportunity.get("executes"):
        if opportunity.get("kind", "").endswith("confusion_self_hit"):
          self_hits = _confusion_self_hit_leaves(row, actor, opportunity)
          if self_hits is None: return _incomplete(row, "confusion_self_hit_exact_identity_unavailable")
          leaves.extend(self_hits); continue
        leaves.append(_gate_cancelled_leaf(row, opportunity)); continue
      if accuracy < 1:
        miss = _miss_leaf(row, actor, target, root * (1 - accuracy)); miss["branch_path"] = ("pre_action", opportunity["kind"], *miss["branch_path"]); leaves.append(miss)
      for critical, cp in ((False, 1 - crit), (True, crit)):
        if not cp:
            continue
        rolls = _damage_rolls(row, critical, terminal["attacker_item"]["effective_item_id"], terminal["target_item"]["effective_item_id"])
        if rolls is None:
            return _incomplete(row, "detached_damage_context_unavailable")
        for index, damage in enumerate(rolls):
            event = _hit_event(row, actor, target, critical, index, damage, root * accuracy * cp * Fraction(1, 16), terminal); event["branch_path"] = ("pre_action", opportunity["kind"], *event["branch_path"])
            secondary = _secondary_branches(row, actor, target, event)
            if secondary is None:
                return _incomplete(row, "detached_secondary_capability_unavailable")
            leaves.extend(_apply_life_orb(secondary, terminal["life_orb"], damage > 0))
    total = sum((_fraction(leaf["probability"]) for leaf in leaves), Fraction())
    if total != 1:
        return _incomplete(row, "detached_attack_ledger_probability_not_normalized")
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "execution_authority": deepcopy(dict(row)), "terminal_authorities": deepcopy(terminal), "pre_action_gate": gate, "hit_probability": _fd(accuracy), "critical_probability": _fd(crit), "terminal_leaves": tuple(leaves), "terminal_probability_mass": _fd(total), "component_manifest": {"accuracy": {"status": "resolved"}, "critical": {"status": "resolved", "stage": crit_stage}, "damage_roll": {"status": "resolved", "roll_count_per_critical_context": 16}, "secondary": {"status": "resolved"}}, "provenance": "authenticated_detached_standard_charge_turn_two_exact_attack_ledger_v1"}


def _required_missing(row: Mapping[str, Any]) -> list[str]:
    required = ("current_level", "current_final_stats", "current_hp", "current_stages", "condition", "item", "ability", "types", "substitute", "critical_hit_volatiles", "lucky_chant", "field", "side_conditions", "direct_mechanics")
    return [key for key in required if not isinstance(row.get(key), Mapping) or row[key].get("status") not in {"known", "known_none", "known_present", "known_absent", "known_active", "known_inactive"}]


def _terminal_authorities(row: Mapping[str, Any], execution: Mapping[str, Any], move: Mapping[str, Any]) -> dict[str, Any]:
    state, fingerprint, predictive = execution.get("next_decision_state"), execution.get("source_next_decision_fingerprint"), execution.get("predictive_mechanics")
    action = {"action_type": "attack", "action_id": row["continuation_action_id"], "identity": row["move_id"]}
    attacker_item = materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, holder=row["actor"])
    target_item = materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, holder=row["target"])
    if attacker_item.get("status") != "resolved" or target_item.get("status") != "resolved": return {"status": "incomplete", "reason": "detached_held_item_effect_applicability_unavailable"}
    if attacker_item.get("terminal_consumption") == "required_unrepresented" or target_item.get("terminal_consumption") == "required_unrepresented": return {"status": "incomplete", "reason": "detached_terminal_consumable_item_consequence_unrepresented"}
    sturdy = materialize_detached_next_turn_sturdy_survival_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, defender=row["target"], attacker=row["actor"], action=action, move_metadata=move)
    sash = materialize_detached_next_turn_focus_sash_survival_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, holder=row["target"], attacker=row["actor"], action=action, move_metadata=move, held_item_effect_applicability=target_item)
    life = materialize_detached_next_turn_life_orb_immediate_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, attacker=row["actor"], target=row["target"], action=action, move_metadata=move, qualifying_damage=True, held_item_effect_applicability=attacker_item)
    if sturdy.get("status") in {"incomplete", "rejected"}: return {"status": "incomplete", "reason": "detached_sturdy_survival_authority_unavailable"}
    if sash.get("status") in {"incomplete", "rejected"}: return {"status": "incomplete", "reason": "detached_focus_sash_survival_authority_unavailable"}
    if life.get("status") in {"incomplete", "rejected"}: return {"status": "incomplete", "reason": "detached_life_orb_authority_unavailable"}
    return {"status": "resolved", "attacker_item": attacker_item, "target_item": target_item, "sturdy": sturdy, "focus_sash": sash, "life_orb": life}


def _apply_life_orb(leaves: list[dict[str, Any]], authority: Mapping[str, Any], qualifying_damage: bool) -> list[dict[str, Any]]:
    if not qualifying_damage:
        return leaves
    recoil = authority.get("recoil", {})
    if not isinstance(recoil, Mapping): return leaves
    out=[]
    for leaf in leaves:
        updated=deepcopy(leaf); consequence=updated["consequences"]
        consequence["life_orb"] = deepcopy(dict(authority))
        consequence["own_final_hp"] = recoil.get("post_hp", consequence.get("own_final_hp"))
        consequence["self_fainted"] = recoil.get("fainted", consequence.get("self_fainted"))
        out.append(updated)
    return out


def _authority_is_self_consistent(authority: Mapping[str, Any]) -> bool:
    """Detect post-materialization mutation without treating metadata as authority.

    Full replay is intentionally performed by materialization (where the next
    decision state exists); this local check prevents an altered bound row from
    silently becoming executable after that authentication boundary.
    """
    forced, predictive, actions, state = authority.get("forced_continuation"), authority.get("predictive_mechanics"), authority.get("actions"), authority.get("next_decision_state")
    if not isinstance(forced, Mapping) or not isinstance(predictive, Mapping) or not isinstance(actions, Mapping) or not isinstance(state, Mapping) or fingerprint_transition_preview_state(state) != authority.get("source_next_decision_fingerprint"):
        return False
    source_actions, source_sides = forced.get("forced_continuation_actions"), predictive.get("sides")
    if not isinstance(source_actions, Mapping) or not isinstance(source_sides, Mapping):
        return False
    for side in _SIDES:
        row = actions.get(side)
        if not isinstance(row, Mapping):
            return False
        if row.get("status") == "not_applicable":
            if not isinstance(source_actions.get(side), Mapping) or source_actions[side].get("status") != "known_none":
                return False
            continue
        source = source_actions.get(side)
        other = "opponent" if side == "self" else "self"
        if not isinstance(source, Mapping) or row.get("actor") != source.get("actor") or row.get("target") != source.get("resolved_target_owner") or row.get("move_id") != source.get("move_id") or row.get("continuation_action_id") != source.get("continuation_action_id") or row.get("original_charge_action_id") != source.get("original_charge_action_id") or row.get("predictive_actor_mechanics") != source_sides.get(side) or row.get("predictive_target_mechanics") != source_sides.get(other):
            return False
        if row.get("canonical_terminal_effect") != resolve_canonical_standard_charge_turn_two_effect(source.get("move_id")):
            return False
    return True


def _damage_rolls(row: Mapping[str, Any], critical: bool, attacker_item: str | None, defender_item: str | None) -> list[int] | None:
    a, t, move = row["predictive_actor_mechanics"], row["predictive_target_mechanics"], row["canonical_terminal_effect"]["move"]
    av, tv = a["current_final_stats"]["values"], t["current_final_stats"]["values"]
    ast, tst = a["current_stages"]["values"], t["current_stages"]["values"]
    offense, defense = ("attack", "defense") if move["category"] == "physical" else ("special-attack", "special-defense")
    os, ds = select_critical_damage_stages(ast[offense], tst[defense], is_critical=critical)
    try:
        field = _field(a["field"], t["side_conditions"])
        ctx = DamageContext(attacker_level=a["current_level"]["value"], move_power=move["power"], attack_stat=apply_boosts(av[offense], os), defense_stat=apply_boosts(tv[defense], ds), move_type=move["type"], move_id=move["move_id"], attacker_types=tuple(a["types"]["value"]), defender_types=tuple(t["types"]["value"]), is_physical=move["category"] == "physical", is_critical=critical, is_spread=False, field=field, attacker_ability=get_ability(_value(a["ability"])), defender_ability=get_ability(_value(t["ability"])), attacker_item=get_item(attacker_item), defender_item=get_item(defender_item), attacker_hp_current=a["current_hp"]["current_hp"], attacker_hp_max=a["current_hp"]["maximum_hp"], defender_hp_current=t["current_hp"]["current_hp"], defender_hp_max=t["current_hp"]["maximum_hp"], attacker_condition=_condition(a["condition"]) or "none")
        return calc_damage_rolls(ctx)
    except (KeyError, TypeError, ValueError):
        return None


def _hit_event(row: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], critical: bool, index: int, damage: int, probability: Fraction, terminal: Mapping[str, Any]) -> dict[str, Any]:
    hp = target["current_hp"]["current_hp"]; actual = min(hp, damage); post = hp - actual
    consequence = {"damage": actual, "raw_damage": damage, "own_final_hp": actor["current_hp"]["current_hp"], "target_final_hp": post, "target_ko": post == 0, "self_fainted": False, "secondary": None, "sturdy_survival": {"outcome": "not_activated"}, "focus_sash_survival": {"outcome": "not_activated"}}
    if post == 0 and terminal["sturdy"].get("status") == "ready":
        consequence.update({"target_final_hp": 1, "target_ko": False, "sturdy_survival": {"outcome": "activated", "authority": deepcopy(terminal["sturdy"]), "final_hp": 1}})
    elif post == 0:
        sash = apply_detached_focus_sash_single_hit(authority=terminal["focus_sash"], damage=damage, source_action_id=row["continuation_action_id"], source_hit_id=f"roll:{index}")
        if sash.get("status") != "resolved":
            consequence["focus_sash_survival"] = sash
        elif sash.get("outcome") == "activated":
            consequence.update({"target_final_hp": 1, "target_ko": False, "focus_sash_survival": sash, "target_item_after": deepcopy(sash["item_after"])})
    return {"leaf_id": f"{row['continuation_action_id']}:hit:{'critical' if critical else 'noncritical'}:roll:{index}", "candidate_id": row["continuation_action_id"], "action_type": "attack", "branch_path": ("hit", "critical" if critical else "noncritical", f"damage_roll:{index}"), "probability": _fd(probability), "hit_state": "hit", "critical_state": "critical" if critical else "non_critical", "damage_roll": {"roll_index": index, "random_factor_percent": 85 + index}, "consequences": consequence, "provenance": {"attacker": deepcopy(row["actor"]), "target": deepcopy(row["target"]), "move_id": row["move_id"], "execution_authority": deepcopy(dict(row))}}


def _miss_leaf(row: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], probability: Fraction) -> dict[str, Any]:
    return {"leaf_id": f"{row['continuation_action_id']}:miss", "candidate_id": row["continuation_action_id"], "action_type": "attack", "branch_path": ("miss",), "probability": _fd(probability), "hit_state": "miss", "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": 0, "own_final_hp": actor["current_hp"]["current_hp"], "target_final_hp": target["current_hp"]["current_hp"], "target_ko": False, "self_fainted": False, "secondary": None, "sturdy_survival": {"outcome": "not_activated"}, "focus_sash_survival": {"outcome": "not_activated"}, "life_orb": {"outcome": "not_triggered"}}, "provenance": {"attacker": deepcopy(row["actor"]), "target": deepcopy(row["target"]), "move_id": row["move_id"], "execution_authority": deepcopy(dict(row))}}


def _secondary_branches(row: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], event: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    secondary = row["canonical_terminal_effect"]["secondary"]
    if secondary["kind"] == "none":
        return [deepcopy(dict(event))]
    # A KO and Substitute are terminal eligibility gates, before catalog modifiers.
    if event["consequences"]["target_ko"] or target["substitute"].get("status") == "known_active":
        return [deepcopy(dict(event))]
    source = _secondary_source(actor, target)
    if secondary["kind"] == "flinch":
        cap = resolve_probabilistic_target_flinch_effect_capability(move=row["canonical_terminal_effect"]["move"], source_authority=source)
    else:
        cap = resolve_probabilistic_target_status_effect_capability(move=row["canonical_terminal_effect"]["move"], source_authority=source)
    if cap.get("status") != "resolved":
        return None
    chance = _fraction(cap["probability"])
    no = deepcopy(dict(event)); no["leaf_id"] += ":secondary:none"; no["branch_path"] += ("secondary:none",); no["probability"] = _fd(_fraction(event["probability"]) * (1 - chance))
    yes = deepcopy(dict(event)); yes["leaf_id"] += f":secondary:{secondary.get('condition', 'flinch')}"; yes["branch_path"] += (f"secondary:{secondary.get('condition', 'flinch')}",); yes["probability"] = _fd(_fraction(event["probability"]) * chance)
    if secondary["kind"] == "flinch":
        yes["consequences"]["secondary"] = {"state": "flinched", "hypothetical_target_flinch": {"schema_version": "detached-hypothetical-immediate-flinch-v1", "state": "flinched", "provenance": "standard_charge_successful_damage_roll_secondary_v1"}, "authority": cap}
    else:
        yes["consequences"]["secondary"] = {"state": "status_applied", "condition": secondary["condition"], "authority": cap, "provenance": "standard_charge_successful_damage_roll_target_status_secondary_v1"}
    return [no, yes]


def _secondary_source(actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    terrain = actor["field"]
    direct = target["direct_mechanics"].get("combatant", {})
    grounded = direct.get("grounded")
    return {"target_condition": deepcopy(target["condition"]), "target_types": {"status": "known", "values": tuple(target["types"]["value"])}, "attacker_ability": deepcopy(actor["ability"]), "target_ability": deepcopy(target["ability"]), "target_item": deepcopy(target["item"]), "terrain": {"status": "known", "value": terrain.get("terrain", "none")}, "target_groundedness": {"status": "known", "value": "grounded" if grounded is True else "ungrounded" if grounded is False else "unknown"}}


def _pre_action_gate(actor: Mapping[str, Any], target: Mapping[str, Any], move_id: str) -> dict[str, Any]:
    if actor.get("fainted") is True or actor["current_hp"].get("current_hp") == 0:
        return {"status": "resolved", "outcome": "cancelled", "reason": "fainted_actor"}
    condition = actor["condition"]
    current = _condition(condition) or "none"
    if current == "paralysis":
        status = [{"kind": "cancelled_due_to_paralysis", "executes": False, "probability": _fd(Fraction(1, 8))}, {"kind": "executes_after_paralysis", "executes": True, "probability": _fd(Fraction(7, 8))}]
    elif current in {"sleep", "freeze"}:
        progression = actor.get("status_progression", {})
        if not isinstance(progression, Mapping) or progression.get("status") != "known": return {"status": "incomplete", "reason": "champions_status_progression_missing"}
        ability = _gate_ability(actor, target)
        branches = resolve_gate_branches(condition=current, progression=progression.get("value"), ability=ability, move_authority=classify_status_move(move_id))
        if isinstance(branches, Mapping): return dict(branches)
        status = branches
    else:
        status = [{"kind": "executes", "executes": True, "probability": _fd(Fraction(1))}]
    # Confusion is consumed only by a status-executable opportunity.
    confusion = actor.get("confusion_state")
    if not isinstance(confusion, Mapping) or confusion.get("status") == "unknown": return {"status": "incomplete", "reason": "champions_confusion_current_state_unknown"}
    result=[]
    for branch in status:
        if not branch.get("executes"): result.append(branch); continue
        if confusion.get("status") == "known_none": result.append(branch); continue
        progression = actor.get("confusion_progression", {})
        if confusion.get("status") != "known_confused" or not isinstance(progression, Mapping) or progression.get("status") != "known": return {"status": "incomplete", "reason": "champions_confusion_progression_missing_or_stale"}
        rows = resolve_confusion_branches(progression=progression.get("value"), ability=_confusion_ability(actor, target))
        if isinstance(rows, Mapping): return dict(rows)
        for c in rows: result.append({**c, "kind": f"{branch['kind']}:{c['kind']}", "probability": _fd(_fraction(branch["probability"]) * _fraction(c["probability"]))})
    return {"status": "resolved", "outcome": "branches", "branches": tuple(result)}


def _gate_ability(actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    abilities = {"self": _value(actor["ability"]) if actor["owner"]["side"] == "self" else _value(target["ability"]), "opponent": _value(actor["ability"]) if actor["owner"]["side"] == "opponent" else _value(target["ability"])}
    exact = all(isinstance(value, str) and value for value in abilities.values()); own = abilities[actor["owner"]["side"]]; gas = "neutralizing-gas" in abilities.values()
    return {"status": "resolved" if exact else "incomplete", "abilities": abilities, "ability_id": own, "suppressed": gas, "early_bird_active": exact and own == "early-bird" and not gas}


def _confusion_ability(actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    base = _gate_ability(actor, target); base["own_tempo_active"] = base["status"] == "resolved" and base["ability_id"] == "own-tempo" and not base["suppressed"]; return base


def _gate_cancelled_leaf(row: Mapping[str, Any], branch: Mapping[str, Any]) -> dict[str, Any]:
    return {"leaf_id": f"{row['continuation_action_id']}:cancelled:{branch['kind']}", "candidate_id": row["continuation_action_id"], "action_type": "attack", "branch_path": ("pre_action", branch["kind"]), "probability": deepcopy(branch["probability"]), "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": 0, "secondary": None, "execution_failure": branch["kind"]}, "provenance": {"execution_authority": deepcopy(dict(row))}}


def _confusion_self_hit_leaves(row: Mapping[str, Any], actor: Mapping[str, Any], branch: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    direct = actor["direct_mechanics"].get("combatant", {})
    species, disguise = direct.get("species_id"), direct.get("disguise_state")
    if not isinstance(species, str) or disguise not in {None, "intact", "broken"}: return None
    values, stages = actor["current_final_stats"]["values"], actor["current_stages"]["values"]
    try:
        attack, defense = apply_boosts(values["attack"], stages["attack"]), apply_boosts(values["defense"], stages["defense"])
        base = ((((2 * actor["current_level"]["value"]) // 5 + 2) * 40 * attack) // defense) // 50 + 2
    except (KeyError, TypeError, ValueError, ZeroDivisionError): return None
    hp, mimikyu = actor["current_hp"]["current_hp"], species in {"mimikyu", "mimikyu-busted"}
    leaves=[]
    for index, factor in enumerate(range(85, 101)):
        raw = (base * factor) // 100; damage = 0 if mimikyu and disguise == "intact" else min(hp, raw); post = hp - damage
        leaves.append({"leaf_id": f"{row['continuation_action_id']}:confusion-self-hit:{index}", "candidate_id": row["continuation_action_id"], "action_type": "attack", "branch_path": ("pre_action", branch["kind"], f"self_hit_roll:{index}"), "probability": _fd(_fraction(branch["probability"]) * Fraction(1, 16)), "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": {"roll_index": index, "random_factor_percent": factor}, "consequences": {"damage": damage, "raw_damage": raw, "own_final_hp": post, "target_final_hp": actor["current_hp"]["current_hp"], "self_fainted": post == 0, "target_ko": False, "secondary": None, "selected_move_does_not_execute": True, "confusion_self_hit": {"base_power": 40, "type": "typeless", "category": "physical", "contact": False, "disguise_before": disguise, "disguise_after": "broken" if mimikyu and disguise == "intact" else disguise}}, "provenance": {"execution_authority": deepcopy(dict(row)), "provenance": "canonical_detached_confusion_self_hit_v1"}})
    return leaves


def _cancelled(row: Mapping[str, Any], gate: Mapping[str, Any]) -> dict[str, Any]:
    leaf = {"leaf_id": f"{row['continuation_action_id']}:cancelled:{gate['reason']}", "candidate_id": row["continuation_action_id"], "action_type": "attack", "branch_path": ("pre_action_cancelled", gate["reason"]), "probability": _fd(Fraction(1, 1)), "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": 0, "secondary": None, "execution_failure": gate["reason"]}, "provenance": {"execution_authority": deepcopy(dict(row))}}
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "execution_authority": deepcopy(dict(row)), "pre_action_gate": deepcopy(dict(gate)), "terminal_leaves": (leaf,), "terminal_probability_mass": _fd(Fraction(1, 1)), "provenance": "detached_standard_charge_pre_action_cancellation_v1"}


def _accuracy(base: int, accuracy_stage: int, evasion_stage: int) -> Fraction | None:
    if not isinstance(base, int) or not -6 <= accuracy_stage <= 6 or not -6 <= evasion_stage <= 6:
        return None
    stage = accuracy_stage - evasion_stage
    stage = max(-6, min(6, stage))
    multiplier = Fraction(3 + stage, 3) if stage >= 0 else Fraction(3, 3 - stage)
    return min(Fraction(1, 1), Fraction(base, 100) * multiplier)


def _field(field_fact: Mapping[str, Any], side_fact: Mapping[str, Any]) -> Field:
    value = side_fact.get("value", {})
    defender = SideField(reflect=bool(value.get("reflect", False)), light_screen=bool(value.get("light_screen", False)), aurora_veil=bool(value.get("aurora_veil", False)))
    return Field(weather=field_fact.get("weather", "none"), terrain=field_fact.get("terrain", "none"), is_doubles=False, defender_side=defender)


def _volatiles(fact: Mapping[str, Any]) -> tuple[str, ...]:
    value = fact.get("value", fact.get("volatiles", ()))
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _fraction(value: Mapping[str, Any]) -> Fraction: return Fraction(value["numerator"], value["denominator"])
def _incomplete(row: Mapping[str, Any], reason: str) -> dict[str, Any]: return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": reason, "execution_authority": deepcopy(dict(row))}
def _value(value: Mapping[str, Any]) -> str | None: return value.get("value") if value.get("status") == "known" else None
def _condition(value: Mapping[str, Any]) -> str | None: return value.get("condition") if value.get("status") == "known_present" else None
def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": AUTHORITY_SCHEMA_VERSION, "reason": reason}
