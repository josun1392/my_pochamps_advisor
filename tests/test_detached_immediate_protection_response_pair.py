"""Strict ordinary Protect response coverage in detached immediate pairs."""
from __future__ import annotations

from copy import deepcopy

from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_d0_canonical_contact_classification_authority import freeze_runtime_d0_canonical_contact_classification_authority
from llm.advisor_runtime_d0_silk_trap_speed_drop_interaction_authority import (
    build_silk_trap_speed_drop_interaction_resolution,
    build_kings_shield_attack_drop_interaction_resolution,
    build_obstruct_defense_drop_interaction_resolution,
)
from llm.advisor_runtime_d0_spiky_shield_reactive_damage_authority import (
    build_spiky_shield_reactive_damage_applicability_resolution,
    build_spiky_shield_successful_block_context,
    freeze_runtime_d0_spiky_shield_reactive_damage_authority,
)
from llm.advisor_runtime_d0_baneful_bunker_reactive_poison_authority import (
    build_baneful_bunker_reactive_poison_applicability_resolution,
    build_baneful_bunker_successful_block_context,
    freeze_runtime_d0_baneful_bunker_reactive_poison_authority,
)
from llm.advisor_runtime_d0_burning_bulwark_reactive_burn_authority import (
    build_burning_bulwark_reactive_burn_applicability_resolution,
    build_burning_bulwark_successful_block_context,
    freeze_runtime_d0_burning_bulwark_reactive_burn_authority,
)
from llm.advisor_runtime_d0_quick_guard_priority_applicability_authority import build_quick_guard_protection_context, freeze_runtime_d0_quick_guard_priority_applicability_authority
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
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


def _kings_interaction(d0, *, move_id="tackle", outcome="applies", delta=-1):
    return build_kings_shield_attack_drop_interaction_resolution(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"],
        blocked_attacker=d0["active_owners"]["self"], blocked_action_id=f"attack:{move_id}",
        blocked_move_id=move_id, outcome=outcome, resulting_delta=delta,
        ability_authority={"status": "known", "value": "pressure"},
        item_authority={"status": "known_absent"},
    )

def _obstruct_interaction(d0, *, move_id="tackle", outcome="applies", delta=-2):
    return build_obstruct_defense_drop_interaction_resolution(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], blocked_attacker=d0["active_owners"]["self"], blocked_action_id=f"attack:{move_id}", blocked_move_id=move_id, outcome=outcome, resulting_delta=delta, ability_authority={"status":"known","value":"pressure"}, item_authority={"status":"known_absent"})


def _spiky_damage_authority(d0, snapshot, own, *, outcome="applies"):
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    protection = {"status": "resolved", "owner": d0["active_owners"]["opponent"], "metadata": {"move_id": "spiky-shield"}, "provenance": "exact_spiky_shield_block_v1"}
    context = build_spiky_shield_successful_block_context(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], shield_action_id="opponent_attack:spiky-shield",
        blocked_attacker=d0["active_owners"]["self"], blocked_action_id=own["action_id"], blocked_move_id=own["identity"],
        protection_authority=protection, action_blocked=True, protection_bypass=False, substitute_authority={"status": "known_absent"},
    )
    applicability = build_spiky_shield_reactive_damage_applicability_resolution(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], blocked_attacker=d0["active_owners"]["self"],
        blocked_action_id=own["action_id"], blocked_move_id=own["identity"], outcome=outcome,
        ability_authority={"status": "known", "value": "pressure"}, item_authority={"status": "known_absent"},
    )
    return freeze_runtime_d0_spiky_shield_reactive_damage_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, shield_owner=d0["active_owners"]["opponent"], shield_action_id="opponent_attack:spiky-shield",
        blocked_attacker=d0["active_owners"]["self"], blocked_action=own, contact_authority=contact,
        protection_block_context=context, applicability_resolution=applicability,
    ), contact


