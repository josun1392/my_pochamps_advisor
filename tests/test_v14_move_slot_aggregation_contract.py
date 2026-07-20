import pytest
from llm.advisor_candidate_contract import evaluate_move_slots
def test_order_duplicates_and_bound():
    rows=evaluate_move_slots(moves=['a','a'],battle_snapshot={},repositories={'a':{'category':'physical'}})
    assert [x['slot_index'] for x in rows]==[0,1]
    with pytest.raises(ValueError): evaluate_move_slots(moves=list('abcde'),battle_snapshot={},repositories={})
