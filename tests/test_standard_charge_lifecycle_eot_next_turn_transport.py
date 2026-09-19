from __future__ import annotations

from copy import deepcopy

import pytest

from llm.advisor_detached_end_of_turn_post_action_branch_authority import (
    materialize_detached_end_of_turn_post_action_branch_authority,
)
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_exact_eot_post_action_lifecycle_coordinator import (
    coordinate_exact_eot_post_action_lifecycle,
)
from llm.advisor_exact_immediate_pair_to_eot_phase_input import (
    SCHEMA_VERSION as TERMINAL_ACTIVE_SCHEMA,
    materialize_exact_immediate_pair_to_eot_phase_input,
)
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_post_eot_replacement_transition import (
    advance_post_eot_entry,
    freeze_post_eot_transition,
    freeze_replacement_intent,
    post_eot_entry_binding,
    post_eot_source_binding,
    prepare_post_eot_replacements,
)
from llm.advisor_standard_charge_lifecycle_transport import (
    NEXT_TURN_SCHEMA_VERSION,
    POST_EOT_SCHEMA_VERSION,
    TRANSPORT_SCHEMA_VERSION,
    derive_standard_charge_lifecycle_transport_authorities,
    validate_next_turn_standard_charge_continuation_authorities,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state as fp
from tests.test_standard_charge_start_immediate_pair_integration import _case


SIDES = ("self", "opponent")


def _ledger_case(
    *,
    own_move="sky-attack",
    opponent_move="tackle",
    order="own_first",
    own_hp=100,
    opponent_hp=100,
    terminal_predicate=None,
):
    *_prefix, pair = _case(
        own_move=own_move,
        opponent_move=opponent_move,
        order=order,
        own_hp=own_hp,
        opponent_hp=opponent_hp,
    )
    assert pair["status"] == "evaluable", pair
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger
    leaves = list(ledger["terminal_leaves"])
    if terminal_predicate is not None:
        leaves = [leaf for leaf in leaves if terminal_predicate(leaf)]
    assert leaves
    return ledger, leaves[0]


def _binding(ledger, owner):
    return {
        "session_id": ledger["session_id"],
        "source_runtime_fingerprint": ledger["source_runtime_fingerprint"],
        "source_branch_fingerprint": ledger["source_branch_fingerprint"],
        "owner": deepcopy(owner),
    }


def _terminal_authorities(
    ledger,
    leaf,
    *,
    conditions=None,
    toxic_stages=None,
    abilities=None,
    types=None,
    speeds=None,
):
    conditions = conditions or {}
    toxic_stages = toxic_stages or {}
    abilities = abilities or {}
    types = types or {}
    speeds = speeds or {"self": 100, "opponent": 90}
    rows = {}
    for side, hp_key, actor_key in (
        ("self", "own_final_hp", "own_actor"),
        ("opponent", "opponent_final_hp", "opponent_actor"),
    ):
        owner = deepcopy(ledger[actor_key])
        hp = leaf["final_consequences"][hp_key]
        binding = _binding(ledger, owner)
        condition = conditions.get(side)
        row = {
            "status": "resolved",
            "schema_version": TERMINAL_ACTIVE_SCHEMA,
            "pair_id": ledger["pair_id"],
            "session_id": ledger["session_id"],
            "source_runtime_fingerprint": ledger["source_runtime_fingerprint"],
            "source_branch_fingerprint": ledger["source_branch_fingerprint"],
            "decision_owner": deepcopy(ledger["decision_owner"]),
            "terminal_leaf_id": leaf["pair_leaf_id"],
            "owner": owner,
            "maximum_hp": 100,
            "condition": (
                {"status": "known_none", "source_binding": deepcopy(binding)}
                if condition is None
                else {
                    "status": "known_present",
                    "condition": condition,
                    "source_binding": deepcopy(binding),
                }
            ),
            "item": {"status": "known_absent", "source_binding": deepcopy(binding)},
            "toxic_progression": (
                {
                    "status": "known",
                    "next_stage": toxic_stages[side],
                    "source_binding": deepcopy(binding),
                }
                if side in toxic_stages
                else {"status": "unknown", "source_binding": deepcopy(binding)}
            ),
            "speed": {
                "status": "known",
                "value": speeds[side],
                "source_binding": deepcopy(binding),
            },
            "ability": {
                "status": "known",
                "value": abilities.get(side, "pressure"),
                "source_binding": deepcopy(binding),
            },
            "persistent_effects": {
                effect: {"status": "known_inactive", "source_binding": deepcopy(binding)}
                for effect in ("aqua_ring", "ingrain")
            },
            "types": {
                "status": "known",
                "value": types.get(side, ["normal"]),
                "source_binding": deepcopy(binding),
            },
        }
        rows[side] = row
    return rows


def _weather(ledger, kind):
    return {
        "status": "known",
        "weather": kind,
        "source_binding": {
            "session_id": ledger["session_id"],
            "source_runtime_fingerprint": ledger["source_runtime_fingerprint"],
            "source_branch_fingerprint": ledger["source_branch_fingerprint"],
        },
    }


def _hazards(ledger, leaf):
    rows = {}
    for side in SIDES:
        rows[side] = {
            "status": "resolved",
            "schema_version": "detached-exact-pair-terminal-switch-hazard-authority-v1",
            "source_binding": {
                "session_id": ledger["session_id"],
                "pair_id": ledger["pair_id"],
                "source_runtime_fingerprint": ledger["source_runtime_fingerprint"],
                "source_branch_fingerprint": ledger["source_branch_fingerprint"],
                "decision_owner": deepcopy(ledger["decision_owner"]),
                "terminal_leaf_id": leaf["pair_leaf_id"],
                "affected_side": side,
            },
            "path_outcome": "no_hazard_change",
            "hazards": {
                "schema_version": "switch-hazard-context-v2",
                "session_id": ledger["session_id"],
                "affected_side": side,
                "stealth_rock": "absent",
                "spikes_layers": 0,
                "toxic_spikes_layers": 0,
                "sticky_web": "absent",
            },
        }
    return rows


def _phase(
    ledger,
    leaf,
    *,
    authorities=None,
    weather=None,
    hazards=None,
):
    return materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=authorities or _terminal_authorities(ledger, leaf),
        weather_authority=weather,
        switch_hazard_authorities=hazards,
    )


