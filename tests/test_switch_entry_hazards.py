from copy import deepcopy

from llm.advisor_switch_entry_hazards import evaluate_entry_hazards
from llm.advisor_switch_hazard_authority import build_switch_hazard_context


def _hazards(*, rock="present", spikes=0):
    return build_switch_hazard_context(session_id="hazards-s", affected_side="self", stealth_rock=rock, spikes_layers=spikes)


def _target(**updates):
    target = {
        "hp_authority": {"status": "known", "current_hp": 100, "maximum_hp": 100, "provenance": "user_confirmed_current_hp"},
        "current_type_authority": {"status": "known", "value": ["normal"]},
        "item_authority": {"status": "known", "value": None},
        "ability_authority": {"status": "known", "value": "pressure"},
        "prospective_groundedness_authority": {"status": "grounded"},
    }
    target.update(updates)
    return target


def test_stealth_rock_uses_candidate_b_current_type_and_canonical_fraction():
    resistant = evaluate_entry_hazards(hazards=_hazards(), target=_target(current_type_authority={"status": "known", "value": ["fighting"]}))
    weak = evaluate_entry_hazards(hazards=_hazards(), target=_target(current_type_authority={"status": "known", "value": ["fire", "flying"]}))
    assert resistant["damage"] == 6
    assert weak["damage"] == 50


def test_spikes_requires_exact_b_owned_groundedness_and_uses_exact_layers():
    assert evaluate_entry_hazards(hazards=_hazards(rock="absent", spikes=1), target=_target())["damage"] == 12
    assert evaluate_entry_hazards(hazards=_hazards(rock="absent", spikes=2), target=_target())["damage"] == 16
    assert evaluate_entry_hazards(hazards=_hazards(rock="absent", spikes=3), target=_target())["damage"] == 25
    ungrounded = evaluate_entry_hazards(hazards=_hazards(rock="absent", spikes=3), target=_target(prospective_groundedness_authority={"status": "ungrounded"}))
    assert ungrounded["status"] == "complete" and ungrounded["damage"] == 0
    unknown = evaluate_entry_hazards(hazards=_hazards(rock="absent", spikes=1), target=_target(prospective_groundedness_authority={"status": "unknown"}))
    assert unknown["status"] == "insufficient_context" and unknown["reason"] == "prospective_groundedness_unknown"


def test_unknown_hazards_and_modifiers_fail_closed_but_exact_exceptions_prove_zero():
    assert evaluate_entry_hazards(hazards=_hazards(rock="unknown"), target=_target())["reason"] == "hazard_unknown"
    assert evaluate_entry_hazards(hazards=_hazards(), target=_target(item_authority={"status": "unknown"}))["reason"] == "entry_modifier_unknown"
    boots = evaluate_entry_hazards(hazards=_hazards(rock="unknown", spikes="unknown"), target=_target(item_authority={"status": "known", "value": "heavy-duty-boots"}, ability_authority={"status": "unknown"}))
    guard = evaluate_entry_hazards(hazards=_hazards(rock="unknown", spikes="unknown"), target=_target(item_authority={"status": "unknown"}, ability_authority={"status": "known", "value": "magic-guard"}))
    assert boots["status"] == guard["status"] == "complete"
    assert boots["damage"] == guard["damage"] == 0
    hp_unknown = evaluate_entry_hazards(hazards=_hazards(rock="unknown"), target=_target(hp_authority={"status": "unknown"}, item_authority={"status": "known", "value": "heavy-duty-boots"}))
    assert hp_unknown["status"] == "complete" and hp_unknown["damage"] == 0 and hp_unknown["hazard_ko"] is False


def test_hazard_ko_and_result_are_detached():
    result = evaluate_entry_hazards(hazards=_hazards(rock="present", spikes=3), target=_target(hp_authority={"status": "known", "current_hp": 40, "maximum_hp": 100, "provenance": "user_confirmed_current_hp"}, current_type_authority={"status": "known", "value": ["fire", "flying"]}))
    assert result["damage"] == 75 and result["post_hazard_hp"] == 0 and result["hazard_ko"] is True
    copied = deepcopy(result); copied["damage"] = 0
    assert result["damage"] == 75
