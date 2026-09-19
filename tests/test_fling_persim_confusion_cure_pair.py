from copy import deepcopy

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_detached_predictive_intermediate_state import (
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_immediate_move_vs_move_action_pair import (
    _defer_confusion_gate_for_first_persim_cure,
    materialize_immediate_move_vs_move_action_pair,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order


def _set_confusion(raw, owner, state):
    raw["current_confusion"] = state
    raw["confusion_provenance"] = {
        "event_kind": "current_confusion_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "state": state,
    }
    if state == "confused":
        raw["champions_confusion_progression"] = {
            "schema_version": "champions-confusion-progression-v1",
            "owner": deepcopy(owner),
            "state": "confused",
            "origin_id": f"pair:{owner['side']}:confusion",
            "established_turn": 1,
            "prior_opportunities": 0,
            "duration": 3,
            "confusion_observation": deepcopy(raw["confusion_provenance"]),
            "observed_turn": 1,
            "provenance": "observed_champions_confusion_progression_v1",
        }
    else:
        raw["champions_confusion_progression"] = None


def _pair(
    *,
    item="persim-berry",
    order="own_first",
    own_confusion="none",
    opponent_confusion="confused",
    own_move="fling",
    target_ability="pressure",
    opponent_hp=100,
):
    state, snapshot, old_d0, old_own, responses, _orders = _inputs(
        opponent_hp=opponent_hp,
    )
    own_raw = state["self_side"]["pokemon"][0]
    foe_raw = state["opponent_side"]["pokemon"][0]
    own_owner = {
        "session_id": state["session_id"], "side": "self", "slot_index": 0,
        "pokemon_id": own_raw["pokemon_id"],
    }
    foe_owner = {
        "session_id": state["session_id"], "side": "opponent", "slot_index": 0,
        "pokemon_id": foe_raw["pokemon_id"],
    }
    _set_confusion(own_raw, own_owner, own_confusion)
    _set_confusion(foe_raw, foe_owner, opponent_confusion)
    own_raw["known_item"] = item
    own_raw["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": "known",
    }
    foe_raw["current_ability"] = target_ability
    foe_raw["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    own_raw["current_ability"] = "pressure"
    own_raw["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": "persim-mr",
        "source_sequence": 1,
    }
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot, decision_owner=own_owner,
    )
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    if own_move == "fling":
        metadata = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
        own = {
            "action_id": "attack:fling",
            "action_type": "attack",
            "identity": "fling",
            "move_metadata_authority": {
                "status": "resolved",
                "candidate_id": "attack:fling",
                "active_attacker": actor,
                "session_id": d0["session_id"],
                "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
                "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
                "decision_owner": d0["decision_owner"],
                "move_id": "fling",
                "metadata": metadata,
            },
        }
    else:
        own = deepcopy(old_own)
        own["action_id"] = f"attack:{own_move}"
        own["identity"] = own_move
        own["move_metadata_authority"]["candidate_id"] = own["action_id"]
        own["move_metadata_authority"]["move_id"] = own_move
        own["move_metadata_authority"]["metadata"]["move_id"] = own_move
        own["move_metadata_authority"].update(
            active_attacker=actor,
            session_id=d0["session_id"],
            source_runtime_fingerprint=d0["source_runtime_fingerprint"],
            source_branch_fingerprint=d0["strategy_preview_fingerprint"],
            decision_owner=d0["decision_owner"],
        )
    opponent = deepcopy(
        next(row for row in responses["actions"] if row["action_id"] == "opponent_attack:water-gun")
    )
    opponent.update(
        session_id=d0["session_id"],
        source_runtime_fingerprint=d0["source_runtime_fingerprint"],
        source_branch_fingerprint=d0["strategy_preview_fingerprint"],
        decision_owner=d0["decision_owner"],
    )
    order_authority = _order(d0, own, opponent, order)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=order_authority,
    )
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    return {
        "state": state, "snapshot": snapshot, "d0": d0,
        "own": own, "opponent": opponent, "order": order_authority,
        "pair": pair, "ledger": ledger,
    }


def test_exact_persim_first_cures_before_pending_action_without_confusion_branching():
    case = _pair()
    pair, ledger = case["pair"], case["ledger"]
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["schema_version"] == "immediate-move-vs-move-action-pair-v1"
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert "confusion_self_hit" not in repr(pair)
    assert "confusion_selected_action_executes" not in repr(pair)
    assert "confusion_snaps_out" not in repr(pair)
    assert {row["action_order"] for row in pair["terminal_branches"]} == {"own_first"}
    assert {row["second_action"]["state"] for row in pair["terminal_branches"]} == {"executed"}

    for branch in pair["terminal_branches"]:
        first = branch["first_action_leaf"]
        payload = first["consequences"]["fling_persim_confusion_cure_target_effect"]
        assert payload["outcome"] == "applied_confusion_cure"
        assert payload["confusion_before"] == "confused"
        assert payload["confusion_after"] == "none"
        assert payload["confusion_progression_after"] is None
        assert first["consequences"]["fling_berry_eaten_transition"]["resulting_state"] == "known_true"
        intermediate = materialize_detached_predictive_intermediate_state(
            strategy_d0=case["d0"], terminal_leaf=first,
        )
        confusion = intermediate["active"]["opponent"]["hypothetical_confusion"]
        assert confusion["status"] == "known_none"
        assert confusion["current_confusion"] == "none"
        assert confusion["champions_confusion_progression"] is None


def test_persim_first_reasoning_leaves_runtime_snapshot_unchanged():
    case = _pair()
    raw = case["snapshot"]["state"]["opponent_side"]["pokemon"][0]
    assert raw["current_confusion"] == "confused"
    assert raw["champions_confusion_progression"]["state"] == "confused"


def test_persim_second_keeps_existing_confusion_gate():
    case = _pair(order="opponent_first")
    pair = case["pair"]
    assert pair["status"] == "incomplete"
    assert pair["schema_version"] == "champions-confusion-gated-immediate-action-pair-v1"
    assert pair["reason"] == "item_modifier"
    base = {
        "own_actor": case["d0"]["active_owners"]["self"],
        "opponent_actor": case["d0"]["active_owners"]["opponent"],
    }
    assert _defer_confusion_gate_for_first_persim_cure(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        base=base,
        orders=[{"order": "opponent_first"}],
        own_action=case["own"],
        own_meta=case["own"]["move_metadata_authority"],
    ) is False


def test_equal_speed_two_order_scope_is_not_globally_bypassed():
    case = _pair(opponent_confusion="none")
    state = deepcopy(case["snapshot"]["state"])
    foe = state["opponent_side"]["pokemon"][0]
    target = case["d0"]["active_owners"]["opponent"]
    _set_confusion(foe, target, "confused")
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": state,
        "state_fingerprint": state_fingerprint(state),
    }
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=case["d0"]["active_owners"]["self"],
    )
    base = {
        "own_actor": d0["active_owners"]["self"],
        "opponent_actor": d0["active_owners"]["opponent"],
    }
    assert _defer_confusion_gate_for_first_persim_cure(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        base=base,
        orders=[
            {"order": "own_first", "probability": 1 / 2},
            {"order": "opponent_first", "probability": 1 / 2},
        ],
        own_action=case["own"],
        own_meta=case["own"]["move_metadata_authority"],
    ) is False


