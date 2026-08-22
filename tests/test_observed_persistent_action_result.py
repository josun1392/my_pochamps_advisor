"""Trusted observed persistent-move results materialize only exact success."""
from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_persistent_action_result import materialize_observed_persistent_action_result
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_aqua_ring, apply_successful_ingrain, apply_successful_leech_seed
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_aqua_ring_detached_eot import _aqua
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leech_seed_detached_eot import _seed
from tests.test_leftovers_end_of_turn import _owner_id, _pre


def _observed(state, move_id, **changes):
    user_side = "opponent" if move_id == "leech-seed" else "self"
    target = "opponent" if move_id == "leech-seed" else "self"
    effects = {
        "aqua-ring": "aqua_ring_persistent_self_volatile",
        "ingrain": "ingrain_persistent_self_volatile",
        "leech-seed": "leech_seed_seeded_volatile",
    }
    user = _owner_id(state, user_side)
    value = {
        "schema_version": "observed-persistent-action-result-v1",
        "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state),
        "user": user,
        "target": target,
        "move_id": move_id,
        "applied_effect": effects[move_id],
        "result": "applied",
        "provenance": "trusted_observed_persistent_action_result_v1",
    }
    if move_id == "leech-seed":
        value["target_owner"] = _owner_id(state, "self")
    value.update(changes)
    return value


def _apply(state, move_id, action):
    adapter = {"aqua-ring": apply_successful_aqua_ring, "ingrain": apply_successful_ingrain, "leech-seed": apply_successful_leech_seed}[move_id]
    return adapter(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), action_effect=action)


def _state(state, family, side="self"):
    owner = _owner_id(state, side)
    return next(row for row in state["branch_persistent_effect_authority"]["states"] if row["family"] == family and row["owner"] == owner)


def test_observed_applied_results_materialize_and_feed_each_canonical_persistent_tier():
    cases = [
        ("aqua-ring", "aqua_ring", _aqua, "aqua_ring_recovery", 6),
        ("ingrain", "ingrain", _ingrain, "ingrain_recovery", 7),
        ("leech-seed", "leech_seed", _seed, "leech_seed", 8),
    ]
    for move_id, family, setup, label, tier in cases:
        pre = _pre(self_hp=50, opponent_hp=40, self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")
        setup(pre["next_state"], self_state="unknown") if family != "leech_seed" else setup(pre["next_state"], target_state="unknown")
        source = pre["next_state"]
        original = deepcopy(source)
        observed = _observed(source, move_id)
        materialized = materialize_observed_persistent_action_result(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), observed_result=observed)
        assert materialized["status"] == "resolved" and source == original
        assert materialize_observed_persistent_action_result(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), observed_result=observed) == materialized

        applied = _apply(source, move_id, materialized["successful_action_effect"])
        owner_side = "self"
        assert applied["status"] == "resolved" and _state(applied["next_state"], family, owner_side)["state"] == "known_active"
        eot = {"status": "resolved", "next_state": applied["next_state"], "boundary": {"phase": "pre_end_of_turn"}}
        result = project_per_owner_end_of_turn(pre_end_of_turn=eot, owner=_owner_id(applied["next_state"], owner_side))
        row = next(row for row in result["eot_consequence_trace"] if row["effect"] == label)
        assert row["tier"] == tier and row["branch_fingerprint_consumed"] == applied["resulting_branch_fingerprint"]
        if family == "leech_seed":
            assert _state(applied["next_state"], family)["source_slot"] == {"session_id": "leftovers-eot", "side": "opponent", "slot_index": 0}
        handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
        assert handoff["status"] == "resolved" and _state(handoff["next_state"], family, owner_side)["state"] == "known_active"
        turn_two = {"status": "resolved", "next_state": handoff["next_state"], "boundary": {"phase": "pre_end_of_turn"}}
        assert project_per_owner_end_of_turn(pre_end_of_turn=turn_two, owner=_owner_id(handoff["next_state"], owner_side))["status"] == "resolved"


