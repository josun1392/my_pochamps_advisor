from __future__ import annotations

from copy import deepcopy

import pytest

from llm.advisor_detached_standard_charge_forced_continuation import (
    materialize_detached_standard_charge_forced_continuation,
)
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_exact_immediate_pair_to_eot_phase_input import (
    materialize_exact_immediate_pair_to_eot_phase_input,
)
from llm.advisor_next_turn_predictive_mechanics_authority import (
    NEXT_TURN_SCHEMA_VERSION,
    POST_EOT_SCHEMA_VERSION,
    TERMINAL_SCHEMA_VERSION,
    normalize_terminal_predictive_mechanics_authority,
    validate_forced_continuation_predictive_mechanics_binding,
    validate_next_turn_predictive_mechanics_authority,
    _status_progression_fact,
    _confusion_facts,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state as fp
from tests.test_detached_sitrus_berry_immediate_consumption import (
    _second_action_sitrus_pair,
)
from tests.test_standard_charge_lifecycle_eot_next_turn_transport import (
    _finish_replacements,
    _hazards,
    _ledger_case,
    _phase,
    _post_branch,
    _terminal_authorities,
)


FINAL_STATS = {
    "hp": 100,
    "attack": 120,
    "defense": 110,
    "special-attack": 130,
    "special-defense": 105,
    "speed": 100,
}
STAGES = {
    "attack": 1,
    "defense": -1,
    "special-attack": 2,
    "special-defense": 0,
    "speed": 1,
    "accuracy": -1,
    "evasion": 2,
}


def test_active_progression_requires_exact_observation_binding():
    owner = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "p"}
    observation = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "condition": "sleep", "turn_number": 1}
    progression = {"schema_version": "champions-sleep-freeze-progression-v1", "owner": owner, "condition": "sleep", "origin_id": "sleep-1", "established_turn": 1, "prior_attempts": 0, "sleep_duration": 2, "condition_observation": observation}
    known, error = _status_progression_fact(progression, owner, {"status": "known_present", "condition": "sleep"}, observation)
    assert error is None and known["status"] == "known"
    missing, error = _status_progression_fact(progression, owner, {"status": "known_present", "condition": "sleep"}, None)
    assert error is None and missing["status"] == "unknown"
    bad, error = _status_progression_fact(progression, owner, {"status": "known_present", "condition": "sleep"}, {**observation, "turn_number": 2})
    assert bad == {} and error == "champions_status_progression_condition_observation_mismatch"


def test_confused_progression_requires_exact_observation_binding():
    owner = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "p"}
    observation = {"event_kind": "current_confusion_observed", "trust": "user_confirmed_observation", "state": "confused", "turn_number": 1}
    progression = {"schema_version": "champions-confusion-progression-v1", "owner": owner, "state": "confused", "origin_id": "confusion-1", "established_turn": 1, "prior_opportunities": 0, "duration": 3, "confusion_observation": observation}
    state, known, error = _confusion_facts({"status": "known_confused"}, progression, owner, observation)
    assert error is None and state["status"] == "known_confused" and known["status"] == "known"
    _, missing, error = _confusion_facts({"status": "known_confused"}, progression, owner, None)
    assert error is None and missing["status"] == "unknown"


def _binding(ledger, leaf, owner):
    return {
        "pair_id": ledger["pair_id"],
        "terminal_leaf_id": leaf["pair_leaf_id"],
        "session_id": ledger["session_id"],
        "source_runtime_fingerprint": ledger["source_runtime_fingerprint"],
        "source_branch_fingerprint": ledger["source_branch_fingerprint"],
        "decision_owner": deepcopy(ledger["decision_owner"]),
        "owner": deepcopy(owner),
    }


