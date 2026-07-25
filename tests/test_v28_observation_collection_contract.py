from llm.advisor_observation_collection import ObservationCollection
def r(i,s,k="used_move_observed",session="s"):return {"status":"confirmed","observation":{"observation_id":i,"observation_sequence":s,"event_kind":k,"session_id":session,"payload":{}}}
def test_add_order_duplicate_and_detach():
 c=ObservationCollection("s");assert c.add_confirmation_result(r("b",2))["status"]=="added";assert c.add_confirmation_result(r("a",1))["status"]=="added";assert c.add_confirmation_result(r("a",1))["status"]=="duplicate"
 x=c.snapshot();assert [e["observation_id"] for e in x["ordered_observations"]]==["a","b"];x["ordered_observations"][0]["payload"]["x"]=1;assert "x" not in c.snapshot()["ordered_observations"][0]["payload"]
def test_rejects_and_new_session_isolates():
 c=ObservationCollection("s");assert c.add_confirmation_result({"status":"not_confirmed"})["status"]=="ignored";assert c.add_confirmation_result(r("x",1,session="old"))["status"]=="stale_session";c.add_confirmation_result(r("x",1));old=c.snapshot();c.start_new_session("new");assert c.snapshot()["ordered_observations"]==[] and old["ordered_observations"][0]["session_id"]=="s"
def test_invalid_sequence_conflict_repeated_and_domain_preservation():
 c=ObservationCollection("s")
 for value in (None,0,-1,True,"1"): assert c.add_confirmation_result({"status":"confirmed","observation":{"observation_id":"bad", "observation_sequence":value,"event_kind":"used_move_observed","session_id":"s"}})["status"]=="invalid_observation"
 assert c.add_confirmation_result(r("a",1,"pokemon_switch_observed"))["status"]=="added";assert c.add_confirmation_result(r("a",2,"pokemon_switch_observed"))["status"]=="conflicting_confirmation"
 for index, kind in enumerate(("direct_move_damage_observed","used_move_observed","exact_hp_transition_observed","pokemon_switch_observed","pokemon_faint_observed"),2): assert c.add_confirmation_result(r(kind+str(index),index,kind))["status"]=="added"
 assert len(c.snapshot()["ordered_observations"])==6 and c.snapshot()==c.snapshot()
