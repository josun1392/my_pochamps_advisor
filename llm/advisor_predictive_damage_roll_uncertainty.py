"""Exact ordered Gen 9 damage-roll ledger for one detached damage interval."""
from collections import Counter
from copy import deepcopy
from typing import Any, Mapping

SCHEMA="deterministic-predictive-damage-roll-uncertainty-v1"

def project_predictive_damage_roll_uncertainty(*,interval:Mapping[str,Any],post_hit:Mapping[str,Any]|None=None,stage_effects:Mapping[str,Any]|None=None)->dict[str,Any]:
 if not isinstance(interval,Mapping) or interval.get("schema_version")!="deterministic-predictive-normal-formula-interval-v1" or interval.get("completeness")!="exact_complete":return _r("incomplete","normal_formula_interval_incomplete")
 rolls=interval.get("exact_damage_rolls")
 if not isinstance(rolls,tuple) or len(rolls)!=16 or any(not isinstance(x,int) or isinstance(x,bool) or x<0 for x in rolls):return _r("incomplete","canonical_sixteen_roll_authority_unavailable")
 post=_by_damage(post_hit,"raw_damage") if post_hit is not None else {}
 stages=_by_damage(stage_effects,"raw_damage") if stage_effects is not None else {}
 outcomes=[]
 for offset,damage in enumerate(rolls):
  row={"roll_index":offset,"random_factor_percent":85+offset,"damage":damage,"probability":{"numerator":1,"denominator":16}}
  if offset in post:row["post_hit_consequence"]=deepcopy(post[offset])
  if offset in stages:row["stage_effect_consequence"]=deepcopy(stages[offset])
  outcomes.append(row)
 counts=Counter(rolls)
 return {"status":"resolved","schema_version":SCHEMA,"session_id":interval["session_id"],"source_branch_fingerprint":interval["source_branch_fingerprint"],"decision_owner":deepcopy(dict(interval["decision_owner"])),"move_id":interval["move_id"],"critical_scope":deepcopy(interval.get("scope",{}).get("critical")),"outcomes":tuple(outcomes),"damage_value_multiplicity":tuple({"damage":damage,"numerator":count,"denominator":16} for damage,count in sorted(counts.items())),"provenance":"canonical_ordered_sixteen_gen9_damage_rolls_v1"}
def _by_damage(value,key):
 branches=value.get("branches") if isinstance(value,Mapping) else None
 return {index:row for index,row in enumerate(branches) if isinstance(row,Mapping) and isinstance(row.get(key),int)} if isinstance(branches,(tuple,list)) and len(branches)==16 else {}
def _r(status,reason):return {"status":status,"schema_version":SCHEMA,"reason":reason}
