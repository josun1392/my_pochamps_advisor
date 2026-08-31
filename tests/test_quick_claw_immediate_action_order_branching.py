from copy import deepcopy

from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_exact_quick_claw_action_order_branching import materialize_exact_quick_claw_action_order_branches
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_d0_action_order_authority import freeze_runtime_d0_action_order_authority
from llm.advisor_runtime_d0_opponent_action_authority import freeze_runtime_d0_opponent_known_move_action_authority
from llm.advisor_runtime_d0_complete_opponent_response_set_authority import freeze_runtime_d0_complete_opponent_response_set_authority
from llm.advisor_runtime_d0_quick_claw_action_order_authority import freeze_runtime_d0_quick_claw_action_order_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import MOVES, _complete_state, _metadata, _owner, _snapshot, _state


def _inputs(*, own_speed=80, opponent_speed=100, own_priority=0, opponent_priority=0, item="quick-claw", opponent_item=None, item_provenance_valid=True, own_hp=100, opponent_hp=100):
    state = _complete_state(_state())
    for side in ("self", "opponent"):
        state[f"{side}_side"]["tailwind_status"] = "inactive"
        state[f"{side}_side"]["tailwind_status_provenance"] = {"event_kind": "set_observed_tailwind", "trust": "user_confirmed_observation"}
    state["field"]["trick_room_status"] = "inactive"
    state["field"]["trick_room_status_provenance"] = {"event_kind": "set_observed_trick_room", "trust": "user_confirmed_observation"}
    state["self_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = own_speed
    state["opponent_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = opponent_speed
    state["self_side"]["pokemon"][0]["current_hp"] = own_hp
    state["opponent_side"]["pokemon"][0]["current_hp"] = opponent_hp
    state["self_side"]["pokemon"][0]["known_item"] = item
    state["self_side"]["pokemon"][0]["known_item_provenance"]["status"] = "known" if item else "known_absent"
    if not item_provenance_valid:
        state["self_side"]["pokemon"][0].pop("known_item_provenance")
    if opponent_item is not None:
        state["opponent_side"]["pokemon"][0]["known_item"] = opponent_item
        state["opponent_side"]["pokemon"][0]["known_item_provenance"]["status"] = "known"
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = _owner(state, "self")
    own_meta = _metadata("iron-head")
    own_meta["metadata"]["priority"] = own_priority
    own_meta.update(candidate_id="attack:iron-head", active_attacker=own, session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=d0["decision_owner"])
    own_action = {"action_id": "attack:iron-head", "action_type": "attack", "identity": "iron-head", "move_metadata_authority": own_meta}
    metadata = {move: _metadata(move) for move in MOVES}
    metadata["tackle"]["metadata"]["priority"] = opponent_priority
    known = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities=metadata)
    response = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=known)
    opponent_action = next(row for row in response["actions"] if row["action_id"] == "opponent_attack:tackle")
    order = freeze_runtime_d0_action_order_authority(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action)
    quick = freeze_runtime_d0_quick_claw_action_order_authority(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action, action_order_authority=order)
    return state, snapshot, d0, own_action, opponent_action, order, quick


def test_strict_quick_claw_authority_distinguishes_applicable_no_effect_unknown_and_stale():
    state, snapshot, d0, own, opponent, order, quick = _inputs()
    assert order["order"] == "opponent_first"
    assert quick["status"] == "resolved" and quick["outcome"] == "applicable"
    assert quick["activation_probability"] == {"numerator": 1, "denominator": 5}
    no_effect = _inputs(item="leftovers")[-1]
    assert no_effect["status"] == "resolved" and no_effect["outcome"] == "known_no_effect"
    assert _inputs(item_provenance_valid=False)[-1]["status"] == "incomplete"
    missing_state = deepcopy(state); missing_state["self_side"]["pokemon"][0].pop("known_item_provenance")
    missing_snapshot = _snapshot(missing_state)
    missing = freeze_runtime_d0_quick_claw_action_order_authority(strategy_d0=d0, runtime_snapshot=missing_snapshot, own_action=own, opponent_action=opponent, action_order_authority=order)
    assert missing["status"] == "rejected"  # stale D0 precedes any item inference
    foreign = deepcopy(order); foreign["own_action_id"] = "attack:foreign"
    assert freeze_runtime_d0_quick_claw_action_order_authority(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=foreign)["status"] == "rejected"


def test_quick_claw_respects_strict_priority_and_composes_exact_tie_non_activation():
    blocked = _inputs(own_priority=0, opponent_priority=1)[-1]
    assert blocked["status"] == "resolved" and blocked["outcome"] == "known_no_effect"
    *_prefix, tied_order, tied_quick = _inputs(own_speed=100, opponent_speed=100)
    assert tied_order["order"] == "unresolved_tie"
    branches = materialize_exact_quick_claw_action_order_branches(quick_claw_authority=tied_quick)
    assert branches["status"] == "resolved"
    assert [row["conditional_probability"] for row in branches["order_branches"]] == [
        {"numerator": 1, "denominator": 5}, {"numerator": 2, "denominator": 5}, {"numerator": 2, "denominator": 5},
    ]


def test_quick_claw_pair_branches_drive_existing_ko_flinch_ledger_and_metrics():
    _state0, snapshot, d0, own, opponent, _order, quick = _inputs(own_hp=1, opponent_hp=1)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=quick["source_action_order_authority"], quick_claw_action_order_authority=quick)
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    activated = [row for row in pair["terminal_branches"] if row.get("action_order_branch", {}).get("activation_state") == "activated"]
    assert activated and all(row["action_order"] == "own_first" and row["second_action"]["state"] == "cancelled_due_to_faint" for row in activated)
    non_activated = [row for row in pair["terminal_branches"] if row.get("action_order_branch", {}).get("activation_state") == "not_activated"]
    assert non_activated and all(row["action_order"] == "opponent_first" for row in non_activated)
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable" and project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)["status"] == "resolved"
    forged = deepcopy(pair); forged["terminal_branches"] = tuple({**row, "action_order_branch": {**row["action_order_branch"], "holder": d0["active_owners"]["opponent"]}} if row.get("action_order_branch", {}).get("activation_state") == "activated" else row for row in pair["terminal_branches"])
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"

    _state1, snapshot, d0, own, opponent, _order, quick = _inputs()
    flinch_pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=quick["source_action_order_authority"], quick_claw_action_order_authority=quick)
    assert any(row.get("action_order_branch", {}).get("activation_state") == "activated" and row["second_action"]["state"] == "cancelled_due_to_flinch" for row in flinch_pair["terminal_branches"])


def test_same_positive_and_negative_priority_brackets_are_applicable_and_both_holders_fail_closed():
    assert _inputs(own_priority=1, opponent_priority=1)[-1]["outcome"] == "applicable"
    assert _inputs(own_priority=-1, opponent_priority=-1)[-1]["outcome"] == "applicable"
    assert _inputs(opponent_item="quick-claw")[-1]["status"] == "unsupported"
