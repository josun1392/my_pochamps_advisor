"""Fingerprint-bound detached Sturdy readiness for one next-turn attack."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ability_interaction_authority import normalize_ability_applicability_context
from llm.advisor_detached_next_turn_held_item_effect_applicability import _base as _predictive_base, _owner

SCHEMA_VERSION = "detached-next-turn-sturdy-survival-authority-v1"

def materialize_detached_next_turn_sturdy_survival_authority(*, next_decision_state: Mapping[str, Any], next_decision_fingerprint: str, predictive_mechanics: Mapping[str, Any], defender: Mapping[str, Any], attacker: Mapping[str, Any], action: Mapping[str, Any], move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    common = _common(next_decision_state, next_decision_fingerprint, predictive_mechanics, defender, attacker, action, move_metadata)
    if isinstance(common, str): return _result("rejected", common, {})
    ability, hp = common["ability"], common["hp"]
    if hp is None: return _result("incomplete", "sturdy_hp_unknown", common)
    if ability.get("status") != "known": return _result("incomplete", "sturdy_ability_unknown", common)
    if ability["value"] != "sturdy": return _ready("resolved", "known_non_sturdy_ability", common, "known_no_effect", False, False)
    context = normalize_ability_applicability_context(next_decision_state.get("ability_applicability_context"), session_id=defender["session_id"], source=defender, ability_id="sturdy")
    common["sturdy_applicability_authority"] = context
    if context["status"] == "unknown": return _result("incomplete", "sturdy_applicability_unknown", common)
    if context["status"] == "not_applicable": return _ready("resolved", "sturdy_suppressed", common, "known_no_effect", False, False)
    if hp[0] != hp[1] or hp[0] <= 1: return _ready("resolved", "sturdy_hp_not_eligible", common, "known_no_effect", True, False)
    return _ready("ready", None, common, "available", True, True)

def validate_detached_next_turn_sturdy_survival_authority(*, authority: Any, next_decision_state: Mapping[str, Any], next_decision_fingerprint: str, predictive_mechanics: Mapping[str, Any], defender: Mapping[str, Any], attacker: Mapping[str, Any], action: Mapping[str, Any], move_metadata: Mapping[str, Any]) -> str | None:
    expected=materialize_detached_next_turn_sturdy_survival_authority(next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=predictive_mechanics,defender=defender,attacker=attacker,action=action,move_metadata=move_metadata)
    return None if isinstance(authority, Mapping) and deepcopy(dict(authority)) == expected else "detached_sturdy_survival_authority_mismatch"

def _common(state, fingerprint, predictive, defender, attacker, action, move):
    if not _owner(defender) or not _owner(attacker) or defender["side"] == attacker["side"]: return "sturdy_owner_identity_invalid"
    base=_predictive_base(state, fingerprint, predictive, defender)
    if isinstance(base,str): return base
    if predictive.get("active_owners",{}).get(attacker["side"]) != dict(attacker): return "sturdy_attacker_identity_mismatch"
    if not isinstance(action,Mapping) or action.get("action_type") != "attack" or not isinstance(action.get("action_id"),str) or not action["action_id"] or not isinstance(move,Mapping) or not isinstance(move.get("move_id"),str) or action.get("identity",action.get("move_id")) != move["move_id"]: return "sturdy_action_or_move_identity_mismatch"
    row=base["row"]; hpv=row.get("current_hp",{}); hp=(hpv.get("current_hp"),hpv.get("maximum_hp"))
    valid=all(isinstance(x,int) and not isinstance(x,bool) for x in hp) and hp[1]>0 and 0<=hp[0]<=hp[1]
    ability=row.get("ability",{})
    return {"session_id":defender["session_id"],"source_next_decision_fingerprint":fingerprint,"defender":deepcopy(dict(defender)),"attacker":deepcopy(dict(attacker)),"continuation_action_id":action["action_id"],"move_id":move["move_id"],"current_hp":hp[0] if valid else None,"maximum_hp":hp[1] if valid else None,"defender_ability":deepcopy(dict(ability)) if isinstance(ability,Mapping) else {"status":"unknown"},"ability":ability,"hp":hp if valid else None,"predictive_mechanics_authority":deepcopy(dict(predictive))}

def _ready(status,reason,base,outcome,available,eligible): return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"outcome":outcome,"sturdy_available":available,"eligible":eligible,"reason":reason,"provenance":"detached_next_turn_sturdy_survival_authority_v1"}
def _result(status,reason,base): return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
