from copy import deepcopy

from llm.advisor_end_of_turn_residual_phase import (
    END_OF_TURN_EVENT_ORDER,
    freeze_end_of_turn_phase_input,
    materialize_end_of_turn_residual_phase,
    validate_end_of_turn_residual_phase_ledger,
    materialize_detached_weather_residual,
)


def test_detached_weather_residual_uses_canonical_sandstorm_and_snow_contracts():
    abilities = {"self": "pressure", "opponent": "pressure"}
    active = {"side": "self", "types": ["normal"], "item": None, "current_hp": 50, "maximum_hp": 100}
    sand = materialize_detached_weather_residual(weather_authority={"status": "known", "weather": "sandstorm"}, active=active, active_abilities=abilities)
    assert sand["result"]["residual_damage"] == 6
    assert materialize_detached_weather_residual(weather_authority={"status": "known", "weather": "snow"}, active=active, active_abilities=abilities)["outcome"] == "non_damaging_weather"
    assert materialize_detached_weather_residual(weather_authority={"status": "unknown"}, active=active, active_abilities=abilities)["status"] == "incomplete"


def _owner(side, pokemon_id):
    return {"session_id": "s", "side": side, "slot_index": 0, "pokemon_id": pokemon_id}


def _ledger(*, self_hp=50, opponent_hp=50):
    return {
        "status": "evaluable", "schema_version": "exact-immediate-action-pair-outcome-ledger-v1",
        "pair_id": "pair", "session_id": "s", "source_runtime_fingerprint": "runtime",
        "source_branch_fingerprint": "branch", "decision_owner": _owner("self", "a"),
        "own_actor": _owner("self", "a"), "opponent_actor": _owner("opponent", "b"),
        "terminal_probability_mass": {"numerator": 1, "denominator": 1},
        "terminal_leaves": ({"pair_leaf_id": "leaf", "final_consequences": {"own_final_hp": self_hp, "opponent_final_hp": opponent_hp}},),
    }