def _predictive(
    ledger,
    leaf,
    terminal_row,
    *,
    stages=None,
    final_stats=None,
    level=50,
    ability=None,
    item=None,
    condition=None,
    types=None,
    substitute=None,
    crit=None,
    lucky=None,
    field=None,
    side_conditions=None,
    direct=True,
    hp_unknown=False,
    confusion_state=None,
):
    owner = terminal_row["owner"]
    hp = leaf["final_consequences"][
        "own_final_hp" if owner["side"] == "self" else "opponent_final_hp"
    ]
    maximum = terminal_row["maximum_hp"]
    ability = ability if ability is not None else {"status": "known", "value": "pressure"}
    item = item if item is not None else {"status": "known_absent"}
    condition = condition if condition is not None else {"status": "known_none"}
    types = types if types is not None else {"status": "known", "value": ["normal"]}
    stages = deepcopy(STAGES if stages is None else stages)
    final_stats = deepcopy(FINAL_STATS if final_stats is None else final_stats)
    substitute = substitute if substitute is not None else {"status": "known_inactive"}
    crit = crit if crit is not None else {"status": "known", "value": []}
    lucky = lucky if lucky is not None else {"status": "known_inactive"}
    field = field if field is not None else {
        "status": "known",
        "weather": "none",
        "terrain": "electric",
    }
    side_conditions = side_conditions if side_conditions is not None else {
        "status": "known",
        "value": {"reflect": "inactive", "light-screen": "inactive"},
    }
    direct_fact = {"status": "unknown"}
    if direct:
        direct_fact = {
            "status": "known",
            "combatant": {
                "level": level,
                "current_hp": hp,
                "max_hp": maximum,
                "stats": deepcopy(final_stats),
                "boosts": {
                    key: stages[key]
                    for key in (
                        "attack", "defense", "special-attack",
                        "special-defense", "speed",
                    )
                    if key in stages
                },
                "status": None if condition.get("status") == "known_none" else condition.get("condition"),
                "item": item.get("value") if item.get("status") == "known" else None,
                "ability": ability.get("value") if ability.get("status") == "known" else None,
                "types": deepcopy(types.get("value")) if types.get("status") == "known" else None,
            },
        }
    return {
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "source_binding": _binding(ledger, leaf, owner),
        "owner": deepcopy(owner),
        "current_level": {"status": "known", "value": level} if level is not None else {"status": "unknown"},
        "current_final_stats": {
            "status": "known" if set(final_stats) == set(FINAL_STATS) else "incomplete",
            "values": deepcopy(final_stats),
        },
        "current_hp": (
            {"status": "unknown"}
            if hp_unknown
            else {"status": "known", "current_hp": hp, "maximum_hp": maximum}
        ),
        "current_stages": {
            "status": "known" if set(stages) == set(STAGES) else "incomplete",
            "values": deepcopy(stages),
        },
        "condition": deepcopy(condition),
        "item": deepcopy(item),
        "ability": deepcopy(ability),
        "types": deepcopy(types),
        "substitute": deepcopy(substitute),
        "critical_hit_volatiles": deepcopy(crit),
        "lucky_chant": deepcopy(lucky),
        "field": deepcopy(field),
        "side_conditions": deepcopy(side_conditions),
        "direct_mechanics": direct_fact,
        "status_progression": {"status": "not_applicable"},
        "confusion_state": confusion_state if confusion_state is not None else {"status": "known_none"},
        "confusion_progression": {"status": "not_applicable"},
    }


def _rich_terminal_authorities(ledger, leaf, *, self_kwargs=None, opponent_kwargs=None):
    rows = _terminal_authorities(ledger, leaf)
    self_kwargs = self_kwargs or {}
    opponent_kwargs = opponent_kwargs or {}
    rows["self"]["predictive_mechanics"] = _predictive(
        ledger, leaf, rows["self"], **self_kwargs
    )
    rows["opponent"]["predictive_mechanics"] = _predictive(
        ledger, leaf, rows["opponent"], **opponent_kwargs
    )
    return rows


def _rich_flow(
    *,
    own_hp=100,
    opponent_hp=100,
    self_kwargs=None,
    opponent_kwargs=None,
    weather=None,
    conditions=None,
):
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=own_hp,
        opponent_hp=opponent_hp,
    )
    terminal = _terminal_authorities(
        ledger,
        leaf,
        conditions=conditions or {},
    )
    terminal["self"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["self"], **(self_kwargs or {})
    )
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["opponent"], **(opponent_kwargs or {})
    )
    phase = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
        weather_authority=weather,
    )
    return ledger, leaf, terminal, phase


