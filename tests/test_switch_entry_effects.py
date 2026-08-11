from llm.advisor_prospective_entry_authority import (
    build_prospective_entry_interactions,
    build_prospective_speed_stage,
    normalize_prospective_entry_interactions,
    normalize_prospective_speed_stage,
)
from llm.advisor_switch_entry_effects import evaluate_switch_entry_effects
from llm.advisor_switch_hazard_authority import build_switch_hazard_context, normalize_switch_hazard_context
from llm.advisor_switch_entry_intimidate_authority import build_switch_entry_intimidate_authority, normalize_switch_entry_intimidate_authority
from llm.advisor_switch_entry_download_authority import build_switch_entry_download_authority, normalize_switch_entry_download_authority


def _hazards(*, toxic=0, web="absent"):
    return build_switch_hazard_context(session_id="entry-s", affected_side="self", stealth_rock="absent", spikes_layers=0, toxic_spikes_layers=toxic, sticky_web=web)


def _target(**updates):
    target = {
        "session_id": "entry-s", "side": "self", "slot_index": 1, "pokemon_id": "b",
        "hp_authority": {"status": "known", "current_hp": 100, "maximum_hp": 100, "provenance": "user_confirmed_current_hp"},
        "current_type_authority": {"status": "known", "value": ["normal"]},
        "item_authority": {"status": "known", "value": None},
        "ability_authority": {"status": "known", "value": "pressure"},
        "persistent_condition_authority": {"status": "known", "value": None},
        "prospective_groundedness_authority": {"status": "grounded"},
        "prospective_speed_stage_authority": {"status": "known", "value": 0},
        "prospective_entry_interactions_authority": {"toxic_spikes": "applicable", "sticky_web": "applicable"},
    }
    target.update(updates)
    return target


def test_toxic_spikes_uses_exact_layers_and_candidate_b_status_authority():
    poison = evaluate_switch_entry_effects(hazards=_hazards(toxic=1), target=_target())
    toxic = evaluate_switch_entry_effects(hazards=_hazards(toxic=2), target=_target())
    assert poison["toxic_spikes_result"] == {"status": "complete", "outcome": "status_applied", "post_condition": "poison"}
    assert toxic["toxic_spikes_result"] == {"status": "complete", "outcome": "status_applied", "post_condition": "toxic"}
    already = evaluate_switch_entry_effects(hazards=_hazards(toxic=2), target=_target(persistent_condition_authority={"status": "known", "value": "burn"}))
    assert already["toxic_spikes_result"]["outcome"] == "already_statused"


def test_toxic_spikes_absorption_immunities_and_unknowns_fail_closed():
    absorbed = evaluate_switch_entry_effects(hazards=_hazards(toxic=2), target=_target(current_type_authority={"status": "known", "value": ["poison"]}))
    steel = evaluate_switch_entry_effects(hazards=_hazards(toxic=2), target=_target(current_type_authority={"status": "known", "value": ["steel"]}))
    ungrounded = evaluate_switch_entry_effects(hazards=_hazards(toxic=2), target=_target(prospective_groundedness_authority={"status": "ungrounded"}))
    assert absorbed["toxic_spikes_result"]["outcome"] == "absorbed" and absorbed["toxic_spikes_result"]["removes_toxic_spikes"] is True
    assert steel["toxic_spikes_result"]["outcome"] == "status_immune"
    assert ungrounded["toxic_spikes_result"]["outcome"] == "ungrounded"
    assert evaluate_switch_entry_effects(hazards=_hazards(toxic=1), target=_target(item_authority={"status": "unknown"}))["toxic_spikes_result"]["reason"] == "item_unknown"
    assert evaluate_switch_entry_effects(hazards=_hazards(toxic=1), target=_target(persistent_condition_authority={"status": "unknown"}))["toxic_spikes_result"]["reason"] == "condition_unknown"
    assert evaluate_switch_entry_effects(hazards=_hazards(toxic=1), target=_target(prospective_entry_interactions_authority={"toxic_spikes": "unknown", "sticky_web": "applicable"}))["toxic_spikes_result"]["reason"] == "toxic_spikes_interaction_unknown"


