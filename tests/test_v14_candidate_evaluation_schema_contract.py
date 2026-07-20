import pytest
from llm.advisor_candidate_contract import validate_candidate
def test_candidate_statuses_and_required_fields():
    base={'move':'flamethrower','status':'partial','availability':'usable','self_effects':[],'dynamic_move':None,'warnings':[],'unavailable_reasons':['missing_hp']}
    assert validate_candidate(base)['status']=='partial'
    with pytest.raises(ValueError): validate_candidate({'move':'x','status':'bad'})