def test_observed_results_reject_unproven_wrong_or_foreign_authority():
    pre = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")
    _aqua(pre["next_state"], self_state="unknown")
    source = pre["next_state"]
    fingerprint = fingerprint_transition_preview_state(source)
    cases = [
        _observed(source, "aqua-ring", result="selected"),
        _observed(source, "aqua-ring", result="allowed"),
        _observed(source, "aqua-ring", result="attempted"),
        _observed(source, "aqua-ring", result="failed"),
        _observed(source, "aqua-ring", result="blocked"),
        _observed(source, "aqua-ring", result="unknown"),
        _observed(source, "aqua-ring", result="unresolved"),
        {**_observed(source, "aqua-ring"), "move_id": "leftovers"},
        _observed(source, "aqua-ring", applied_effect="ingrain_persistent_self_volatile"),
        _observed(source, "aqua-ring", target="opponent"),
        _observed(source, "aqua-ring", user={**_owner_id(source, "self"), "pokemon_id": "foreign"}),
        _observed(source, "aqua-ring", source_branch_fingerprint="stale"),
        _observed(source, "aqua-ring", provenance="ui_label"),
    ]
    for observed in cases:
        result = materialize_observed_persistent_action_result(branch_state=source, source_branch_fingerprint=fingerprint, observed_result=observed)
        assert result["status"] in {"incomplete", "rejected", "unsupported"}
        assert _state(source, "aqua_ring")["state"] == "unknown"

    seed = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")
    _seed(seed["next_state"], target_state="unknown")
    leech = _observed(seed["next_state"], "leech-seed", target_owner={**_owner_id(seed["next_state"], "self"), "pokemon_id": "foreign"})
    assert materialize_observed_persistent_action_result(branch_state=seed["next_state"], source_branch_fingerprint=fingerprint_transition_preview_state(seed["next_state"]), observed_result=leech)["status"] == "rejected"


def test_observation_and_action_records_are_historical_after_eot_and_handoff_but_new_branch_observation_is_valid():
    pre = _pre(self_hp=50, self_item=None, self_condition="none")
    _aqua(pre["next_state"], self_state="unknown")
    source = pre["next_state"]
    source_fingerprint = fingerprint_transition_preview_state(source)
    observation = _observed(source, "aqua-ring")
    materialized = materialize_observed_persistent_action_result(branch_state=source, source_branch_fingerprint=source_fingerprint, observed_result=observation)
    applied = _apply(source, "aqua-ring", materialized["successful_action_effect"])
    eot = {"status": "resolved", "next_state": applied["next_state"], "boundary": {"phase": "pre_end_of_turn"}}
    resolved = project_per_owner_end_of_turn(pre_end_of_turn=eot, owner=_owner_id(applied["next_state"], "self"))
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=resolved)

    assert materialize_observed_persistent_action_result(branch_state=applied["next_state"], source_branch_fingerprint=source_fingerprint, observed_result=observation) == {"status": "rejected", "reason": "stale_or_invalid_observed_action_branch"}
    assert materialize_observed_persistent_action_result(branch_state=handoff["next_state"], source_branch_fingerprint=source_fingerprint, observed_result=observation) == {"status": "rejected", "reason": "stale_or_invalid_observed_action_branch"}
    assert apply_successful_aqua_ring(branch_state=handoff["next_state"], source_branch_fingerprint=source_fingerprint, action_effect=materialized["successful_action_effect"]) == {"status": "rejected", "reason": "stale_or_invalid_action_branch"}

    fresh = _observed(handoff["next_state"], "aqua-ring")
    next_materialized = materialize_observed_persistent_action_result(branch_state=handoff["next_state"], source_branch_fingerprint=fingerprint_transition_preview_state(handoff["next_state"]), observed_result=fresh)
    assert next_materialized["status"] == "resolved"
