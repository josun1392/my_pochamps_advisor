from copy import deepcopy
from fractions import Fraction

import pytest

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from llm.advisor_runtime_d0_solar_charge_weather_authority import (
    freeze_runtime_d0_solar_charge_weather_decision_authority,
)
from llm.advisor_runtime_d0_solar_weather_skip_execution import (
    execute_runtime_d0_solar_weather_skip,
    freeze_runtime_d0_solar_weather_skip_execution_authority,
    materialize_runtime_d0_solar_weather_skip_terminal_execution_contract,
)
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import (
    freeze_runtime_d0_standard_charge_start_readiness_authority,
)
from llm.advisor_runtime_d0_standard_charge_power_herb_skip_execution import (
    execute_runtime_d0_standard_charge_power_herb_skip,
    freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context,
    freeze_runtime_strategy_d0,
)
from llm.advisor_solar_terminal_weather_damage_modifier import (
    materialize_solar_terminal_weather_damage_modifier_authority,
)
from llm.advisor_standard_charge_terminal_execution import (
    execute_standard_charge_terminal_attack,
    validate_standard_charge_terminal_execution_contract,
)
from llm.advisor_ability_interaction_authority import build_ability_applicability_context
from tests.test_detached_intermediate_predictive_authority import _owner
from tests.test_runtime_d0_standard_charge_terminal_mechanics_authority import _ready, _refresh
from tests.test_standard_charge_start_immediate_pair_integration import _own_action
from tests.test_detached_next_turn_action_order_temporal_state import _production_temporal_handoff
from llm.advisor_detached_standard_charge_forced_continuation import (
    materialize_detached_standard_charge_forced_continuation,
)
from llm.advisor_detached_standard_charge_turn_two_attack_execution import (
    execute_detached_standard_charge_turn_two_attacks,
    materialize_detached_standard_charge_turn_two_execution_authority,
    materialize_detached_standard_charge_turn_two_terminal_execution_contract,
)
from llm.advisor_next_turn_predictive_mechanics_authority import (
    materialize_next_turn_predictive_mechanics_authority,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from tests.test_standard_charge_start_immediate_pair_integration import (
    _opponent_action,
    _order,
    _with_terminal_mechanics_facts,
    _complete_state,
    _state as _pair_state,
    _snapshot as _pair_snapshot,
)


SOLAR = ("solar-beam", "solar-blade")


def _state_case(move_id="solar-beam", *, weather="none", item=None, item_status="known_absent", magic_room="inactive", actor_ability="static"):
    state, _snapshot0, _d00 = _ready()
    field = state["field"]
    field["weather"] = weather
    field["weather_provenance"] = {
        "event_kind": "current_weather_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    field["magic_room_status"] = magic_room
    field["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": "solar-magic-room",
        "source_sequence": 1,
    }
    actor_raw = state["self_side"]["pokemon"][0]
    actor_raw["known_item"] = item
    actor_raw["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": item_status,
    }
    actor_raw["current_ability"] = actor_ability
    actor_raw["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, move_id)
    return state, snapshot, d0, actor, target, action


@pytest.mark.parametrize("move_id", SOLAR)
def test_solar_canonical_terminal_effect_is_bounded_and_non_granting(move_id):
    effect = resolve_canonical_standard_charge_turn_two_effect(move_id)
    assert effect["status"] == "resolved"
    assert effect["lifecycle"]["lifecycle_family"] == "weather_sensitive_charge_then_damage"
    assert effect["lifecycle"]["canonical_recognition_grants_immediate_execution"] is False
    assert effect["secondary"] == {"kind": "none", "chance": 0}
    expected = {
        "solar-beam": (120, "special"),
        "solar-blade": (125, "physical"),
    }[move_id]
    assert (effect["move"]["power"], effect["move"]["category"], effect["move"]["type"], effect["move"]["accuracy"]) == (expected[0], expected[1], "grass", 100)


@pytest.mark.parametrize("move_id", SOLAR)
def test_exact_neutral_weather_uses_ordinary_charge(move_id):
    _state0, snapshot, d0, actor, target, action = _state_case(move_id)
    weather = freeze_runtime_d0_solar_charge_weather_decision_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert (weather["status"], weather["outcome"]) == ("resolved", "ordinary_charge")
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["status"] == "resolved"
    assert readiness["outcome"] == "charge_start_ready"
    assert readiness["skip_reason"] == "ordinary_charge"


@pytest.mark.parametrize("move_id", SOLAR)
def test_sunny_weather_executes_same_turn_without_item_consumption(move_id):
    _state0, snapshot, d0, actor, target, action = _state_case(move_id, weather="sun")
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "weather_charge_skip_ready"
    assert readiness["skip_reason"] == "weather_skip"
    execution = freeze_runtime_d0_solar_weather_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": move_id}, readiness_authority=readiness,
    )
    assert execution["status"] == "resolved", execution
    kernel = execute_runtime_d0_solar_weather_skip(execution_authority=execution)
    assert kernel["status"] == "resolved", kernel
    assert kernel["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all("power_herb_consumption" not in leaf["consequences"] for leaf in kernel["terminal_leaves"])


def test_sunny_plus_power_herb_prefers_weather_skip_and_preserves_power_herb():
    _state0, snapshot, d0, actor, target, action = _state_case(
        "solar-beam", weather="sun", item="power-herb", item_status="known",
    )
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "weather_charge_skip_ready"
    assert readiness["skip_reason"] == "weather_skip"
    assert readiness["power_herb_applicability_state"]["status"] == "active"
    execution = freeze_runtime_d0_solar_weather_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"}, readiness_authority=readiness,
    )
    kernel = execute_runtime_d0_solar_weather_skip(execution_authority=execution)
    assert kernel["status"] == "resolved", kernel
    assert all("power_herb_consumption" not in leaf["consequences"] for leaf in kernel["terminal_leaves"])
    assert all("actor_item_after" not in leaf["consequences"] for leaf in kernel["terminal_leaves"])


def test_non_sunny_active_power_herb_consumes_only_executing_branches():
    _state0, snapshot, d0, actor, target, action = _state_case(
        "solar-blade", weather="rain", item="power-herb", item_status="known",
    )
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "power_herb_charge_skip_ready"
    assert readiness["skip_reason"] == "power_herb_skip"
    execution = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-blade"}, readiness_authority=readiness,
    )
    assert execution["status"] == "resolved", execution
    kernel = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=execution)
    assert kernel["status"] == "resolved", kernel
    assert all("power_herb_consumption" in leaf["consequences"] for leaf in kernel["terminal_leaves"])