def _row(side, pid, hp, *, maximum=100, condition=None, item=None, toxic=None, speed=100, ability=None):
    binding = {"session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "owner": _owner(side, pid)}
    return {
        "owner": _owner(side, pid), "hp": {"status": "known", "current_hp": hp, "maximum_hp": maximum, "source_terminal_leaf_id": "leaf"},
        "fainted": {"status": "known", "value": hp == 0, "source_terminal_leaf_id": "leaf"},
        "condition": {"status": "known_none", "source_binding": binding} if condition is None else {"status": "known_present", "condition": condition, "source_binding": binding},
        "item": {"status": "known_absent", "source_binding": binding} if item is None else {"status": "known", "value": item, "source_binding": binding},
        "toxic_progression": {"status": "unknown", "source_binding": binding} if toxic is None else {"status": "known", "next_stage": toxic, "source_binding": binding},
        "speed": {"status": "known", "value": speed, "source_binding": binding},
        "ability": {"status": "known_absent", "source_binding": binding} if ability is None else {"status": "known", "value": ability, "source_binding": binding},
    }


def _input(*, self_hp=50, opponent_hp=50, self_row=None, opponent_row=None, weather_authority=None, leech_seed_transfers=()):
    return freeze_end_of_turn_phase_input(
        terminal_ledger=_ledger(self_hp=self_hp, opponent_hp=opponent_hp), terminal_leaf_id="leaf",
        active_states={"self": self_row or _row("self", "a", self_hp), "opponent": opponent_row or _row("opponent", "b", opponent_hp)}, weather_authority=weather_authority, leech_seed_transfers=leech_seed_transfers,
    )


def _weather(weather):
    return {"status": "known", "weather": weather, "source_binding": {"session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch"}}


def _weather_row(side, pid, hp, *, types, ability="pressure", item=None):
    row = _row(side, pid, hp, item=item, ability=ability)
    row["types"] = {"status": "known", "value": types, "source_binding": row["ability"]["source_binding"]}
    return row


def test_phase_integrates_sandstorm_with_immunities_and_snow_no_chip():
    self_row = _weather_row("self", "a", 50, types=["normal"])
    foe_row = _weather_row("opponent", "b", 50, types=["rock"])
    result = materialize_end_of_turn_residual_phase(phase_input=_input(self_row=self_row, opponent_row=foe_row, weather_authority=_weather("sandstorm")))
    assert [(event["event_kind"], event["affected_owner"]["side"], event["hp_delta"]) for event in result["events"]] == [("sandstorm", "self", -6)]
    assert not materialize_end_of_turn_residual_phase(phase_input=_input(self_row=self_row, opponent_row=foe_row, weather_authority=_weather("snow")))["events"]


def test_sandstorm_modifier_immunities_and_missing_authority_fail_closed():
    foe = _weather_row("opponent", "b", 50, types=["normal"])
    for types, ability, item in ((["ground"], "pressure", None), (["steel"], "pressure", None), (["normal"], "magic-guard", None), (["normal"], "overcoat", None), (["normal"], "pressure", "safety-goggles")):
        row = _weather_row("self", "a", 50, types=types, ability=ability, item=item)
        events = materialize_end_of_turn_residual_phase(phase_input=_input(self_row=row, opponent_row=foe, weather_authority=_weather("sandstorm")))["events"]
        assert not [event for event in events if event["affected_owner"]["side"] == "self"]
    row = _weather_row("self", "a", 50, types=["normal"]); row["ability"] = {"status": "unknown", "source_binding": row["types"]["source_binding"]}
    assert materialize_end_of_turn_residual_phase(phase_input=_input(self_row=row, opponent_row=foe, weather_authority=_weather("sandstorm")))["status"] == "incomplete"


def test_phase_binds_exact_terminal_leaf_and_uses_detached_post_action_hp():
    phase = _input(self_hp=50, self_row=_row("self", "a", 50, item="leftovers"))
    result = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert result["status"] == "evaluable"
    event = result["events"][0]
    assert event["event_kind"] == "leftovers" and event["pre_hp"] == 50 and event["hp_delta"] == 6 and event["post_hp"] == 56


def test_linked_leech_seed_transfer_updates_target_and_current_source_position_recipient():
    trace = {"effect":"leech_seed","owner":_owner("self","a"),"recipient":_owner("opponent","b"),"source_slot":{"session_id":"s","side":"opponent","slot_index":0},"target_pre_hp":50,"target_post_hp":38,"target_damage":12,"recipient_pre_hp":50,"recipient_post_hp":62,"recipient_modifier":"none","liquid_ooze":False,"attempted_recovery":12,"recipient_outcome":"recovered","execution_status":"executed","provenance":"detached_branch_leech_seed_v1"}
    phase = _input(leech_seed_transfers=(trace,))
    result = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert result["status"] == "evaluable" and result["events"][0]["event_kind"] == "leech_seed"
    assert result["post_end_of_turn_active_states"]["self"]["current_hp"] == 38
    assert result["post_end_of_turn_active_states"]["opponent"]["current_hp"] == 62


def test_linked_leech_seed_liquid_ooze_reversal_preserves_exact_recipient_damage():
    trace = {"effect":"leech_seed","owner":_owner("self","a"),"recipient":_owner("opponent","b"),"source_slot":{"session_id":"s","side":"opponent","slot_index":0},"target_pre_hp":20,"target_post_hp":8,"target_damage":12,"recipient_pre_hp":15,"recipient_post_hp":0,"recipient_modifier":"big_root","liquid_ooze":True,"attempted_recovery":15,"recipient_outcome":"liquid_ooze_damage","execution_status":"executed","provenance":"detached_branch_leech_seed_v1"}
    result = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=20, opponent_hp=15, leech_seed_transfers=(trace,)))
    event = result["events"][0]
    assert event["linked_recipient"] == _owner("opponent", "b")
    assert result["post_end_of_turn_active_states"]["opponent"]["current_hp"] == 0


def test_linked_leech_seed_magic_guard_prevention_keeps_both_hp_values():
    trace = {"effect":"leech_seed","owner":_owner("self","a"),"recipient":_owner("opponent","b"),"source_slot":{"session_id":"s","side":"opponent","slot_index":0},"target_pre_hp":50,"target_post_hp":50,"target_damage":0,"recipient_pre_hp":50,"recipient_post_hp":50,"recipient_modifier":"none","liquid_ooze":False,"attempted_recovery":0,"recipient_outcome":"prevented_by_magic_guard","execution_status":"executed","provenance":"detached_branch_leech_seed_v1"}
    result = materialize_end_of_turn_residual_phase(phase_input=_input(leech_seed_transfers=(trace,)))
    assert result["post_end_of_turn_active_states"]["self"]["current_hp"] == 50
    assert result["post_end_of_turn_active_states"]["opponent"]["current_hp"] == 50


