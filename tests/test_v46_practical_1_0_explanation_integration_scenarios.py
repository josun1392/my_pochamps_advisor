"""Offline semantic checks for deterministic recommendation presentation."""
from copy import deepcopy

from llm.advisor_candidate_contract import build_recommendation_presentation_model
from llm.advisor_client import format_recommendation_presentation_text
from llm.advisor_combined_action_recommendation import build_combined_action_envelope, build_combined_action_presentation


class _Snapshot:
    def to_dict(self):
        return {"current_state": {}}


class _BlockerSnapshot:
    def to_dict(self):
        return {"current_state": {"ability_interaction_authority": {"session_id": "s", "source": {"side": "opponent", "slot_index": 0, "pokemon_id": "op"}, "target": {"side": "self", "slot_index": 0, "pokemon_id": "me"}, "ability_id": "shadow-tag", "applicability": "applicable", "interaction": "affecting"}, "switch_candidate_context": {"switch_permission_context": {"status": "permitted"}}, "current_type_context": {"current_types": [{"side": "self", "state": "known", "types": ["normal"]}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": "pressure"}]}}, "battle_state": {"active_player": {"item_status": "absent"}}}


def _prepared(*, moves, switches, summaries=(), snapshot=None):
    return {"candidates": moves, "evidence_bundle": {"turn_snapshot": snapshot or _Snapshot(), "switch_candidates": switches, "known_opponent_threat_summaries": {"threat_summaries": list(summaries)}, "opponent_action_candidates": []}}


def _switch(*, selectable=True):
    return {"candidate_id": "self-switch:s:1:raichu", "action_kind": "switch", "target_pokemon_id": "raichu", "target_slot_index": 1, "selectable": selectable, "availability_supportability": "complete", "reason_code": "switch_available"}


def test_switch_envelope_and_ui_text_preserve_the_exact_deterministic_target():
    prepared = _prepared(moves=[], switches=[_switch()])
    envelope = build_combined_action_envelope(prepared_cycle=prepared)
    presentation = build_combined_action_presentation(envelope=envelope)
    assert envelope["action_kind"] == "switch" and envelope["target_pokemon_id"] == "raichu"
    assert presentation["status"] == "resolved" and presentation["envelope"]["candidate_id"] == envelope["candidate_id"]
    assert format_recommendation_presentation_text(presentation_model=presentation) == presentation["text"]
    envelope["target_pokemon_id"] = "forged"
    assert presentation["envelope"]["target_pokemon_id"] == "raichu"


def test_proven_move_danger_selects_switch_without_presenting_a_new_strategic_score():
    move = {"slot_index": 0, "move": "tackle", "availability": "available"}
    summary = {"self_candidate_id": "self:0:tackle", "known_executed_guaranteed_ohko_threat_exists": True}
    envelope = build_combined_action_envelope(prepared_cycle=_prepared(moves=[move], switches=[_switch()], summaries=[summary]))
    assert envelope["action_kind"] == "switch"
    assert envelope["selection_reason"] == "only_selectable_action"
    assert envelope["danger_tier"] == "neutral_no_positive_danger"
    assert "danger_tier" not in build_combined_action_presentation(envelope=envelope)["text"]


def test_same_danger_tier_move_preference_is_not_exposed_as_a_switch_advantage():
    envelope = build_combined_action_envelope(prepared_cycle=_prepared(moves=[{"slot_index": 0, "move": "tackle", "availability": "available"}], switches=[_switch()]))
    presentation = build_combined_action_presentation(envelope=envelope)
    assert envelope["action_kind"] == "move" and envelope["selection_reason"] == "same_tier_move_preference"
    assert presentation["text"] is None and presentation["action_kind"] is None


def test_blocked_or_incomplete_switch_context_does_not_produce_a_favorable_ui_claim():
    blocked = build_combined_action_envelope(prepared_cycle=_prepared(moves=[], switches=[_switch()], snapshot=_BlockerSnapshot()))
    incomplete = build_combined_action_envelope(prepared_cycle=_prepared(moves=[{"slot_index": 0, "move": "tackle", "availability": "available"}], switches=[_switch(selectable=False)]))
    assert blocked["selection_status"] == "no_selectable_action"
    assert incomplete["action_kind"] == "move" and incomplete["selection_status"] == "resolved"
    assert build_combined_action_presentation(envelope=blocked)["text"] is None
    assert build_combined_action_presentation(envelope=incomplete)["text"] is None


def test_validated_move_presentation_hides_incomplete_or_unsupported_mechanics_details():
    completed = {"status": "resolved", "candidates": [{"slot_index": 0, "move": "tackle", "warnings": []}], "recommendation_result": {"status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "errors": []}, "errors": []}
    model = build_recommendation_presentation_model(completed_cycle=completed)
    candidate = {"selected_candidate_id": 0, "selected_action": {"slot_index": 0, "move": "tackle"}, "explanation_code": "only_rankable_candidate", "evidence": {"mechanics_result": {"status": "insufficient_context", "missing_inputs": ["private_input"]}, "action_order": {"status": "unsupported_mechanic"}, "comparison_facts": {"comparison_tags": ["unsupported_mechanic"]}}, "uncertainty": {}}
    text = format_recommendation_presentation_text(presentation_model={**model, "selected_candidate": deepcopy(candidate)})
    assert "private_input" not in text
    assert "candidate_comparisons" not in text and "raw_response" not in text
