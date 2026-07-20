from llm.advisor_candidate_contract import evaluate_move_slots
def test_bad_slot_does_not_stop_others():
    rows=evaluate_move_slots(moves=['good','bad'],battle_snapshot={},repositories={'good':{'category':'physical'}})
    assert [x['status'] for x in rows]==['resolved','unavailable']