def test_leech_seed_is_atomic_tier_eight_before_conditions_and_uses_actual_drain_basis():
    trace = {"effect":"leech_seed","owner":_owner("self","a"),"recipient":_owner("opponent","b"),"source_slot":{"session_id":"s","side":"opponent","slot_index":0},"target_pre_hp":5,"target_post_hp":0,"target_damage":5,"recipient_pre_hp":50,"recipient_post_hp":55,"recipient_modifier":"none","liquid_ooze":False,"attempted_recovery":5,"recipient_outcome":"recovered","execution_status":"executed","provenance":"detached_branch_leech_seed_v1"}
    result = materialize_end_of_turn_residual_phase(phase_input=_input(
        self_hp=5, opponent_hp=50, self_row=_row("self", "a", 5, condition="burn"), leech_seed_transfers=(trace,),
    ))
    assert [event["event_kind"] for event in result["events"]] == ["leech_seed"]
    assert result["events"][0]["hp_delta"] == -5
    assert result["post_end_of_turn_active_states"]["opponent"]["current_hp"] == 55


def test_linked_transfer_rejects_terminal_recipient_identity_forgery():
    trace = {"effect":"leech_seed","owner":_owner("self","a"),"recipient":_owner("opponent","foreign"),"source_slot":{"session_id":"s","side":"opponent","slot_index":0},"target_pre_hp":50,"target_post_hp":38,"target_damage":12,"recipient_pre_hp":50,"recipient_post_hp":62,"recipient_modifier":"none","liquid_ooze":False,"attempted_recovery":12,"recipient_outcome":"recovered","execution_status":"executed","provenance":"detached_branch_leech_seed_v1"}
    assert materialize_end_of_turn_residual_phase(phase_input=_input(leech_seed_transfers=(trace,)))["reason"] == "leech_seed_transfer_terminal_identity_mismatch"


def test_terminal_binding_and_missing_hp_fail_closed():
    assert _input(self_hp=50, self_row=_row("self", "a", 49))["reason"] == "end_of_turn_terminal_hp_binding_mismatch"
    phase = _input(); forged = deepcopy(phase); forged["terminal_leaf_id"] = "foreign"
    assert materialize_end_of_turn_residual_phase(phase_input=forged)["status"] == "rejected"
    missing = _row("self", "a", 50); missing["hp"] = {"status": "unknown"}
    assert _input(self_row=missing)["status"] == "incomplete"


def test_leftovers_caps_and_never_revives_and_unknown_item_is_not_absence():
    cap = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=99, self_row=_row("self", "a", 99, item="leftovers")))
    assert cap["events"][0]["post_hp"] == 100
    fainted = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=0, self_row=_row("self", "a", 0, item="leftovers")))
    assert not fainted["events"]
    unknown = _row("self", "a", 50); unknown["item"] = {"status": "unknown", "source_binding": unknown["item"]["source_binding"]}
    assert materialize_end_of_turn_residual_phase(phase_input=_input(self_row=unknown))["status"] == "incomplete"
    full = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=100, self_row=_row("self", "a", 100, item="leftovers")))
    assert full["events"][0]["hp_delta"] == 0 and full["events"][0]["terminal_reason"] == "already_full_hp"
    stale = _row("self", "a", 50, item="leftovers")
    stale["item"]["source_binding"]["source_runtime_fingerprint"] = "stale"
    assert _input(self_row=stale)["status"] == "rejected"


def test_burn_and_regular_poison_use_post_action_hp_and_guts_does_not_suppress():
    burn = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=7, self_row=_row("self", "a", 7, condition="burn", ability="guts")))
    assert burn["events"][0]["hp_delta"] == -6 and burn["events"][0]["post_hp"] == 1
    poison = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=13, self_row=_row("self", "a", 13, condition="poison")))
    assert poison["events"][0]["event_kind"] == "poison" and poison["events"][0]["hp_delta"] == -12 and poison["events"][0]["post_hp"] == 1


