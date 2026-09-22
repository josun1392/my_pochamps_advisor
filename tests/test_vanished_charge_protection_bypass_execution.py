from copy import deepcopy
from fractions import Fraction

import pytest

from core.charge_move_repository import ChargeMoveRepository
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_detached_next_turn_ordinary_attack_execution import execute_detached_next_turn_ordinary_attack
from llm.advisor_detached_semi_invulnerable_charge_authority import (
    freeze_detached_semi_invulnerable_targetability_authority,
    materialize_detached_semi_invulnerable_charge_state_authority,
    validate_detached_semi_invulnerable_charge_state_authority,
)
from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation
from llm.advisor_detached_standard_charge_start import materialize_detached_standard_charge_start
from llm.advisor_detached_standard_charge_turn_two_attack_execution import (
    execute_detached_standard_charge_turn_two_attacks,
    materialize_detached_standard_charge_turn_two_execution_authority,
    materialize_detached_standard_charge_turn_two_terminal_execution_contract,
)
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_d0_canonical_contact_classification_authority import freeze_runtime_d0_canonical_contact_classification_authority
from llm.advisor_runtime_d0_standard_charge_power_herb_skip_execution import (
    execute_runtime_d0_standard_charge_power_herb_skip,
    freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority,
)
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import freeze_runtime_d0_standard_charge_start_readiness_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_ability_interaction_authority import build_ability_applicability_context
from llm.advisor_next_turn_predictive_mechanics_authority import materialize_next_turn_predictive_mechanics_authority
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_standard_charge_terminal_execution import execute_standard_charge_terminal_attack, materialize_standard_charge_terminal_execution_contract
from llm.advisor_vanished_protection_bypass_authority import (
    execute_vanished_terminal_through_protection,
    materialize_vanished_protection_bypass_break_authority,
    validate_vanished_protection_bypass_break_authority,
)
from tests.test_detached_immediate_protection_response_pair import _protect_action, _success
from tests.test_detached_next_turn_action_order_temporal_state import _production_temporal_handoff
from tests.test_detached_opponent_response_profile import _complete_state, _metadata, _owner, _snapshot, _state
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order
from tests.test_semi_invulnerable_charge_execution import _case, _incoming, _semi_metadata, _state_authority
from tests.test_standard_charge_start_immediate_pair_integration import _own_action, _with_terminal_mechanics_facts
from tests.test_runtime_d0_standard_charge_terminal_mechanics_authority import _ready, _refresh


VANISHED = ("phantom-force", "shadow-force")


@pytest.mark.parametrize(("move_id","power"), (("phantom-force", 90), ("shadow-force", 120)))
def test_vanished_charge_state_and_terminal_inventory(move_id, power):
    state, snapshot, d0, actor, target, action = _case(move_id)
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["status"] == "resolved" and readiness["outcome"] == "charge_start_ready", readiness
    start = materialize_detached_standard_charge_start(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        readiness_authority=readiness,
    )
    assert start["status"] == "resolved", start
    semi = start["semi_invulnerable_charge_state_authority"]
    assert semi["semi_invulnerability_class"] == "vanished"
    assert semi["state"] == "active"
    assert semi["canonical_lifecycle"]["protection_bypass_later_execution"] is True
    assert semi["source_move_id"] == move_id and semi["owner"] == actor and semi["original_target"] == target
    assert readiness["canonical_charge_lifecycle_authority"]["execution_model"] == "semi_invulnerable_then_execute"
    assert readiness["canonical_charge_lifecycle_authority"]["protection_bypass_later_execution"] is True
    assert start["action_leaf"]["consequences"]["semi_invulnerable_charge_state"] == semi
    intermediate = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=start["action_leaf"])
    assert intermediate["status"] == "resolved"
    assert intermediate["semi_invulnerable_charge_state_authority"] == semi
    effect = readiness["canonical_charge_lifecycle_authority"]
    assert effect["semi_invulnerability_class"] == "vanished"
    terminal = __import__("advisor.canonical_standard_charge_turn_two_effects", fromlist=["resolve_canonical_standard_charge_turn_two_effect"]).resolve_canonical_standard_charge_turn_two_effect(move_id)
    assert terminal["status"] == "resolved"
    assert {key: terminal["move"][key] for key in ("move_id","power","category","type","accuracy")} == {"move_id": move_id, "power": power, "category": "physical", "type": "ghost", "accuracy": 100}
    assert terminal["secondary"] == {"kind": "none", "chance": 0}