def _post_branch(eot):
    return materialize_detached_end_of_turn_post_action_branch_authority(
        eot_ledger=eot,
        source_eot_fingerprint=fp(eot),
    )


def _handoff(branch):
    return handoff_end_of_turn_to_next_turn_start(
        end_of_turn_branch={
            "status": "resolved",
            "boundary": {"phase": "end_of_turn"},
            "next_state": deepcopy(branch["state"]),
            "resulting_branch_fingerprint": branch["state_fingerprint"],
        }
    )


def _owner(session, side, slot, pokemon_id):
    return {
        "session_id": session,
        "side": side,
        "slot_index": slot,
        "pokemon_id": pokemon_id,
    }


def _incoming_current(session, side, owner, hp, ability="pressure"):
    return {
        "current_state_session_id": session,
        "current_hp_context": {
            "current_hp": [
                {"side": side, "current_hp": hp, "maximum_hp": 100},
            ]
        },
        "condition_context": {
            "current_conditions": [
                {
                    "side": side,
                    "condition_type": "none",
                    "status": "user_confirmed",
                    "source": "user_confirmed_current_condition",
                }
            ]
        },
        "ability_context": {
            "current_abilities": [
                {
                    "side": side,
                    "ability": ability,
                    "status": "user_confirmed",
                    "source": "user_confirmed_current_ability",
                }
            ]
        },
        "stat_stage_context": {
            "current_stages": [
                {
                    "side": side,
                    "stat": stat,
                    "stage": 0,
                    "status": "user_confirmed",
                    "source": "user_confirmed_current_stat_stage",
                    "confidence": "known",
                }
                for stat in (
                    "attack",
                    "defense",
                    "special-attack",
                    "special-defense",
                    "speed",
                )
            ]
        },
        "field_state_context": {"current_field": {"weather": "none", "side_effects": []}},
    }


