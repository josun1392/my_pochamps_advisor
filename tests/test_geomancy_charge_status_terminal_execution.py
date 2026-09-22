from __future__ import annotations

from copy import deepcopy

from advisor.canonical_geomancy_charge_status_terminal import resolve_canonical_geomancy_charge_status_terminal
from core.charge_move_repository import ChargeMoveRepository
from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation
from llm.advisor_detached_standard_charge_turn_two_attack_execution import (
    execute_detached_standard_charge_turn_two_attacks,
    materialize_detached_standard_charge_turn_two_execution_authority,
    materialize_detached_standard_charge_turn_two_terminal_execution_contract,
)
from llm.advisor_geomancy_charge_status_terminal_execution import (
    FORCED_MODE,
    execute_geomancy_status_terminal,
    execute_runtime_d0_geomancy_power_herb_skip,
    freeze_runtime_d0_geomancy_power_herb_skip_execution_authority,
    materialize_geomancy_status_terminal_contract,
    materialize_geomancy_terminal_stage_transition,
    validate_runtime_d0_geomancy_power_herb_skip_execution_authority,
)
from tests.test_detached_next_turn_action_order_temporal_state import _production_temporal_handoff
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import freeze_runtime_d0_standard_charge_participant_mechanics_authority
from llm.advisor_runtime_d0_action_order_authority import freeze_runtime_d0_action_order_authority
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import freeze_runtime_d0_standard_charge_start_readiness_authority
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_reducer_state_model import state_fingerprint
from tests.test_standard_charge_start_immediate_pair_integration import _own_action, _opponent_action, _with_terminal_mechanics_facts
from tests.test_standard_charge_turn_two_ordered_pair_core import _runtime_fixture
from tests.test_runtime_d0_standard_charge_start_readiness_authority import _inputs as readiness_inputs
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state


def test_geomancy_canonical_status_terminal_and_generic_guard():
    canonical = resolve_canonical_geomancy_charge_status_terminal("geomancy")
    assert canonical["status"] == "resolved", canonical
    assert canonical["move"] == {
        "move_id": "geomancy",
        "category": "status",
        "power": 0,
        "accuracy": True,
        "target": "self",
        "type": "fairy",
    }
    assert canonical["boosts"] == {
        "special-attack": 2,
        "special-defense": 2,
        "speed": 2,
    }
    guard = ChargeMoveRepository().immediate_execution_guard("geomancy")
    assert guard["reason"] == "two_turn_execution_unrepresented"
    assert guard["canonical_recognition_grants_immediate_execution"] is False


def test_geomancy_stage_transition_caps_independently_and_all_capped_is_explicit():
    handoff = _production_temporal_handoff(own_move="geomancy", opponent_move="razor-wind")
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    )
    assert forced["status"] == "resolved", forced
    execution = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        forced_continuation=forced,
        predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"],
    )
    assert execution["status"] == "resolved", execution
    actor = execution["actions"]["self"]["predictive_actor_mechanics"]
    owner = execution["actions"]["self"]["actor"]

    mixed = deepcopy(actor)
    mixed["current_stages"]["values"].update({
        "special-attack": 0,
        "special-defense": 5,
        "speed": 6,
    })
    transition = materialize_geomancy_terminal_stage_transition(
        actor=owner,
        action_id=execution["actions"]["self"]["continuation_action_id"],
        actor_mechanics=mixed,
    )
    assert transition["status"] == "resolved", transition
    by_stat = {row["stat"]: row for row in transition["transitions"]}
    assert by_stat["special-attack"]["resulting_stage"] == 2
    assert by_stat["special-defense"]["resulting_stage"] == 6
    assert by_stat["speed"]["resulting_stage"] == 6
    assert transition["all_stages_capped"] is False

    capped = deepcopy(actor)
    capped["current_stages"]["values"].update({
        "special-attack": 6,
        "special-defense": 6,
        "speed": 6,
    })
    transition = materialize_geomancy_terminal_stage_transition(
        actor=owner,
        action_id=execution["actions"]["self"]["continuation_action_id"],
        actor_mechanics=capped,
    )
    assert transition["status"] == "resolved", transition
    assert transition["outcome"] == "executed_no_change_all_stages_capped"
    assert transition["all_stages_capped"] is True
    assert all(row["resulting_stage"] == 6 for row in transition["transitions"])