def _next_from_phase(phase):
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["status"] == "evaluable", eot
    branch = _post_branch(eot)
    assert branch["status"] == "known", branch
    handoff = __import__(
        "llm.advisor_next_turn_handoff",
        fromlist=["handoff_end_of_turn_to_next_turn_start"],
    ).handoff_end_of_turn_to_next_turn_start(
        end_of_turn_branch={
            "status": "resolved",
            "boundary": {"phase": "end_of_turn"},
            "next_state": deepcopy(branch["state"]),
            "resulting_branch_fingerprint": branch["state_fingerprint"],
        }
    )
    assert handoff["status"] == "resolved", handoff
    return eot, branch, handoff


def test_survivor_exact_mechanics_crosses_pair_eot_post_eot_and_next_turn():
    ledger, leaf, _, phase = _rich_flow()
    assert phase["status"] == "resolved", phase
    source = phase["active_states"]["self"]["predictive_mechanics"]
    assert source["status"] == "resolved"
    assert source["current_hp"]["current_hp"] == leaf["final_consequences"]["own_final_hp"]
    assert source["current_level"] == {"status": "known", "value": 50}
    assert source["current_final_stats"]["values"] == FINAL_STATS
    assert source["current_stages"]["values"] == STAGES
    assert source["ability"] == {"status": "known", "value": "pressure"}
    assert source["types"] == {"status": "known", "value": ["normal"]}
    assert source["substitute"]["status"] == "known_inactive"
    assert source["critical_hit_volatiles"] == {"status": "known", "value": []}
    assert source["lucky_chant"]["status"] == "known_inactive"
    assert source["field"]["terrain"] == "electric"
    assert source["side_conditions"]["status"] == "known"

    eot, branch, handoff = _next_from_phase(phase)
    post = branch["state"]["post_eot_predictive_mechanics_authorities"]["self"]
    assert post["schema_version"] == POST_EOT_SCHEMA_VERSION
    assert post["status"] == "resolved"
    current = branch["state"]["current_state"]
    assert len([
        x for x in current["stat_stage_context"]["current_stages"]
        if x["side"] == "self"
    ]) == 7
    assert next(
        x for x in current["trusted_level_context"]["current_levels"]
        if x["side"] == "self"
    )["value"] == 50
    assert current["field_state_context"]["current_field"]["terrain"] == "electric"
    next_auth = handoff["next_turn_predictive_mechanics_authority"]
    assert next_auth["schema_version"] == NEXT_TURN_SCHEMA_VERSION
    assert next_auth["status"] == "resolved"
    assert next_auth["source_next_decision_fingerprint"] == handoff["resulting_branch_fingerprint"]
    assert next_auth["sides"]["self"]["owner"] == ledger["own_actor"]
    assert eot["phase_input"]["active_states"]["self"]["predictive_mechanics"] == source


def test_terminal_hp_is_authoritative_and_stale_known_hp_rejects():
    ledger, leaf, _, phase = _rich_flow(
        own_hp=73,
        self_kwargs={"hp_unknown": True},
    )
    assert phase["status"] == "resolved", phase
    normalized = phase["active_states"]["self"]["predictive_mechanics"]
    assert normalized["current_hp"] == {
        "status": "known",
        "current_hp": 73,
        "maximum_hp": 100,
        "source_terminal_leaf_id": leaf["pair_leaf_id"],
        "provenance": "exact_pair_terminal_hp",
    }

    rows = _terminal_authorities(ledger, leaf)
    source = _predictive(ledger, leaf, rows["self"])
    source["current_hp"]["current_hp"] = 74
    rows["self"]["predictive_mechanics"] = source
    rejected = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=rows,
    )
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "terminal_predictive_mechanics_hp_contradiction"