@pytest.mark.parametrize("move_id", VANISHED)
def test_vanished_blocks_ordinary_before_accuracy_and_rejects_named_airborne_exception(move_id):
    snapshot, d0, _actor, _target, _action, semi = _state_authority(move_id)
    target = semi["owner"]
    attacker = d0["active_owners"]["opponent"]

    tackle, tackle_meta = _incoming(d0, "tackle", _metadata("tackle")["metadata"])
    blocked = freeze_detached_semi_invulnerable_targetability_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, incoming_action=tackle,
        incoming_move_metadata_authority=tackle_meta, attacker=attacker, target=target,
        semi_invulnerable_state_authority=semi,
    )
    assert blocked["status"] == "resolved"
    assert blocked["outcome"] == "blocked_by_semi_invulnerability"

    gust, gust_meta = _incoming(
        d0, "gust", {"move_id": "gust", "category": "special", "power": 40, "type": "flying", "accuracy": 100, "priority": 0},
    )
    gust_result = freeze_detached_semi_invulnerable_targetability_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, incoming_action=gust,
        incoming_move_metadata_authority=gust_meta, attacker=attacker, target=target,
        semi_invulnerable_state_authority=semi,
    )
    assert gust_result["status"] == "resolved"
    assert gust_result["outcome"] == "blocked_by_semi_invulnerability"


@pytest.mark.parametrize("mode,expected", (("active","allowed_by_locked_on"), ("noguard","allowed_by_no_guard")))
def test_vanished_exact_locked_on_and_no_guard_bypass(mode, expected):
    kwargs = {"opponent_locked": "active"} if mode == "active" else {"opponent_locked": "inactive", "no_guard_side": "opponent"}
    _s, snapshot, d0, actor, original_target, action = _case("phantom-force", **kwargs)
    semi = materialize_detached_semi_invulnerable_charge_state_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=original_target,
        action_id=action["action_id"], move_id="phantom-force", source_leaf_id=f"{action['action_id']}:charge-start",
    )
    tackle, meta = _incoming(d0, "tackle", _metadata("tackle")["metadata"])
    result = freeze_detached_semi_invulnerable_targetability_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, incoming_action=tackle, incoming_move_metadata_authority=meta,
        attacker=d0["active_owners"]["opponent"], target=semi["owner"], semi_invulnerable_state_authority=semi,
    )
    assert result["status"] == "resolved", result
    assert result["outcome"] == expected
    assert result["accuracy_bypassed"] is True


@pytest.mark.parametrize("move_id", VANISHED)
def test_vanished_eot_transport_forced_continuation_and_retirement(move_id):
    handoff = _production_temporal_handoff(own_move=move_id, opponent_move="razor-wind")
    state, fingerprint = handoff["next_state"], handoff["resulting_branch_fingerprint"]
    row = state["next_turn_standard_charge_continuation_authorities"]["self"]
    semi = row["semi_invulnerable_charge_state_authority"]
    assert semi["semi_invulnerability_class"] == "vanished" and semi["state"] == "active"

    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
    )
    assert forced["status"] == "resolved", forced
    authority = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
        forced_continuation=forced, predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"],
    )
    assert authority["status"] == "resolved", authority
    contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(execution_authority=authority, side="self")
    assert contract["status"] == "resolved", contract
    assert contract["semi_invulnerable_charge_state_authority"] == semi
    result = execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    assert result["status"] == "resolved", result
    ledger = result["actions"]["self"]
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all(
        leaf["consequences"]["semi_invulnerable_state_retirement"]["state_after"] == "inactive"
        for leaf in ledger["terminal_leaves"]
    )


@pytest.mark.parametrize("move_id", VANISHED)
def test_vanished_power_herb_is_immediate_without_waiting_state(move_id):
    _s, snapshot, d0, actor, target, action = _case(move_id, power_herb=True)
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "power_herb_charge_skip_ready", readiness
    authority = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": move_id}, readiness_authority=readiness,
    )
    assert authority["status"] == "resolved", authority
    result = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert result["status"] == "resolved", result
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all("semi_invulnerable_charge_state" not in leaf["consequences"] for leaf in result["terminal_leaves"])


