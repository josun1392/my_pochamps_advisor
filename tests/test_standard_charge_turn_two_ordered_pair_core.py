"""Production-shaped Razor Wind release-pair regression.

The fixture deliberately enters through runtime confirmations and the reducer,
then uses the real D0 order authority, immediate pair and exact ledger.
"""
from copy import deepcopy

from llm.advisor_lifecycle_confirmation import (
    LifecycleConfirmationBoundary, TAILWIND_SOURCE, TRICK_ROOM_SOURCE,
    USED_MOVE_SOURCE, USER_TRUST,
)
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_action_order_authority import freeze_runtime_d0_action_order_authority
from llm.advisor_runtime_d0_opponent_action_authority import freeze_runtime_d0_opponent_known_move_action_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_standard_charge_turn_two_ordered_pair_core import materialize_standard_charge_turn_two_ordered_pair_core
from tests.test_detached_opponent_response_profile import _complete_state, _metadata, _owner, _state


def _confirm(boundary, *, kind, payload, source, side=None, slot=None, pokemon=None):
    return boundary.confirm(event_kind=kind, payload=payload, session_id="response-profile", source=source, trust=USER_TRUST, confirmed=True, side=side, slot_index=slot, pokemon_id=pokemon, turn_number=1)


def _runtime_fixture():
    state = _complete_state(_state())
    owners = {side: _owner(state, side) for side in ("self", "opponent")}
    boundary = LifecycleConfirmationBoundary("response-profile", {side: {"slot_index": row["slot_index"], "pokemon_id": row["pokemon_id"]} for side, row in owners.items()})
    confirmations = [
        _confirm(boundary, kind="tailwind_side_condition_observed", payload={"status": "inactive"}, source=TAILWIND_SOURCE, side=side)
        for side in ("self", "opponent")
    ]
    confirmations.append(_confirm(boundary, kind="trick_room_field_observed", payload={"status": "inactive"}, source=TRICK_ROOM_SOURCE))
    confirmations.append(_confirm(boundary, kind="used_move_observed", payload={"move_id": "razor-wind", "move_slot": 0}, source=USED_MOVE_SOURCE, side="self", slot=0, pokemon=owners["self"]["pokemon_id"]))
    assert all(row["status"] == "confirmed" for row in confirmations)
    plan = {"session_id": "response-profile", "status": "planned", "conflicts": [], "ordered_steps": [
        {"observation_id": confirmations[0]["observation"]["observation_id"], "observation_sequence": 2, "event_kind": "set_observed_tailwind", "planned_effect": "set_observed_tailwind", "trust": USER_TRUST, **owners["self"], "tailwind_status": "inactive"},
        {"observation_id": confirmations[1]["observation"]["observation_id"], "observation_sequence": 3, "event_kind": "set_observed_tailwind", "planned_effect": "set_observed_tailwind", "trust": USER_TRUST, **owners["opponent"], "tailwind_status": "inactive"},
        {"observation_id": confirmations[2]["observation"]["observation_id"], "observation_sequence": 4, "event_kind": "set_observed_trick_room", "planned_effect": "set_observed_trick_room", "trust": USER_TRUST, "trick_room_status": "inactive"},
        {"observation_id": confirmations[3]["observation"]["observation_id"], "observation_sequence": 5, "event_kind": "used_move_observed", "planned_effect": "record_known_move", "trust": USER_TRUST, **owners["self"], "canonical_move_id": "razor-wind"},
    ]}
    replayed = project_atomic_transition(state, plan, "response-profile")
    assert replayed["status"] == "ready_with_projected_state", replayed
    state = replayed["projected_state"]
    snapshot = {"status": "runtime_snapshot_ready", "session_id": "response-profile", "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owners["self"])
    metadata = _metadata("tackle")
    razor = {**metadata, "move_id": "razor-wind", "metadata": {**metadata["metadata"], "move_id": "razor-wind", "power": 80, "type": "normal"}}
    razor.update(candidate_id="attack:razor-wind", active_attacker=owners["self"], session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=d0["decision_owner"])
    own = {"action_id": "attack:razor-wind", "action_type": "attack", "identity": "razor-wind", "move_metadata_authority": razor}
    known = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities={move: _metadata(move) for move in ("tackle", "water-gun", "scratch", "pound")})
    assert known.get("status") == "resolved", known
    opponent = {**next(row for row in known["actions"] if row["action_id"] == "opponent_attack:tackle"), "selectability": "selectable", "usability": {"status": "known_usable", "reason": None}}
    order = freeze_runtime_d0_action_order_authority(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent)
    charge = confirmations[3]["observation"]
    return snapshot, d0, own, opponent, order, charge


def test_razor_wind_tackle_release_pair_is_bound_to_replayed_charge_and_real_runtime_order():
    snapshot, d0, own, opponent, order, charge = _runtime_fixture()
    assert order["status"] == "resolved" and order["order"] == "own_first", order
    result = materialize_standard_charge_turn_two_ordered_pair_core(strategy_d0=d0, runtime_snapshot=snapshot, charge_observation=charge, own_action=own, opponent_action=opponent, action_order_authority=order)
    assert result["status"] == "evaluable", result
    assert result["temporal_source"]["charge_observation_id"] == charge["observation_id"]
    assert result["immediate_pair"]["status"] == result["exact_ledger"]["status"] == "evaluable"
    assert result["exact_ledger"]["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_charge_source_cannot_be_borrowed_by_a_later_tackle_or_foreign_observation():
    snapshot, d0, own, opponent, order, charge = _runtime_fixture()
    tackle = deepcopy(own); tackle["action_id"] = tackle["identity"] = "tackle"; tackle["move_metadata_authority"] = _metadata("tackle")
    assert materialize_standard_charge_turn_two_ordered_pair_core(strategy_d0=d0, runtime_snapshot=snapshot, charge_observation=charge, own_action=tackle, opponent_action=opponent, action_order_authority=order)["reason"] == "standard_charge_release_action_invalid"
    foreign = {**charge, "pokemon_id": "foreign"}
    assert materialize_standard_charge_turn_two_ordered_pair_core(strategy_d0=d0, runtime_snapshot=snapshot, charge_observation=foreign, own_action=own, opponent_action=opponent, action_order_authority=order)["reason"] == "standard_charge_observation_owner_mismatch"