def test_eot_hp_change_updates_predictive_and_direct_mechanics_hp():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=80,
    )
    terminal = _terminal_authorities(ledger, leaf)
    binding = terminal["self"]["item"]["source_binding"]
    terminal["self"]["item"] = {
        "status": "known",
        "value": "leftovers",
        "source_binding": deepcopy(binding),
    }
    terminal["self"]["predictive_mechanics"] = _predictive(
        ledger,
        leaf,
        terminal["self"],
        item={"status": "known", "value": "leftovers"},
    )
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["opponent"]
    )
    phase = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
    )
    assert phase["status"] == "resolved", phase
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["status"] == "evaluable", eot
    assert eot["post_end_of_turn_active_states"]["self"]["current_hp"] == 86
    branch = _post_branch(eot)
    row = branch["state"]["post_eot_predictive_mechanics_authorities"]["self"]
    assert row["current_hp"]["current_hp"] == 86
    assert row["direct_mechanics"]["combatant"]["current_hp"] == 86
    assert branch["state"]["current_state"]["direct_mechanics_context"]["attacker"]["current_hp"] == 86


def test_path_local_condition_must_agree_with_predictive_source():
    ledger, leaf = _ledger_case(
        own_move="thunderbolt",
        opponent_move="sky-attack",
        order="own_first",
        terminal_predicate=lambda x: any(
            isinstance(action, dict)
            and isinstance(action.get("consequences"), dict)
            and isinstance(action["consequences"].get("secondary"), dict)
            and isinstance(
                action["consequences"]["secondary"].get("hypothetical_target_condition"),
                dict,
            )
            for action in (
                x["source_pair_branch"].get("first_action_leaf"),
                x["source_pair_branch"].get("second_action", {}).get("leaf"),
            )
        ),
    )
    terminal = _terminal_authorities(ledger, leaf)
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger,
        leaf,
        terminal["opponent"],
        condition={"status": "known_present", "condition": "paralysis"},
    )
    ok = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
    )
    assert ok["status"] == "resolved", ok.get("reason", ok)
    assert ok["active_states"]["opponent"]["condition"]["condition"] == "paralysis"

    bad_terminal = _terminal_authorities(ledger, leaf)
    bad_terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger,
        leaf,
        bad_terminal["opponent"],
        condition={"status": "known_none"},
    )
    bad = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=bad_terminal,
    )
    assert bad["status"] == "rejected"
    assert bad["reason"] == "terminal_predictive_mechanics_condition_contradiction"


def _sitrus_ledger():
    pair = _second_action_sitrus_pair()
    assert pair["status"] == "evaluable", pair
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger
    leaves = [
        leaf for leaf in ledger["terminal_leaves"]
        if any(
            isinstance(action, dict)
            and isinstance(action.get("consequences"), dict)
            and action["consequences"].get(
                "sitrus_berry_immediate_consumption", {}
            ).get("outcome") == "activated"
            for action in (
                leaf["source_pair_branch"].get("first_action_leaf"),
                leaf["source_pair_branch"].get("second_action", {}).get("leaf"),
            )
        )
    ]
    assert leaves
    return ledger, leaves[0]


def test_path_local_sitrus_consumption_prevents_stale_item_restoration():
    ledger, leaf = _sitrus_ledger()
    terminal = _terminal_authorities(ledger, leaf)
    binding = terminal["opponent"]["item"]["source_binding"]
    terminal["opponent"]["item"] = {
        "status": "known",
        "value": "sitrus-berry",
        "source_binding": deepcopy(binding),
    }
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger,
        leaf,
        terminal["opponent"],
        item={"status": "known_absent"},
    )
    ok = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
    )
    assert ok["status"] == "resolved", ok.get("reason", ok)
    assert ok["active_states"]["opponent"]["item"]["status"] == "known_absent"
    assert ok["active_states"]["opponent"]["predictive_mechanics"]["item"]["status"] == "known_absent"

    stale = deepcopy(terminal)
    stale["opponent"]["predictive_mechanics"]["item"] = {
        "status": "known",
        "value": "sitrus-berry",
    }
    rejected = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=stale,
    )
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "terminal_predictive_mechanics_item_contradiction"