def test_geomancy_ordinary_charge_transports_and_terminal_boosts_once_without_damage_contract():
    handoff = _production_temporal_handoff(own_move="geomancy", opponent_move="razor-wind")
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    continuation = state["next_turn_standard_charge_continuation_authorities"]["self"]
    assert continuation["status"] == "known_present"
    assert continuation["move_id"] == "geomancy"
    assert continuation["source_charge_context"]["canonical_lifecycle_family"] == "charge_then_status_terminal"
    assert continuation["source_charge_context"]["execution_model"] == "other_two_turn"
    assert "semi_invulnerable_charge_state_authority" not in continuation

    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    )
    assert forced["status"] == "resolved", forced
    execution = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        forced_continuation=forced,
        predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"],
    )
    assert execution["status"] == "resolved", execution
    row = execution["actions"]["self"]
    assert row["canonical_terminal_effect"]["schema_version"] == "canonical-geomancy-charge-status-terminal-v1"

    damage_contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=execution,
        side="self",
    )
    assert damage_contract["status"] == "rejected"
    assert damage_contract["reason"] == "geomancy_requires_status_terminal_contract"

    result = execute_detached_standard_charge_turn_two_attacks(execution_authority=execution)
    assert result["status"] == "resolved", result
    ledger = result["actions"]["self"]
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    executed = [leaf for leaf in ledger["terminal_leaves"] if leaf["consequences"]["geomancy_terminal_execution"]["status"] == "executed"]
    assert executed
    for leaf in executed:
        assert leaf["hit_state"] == "not_applicable"
        assert leaf["critical_state"] == "not_applicable"
        assert leaf["damage_roll"] == "not_applicable"
        assert leaf["consequences"]["damage"] == 0
        stage = leaf["consequences"]["geomancy_terminal_self_stage_transition"]
        by_stat = {item["stat"]: item for item in stage["transitions"]}
        assert by_stat["special-attack"]["resulting_stage"] == min(6, by_stat["special-attack"]["previous_stage"] + 2)
        assert by_stat["special-defense"]["resulting_stage"] == min(6, by_stat["special-defense"]["previous_stage"] + 2)
        assert by_stat["speed"]["resulting_stage"] == min(6, by_stat["speed"]["previous_stage"] + 2)
        retirement = leaf["consequences"]["geomancy_continuation_retirement"]
        assert retirement["state_after"] == "retired"
        assert retirement["terminal_reapplication_allowed"] is False



def _current_turn_geomancy_pair(*, power_herb: bool, condition: str = "none", own_hp: int = 100, self_speed: int | None = None, opponent_speed: int | None = None, opponent_move: str = "tackle"):
    snapshot, d0, _own0, _opp0, _order0, _charge = _runtime_fixture()
    state = _with_terminal_mechanics_facts(snapshot["state"])
    snapshot["state"] = state
    raw = state["self_side"]["pokemon"][0]
    raw["current_hp"] = own_hp
    raw["max_hp"] = 100
    raw["fainted"] = own_hp == 0
    raw["condition"] = condition
    raw["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "condition": condition,
        "turn_number": 1,
    }
    if self_speed is not None:
        raw["current_final_stats"]["speed"]["value"] = self_speed
    if opponent_speed is not None:
        state["opponent_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = opponent_speed
    if power_herb:
        raw["known_item"] = "power-herb"
        raw["known_item_provenance"] = {
            "event_kind": "current_item_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "status": "known",
        }
        state["field"]["magic_room_status"] = "inactive"
        state["field"]["magic_room_status_provenance"] = {
            "event_kind": "magic_room_field_observed",
            "trust": "user_confirmed_observation",
            "source_observation_id": "geomancy-power-herb-magic-room",
            "source_sequence": 1,
        }
    else:
        raw["known_item"] = None
        raw["known_item_provenance"] = {
            "event_kind": "current_item_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "status": "known_absent",
        }
    snapshot["state_fingerprint"] = state_fingerprint(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=d0["active_owners"]["self"],
    )
    own = _own_action(d0, d0["active_owners"]["self"], "geomancy")
    opponent = _opponent_action(d0, opponent_move)
    if power_herb:
        actor_mechanics = freeze_runtime_d0_standard_charge_participant_mechanics_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, action=own,
            actor=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"],
            owner=d0["active_owners"]["self"], participant_role="actor",
            move_metadata=own["move_metadata_authority"]["metadata"],
        )
        assert actor_mechanics["status"] == "resolved", (
            actor_mechanics.get("reason"), actor_mechanics.get("missing_authority"),
        )
    order = freeze_runtime_d0_action_order_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
    )
    assert order["status"] == "resolved", order
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=order,
    )
    return snapshot, d0, own, opponent, order, pair


