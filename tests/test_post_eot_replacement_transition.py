from copy import deepcopy

import pytest

from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_post_eot_replacement_transition import (
    freeze_post_eot_transition, post_eot_source_binding, freeze_replacement_intent,
    prepare_post_eot_replacements, advance_post_eot_entry, post_eot_entry_binding,
    validate_post_eot_transition,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state as fp
from tests.test_end_of_turn_residual_phase import _input, _row, _owner


def _current(owners, hps, abilities=None):
    abilities = abilities or {side: "torrent" for side in owners}
    return {"current_state_session_id": "s",
            "current_hp_context": {"current_hp": [{"side": s, "current_hp": hps[s], "maximum_hp": 100} for s in owners]},
            "condition_context": {"current_conditions": [{"side": s, "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"} for s in owners]},
            "ability_context": {"current_abilities": [{"side": s, "ability": abilities[s], "status": "user_confirmed", "source": "user_confirmed_current_ability"} for s in owners]},
            "stat_stage_context": {"current_stages": [{"side": s, "stat": stat, "stage": 0, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"} for s in owners for stat in ("attack", "defense", "special-attack", "special-defense", "speed")]},
            "field_state_context": {"current_field": {"weather": "none", "side_effects": []}}}


def _hazards(side, rock="absent", spikes=0, toxic=0, sticky="absent"):
    return {"schema_version": "switch-hazard-context-v2", "session_id": "s", "affected_side": side,
            "stealth_rock": rock, "spikes_layers": spikes, "toxic_spikes_layers": toxic, "sticky_web": sticky}


def _member(side, slot=1, hp=80, speed=100, ability="torrent"):
    owner = {**_owner(side, f"{side}-{slot}"), "slot_index": slot}
    hp_authority = {"status": "known", "current_hp": hp, "maximum_hp": 100}
    incoming = {"owner": owner, "hp_authority": hp_authority, "fainted_authority": {"status": "known", "value": hp == 0},
                "provenance": "identity_bound_incoming_current_state_v1", "current_state": _current({side: owner}, {side: hp}, {side: ability})}
    mechanics = {**owner, "hp_authority": hp_authority, "item_authority": {"status": "known", "value": None},
                 "ability_authority": {"status": "known", "value": ability}, "current_type_authority": {"status": "known", "value": ["fire"]},
                 "prospective_groundedness_authority": {"status": "grounded"}, "persistent_condition_authority": {"status": "known", "value": "none"},
                 "prospective_entry_interactions_authority": {"toxic_spikes": "applicable", "sticky_web": "applicable"},
                 "prospective_speed_stage_authority": {"status": "known", "value": 0}, "prospective_offensive_stages_authority": {"attack": 0, "special-attack": 0}}
    return {"owner": owner, "hp": hp_authority, "eligible": {"status": "known", "value": True}, "incoming_authority": incoming,
            "entry_mechanics": mechanics, "entry_speed": {"status": "known", "value": speed}}


def _source(self_hp=0, opponent_hp=50, members=None, hazards=None):
    eot = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=self_hp, opponent_hp=opponent_hp))
    final = eot["post_end_of_turn_active_states"]
    owners = {s: final[s]["owner"] for s in ("self", "opponent")}
    hps = {"self": self_hp, "opponent": opponent_hp}
    state = {"schema_version": "deterministic-transition-preview-v1",
             "active": {s: {**owners[s], "current_hp": hps[s], "max_hp": 100, "fainted": hps[s] == 0} for s in owners},
             "current_state": _current(owners, hps), "post_eot_hazard_authorities": hazards or {s: _hazards(s) for s in owners}}
    binding = post_eot_source_binding(eot)
    branch = {"status": "known", "source_binding": binding, "state": state, "state_fingerprint": fp(state)}
    members = members if members is not None else {"self": [_member("self")], "opponent": [_member("opponent")]}
    teams = {s: {"status": "known", "source_binding": binding, "side": s, "completeness": "complete",
                 "members": [{"owner": owners[s], "hp": {"status": "known", "current_hp": hps[s], "maximum_hp": 100}, "eligible": {"status": "known", "value": True}}, *members.get(s, [])]} for s in owners}
    return dict(eot_ledger=eot, source_eot_fingerprint=fp(eot), branch_authority=branch, team_authorities=teams)


def _prepare(source):
    request = freeze_post_eot_transition(**source)
    intents = {s: freeze_replacement_intent(transition=request, side=s, incoming_owner=r["candidates"][0]) for s, r in request["requirements"].items() if r["state"] == "replacement_required"}
    cursor = prepare_post_eot_replacements(transition=request, intents=intents)
    assert cursor["status"] == "entry_pending", cursor
    return cursor


def _entry(cursor, hazards=None):
    phase, side = cursor["entry_queue"][0]
    target = deepcopy(cursor["entrants"][side]["entry_mechanics"])
    active = cursor["state"]["active"][side]
    target["hp_authority"] = {"status": "known", "current_hp": active["current_hp"], "maximum_hp": active["max_hp"]}
    stages = {r["stat"]: r["stage"] for r in cursor["state"]["current_state"]["stat_stage_context"]["current_stages"] if r["side"] == side}
    target["prospective_speed_stage_authority"] = {"status": "known", "value": stages["speed"]}
    target["prospective_offensive_stages_authority"] = {s: stages[s] for s in ("attack", "special-attack")}
    condition = next(r["condition_type"] for r in cursor["state"]["current_state"]["condition_context"]["current_conditions"] if r["side"] == side)
    target["persistent_condition_authority"] = {"status": "known", "value": condition}
    return {"source_binding": post_eot_entry_binding(cursor), "mechanics": {"target_roster_mechanics": target, "hazards": hazards or deepcopy(cursor["state"]["post_eot_hazard_authorities"][side]),
            "field_state_context": deepcopy(cursor["state"]["current_state"]["field_state_context"]), "intimidate_authority": None, "download_authority": None}}


def _finish(cursor, hazards=None):
    while cursor["status"] == "entry_pending":
        cursor = advance_post_eot_entry(transition=cursor, entry_authority=_entry(cursor, hazards))
    return cursor


@pytest.mark.parametrize("self_hp,opponent_hp", [(50, 50), (0, 50), (50, 0), (0, 0)])
def test_independent_replacement_requirements_and_no_trainer_probabilities(self_hp, opponent_hp):
    source = _source(self_hp, opponent_hp)
    request = freeze_post_eot_transition(**source)
    for side, hp in (("self", self_hp), ("opponent", opponent_hp)):
        assert request["requirements"][side]["state"] == ("replacement_required" if hp == 0 else "no_replacement_needed")
    assert "probability" not in repr(request["requirements"])
    assert validate_post_eot_transition(transition=request)["status"] == "valid"


def test_multiple_choices_are_exposed_without_auto_selection():
    request = freeze_post_eot_transition(**_source(members={"self": [_member("self", 2), _member("self", 1)]}))
    assert [o["slot_index"] for o in request["requirements"]["self"]["candidates"]] == [1, 2]
    assert prepare_post_eot_replacements(transition=request, intents={})["reason"] == "all_required_trainer_intents_needed"


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_complete_no_survivors_is_terminal_but_missing_roster_is_incomplete(side):
    source = _source(self_hp=0 if side == "self" else 50, opponent_hp=0 if side == "opponent" else 50, members={})
    result = freeze_post_eot_transition(**source)
    assert result["status"] == "battle_terminal" and result["battle_terminal"]["unable_to_replace_sides"] == (side,)
    source["team_authorities"].pop(side)
    assert freeze_post_eot_transition(**source)["status"] == "incomplete"


@pytest.mark.parametrize("mutation", ["foreign_eot", "hp", "condition", "team_binding", "incomplete_team", "unknown_member"])
def test_source_and_roster_fail_closed(mutation):
    source = _source()
    if mutation == "foreign_eot": source["source_eot_fingerprint"] = "foreign"
    elif mutation == "hp":
        source["branch_authority"]["state"]["active"]["self"]["current_hp"] = 100
        source["branch_authority"]["state_fingerprint"] = fp(source["branch_authority"]["state"])
    elif mutation == "condition":
        source["branch_authority"]["state"]["current_state"]["condition_context"]["current_conditions"][0]["condition_type"] = "burn"
        source["branch_authority"]["state_fingerprint"] = fp(source["branch_authority"]["state"])
    elif mutation == "team_binding": source["team_authorities"]["self"]["source_binding"] = {}
    elif mutation == "incomplete_team": source["team_authorities"]["self"]["completeness"] = "incomplete"
    else: source["team_authorities"]["self"]["members"][1]["hp"] = {"status": "unknown"}
    assert freeze_post_eot_transition(**source)["status"] in {"rejected", "incomplete"}


@pytest.mark.parametrize("candidate", [_owner("self", "foreign"), {**_owner("self", "self-1"), "slot_index": 7}, _owner("opponent", "b")])
def test_invalid_trainer_choice_rejects(candidate):
    request = freeze_post_eot_transition(**_source())
    assert freeze_replacement_intent(transition=request, side="self", incoming_owner=candidate)["status"] == "rejected"


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_replacement_preserves_survivor_and_yields_detached_next_decision(side):
    source = _source(self_hp=0 if side == "self" else 50, opponent_hp=0 if side == "opponent" else 50)
    before = deepcopy(source)
    cursor = _prepare(source)
    result = _finish(cursor)
    assert result["status"] == "next_decision_ready", result
    assert result["detached_next_decision_state"]["active"][side]["pokemon_id"] == f"{side}-1"
    survivor = "opponent" if side == "self" else "self"
    assert result["state"]["active"][survivor] == source["branch_authority"]["state"]["active"][survivor]
    assert source == before
    assert validate_post_eot_transition(transition=result)["status"] == "valid"


def test_hazards_reused_and_entry_ko_requires_fresh_trainer_choice():
    source = _source(members={"self": [_member("self", 1, hp=1), _member("self", 2)]}, hazards={"self": _hazards("self", rock="present"), "opponent": _hazards("opponent")})
    cursor = _prepare(source)
    original_request = cursor["request_id"]
    result = _finish(cursor, _hazards("self", rock="present"))
    assert result["status"] == "replacement_required", result
    assert result["state"]["active"]["self"]["current_hp"] == 0
    assert result["generation"] == 1 and result["request_id"] != original_request
    assert [x["slot_index"] for x in result["requirements"]["self"]["candidates"]] == [2]
    stale = deepcopy(cursor["history"][-1]["intents"])
    assert prepare_post_eot_replacements(transition=result, intents=stale)["status"] == "rejected"
    assert validate_post_eot_transition(transition=result)["status"] == "valid"


def test_double_replacement_requires_both_choices_and_speed_controls_entry():
    source = _source(0, 0, {"self": [_member("self", speed=50)], "opponent": [_member("opponent", speed=100)]})
    cursor = _prepare(source)
    assert cursor["entry_order"] == ("opponent", "self")
    assert all(cursor["state"]["active"][s]["pokemon_id"] == f"{s}-1" for s in ("self", "opponent"))
    assert cursor["entry_queue"] == (("hazards", "opponent"), ("hazards", "self"), ("abilities", "opponent"), ("abilities", "self"))
    assert _finish(cursor)["status"] == "next_decision_ready"


@pytest.mark.parametrize("field", ["state", "request_id", "requirements"])
def test_forged_transition_rejected_by_source_replay(field):
    result = _finish(_prepare(_source()))
    forged = deepcopy(result)
    if field == "state": forged["state"]["active"]["self"]["current_hp"] = 99
    elif field == "request_id": forged["request_id"] = "foreign"
    else: forged["requirements"]["self"]["candidates"] = (_owner("self", "forged"),)
    assert validate_post_eot_transition(transition=forged)["status"] == "rejected"


def _identity(active): return {k: active[k] for k in ("side", "slot_index", "pokemon_id")}


def _ability_entry(cursor):
    entry = _entry(cursor)
    phase, side = cursor["entry_queue"][0]
    other = "opponent" if side == "self" else "self"
    ability = entry["mechanics"]["target_roster_mechanics"]["ability_authority"]["value"]
    active = cursor["state"]["active"]
    if ability == "intimidate":
        stage = next(r["stage"] for r in cursor["state"]["current_state"]["stat_stage_context"]["current_stages"] if r["side"] == other and r["stat"] == "attack")
        entry["mechanics"]["intimidate_authority"] = {"schema_version": "switch-entry-intimidate-authority-v1", "session_id": "s",
            "source": _identity(active[side]), "target": _identity(active[other]), "interaction": "lowered", "target_attack_stage": stage}
    if ability == "download":
        entry["mechanics"]["download_authority"] = {"schema_version": "switch-entry-download-authority-v1", "session_id": "s",
            "source": _identity(active[side]), "target": _identity(active[other]), "applicability": "applicable", "target_defense": 80, "target_special_defense": 100}
    return entry


@pytest.mark.parametrize("ability,weather", [("drizzle", "rain"), ("drought", "sun"), ("sand-stream", "sandstorm"), ("snow-warning", "snow")])
def test_weather_setter_reused_before_next_decision(ability, weather):
    cursor = _prepare(_source(members={"self": [_member("self", ability=ability)]}))
    result = _finish(cursor)
    assert result["status"] == "next_decision_ready", result
    assert result["detached_next_decision_state"]["current_state"]["field_state_context"]["current_field"]["weather"] == weather


@pytest.mark.parametrize("side,ability", [(s, a) for s in ("self", "opponent") for a in ("intimidate", "download")])
def test_entry_abilities_reuse_exact_new_source_and_opponent_identity(side, ability):
    source = _source(self_hp=0 if side == "self" else 50, opponent_hp=0 if side == "opponent" else 50, members={side: [_member(side, ability=ability)]})
    cursor = _prepare(source)
    while cursor["status"] == "entry_pending":
        cursor = advance_post_eot_entry(transition=cursor, entry_authority=_ability_entry(cursor))
    assert cursor["status"] == "next_decision_ready", cursor
    affected = side if ability == "download" else "opponent" if side == "self" else "self"
    attack = next(r["stage"] for r in cursor["state"]["current_state"]["stat_stage_context"]["current_stages"] if r["side"] == affected and r["stat"] == "attack")
    assert attack == (1 if ability == "download" else -1)
    assert validate_post_eot_transition(transition=cursor)["status"] == "valid"


def test_simultaneous_weather_order_uses_speed_and_refreshes_weather_generation():
    source = _source(0, 0, {"self": [_member("self", speed=50, ability="drought")], "opponent": [_member("opponent", speed=100, ability="drizzle")]})
    result = _finish(_prepare(source))
    assert result["status"] == "next_decision_ready"
    assert result["state"]["current_state"]["field_state_context"]["current_field"]["weather"] == "sun"
    reversed_source = deepcopy(source)
    reversed_source["team_authorities"] = dict(reversed(list(source["team_authorities"].items())))
    assert _finish(_prepare(reversed_source))["state"] == result["state"]


@pytest.mark.parametrize("rock,spikes,toxic,sticky,damage,condition,speed", [
    ("present", 1, 0, "absent", 37, "none", 0),
    ("absent", 0, 1, "absent", 0, "poison", 0),
    ("absent", 0, 2, "present", 0, "toxic", -1),
])
def test_hazard_damage_condition_and_stage_consumers_reused(rock, spikes, toxic, sticky, damage, condition, speed):
    source = _source(hazards={"self": _hazards("self", rock, spikes, toxic, sticky), "opponent": _hazards("opponent")})
    result = _finish(_prepare(source))
    assert result["status"] == "next_decision_ready", result
    assert result["state"]["active"]["self"]["current_hp"] == 80 - damage
    current = result["state"]["current_state"]
    assert next(r["condition_type"] for r in current["condition_context"]["current_conditions"] if r["side"] == "self") == condition
    assert next(r["stage"] for r in current["stat_stage_context"]["current_stages"] if r["side"] == "self" and r["stat"] == "speed") == speed


@pytest.mark.parametrize("mutation", ["hazard", "target_hp", "owner", "binding", "target_ability"])
def test_forged_entry_inputs_reject(mutation):
    cursor = _prepare(_source())
    entry = _entry(cursor)
    if mutation == "hazard": entry["mechanics"]["hazards"]["stealth_rock"] = "present"
    elif mutation == "target_hp": entry["mechanics"]["target_roster_mechanics"]["hp_authority"]["current_hp"] = 99
    elif mutation == "owner": entry["mechanics"]["target_roster_mechanics"]["pokemon_id"] = "foreign"
    elif mutation == "binding": entry["source_binding"]["source_branch_fingerprint"] = "stale"
    else: entry["mechanics"]["target_roster_mechanics"]["ability_authority"]["value"] = "drizzle"
    assert advance_post_eot_entry(transition=cursor, entry_authority=entry)["status"] == "rejected"


def test_missing_tie_order_does_not_use_side_order_or_quick_claw():
    request = freeze_post_eot_transition(**_source(0, 0))
    intents = {s: freeze_replacement_intent(transition=request, side=s, incoming_owner=request["requirements"][s]["candidates"][0]) for s in ("self", "opponent")}
    assert prepare_post_eot_replacements(transition=request, intents=intents)["reason"] == "simultaneous_entry_speed_tie_unresolved"
    invalid = {"request_id": request["request_id"], "basis": "quick_claw", "selected_owners": {s: i["incoming_owner"] for s, i in intents.items()}, "ordered_sides": ["self", "opponent"]}
    assert prepare_post_eot_replacements(transition=request, intents=intents, tie_order_authority=invalid)["status"] == "rejected"


def test_known_restrictions_retire_and_major_status_survives_on_the_surviving_side():
    source = _source()
    current = source["branch_authority"]["state"]["current_state"]
    for key in ("current_taunt_restrictions", "current_encore_restrictions", "current_disable_restrictions"):
        current[key] = {"self": {"owner": _owner("self", "a"), "state": "active"}, "opponent": {"owner": _owner("opponent", "b"), "state": "active"}}
    current["selected_action"] = {"identity": "old-turn-only"}
    source["branch_authority"]["state_fingerprint"] = fp(source["branch_authority"]["state"])
    result = _finish(_prepare(source))
    state = result["detached_next_decision_state"]
    for key in ("current_taunt_restrictions", "current_encore_restrictions", "current_disable_restrictions"):
        assert "self" not in state["current_state"][key]
        assert state["current_state"][key]["opponent"] == current[key]["opponent"]
    assert "selected_action" not in state["current_state"]


def test_both_unable_to_replace_is_exact_mechanics_terminal_without_scoring():
    result = freeze_post_eot_transition(**_source(0, 0, members={}))
    assert result["status"] == "battle_terminal"
    assert result["battle_terminal"] == {"unable_to_replace_sides": ("self", "opponent")}


def test_fainted_member_cannot_be_selected_and_unknown_eligibility_is_not_available():
    source = _source(members={"self": [_member("self", 1, hp=0), _member("self", 2)]})
    request = freeze_post_eot_transition(**source)
    dead = source["team_authorities"]["self"]["members"][1]["owner"]
    assert freeze_replacement_intent(transition=request, side="self", incoming_owner=dead)["status"] == "rejected"
    source["team_authorities"]["self"]["members"][2]["eligible"] = {"status": "unknown"}
    assert freeze_post_eot_transition(**source)["status"] == "incomplete"


def test_resolved_speed_tie_is_bound_to_both_explicit_selections():
    request = freeze_post_eot_transition(**_source(0, 0))
    intents = {s: freeze_replacement_intent(transition=request, side=s, incoming_owner=request["requirements"][s]["candidates"][0]) for s in ("self", "opponent")}
    tie = {"request_id": request["request_id"], "basis": "resolved_switch_in_speed_tie", "selected_owners": {s: i["incoming_owner"] for s, i in intents.items()}, "ordered_sides": ["opponent", "self"]}
    cursor = prepare_post_eot_replacements(transition=request, intents=intents, tie_order_authority=tie)
    assert cursor["entry_order"] == ("opponent", "self")
    assert _finish(cursor)["status"] == "next_decision_ready"
    tie["request_id"] = "stale"
    assert prepare_post_eot_replacements(transition=request, intents=intents, tie_order_authority=tie)["status"] == "rejected"


def test_second_explicit_replacement_can_finish_after_first_entry_ko():
    source = _source(members={"self": [_member("self", 1, hp=1), _member("self", 2)]}, hazards={"self": _hazards("self", rock="present"), "opponent": _hazards("opponent")})
    request = _finish(_prepare(source))
    intent = freeze_replacement_intent(transition=request, side="self", incoming_owner=request["requirements"]["self"]["candidates"][0])
    result = _finish(prepare_post_eot_replacements(transition=request, intents={"self": intent}))
    assert result["status"] == "next_decision_ready"
    assert result["state"]["active"]["self"]["pokemon_id"] == "self-2"
    assert result["state"]["active"]["self"]["current_hp"] == 55
    assert len(result["state"]["post_eot_bench_records"]) == 2
    assert validate_post_eot_transition(transition=result)["status"] == "valid"


def test_double_replacement_hazard_ko_preserves_other_entry_and_requests_only_dead_side():
    source = _source(0, 0, {"self": [_member("self", 1, hp=1, speed=50), _member("self", 2)], "opponent": [_member("opponent", speed=100, ability="intimidate")]},
                     hazards={"self": _hazards("self", rock="present"), "opponent": _hazards("opponent")})
    cursor = _prepare(source)
    while cursor["status"] == "entry_pending":
        cursor = advance_post_eot_entry(transition=cursor, entry_authority=_ability_entry(cursor))
    assert cursor["status"] == "replacement_required", cursor
    assert cursor["requirements"]["opponent"]["state"] == "no_replacement_needed"
    assert cursor["requirements"]["self"]["candidates"][0]["slot_index"] == 2
    assert cursor["state"]["active"]["opponent"]["current_hp"] == 80


def test_sturdy_post_entry_state_reuses_canonical_evaluator():
    cursor = _prepare(_source(members={"self": [_member("self", hp=100, ability="sturdy")]}))
    cursor = advance_post_eot_entry(transition=cursor, entry_authority=_entry(cursor))
    entry = _entry(cursor)
    assert advance_post_eot_entry(transition=cursor, entry_authority=entry)["reason"] == "sturdy_entry_authority"
    entry["mechanics"]["sturdy_authority"] = {"schema_version": "switch-entry-sturdy-authority-v1", "session_id": "s",
        "source": _identity(cursor["state"]["active"]["self"]), "target": _identity(cursor["state"]["active"]["opponent"]), "applicability": "applicable"}
    result = advance_post_eot_entry(transition=cursor, entry_authority=entry)
    assert result["status"] == "next_decision_ready", result
    assert result["state"]["active"]["self"]["current_hp"] == 100


def test_seeded_target_retires_but_surviving_seed_keeps_source_position():
    source = _source()
    state = source["branch_authority"]["state"]
    seed = {"schema_version": "detached-leech-seed-persistent-effect-v1", "session_id": "s", "source_branch_fingerprint": "seed-application",
            "provenance": "trusted_leech_seed_persistent_effect_state", "states": [
                {"owner": _owner("self", "a"), "state": "known_active", "source_slot": {"session_id": "s", "side": "opponent", "slot_index": 0}},
                {"owner": _owner("opponent", "b"), "state": "known_active", "source_slot": {"session_id": "s", "side": "self", "slot_index": 0}}]}
    state["leech_seed_persistent_effect_context"] = seed
    source["branch_authority"]["state_fingerprint"] = fp(state)
    result = _finish(_prepare(source))
    rows = result["state"]["leech_seed_persistent_effect_context"]["states"]
    assert rows[0]["state"] == "known_inactive" and "source_slot" not in rows[0]
    assert rows[1]["state"] == "known_active" and rows[1]["source_slot"]["slot_index"] == 1
    assert rows[1]["historical_source_slot"]["slot_index"] == 0


def test_post_eot_hp_is_used_after_residual_ko_and_condition_is_retained_in_bench_record():
    source = _source()
    eot = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=6, self_row=_row("self", "a", 6, condition="burn")))
    source["eot_ledger"], source["source_eot_fingerprint"] = eot, fp(eot)
    binding = post_eot_source_binding(eot)
    branch = source["branch_authority"]
    branch["source_binding"] = binding
    branch["state"]["current_state"]["condition_context"]["current_conditions"][0]["condition_type"] = "burn"
    branch["state_fingerprint"] = fp(branch["state"])
    for team in source["team_authorities"].values(): team["source_binding"] = binding
    result = _finish(_prepare(source))
    retired = result["state"]["post_eot_bench_records"][0]
    assert retired["outgoing_active"]["current_hp"] == 0
    assert retired["condition_context"]["current_conditions"][0]["condition_type"] == "burn"
    assert result["state"]["active"]["self"]["current_hp"] == 80


