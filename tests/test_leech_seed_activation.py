"""Exact successful action evidence is the sole Leech Seed activation source."""
from copy import deepcopy

from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_leech_seed
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_leech_seed_detached_eot import _seed
from tests.test_leftovers_end_of_turn import _owner_id, _pre


def _effect(state, **changes):
    user, target = _owner_id(state, "opponent"), _owner_id(state, "self")
    value = {
        "schema_version": "successful-action-effect-v1",
        "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state),
        "user": user,
        "target_owner": target,
        "move_id": "leech-seed",
        "target": "opponent",
        "applied_effect": "leech_seed_seeded_volatile",
        "execution_status": "applied",
        "provenance": "trusted_deterministic_leech_seed_application",
    }
    value.update(changes)
    return value


def _seed_row(state, side="self"):
    owner = _owner_id(state, side)
    return next(row for row in state["branch_persistent_effect_authority"]["states"] if row["family"] == "leech_seed" and row["owner"] == owner)


def test_successful_leech_seed_promotes_unknown_captures_source_slot_and_feeds_tier_eight():
    pre = _pre(self_hp=50, opponent_hp=40, self_item=None, opponent_item=None, self_condition="poison", opponent_condition="none")
    _seed(pre["next_state"], target_state="unknown")
    source = pre["next_state"]
    result = apply_successful_leech_seed(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), action_effect=_effect(source))

    assert result["status"] == "resolved"
    assert _seed_row(source)["state"] == "unknown"  # source branch is immutable
    assert _seed_row(result["next_state"])["state"] == "known_active"
    assert _seed_row(result["next_state"])["source_slot"] == {"session_id": "leftovers-eot", "side": "opponent", "slot_index": 0}
    assert _seed_row(result["next_state"], "opponent")["state"] == "known_inactive"

    eot = {"status": "resolved", "next_state": result["next_state"], "boundary": {"phase": "pre_end_of_turn"}}
    resolved = project_per_owner_end_of_turn(pre_end_of_turn=eot, owner=_owner_id(result["next_state"], "self"))
    assert [(row["tier"], row["effect"]) for row in resolved["eot_consequence_trace"]] == [(8, "leech_seed"), (9, "poison_residual")]
    assert resolved["eot_consequence_trace"][0]["target_post_hp"] == 38
    assert resolved["eot_consequence_trace"][0]["recipient_post_hp"] == 52
    assert resolved["eot_consequence_trace"][0]["branch_fingerprint_consumed"] == result["resulting_branch_fingerprint"]
    assert resolved["eot_consequence_trace"][1]["pre_hp"] == 38

    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=resolved)
    assert handoff["status"] == "resolved" and _seed_row(handoff["next_state"])["state"] == "known_active"
    turn_two = {"status": "resolved", "next_state": handoff["next_state"], "boundary": {"phase": "pre_end_of_turn"}}
    assert project_per_owner_end_of_turn(pre_end_of_turn=turn_two, owner=_owner_id(handoff["next_state"], "self"))["status"] == "resolved"


def test_successful_leech_seed_inactive_and_repeat_preserve_other_rows_and_source_slot():
    pre = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")
    _seed(pre["next_state"], target_state="known_inactive")
    source = pre["next_state"]
    preserved = deepcopy([row for row in source["branch_persistent_effect_authority"]["states"] if row["family"] != "leech_seed"])
    result = apply_successful_leech_seed(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), action_effect=_effect(source))
    assert result["status"] == "resolved" and _seed_row(result["next_state"])["state"] == "known_active"
    assert [row for row in result["next_state"]["branch_persistent_effect_authority"]["states"] if row["family"] != "leech_seed"] == preserved

    _seed_row(result["next_state"])["source_slot"] = {"session_id": "leftovers-eot", "side": "opponent", "slot_index": 7}
    repeated = apply_successful_leech_seed(branch_state=result["next_state"], source_branch_fingerprint=fingerprint_transition_preview_state(result["next_state"]), action_effect=_effect(result["next_state"]))
    assert repeated["status"] == "resolved" and _seed_row(repeated["next_state"])["source_slot"]["slot_index"] == 7

    malformed = deepcopy(result["next_state"])
    _seed_row(malformed)["source_slot"] = {"session_id": "leftovers-eot", "side": "opponent"}
    assert apply_successful_leech_seed(branch_state=malformed, source_branch_fingerprint=fingerprint_transition_preview_state(malformed), action_effect=_effect(malformed)) == {"status": "rejected", "reason": "invalid_active_leech_seed_source_slot"}


def test_move_created_seed_reuses_existing_big_root_and_liquid_ooze_resolution():
    pre = _pre(self_hp=10, opponent_hp=10, self_item=None, opponent_item="big-root", self_condition="none", opponent_condition="none")
    _seed(pre["next_state"], target_state="unknown")
    abilities = pre["next_state"]["current_state"]["ability_context"]["current_abilities"]
    next(row for row in abilities if row["side"] == "self")["ability"] = "liquid-ooze"
    source = pre["next_state"]
    applied = apply_successful_leech_seed(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), action_effect=_effect(source))
    eot = {"status": "resolved", "next_state": applied["next_state"], "boundary": {"phase": "pre_end_of_turn"}}

    result = project_per_owner_end_of_turn(pre_end_of_turn=eot, owner=_owner_id(applied["next_state"], "self"))
    row = result["eot_consequence_trace"][0]
    assert row["target_post_hp"] == 0 and row["recipient_post_hp"] == 0 and row["liquid_ooze"] is True


def test_invalid_or_unproven_leech_seed_never_seeds_target_and_switch_clears_move_created_seed():
    pre = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")
    _seed(pre["next_state"], target_state="known_inactive")
    source = pre["next_state"]
    fingerprint = fingerprint_transition_preview_state(source)
    cases = [
        {},
        {"move_success": "allowed"},
        {"selected_move": "leech-seed"},
        _effect(source, move_id="ingrain"),
        _effect(source, applied_effect="aqua_ring_persistent_self_volatile"),
        _effect(source, target="self"),
        _effect(source, user={**_owner_id(source, "opponent"), "pokemon_id": "foreign"}),
        _effect(source, target_owner={**_owner_id(source, "self"), "pokemon_id": "foreign"}),
        _effect(source, source_branch_fingerprint="stale"),
        _effect(source, execution_status="failed"),
    ]
    for record in cases:
        result = apply_successful_leech_seed(branch_state=source, source_branch_fingerprint=fingerprint, action_effect=record)
        assert result["status"] in {"incomplete", "rejected"}
        assert _seed_row(source)["state"] == "known_inactive"

    resolved = apply_successful_leech_seed(branch_state=source, source_branch_fingerprint=fingerprint, action_effect=_effect(source))
    incoming = {
        "provenance": "identity_bound_incoming_current_state_v1",
        "owner": {"session_id": "leftovers-eot", "side": "self", "slot_index": 1, "pokemon_id": "incoming"},
        "hp_authority": {"status": "known", "current_hp": 50, "maximum_hp": 100},
        "fainted_authority": {"status": "known", "value": False},
        "current_state": deepcopy(source["current_state"]),
    }
    switched = materialize_incoming_active_branch(source_branch=resolved["next_state"], source_branch_fingerprint=resolved["resulting_branch_fingerprint"], incoming_authority=incoming)
    assert switched["status"] == "resolved" and "leech_seed_persistent_effect_context" not in switched["next_state"]
