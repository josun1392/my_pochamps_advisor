from __future__ import annotations

from copy import deepcopy

import pytest

from llm.advisor_detached_standard_charge_forced_continuation import (
    ACTION_SCHEMA_VERSION,
    SCHEMA_VERSION,
    materialize_detached_standard_charge_forced_continuation,
    validate_detached_standard_charge_forced_continuation,
)
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_transition_preview import fingerprint_transition_preview_state as fp
from tests.test_standard_charge_lifecycle_eot_next_turn_transport import (
    _finish_replacements,
    _handoff,
    _hazards,
    _ledger_case,
    _phase,
    _post_branch,
    _terminal_authorities,
)


STANDARD = ("sky-attack", "razor-wind", "freeze-shock", "ice-burn")


def _next_state(
    *,
    own_move="sky-attack",
    opponent_move="tackle",
    order="own_first",
):
    ledger, leaf = _ledger_case(
        own_move=own_move,
        opponent_move=opponent_move,
        order=order,
    )
    eot = materialize_end_of_turn_residual_phase(
        phase_input=_phase(ledger, leaf)
    )
    assert eot["status"] == "evaluable", eot
    branch = _post_branch(eot)
    assert branch["status"] == "known", branch
    handoff = _handoff(branch)
    assert handoff["status"] == "resolved", handoff
    state = handoff["next_state"]
    return ledger, leaf, eot, branch, state, handoff["resulting_branch_fingerprint"]


def _forced(state, fingerprint=None):
    return materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint or fp(state),
    )


@pytest.mark.parametrize("move_id", STANDARD)
def test_self_standard_charge_continuation_materializes_forced_request(move_id):
    _, _, _, _, state, fingerprint = _next_state(
        own_move=move_id,
        opponent_move="tackle",
        order="own_first",
    )
    result = _forced(state, fingerprint)
    assert result["status"] == "resolved", result
    row = result["forced_continuation_actions"]["self"]
    assert row["status"] == "resolved"
    assert row["schema_version"] == ACTION_SCHEMA_VERSION
    assert row["move_id"] == move_id
    assert row["lifecycle_state"] == "turn_two_continuation_forced"
    assert row["continuation_forced"] is True
    assert row["user_selection_required"] is False
    assert row["forced_action_materialized"] is True
    assert row["target_occupant_resolved"] is True
    assert row["execution_grant"] is False
    assert row["damage_execution_synthesized"] is False
    assert row["pp_consumption_materialized"] is False
    assert result["action_order_materialized"] is False


def test_opponent_continuation_materializes_actor_neutrally_and_self_is_explicit_none():
    _, _, _, _, state, fingerprint = _next_state(
        own_move="tackle",
        opponent_move="sky-attack",
        order="opponent_first",
    )
    result = _forced(state, fingerprint)
    assert result["status"] == "resolved", result
    own = result["forced_continuation_actions"]["self"]
    opponent = result["forced_continuation_actions"]["opponent"]
    assert own["status"] == "known_none"
    assert own["forced_action_materialized"] is False
    assert opponent["status"] == "resolved"
    assert opponent["actor"] == {
        key: state["active"]["opponent"][key]
        for key in ("session_id", "side", "slot_index", "pokemon_id")
    }
    assert opponent["resolved_target_owner"] == {
        key: state["active"]["self"][key]
        for key in ("session_id", "side", "slot_index", "pokemon_id")
    }


def test_both_sides_charging_materializes_two_independent_forced_requests_without_order():
    _, _, _, _, state, fingerprint = _next_state(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
    )
    result = _forced(state, fingerprint)
    assert result["status"] == "resolved", result
    rows = result["forced_continuation_actions"]
    assert all(rows[side]["status"] == "resolved" for side in ("self", "opponent"))
    assert rows["self"]["move_id"] == "sky-attack"
    assert rows["opponent"]["move_id"] == "ice-burn"
    assert result["action_order_materialized"] is False