@pytest.mark.parametrize(
    "field,expected_reason",
    [
        ("missing_stage", "stage_evasion_unknown"),
        ("missing_final_stat", "final_stat_special-defense_unknown"),
    ],
)
def test_missing_stage_or_final_stat_remains_incomplete_not_defaulted(field, expected_reason):
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
    )
    terminal = _terminal_authorities(ledger, leaf)
    kwargs = {}
    if field == "missing_stage":
        stages = deepcopy(STAGES)
        stages.pop("evasion")
        kwargs["stages"] = stages
    else:
        stats = deepcopy(FINAL_STATS)
        stats.pop("special-defense")
        kwargs["final_stats"] = stats
    terminal["self"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["self"], **kwargs
    )
    phase = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
    )
    assert phase["status"] == "resolved", phase
    row = phase["active_states"]["self"]["predictive_mechanics"]
    assert row["status"] == "incomplete"
    assert expected_reason in row["incomplete_reasons"]
    if field == "missing_stage":
        assert "evasion" not in row["current_stages"]["values"]
    else:
        assert "special-defense" not in row["current_final_stats"]["values"]


@pytest.mark.parametrize(
    "field,reason",
    [
        ("ability", "ability_unknown"),
        ("item", "item_unknown"),
        ("types", "types_unknown"),
    ],
)
def test_unknown_identity_fact_remains_unknown_when_terminal_source_is_also_unknown(field, reason):
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
    )
    terminal = _terminal_authorities(ledger, leaf)
    source = _predictive(ledger, leaf, terminal["self"], direct=False)
    source[field] = {"status": "unknown"}
    resolved = {
        "owner": deepcopy(terminal["self"]["owner"]),
        "hp": {
            "status": "known",
            "current_hp": leaf["final_consequences"]["own_final_hp"],
            "maximum_hp": terminal["self"]["maximum_hp"],
        },
        "condition": deepcopy(terminal["self"]["condition"]),
        "item": deepcopy(terminal["self"]["item"]),
        "ability": deepcopy(terminal["self"]["ability"]),
        "types": deepcopy(terminal["self"]["types"]),
    }
    resolved[field] = {"status": "unknown"}
    normalized = normalize_terminal_predictive_mechanics_authority(
        value=source,
        base={
            "pair_id": ledger["pair_id"],
            "session_id": ledger["session_id"],
            "source_runtime_fingerprint": ledger["source_runtime_fingerprint"],
            "source_branch_fingerprint": ledger["source_branch_fingerprint"],
            "decision_owner": deepcopy(ledger["decision_owner"]),
        },
        terminal_leaf=leaf,
        owner=terminal["self"]["owner"],
        resolved_active=resolved,
    )
    assert normalized["status"] == "incomplete"
    assert normalized[field]["status"] == "unknown"
    assert reason in normalized["incomplete_reasons"]


@pytest.mark.parametrize("mutation", ("owner", "terminal_leaf", "condition", "item"))
def test_terminal_predictive_tamper_rejects(mutation):
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
    )
    terminal = _terminal_authorities(ledger, leaf)
    source = _predictive(ledger, leaf, terminal["self"])
    if mutation == "owner":
        source["owner"]["pokemon_id"] = "forged"
    elif mutation == "terminal_leaf":
        source["source_binding"]["terminal_leaf_id"] = "stale"
    elif mutation == "condition":
        source["condition"] = {"status": "known_present", "condition": "burn"}
    else:
        source["item"] = {"status": "known", "value": "choice-band"}
    terminal["self"]["predictive_mechanics"] = source
    result = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
    )
    assert result["status"] == "rejected"