@pytest.mark.parametrize("move_id", VANISHED)
def test_vanished_state_strict_tamper_and_generic_guard(move_id):
    _snapshot0, _d0, _actor, _target, _action, state = _state_authority(move_id)
    assert validate_detached_semi_invulnerable_charge_state_authority(state) is None
    forged = deepcopy(state); forged["semi_invulnerability_class"] = "airborne"
    assert validate_detached_semi_invulnerable_charge_state_authority(forged) is not None
    forged = deepcopy(state); forged["source_move_id"] = "fly"
    assert validate_detached_semi_invulnerable_charge_state_authority(forged) is not None
    forged = deepcopy(state); forged["canonical_lifecycle"]["protection_bypass_later_execution"] = False
    assert validate_detached_semi_invulnerable_charge_state_authority(forged) is not None
    guard = ChargeMoveRepository().immediate_execution_guard(move_id)
    assert guard["reason"] == "two_turn_execution_unrepresented"
    assert guard["canonical_recognition_grants_immediate_execution"] is False


def _protect_effect(d0, move_id="protect"):
    from llm.advisor_hypothetical_protection_effects import project_self_protection
    from llm.advisor_hypothetical_silk_trap_effects import (
        project_baneful_bunker_protection, project_burning_bulwark_protection,
        project_kings_shield_protection, project_obstruct_protection,
        project_silk_trap_protection, project_spiky_shield_protection,
    )
    action = _protect_action(d0, move_id)
    branch = deepcopy(d0["strategy_state"])
    owner = d0["active_owners"]["opponent"]
    branch["active"]["self"] = deepcopy(branch["active"]["opponent"])
    proxy = {"owner": owner, "move": deepcopy(action["metadata_authority"]["metadata"])}
    success = _success(owner)
    family = {
        "silk-trap": project_silk_trap_protection,
        "kings-shield": project_kings_shield_protection,
        "obstruct": project_obstruct_protection,
        "spiky-shield": project_spiky_shield_protection,
        "baneful-bunker": project_baneful_bunker_protection,
        "burning-bulwark": project_burning_bulwark_protection,
    }.get(move_id)
    if family is not None:
        effect = family(branch_state=branch, action=proxy, owner=owner, success_authority=success)
    else:
        effect = project_self_protection(branch_state=branch, action=proxy, expected_owner=owner, success_authority=success)
    assert effect["status"] == "resolved", effect
    return effect, action


@pytest.mark.parametrize(("move_id","protect_move"), (("phantom-force","protect"), ("shadow-force","detect")))
def test_typed_protection_bypass_authority_is_strict(move_id, protect_move):
    _s, snapshot, d0, actor, target, action = _case(move_id, power_herb=True)
    effect, protect_action = _protect_effect(d0, protect_move)
    authority = materialize_vanished_protection_bypass_break_authority(
        session_id=d0["session_id"],
        source_runtime_fingerprint=d0["source_runtime_fingerprint"],
        source_branch_fingerprint=d0["strategy_preview_fingerprint"],
        decision_owner=d0["decision_owner"], attacker=actor, protected_target=target,
        source_action_id=action["action_id"], move_id=move_id, source_terminal_leaf_id=f"{action['action_id']}:hit",
        active_protection_effect=effect, protection_action_authority=protect_action,
        protection_context_fingerprint=d0["strategy_preview_fingerprint"],
    )
    assert authority["status"] == "resolved", authority
    assert authority["outcome"] == "bypasses_and_breaks"
    assert authority["timing"] == "after_accuracy_before_hit_resolution"
    assert authority["blocked_contact_reactive_consequences_apply"] is False
    assert validate_vanished_protection_bypass_break_authority(authority) is None

    forged = deepcopy(authority); forged["canonical_breaks_protect"] = False
    assert validate_vanished_protection_bypass_break_authority(forged) is not None
    forged = deepcopy(authority); forged["protected_target"] = actor
    assert validate_vanished_protection_bypass_break_authority(forged) is not None
    forged = deepcopy(authority); forged["source_terminal_leaf_id"] = "forged"
    assert validate_vanished_protection_bypass_break_authority(forged) is not None


