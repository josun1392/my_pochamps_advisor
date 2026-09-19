from copy import deepcopy

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_belch_eligibility_authority import freeze_runtime_d0_belch_eligibility_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0, freeze_runtime_strategy_selection_authority
from llm.advisor_runtime_d0_opponent_action_authority import (
    compose_runtime_d0_opponent_move_usability,
    freeze_runtime_d0_opponent_known_move_action_authority,
)
from llm.advisor_runtime_d0_opponent_move_usability_authority import freeze_runtime_d0_opponent_move_usability_authority
from llm.advisor_reducer_state_model import project_atomic_transition
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_runtime_strategy_d0 import _selection
from tests.test_runtime_d0_opponent_move_usability_authority import (
    _metadata as _opponent_metadata,
    _state as _opponent_state,
    _owner as _opponent_owner,
    _snapshot as _opponent_snapshot,
)


def _berry_state(state, *, side, value):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    if value is None:
        pokemon.pop("berry_eaten_state", None)
        pokemon.pop("berry_eaten_state_provenance", None)
        return
    pokemon["berry_eaten_state"] = value
    pokemon["berry_eaten_state_provenance"] = {
        "event_kind": "berry_eaten_state_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": f"{side}-berry",
        "source_sequence": 1,
        "turn_number": 1 if value == "known_false" else 2,
        "basis": "fresh_battle_initialization" if value == "known_false" else "observed_berry_consumption",
        **({"item_id": "cheri-berry"} if value == "known_true" else {}),
    }


def _d0_for(side="self", value=None):
    state, snapshot, old_d0, own, responses, orders = _inputs()
    _berry_state(state, side=side, value=value)
    snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=old_d0["active_owners"]["self"])
    return state, snapshot, d0, own, responses, orders


def _belch_action(d0, *, side):
    if side == "self":
        return {
            "action_id": "attack:belch", "action_type": "attack", "identity": "belch",
            "session_id": d0["session_id"],
            "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
            "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
            "decision_owner": deepcopy(d0["decision_owner"]),
        }
    return {
        "status": "resolved", "action_id": "opponent_attack:belch", "action_type": "attack",
        "identity": "belch", "move_id": "belch", "acting_side": "opponent", "target_side": "self",
        "opponent_actor": deepcopy(d0["active_owners"]["opponent"]),
        "target_owner": deepcopy(d0["active_owners"]["self"]),
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]),
        "metadata_authority": {
            "status": "resolved", "move_id": "belch",
            "metadata": {"move_id": "belch", "category": "special", "power": 120, "type": "poison", "accuracy": 90, "priority": 0},
        },
        "usability": {"status": "known_usable"}, "selectability": "selectable",
    }


def test_belch_eligibility_true_false_unknown():
    for value, expected_status, expected_eligibility in (
        ("known_true", "resolved", "eligible"),
        ("known_false", "resolved", "not_eligible"),
        (None, "incomplete", "unknown"),
    ):
        _state, _snapshot, d0, _own, _responses, _orders = _d0_for("self", value)
        result = freeze_runtime_d0_belch_eligibility_authority(
            strategy_d0=d0, action=_belch_action(d0, side="self"),
            actor=d0["active_owners"]["self"],
        )
        assert result["status"] == expected_status
        assert result["eligibility"] == expected_eligibility


def test_own_selection_projection_gates_belch_without_removing_move_identity():
    for value, expected in (("known_true", "selectable"), ("known_false", "not_selectable"), (None, "selection_unknown")):
        _state, _snapshot, d0, _own, _responses, _orders = _d0_for("self", value)
        projection = _selection(d0)
        projection["moves"] = [{"move_id": "belch", "selection": "selectable"}]
        selection = freeze_runtime_strategy_selection_authority(strategy_d0=d0, selection_projection=projection)
        attack = next(row for row in selection["actions"] if row["action_id"] == "attack:belch")
        assert attack["selection"] == expected


def _pair(*, opponent_berry_state, own_move="tackle", observed_usable=True):
    state, snapshot, old_d0, old_own, responses, _orders = _inputs(own_move="tackle")
    _berry_state(state, side="opponent", value=opponent_berry_state)
    if own_move == "fling":
        state["self_side"]["pokemon"][0]["known_item"] = "cheri-berry"
        state["self_side"]["pokemon"][0]["known_item_provenance"]["status"] = "known"
        state["field"]["magic_room_status"] = "inactive"
        state["field"]["magic_room_status_provenance"] = {
            "event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation",
            "source_observation_id": "belch-fling-mr", "source_sequence": 1,
        }
    snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=old_d0["active_owners"]["self"])
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]

    if own_move == "fling":
        metadata = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
    else:
        metadata = deepcopy(old_own["move_metadata_authority"]["metadata"])
    own = {
        "action_id": f"attack:{own_move}", "action_type": "attack", "identity": own_move,
        "move_metadata_authority": {
            "status": "resolved", "candidate_id": f"attack:{own_move}", "active_attacker": actor,
            "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
            "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
            "move_id": own_move, "metadata": metadata,
        },
    }
    opponent = _belch_action(d0, side="opponent")
    if not observed_usable:
        opponent["usability"] = {"status": "unknown", "reason": "no_exact_current_usability"}
    order = {
        "status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "own_first",
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
        "own_action_id": own["action_id"], "opponent_action_id": opponent["action_id"],
        "own_actor": actor, "opponent_actor": target,
    }
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own,
        opponent_action=opponent, action_order_authority=order,
    )
    return pair


