import pytest
from llm.advisor_candidate_contract import validate_recommendation
def test_exact_set_recommendation():
    response={'recommended_move':'a','recommendation_status':'resolved','primary_reasons':[],'risks':[],'alternatives':[]}
    assert validate_recommendation(response,[{'move':'a'}])['recommended_move']=='a'
    response['recommended_move']='x'
    with pytest.raises(ValueError): validate_recommendation(response,[{'move':'a'}])
