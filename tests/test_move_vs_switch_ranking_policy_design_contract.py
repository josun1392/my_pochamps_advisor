from llm.advisor_cross_action_danger import compare_cross_action_danger, project_move_cross_action_danger, reduce_switch_cross_action_danger

def _switch(label=None, probability=None):
    damage = {"ko_interpretation": {"ko_supportability": "complete", "primary_ko_label": label}} if label else {"damage_range": {"minimum": 20, "maximum": 70}}
    if probability is not None: damage["ko_probability"] = {"by1": probability}
    return {"damage_evidence": damage, "full_switch_outcome_supportability": "unsupported_mechanic"}

def test_danger_mapping_is_categorical_and_excludes_probability_damage_and_rewards():
    assert project_move_cross_action_danger(candidate_id="m", selectable=True, threat_tier="executed_guaranteed_ohko")["cross_action_danger_tier"] == "executed_guaranteed_self_ko"
    assert project_move_cross_action_danger(candidate_id="m", selectable=True, threat_tier="unresolved_guaranteed_ohko_exposure")["cross_action_danger_tier"] == "unresolved_guaranteed_self_ko_exposure"
    assert project_move_cross_action_danger(candidate_id="m", selectable=True, threat_tier="executed_possible_ohko")["cross_action_danger_tier"] == "possible_self_ko_exposure"
    low = reduce_switch_cross_action_danger(switch_candidate_id="s", selectable=True, incoming_results=[_switch(None, "1/10")])
    high = reduce_switch_cross_action_danger(switch_candidate_id="s2", selectable=True, incoming_results=[_switch(None, "9/10")])
    assert low["cross_action_danger_tier"] == high["cross_action_danger_tier"] == "neutral_no_positive_danger"
    assert low["full_switch_outcome_supportability"] == "unsupported_mechanic"

def test_switch_danger_and_ties_preserve_eligibility_without_cross_kind_policy():
    guaranteed = reduce_switch_cross_action_danger(switch_candidate_id="s", selectable=True, incoming_results=[_switch("guaranteed_ohko")])
    possible = reduce_switch_cross_action_danger(switch_candidate_id="s", selectable=True, incoming_results=[_switch("possible_ohko")])
    move = project_move_cross_action_danger(candidate_id="m", selectable=True, threat_tier=None)
    neutral = reduce_switch_cross_action_danger(switch_candidate_id="s", selectable=True, incoming_results=[_switch()])
    assert guaranteed["cross_action_danger_tier"] == "executed_guaranteed_self_ko"
    assert possible["cross_action_danger_tier"] == "possible_self_ko_exposure"
    assert compare_cross_action_danger(move, neutral) == "tied_cross_kind_unresolved"
    assert compare_cross_action_danger(move, {**neutral, "selectable": False, "cross_action_danger_tier": "executed_guaranteed_self_ko"}) == "left_better_eligibility"
    assert compare_cross_action_danger(move, project_move_cross_action_danger(candidate_id="m2", selectable=True, threat_tier=None)) == "tied_same_kind_native_resolvable"


def test_deterministic_hazard_ko_feeds_existing_danger_tier_without_chip_reward():
    hazard_ko = {"damage_evidence": None, "entry_hazard_result": {"status": "complete", "hazard_ko": True}, "full_switch_outcome_supportability": "unsupported_mechanic"}
    chip_only = {"damage_evidence": None, "entry_hazard_result": {"status": "complete", "hazard_ko": False}, "full_switch_outcome_supportability": "unsupported_mechanic"}
    assert reduce_switch_cross_action_danger(switch_candidate_id="s", selectable=True, incoming_results=[hazard_ko])["cross_action_danger_tier"] == "executed_guaranteed_self_ko"
    assert reduce_switch_cross_action_danger(switch_candidate_id="s", selectable=True, incoming_results=[chip_only])["cross_action_danger_tier"] == "neutral_no_positive_danger"


def test_proven_toxic_spikes_post_turn_ko_uses_existing_danger_tier_only():
    row = {"damage_evidence": {"ko_interpretation": {"ko_supportability": "complete", "primary_ko_label": "no_ko"}}, "post_turn_residual_evidence": {"status": "complete", "guaranteed_ko": True}, "full_switch_outcome_supportability": "unsupported_mechanic"}
    assert reduce_switch_cross_action_danger(switch_candidate_id="s", selectable=True, incoming_results=[row])["cross_action_danger_tier"] == "executed_guaranteed_self_ko"