def _bench_member(session, side, *, slot=1, hp=80, speed=100):
    owner = _owner(session, side, slot, f"{side}-bench-{slot}")
    hp_authority = {"status": "known", "current_hp": hp, "maximum_hp": 100}
    incoming = {
        "owner": deepcopy(owner),
        "hp_authority": deepcopy(hp_authority),
        "fainted_authority": {"status": "known", "value": False},
        "provenance": "identity_bound_incoming_current_state_v1",
        "current_state": _incoming_current(session, side, owner, hp),
    }
    mechanics = {
        **deepcopy(owner),
        "hp_authority": deepcopy(hp_authority),
        "item_authority": {"status": "known", "value": None},
        "ability_authority": {"status": "known", "value": "pressure"},
        "current_type_authority": {"status": "known", "value": ["normal"]},
        "prospective_groundedness_authority": {"status": "grounded"},
        "persistent_condition_authority": {"status": "known", "value": "none"},
        "prospective_entry_interactions_authority": {
            "toxic_spikes": "applicable",
            "sticky_web": "applicable",
        },
        "prospective_speed_stage_authority": {"status": "known", "value": 0},
        "prospective_offensive_stages_authority": {
            "attack": 0,
            "special-attack": 0,
        },
    }
    return {
        "owner": owner,
        "hp": hp_authority,
        "eligible": {"status": "known", "value": True},
        "incoming_authority": incoming,
        "entry_mechanics": mechanics,
        "entry_speed": {"status": "known", "value": speed},
    }


def _teams(eot, *, bench_sides=()):
    binding = post_eot_source_binding(eot)
    session = eot["session_id"]
    teams = {}
    for side in SIDES:
        final = eot["post_end_of_turn_active_states"][side]
        members = [
            {
                "owner": deepcopy(final["owner"]),
                "hp": {
                    "status": "known",
                    "current_hp": final["current_hp"],
                    "maximum_hp": final["maximum_hp"],
                },
                "eligible": {"status": "known", "value": True},
            }
        ]
        if side in bench_sides:
            members.append(
                _bench_member(
                    session,
                    side,
                    speed=90 if side == "self" else 110,
                )
            )
        teams[side] = {
            "status": "known",
            "source_binding": deepcopy(binding),
            "side": side,
            "completeness": "complete",
            "members": members,
        }
    return teams


def _entry_authority(cursor):
    phase, side = cursor["entry_queue"][0]
    target = deepcopy(cursor["entrants"][side]["entry_mechanics"])
    active = cursor["state"]["active"][side]
    target["hp_authority"] = {
        "status": "known",
        "current_hp": active["current_hp"],
        "maximum_hp": active["max_hp"],
    }
    stages = {
        row["stat"]: row["stage"]
        for row in cursor["state"]["current_state"]["stat_stage_context"]["current_stages"]
        if row["side"] == side
    }
    target["prospective_speed_stage_authority"] = {
        "status": "known",
        "value": stages["speed"],
    }
    target["prospective_offensive_stages_authority"] = {
        stat: stages[stat] for stat in ("attack", "special-attack")
    }
    condition = next(
        row["condition_type"]
        for row in cursor["state"]["current_state"]["condition_context"]["current_conditions"]
        if row["side"] == side
    )
    target["persistent_condition_authority"] = {"status": "known", "value": condition}
    return {
        "source_binding": post_eot_entry_binding(cursor),
        "mechanics": {
            "target_roster_mechanics": target,
            "hazards": deepcopy(cursor["state"]["post_eot_hazard_authorities"][side]),
            "field_state_context": deepcopy(
                cursor["state"]["current_state"]["field_state_context"]
            ),
            "intimidate_authority": None,
            "download_authority": None,
        },
    }


def _finish_replacements(eot, branch, *, bench_sides):
    transition = freeze_post_eot_transition(
        eot_ledger=eot,
        source_eot_fingerprint=fp(eot),
        branch_authority=branch,
        team_authorities=_teams(eot, bench_sides=bench_sides),
    )
    assert transition["status"] in {"replacement_required", "next_decision_ready"}, transition
    if transition["status"] == "next_decision_ready":
        return transition
    intents = {
        side: freeze_replacement_intent(
            transition=transition,
            side=side,
            incoming_owner=request["candidates"][0],
        )
        for side, request in transition["requirements"].items()
        if request["state"] == "replacement_required"
    }
    cursor = prepare_post_eot_replacements(
        transition=transition,
        intents=intents,
    )
    assert cursor["status"] == "entry_pending", cursor
    while cursor["status"] == "entry_pending":
        cursor = advance_post_eot_entry(
            transition=cursor,
            entry_authority=_entry_authority(cursor),
        )
    return cursor


