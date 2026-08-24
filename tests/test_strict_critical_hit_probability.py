from copy import deepcopy

from llm.advisor_runtime_strategy_d0 import build_runtime_d0_strict_critical_hit_probability_assessment
from tests.test_runtime_d0_critical_hit_authority import _d0, _owner, _snapshot, _state


def _assessment(state, move_id="tackle"):
    snapshot, d0 = _d0(state)
    return build_runtime_d0_strict_critical_hit_probability_assessment(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state),
        target=_owner(state, "opponent"), move_metadata={"move_id": move_id},
    )


def test_exact_gen9_base_high_and_guaranteed_crit_probabilities_are_rational():
    base = _assessment(_state())
    high = _assessment(_state(), "slash")
    guaranteed = _assessment(_state(), "flower-trick")
    assert (base["crit_stage"], base["critical_probability"]) == (0, {"numerator": 1, "denominator": 24})
    assert (high["crit_stage"], high["critical_probability"]) == (1, {"numerator": 1, "denominator": 8})
    assert guaranteed["always_crit"] is True
    assert guaranteed["critical_probability"] == {"numerator": 1, "denominator": 1}


def test_stage_contributors_and_canonical_stage_clamp_preserve_exact_probability():
    super_luck = _state(); super_luck["self_side"]["pokemon"][0]["current_ability"] = "super-luck"
    focus = _state(); focus["self_side"]["pokemon"][0]["current_crit_volatiles"] = ["focus-energy"]
    item = _state(); item["self_side"]["pokemon"][0].update(known_item="scope-lens", known_item_provenance={"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"})
    capped = _state(); capped["self_side"]["pokemon"][0].update(current_ability="super-luck", known_item="scope-lens", known_item_provenance={"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"}, current_crit_volatiles=["focus-energy"])
    assert _assessment(super_luck)["critical_probability"] == {"numerator": 1, "denominator": 8}
    assert _assessment(focus)["critical_probability"] == {"numerator": 1, "denominator": 2}
    assert _assessment(item)["critical_probability"] == {"numerator": 1, "denominator": 8}
    result = _assessment(capped)
    assert (result["crit_stage"], result["effective_crit_stage"], result["critical_probability"]) == (4, 3, {"numerator": 1, "denominator": 1})


def test_merciless_and_positive_blockers_produce_canonical_exact_results():
    merciless = _state(); merciless["self_side"]["pokemon"][0]["current_ability"] = "merciless"; merciless["opponent_side"]["pokemon"][0]["condition"] = "poison"
    armor = _state(); armor["opponent_side"]["pokemon"][0]["current_ability"] = "battle-armor"
    lucky = _state(); lucky["opponent_side"]["side_conditions"] = ["lucky-chant"]
    assert _assessment(merciless)["critical_probability"] == {"numerator": 1, "denominator": 1}
    for state in (armor, lucky):
        result = _assessment(state)
        assert result["result"] == "crit_blocked"
        assert result["critical_probability"] == {"numerator": 0, "denominator": 1}


def test_incomplete_unsupported_and_rejected_authority_fail_closed():
    incomplete = _state(); incomplete["self_side"]["pokemon"][0]["current_crit_volatiles"] = {"knowledge": "unknown"}; incomplete["self_side"]["pokemon"][0].pop("current_crit_volatiles_provenance")
    unsupported = _state(); unsupported["self_side"]["pokemon"][0]["current_ability"] = "compound-eyes"
    assert _assessment(incomplete)["status"] == "incomplete"
    assert _assessment(unsupported)["status"] == "unsupported"
    state = _state(); snapshot, d0 = _d0(state); state["last_applied_observation_sequence"] = 1
    stale = build_runtime_d0_strict_critical_hit_probability_assessment(strategy_d0=d0, runtime_snapshot=_snapshot(state), attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": "tackle"})
    assert stale["status"] == "rejected"


def test_result_is_detached_and_keeps_runtime_bindings_without_mutation():
    state = _state(); original = deepcopy(state)
    result = _assessment(state)
    assert result["status"] == "resolved"
    assert result["session_id"] == state["session_id"]
    assert result["attacker"] == _owner(state)
    result["critical_hit_authority"]["capability_resolution"]["crit_stage"] = 99
    assert state == original
