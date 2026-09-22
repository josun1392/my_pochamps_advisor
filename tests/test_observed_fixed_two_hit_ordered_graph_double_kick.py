from copy import deepcopy

from llm.advisor_fixed_two_hit_observation_runtime_admission import admit_observed_fixed_two_hit_result
from llm.advisor_multi_hit_graph_reconciliation import reconcile_observed_fixed_two_hit_graph
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from tests.test_observed_fixed_two_hit_ordered_graph_reconciliation import _artifact,_retain,_mass,_parent,_children,_runtime_state,_execution

def test_double_kick_production_shape_and_generic_hp_alone_is_insufficient():
    _,artifact,_,_,_=_artifact(move="double-kick");ret=_retain(artifact)
    assert ret["move_id"]=="double-kick"
    generic={"event_kind":"exact_hp_transition_observed","payload":{"hp_before":100,"hp_after":90}}
    rec=reconcile_observed_fixed_two_hit_graph(retained_prediction=ret)
    assert rec["status"]=="incomplete" and _mass(rec)==1
