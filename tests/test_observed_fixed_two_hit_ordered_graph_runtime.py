from copy import deepcopy

from llm.advisor_fixed_two_hit_observation_runtime_admission import admit_observed_fixed_two_hit_result
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from tests.test_observed_fixed_two_hit_ordered_graph_reconciliation import _artifact,_retain,_runtime_state,_execution

class _FastManager(BattleObservationRuntimeSessionManager):
    def __init__(self,state,rows):
        self.state=deepcopy(state);self.rows=deepcopy(list(rows));self.seq=max((x.get("observation_sequence",0) for x in self.rows),default=0)
    def capture_runtime_state_snapshot(self,session_id):
        return {"status":"runtime_snapshot_ready","session_id":session_id,"state":deepcopy(self.state),"state_fingerprint":"test-runtime"}
    def read_collection_snapshot(self):
        return {"status":"ready","session_id":self.state["session_id"],"ordered_observations":deepcopy(self.rows)}
    def allocate_observation_sequence(self):
        self.seq+=1;return {"status":"allocated","session_id":self.state["session_id"],"observation_sequence":self.seq}
    def preview(self,session_id,snapshot):
        return {"status":"preview_ready"}
    def admit_confirmations_atomically(self,session_id,confirmations):
        for row in confirmations:
            obs=deepcopy(row["observation"])
            old=next((x for x in self.rows if x.get("observation_id")==obs.get("observation_id")),None)
            if old is not None and old!=obs:return {"status":"conflicting_confirmation"}
            if old is None:self.rows.append(obs)
        return {"status":"added"}
    def apply(self,session_id,snapshot):
        for obs in sorted(snapshot.get("ordered_observations",()),key=lambda x:x.get("observation_sequence",0)):
            if obs.get("event_kind")=="exact_hp_transition_observed":
                side=obs.get("side");slot=obs.get("slot_index");pokemon=self.state[f"{side}_side"]["pokemon"][slot]
                pokemon["current_hp"]=obs["payload"]["hp_after"];pokemon["fainted"]=pokemon["current_hp"]==0
        return {"status":"applied"}

def test_production_double_hit_atomic_hp_duplicate_and_conflict():
    _predictive_state,artifact,action,own,_=_artifact(target_hp=1);ret=_retain(artifact)
    state=_runtime_state();state["session_id"]=ret["session_id"]
    state["self_side"]["pokemon"][0]["pokemon_id"]=ret["actor"]["pokemon_id"]
    state["opponent_side"]["pokemon"][0]["pokemon_id"]=ret["target"]["pokemon_id"]
    first_pre=artifact["terminal_leaves"][0]["ordered_hits"][0]["pre_hp"]
    state["opponent_side"]["pokemon"][0]["current_hp"]=first_pre
    state["opponent_side"]["pokemon"][0]["max_hp"]=max(first_pre,100)
    execution=_execution(ret)
    manager=_FastManager(state,[execution])
    leaf=artifact["terminal_leaves"][0]
    hits=tuple({"hit_index":h["hit_index"],"hp_before":h["pre_hp"],"hp_after":h["post_hp"],"critical_state":None,"related_contact_observation_ids":()} for h in leaf["ordered_hits"])
    first=admit_observed_fixed_two_hit_result(runtime_session_manager=manager,captured_session_id=state["session_id"],retained_prediction=ret,turn_number=1,source_execution_observation=execution,action_outcome="landed",landed_hit_count=len(hits),terminal_reason=leaf["consequences"]["terminal_reason"],ordered_hits=hits)
    assert first["status"]=="resolved",first
    assert first["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["current_hp"]==hits[-1]["hp_after"]
    dup=admit_observed_fixed_two_hit_result(runtime_session_manager=manager,captured_session_id=state["session_id"],retained_prediction=ret,turn_number=1,source_execution_observation=execution,action_outcome="landed",landed_hit_count=len(hits),terminal_reason=leaf["consequences"]["terminal_reason"],ordered_hits=hits)
    assert dup["status"]=="resolved" and dup["idempotent"] is True
    assert dup["reconciliation"]["source_observation_ids"]==first["reconciliation"]["source_observation_ids"]
    changed=list(deepcopy(hits));changed[-1]["hp_after"]=changed[-1]["hp_before"]
    assert admit_observed_fixed_two_hit_result(runtime_session_manager=manager,captured_session_id=state["session_id"],retained_prediction=ret,turn_number=1,source_execution_observation=execution,action_outcome="landed",landed_hit_count=len(hits),terminal_reason=leaf["consequences"]["terminal_reason"],ordered_hits=changed)["status"]=="rejected"