def test_geomancy_turn_one_charge_pair_has_no_boost_and_no_semi_invulnerability():
    _snapshot, _d0, _own, _opponent, _order, pair = _current_turn_geomancy_pair(power_herb=False)
    assert pair["status"] == "evaluable", pair
    charge_leaves = [
        branch["first_action_leaf"]
        for branch in pair["terminal_branches"]
        if branch["first_action_leaf"].get("provenance", {}).get("move_id") == "geomancy"
    ]
    assert charge_leaves
    for leaf in charge_leaves:
        consequences = leaf["consequences"]
        assert "geomancy_terminal_self_stage_transition" not in consequences
        assert "charge_turn_self_stage_effect" not in consequences
        context = consequences["detached_standard_charge_lifecycle_context"]
        assert context["canonical_lifecycle_family"] == "charge_then_status_terminal"
        assert context["execution_model"] == "other_two_turn"
        assert "semi_invulnerable_charge_state_authority" not in context


def test_geomancy_power_herb_is_same_turn_status_terminal_with_consumption_and_no_continuation():
    _snapshot, _d0, _own, _opponent, _order, pair = _current_turn_geomancy_pair(power_herb=True)
    assert pair["status"] == "evaluable", (pair.get("status"), pair.get("reason"))
    geomancy_leaves = [
        branch["first_action_leaf"]
        for branch in pair["terminal_branches"]
        if branch["first_action_leaf"].get("provenance", {}).get("move_id") == "geomancy"
    ]
    assert geomancy_leaves
    executed = [
        leaf for leaf in geomancy_leaves
        if leaf["consequences"].get("geomancy_terminal_execution", {}).get("status") == "executed"
    ]
    assert executed
    for leaf in executed:
        consequences = leaf["consequences"]
        assert consequences["damage"] == 0
        assert leaf["hit_state"] == leaf["critical_state"] == "not_applicable"
        assert leaf["damage_roll"] == "not_applicable"
        assert "detached_standard_charge_lifecycle_context" not in consequences
        assert "geomancy_continuation_retirement" not in consequences
        consumption = consequences["geomancy_power_herb_consumption"]
        assert consumption["phase"] == "after_pre_action_gate_at_charge_move_skip"
        assert consumption["item_before"] == "power-herb"
        assert consumption["item_after"] == {"status": "known_absent", "value": None}
        stage = consequences["geomancy_terminal_self_stage_transition"]
        assert len(stage["transitions"]) == 3



def _forced_geomancy_contract():
    handoff = _production_temporal_handoff(own_move="geomancy", opponent_move="razor-wind")
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
    )
    authority = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        forced_continuation=forced,
        predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"],
    )
    assert authority["status"] == "resolved", authority
    row = authority["actions"]["self"]
    contract = materialize_geomancy_status_terminal_contract(
        execution_mode=FORCED_MODE,
        source_state_fingerprint=fingerprint,
        actor=row["actor"],
        target=row["target"],
        action_id=row["continuation_action_id"],
        actor_mechanics=row["predictive_actor_mechanics"],
        target_mechanics=row["predictive_target_mechanics"],
        caller_action_authority=row,
    )
    assert contract["status"] == "resolved", contract
    return handoff, authority, row, contract


