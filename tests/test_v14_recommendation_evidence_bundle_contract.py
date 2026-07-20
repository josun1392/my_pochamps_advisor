from llm.advisor_candidate_contract import build_evidence_bundle
def test_bundle_preserves_slot_order():
    rows=[{'move':m,'status':'resolved','availability':'usable','self_effects':[],'dynamic_move':None,'warnings':[],'unavailable_reasons':[]} for m in ('a','b')]
    assert [x['move'] for x in build_evidence_bundle({},rows,[])['candidates']]==['a','b']