@pytest.mark.parametrize("weather", ("rain", "sandstorm", "snow"))
def test_weak_weather_terminal_modifier_is_exact_half(weather):
    _state0, snapshot, d0, actor, target, action = _state_case("solar-beam", weather=weather)
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "charge_start_ready"
    terminal = readiness["solar_weather_decision_authority"]
    assert terminal["outcome"] == "weak_weather_charge"

    from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import freeze_runtime_d0_standard_charge_terminal_mechanics_authority
    bundle = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"},
    )
    assert bundle["status"] == "resolved", bundle
    modifier = materialize_solar_terminal_weather_damage_modifier_authority(
        move_id="solar-beam", actor=actor, target=target, action_id=action["action_id"],
        source_state_fingerprint=d0["source_runtime_fingerprint"],
        actor_mechanics=bundle["actor_participant_mechanics_authority"],
    )
    assert modifier["status"] == "resolved"
    assert modifier["weak_weather"] is True
    assert modifier["modifier_fraction"] == {"numerator": 1, "denominator": 2}
    assert modifier["modifier_q12"] == 2048
    assert modifier["modifier_stage"] == "weather_modifier_after_generic_weather_before_critical"


@pytest.mark.parametrize("weather", ("sun", "none"))
def test_non_weak_terminal_weather_has_neutral_modifier(weather):
    _state0, snapshot, d0, actor, target, action = _state_case("solar-beam", weather=weather)
    from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import freeze_runtime_d0_standard_charge_terminal_mechanics_authority
    bundle = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"},
    )
    modifier = materialize_solar_terminal_weather_damage_modifier_authority(
        move_id="solar-beam", actor=actor, target=target, action_id=action["action_id"],
        source_state_fingerprint=d0["source_runtime_fingerprint"],
        actor_mechanics=bundle["actor_participant_mechanics_authority"],
    )
    assert modifier["modifier_fraction"] == {"numerator": 1, "denominator": 1}
    assert modifier["modifier_q12"] == 4096


