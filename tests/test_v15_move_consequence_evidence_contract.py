from llm.advisor_candidate_contract import _comparison_facts, evaluate_move_candidate
from llm.advisor_client import format_recommendation_presentation_text
from llm.move_consequence_evidence import evaluate_move_consequence_evidence


def test_canonical_consequence_tags_do_not_calculate_hp_or_ranking_value():
    assert evaluate_move_consequence_evidence(move_id="brave-bird", metadata={"category": "physical", "drain": -33}) == {"status": "known", "consequence_tags": ["recoil"], "canonical_ratio": 33, "uncertainty": []}
    assert evaluate_move_consequence_evidence(move_id="drain-punch", metadata={"category": "physical", "drain": 50})["consequence_tags"] == ["drain_or_healing_from_damage"]
    assert "charge_turn" in evaluate_move_consequence_evidence(move_id="solar-beam", metadata={"category": "special"})["consequence_tags"]
    assert "recharge_turn" in evaluate_move_consequence_evidence(move_id="hyper-beam", metadata={"category": "special"})["consequence_tags"]
    assert "self_faint" in evaluate_move_consequence_evidence(move_id="explosion", metadata={"category": "physical"})["consequence_tags"]
    assert "forced_switch" in evaluate_move_consequence_evidence(move_id="roar", metadata={"category": "status"})["consequence_tags"]
    evidence = evaluate_move_consequence_evidence(move_id="brave-bird", metadata={"category": "physical", "drain": -33})
    assert set(evidence) == {"status", "consequence_tags", "canonical_ratio", "uncertainty"}


def test_unknown_and_dynamic_consequences_remain_bounded():
    assert evaluate_move_consequence_evidence(move_id="tackle", metadata={"category": "physical"})["status"] == "no_known_consequence"
    assert evaluate_move_consequence_evidence(move_id="dynamic", metadata={"category": "physical", "dynamic_consequence": True})["status"] == "unsupported_mechanic"


def test_candidate_facts_and_presentation_keep_consequence_candidate_local():
    recoil = evaluate_move_candidate(slot_index=0, move="brave-bird", battle_snapshot={}, repositories={"brave-bird": {"category": "physical", "power": 120, "type": "flying", "drain": -33}})
    plain = evaluate_move_candidate(slot_index=1, move="tackle", battle_snapshot={}, repositories={"tackle": {"category": "physical", "power": 40, "type": "normal"}})
    facts = _comparison_facts(candidate=recoil, comparison={"comparison_status": "rankable"}, candidates=[recoil, plain])
    assert "known_recoil" in facts["comparison_tags"] and "move_consequence_evidence" in facts["evidence_refs"]
    presentation = {"status": "resolved", "recommended_move": "brave-bird", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": [], "selected_candidate": {"selected_action": {"slot_index": 0, "move": "brave-bird"}, "evidence": {"mechanics_result": {"status": "insufficient_context"}, "action_order": {"status": "insufficient_context"}, "move_consequence_evidence": recoil["move_consequence_evidence"], "comparison_facts": facts}}}
    text = format_recommendation_presentation_text(presentation_model=presentation)
    assert "기술 사용 시 주의" in text and "canonical_ratio" not in text and "HP" not in text
