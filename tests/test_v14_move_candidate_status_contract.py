from llm.advisor_candidate_contract import evaluate_move_candidate
def test_invalid_and_missing_metadata_are_unavailable():
    assert evaluate_move_candidate(slot_index=0,move=None,battle_snapshot={},repositories={})['status']=='unavailable'
    assert evaluate_move_candidate(slot_index=0,move='missing',battle_snapshot={},repositories={})['unavailable_reasons']==['move_metadata_unavailable']