@pytest.mark.parametrize("protect_move", ("protect","detect","silk-trap","kings-shield","obstruct","spiky-shield","baneful-bunker","burning-bulwark"))
def test_vanished_bypass_owner_admits_existing_single_target_protection_families(protect_move):
    _s, _snapshot0, d0, actor, target, action = _case("phantom-force", power_herb=True)
    effect, protect_action = _protect_effect(d0, protect_move)
    authority = materialize_vanished_protection_bypass_break_authority(
        session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"],
        source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=d0["decision_owner"],
        attacker=actor, protected_target=target, source_action_id=action["action_id"], move_id="phantom-force",
        source_terminal_leaf_id=f"{action['action_id']}:hit", active_protection_effect=effect,
        protection_action_authority=protect_action, protection_context_fingerprint=d0["strategy_preview_fingerprint"],
    )
    assert authority["status"] == "resolved", (protect_move, authority)


def test_geomancy_stays_outside_terminal_family():
    from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
    assert resolve_canonical_standard_charge_turn_two_effect("geomancy")["status"] == "unsupported"


@pytest.mark.parametrize("move_id", VANISHED)
def test_opponent_first_protect_does_not_break_on_ordinary_charge_turn(move_id):
    _s, snapshot, d0, _actor, _target, own = _case(move_id)
    protect = _protect_action(d0, "protect")
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot,
        own_action=own, opponent_action=protect,
        action_order_authority=_order(d0, own, protect, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
    )
    assert pair["status"] == "evaluable", (pair.get("status"), pair.get("reason"))
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    charge_leaves = [row["first_action_leaf"] for row in pair["terminal_branches"] if row["second_action"]["state"] == "executed_protection"]
    assert charge_leaves
    assert all(leaf["consequences"].get("semi_invulnerable_charge_state", {}).get("semi_invulnerability_class") == "vanished" for leaf in charge_leaves)
    assert all("vanished_protection_bypass_break" not in leaf["consequences"] for leaf in charge_leaves)


@pytest.mark.parametrize(("move_id","protect_move"), (("phantom-force","protect"), ("shadow-force","detect")))
def test_power_herb_terminal_bypasses_and_breaks_protect_detect(move_id, protect_move):
    _s, snapshot, d0, _actor, _target, own = _case(move_id, power_herb=True)
    protect = _protect_action(d0, protect_move)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot,
        own_action=own, opponent_action=protect,
        action_order_authority=_order(d0, own, protect, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
    )
    assert pair["status"] == "evaluable", (pair.get("status"), pair.get("reason"))
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    hit_rows = [
        row for row in pair["terminal_branches"]
        if row["second_action"]["state"] == "executed_bypassing_protection"
    ]
    assert hit_rows
    for row in hit_rows:
        leaf = row["first_action_leaf"]
        assert leaf["hit_state"] == "hit"
        bypass = leaf["consequences"]["vanished_protection_bypass_break"]
        assert bypass["outcome"] == "bypasses_and_breaks"
        assert bypass["protection_move_id"] == protect_move
        assert bypass["timing"] == "after_accuracy_before_hit_resolution"
        assert leaf["consequences"]["protection_state_transition"]["state_after"] == "retired"
        assert "semi_invulnerable_charge_state" not in leaf["consequences"]


@pytest.mark.parametrize("protect_move", ("spiky-shield","kings-shield","obstruct","baneful-bunker","burning-bulwark","silk-trap"))
def test_power_herb_bypasses_reactive_shield_without_blocked_contact_reaction(protect_move):
    _s, snapshot, d0, _actor, _target, own = _case("phantom-force", power_herb=True)
    protect = _protect_action(d0, protect_move)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot,
        own_action=own, opponent_action=protect,
        action_order_authority=_order(d0, own, protect, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
    )
    assert pair["status"] == "evaluable", (protect_move, pair.get("status"), pair.get("reason"))
    rows = [row for row in pair["terminal_branches"] if row["second_action"]["state"] == "executed_bypassing_protection"]
    assert rows
    for row in rows:
        consequences = row["first_action_leaf"]["consequences"]
        assert consequences["vanished_protection_bypass_break"]["protection_move_id"] == protect_move
        assert consequences.get("deterministic_stage_effect") is None
        assert consequences.get("silk_trap_reactive_consequence") is None
        assert consequences.get("spiky_shield_reactive_damage") is None
        assert consequences.get("baneful_bunker_reactive_poison") is None
        assert consequences.get("burning_bulwark_reactive_burn") is None


