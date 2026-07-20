from llm.advisor_candidate_contract import evaluate_move_candidate
def test_damage_and_status_candidates():
    repo={'flame':{'category':'special','minimum':1,'maximum':2},'protect':{'category':'status'}}
    assert evaluate_move_candidate(slot_index=0,move='flame',battle_snapshot={},repositories=repo)['status']=='resolved'
    assert evaluate_move_candidate(slot_index=1,move='protect',battle_snapshot={},repositories=repo)['damage']['status']=='not_applicable'
