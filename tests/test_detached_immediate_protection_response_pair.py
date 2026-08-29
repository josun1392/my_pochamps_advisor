"""Strict ordinary Protect response coverage in detached immediate pairs."""
from __future__ import annotations

from copy import deepcopy

from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_d0_canonical_contact_classification_authority import freeze_runtime_d0_canonical_contact_classification_authority
from llm.advisor_runtime_d0_silk_trap_speed_drop_interaction_authority import (
    build_silk_trap_speed_drop_interaction_resolution,
)
from tests.test_detached_opponent_response_profile import _equal_speed_order, _inputs, _metadata
from tests.test_fixed_two_hit_immediate_move_pair_integration import _fixed_two_action, _order


def _protect_action(d0, move_id="protect") -> dict:
    opponent = d0["active_owners"]["opponent"]
    metadata = {"move_id": move_id, "category": "status", "target": "user", "accuracy": None, "priority": 4}
    return {
        "status": "resolved", "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": f"opponent_attack:{move_id}", "action_type": "attack", "move_id": move_id,
        "opponent_actor": opponent, "target_owner": d0["active_owners"]["self"],
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
        "metadata_authority": {"status": "resolved", "move_id": move_id, "metadata": metadata},
        "usability": {"status": "known_usable"}, "selectability": "selectable",
    }


def _own_action(d0, move_id: str) -> dict:
    metadata = deepcopy(_metadata(move_id))
    metadata["metadata"]["protection_bypass"] = False
    metadata.update({"candidate_id": f"attack:{move_id}", "active_attacker": d0["decision_owner"], "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]})
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": metadata}


def _success(opponent) -> dict:
    return {"schema_version": "branch-protection-success-v1", "owner": opponent, "previous_successful_protection_count": 0, "provenance": "explicit_branch_nonconsecutive_protection"}


def _silk_interaction(d0, *, move_id="tackle", outcome="applies", delta=-1):
    return build_silk_trap_speed_drop_interaction_resolution(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"],
        blocked_attacker=d0["active_owners"]["self"], blocked_action_id=f"attack:{move_id}",
        blocked_move_id=move_id, outcome=outcome, resulting_delta=delta,
        ability_authority={"status": "known", "value": "pressure"},
        item_authority={"status": "known_absent"},
    )


def test_confirmed_opponent_first_protect_blocks_normal_fixed_damage_and_fixed_two_hit_without_attack_leaves():
    for move in ("tackle", "seismic-toss"):
        _state, snapshot, d0, _unused, _responses, _orders = _inputs()
        own, protect = _own_action(d0, move), _protect_action(d0)
        pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=protect, action_order_authority=_order(d0, own, protect, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]))
        assert pair["status"] == "evaluable", pair.get("reason")
        assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert all(row["second_action"]["state"] == "prevented_by_protection" for row in pair["terminal_branches"])
        ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
        assert ledger["status"] == "evaluable"
        assert project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)["status"] == "resolved"

    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    own = _fixed_two_action(d0, move_id="double-hit")
    own["move_metadata_authority"]["metadata"]["protection_bypass"] = False
    protect = _protect_action(d0)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=protect, action_order_authority=_order(d0, own, protect, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]))
    assert pair["status"] == "evaluable", pair.get("reason")
    assert all(row["first_action_leaf"]["hit_state"] == "not_applicable" for row in pair["terminal_branches"])


def test_own_first_and_equal_speed_preserve_order_and_unknown_success_fails_closed():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs(equal_speed=True)
    own, protect = _own_action(d0, "tackle"), _protect_action(d0)
    own_first = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=protect, action_order_authority=_order(d0, own, protect, "own_first"))
    assert own_first["status"] == "evaluable", own_first.get("reason")
    assert all(row["second_action"]["state"] == "executed_protection" for row in own_first["terminal_branches"])

    tied = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=protect, action_order_authority=_equal_speed_order(d0, own, protect), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]))
    assert tied["status"] == "evaluable", tied.get("reason")
    assert tied["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert {row["action_order"] for row in tied["terminal_branches"]} == {"own_first", "opponent_first"}

    missing = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=protect, action_order_authority=_order(d0, own, protect, "opponent_first"))
    assert missing["status"] == "incomplete"


def test_detect_uses_existing_pair_protection_and_ledger_contracts():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs(equal_speed=True)
    own, detect = _own_action(d0, "tackle"), _protect_action(d0, "detect")
    blocked = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=detect,
        action_order_authority=_order(d0, own, detect, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
    )
    assert blocked["status"] == "evaluable", blocked.get("reason")
    assert all(row["second_action"]["state"] == "prevented_by_protection" for row in blocked["terminal_branches"])
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=blocked)["status"] == "evaluable"

    tied = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=detect,
        action_order_authority=_equal_speed_order(d0, own, detect),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
    )
    assert tied["status"] == "evaluable", tied.get("reason")
    assert tied["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert {row["action_order"] for row in tied["terminal_branches"]} == {"own_first", "opponent_first"}


def test_silk_trap_blocks_contact_and_projects_exact_blocked_attacker_speed_drop():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    own, silk = _own_action(d0, "tackle"), _protect_action(d0, "silk-trap")
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    assert contact["contact_state"] == "contact"
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=silk,
        action_order_authority=_order(d0, own, silk, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact,
        silk_trap_reactive_interaction_authority=_silk_interaction(d0),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    effect = pair["terminal_branches"][0]["first_action_leaf"]["consequences"]["deterministic_stage_effect"]
    assert effect["owner"] == "blocked_attacker" and effect["stat"] == "speed" and effect["requested_delta"] == -1
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_silk_trap_prevented_reversed_non_contact_and_missing_interaction_are_strict():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    silk = _protect_action(d0, "silk-trap")
    for outcome, delta, expected in (("prevented", 0, None), ("reversed", 1, 1)):
        own = _own_action(d0, "tackle")
        contact = freeze_runtime_d0_canonical_contact_classification_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, action=own,
            attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
        )
        pair = materialize_immediate_move_vs_move_action_pair(
            strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=silk,
            action_order_authority=_order(d0, own, silk, "opponent_first"),
            opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
            incoming_contact_authority=contact,
            silk_trap_reactive_interaction_authority=_silk_interaction(d0, outcome=outcome, delta=delta),
        )
        assert pair["status"] == "evaluable", pair.get("reason")
        effect = pair["terminal_branches"][0]["first_action_leaf"]["consequences"]["deterministic_stage_effect"]
        assert (effect is None) if expected is None else effect["resulting_stage"] == expected

    own = _own_action(d0, "flamethrower")
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    assert contact["contact_state"] == "non_contact"
    non_contact = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=silk,
        action_order_authority=_order(d0, own, silk, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact,
    )
    assert non_contact["status"] == "evaluable"
    assert non_contact["terminal_branches"][0]["first_action_leaf"]["consequences"]["deterministic_stage_effect"] is None

    own = _own_action(d0, "tackle")
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    missing = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=silk,
        action_order_authority=_order(d0, own, silk, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact,
    )
    assert missing["status"] == "incomplete"