@pytest.mark.parametrize("mutation", ["owner", "hp", "hazard"])
def test_replayed_entry_consequences_cannot_be_forged(mutation):
    cursor = _prepare(_source())
    advanced = advance_post_eot_entry(transition=cursor, entry_authority=_entry(cursor))
    forged = deepcopy(advanced)
    result = forged["entry_results"][0]["result"]
    if mutation == "owner": result["next_state"]["active"]["self"]["pokemon_id"] = "forged"
    elif mutation == "hp": result["next_state"]["active"]["self"]["current_hp"] = 99
    else: result["consequence_trace"][0]["damage"] = 99
    assert validate_post_eot_transition(transition=forged)["status"] == "rejected"


def test_surviving_toxic_progression_comes_from_completed_eot():
    source = _source(opponent_hp=32)
    eot = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=0, opponent_hp=50, opponent_row=_row("opponent", "b", 50, condition="toxic", toxic=3)))
    source["eot_ledger"], source["source_eot_fingerprint"] = eot, fp(eot)
    binding = post_eot_source_binding(eot)
    branch = source["branch_authority"]
    branch["source_binding"] = binding
    branch["state"]["current_state"]["condition_context"]["current_conditions"][1]["condition_type"] = "toxic"
    branch["state_fingerprint"] = fp(branch["state"])
    for team in source["team_authorities"].values(): team["source_binding"] = binding
    before = deepcopy(source)
    result = _finish(_prepare(source))
    assert result["state"]["active"]["opponent"]["current_hp"] == 32
    assert result["state"]["post_eot_toxic_progression"]["opponent"]["authority"]["next_stage"] == 4
    assert result["state"]["post_eot_toxic_progression"]["self"]["authority"]["status"] == "unknown"
    assert source == before


