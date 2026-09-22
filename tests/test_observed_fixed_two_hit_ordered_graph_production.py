from copy import deepcopy
from fractions import Fraction

from llm.advisor_fixed_two_hit_observation_runtime_admission import admit_observed_fixed_two_hit_result
from llm.advisor_multi_hit_graph_reconciliation import reconcile_observed_fixed_two_hit_graph
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from tests.test_observed_fixed_two_hit_ordered_graph_reconciliation import _artifact,_retain,_mass,_parent,_children,_runtime_state,_execution

def test_sturdy_and_focus_sash_path_local_survival_are_filtered_not_recomputed():
    for kind in ("sturdy","sash"):
        _,artifact,_,_,_=_artifact(power=500,sturdy=kind=="sturdy",sash=kind=="sash");ret=_retain(artifact);leaf=artifact["terminal_leaves"][0]
        parent=_parent(ret,count=2,reason="target_fainted");rec=reconcile_observed_fixed_two_hit_graph(retained_prediction=ret,source_execution_observation=_execution(ret),parent_observation=parent,hit_observations=_children(ret,leaf))
        assert rec["status"]=="resolved" and rec["compatible_terminal_leaf_ids"]
        assert all(p["ordered_hits"][0]["post_hp"]==1 for p in rec["compatible_source_paths"])