def test_explicit_terminal_stage_consequence_contradiction_rejects():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
    )
    forged = deepcopy(leaf)
    forged["source_pair_branch"]["first_action_leaf"]["consequences"][
        "deterministic_stage_effect"
    ] = {
        "target": deepcopy(ledger["opponent_actor"]),
        "stat": "defense",
        "pre_stage": 0,
        "actual_delta": -1,
        "post_stage": -1,
    }
    forged_ledger = deepcopy(ledger)
    forged_ledger["terminal_leaves"] = tuple(
        forged if x["pair_leaf_id"] == leaf["pair_leaf_id"] else x
        for x in forged_ledger["terminal_leaves"]
    )
    terminal = _terminal_authorities(forged_ledger, forged)
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        forged_ledger,
        forged,
        terminal["opponent"],
        stages={**STAGES, "defense": 0},
    )
    result = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=forged_ledger,
        terminal_leaf_id=forged["pair_leaf_id"],
        terminal_active_authorities=terminal,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "terminal_predictive_mechanics_stage_contradiction"


def test_residual_ko_retires_predictive_mechanics_for_that_identity():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=1,
    )
    terminal = _terminal_authorities(
        ledger,
        leaf,
        conditions={"self": "burn"},
    )
    terminal["self"]["predictive_mechanics"] = _predictive(
        ledger,
        leaf,
        terminal["self"],
        condition={"status": "known_present", "condition": "burn"},
    )
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["opponent"]
    )
    phase = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["post_end_of_turn_active_states"]["self"]["fainted"] is True
    branch = _post_branch(eot)
    self_row = branch["state"]["post_eot_predictive_mechanics_authorities"]["self"]
    opponent_row = branch["state"]["post_eot_predictive_mechanics_authorities"]["opponent"]
    assert self_row["retired"] is True
    assert self_row["status"] == "incomplete"
    assert opponent_row["status"] == "resolved"


def test_replacement_does_not_inherit_outgoing_mechanics_and_opponent_survivor_is_unchanged():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        own_hp=1,
    )
    terminal = _terminal_authorities(
        ledger,
        leaf,
        conditions={"self": "burn"},
    )
    terminal["self"]["predictive_mechanics"] = _predictive(
        ledger,
        leaf,
        terminal["self"],
        condition={"status": "known_present", "condition": "burn"},
        ability={"status": "known", "value": "pressure"},
        types={"status": "known", "value": ["normal"]},
        direct=False,
    )
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["opponent"]
    )
    phase = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
        switch_hazard_authorities=_hazards(ledger, leaf),
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    branch = _post_branch(eot)
    old_opponent = deepcopy(
        branch["state"]["post_eot_predictive_mechanics_authorities"]["opponent"]
    )
    result = _finish_replacements(eot, branch, bench_sides={"self"})
    assert result["status"] == "next_decision_ready", result
    authority = result["next_turn_predictive_mechanics_authority"]
    incoming = result["detached_next_decision_state"]["active"]["self"]
    self_row = authority["sides"]["self"]
    assert self_row["owner"] == {
        key: incoming[key]
        for key in ("session_id", "side", "slot_index", "pokemon_id")
    }
    assert self_row["status"] == "incomplete"
    assert self_row["ability"] == {"status": "known", "value": "pressure"}
    assert self_row["condition"] == {"status": "known_none"}
    assert self_row["current_stages"]["values"]["attack"] == 0
    assert self_row["current_stages"]["values"]["speed"] == 0
    assert self_row.get("types") != {"status": "known", "value": ["fire"]}
    assert authority["sides"]["opponent"]["source_post_eot_predictive_mechanics"] == old_opponent


def test_next_turn_fingerprint_and_active_owner_tamper_rejects():
    _, _, _, phase = _rich_flow()
    _, branch, handoff = _next_from_phase(phase)
    assert handoff["next_turn_predictive_mechanics_authority"]["status"] == "resolved"

    stale = deepcopy(branch["state"])
    from llm.advisor_next_turn_predictive_mechanics_authority import (
        materialize_next_turn_predictive_mechanics_authority,
    )
    result = materialize_next_turn_predictive_mechanics_authority(
        next_decision_state=stale,
        next_decision_fingerprint="stale",
        source_post_eot_fingerprint=branch["state_fingerprint"],
    )
    assert result["status"] == "rejected"

    forged = deepcopy(handoff["next_state"])
    forged["active"]["self"]["pokemon_id"] = "forged"
    result = materialize_next_turn_predictive_mechanics_authority(
        next_decision_state=forged,
        next_decision_fingerprint=fp(forged),
        source_post_eot_fingerprint=branch["state_fingerprint"],
    )
    assert result["status"] == "rejected"


