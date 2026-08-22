from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_successful_action_effect import apply_successful_aqua_ring
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_aqua_ring_detached_eot import _aqua
from tests.test_leftovers_end_of_turn import _pre,_owner_id

def _effect(state, **changes):
    owner = _owner_id(state, "self")
    value = {
        "schema_version": "successful-action-effect-v1",
        "session_id": owner["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state),
        "user": owner,
        "move_id": "aqua-ring",
        "target": "self",
        "applied_effect": "aqua_ring_persistent_self_volatile",
        "execution_status": "applied",
        "provenance": "trusted_deterministic_aqua_ring_application",
    }
    value.update(changes)
    return value


def _aqua_state(state, side="self"):
    owner = _owner_id(state, side)
    return next(
        row["state"]
        for row in state["branch_persistent_effect_authority"]["states"]
        if row["family"] == "aqua_ring" and row["owner"] == owner
    )


def test_successful_aqua_ring_promotes_unknown_and_feeds_same_turn_eot_and_turn_two():
    pre = _pre(self_hp=50, self_item=None, self_condition="none")
    _aqua(pre["next_state"], self_state="unknown")
    source = pre["next_state"]
    result = apply_successful_aqua_ring(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), action_effect=_effect(source))

    assert result["status"] == "resolved"
    assert _aqua_state(source) == "unknown"  # source branch is immutable
    assert _aqua_state(result["next_state"]) == "known_active"
    assert result["resulting_branch_fingerprint"] != result["source_branch_fingerprint"]

    eot = {"status": "resolved", "next_state": result["next_state"], "boundary": {"phase": "pre_end_of_turn"}}
    resolved = project_per_owner_end_of_turn(pre_end_of_turn=eot, owner=_owner_id(result["next_state"], "self"))
    assert [(row["tier"], row["effect"]) for row in resolved["eot_consequence_trace"]] == [(6, "aqua_ring_recovery")]
    assert resolved["eot_consequence_trace"][0]["pre_hp"] == 50
    assert resolved["eot_consequence_trace"][0]["post_hp"] == 56

    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=resolved)
    assert handoff["status"] == "resolved"
    assert _aqua_state(handoff["next_state"]) == "known_active"
    turn_two = {"status": "resolved", "next_state": handoff["next_state"], "boundary": {"phase": "pre_end_of_turn"}}
    assert project_per_owner_end_of_turn(pre_end_of_turn=turn_two, owner=_owner_id(handoff["next_state"], "self"))["status"] == "resolved"


def test_successful_application_transitions_inactive_and_preserves_other_bundle_families():
    pre = _pre(self_item=None, self_condition="none")
    _aqua(pre["next_state"], self_state="known_inactive")
    source = pre["next_state"]
    original = deepcopy(source["branch_persistent_effect_authority"]["states"])
    result = apply_successful_aqua_ring(branch_state=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), action_effect=_effect(source))

    assert result["status"] == "resolved"
    assert _aqua_state(result["next_state"]) == "known_active"
    assert [row for row in result["next_state"]["branch_persistent_effect_authority"]["states"] if row["family"] != "aqua_ring"] == [row for row in original if row["family"] != "aqua_ring"]

    repeated = apply_successful_aqua_ring(branch_state=result["next_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], action_effect=_effect(result["next_state"]))
    rows = [row for row in repeated["next_state"]["branch_persistent_effect_authority"]["states"] if row["family"] == "aqua_ring" and row["owner"]["side"] == "self"]
    assert repeated["status"] == "resolved" and len(rows) == 1 and rows[0]["state"] == "known_active"


def test_eligibility_selection_and_invalid_or_unresolved_effects_never_activate():
    pre = _pre(self_item=None, self_condition="none")
    _aqua(pre["next_state"], self_state="known_inactive")
    source = pre["next_state"]
    fingerprint = fingerprint_transition_preview_state(source)
    cases = [
        {},
        {"move_success": "allowed"},
        {"selected_move": "aqua-ring"},
        _effect(source, move_id="ingrain"),
        _effect(source, target="opponent"),
        _effect(source, applied_effect="ingrain_persistent_self_volatile"),
        _effect(source, execution_status="failed"),
        _effect(source, user={**_owner_id(source, "self"), "pokemon_id": "foreign"}),
        _effect(source, source_branch_fingerprint="stale"),
    ]
    for record in cases:
        result = apply_successful_aqua_ring(branch_state=source, source_branch_fingerprint=fingerprint, action_effect=record)
        assert result["status"] in {"incomplete", "rejected"}
        assert _aqua_state(source) == "known_inactive"