def _forced_vanished_contract(move_id="phantom-force"):
    handoff = _production_temporal_handoff(own_move=move_id, opponent_move="razor-wind")
    state, fingerprint = handoff["next_state"], handoff["resulting_branch_fingerprint"]
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
    )
    authority = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
        forced_continuation=forced, predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"],
    )
    assert authority["status"] == "resolved", authority
    contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=authority, side="self",
    )
    assert contract["status"] == "resolved", contract
    return handoff, authority, contract


def test_turn_two_terminal_composer_bypasses_active_protect_and_breaks_only_hit_leaves():
    from llm.advisor_hypothetical_protection_effects import canonical_protection_metadata

    _handoff, _authority, contract = _forced_vanished_contract("phantom-force")
    protect_effect = {
        "status": "resolved",
        "owner": deepcopy(contract["target"]),
        "metadata": canonical_protection_metadata("protect"),
        "provenance": "focused_exact_turn_two_protection_effect",
    }
    protect_action = {
        "action_id": "next-turn:protect",
        "move_id": "protect",
        "opponent_actor": deepcopy(contract["target"]),
        "target_owner": deepcopy(contract["actor"]),
        "source_next_decision_fingerprint": contract["source_state_fingerprint"],
    }
    result = execute_vanished_terminal_through_protection(
        execution_contract=contract,
        active_protection_effect=protect_effect,
        protection_action_authority=protect_action,
    )
    assert result["status"] == "resolved", result
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    hits = [leaf for leaf in result["terminal_leaves"] if leaf["hit_state"] == "hit"]
    misses = [leaf for leaf in result["terminal_leaves"] if leaf["hit_state"] == "miss"]
    assert hits
    assert all(
        leaf["consequences"]["vanished_protection_bypass_break"]["outcome"] == "bypasses_and_breaks"
        and leaf["consequences"]["protection_state_transition"]["state_after"] == "retired"
        for leaf in hits
    )
    assert all("vanished_protection_bypass_break" not in leaf["consequences"] for leaf in misses)


def test_power_herb_bypass_still_allows_normal_rough_skin_after_real_contact_hit():
    state, _snapshot0, _d00, actor, target, _action0 = _case("phantom-force", power_herb=True)
    raw = state["opponent_side"]["pokemon"][0]
    raw["current_ability"] = "rough-skin"
    raw["current_type"] = ["psychic"]
    raw["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    own = _own_action(d0, actor, "phantom-force", metadata=_semi_metadata("phantom-force"))
    protect = _protect_action(d0, "protect")
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=own,
        attacker=actor, target=target,
    )
    assert contact["status"] == "resolved" and contact["contact_state"] == "contact", contact
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot,
        own_action=own, opponent_action=protect,
        action_order_authority=_order(d0, own, protect, "opponent_first"),
        opponent_protection_success_authority=_success(target),
        incoming_contact_authority=contact,
    )
    assert pair["status"] == "evaluable", pair
    hits = [row["first_action_leaf"] for row in pair["terminal_branches"] if row["second_action"]["state"] == "executed_bypassing_protection"]
    assert hits
    assert any(
        leaf["consequences"].get("contact_reactive_damage", {}).get("outcome") == "applies"
        and any(source["source_kind"] == "rough-skin" for source in leaf["consequences"]["contact_reactive_damage"]["ordered_sources"])
        for leaf in hits
    )
    assert all(leaf["consequences"].get("spiky_shield_reactive_damage") is None for leaf in hits)