@pytest.mark.parametrize(
    "own_move,opponent_move,order,side",
    [
        ("sky-attack", "tackle", "own_first", "self"),
        ("freeze-shock", "tackle", "opponent_first", "self"),
        ("tackle", "sky-attack", "opponent_first", "opponent"),
        ("tackle", "ice-burn", "own_first", "opponent"),
    ],
)
def test_surviving_charge_first_or_second_derives_exact_pair_terminal_transport(
    own_move, opponent_move, order, side
):
    ledger, leaf = _ledger_case(
        own_move=own_move,
        opponent_move=opponent_move,
        order=order,
    )
    phase = _phase(ledger, leaf)
    assert phase["status"] == "resolved", phase
    rows = phase["standard_charge_lifecycle_authorities"]
    assert rows[side]["status"] == "known_present"
    assert rows[side]["schema_version"] == TRANSPORT_SCHEMA_VERSION
    other = "opponent" if side == "self" else "self"
    assert rows[other]["status"] == "known_none"
    locator = rows[side]["continuation_target_locator"]
    assert set(locator) == {"session_id", "side", "slot_index"}
    assert "pokemon_id" not in locator


def test_charge_vs_charge_transports_both_and_ordinary_pair_transports_explicit_none():
    ledger, leaf = _ledger_case(
        own_move="razor-wind",
        opponent_move="ice-burn",
        order="own_first",
    )
    phase = _phase(ledger, leaf)
    assert all(
        phase["standard_charge_lifecycle_authorities"][side]["status"] == "known_present"
        for side in SIDES
    )

    ordinary, ordinary_leaf = _ledger_case(
        own_move="tackle",
        opponent_move="tackle",
        order="own_first",
    )
    ordinary_phase = _phase(ordinary, ordinary_leaf)
    assert all(
        ordinary_phase["standard_charge_lifecycle_authorities"][side]["status"] == "known_none"
        for side in SIDES
    )


def test_cancelled_second_charge_is_none_and_same_turn_ko_after_first_charge_retires_before_eot():
    cancelled, cancelled_leaf = _ledger_case(
        own_move="tackle",
        opponent_move="sky-attack",
        order="own_first",
        opponent_hp=1,
        terminal_predicate=lambda leaf: leaf["second_action"]["state"] == "cancelled_due_to_faint",
    )
    rows = _phase(cancelled, cancelled_leaf)["standard_charge_lifecycle_authorities"]
    assert rows["opponent"]["status"] == "known_none"
    assert rows["opponent"]["reason"] == "no_executed_standard_charge_start"

    ko, ko_leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
        own_hp=1,
        terminal_predicate=lambda leaf: leaf["final_consequences"]["own_final_hp"] == 0,
    )
    ko_rows = _phase(ko, ko_leaf)["standard_charge_lifecycle_authorities"]
    assert ko_rows["self"]["status"] == "known_none"
    assert ko_rows["self"]["reason"] == "charger_fainted_before_eot"


def test_pair_terminal_tamper_and_eot_transport_tamper_fail_closed():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    forged = deepcopy(ledger)
    source_leaf = forged["terminal_leaves"][0]["source_pair_branch"]["first_action_leaf"]
    source_leaf["consequences"]["detached_standard_charge_lifecycle_context"][
        "continuation_target_locator"
    ]["pokemon_id"] = "forged-target"
    assert _phase(forged, forged["terminal_leaves"][0])["status"] == "rejected"

    phase = _phase(ledger, leaf)
    tampered = deepcopy(phase)
    tampered["standard_charge_lifecycle_authorities"]["self"]["move_id"] = "razor-wind"
    assert materialize_end_of_turn_residual_phase(phase_input=tampered)["status"] == "rejected"


def test_eot_preserves_transport_without_charge_event_or_probability_branch():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    phase = _phase(ledger, leaf)
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["status"] == "evaluable", eot
    assert eot["phase_input"]["standard_charge_lifecycle_authorities"] == phase[
        "standard_charge_lifecycle_authorities"
    ]
    assert not [event for event in eot["events"] if "charge" in event["event_kind"]]
    assert phase["terminal_probability_mass"] == ledger["terminal_probability_mass"]


