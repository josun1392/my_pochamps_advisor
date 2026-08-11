from llm.advisor_combined_action_recommendation import build_combined_action_envelope, build_combined_action_presentation
from llm.advisor_client import format_recommendation_presentation_text


class _Snapshot:
    def to_dict(self): return {"current_state": {}}


class _AuthoritySnapshot:
    def __init__(self, *, type_value=("normal",), item_status="absent", ability="pressure", manual="permitted", applicability="applicable", interaction="affecting"):
        self.value = {"current_state": {"ability_interaction_authority": {"session_id": "s", "source": {"side": "opponent", "slot_index": 0, "pokemon_id": "op"}, "target": {"side": "self", "slot_index": 0, "pokemon_id": "me"}, "ability_id": "shadow-tag", "applicability": applicability, "interaction": interaction}, "switch_candidate_context": {"switch_permission_context": {"status": manual}}, "current_type_context": {"current_types": [{"side": "self", "state": "known", "types": list(type_value)}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": ability}]}}, "battle_state": {"active_player": {"item_status": item_status, "known_item_id": "shed-shell" if item_status == "user_confirmed" else None}}}
    def to_dict(self): return self.value


def _prepared(*, moves, switches):
    return {"candidates": moves, "evidence_bundle": {"turn_snapshot": _Snapshot(), "switch_candidates": switches, "known_opponent_threat_summaries": {"threat_summaries": []}, "opponent_action_candidates": []}}


def test_lower_danger_switch_gets_exact_identity_and_bounded_presentation():
    switch = {"candidate_id": "self-switch:s:1:pikachu-b", "action_kind": "switch", "target_pokemon_id": "pikachu-b", "target_slot_index": 1, "selectable": True}
    move = {"slot_index": 0, "move": "tackle", "availability": "available"}
    prepared = _prepared(moves=[move], switches=[switch]); prepared["evidence_bundle"]["known_opponent_threat_summaries"]["threat_summaries"] = [{"self_candidate_id": "self:0:tackle", "known_executed_guaranteed_ohko_threat_exists": True}]
    envelope = build_combined_action_envelope(prepared_cycle=prepared)
    assert envelope["action_kind"] == "switch" and envelope["candidate_id"] == switch["candidate_id"]
    text = build_combined_action_presentation(envelope=envelope)["text"]
    assert "pikachu-b" in text and "안전" not in text
    assert format_recommendation_presentation_text(presentation_model=build_combined_action_presentation(envelope=envelope)) == text


def test_same_tier_move_is_preserved_and_forged_switch_is_rejected():
    switch = {"candidate_id": "self-switch:s:1:pikachu-b", "action_kind": "switch", "target_pokemon_id": "pikachu-b", "target_slot_index": 1, "selectable": True}
    envelope = build_combined_action_envelope(prepared_cycle=_prepared(moves=[{"slot_index": 0, "move": "tackle", "availability": "available"}], switches=[switch]))
    assert envelope["action_kind"] == "move"
    forged = dict(switch, candidate_id="bad")
    assert build_combined_action_envelope(prepared_cycle=_prepared(moves=[], switches=[forged]))["selection_status"] == "no_selectable_action"


def test_equal_switches_remain_unresolved_without_provider_presentation():
    switches = [{"candidate_id": f"self-switch:s:{slot}:same-{slot}", "action_kind": "switch", "target_pokemon_id": f"same-{slot}", "target_slot_index": slot, "selectable": True} for slot in (1, 2)]
    envelope = build_combined_action_envelope(prepared_cycle=_prepared(moves=[], switches=switches))
    assert envelope["selection_status"] == "unresolved_equal_switches"
    assert build_combined_action_presentation(envelope=envelope)["status"] == "unresolved_equal_switches"


def test_frozen_shadow_tag_finalization_blocks_or_preserves_exception_switches():
    switch = {"candidate_id": "self-switch:s:1:b", "action_kind": "switch", "target_pokemon_id": "b", "target_slot_index": 1, "selectable": True, "availability_supportability": "complete", "reason_code": "switch_available"}
    blocked = _prepared(moves=[], switches=[switch]); blocked["evidence_bundle"]["turn_snapshot"] = _AuthoritySnapshot()
    assert build_combined_action_envelope(prepared_cycle=blocked)["selection_status"] == "no_selectable_action"
    ghost = _prepared(moves=[], switches=[switch]); ghost["evidence_bundle"]["turn_snapshot"] = _AuthoritySnapshot(type_value=("ghost",))
    assert build_combined_action_envelope(prepared_cycle=ghost)["action_kind"] == "switch"


def test_frozen_unknown_preserves_manual_but_never_authorizes_unknown_manual_permission():
    switch = {"candidate_id": "self-switch:s:1:b", "action_kind": "switch", "target_pokemon_id": "b", "target_slot_index": 1, "selectable": True, "availability_supportability": "complete", "reason_code": "switch_available"}
    permitted = _prepared(moves=[], switches=[switch]); permitted["evidence_bundle"]["turn_snapshot"] = _AuthoritySnapshot(applicability="unknown")
    assert build_combined_action_envelope(prepared_cycle=permitted)["action_kind"] == "switch"
    unknown = _prepared(moves=[], switches=[switch]); unknown["evidence_bundle"]["turn_snapshot"] = _AuthoritySnapshot(applicability="unknown", manual="unknown")
    assert build_combined_action_envelope(prepared_cycle=unknown)["selection_status"] == "no_selectable_action"