def _recontract_geomancy(base, actor_mechanics):
    return materialize_geomancy_status_terminal_contract(
        execution_mode=FORCED_MODE,
        source_state_fingerprint=base["source_state_fingerprint"],
        actor=base["actor"],
        target=base["target"],
        action_id=base["action_id"],
        actor_mechanics=actor_mechanics,
        target_mechanics=base["target_mechanics"],
        caller_action_authority=base["caller_action_authority"],
    )


def test_geomancy_turn_two_faint_and_paralysis_cancel_without_boost_and_retire():
    _handoff, _authority, _row, base = _forced_geomancy_contract()

    fainted = deepcopy(base["actor_mechanics"])
    fainted["current_hp"]["current_hp"] = 0
    fainted["fainted"] = True
    fainted["direct_mechanics"]["combatant"]["current_hp"] = 0
    result = execute_geomancy_status_terminal(_recontract_geomancy(base, fainted))
    assert result["status"] == "resolved", result
    assert result["pre_action_gate"]["reason"] == "fainted_actor"
    leaf = result["terminal_leaves"][0]
    assert "geomancy_terminal_self_stage_transition" not in leaf["consequences"]
    assert leaf["consequences"]["geomancy_continuation_retirement"]["reason"] == "actor_faint_prevents_continuation"

    paralyzed = deepcopy(base["actor_mechanics"])
    paralyzed["condition"] = {"status": "known_present", "condition": "paralysis"}
    paralyzed["direct_mechanics"]["combatant"]["status"] = "paralysis"
    result = execute_geomancy_status_terminal(_recontract_geomancy(base, paralyzed))
    assert result["status"] == "resolved", result
    cancelled = [
        leaf for leaf in result["terminal_leaves"]
        if "cancelled_due_to_paralysis" in " ".join(str(x) for x in leaf["branch_path"])
    ]
    executed = [
        leaf for leaf in result["terminal_leaves"]
        if leaf["consequences"].get("geomancy_terminal_execution", {}).get("status") == "executed"
    ]
    assert cancelled and executed
    assert all("geomancy_terminal_self_stage_transition" not in leaf["consequences"] for leaf in cancelled)
    assert all(
        leaf["consequences"]["geomancy_continuation_retirement"]["reason"] == "full_paralysis_cancellation"
        for leaf in cancelled
    )
    assert all("geomancy_terminal_self_stage_transition" in leaf["consequences"] for leaf in executed)
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_geomancy_turn_two_confusion_self_hit_cancels_selected_move_and_retires():
    _handoff, _authority, _row, base = _forced_geomancy_contract()
    confused = deepcopy(base["actor_mechanics"])
    confused["confusion_state"] = {"status": "known_confused"}
    confused["confusion_progression"] = {
        "status": "known",
        "value": {"origin_id": "geomancy-confusion", "prior_opportunities": 0, "duration": 3},
    }
    confused["direct_mechanics"]["combatant"]["pokemon_id"] = base["actor"]["pokemon_id"]
    result = execute_geomancy_status_terminal(_recontract_geomancy(base, confused))
    assert result["status"] == "resolved", result
    self_hits = [
        leaf for leaf in result["terminal_leaves"]
        if "confusion_self_hit" in " ".join(str(x) for x in leaf["branch_path"])
    ]
    assert self_hits
    assert all("geomancy_terminal_self_stage_transition" not in leaf["consequences"] for leaf in self_hits)
    assert all(
        leaf["consequences"]["geomancy_continuation_retirement"]["reason"] == "confusion_self_hit"
        for leaf in self_hits
    )
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_geomancy_forced_authority_tamper_and_duplicate_side_reject():
    _handoff, authority, _row, _contract = _forced_geomancy_contract()
    forged = deepcopy(authority)
    forged["actions"]["self"]["original_charge_action_id"] = "attack:forged"
    rejected = execute_detached_standard_charge_turn_two_attacks(execution_authority=forged)
    assert rejected["status"] == "rejected"

    duplicated = deepcopy(authority)
    duplicated["actions"]["opponent"] = deepcopy(duplicated["actions"]["self"])
    rejected = execute_detached_standard_charge_turn_two_attacks(execution_authority=duplicated)
    assert rejected["status"] == "rejected"