def test_both_toxic_spikes_applications_survive_in_detached_next_decision():
    source = _source(0, 0, {"self": [_member("self", speed=50)], "opponent": [_member("opponent", speed=100)]},
                     hazards={s: _hazards(s, toxic=2) for s in ("self", "opponent")})
    result = _finish(_prepare(source))
    assert result["status"] == "next_decision_ready", result
    state = result["detached_next_decision_state"]
    assert set(state["post_eot_condition_overlays"]) == {"self", "opponent"}
    assert all(row["condition_type"] == "toxic" for row in state["post_eot_condition_overlays"].values())
    assert all(row["current_stage"] == 1 for row in state["post_eot_toxic_lifecycles"].values())


def test_only_one_of_two_required_intents_does_not_materialize_either_replacement():
    request = freeze_post_eot_transition(**_source(0, 0))
    before = deepcopy(request)
    intent = freeze_replacement_intent(transition=request, side="self", incoming_owner=request["requirements"]["self"]["candidates"][0])
    result = prepare_post_eot_replacements(transition=request, intents={"self": intent})
    assert result["status"] == "incomplete" and "state" not in result
    assert request == before


@pytest.mark.parametrize("field", ["generation", "outgoing_owner", "request_id"])
def test_stale_trainer_intents_reject(field):
    request = freeze_post_eot_transition(**_source())
    intent = freeze_replacement_intent(transition=request, side="self", incoming_owner=request["requirements"]["self"]["candidates"][0])
    intent[field] = 99 if field == "generation" else _owner("self", "foreign") if field == "outgoing_owner" else "stale"
    assert prepare_post_eot_replacements(transition=request, intents={"self": intent})["status"] == "rejected"