def test_unknown_weather_fails_closed():
    state, _snapshot0, _d00 = _ready()
    state["field"]["weather"] = {"knowledge": "unknown"}
    state["field"].pop("weather_provenance", None)
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, "solar-beam")
    weather = freeze_runtime_d0_solar_charge_weather_decision_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert weather["status"] == "incomplete"
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["status"] == "incomplete"
    assert readiness["reason"] == "solar_current_weather_unknown"


def test_sunny_life_orb_uses_current_item_without_power_herb_adapter():
    _state0, snapshot, d0, actor, target, action = _state_case(
        "solar-beam", weather="sun", item="life-orb", item_status="known",
    )
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    execution = freeze_runtime_d0_solar_weather_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"}, readiness_authority=readiness,
    )
    assert execution["status"] == "resolved", execution
    assert execution["attacker_life_orb_terminal_authority"]["damage_modifier"]["applies"] is True
    kernel = execute_runtime_d0_solar_weather_skip(execution_authority=execution)
    assert kernel["status"] == "resolved", kernel
    assert any(leaf["consequences"]["life_orb"]["outcome"] == "recoiled" for leaf in kernel["terminal_leaves"])


@pytest.mark.parametrize("move_id", SOLAR)
def test_normal_solar_charge_reaches_authenticated_turn_two_shared_kernel(move_id):
    handoff = _production_temporal_handoff(
        own_move=move_id,
        opponent_move="razor-wind",
        weather="none",
    )
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    )
    assert forced["status"] == "resolved", forced
    own = forced["forced_continuation_actions"]["self"]
    assert own["status"] == "resolved"
    assert own["move_id"] == move_id
    authority = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        forced_continuation=forced,
        predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"],
    )
    assert authority["status"] == "resolved", authority
    result = execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    assert result["status"] == "resolved", result
    ledger = result["actions"]["self"]
    assert ledger["status"] == "resolved", ledger
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def _reweather_next_turn(handoff, weather):
    state = deepcopy(handoff["next_state"])
    for side in ("self", "opponent"):
        row = state["post_eot_predictive_mechanics_authorities"][side]
        assert row["status"] == "resolved"
        row["field"] = {**deepcopy(row["field"]), "weather": weather}
    current_field = state.setdefault("current_state", {}).setdefault("field_state_context", {}).setdefault("current_field", {})
    current_field["weather"] = weather
    fingerprint = fingerprint_transition_preview_state(state)
    source_post_eot = handoff["next_turn_predictive_mechanics_authority"]["source_post_eot_fingerprint"]
    predictive = materialize_next_turn_predictive_mechanics_authority(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        source_post_eot_fingerprint=source_post_eot,
    )
    assert predictive["status"] == "resolved", predictive
    return state, fingerprint, predictive


@pytest.mark.parametrize(
    ("turn_one_weather", "turn_two_weather", "expected_q12"),
    (("none", "rain", 2048), ("rain", "none", 4096)),
)
def test_turn_two_solar_modifier_uses_terminal_weather_not_turn_one_weather(turn_one_weather, turn_two_weather, expected_q12):
    handoff = _production_temporal_handoff(
        own_move="solar-beam",
        opponent_move="razor-wind",
        weather=turn_one_weather,
    )
    state, fingerprint, predictive = _reweather_next_turn(handoff, turn_two_weather)
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    )
    assert forced["status"] == "resolved", forced
    authority = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        forced_continuation=forced,
        predictive_mechanics=predictive,
    )
    assert authority["status"] == "resolved", authority
    contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=authority,
        side="self",
    )
    assert contract["status"] == "resolved", contract
    modifier = contract["solar_terminal_weather_damage_modifier_authority"]
    assert modifier["terminal_weather"]["value"] == turn_two_weather
    assert modifier["modifier_q12"] == expected_q12