def test_toxic_uses_exact_stage_advances_detached_only_and_unknown_counter_fails_closed():
    result = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=30, self_row=_row("self", "a", 30, condition="toxic", toxic=3)))
    event = result["events"][0]
    assert event["event_kind"] == "toxic" and event["hp_delta"] == -18
    assert result["post_end_of_turn_active_states"]["self"]["toxic_progression"]["next_stage"] == 4
    unknown = _row("self", "a", 30, condition="toxic")
    assert materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=30, self_row=unknown))["reason"] == "end_of_turn_toxic_counter_unknown"
    first = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=30, self_row=_row("self", "a", 30, condition="toxic", toxic=1)))
    assert first["events"][0]["hp_delta"] == -6 and first["post_end_of_turn_active_states"]["self"]["toxic_progression"]["next_stage"] == 2
    forged = _row("self", "a", 30, condition="toxic", toxic=3)
    forged["toxic_progression"]["source_binding"]["owner"] = _owner("opponent", "b")
    assert _input(self_hp=30, self_row=forged)["status"] == "rejected"


def test_proven_same_turn_condition_is_consumed_but_forged_source_is_rejected():
    row = _row("self", "a", 50, condition="burn")
    row["condition"]["source_terminal_leaf_id"] = "leaf"
    row["condition"]["hypothetical_condition_authority"] = {"status": "known_present", "condition": "burn"}
    result = materialize_end_of_turn_residual_phase(phase_input=_input(self_row=row))
    assert result["events"][0]["event_kind"] == "burn"
    forged = deepcopy(row); forged["condition"]["source_terminal_leaf_id"] = "other"
    assert _input(self_row=forged)["reason"] == "end_of_turn_condition_terminal_binding_mismatch"
    poison = _row("self", "a", 50, condition="poison")
    poison["condition"]["source_terminal_leaf_id"] = "leaf"
    poison["condition"]["hypothetical_condition_authority"] = {"status": "known_present", "condition": "poison"}
    assert materialize_end_of_turn_residual_phase(phase_input=_input(self_row=poison))["events"][0]["event_kind"] == "poison"
    attempted = _row("self", "a", 50, condition="burn")
    attempted["condition"]["source_terminal_leaf_id"] = "leaf"
    assert _input(self_row=attempted)["reason"] == "end_of_turn_hypothetical_condition_transition_unproven"
    not_applied = _row("self", "a", 50)
    assert not materialize_end_of_turn_residual_phase(phase_input=_input(self_row=not_applied))["events"]
    incomplete = _row("self", "a", 50); incomplete["condition"] = {"status": "unknown", "source_binding": incomplete["condition"]["source_binding"]}
    assert _input(self_row=incomplete)["status"] == "incomplete"


def test_order_is_catalog_driven_speed_ordered_and_ledger_rejects_forgery():
    phase = _input(
        self_row=_row("self", "a", 50, condition="burn", speed=50),
        opponent_row=_row("opponent", "b", 50, condition="poison", speed=100),
    )
    result = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert [e["event_kind"] for e in result["events"]] == ["poison", "burn"]
    assert result["events"][0]["order_class"] == END_OF_TURN_EVENT_ORDER["poison"]
    forged = deepcopy(result); forged["events"] = tuple(reversed(forged["events"]))
    assert validate_end_of_turn_residual_phase_ledger(ledger=forged)["status"] == "rejected"


def test_residual_ko_defers_replacement_and_magic_guard_fails_closed():
    ko = materialize_end_of_turn_residual_phase(phase_input=_input(self_hp=6, self_row=_row("self", "a", 6, condition="burn", item="leftovers")))
    assert len(ko["events"]) == 1 and ko["events"][0]["post_hp"] == 0
    assert ko["post_end_of_turn_active_states"]["self"]["replacement_after_end_of_turn_faint"] == "deferred"
    guarded = materialize_end_of_turn_residual_phase(phase_input=_input(self_row=_row("self", "a", 50, condition="burn", ability="magic-guard")))
    assert guarded["reason"] == "end_of_turn_magic_guard_residual_consumer_unimplemented"


def test_two_actives_receive_events_and_missing_cross_residual_speed_fails_closed():
    result = materialize_end_of_turn_residual_phase(phase_input=_input(
        self_row=_row("self", "a", 50, condition="burn", speed=100),
        opponent_row=_row("opponent", "b", 50, item="leftovers", speed=50),
    ))
    assert [(event["event_kind"], event["affected_owner"]["side"]) for event in result["events"]] == [("burn", "self"), ("leftovers", "opponent")]
    self_row, opponent_row = _row("self", "a", 50, condition="burn"), _row("opponent", "b", 50, condition="poison")
    self_row["speed"] = {"status": "unknown", "source_binding": self_row["speed"]["source_binding"]}
    assert materialize_end_of_turn_residual_phase(phase_input=_input(self_row=self_row, opponent_row=opponent_row))["reason"] == "end_of_turn_residual_speed_unknown"