def test_false_before_turn_fling_cannot_retroactively_legalize_belch():
    pair = _pair(opponent_berry_state="known_false", own_move="fling")
    assert pair["status"] == "incomplete"
    assert pair["reason"] == "belch_requires_prior_berry_eaten"


def test_forged_known_usable_without_authenticated_usability_authority_does_not_open_unknown_belch():
    pair = _pair(opponent_berry_state=None, own_move="tackle")
    assert pair["status"] == "incomplete"
    assert pair["reason"] == "belch_berry_eaten_state_unknown"


def test_unknown_before_turn_forged_pending_belch_fails_closed_before_damage():
    pair = _pair(opponent_berry_state=None, own_move="tackle", observed_usable=False)
    assert pair["status"] == "incomplete"
    assert pair["reason"] == "opponent_action_not_known_usable"


def _opponent_belch_case(status, reason):
    state = _opponent_state()
    pokemon = state["opponent_side"]["pokemon"][0]
    pokemon["known_move_ids"] = ["belch"]
    pokemon["known_move_ids_provenance"] = {
        "belch": {
            "event_kind": "used_move_observed",
            "trust": "user_confirmed_observation",
            "source_observation_id": "belch-used",
            "source_sequence": 1,
        }
    }
    pokemon["current_move_usability"] = {}
    opponent = _opponent_owner(state, "opponent")
    plan = {
        "session_id": state["session_id"], "status": "planned", "conflicts": [],
        "ordered_steps": [{
            "observation_id": "belch-usability", "observation_sequence": 2,
            "planned_effect": "set_current_move_usability",
            "trust": "user_confirmed_observation",
            **opponent, "canonical_move_id": "belch",
            "usability": status, "reason": reason, "turn_number": 1,
        }],
    }
    projected = project_atomic_transition(state, plan, state["session_id"])
    assert projected["status"] == "ready_with_projected_state", projected
    state = projected["projected_state"]
    snapshot = _opponent_snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_opponent_owner(state, "self"),
    )
    frozen = freeze_runtime_d0_opponent_known_move_action_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        canonical_move_metadata_authorities={"belch": _opponent_metadata("belch")},
    )
    assert frozen["status"] == "resolved", frozen
    return d0, snapshot, frozen["actions"][0]


def test_opponent_known_usable_belch_can_resolve_unknown_history_but_other_unusable_reason_does_not_imply_false():
    d0, snapshot, action = _opponent_belch_case("known_usable", None)
    usable = freeze_runtime_d0_opponent_move_usability_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, opponent_action=action,
    )
    assert usable["status"] == "resolved"
    assert usable["selectability"] == "selectable"
    assert usable["belch_eligibility_authority"]["provenance"] == "observed_current_belch_usability_gate_v1"
    assert d0["current_berry_eaten_authority"]["opponent"]["status"] == "incomplete"
    composed = compose_runtime_d0_opponent_move_usability(
        opponent_action=action, usability_authority=usable,
    )
    assert composed["opponent_move_usability_authority"] == usable
    gate = freeze_runtime_d0_belch_eligibility_authority(
        strategy_d0=d0,
        action=composed,
        actor=d0["active_owners"]["opponent"],
        observed_usability=composed["opponent_move_usability_authority"],
    )
    assert gate["status"] == "resolved"
    assert gate["eligibility"] == "eligible"
    assert gate["provenance"] == "observed_current_belch_usability_gate_v1"

    d02, snapshot2, action2 = _opponent_belch_case("known_unusable", "no_pp")
    unusable = freeze_runtime_d0_opponent_move_usability_authority(
        strategy_d0=d02, runtime_snapshot=snapshot2, opponent_action=action2,
    )
    assert unusable["status"] == "resolved"
    assert unusable["selectability"] == "not_selectable"
    assert unusable["usability"]["reason"] == "no_pp"
    assert d02["current_berry_eaten_authority"]["opponent"]["status"] == "incomplete"


def test_already_true_belch_executes_as_normal_120_bp_attack():
    pair = _pair(opponent_berry_state="known_true", own_move="tackle")
    assert pair["status"] == "evaluable", pair.get("reason")
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable"
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    second = pair["terminal_branches"][0]["second_action"]
    assert second["state"] == "executed"
    assert second["leaf"]["provenance"]["move_id"] == "belch"