def _baneful_poison_authority(d0, snapshot, own, *, outcome="applies"):
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    protection = {"status": "resolved", "owner": d0["active_owners"]["opponent"], "metadata": {"move_id": "baneful-bunker"}, "provenance": "exact_baneful_bunker_block_v1"}
    context = build_baneful_bunker_successful_block_context(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], shield_action_id="opponent_attack:baneful-bunker",
        blocked_attacker=d0["active_owners"]["self"], blocked_action_id=own["action_id"], blocked_move_id=own["identity"],
        protection_authority=protection, action_blocked=True, protection_bypass=False, substitute_authority={"status": "known_absent"},
    )
    applicability = build_baneful_bunker_reactive_poison_applicability_resolution(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], blocked_attacker=d0["active_owners"]["self"],
        blocked_action_id=own["action_id"], blocked_move_id=own["identity"], outcome=outcome,
        ability_authority={"status": "known", "value": "pressure"}, item_authority={"status": "known_absent"},
    )
    return freeze_runtime_d0_baneful_bunker_reactive_poison_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, shield_owner=d0["active_owners"]["opponent"], shield_action_id="opponent_attack:baneful-bunker",
        blocked_attacker=d0["active_owners"]["self"], blocked_action=own, contact_authority=contact,
        protection_block_context=context, applicability_resolution=applicability,
    ), contact


def _burning_burn_authority(d0, snapshot, own, *, outcome="applies"):
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    protection = {"status": "resolved", "owner": d0["active_owners"]["opponent"], "metadata": {"move_id": "burning-bulwark"}, "provenance": "exact_burning_bulwark_block_v1"}
    context = build_burning_bulwark_successful_block_context(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], shield_action_id="opponent_attack:burning-bulwark",
        blocked_attacker=d0["active_owners"]["self"], blocked_action_id=own["action_id"], blocked_move_id=own["identity"],
        protection_authority=protection, action_blocked=True, protection_bypass=False, substitute_authority={"status": "known_absent"},
    )
    applicability = build_burning_bulwark_reactive_burn_applicability_resolution(
        session_id=d0["session_id"], shield_owner=d0["active_owners"]["opponent"], blocked_attacker=d0["active_owners"]["self"],
        blocked_action_id=own["action_id"], blocked_move_id=own["identity"], outcome=outcome,
        ability_authority={"status": "known", "value": "pressure"}, item_authority={"status": "known_absent"},
    )
    return freeze_runtime_d0_burning_bulwark_reactive_burn_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, shield_owner=d0["active_owners"]["opponent"], shield_action_id="opponent_attack:burning-bulwark",
        blocked_attacker=d0["active_owners"]["self"], blocked_action=own, contact_authority=contact,
        protection_block_context=context, applicability_resolution=applicability,
    ), contact


def _quick_guard_authority(d0, snapshot, own, *, blocked=True, bypass=False):
    protection={"status":"resolved","owner":d0["active_owners"]["opponent"],"metadata":{"move_id":"quick-guard"}}
    context=build_quick_guard_protection_context(session_id=d0["session_id"],guard_user=d0["active_owners"]["opponent"],guard_action_id="opponent_attack:quick-guard",incoming_actor=d0["active_owners"]["self"],incoming_action_id=own["action_id"],incoming_move_id=own["identity"],selected_target=d0["active_owners"]["opponent"],protection_authority=protection,action_blocked=blocked,protection_bypass=bypass)
    return freeze_runtime_d0_quick_guard_priority_applicability_authority(strategy_d0=d0,runtime_snapshot=snapshot,guard_user=d0["active_owners"]["opponent"],guard_action_id="opponent_attack:quick-guard",incoming_actor=d0["active_owners"]["self"],incoming_action=own,selected_target=d0["active_owners"]["opponent"],protection_context=context)


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