def test_confused_fling_user_keeps_existing_confusion_gate():
    case = _pair(own_confusion="confused", opponent_confusion="none")
    pair = case["pair"]
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["schema_version"] == "champions-confusion-gated-immediate-action-pair-v1"
    assert "confusion_self_hit" in repr(pair)


def test_wrong_berry_and_non_fling_do_not_defer_confusion_gate():
    wrong = _pair(item="colbur-berry")
    assert wrong["pair"]["schema_version"] == "champions-confusion-gated-immediate-action-pair-v1"

    non_fling = _pair(own_move="tackle")
    assert non_fling["pair"]["schema_version"] == "champions-confusion-gated-immediate-action-pair-v1"


def test_target_none_has_no_special_confusion_deferral():
    case = _pair(opponent_confusion="none")
    base = {
        "own_actor": case["d0"]["active_owners"]["self"],
        "opponent_actor": case["d0"]["active_owners"]["opponent"],
    }
    assert _defer_confusion_gate_for_first_persim_cure(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        base=base,
        orders=[{"order": "own_first"}],
        own_action=case["own"],
        own_meta=case["own"]["move_metadata_authority"],
    ) is False


def test_persim_first_with_target_ko_does_not_claim_cure_or_ateberry():
    case = _pair(opponent_hp=1)
    pair = case["pair"]
    assert pair["status"] == "evaluable", pair.get("reason")
    for branch in pair["terminal_branches"]:
        first = branch["first_action_leaf"]
        assert first["consequences"]["target_ko"] is True
        assert "fling_persim_confusion_cure_target_effect" not in first["consequences"]
        assert "fling_berry_eaten_transition" not in first["consequences"]
        assert branch["second_action"]["state"] == "cancelled_due_to_faint"


def test_ledger_rejects_forged_confusion_removal_progression_eat_and_ateberry():
    case = _pair()
    pair = case["pair"]
    mutations = ("removal", "progression", "eat", "ateberry")
    for mutation in mutations:
        forged = deepcopy(pair)
        branch = deepcopy(forged["terminal_branches"][0])
        first = branch["first_action_leaf"]
        payload = first["consequences"]["fling_persim_confusion_cure_target_effect"]
        if mutation == "removal":
            payload["hypothetical_target_confusion_removal"]["confusion_after"] = "confused"
        elif mutation == "progression":
            payload["authority"]["confusion_progression_before"]["prior_opportunities"] = 4
        elif mutation == "eat":
            payload["authority"]["berry_eat_item_interaction_authority"]["target"] = deepcopy(
                payload["authority"]["actor"]
            )
        else:
            first["consequences"]["fling_berry_eaten_transition"]["resulting_state"] = "known_false"
        forged["terminal_branches"] = (
            branch, *forged["terminal_branches"][1:]
        )
        result = normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)
        assert result["status"] == "rejected", (mutation, result)
