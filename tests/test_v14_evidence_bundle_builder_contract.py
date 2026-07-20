from llm.advisor_candidate_contract import build_evidence_bundle
def test_bundle_copies_inputs_and_retains_reasons():
    row={'move':'a','status':'unavailable','availability':'unavailable','self_effects':[],'dynamic_move':None,'warnings':[],'unavailable_reasons':['x']}
    bundle=build_evidence_bundle({'x':1},[row],['limit']); row['unavailable_reasons'].append('mutated')
    assert bundle['comparison_policy']['no_untrusted_inference'] and bundle['candidates'][0]['unavailable_reasons']==['x']