@pytest.mark.parametrize(
    ("survival_key", "ability", "item"),
    (("sturdy_survival", "sturdy", None), ("focus_sash_survival", "pressure", "focus-sash")),
)
def test_power_herb_shadow_force_reuses_sturdy_and_focus_sash(survival_key, ability, item):
    state, _snapshot0, _d00 = _ready()
    actor_raw = state["self_side"]["pokemon"][0]
    actor_raw["known_item"] = "power-herb"
    actor_raw["known_item_provenance"] = {
        "event_kind": "current_item_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "status": "known",
    }
    target_raw = state["opponent_side"]["pokemon"][0]
    target_raw["current_hp"] = 100
    target_raw["max_hp"] = 100
    target_raw["fainted"] = False
    target_raw["current_final_stats"]["defense"]["value"] = 1
    target_raw["current_ability"] = ability
    target_raw["current_ability_provenance"] = {
        "event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1,
    }
    if ability == "sturdy":
        state["ability_applicability_context"] = build_ability_applicability_context(
            session_id=state["session_id"],
            source={"side": "opponent", "slot_index": 0, "pokemon_id": target_raw["pokemon_id"]},
            ability_id="sturdy", status="applicable",
        )
    target_raw["known_item"] = item
    target_raw["known_item_provenance"] = {
        "event_kind": "current_item_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "status": "known" if item else "known_absent",
    }
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, "shadow-force")
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    authority = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "shadow-force"}, readiness_authority=readiness,
    )
    kernel = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"] == "resolved", kernel
    applied = [
        leaf for leaf in kernel["terminal_leaves"]
        if isinstance(leaf["consequences"].get(survival_key), dict)
        and leaf["consequences"][survival_key].get("outcome") in {"applied", "activated"}
    ]
    assert applied
    assert all(leaf["consequences"]["target_final_hp"] == 1 for leaf in applied)


def test_ordinary_turn_two_phantom_force_preserves_life_orb_support():
    handoff = _production_temporal_handoff(
        own_move="phantom-force", opponent_move="razor-wind", self_item="life-orb",
    )
    state = deepcopy(handoff["next_state"])
    field = state.setdefault("field", {})
    field["magic_room_status"] = "inactive"
    field["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation",
        "source_observation_id": "turn-two-phantom-life-orb-magic-room", "source_sequence": 1,
    }
    current = state.setdefault("current_state", {}).setdefault("field_state_context", {}).setdefault("current_field", {})
    current["magic_room_status"] = "inactive"
    current["magic_room_status_provenance"] = deepcopy(field["magic_room_status_provenance"])
    fingerprint = fingerprint_transition_preview_state(state)
    predictive = materialize_next_turn_predictive_mechanics_authority(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
        source_post_eot_fingerprint=handoff["next_turn_predictive_mechanics_authority"]["source_post_eot_fingerprint"],
    )
    assert predictive["status"] == "resolved", predictive
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
    )
    authority = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
        forced_continuation=forced, predictive_mechanics=predictive,
    )
    contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=authority, side="self",
    )
    assert contract["status"] == "resolved", contract
    assert contract["attacker_life_orb_authority"]["damage_modifier"]["applies"] is True
    target_mechanics = deepcopy(contract["target_mechanics"])
    target_mechanics["types"] = {"status": "known", "value": ("psychic",)}
    auth = deepcopy(contract["caller_authentication"])
    auth["target_mechanics"] = deepcopy(target_mechanics)
    executable = materialize_standard_charge_terminal_execution_contract(
        execution_mode=contract["execution_mode"],
        source_state_fingerprint=contract["source_state_fingerprint"],
        decision_owner=contract["decision_owner"], actor=contract["actor"], target=contract["target"],
        action_id=contract["action_id"], move_id=contract["move_id"],
        canonical_terminal_effect=contract["canonical_terminal_effect"],
        actor_mechanics=contract["actor_mechanics"], target_mechanics=target_mechanics,
        attacker_held_item_effect_authority=contract["attacker_held_item_effect_authority"],
        target_held_item_effect_authority=contract["target_held_item_effect_authority"],
        target_sturdy_authority=contract["target_sturdy_authority"],
        target_focus_sash_authority=contract["target_focus_sash_authority"],
        attacker_life_orb_authority=contract["attacker_life_orb_authority"],
        caller_action_authority=contract["caller_action_authority"],
        caller_authentication=auth,
        semi_invulnerable_charge_state_authority=contract["semi_invulnerable_charge_state_authority"],
    )
    assert executable["status"] == "resolved", executable
    result = execute_standard_charge_terminal_attack(execution_contract=executable)
    assert result["status"] == "resolved", result
    leaves = result["terminal_leaves"]
    assert any(
        isinstance(leaf["consequences"].get("life_orb"), dict)
        and leaf["consequences"]["life_orb"].get("damage_modifier", {}).get("applies") is True
        and leaf["consequences"]["own_final_hp"] < executable["actor_mechanics"]["current_hp"]["current_hp"]
        for leaf in leaves if leaf["hit_state"] == "hit" and leaf["consequences"].get("damage", 0) > 0
    )


