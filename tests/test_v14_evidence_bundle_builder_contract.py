from llm.advisor_candidate_contract import build_evidence_bundle
def test_bundle_copies_inputs_and_retains_reasons():
    row={'move':'a','status':'unavailable','availability':'unavailable','damage':{'status':'unavailable'},'self_effects':[],'dynamic_move':{'status':'unavailable'},'warnings':['warning'],'unavailable_reasons':['x']}
    snapshot={'x':[1]}; limitations=['limit']; bundle=build_evidence_bundle(snapshot,[row],limitations)
    row['damage']['status']='resolved'; row['dynamic_move']['status']='resolved'; row['warnings'].append('mutated'); row['unavailable_reasons'].append('mutated'); snapshot['x'].append(2); limitations.append('mutated')
    assert bundle['comparison_policy']['no_untrusted_inference']
    assert bundle['battle_snapshot_summary']=={'x':[1]} and bundle['known_limitations']==['limit']
    assert bundle['candidates'][0]['damage']=={'status':'unavailable'} and bundle['candidates'][0]['dynamic_move']=={'status':'unavailable'}
    assert bundle['candidates'][0]['warnings']==['warning'] and bundle['candidates'][0]['unavailable_reasons']==['x']