def _pair_case(move_id, *, weather, item=None, item_status="known_absent", own_hp=100, order="own_first"):
    state = _with_terminal_mechanics_facts(_complete_state(_pair_state()))
    field = state["field"]
    field["weather"] = weather
    field["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    actor_raw = state["self_side"]["pokemon"][0]
    actor_raw["known_item"] = item
    actor_raw["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": item_status}
    actor_raw["current_hp"] = own_hp
    actor_raw["max_hp"] = 100
    actor_raw["fainted"] = own_hp == 0
    snapshot = _pair_snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    action = _own_action(d0, d0["active_owners"]["self"], move_id)
    opponent = _opponent_action(d0, "tackle")
    return state, snapshot, d0, action, opponent, _order(d0, action, opponent, order)


@pytest.mark.parametrize("move_id", SOLAR)
def test_sunny_solar_enters_immediate_pair_without_charge_continuation(move_id):
    _state0, snapshot, d0, action, opponent, order = _pair_case(move_id, weather="sun")
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=action,
        opponent_action=opponent,
        action_order_authority=order,
    )
    assert pair["status"] == "evaluable", (pair.get("status"), pair.get("reason"))
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    first = [branch["first_action_leaf"] for branch in pair["terminal_branches"]]
    assert first
    assert all("detached_standard_charge_lifecycle_context" not in leaf["consequences"] for leaf in first)
    assert all("power_herb_consumption" not in leaf["consequences"] for leaf in first)


def test_solar_second_action_ko_cancellation_never_consumes_power_herb():
    _state0, snapshot, d0, action, opponent, order = _pair_case(
        "solar-beam", weather="rain", item="power-herb", item_status="known", own_hp=1, order="opponent_first",
    )
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=action,
        opponent_action=opponent,
        action_order_authority=order,
    )
    assert pair["status"] == "evaluable", (pair.get("status"), pair.get("reason"))
    cancelled = [
        branch for branch in pair["terminal_branches"]
        if isinstance(branch.get("second_action"), dict)
        and branch["second_action"].get("state") == "cancelled_due_to_faint"
    ]
    assert cancelled, pair
    for branch in cancelled:
        assert "leaf" not in branch["second_action"]
        assert "detached_standard_charge_lifecycle_context" not in branch["first_action_leaf"].get("consequences", {})
        assert "power_herb_consumption" not in branch["first_action_leaf"].get("consequences", {})


def test_power_herb_suppression_follows_weather_result():
    for weather, expected in (("rain", "charge_start_ready"), ("sun", "weather_charge_skip_ready")):
        _state0, snapshot, d0, actor, target, action = _state_case(
            "solar-beam", weather=weather, item="power-herb", item_status="known", magic_room="active",
        )
        readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        )
        assert readiness["status"] == "resolved", readiness
        assert readiness["outcome"] == expected
        assert readiness["power_herb_applicability_state"]["status"] == "suppressed"


def test_sunny_skip_pre_action_faint_cancels_without_continuation_or_item_consumption():
    state, _snapshot0, _d00 = _ready()
    field = state["field"]
    field["weather"] = "sun"
    field["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    actor_raw = state["self_side"]["pokemon"][0]
    actor_raw["current_hp"] = 0
    actor_raw["fainted"] = True
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, "solar-beam")
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "weather_charge_skip_ready"
    execution = freeze_runtime_d0_solar_weather_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"}, readiness_authority=readiness,
    )
    kernel = execute_runtime_d0_solar_weather_skip(execution_authority=execution)
    assert kernel["status"] == "resolved", kernel
    assert kernel["pre_action_gate"] == {"status": "resolved", "outcome": "cancelled", "reason": "fainted_actor"}
    assert kernel["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    leaf = kernel["terminal_leaves"][0]
    assert "power_herb_consumption" not in leaf["consequences"]
    assert "detached_standard_charge_lifecycle_context" not in leaf["consequences"]


def test_solar_power_herb_pre_action_faint_cancels_without_consumption_or_continuation():
    state, _snapshot0, _d00 = _ready()
    field = state["field"]
    field["weather"] = "rain"
    field["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    actor_raw = state["self_side"]["pokemon"][0]
    actor_raw["known_item"] = "power-herb"
    actor_raw["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"}
    actor_raw["current_hp"] = 0
    actor_raw["fainted"] = True
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, "solar-beam")
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "power_herb_charge_skip_ready"
    execution = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"}, readiness_authority=readiness,
    )
    kernel = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=execution)
    assert kernel["status"] == "resolved", kernel
    assert kernel["pre_action_gate"] == {"status": "resolved", "outcome": "cancelled", "reason": "fainted_actor"}
    leaf = kernel["terminal_leaves"][0]
    assert "power_herb_consumption" not in leaf["consequences"]
    assert "actor_item_after" not in leaf["consequences"]
    assert "detached_standard_charge_lifecycle_context" not in leaf["consequences"]


