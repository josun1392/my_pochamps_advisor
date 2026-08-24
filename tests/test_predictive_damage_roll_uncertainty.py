from llm.advisor_predictive_damage_roll_uncertainty import project_predictive_damage_roll_uncertainty
from tests.test_predictive_critical_damage_context import _context
from llm.advisor_predictive_normal_formula_interval import build_predictive_normal_formula_interval

def test_ordered_sixteen_rolls_keep_factor_identity_and_duplicate_multiplicity():
 state,owner,target,damage,provenance=_context(stages=(0,0))
 interval=build_predictive_normal_formula_interval(branch_state=state,decision_owner=owner,target_owner=target,snapshot_damage_input=damage,stat_provenance=provenance,trusted_level=50)
 result=project_predictive_damage_roll_uncertainty(interval=interval)
 assert result["status"]=="resolved" and len(result["outcomes"])==16
 assert [(x["roll_index"],x["random_factor_percent"],x["probability"]) for x in result["outcomes"]]==[(i,85+i,{"numerator":1,"denominator":16}) for i in range(16)]
 assert sum(row["numerator"] for row in result["damage_value_multiplicity"])==16
 assert len(result["damage_value_multiplicity"])<16

def test_roll_ledger_preserves_critical_scope_without_flattening():
 state,owner,target,damage,provenance=_context(stages=(-2,2))
 normal=build_predictive_normal_formula_interval(branch_state=state,decision_owner=owner,target_owner=target,snapshot_damage_input=damage,stat_provenance=provenance,trusted_level=50)
 critical=build_predictive_normal_formula_interval(branch_state=state,decision_owner=owner,target_owner=target,snapshot_damage_input=damage,stat_provenance=provenance,trusted_level=50,is_critical=True)
 left=project_predictive_damage_roll_uncertainty(interval=normal);right=project_predictive_damage_roll_uncertainty(interval=critical)
 assert left["critical_scope"]=="non_critical_assumed" and right["critical_scope"]=="critical_assumed"
 assert min(x["damage"] for x in right["outcomes"])>min(x["damage"] for x in left["outcomes"])
