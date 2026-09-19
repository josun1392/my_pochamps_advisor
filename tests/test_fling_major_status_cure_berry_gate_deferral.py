from copy import deepcopy

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_immediate_move_vs_move_action_pair import (
    _defer_sleep_freeze_gate_for_first_fling_cure,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _inputs


_TARGET_ITEM_UNSET = object()


def _case(
    *,
    item: str,
    target_condition: str,
    actor_condition: str = "none",
    target_ability: str = "pressure",
    target_item=_TARGET_ITEM_UNSET,
):
    state, snapshot, d0, _own, responses, _orders = _inputs()
    own_row = state["self_side"]["pokemon"][0]
    foe_row = state["opponent_side"]["pokemon"][0]
    own_row["known_item"] = item
    own_row["known_item_provenance"]["status"] = "known"
    own_row["condition"] = actor_condition
    own_row["condition_provenance"]["condition"] = actor_condition
    foe_row["condition"] = target_condition
    foe_row["condition_provenance"]["condition"] = target_condition
    foe_row["current_ability"] = target_ability
    foe_row["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    if target_item is not _TARGET_ITEM_UNSET:
        if target_item == "__unknown__":
            foe_row["known_item"] = {"knowledge": "unknown"}
            foe_row.pop("known_item_provenance", None)
        elif target_item is None:
            foe_row["known_item"] = None
            foe_row["known_item_provenance"] = {
                "event_kind": "current_item_observed",
                "trust": "user_confirmed_observation",
                "turn_number": 1,
                "status": "known_absent",
            }
        else:
            foe_row["known_item"] = target_item
            foe_row["known_item_provenance"] = {
                "event_kind": "current_item_observed",
                "trust": "user_confirmed_observation",
                "turn_number": 1,
                "status": "known",
            }
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": "fling-cure-gate",
        "source_sequence": 1,
    }
    snapshot = {
        **snapshot,
        "state": state,
        "state_fingerprint": state_fingerprint(state),
    }
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=d0["active_owners"]["self"],
    )
    actor = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    fling_metadata = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
    own_action = {
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
            "metadata": fling_metadata,
        },
    }
    opponent_action = deepcopy(
        next(row for row in responses["actions"] if row["action_id"] == "opponent_attack:water-gun")
    )
    opponent_action.update(
        session_id=d0["session_id"],
        source_runtime_fingerprint=d0["source_runtime_fingerprint"],
        source_branch_fingerprint=d0["strategy_preview_fingerprint"],
        decision_owner=d0["decision_owner"],
    )
    own_meta = {"status": "resolved", "metadata": fling_metadata}
    opponent_meta = {
        "status": "resolved",
        "metadata": deepcopy(opponent_action["metadata_authority"]["metadata"]),
    }
    base = {
        "pair_id": f"pair:{own_action['action_id']}:{opponent_action['action_id']}",
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "own_action_id": own_action["action_id"],
        "opponent_action_id": opponent_action["action_id"],
        "own_actor": deepcopy(actor),
        "opponent_actor": deepcopy(target),
    }
    return {
        "strategy_d0": d0,
        "runtime_snapshot": snapshot,
        "base": base,
        "own_action": own_action,
        "opponent_action": opponent_action,
        "own_meta": own_meta,
        "opponent_meta": opponent_meta,
    }


def _defer(case, orders):
    return _defer_sleep_freeze_gate_for_first_fling_cure(
        **case,
        orders=orders,
    )


def test_chesto_and_aspear_defer_only_when_exact_cure_fling_is_first():
    chesto = _case(item="chesto-berry", target_condition="sleep")
    aspear = _case(item="aspear-berry", target_condition="freeze")
    own_first = [{"order": "own_first", "probability": 1, "source_branch": None}]
    assert _defer(chesto, own_first) is True
    assert _defer(aspear, own_first) is True


def test_gate_is_not_deferred_when_cure_fling_acts_second():
    case = _case(item="chesto-berry", target_condition="sleep")
    opponent_first = [{"order": "opponent_first", "probability": 1, "source_branch": None}]
    assert _defer(case, opponent_first) is False


def test_gate_is_not_deferred_for_equal_speed_two_order_branch():
    case = _case(item="chesto-berry", target_condition="sleep")
    orders = [
        {"order": "own_first", "probability": 0.5, "source_branch": {"order_branch_id": "a"}},
        {"order": "opponent_first", "probability": 0.5, "source_branch": {"order_branch_id": "b"}},
    ]
    assert _defer(case, orders) is False


def test_gate_is_not_deferred_for_wrong_or_unsupported_berry():
    wrong = _case(item="aspear-berry", target_condition="sleep")
    unsupported = _case(item="oran-berry", target_condition="sleep")
    own_first = [{"order": "own_first", "probability": 1, "source_branch": None}]
    assert _defer(wrong, own_first) is False
    assert _defer(unsupported, own_first) is False


def test_gate_is_not_deferred_when_fling_actor_is_sleep_or_freeze_blocked():
    sleeping = _case(
        item="chesto-berry",
        target_condition="sleep",
        actor_condition="sleep",
    )
    frozen = _case(
        item="aspear-berry",
        target_condition="freeze",
        actor_condition="freeze",
    )
    own_first = [{"order": "own_first", "probability": 1, "source_branch": None}]
    assert _defer(sleeping, own_first) is False
    assert _defer(frozen, own_first) is False


def test_gate_is_not_deferred_for_non_fling_action():
    case = _case(item="chesto-berry", target_condition="sleep")
    case["own_action"] = deepcopy(case["opponent_action"])
    case["own_meta"] = deepcopy(case["opponent_meta"])
    own_first = [{"order": "own_first", "probability": 1, "source_branch": None}]
    assert _defer(case, own_first) is False