def test_heavy_duty_boots_prevents_new_effects_without_using_unknown_modifiers():
    result = evaluate_switch_entry_effects(hazards=_hazards(toxic=2, web="present"), target=_target(item_authority={"status": "known", "value": "heavy-duty-boots"}, ability_authority={"status": "unknown"}, current_type_authority={"status": "unknown"}, prospective_groundedness_authority={"status": "unknown"}))
    assert result["toxic_spikes_result"]["outcome"] == "prevented_by_heavy_duty_boots"
    assert result["sticky_web_result"]["outcome"] == "prevented_by_heavy_duty_boots"


def test_sticky_web_uses_b_owned_speed_stage_and_explicit_interaction_authority():
    lowered = evaluate_switch_entry_effects(hazards=_hazards(web="present"), target=_target())
    capped = evaluate_switch_entry_effects(hazards=_hazards(web="present"), target=_target(prospective_speed_stage_authority={"status": "known", "value": -6}))
    blocked = evaluate_switch_entry_effects(hazards=_hazards(web="present"), target=_target(prospective_entry_interactions_authority={"toxic_spikes": "applicable", "sticky_web": "blocked"}))
    unknown = evaluate_switch_entry_effects(hazards=_hazards(web="present"), target=_target(prospective_speed_stage_authority={"status": "unknown"}))
    assert lowered["sticky_web_result"] == {"status": "complete", "outcome": "speed_stage_lowered", "speed_stage_before": 0, "speed_stage_after": -1}
    assert capped["sticky_web_result"]["outcome"] == "speed_stage_minimum"
    assert blocked["sticky_web_result"]["outcome"] == "speed_drop_prevented"
    assert unknown["sticky_web_result"]["reason"] == "prospective_speed_stage_unknown"


def test_new_identity_authorities_and_hazard_v1_upgrade_fail_stale_records_closed():
    speed = build_prospective_speed_stage(session_id="entry-s", side="self", slot_index=1, pokemon_id="b", stage=2)
    interactions = build_prospective_entry_interactions(session_id="entry-s", side="self", slot_index=1, pokemon_id="b", toxic_spikes="applicable", sticky_web="blocked")
    assert normalize_prospective_speed_stage(speed, session_id="entry-s", side="self", slot_index=1, pokemon_id="other")["stage"] == "unknown"
    assert normalize_prospective_entry_interactions(interactions, session_id="entry-s", side="self", slot_index=1, pokemon_id="other")["toxic_spikes"] == "unknown"
    legacy = {"schema_version": "switch-hazard-context-v1", "session_id": "entry-s", "affected_side": "self", "stealth_rock": "present", "spikes_layers": 1}
    upgraded = normalize_switch_hazard_context(legacy, session_id="entry-s", affected_side="self")
    assert upgraded["schema_version"] == "switch-hazard-context-v2" and upgraded["toxic_spikes_layers"] == upgraded["sticky_web"] == "unknown"
    assert normalize_switch_hazard_context({**legacy, "session_id": "old"}, session_id="entry-s", affected_side="self")["stealth_rock"] == "unknown"


def test_intimidate_requires_exact_b_opponent_interaction_and_uses_canonical_stage_clamp():
    authority = build_switch_entry_intimidate_authority(
        session_id="entry-s", source={"side": "self", "slot_index": 1, "pokemon_id": "b"},
        target={"side": "opponent", "slot_index": 0, "pokemon_id": "x"}, interaction="lowered", target_attack_stage=-6,
    )
    lowered = evaluate_switch_entry_effects(hazards=_hazards(), target=_target(slot_index=1, pokemon_id="b", ability_authority={"status": "known", "value": "intimidate"}), intimidate_authority=authority)
    assert lowered["intimidate_result"] == {"status": "complete", "outcome": "attack_stage_minimum", "opponent_identity": {"side": "opponent", "slot_index": 0, "pokemon_id": "x"}, "attack_stage_before": -6, "attack_stage_after": -6}
    reversed_authority = {**authority, "interaction": "reversed", "target_attack_stage": 6}
    reversed_result = evaluate_switch_entry_effects(hazards=_hazards(), target=_target(slot_index=1, pokemon_id="b", ability_authority={"status": "known", "value": "intimidate"}), intimidate_authority=reversed_authority)
    assert reversed_result["intimidate_result"]["outcome"] == "attack_stage_maximum"
    stale = {**authority, "source": {"side": "self", "slot_index": 0, "pokemon_id": "a"}}
    assert evaluate_switch_entry_effects(hazards=_hazards(), target=_target(slot_index=1, pokemon_id="b", ability_authority={"status": "known", "value": "intimidate"}), intimidate_authority=stale)["intimidate_result"]["reason"] == "intimidate_interaction_unknown"
    assert normalize_switch_entry_intimidate_authority(authority, session_id="entry-s", target={"side": "opponent", "slot_index": 0, "pokemon_id": "other"}) is None


