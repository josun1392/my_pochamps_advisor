"""Apply a drain consequence to an already materialized damaging terminal leaf."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_drain_move_family import resolve_canonical_drain_move

SCHEMA_VERSION = "detached-drain-consequence-v1"

def apply_detached_drain_consequence(*, runtime_snapshot: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any], leaf: Mapping[str, Any]) -> dict[str, Any]:
    canonical = resolve_canonical_drain_move(move=move_metadata)
    if canonical.get("status") == "unsupported": return {"status":"resolved", "leaf":deepcopy(dict(leaf))}
    if canonical.get("status") != "resolved": return {"status":canonical.get("status","rejected"), "reason":canonical.get("reason","drain_catalog_unavailable")}
    consequences = leaf.get("consequences") if isinstance(leaf, Mapping) else None
    source = consequences.get("source_hit_context") if isinstance(consequences, Mapping) else None
    if not isinstance(consequences, Mapping) or not isinstance(source, Mapping): return {"status":"rejected", "reason":"drain_source_hit_missing"}
    if leaf.get("hit_state") != "hit" or source.get("target_routing") != "target": return {"status":"resolved", "leaf":deepcopy(dict(leaf))}
    pre, post, actual = source.get("target_pre_hp"), source.get("target_post_hp"), source.get("actual_damage")
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (pre, post, actual)) or not 0 <= post <= pre or actual != pre - post: return {"status":"rejected", "reason":"drain_actual_target_hp_loss_invalid"}
    if actual == 0: return {"status":"resolved", "leaf":deepcopy(dict(leaf))}
    own = consequences.get("own_final_hp")
    maximum = _max_hp(runtime_snapshot, attacker)
    if not isinstance(own, int) or isinstance(own, bool) or maximum is None or not 0 <= own <= maximum: return {"status":"incomplete", "reason":"drain_path_local_attacker_hp_unknown"}
    item, ability = _current_item(runtime_snapshot, attacker), _current_ability(runtime_snapshot, target)
    if item is None or ability is None: return {"status":"incomplete", "reason":"drain_item_or_ability_authority_unknown"}
    num, den = canonical["effect"]["drain_numerator"], canonical["effect"]["drain_denominator"]
    nominal = (actual * num + den // 2) // den
    would_be = (nominal * 5324) // 4096 if item == "big-root" else nominal
    liquid = ability == "liquid-ooze"
    post_own = max(0, own - would_be) if liquid else min(maximum, own + would_be)
    row = deepcopy(dict(leaf)); updated = deepcopy(dict(consequences)); updated["own_final_hp"] = post_own; updated["self_fainted"] = post_own == 0
    updated["drain"] = {"schema_version":SCHEMA_VERSION, "move_id":move_metadata["move_id"], "drain_family":canonical["effect"]["drain_family"], "fraction":{"numerator":num,"denominator":den}, "source_hit":deepcopy(dict(source)), "actual_target_hp_loss":actual, "attacker_pre_hp":own, "attacker_max_hp":maximum, "nominal_recovery":nominal, "big_root":{"applies":item == "big-root", "modifier":{"numerator":5324,"denominator":4096}, "would_be_recovery":would_be}, "liquid_ooze":liquid, "effective_heal":0 if liquid else post_own-own, "reversed_damage":would_be if liquid else 0, "attacker_post_hp":post_own, "attacker_fainted":post_own == 0}
    row["consequences"] = updated
    row["provenance"] = {**deepcopy(dict(row.get("provenance", {}))), "drain_catalog":deepcopy(canonical)}
    return {"status":"resolved", "leaf":row}

def _max_hp(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> int | None:
    state=snapshot.get("state") if isinstance(snapshot, Mapping) else None; side=state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None; roster=side.get("pokemon") if isinstance(side, Mapping) else None; row=roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    value=row.get("max_hp") if isinstance(row, Mapping) and row.get("pokemon_id")==owner.get("pokemon_id") else None
    return value if isinstance(value,int) and not isinstance(value,bool) and value>0 else None

def _pokemon(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    state=snapshot.get("state") if isinstance(snapshot, Mapping) else None; side=state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None; roster=side.get("pokemon") if isinstance(side, Mapping) else None; row=roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    return row if isinstance(row, Mapping) and row.get("pokemon_id")==owner.get("pokemon_id") else None
def _trusted(value: Any, kind: str) -> bool: return isinstance(value, Mapping) and value.get("event_kind")==kind and value.get("trust")=="user_confirmed_observation"
def _current_item(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> str | None:
    row=_pokemon(snapshot,owner); provenance=row.get("known_item_provenance") if isinstance(row,Mapping) else None
    if not _trusted(provenance,"current_item_observed"): return None
    if provenance.get("status")=="known_absent": return ""
    item=row.get("known_item")
    return item if provenance.get("status")=="known" and isinstance(item,str) and item else None
def _current_ability(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> str | None:
    row=_pokemon(snapshot,owner); ability=row.get("current_ability") if isinstance(row,Mapping) else None
    return ability if isinstance(ability,str) and ability and _trusted(row.get("current_ability_provenance"),"current_ability_observed") else None