@pytest.mark.parametrize(
    "condition,toxic_stage",
    [("burn", None), ("poison", None), ("toxic", 1)],
)
def test_residual_condition_ko_retires_charge(condition, toxic_stage):
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=1,
    )
    authorities = _terminal_authorities(
        ledger,
        leaf,
        conditions={"self": condition},
        toxic_stages={"self": toxic_stage} if toxic_stage is not None else {},
    )
    phase = _phase(ledger, leaf, authorities=authorities)
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["status"] == "evaluable", eot
    assert eot["post_end_of_turn_active_states"]["self"]["fainted"] is True
    branch = _post_branch(eot)
    row = branch["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"]
    assert row["status"] == "known_none"
    assert row["reason"] == "charger_fainted_during_eot"


def test_sandstorm_ko_retires_charge_without_new_charge_rng():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=1,
    )
    authorities = _terminal_authorities(
        ledger,
        leaf,
        types={"self": ["normal"], "opponent": ["rock"]},
    )
    phase = _phase(
        ledger,
        leaf,
        authorities=authorities,
        weather=_weather(ledger, "sandstorm"),
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["status"] == "evaluable", eot
    assert [event["event_kind"] for event in eot["events"]] == ["sandstorm"]
    branch = _post_branch(eot)
    assert branch["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"][
        "reason"
    ] == "charger_fainted_during_eot"


def test_surviving_charger_reaches_next_turn_as_pending_without_execution_grant():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=_phase(ledger, leaf))
    branch = _post_branch(eot)
    row = branch["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"]
    assert row["status"] == "known_present"
    handoff = _handoff(branch)
    assert handoff["status"] == "resolved", handoff
    continuation = handoff["next_turn_standard_charge_continuation_authorities"]["self"]
    assert continuation["schema_version"] == NEXT_TURN_SCHEMA_VERSION
    assert continuation["lifecycle_state"] == "continuation_pending"
    assert continuation["execution_grant"] is False
    assert continuation["target_occupant_resolved"] is False
    assert continuation["selected_action_synthesized"] is False
    assert continuation["forced_action_synthesized"] is False
    assert continuation["damage_execution_synthesized"] is False
    assert continuation["pp_consumption_materialized"] is False
    assert "pokemon_id" not in continuation["continuation_target_locator"]


def test_both_chargers_survive_to_two_next_turn_continuations():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=_phase(ledger, leaf))
    branch = _post_branch(eot)
    handoff = _handoff(branch)
    rows = handoff["next_turn_standard_charge_continuation_authorities"]
    assert all(rows[side]["status"] == "known_present" for side in SIDES)