def test_self_and_opponent_forced_charge_actions_match_next_turn_predictive_mechanics():
    _, _, _, phase = _rich_flow()
    _, _, handoff = _next_from_phase(phase)
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    )
    assert forced["status"] == "resolved", forced
    predictive = handoff["next_turn_predictive_mechanics_authority"]
    bound = validate_forced_continuation_predictive_mechanics_binding(
        forced_continuation=forced,
        predictive_mechanics=predictive,
        next_decision_state=state,
    )
    assert bound["status"] == "resolved", bound
    assert set(bound["bindings"]) == {"self", "opponent"}
    assert bound["bindings"]["self"]["actor"] == forced["forced_continuation_actions"]["self"]["actor"]
    assert bound["bindings"]["opponent"]["actor"] == forced["forced_continuation_actions"]["opponent"]["actor"]
    assert bound["execution_grant"] is False


def test_replaced_target_binding_uses_incoming_mechanics_not_historical_target():
    ledger, leaf = _ledger_case(
        own_move="sky-attack",
        opponent_move="ice-burn",
        order="own_first",
        opponent_hp=1,
    )
    terminal = _terminal_authorities(
        ledger,
        leaf,
        conditions={"opponent": "burn"},
    )
    terminal["self"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["self"]
    )
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger,
        leaf,
        terminal["opponent"],
        condition={"status": "known_present", "condition": "burn"},
        ability={"status": "known", "value": "pressure"},
    )
    phase = materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger,
        terminal_leaf_id=leaf["pair_leaf_id"],
        terminal_active_authorities=terminal,
        switch_hazard_authorities=_hazards(ledger, leaf),
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    branch = _post_branch(eot)
    historical = deepcopy(ledger["opponent_actor"])
    result = _finish_replacements(eot, branch, bench_sides={"opponent"})
    state = result["detached_next_decision_state"]
    predictive = result["next_turn_predictive_mechanics_authority"]
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state,
        next_decision_fingerprint=result["next_decision_fingerprint"],
    )
    binding = validate_forced_continuation_predictive_mechanics_binding(
        forced_continuation=forced,
        predictive_mechanics=predictive,
        next_decision_state=state,
    )
    assert binding["status"] == "incomplete"
    incoming = state["active"]["opponent"]
    target_row = predictive["sides"]["opponent"]
    assert target_row["owner"]["pokemon_id"] == incoming["pokemon_id"]
    assert target_row["owner"]["pokemon_id"] != historical["pokemon_id"]
    assert target_row.get("source_terminal_predictive_mechanics", {}).get("owner") != historical



def test_forged_next_turn_predictive_mechanics_sidecar_rejects_exact_validation():
    _, _, _, phase = _rich_flow()
    _, _, handoff = _next_from_phase(phase)
    authority = handoff["next_turn_predictive_mechanics_authority"]
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    assert validate_next_turn_predictive_mechanics_authority(
        authority=authority,
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    ) is None
    forged = deepcopy(authority)
    forged["sides"]["self"]["current_final_stats"]["values"]["attack"] += 1
    assert validate_next_turn_predictive_mechanics_authority(
        authority=forged,
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    ) == "next_turn_predictive_mechanics_authority_mismatch"

def test_legacy_terminal_authorities_without_predictive_mechanics_remain_unchanged():
    ledger, leaf = _ledger_case(
        own_move="tackle",
        opponent_move="tackle",
        order="own_first",
    )
    phase = _phase(ledger, leaf)
    assert phase["status"] == "resolved", phase
    assert all(
        "predictive_mechanics" not in phase["active_states"][side]
        for side in ("self", "opponent")
    )
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    branch = _post_branch(eot)
    assert "post_eot_predictive_mechanics_authorities" not in branch["state"]
