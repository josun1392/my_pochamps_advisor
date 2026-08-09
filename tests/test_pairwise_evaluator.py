from copy import deepcopy

from llm.advisor_pairwise_evaluator import _preemption, evaluate_self_opponent_pairs


class Snapshot:
 def to_dict(self): return {"current_state": {}}


REPO={"tackle":{"move_id":"tackle","priority":0,"category":"physical","type":"normal"},"quick":{"move_id":"quick","priority":1,"category":"physical","type":"normal"}}


def _self(slot, move, ko="no"):
 return {"slot_index":slot,"move":move,"move_success":{"status":"allowed"},"mechanics_result":{"status":"known","ko_interpretation":{"ko_supportability":"complete","ohko_result":ko}}}


def _opponent(identifier, move, ko="no"):
 return {"candidate_id":identifier,"session_id":"s","move_id":move,"move_success":{"status":"allowed"},"incoming_damage":{"status":"known","ko_interpretation":{"ko_supportability":"complete","ohko_result":ko}}}


def test_cartesian_pairs_are_deterministic_and_preserve_partial_set_metadata():
 self_rows=[_self(0,"tackle"),_self(1,"quick")]; opponent=[_opponent("opponent-action:s:a:tackle:0","tackle"),_opponent("opponent-action:s:a:quick:1","quick")]
 result=evaluate_self_opponent_pairs(self_candidates=self_rows,opponent_evaluation={"known_move_state":"partially_known","candidate_set_complete":False,"unknown_slots_remaining":2,"opponent_action_evaluations":opponent},turn_snapshot=Snapshot(),repositories=REPO)
 assert result["pair_count"]==4 and result["opponent_candidate_set_complete"] is False
 assert len({row["pair_id"] for row in result["pairs"]})==4
 assert result["pairs"][0]["self_candidate_id"]=="self:0:tackle"


def test_guaranteed_first_ohko_only_preempts_and_possible_or_blocked_does_not():
 order={"status":"acts_first"}; allowed={"status":"allowed"}; blocked={"status":"blocked"}
 guaranteed={"ko_interpretation":{"ko_supportability":"complete","ohko_result":"guaranteed"}}
 possible={"ko_interpretation":{"ko_supportability":"complete","ohko_result":"possible"}}
 assert _preemption(order,allowed,allowed,guaranteed,possible)==("executable","preempted")
 assert _preemption(order,allowed,allowed,possible,guaranteed)==("executable","executable")
 assert _preemption(order,blocked,allowed,guaranteed,possible)==("blocked","executable")
 assert _preemption({"status":"speed_tie"},allowed,allowed,guaranteed,guaranteed)==("executable","executable")


def test_pair_construction_does_not_mutate_source_evidence():
 self_row=_self(0,"tackle"); opponent_row=_opponent("opponent-action:s:a:tackle:0","tackle")
 original=(deepcopy(self_row),deepcopy(opponent_row))
 result=evaluate_self_opponent_pairs(self_candidates=[self_row],opponent_evaluation={"opponent_action_evaluations":[opponent_row]},turn_snapshot=Snapshot(),repositories=REPO)
 result["pairs"][0]["self_move_success"]["status"]="blocked"
 assert (self_row,opponent_row)==original