def test_target_replacement_preserves_surviving_charger_positional_target_only():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        opponent_hp=1,
    )
    authorities = _terminal_authorities(
        ledger,
        leaf,
        conditions={"opponent": "burn"},
    )
    phase = _phase(
        ledger,
        leaf,
        authorities=authorities,
        hazards=_hazards(ledger, leaf),
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["post_end_of_turn_active_states"]["opponent"]["fainted"] is True
    branch = _post_branch(eot)
    old_target = deepcopy(
        branch["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"][
            "source_charge_context"
        ]["source_target_owner"]
    )
    result = _finish_replacements(eot, branch, bench_sides={"opponent"})
    assert result["status"] == "next_decision_ready", result
    incoming = result["state"]["active"]["opponent"]
    assert incoming["pokemon_id"] != old_target["pokemon_id"]
    continuation = result["detached_next_decision_state"][
        "next_turn_standard_charge_continuation_authorities"
    ]["self"]
    assert continuation["status"] == "known_present"
    locator = continuation["continuation_target_locator"]
    assert locator["side"] == "opponent" and locator["slot_index"] == old_target["slot_index"]
    assert "pokemon_id" not in locator
    assert continuation["source_charge_context"]["source_target_owner"] == old_target


def test_charger_replacement_never_inherits_old_charge_but_surviving_other_charger_does():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=1,
    )
    authorities = _terminal_authorities(
        ledger,
        leaf,
        conditions={"self": "burn"},
    )
    phase = _phase(
        ledger,
        leaf,
        authorities=authorities,
        hazards=_hazards(ledger, leaf),
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    branch = _post_branch(eot)
    result = _finish_replacements(eot, branch, bench_sides={"self"})
    assert result["status"] == "next_decision_ready", result
    incoming = result["state"]["active"]["self"]
    rows = result["detached_next_decision_state"][
        "next_turn_standard_charge_continuation_authorities"
    ]
    assert rows["self"]["status"] == "known_none"
    assert rows["self"]["execution_grant"] is False
    assert rows["opponent"]["status"] == "known_present"
    assert rows["opponent"]["charger_owner"] == {
        key: result["state"]["active"]["opponent"][key]
        for key in ("session_id", "side", "slot_index", "pokemon_id")
    }
    assert rows["self"].get("charger_owner") != {
        key: incoming[key] for key in ("session_id", "side", "slot_index", "pokemon_id")
    }


def test_both_chargers_faint_and_replacements_receive_no_active_continuation():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=1,
        opponent_hp=1,
    )
    authorities = _terminal_authorities(
        ledger,
        leaf,
        conditions={"self": "burn", "opponent": "burn"},
        speeds={"self": 100, "opponent": 90},
    )
    phase = _phase(
        ledger,
        leaf,
        authorities=authorities,
        hazards=_hazards(ledger, leaf),
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert all(eot["post_end_of_turn_active_states"][side]["fainted"] for side in SIDES)
    branch = _post_branch(eot)
    result = _finish_replacements(eot, branch, bench_sides=set(SIDES))
    assert result["status"] == "next_decision_ready", result
    rows = result["detached_next_decision_state"][
        "next_turn_standard_charge_continuation_authorities"
    ]
    assert all(rows[side]["status"] == "known_none" for side in SIDES)


def test_post_eot_and_next_turn_tampering_rejects_identity_fingerprints_power_herb_and_pp():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    phase = _phase(ledger, leaf)
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    branch = _post_branch(eot)

    forged_actor = deepcopy(branch)
    forged_actor["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"][
        "charger_owner"
    ]["pokemon_id"] = "replacement-forgery"
    forged_actor["state_fingerprint"] = fp(forged_actor["state"])
    transition = freeze_post_eot_transition(
        eot_ledger=eot,
        source_eot_fingerprint=fp(eot),
        branch_authority=forged_actor,
        team_authorities=_teams(eot),
    )
    assert transition["status"] == "rejected"

    for field, value in (
        ("pp_consumption_materialized", True),
        ("execution_grant", True),
    ):
        forged = deepcopy(branch)
        forged["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"][field] = value
        forged["state_fingerprint"] = fp(forged["state"])
        assert freeze_post_eot_transition(
            eot_ledger=eot,
            source_eot_fingerprint=fp(eot),
            branch_authority=forged,
            team_authorities=_teams(eot),
        )["status"] == "rejected"

    stale = {
        "status": "resolved",
        "boundary": {"phase": "end_of_turn"},
        "next_state": deepcopy(branch["state"]),
        "resulting_branch_fingerprint": "stale",
    }
    assert handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=stale)["status"] == "rejected"

    valid = _handoff(branch)
    next_rows = valid["next_turn_standard_charge_continuation_authorities"]
    assert validate_next_turn_standard_charge_continuation_authorities(
        authorities=next_rows,
        post_eot_authorities=branch["state"][
            "post_eot_standard_charge_lifecycle_authorities"
        ],
        active_states=branch["state"]["active"],
        source_post_eot_fingerprint=branch["state_fingerprint"],
    ) is None
    forged_next = deepcopy(next_rows)
    forged_next["self"]["source_post_eot_fingerprint"] = "foreign"
    assert validate_next_turn_standard_charge_continuation_authorities(
        authorities=forged_next,
        post_eot_authorities=branch["state"][
            "post_eot_standard_charge_lifecycle_authorities"
        ],
        active_states=branch["state"]["active"],
        source_post_eot_fingerprint=branch["state_fingerprint"],
    ) is not None

@pytest.mark.parametrize(
    "mutation",
    ("pair_id", "terminal_leaf_id", "runtime_fingerprint", "branch_fingerprint"),
)
def test_terminal_transport_rejects_forged_pair_envelope_binding(mutation):
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    forged = deepcopy(ledger)
    forged_leaf_id = leaf["pair_leaf_id"]
    if mutation == "pair_id":
        forged["pair_id"] = "forged-pair"
    elif mutation == "terminal_leaf_id":
        forged["terminal_leaves"][0]["pair_leaf_id"] = "forged-terminal"
        forged_leaf_id = "forged-terminal"
    elif mutation == "runtime_fingerprint":
        forged["source_runtime_fingerprint"] = "forged-runtime"
    else:
        forged["source_branch_fingerprint"] = "forged-branch"
    result = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=forged,
        terminal_leaf_id=forged_leaf_id,
        terminal_active_authorities=_terminal_authorities(ledger, leaf),
    )
    assert result["status"] == "rejected"