def test_kings_shield_contact_attack_drop_reuses_strict_reactive_path_without_changing_silk_trap():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    own, shield = _own_action(d0, "tackle"), _protect_action(d0, "kings-shield")
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own,
        attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
    )
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact,
        kings_shield_reactive_interaction_authority=_kings_interaction(d0),
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    effect = pair["terminal_branches"][0]["first_action_leaf"]["consequences"]["deterministic_stage_effect"]
    assert effect == {"owner": "blocked_attacker", "stat": "attack", "previous_stage": 0, "requested_delta": -1, "resulting_stage": -1, "interaction_outcome": "applies"}
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"

def test_obstruct_contact_defense_drop_uses_exact_minus_two_authority():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    own, shield = _own_action(d0,"tackle"), _protect_action(d0,"obstruct")
    contact=freeze_runtime_d0_canonical_contact_classification_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=own,attacker=d0["active_owners"]["self"],target=d0["active_owners"]["opponent"])
    pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=shield,action_order_authority=_order(d0,own,shield,"opponent_first"),opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),incoming_contact_authority=contact,obstruct_reactive_interaction_authority=_obstruct_interaction(d0))
    assert pair["status"]=="evaluable",pair.get("reason")
    assert pair["terminal_branches"][0]["first_action_leaf"]["consequences"]["deterministic_stage_effect"]["resulting_stage"]==-2


def _spiky_pair_inputs(*, own_hp: int):
    state, snapshot, d0, _unused, _responses, _orders = _inputs(own_hp=own_hp)
    state["self_side"]["pokemon"][0]["max_hp"] = 80
    snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["decision_owner"])
    own, shield = _own_action(d0, "tackle"), _protect_action(d0, "spiky-shield")
    damage, contact = _spiky_damage_authority(d0, snapshot, own)
    return snapshot, d0, own, shield, damage, contact


def test_spiky_shield_consumes_reactive_damage_into_pair_ledger_and_metrics():
    snapshot, d0, own, shield, damage, contact = _spiky_pair_inputs(own_hp=80)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, spiky_shield_reactive_damage_authority=damage,
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    leaf = pair["terminal_branches"][0]["first_action_leaf"]
    assert leaf["hit_state"] == leaf["critical_state"] == leaf["damage_roll"] == "not_applicable"
    assert leaf["consequences"]["target_final_hp"] == 70 and leaf["consequences"]["target_ko"] is False
    assert leaf["consequences"]["spiky_shield_reactive_damage"]["authority"]["reactive_damage"] == 10
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
    assert ledger["status"] == "evaluable" and ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert metrics["status"] == "resolved" and metrics["own"]["final_hp_distribution"]["outcomes"][0]["final_hp"] == 70


def test_spiky_shield_reactive_ko_and_non_contact_or_missing_authority_remain_exact():
    snapshot, d0, own, shield, damage, contact = _spiky_pair_inputs(own_hp=5)
    ko = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, spiky_shield_reactive_damage_authority=damage,
    )
    assert ko["status"] == "evaluable" and ko["terminal_branches"][0]["second_action"]["state"] == "prevented_by_protection"
    assert ko["terminal_branches"][0]["first_action_leaf"]["consequences"]["target_ko"] is True
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=ko)
    assert project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)["own"]["ko_probability"] == {"numerator": 1, "denominator": 1}

    non_contact = _own_action(d0, "shadow-ball")
    non_contact_damage, non_contact_authority = _spiky_damage_authority(d0, snapshot, non_contact)
    block_only = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=non_contact, opponent_action=shield,
        action_order_authority=_order(d0, non_contact, shield, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=non_contact_authority, spiky_shield_reactive_damage_authority=non_contact_damage,
    )
    assert block_only["status"] == "evaluable"
    assert block_only["terminal_branches"][0]["first_action_leaf"]["consequences"]["spiky_shield_reactive_damage"]["outcome"] == "not_applicable"
    missing = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]), incoming_contact_authority=contact,
    )
    assert missing["status"] == "incomplete"


