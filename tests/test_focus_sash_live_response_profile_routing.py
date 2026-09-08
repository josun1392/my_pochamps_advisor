from copy import deepcopy

from llm.advisor_detached_opponent_response_profile import materialize_detached_opponent_response_profile
from llm.advisor_runtime_d0_complete_opponent_response_set_authority import (
    freeze_runtime_d0_complete_opponent_response_set_authority,
)
from llm.advisor_runtime_d0_focus_sash_survival_authority import (
    freeze_runtime_d0_focus_sash_survival_authority,
)
from llm.advisor_runtime_d0_opponent_action_authority import (
    freeze_runtime_d0_opponent_known_move_action_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import MOVES, _complete_state, _metadata, _owner, _snapshot, _state


def _inputs(*, sash_side: str, own_first: bool, item_status: str = "known"):
    state = _complete_state(_state())
    holder = state[f"{sash_side}_side"]["pokemon"][0]
    holder.update(current_hp=1, max_hp=1, known_item="focus-sash")
    holder["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": item_status,
    }
    if not own_first:
        state["opponent_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = 110
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = _owner(state, "self")
    own_metadata = _metadata("tackle") | {
        "candidate_id": "attack:tackle",
        "active_attacker": own,
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": d0["decision_owner"],
    }
    own_action = {
        "action_id": "attack:tackle",
        "action_type": "attack",
        "identity": "tackle",
        "move_metadata_authority": own_metadata,
    }
    known = freeze_runtime_d0_opponent_known_move_action_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        canonical_move_metadata_authorities={move: _metadata(move) for move in MOVES},
    )
    response_set = freeze_runtime_d0_complete_opponent_response_set_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        opponent_known_move_authority=known,
    )
    orders = {
        action_id: {
            "status": "resolved",
            "schema_version": "runtime-d0-action-order-authority-v1",
            "order": "own_first" if own_first else "opponent_first",
            "session_id": d0["session_id"],
            "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
            "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
            "decision_owner": d0["decision_owner"],
            "own_action_id": own_action["action_id"],
            "opponent_action_id": action_id,
            "own_actor": d0["active_owners"]["self"],
            "opponent_actor": d0["active_owners"]["opponent"],
        }
        for action_id in response_set["selectable_response_action_ids"]
    }
    authorities = {
        action["action_id"]: {
            "own_first": freeze_runtime_d0_focus_sash_survival_authority(
                strategy_d0=d0,
                runtime_snapshot=snapshot,
                holder=d0["active_owners"]["opponent"],
                attacker=d0["active_owners"]["self"],
                action=own_action,
                move_metadata=own_metadata["metadata"],
            ),
            "opponent_first": freeze_runtime_d0_focus_sash_survival_authority(
                strategy_d0=d0,
                runtime_snapshot=snapshot,
                holder=d0["active_owners"]["self"],
                attacker=d0["active_owners"]["opponent"],
                action=action,
                move_metadata=action["metadata_authority"]["metadata"],
            ),
        }
        for action in response_set["actions"]
        if action["action_id"] in orders
    }
    return snapshot, d0, own_action, response_set, orders, authorities


def _profile(*, sash_side: str, own_first: bool, item_status: str = "known"):
    snapshot, d0, own_action, response_set, orders, authorities = _inputs(
        sash_side=sash_side,
        own_first=own_first,
        item_status=item_status,
    )
    return materialize_detached_opponent_response_profile(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own_action,
        response_set_authority=response_set,
        action_order_authorities=orders,
        first_action_focus_sash_survival_authorities=authorities,
    )


def test_live_response_profile_routes_focus_sash_for_the_own_first_branch() -> None:
    profile = _profile(sash_side="opponent", own_first=True)

    assert profile["status"] == "evaluable", profile.get("reason")
    for entry in profile["response_entries"]:
        first = entry["pair"]["terminal_branches"][0]["first_action_leaf"]
        assert first["consequences"]["target_final_hp"] == 1
        assert first["consequences"]["focus_sash_survival"]["outcome"] == "applied"
        assert entry["pair"]["terminal_branches"][0]["second_action"]["state"] == "executed"
        assert entry["exact_pair_outcome_ledger"]["status"] == "evaluable"


def test_live_response_profile_carries_opponent_first_focus_sash_authority_fail_closed() -> None:
    snapshot, d0, own_action, response_set, orders, authorities = _inputs(
        sash_side="self",
        own_first=False,
    )
    assert all(value["opponent_first"]["status"] == "ready" for value in authorities.values())

    profile = materialize_detached_opponent_response_profile(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own_action,
        response_set_authority=response_set,
        action_order_authorities=orders,
        first_action_focus_sash_survival_authorities=authorities,
    )

    assert profile["status"] == "rejected"
    assert profile["reason"] == "first_action_focus_sash_survival_authority_binding_mismatch"


def test_live_response_profile_fails_closed_when_focus_sash_item_authority_is_unknown() -> None:
    profile = _profile(sash_side="opponent", own_first=True, item_status="unknown")

    assert profile["status"] == "incomplete"
    assert profile["reason"] == "required_response_pair_not_evaluable"


def test_response_profile_rejects_missing_order_bound_focus_sash_authority() -> None:
    snapshot, d0, own_action, response_set, orders, authorities = _inputs(
        sash_side="opponent",
        own_first=True,
    )
    forged = deepcopy(authorities)
    forged.pop(next(iter(forged)))

    profile = materialize_detached_opponent_response_profile(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own_action,
        response_set_authority=response_set,
        action_order_authorities=orders,
        first_action_focus_sash_survival_authorities=forged,
    )
    assert profile["status"] == "rejected"
    assert profile["reason"] == "response_profile_focus_sash_authority_set_mismatch"