def test_post_eot_envelope_mismatch_rejects_even_with_new_content_fingerprint():
    source = _source()
    source["eot_ledger"]["source_runtime_fingerprint"] = "foreign"
    source["source_eot_fingerprint"] = fp(source["eot_ledger"])
    assert freeze_post_eot_transition(**source)["reason"] == "eot_envelope_binding_mismatch"


def test_intimidate_private_direct_projection_consumes_new_stage():
    source = _source(members={"self": [_member("self", ability="intimidate")]})
    source["branch_authority"]["state"]["current_state"]["direct_mechanics_context"] = {
        "defender": {"current_hp": 50, "max_hp": 100, "boosts": {"attack": 0}}}
    source["branch_authority"]["state_fingerprint"] = fp(source["branch_authority"]["state"])
    cursor = _prepare(source)
    while cursor["status"] == "entry_pending": cursor = advance_post_eot_entry(transition=cursor, entry_authority=_ability_entry(cursor))
    assert cursor["state"]["current_state"]["direct_mechanics_context"]["defender"]["boosts"]["attack"] == -1


def test_simultaneous_intimidate_then_download_consumes_updated_entry_stage():
    source = _source(0, 0, {"self": [_member("self", ability="download", speed=50)], "opponent": [_member("opponent", ability="intimidate", speed=100)]})
    cursor = _prepare(source)
    while cursor["status"] == "entry_pending": cursor = advance_post_eot_entry(transition=cursor, entry_authority=_ability_entry(cursor))
    assert cursor["status"] == "next_decision_ready", cursor
    stage = next(r["stage"] for r in cursor["state"]["current_state"]["stat_stage_context"]["current_stages"] if r["side"] == "self" and r["stat"] == "attack")
    assert stage == 0  # Intimidate lowered to -1; Download then raised to 0.