def test_baneful_bunker_consumes_exact_poison_transition_into_protection_pair_and_ledger():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    own, shield = _own_action(d0, "tackle"), _protect_action(d0, "baneful-bunker")
    poison, contact = _baneful_poison_authority(d0, snapshot, own)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, baneful_bunker_reactive_poison_authority=poison,
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    leaf = pair["terminal_branches"][0]["first_action_leaf"]
    assert leaf["hit_state"] == leaf["critical_state"] == leaf["damage_roll"] == "not_applicable"
    transition = leaf["consequences"]["reactive_shield_condition_transition"]
    assert transition["condition"] == "poison" and transition["condition_before"] == "known_none"
    assert leaf["consequences"]["secondary"] is None
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable" and ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["terminal_leaves"][0]["final_consequences"]["reactive_shield_condition_consequence"] == transition


def test_baneful_bunker_no_effect_and_missing_or_foreign_authority_remain_strict():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    shield, own = _protect_action(d0, "baneful-bunker"), _own_action(d0, "shadow-ball")
    non_contact, contact = _baneful_poison_authority(d0, snapshot, own)
    block_only = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, baneful_bunker_reactive_poison_authority=non_contact,
    )
    assert block_only["status"] == "evaluable"
    assert block_only["terminal_branches"][0]["first_action_leaf"]["consequences"]["reactive_shield_condition_transition"] is None
    own = _own_action(d0, "tackle"); prevented, contact = _baneful_poison_authority(d0, snapshot, own, outcome="prevented")
    prevented_pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, baneful_bunker_reactive_poison_authority=prevented,
    )
    assert prevented_pair["status"] == "evaluable"
    assert prevented_pair["terminal_branches"][0]["first_action_leaf"]["consequences"]["reactive_shield_condition_transition"] is None
    for condition, types in (("burn", ["normal"]), ("none", ["poison"]), ("none", ["steel"])):
        state, snapshot, d0, _unused, _responses, _orders = _inputs()
        state["self_side"]["pokemon"][0]["condition"] = condition
        state["self_side"]["pokemon"][0]["condition_provenance"]["condition"] = condition
        state["self_side"]["pokemon"][0]["current_type"] = types
        snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["decision_owner"])
        own, shield = _own_action(d0, "tackle"), _protect_action(d0, "baneful-bunker")
        no_effect, contact = _baneful_poison_authority(d0, snapshot, own)
        pair = materialize_immediate_move_vs_move_action_pair(
            strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
            action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
            incoming_contact_authority=contact, baneful_bunker_reactive_poison_authority=no_effect,
        )
        assert pair["status"] == "evaluable"
        assert pair["terminal_branches"][0]["first_action_leaf"]["consequences"]["reactive_shield_condition_transition"] is None
    own = _own_action(d0, "tackle"); poison, contact = _baneful_poison_authority(d0, snapshot, own)
    missing = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]), incoming_contact_authority=contact,
    )
    assert missing["status"] == "incomplete"
    foreign = deepcopy(poison); foreign["blocked_action_id"] = "foreign"
    rejected = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]), incoming_contact_authority=contact, baneful_bunker_reactive_poison_authority=foreign,
    )
    assert rejected["status"] == "rejected"


def test_burning_bulwark_consumes_exact_burn_transition_into_protection_pair_and_ledger():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    own, shield = _own_action(d0, "tackle"), _protect_action(d0, "burning-bulwark")
    burn, contact = _burning_burn_authority(d0, snapshot, own)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, burning_bulwark_reactive_burn_authority=burn,
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    leaf = pair["terminal_branches"][0]["first_action_leaf"]
    assert leaf["hit_state"] == leaf["critical_state"] == leaf["damage_roll"] == "not_applicable"
    transition = leaf["consequences"]["reactive_shield_condition_transition"]
    assert transition["condition"] == "burn" and transition["condition_before"] == "known_none"
    assert leaf["consequences"]["secondary"] is None
    assert leaf["consequences"]["baneful_bunker_reactive_poison"] is None
    assert leaf["consequences"]["burning_bulwark_reactive_burn"]["authority"]["trigger"] == "burning_bulwark_successful_blocked_contact"
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable" and ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["terminal_leaves"][0]["final_consequences"]["reactive_shield_condition_consequence"] == transition