def _power_herb_geomancy_authority(*, condition: str = "none"):
    snapshot, d0, own, _opponent, _order, pair = _current_turn_geomancy_pair(power_herb=True, condition=condition)
    if condition == "none":
        assert pair["status"] == "evaluable", (pair.get("status"), pair.get("reason"))
    actor = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own, actor=actor, target=target,
    )
    assert readiness["status"] == "resolved"
    assert readiness["outcome"] == "power_herb_charge_skip_ready"
    authority = freeze_runtime_d0_geomancy_power_herb_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own, actor=actor, target=target,
        move_metadata=own["move_metadata_authority"]["metadata"],
        readiness_authority=readiness,
    )
    assert authority["status"] == "resolved", authority
    return snapshot, d0, own, authority


def test_geomancy_power_herb_authority_is_status_only_and_tamper_replays_fail_closed():
    _snapshot, _d0, _own, authority = _power_herb_geomancy_authority()
    assert authority["damage_terminal_mechanics_authority"] is None
    assert validate_runtime_d0_geomancy_power_herb_skip_execution_authority(authority) is None
    forged = deepcopy(authority)
    forged["actor"]["pokemon_id"] = "forged"
    assert validate_runtime_d0_geomancy_power_herb_skip_execution_authority(forged) is not None
    assert execute_runtime_d0_geomancy_power_herb_skip(forged)["status"] == "rejected"



def test_geomancy_turn_two_sleep_and_freeze_use_existing_exact_status_gate_and_never_boost_cancelled_paths():
    _handoff, _authority, _row, base = _forced_geomancy_contract()
    cases = (
        ("sleep", {"condition": "sleep", "origin_id": "geomancy-sleep", "prior_attempts": 0, "sleep_duration": None}),
        ("freeze", {"condition": "freeze", "origin_id": "geomancy-freeze", "prior_attempts": 0, "sleep_duration": None}),
    )
    for condition, progression in cases:
        actor = deepcopy(base["actor_mechanics"])
        actor["condition"] = {"status": "known_present", "condition": condition}
        actor["direct_mechanics"]["combatant"]["status"] = condition
        actor["status_progression"] = {"status": "known", "value": progression}
        result = execute_geomancy_status_terminal(_recontract_geomancy(base, actor))
        assert result["status"] == "resolved", (condition, result)
        cancelled = [
            leaf for leaf in result["terminal_leaves"]
            if leaf["consequences"].get("geomancy_terminal_execution", {}).get("status") == "cancelled"
        ]
        assert cancelled, (condition, result)
        assert all("geomancy_terminal_self_stage_transition" not in leaf["consequences"] for leaf in cancelled)
        assert all("geomancy_continuation_retirement" in leaf["consequences"] for leaf in cancelled)
        assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_geomancy_power_herb_klutz_or_magic_room_does_not_skip():
    *_prefix, klutz = readiness_inputs(
        "geomancy",
        item="power-herb",
        item_mode="known",
        actor_ability="klutz",
        target_ability="static",
        magic_room="inactive",
    )
    assert klutz["status"] == "resolved", klutz
    assert klutz["outcome"] == "charge_start_ready"
    assert klutz["power_herb_applicability_state"]["status"] == "suppressed"

    *_prefix, magic_room = readiness_inputs(
        "geomancy",
        item="power-herb",
        item_mode="known",
        actor_ability="static",
        target_ability="static",
        magic_room="active",
    )
    assert magic_room["status"] == "resolved", magic_room
    assert magic_room["outcome"] == "charge_start_ready"
    assert magic_room["power_herb_applicability_state"]["status"] == "suppressed"