def test_ordinary_known_none_rows_remain_explicit_and_missing_authority_is_explicit_none():
    _, _, _, _, state, fingerprint = _next_state(
        own_move="tackle",
        opponent_move="tackle",
        order="own_first",
    )
    result = _forced(state, fingerprint)
    assert result["status"] == "resolved", result
    assert all(
        result["forced_continuation_actions"][side]["status"] == "known_none"
        for side in ("self", "opponent")
    )

    absent = deepcopy(state)
    absent.pop("next_turn_standard_charge_continuation_authorities")
    absent_result = _forced(absent)
    assert absent_result["status"] == "resolved"
    assert all(
        absent_result["forced_continuation_actions"][side]["status"] == "known_none"
        for side in ("self", "opponent")
    )


def test_same_target_identity_resolves_current_occupant_and_locator_stays_identity_free():
    ledger, _, _, _, state, fingerprint = _next_state(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    historical = deepcopy(
        state["next_turn_standard_charge_continuation_authorities"]["self"]
        ["source_charge_context"]["source_target_owner"]
    )
    result = _forced(state, fingerprint)
    row = result["forced_continuation_actions"]["self"]
    assert row["resolved_target_owner"] == historical
    assert row["historical_source_target_owner"] == historical
    assert row["continuation_target_locator"] == {
        "session_id": ledger["session_id"],
        "side": "opponent",
        "slot_index": ledger["opponent_actor"]["slot_index"],
    }
    assert "pokemon_id" not in row["continuation_target_locator"]


def test_target_replacement_reresolves_current_occupant_but_preserves_historical_target():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        opponent_hp=1,
    )
    authorities = _terminal_authorities(
        ledger,
        leaf,
        conditions={"opponent": "burn"},
    )
    phase = _phase(
        ledger,
        leaf,
        authorities=authorities,
        hazards=_hazards(ledger, leaf),
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    branch = _post_branch(eot)
    historical = deepcopy(
        branch["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"]
        ["source_charge_context"]["source_target_owner"]
    )
    replacement = _finish_replacements(
        eot,
        branch,
        bench_sides={"opponent"},
    )
    assert replacement["status"] == "next_decision_ready", replacement
    state = replacement["detached_next_decision_state"]
    result = _forced(state, replacement["next_decision_fingerprint"])
    assert result["status"] == "resolved", result
    row = result["forced_continuation_actions"]["self"]
    assert row["status"] == "resolved"
    assert row["historical_source_target_owner"] == historical
    assert row["original_charge_provenance"]["source_target_owner"] == historical
    assert row["resolved_target_owner"]["pokemon_id"] != historical["pokemon_id"]
    assert row["resolved_target_owner"] == {
        key: state["active"]["opponent"][key]
        for key in ("session_id", "side", "slot_index", "pokemon_id")
    }
    assert row["continuation_target_locator"]["side"] == "opponent"
    assert row["continuation_target_locator"]["slot_index"] == historical["slot_index"]
    assert "pokemon_id" not in row["continuation_target_locator"]


def test_no_new_selected_move_is_required_or_consumed():
    _, _, _, _, state, fingerprint = _next_state(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    state = deepcopy(state)
    state.setdefault("current_state", {})["selected_actions"] = {
        "self": {"action_id": "attack:tackle", "identity": "tackle"}
    }
    result = _forced(state)
    assert result["status"] == "resolved", result
    row = result["forced_continuation_actions"]["self"]
    assert row["move_id"] == "sky-attack"
    assert row["user_selection_required"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        "stale_fingerprint",
        "wrong_schema",
        "forged_charger",
        "active_charger_changed",
        "forged_move",
        "forged_action",
        "malformed_locator",
        "locator_with_pokemon",
        "wrong_target_side",
        "wrong_target_slot",
        "foreign_session",
        "forged_post_eot_fingerprint",
        "forged_charge_context",
        "execution_grant",
        "pp_consumed",
        "pre_resolved_target",
        "malformed_metadata",
    ),
)
def test_forced_continuation_tamper_rejects(mutation):
    _, _, _, _, state, fingerprint = _next_state(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    forged = deepcopy(state)
    row = forged["next_turn_standard_charge_continuation_authorities"]["self"]
    supplied_fingerprint = fingerprint

    if mutation == "stale_fingerprint":
        supplied_fingerprint = "stale"
    elif mutation == "wrong_schema":
        row["schema_version"] = "forged-schema"
    elif mutation == "forged_charger":
        row["charger_owner"]["pokemon_id"] = "forged-charger"
    elif mutation == "active_charger_changed":
        forged["active"]["self"]["pokemon_id"] = "replacement"
    elif mutation == "forged_move":
        row["move_id"] = "razor-wind"
    elif mutation == "forged_action":
        row["action_id"] = "forged-action"
    elif mutation == "malformed_locator":
        row["continuation_target_locator"] = "opponent"
    elif mutation == "locator_with_pokemon":
        row["continuation_target_locator"]["pokemon_id"] = "forged-target"
    elif mutation == "wrong_target_side":
        row["continuation_target_locator"]["side"] = "self"
    elif mutation == "wrong_target_slot":
        row["continuation_target_locator"]["slot_index"] = 7
    elif mutation == "foreign_session":
        row["continuation_target_locator"]["session_id"] = "foreign"
    elif mutation == "forged_post_eot_fingerprint":
        row["source_post_eot_fingerprint"] = "foreign-post-eot"
    elif mutation == "forged_charge_context":
        row["source_charge_context"]["move_id"] = "razor-wind"
    elif mutation == "execution_grant":
        row["execution_grant"] = True
    elif mutation == "pp_consumed":
        row["pp_consumption_materialized"] = True
    elif mutation == "pre_resolved_target":
        row["target_occupant_resolved"] = True
    else:
        (
            row["source_charge_context"]["readiness_authority"]
            ["move_metadata_authority"]["metadata"]["power"]
        ) = 0

    if mutation != "stale_fingerprint":
        supplied_fingerprint = fp(forged)
    result = _forced(forged, supplied_fingerprint)
    assert result["status"] == "rejected", (mutation, result)


def test_current_target_slot_and_current_target_session_are_strictly_bound():
    _, _, _, _, state, _ = _next_state(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    wrong_slot = deepcopy(state)
    wrong_slot["active"]["opponent"]["slot_index"] = 1
    assert _forced(wrong_slot)["status"] == "rejected"

    foreign = deepcopy(state)
    foreign["active"]["opponent"]["session_id"] = "foreign"
    assert _forced(foreign)["status"] == "rejected"


def test_forced_request_rebinds_immutable_metadata_to_current_next_decision_fingerprint():
    _, _, _, _, state, fingerprint = _next_state(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    result = _forced(state, fingerprint)
    row = result["forced_continuation_actions"]["self"]
    metadata = row["move_metadata_authority"]
    assert metadata["source_next_decision_fingerprint"] == fingerprint
    assert metadata["move_id"] == "sky-attack"
    assert metadata["metadata"]["move_id"] == "sky-attack"
    assert metadata["metadata"]["power"] == 140
    assert metadata["metadata"]["category"] == "physical"
    assert metadata["active_attacker"] == row["actor"]
    assert metadata["resolved_target_owner"] == row["resolved_target_owner"]
    assert metadata["source_move_metadata_authority"] != metadata


def test_result_validator_replays_exact_materialization():
    _, _, _, _, state, fingerprint = _next_state(
        own_move="freeze-shock",
        opponent_move="tackle",
        order="own_first",
    )
    result = _forced(state, fingerprint)
    assert result["schema_version"] == SCHEMA_VERSION
    assert validate_detached_standard_charge_forced_continuation(
        result=result,
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    )
    forged = deepcopy(result)
    forged["forced_continuation_actions"]["self"]["execution_grant"] = True
    assert not validate_detached_standard_charge_forced_continuation(
        result=forged,
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    )