def test_intimidate_unknowns_and_hazard_ko_never_become_a_successful_drop():
    target = _target(slot_index=1, pokemon_id="b", ability_authority={"status": "known", "value": "intimidate"})
    assert evaluate_switch_entry_effects(hazards=_hazards(), target=target)["intimidate_result"]["reason"] == "intimidate_interaction_unknown"
    ko_target = _target(slot_index=1, pokemon_id="b", ability_authority={"status": "known", "value": "intimidate"}, hp_authority={"status": "known", "current_hp": 1, "maximum_hp": 100, "provenance": "user_confirmed_current_hp"}, current_type_authority={"status": "known", "value": ["fire"]}, item_authority={"status": "known", "value": None})
    ko_hazards = build_switch_hazard_context(session_id="entry-s", affected_side="self", stealth_rock="present", spikes_layers=0)
    assert evaluate_switch_entry_effects(hazards=ko_hazards, target=ko_target)["intimidate_result"]["outcome"] == "not_activated_hazard_ko"


def test_download_uses_exact_opposing_defenses_tie_rule_and_b_owned_stage():
    target = _target(slot_index=1, pokemon_id="b", ability_authority={"status": "known", "value": "download"}, prospective_offensive_stages_authority={"attack": 0, "special-attack": 5})
    authority = build_switch_entry_download_authority(session_id="entry-s", source={"side": "self", "slot_index": 1, "pokemon_id": "b"}, target={"side": "opponent", "slot_index": 0, "pokemon_id": "x"}, applicability="applicable", target_defense=90, target_special_defense=100)
    physical = evaluate_switch_entry_effects(hazards=_hazards(), target=target, download_authority=authority)["download_result"]
    assert physical == {"status": "complete", "outcome": "attack_stage_raised", "boosted_stat": "attack", "stage_before": 0, "stage_after": 1, "opponent_identity": {"side": "opponent", "slot_index": 0, "pokemon_id": "x"}}
    tied = {**authority, "target_special_defense": 90}
    special = evaluate_switch_entry_effects(hazards=_hazards(), target=target, download_authority=tied)["download_result"]
    assert special["boosted_stat"] == "special-attack" and special["stage_after"] == 6
    assert normalize_switch_entry_download_authority(authority, session_id="entry-s", target={"side": "opponent", "slot_index": 0, "pokemon_id": "other"}) is None


def test_download_unknown_defenses_applicability_or_b_stage_stay_incomplete():
    target = _target(slot_index=1, pokemon_id="b", ability_authority={"status": "known", "value": "download"}, prospective_offensive_stages_authority={"attack": "unknown", "special-attack": 0})
    authority = build_switch_entry_download_authority(session_id="entry-s", source={"side": "self", "slot_index": 1, "pokemon_id": "b"}, target={"side": "opponent", "slot_index": 0, "pokemon_id": "x"}, applicability="applicable", target_defense=90, target_special_defense=100)
    assert evaluate_switch_entry_effects(hazards=_hazards(), target=target, download_authority=authority)["download_result"]["reason"] == "prospective_attack_stage_unknown"
    assert evaluate_switch_entry_effects(hazards=_hazards(), target=target, download_authority={**authority, "applicability": "unknown"})["download_result"]["reason"] == "download_applicability_unknown"
