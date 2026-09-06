from copy import deepcopy

from advisor.canonical_atomic_item_swap_status import resolve_canonical_atomic_item_swap_status_move
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_d0_atomic_item_swap_status_execution_authority import freeze_runtime_d0_atomic_item_swap_status_execution_authority
from llm.advisor_runtime_d0_pure_status_action_execution_authority import freeze_runtime_d0_pure_status_action_execution_authority
from tests.test_detached_opponent_response_profile import _inputs


def _pair(move_id="trick"):
    state, snapshot, d0, _, responses, orders = _inputs()
    state["self_side"]["pokemon"][0]["known_item"] = "muscle-band"
    state["opponent_side"]["pokemon"][0]["known_item"] = "life-orb"
    # Reuse the fixture's current, provenance-backed snapshot shape.
    from llm.advisor_reducer_state_model import state_fingerprint
    snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["active_owners"]["self"])
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    metadata = {"move_id":move_id, "type":"psychic" if move_id == "trick" else "dark", "category":"status", "accuracy":100, "priority":0, "target":"selected-pokemon", "contact":False}
    meta = {"status":"resolved", "candidate_id":f"attack:{move_id}", "active_attacker":actor, "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "move_id":move_id, "metadata":metadata}
    own = {"action_id":f"attack:{move_id}", "action_type":"attack", "identity":move_id, "move_metadata_authority":meta}
    tail_meta = {"move_id":"tail-whip", "category":"status", "target":"selected-pokemon", "accuracy":100, "priority":0}
    opponent = {"status":"resolved", "action_id":"opponent_attack:tail-whip", "action_type":"attack", "move_id":"tail-whip", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "metadata_authority":{"status":"resolved", "metadata":tail_meta}, "selectability":"selectable", "usability":{"status":"known_usable"}}
    tail_action = {"action_id":opponent["action_id"], "action_type":"attack", "identity":"tail-whip", "metadata_authority":opponent["metadata_authority"]}
    tail_accuracy = {"status":"resolved", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "actor":target, "target":actor, "action_id":tail_action["action_id"], "move_id":"tail-whip", "outcome":"hit"}
    tail_authority = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=tail_action, actor=target, target=actor, status_accuracy_authority=tail_accuracy)
    order = {"status":"resolved", "schema_version":"runtime-d0-action-order-authority-v1", "order":"own_first", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "own_action_id":own["action_id"], "opponent_action_id":opponent["action_id"], "own_actor":actor, "opponent_actor":target}
    app = {"status":"resolved", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "actor":actor, "target":target, "action_id":own["action_id"], "move_id":move_id, "outcome":"ordinary"}
    authority = freeze_runtime_d0_atomic_item_swap_status_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=own, actor=actor, target=target, execution_applicability_authority=app)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=order, atomic_item_swap_status_execution_authorities={own["action_id"]:authority}, pure_status_execution_authorities={opponent["action_id"]:tail_authority})
    return authority, pair


def test_catalog_is_exact_for_both_production_moves():
    for move_id, move_type in (("trick", "psychic"), ("switcheroo", "dark")):
        row = resolve_canonical_atomic_item_swap_status_move(move={"move_id":move_id, "type":move_type, "category":"status", "accuracy":100, "priority":0, "target":"selected-pokemon", "contact":False})
        assert row["status"] == "resolved" and row["effect"]["contact"] is False


def test_trick_and_switcheroo_dispatch_through_atomic_authority_and_ledger():
    for move_id in ("trick", "switcheroo"):
        authority, pair = _pair(move_id)
        assert authority["outcome"] == "executed_swap"
        assert pair["status"] == "evaluable"
        ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
        assert ledger["status"] == "evaluable"
        first = pair["terminal_branches"][0]["first_action_leaf"]
        assert first["consequences"]["atomic_item_swap_status"]["actor_item_after"]["item"] == "life-orb"