def test_faster_turn_two_opponent_still_sees_active_vanished_state():
    from tests.test_semi_invulnerable_charge_execution import _next_turn_opponent_action_chain

    _handoff, order, ordinary, _charge = _next_turn_opponent_action_chain(
        "tackle", self_speed=50, opponent_speed=150, own_move="phantom-force",
    )
    assert order["status"] == "resolved" and order["order"] == "opponent_first", order
    assert ordinary["action"]["semi_invulnerable_charge_state_authority"]["state"] == "active"
    assert ordinary["action"]["semi_invulnerable_charge_state_authority"]["semi_invulnerability_class"] == "vanished"
    result = execute_detached_next_turn_ordinary_attack(execution_authority=ordinary)
    assert result["status"] in {"resolved", "incomplete"}, result
    if result["status"] == "resolved":
        assert all(
            leaf["consequences"]["semi_invulnerable_targetability"]["outcome"] == "blocked_by_semi_invulnerability"
            for leaf in result["action_ledger"]["terminal_leaves"]
        )
    else:
        assert "locked_on" in result.get("reason", "") or "targetability" in result.get("reason", "")


def _recontract_vanished(contract, *, actor_mechanics=None, target_mechanics=None):
    actor_mechanics = deepcopy(actor_mechanics if actor_mechanics is not None else contract["actor_mechanics"])
    target_mechanics = deepcopy(target_mechanics if target_mechanics is not None else contract["target_mechanics"])
    auth = deepcopy(contract["caller_authentication"])
    auth["actor_mechanics"] = deepcopy(actor_mechanics)
    auth["target_mechanics"] = deepcopy(target_mechanics)
    return materialize_standard_charge_terminal_execution_contract(
        execution_mode=contract["execution_mode"],
        source_state_fingerprint=contract["source_state_fingerprint"],
        decision_owner=contract["decision_owner"],
        actor=contract["actor"], target=contract["target"],
        action_id=contract["action_id"], move_id=contract["move_id"],
        canonical_terminal_effect=contract["canonical_terminal_effect"],
        actor_mechanics=actor_mechanics, target_mechanics=target_mechanics,
        attacker_held_item_effect_authority=contract["attacker_held_item_effect_authority"],
        target_held_item_effect_authority=contract["target_held_item_effect_authority"],
        target_sturdy_authority=contract["target_sturdy_authority"],
        target_focus_sash_authority=contract["target_focus_sash_authority"],
        attacker_life_orb_authority=contract["attacker_life_orb_authority"],
        caller_action_authority=contract["caller_action_authority"],
        caller_authentication=auth,
        semi_invulnerable_charge_state_authority=contract["semi_invulnerable_charge_state_authority"],
    )


