from llm.advisor_candidate_contract import validate_recommendation
def test_validation_failure_needs_no_raw_response():
    assert validate_recommendation({'recommended_move':None,'recommendation_status':'validation_failed','primary_reasons':[],'risks':[],'alternatives':[]},[])['recommendation_status']=='validation_failed'
