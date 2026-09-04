from copy import deepcopy

from llm.advisor_end_of_turn_residual_phase import (
    END_OF_TURN_EVENT_ORDER,
    freeze_end_of_turn_phase_input,
    materialize_end_of_turn_residual_phase,
    validate_end_of_turn_residual_phase_ledger,
)


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


def _input(*, self_hp=50, opponent_hp=50, self_row=None, opponent_row=None):
    return freeze_end_of_turn_phase_input(
        terminal_ledger=_ledger(self_hp=self_hp, opponent_hp=opponent_hp), terminal_leaf_id="leaf",
        active_states={"self": self_row or _row("self", "a", self_hp), "opponent": opponent_row or _row("opponent", "b", opponent_hp)},
    )


def test_phase_binds_exact_terminal_leaf_and_uses_detached_post_action_hp():
    phase = _input(self_hp=50, self_row=_row("self", "a", 50, item="leftovers"))
    result = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert result["status"] == "evaluable"
    event = result["events"][0]
    assert event["event_kind"] == "leftovers" and event["pre_hp"] == 50 and event["hp_delta"] == 6 and event["post_hp"] == 56


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