def test_final_available_candidate_hazard_ko_proves_battle_terminal():
    source = _source(members={"self": [_member("self", hp=1)]}, hazards={"self": _hazards("self", rock="present"), "opponent": _hazards("opponent")})
    result = _finish(_prepare(source))
    assert result["status"] == "battle_terminal"
    assert result["battle_terminal"]["unable_to_replace_sides"] == ("self",)
    assert validate_post_eot_transition(transition=result)["status"] == "valid"


def test_stale_d0_hp_in_optional_calculator_mirror_cannot_cross_post_eot_boundary():
    source = _source(self_hp=50)
    branch = source["branch_authority"]
    branch["state"]["current_state"]["direct_mechanics_context"] = {"attacker": {"current_hp": 100, "max_hp": 100}}
    branch["state_fingerprint"] = fp(branch["state"])
    assert freeze_post_eot_transition(**source)["reason"] == "post_eot_calculator_hp_mismatch"


def test_incoming_optional_calculator_hp_must_match_selected_member():
    source = _source()
    incoming = source["team_authorities"]["self"]["members"][1]["incoming_authority"]
    incoming["current_state"]["direct_mechanics_context"] = {"attacker": {"current_hp": 100, "max_hp": 100}}
    request = freeze_post_eot_transition(**source)
    intent = freeze_replacement_intent(transition=request, side="self", incoming_owner=request["requirements"]["self"]["candidates"][0])
    assert prepare_post_eot_replacements(transition=request, intents={"self": intent})["reason"] == "incoming_current_mechanics_mismatch"


def test_next_decision_keeps_original_eot_and_post_entry_provenance_domains_distinct():
    source = _source()
    result = _finish(_prepare(source))
    lifecycle = result["detached_next_decision_state"]["turn_engine_lifecycle"]
    assert lifecycle["source_end_of_turn_fingerprint"] == source["source_eot_fingerprint"]
    assert lifecycle["source_post_eot_state_fingerprint"] == fp(result["state"])
    assert lifecycle["source_end_of_turn_fingerprint"] != lifecycle["source_post_eot_state_fingerprint"]
    assert lifecycle["source_replacement_request_id"] == result["request_id"]
    assert result["next_decision_fingerprint"] == fp(result["detached_next_decision_state"])