def test_geomancy_power_herb_terminal_projects_boosted_same_turn_detached_state():
    _snapshot, d0, _own, _opponent, _order, pair = _current_turn_geomancy_pair(power_herb=True)
    leaf = next(
        branch["first_action_leaf"]
        for branch in pair["terminal_branches"]
        if branch["first_action_leaf"]["consequences"].get("geomancy_terminal_execution", {}).get("status") == "executed"
    )
    projected = materialize_detached_predictive_intermediate_state(
        strategy_d0=d0,
        terminal_leaf=leaf,
    )
    assert projected["status"] == "resolved", projected
    stage = leaf["consequences"]["geomancy_terminal_self_stage_transition"]
    expected = {row["stat"]: row["resulting_stage"] for row in stage["transitions"]}
    stages = projected["active"]["self"]["hypothetical_stages"]
    assert stages["special-attack"]["status"] == "known" and stages["special-attack"]["value"] == expected["special-attack"]
    assert stages["special-defense"]["status"] == "known" and stages["special-defense"]["value"] == expected["special-defense"]
    assert stages["speed"]["status"] == "known" and stages["speed"]["value"] == expected["speed"]



def test_geomancy_power_herb_full_paralysis_branch_does_not_consume_or_boost():
    _snapshot, _d0, _own, authority = _power_herb_geomancy_authority(condition="paralysis")
    result = execute_runtime_d0_geomancy_power_herb_skip(authority)
    assert result["status"] == "resolved", result
    cancelled = [
        leaf for leaf in result["terminal_leaves"]
        if "cancelled_due_to_paralysis" in " ".join(str(x) for x in leaf["branch_path"])
    ]
    executed = [
        leaf for leaf in result["terminal_leaves"]
        if leaf["consequences"].get("geomancy_terminal_execution", {}).get("status") == "executed"
    ]
    assert cancelled and executed
    assert all("geomancy_power_herb_consumption" not in leaf["consequences"] for leaf in cancelled)
    assert all("geomancy_terminal_self_stage_transition" not in leaf["consequences"] for leaf in cancelled)
    assert all("geomancy_power_herb_consumption" in leaf["consequences"] for leaf in executed)
    assert all("geomancy_terminal_self_stage_transition" in leaf["consequences"] for leaf in executed)


def test_opponent_first_ko_prevents_geomancy_charge_boost_and_power_herb_consumption():
    _snapshot, _d0, _own, _opponent, order, pair = _current_turn_geomancy_pair(
        power_herb=True,
        own_hp=1,
        self_speed=1,
        opponent_speed=999,
    )
    assert order["status"] == "resolved" and order["order"] == "opponent_first", order
    assert pair["status"] == "evaluable", (pair.get("status"), pair.get("reason"))
    cancelled = [
        branch for branch in pair["terminal_branches"]
        if branch["second_action"]["state"] == "cancelled_due_to_faint"
    ]
    assert cancelled
    for branch in cancelled:
        assert branch["second_action"].get("leaf") is None
        first = branch["first_action_leaf"]
        assert first["consequences"]["target_final_hp"] == 0
        assert "geomancy_power_herb_consumption" not in first["consequences"]
        assert "geomancy_terminal_self_stage_transition" not in first["consequences"]



def test_power_herb_geomancy_first_special_damage_consumer_sees_boosted_spd():
    _s0, _d0, _own, _opp, order0, ordinary = _current_turn_geomancy_pair(
        power_herb=False, opponent_move="water-gun",
    )
    _s1, _d1, _own1, _opp1, order1, boosted = _current_turn_geomancy_pair(
        power_herb=True, opponent_move="water-gun",
    )
    assert order0["order"] == order1["order"] == "own_first"
    assert ordinary["status"] == boosted["status"] == "evaluable"

    def post_hp(pair):
        values = []
        for branch in pair["terminal_branches"]:
            second = branch["second_action"]
            leaf = second.get("leaf")
            if second.get("state") == "executed" and isinstance(leaf, dict) and leaf.get("hit_state") == "hit" and leaf.get("critical_state") == "non_critical":
                values.append(leaf["consequences"]["target_final_hp"])
        assert values
        return sorted(values)

    ordinary_hp = post_hp(ordinary)
    boosted_hp = post_hp(boosted)
    assert min(boosted_hp) > min(ordinary_hp)
    assert max(boosted_hp) > max(ordinary_hp)