def test_vanished_retirement_reasons_cover_hit_miss_paralysis_confusion_and_faint():
    _handoff, _authority, contract = _forced_vanished_contract("phantom-force")

    hit_result = execute_standard_charge_terminal_attack(execution_contract=contract)
    assert hit_result["status"] == "resolved", hit_result
    hit_leaves = [leaf for leaf in hit_result["terminal_leaves"] if leaf["hit_state"] == "hit"]
    assert hit_leaves and all(
        leaf["consequences"]["semi_invulnerable_state_retirement"]["reason"] == "terminal_attack_executed"
        for leaf in hit_leaves
    )

    inaccurate_actor = deepcopy(contract["actor_mechanics"])
    inaccurate_target = deepcopy(contract["target_mechanics"])
    inaccurate_actor["current_stages"]["values"]["accuracy"] = -6
    inaccurate_target["current_stages"]["values"]["evasion"] = 6
    miss_contract = _recontract_vanished(
        contract, actor_mechanics=inaccurate_actor, target_mechanics=inaccurate_target,
    )
    miss_result = execute_standard_charge_terminal_attack(execution_contract=miss_contract)
    assert miss_result["status"] == "resolved", miss_result
    misses = [leaf for leaf in miss_result["terminal_leaves"] if leaf["hit_state"] == "miss"]
    assert misses and all(
        leaf["consequences"]["semi_invulnerable_state_retirement"]["reason"] == "terminal_attack_missed"
        for leaf in misses
    )

    paralyzed = deepcopy(contract["actor_mechanics"])
    paralyzed["condition"] = {"status": "known_present", "condition": "paralysis"}
    paralyzed["direct_mechanics"]["combatant"]["status"] = "paralysis"
    paralysis = execute_standard_charge_terminal_attack(
        execution_contract=_recontract_vanished(contract, actor_mechanics=paralyzed),
    )
    cancelled = [
        leaf for leaf in paralysis["terminal_leaves"]
        if "cancelled_due_to_paralysis" in " ".join(str(value) for value in leaf["branch_path"])
    ]
    assert cancelled and all(
        leaf["consequences"]["semi_invulnerable_state_retirement"]["reason"] == "full_paralysis_cancellation"
        for leaf in cancelled
    )

    confused = deepcopy(contract["actor_mechanics"])
    confused["confusion_state"] = {"status": "known_confused"}
    confused["confusion_progression"] = {
        "status": "known",
        "value": {"origin_id": "vanished-confusion", "prior_opportunities": 0, "duration": 3},
    }
    confused["direct_mechanics"]["combatant"]["pokemon_id"] = contract["actor"]["pokemon_id"]
    confusion = execute_standard_charge_terminal_attack(
        execution_contract=_recontract_vanished(contract, actor_mechanics=confused),
    )
    assert confusion["status"] == "resolved", confusion
    self_hits = [
        leaf for leaf in confusion["terminal_leaves"]
        if "confusion_self_hit" in " ".join(str(value) for value in leaf["branch_path"])
    ]
    assert self_hits and all(
        leaf["consequences"]["semi_invulnerable_state_retirement"]["reason"] == "confusion_self_hit"
        for leaf in self_hits
    )

    fainted = deepcopy(contract["actor_mechanics"])
    fainted["current_hp"]["current_hp"] = 0
    fainted["fainted"] = True
    fainted["direct_mechanics"]["combatant"]["current_hp"] = 0
    faint = execute_standard_charge_terminal_attack(
        execution_contract=_recontract_vanished(contract, actor_mechanics=fainted),
    )
    assert faint["status"] == "resolved", faint
    assert faint["terminal_leaves"][0]["consequences"]["semi_invulnerable_state_retirement"]["reason"] == "actor_faint_prevents_continuation"


def test_power_herb_pre_action_paralysis_cancellation_does_not_consume_or_create_vanished_state():
    _s, snapshot, d0, actor, target, action = _case(
        "phantom-force", power_herb=True, condition="paralysis",
    )
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "power_herb_charge_skip_ready", readiness
    authority = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "phantom-force"}, readiness_authority=readiness,
    )
    result = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert result["status"] == "resolved", result
    cancelled = [
        leaf for leaf in result["terminal_leaves"]
        if leaf["consequences"].get("execution_failure") == "cancelled_due_to_paralysis"
    ]
    assert cancelled
    assert all("power_herb_consumption" not in leaf["consequences"] for leaf in cancelled)
    assert all("hypothetical_self_item" not in leaf["consequences"] for leaf in cancelled)
    assert all("semi_invulnerable_charge_state" not in leaf["consequences"] for leaf in cancelled)


def test_ordinary_tackle_remains_blocked_by_protect():
    state = _with_terminal_mechanics_facts(_complete_state(_state()))
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = __import__("tests.test_detached_immediate_protection_response_pair", fromlist=["_own_action"])._own_action(d0, "tackle")
    protect = _protect_action(d0, "protect")
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot,
        own_action=own, opponent_action=protect,
        action_order_authority=_order(d0, own, protect, "opponent_first"),
        opponent_protection_success_authority=_success(d0["active_owners"]["opponent"]),
    )
    assert pair["status"] == "evaluable", pair
    assert all(row["second_action"]["state"] == "prevented_by_protection" for row in pair["terminal_branches"])