def test_burning_bulwark_no_effect_missing_and_foreign_authority_remain_strict():
    _state, snapshot, d0, _unused, _responses, _orders = _inputs()
    shield, own = _protect_action(d0, "burning-bulwark"), _own_action(d0, "shadow-ball")
    non_contact, contact = _burning_burn_authority(d0, snapshot, own)
    block_only = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, burning_bulwark_reactive_burn_authority=non_contact,
    )
    assert block_only["status"] == "evaluable"
    assert block_only["terminal_branches"][0]["first_action_leaf"]["consequences"]["reactive_shield_condition_transition"] is None

    own = _own_action(d0, "tackle")
    prevented, contact = _burning_burn_authority(d0, snapshot, own, outcome="prevented")
    prevented_pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, burning_bulwark_reactive_burn_authority=prevented,
    )
    assert prevented_pair["status"] == "evaluable"
    assert prevented_pair["terminal_branches"][0]["first_action_leaf"]["consequences"]["reactive_shield_condition_transition"] is None

    missing = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]), incoming_contact_authority=contact,
    )
    assert missing["status"] == "incomplete"
    foreign = deepcopy(prevented)
    foreign["blocked_action_id"] = "foreign"
    rejected = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=shield,
        action_order_authority=_order(d0, own, shield, "opponent_first"), opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
        incoming_contact_authority=contact, burning_bulwark_reactive_burn_authority=foreign,
    )
    assert rejected["status"] == "rejected"


def test_quick_guard_consumes_only_exact_priority_applicability():
    _state,snapshot,d0,_unused,_responses,_orders=_inputs()
    own,guard=_own_action(d0,"tackle"),_protect_action(d0,"quick-guard")
    own["move_metadata_authority"]["metadata"].update(priority=1,target="selected-pokemon")
    applies=_quick_guard_authority(d0,snapshot,own)
    pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=guard,action_order_authority=_order(d0,own,guard,"opponent_first"),quick_guard_priority_applicability_authority=applies)
    assert pair["status"]=="evaluable",pair.get("reason")
    leaf=pair["terminal_branches"][0]["first_action_leaf"]
    assert leaf["hit_state"]==leaf["critical_state"]==leaf["damage_roll"]=="not_applicable"
    assert leaf["consequences"]["quick_guard_priority_applicability"]["outcome"]=="applies"
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["terminal_probability_mass"]=={"numerator":1,"denominator":1}


def test_quick_guard_no_effect_and_fail_closed_paths_preserve_order_contracts():
    _state,snapshot,d0,_unused,_responses,_orders=_inputs(equal_speed=True)
    own,guard=_own_action(d0,"tackle"),_protect_action(d0,"quick-guard")
    own["move_metadata_authority"]["metadata"].update(priority=0,target="selected-pokemon")
    no_effect=_quick_guard_authority(d0,snapshot,own)
    pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=guard,action_order_authority=_order(d0,own,guard,"opponent_first"),quick_guard_priority_applicability_authority=no_effect)
    assert pair["status"]=="evaluable",pair.get("reason")
    leaf=pair["terminal_branches"][0]["first_action_leaf"]
    assert leaf["hit_state"] != "not_applicable" and leaf["consequences"].get("quick_guard_priority_applicability") is None
    tied=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=guard,action_order_authority=_equal_speed_order(d0,own,guard),quick_guard_priority_applicability_authority=no_effect)
    assert tied["status"]=="evaluable" and tied["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    assert {row["action_order"] for row in tied["terminal_branches"]}=={"own_first","opponent_first"}
    assert materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=guard,action_order_authority=_order(d0,own,guard,"opponent_first"))["status"]=="incomplete"
    foreign=deepcopy(no_effect);foreign["incoming_action_id"]="foreign"
    assert materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=guard,action_order_authority=_order(d0,own,guard,"opponent_first"),quick_guard_priority_applicability_authority=foreign)["status"]=="rejected"