@pytest.mark.parametrize(
    "mutation",
    (
        "actor",
        "move",
        "action",
        "source_charge_leaf_id",
        "readiness",
        "canonical",
        "locator",
        "power_herb",
        "pp_consumed",
    ),
)
def test_terminal_transport_rejects_forged_charge_source_leaf_semantics(mutation):
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    forged = deepcopy(ledger)
    source_leaf = forged["terminal_leaves"][0]["source_pair_branch"]["first_action_leaf"]
    context = source_leaf["consequences"]["detached_standard_charge_lifecycle_context"]
    if mutation == "actor":
        source_leaf["provenance"]["attacker"]["pokemon_id"] = "forged-actor"
    elif mutation == "move":
        context["move_id"] = "razor-wind"
    elif mutation == "action":
        context["action_id"] = "forged-action"
    elif mutation == "source_charge_leaf_id":
        context["source_charge_start_leaf_id"] = "forged-leaf"
    elif mutation == "readiness":
        context["readiness_authority"]["action_id"] = "forged-readiness"
    elif mutation == "canonical":
        context["canonical_lifecycle_family"] = "weather_sensitive_charge_then_damage"
    elif mutation == "locator":
        context["continuation_target_locator"]["slot_index"] = 7
    elif mutation == "power_herb":
        context["power_herb_applicability_state"]["status"] = "active"
    else:
        context["pp_consumption_materialized"] = True
    phase = _phase(forged, forged["terminal_leaves"][0])
    assert phase["status"] == "rejected"


def test_post_eot_rejects_forged_source_eot_fingerprint_and_retired_reactivation():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=1,
    )
    authorities = _terminal_authorities(
        ledger,
        leaf,
        conditions={"self": "burn"},
    )
    eot = materialize_end_of_turn_residual_phase(
        phase_input=_phase(ledger, leaf, authorities=authorities)
    )
    branch = _post_branch(eot)
    assert branch["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"][
        "status"
    ] == "known_none"

    forged_fp = deepcopy(branch)
    forged_fp["state"]["post_eot_standard_charge_lifecycle_authorities"]["opponent"][
        "source_eot_fingerprint"
    ] = "foreign-eot"
    forged_fp["state_fingerprint"] = fp(forged_fp["state"])
    assert freeze_post_eot_transition(
        eot_ledger=eot,
        source_eot_fingerprint=fp(eot),
        branch_authority=forged_fp,
        team_authorities=_teams(eot),
    )["status"] == "rejected"

    reactivated = deepcopy(branch)
    row = reactivated["state"]["post_eot_standard_charge_lifecycle_authorities"]["self"]
    row["status"] = "known_present"
    row["charger_owner"] = deepcopy(eot["post_end_of_turn_active_states"]["self"]["owner"])
    row["move_id"] = "sky-attack"
    row["action_id"] = "attack:sky-attack"
    row["continuation_target_locator"] = {
        "session_id": ledger["session_id"],
        "side": "opponent",
        "slot_index": ledger["opponent_actor"]["slot_index"],
    }
    row["pp_consumption_materialized"] = False
    reactivated["state_fingerprint"] = fp(reactivated["state"])
    assert freeze_post_eot_transition(
        eot_ledger=eot,
        source_eot_fingerprint=fp(eot),
        branch_authority=reactivated,
        team_authorities=_teams(eot),
    )["status"] == "rejected"


def test_exact_eot_coordinator_exposes_charge_continuation_through_existing_pipeline():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="tackle",
        order="own_first",
    )
    authorities = _terminal_authorities(ledger, leaf)
    phase = _phase(ledger, leaf, authorities=authorities)
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    result = coordinate_exact_eot_post_action_lifecycle(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=authorities,
        team_authorities=_teams(eot),
    )
    assert result["status"] == "next_decision_ready", result
    continuation = result["detached_next_decision_state"][
        "next_turn_standard_charge_continuation_authorities"
    ]["self"]
    assert continuation["status"] == "known_present"
    assert continuation["lifecycle_state"] == "continuation_pending"
    assert continuation["execution_grant"] is False