@pytest.mark.parametrize(("survival_kind", "target_ability", "target_item"), (
    ("sturdy_survival", "sturdy", None),
    ("focus_sash_survival", "pressure", "focus-sash"),
))
def test_sunny_solar_reuses_exact_target_survival_supports(survival_kind, target_ability, target_item):
    state, _snapshot0, _d00 = _ready()
    state["field"]["weather"] = "sun"
    state["field"]["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    target_raw = state["opponent_side"]["pokemon"][0]
    target_raw["current_hp"] = 100
    target_raw["max_hp"] = 100
    target_raw["fainted"] = False
    target_raw["current_final_stats"]["special-defense"]["value"] = 1
    target_raw["current_ability"] = target_ability
    target_raw["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    if target_ability == "sturdy":
        state["ability_applicability_context"] = build_ability_applicability_context(
            session_id=state["session_id"],
            source={"side": "opponent", "slot_index": 0, "pokemon_id": target_raw["pokemon_id"]},
            ability_id="sturdy",
            status="applicable",
        )
    target_raw["known_item"] = target_item
    target_raw["known_item_provenance"] = {
        "event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1,
        "status": "known" if target_item else "known_absent",
    }
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, "solar-beam")
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    execution = freeze_runtime_d0_solar_weather_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"}, readiness_authority=readiness,
    )
    assert execution["status"] == "resolved", execution
    kernel = execute_runtime_d0_solar_weather_skip(execution_authority=execution)
    assert kernel["status"] == "resolved", kernel
    applied = [
        leaf for leaf in kernel["terminal_leaves"]
        if isinstance(leaf["consequences"].get(survival_kind), dict)
        and leaf["consequences"][survival_kind].get("outcome") in {"applied", "activated"}
    ]
    assert applied
    assert all(leaf["consequences"]["target_final_hp"] == 1 for leaf in applied)


def test_solar_weather_skip_and_modifier_tampering_fail_closed():
    _state0, snapshot, d0, actor, target, action = _state_case("solar-beam", weather="sun")
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    authority = freeze_runtime_d0_solar_weather_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"}, readiness_authority=readiness,
    )
    assert authority["status"] == "resolved", authority

    for key in ("session_id", "source_runtime_fingerprint", "actor", "target", "action_id", "move_id", "readiness_authority", "weather_decision_authority", "terminal_mechanics_authority", "execution_mode"):
        forged = deepcopy(authority)
        forged[key] = {"tampered": True}
        assert execute_runtime_d0_solar_weather_skip(execution_authority=forged)["status"] == "rejected", key

    forged_weather = deepcopy(authority)
    forged_weather["weather_decision_authority"]["weather"]["value"] = "rain"
    assert execute_runtime_d0_solar_weather_skip(execution_authority=forged_weather)["status"] == "rejected"

    contract = materialize_runtime_d0_solar_weather_skip_terminal_execution_contract(execution_authority=authority)
    assert contract["status"] == "resolved", contract
    forged_modifier = deepcopy(contract)
    forged_modifier["solar_terminal_weather_damage_modifier_authority"]["modifier_q12"] = 2048
    assert validate_standard_charge_terminal_execution_contract(forged_modifier) is not None
    assert execute_standard_charge_terminal_attack(execution_contract=forged_modifier)["status"] == "rejected"


@pytest.mark.parametrize("move_id", SOLAR)
def test_generic_direct_damage_guard_still_blocks_solar(move_id):
    _state0, snapshot, d0, actor, target, _action = _state_case(move_id, weather="sun")
    result = build_runtime_d0_native_damage_context(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        attacker=actor,
        target=target,
        move_metadata=resolve_canonical_standard_charge_turn_two_effect(move_id)["move"],
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "two_turn_execution_unrepresented"
