from copy import deepcopy
from fractions import Fraction
import pytest
from tests.test_detached_opponent_response_profile import _state, _owner, _snapshot, _complete_state, _metadata, MOVES
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_champions_sleep_freeze_action_gate import freeze_champions_status_action_gate as freeze, materialize_status_gate_branch as materialize, validate_status_gate, fraction, SELF_THAW_MOVES


def inputs(condition="sleep", prior=0, duration=None, ability="pressure", opposing_ability="pressure", side="self"):
    state = _complete_state(_state())
    raw = state[f"{side}_side"]["pokemon"][0]
    raw["condition"] = condition
    raw["condition_provenance"]["condition"] = condition
    raw["current_ability"] = ability
    state[f"{'opponent' if side == 'self' else 'self'}_side"]["pokemon"][0]["current_ability"] = opposing_ability
    owner = _owner(state, side)
    event = {"observation_id":"progression", "observation_sequence":1, "planned_effect":"record_champions_status_progression", "trust":"user_confirmed_observation", **owner,
             "condition":condition, "origin_id":"status:origin:1", "established_turn":1, "prior_attempts":prior, "sleep_duration":duration, "turn_number":1}
    result = project_atomic_transition(state, {"session_id":state["session_id"], "status":"planned", "conflicts":[], "ordered_steps":[event]}, state["session_id"])
    assert result["status"] == "ready_with_projected_state", result
    snapshot = _snapshot(result["projected_state"])
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state,"self"))
    return snapshot, d0, owner


def gate(condition="sleep", move="tackle", **kwargs):
    snapshot,d0,actor=inputs(condition,**kwargs)
    result=freeze(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,action_id=f"attack:{move}",move_id=move,action_order={"order":"own_first"},path=("root",))
    return snapshot,d0,result


def test_sleep_initial_distribution_is_persistent_not_independent_wake_rolls():
    snapshot,d0,g=gate()
    assert validate_status_gate(g)
    assert [fraction(b["probability"]) for b in g["branches"]] == [Fraction(1,3),Fraction(2,3)]
    assert all(b["kind"]=="cancelled_sleep" for b in g["branches"])
    original=deepcopy((snapshot,d0))
    for branch in g["branches"]:
        view=materialize(strategy_d0=d0,runtime_snapshot=snapshot,authority=g,branch=branch)
        nxt=freeze(strategy_d0=view["strategy_d0"],runtime_snapshot=view["runtime_snapshot"],actor=g["actor"],action_id="next:tackle",move_id="tackle",action_order={},path=(branch["branch_id"],))
        assert len(nxt["branches"])==1 and fraction(nxt["branches"][0]["probability"])==1
        b=nxt["branches"][0]
        assert b["sleep_duration"]==branch["sleep_duration"] and b["duration_identity"]==branch["duration_identity"]
        assert b["kind"]==("wakes_and_executes" if b["sleep_duration"]==2 else "cancelled_sleep")
        if b["sleep_duration"]==3:
            second=materialize(strategy_d0=view["strategy_d0"],runtime_snapshot=view["runtime_snapshot"],authority=nxt,branch=b)
            third=freeze(strategy_d0=second["strategy_d0"],runtime_snapshot=second["runtime_snapshot"],actor=g["actor"],action_id="third:tackle",move_id="tackle",action_order={},path=(b["branch_id"],))
            assert third["branches"][0]["kind"]=="wakes_and_executes" and fraction(third["branches"][0]["probability"])==1
    assert (snapshot,d0)==original


@pytest.mark.parametrize("prior",[0,1,2])
def test_freeze_probabilities_and_third_attempt(prior):
    snapshot,d0,g=gate("freeze",prior=prior)
    assert validate_status_gate(g)
    assert [fraction(b["probability"]) for b in g["branches"]]==([Fraction(1,4),Fraction(3,4)] if prior<2 else [Fraction(1)])
    assert g["branches"][0]["kind"]=="thaws_and_executes"
    assert sum((fraction(b["probability"]) for b in g["branches"]),Fraction())==1
    original=deepcopy((snapshot,d0))
    view=materialize(strategy_d0=d0,runtime_snapshot=snapshot,authority=g,branch=g["branches"][0])
    assert view["strategy_d0"]["current_condition_authority"]["self"]["condition"]["status"]=="known_none"
    assert (snapshot,d0)==original


@pytest.mark.parametrize("move", sorted(SELF_THAW_MOVES))
def test_self_thaw_catalog_bypasses_natural_rng(move):
    _,_,g=gate("freeze",move=move)
    assert validate_status_gate(g)
    assert len(g["branches"])==1 and g["branches"][0]["kind"]=="self_thaw_move_executes"
    assert fraction(g["branches"][0]["probability"])==1
    assert g["move_authority"]["target_thaw"]=="separate_effect_not_authorized_by_user_gate"


@pytest.mark.parametrize("move",["sleep-talk","snore"])
def test_sleep_exception_handoff(move):
    _,_,g=gate(move=move)
    assert all(b["kind"]=="move_specific_sleep_exception_executes" and b["condition_after"]=="sleep" for b in g["branches"])
    assert validate_status_gate(g)


def test_early_bird_and_suppression():
    _,_,g=gate(ability="early-bird")
    assert all(b["adjusted_duration"]==b["sleep_duration"]//2==1 and b["kind"]=="wakes_and_executes" for b in g["branches"])
    _,_,suppressed=gate(ability="early-bird",opposing_ability="neutralizing-gas")
    assert all(b["kind"]=="cancelled_sleep" and b["adjusted_duration"]==b["sleep_duration"] for b in suppressed["branches"])
    _,_,unknown=gate(ability={"knowledge":"unknown"})
    assert unknown["status"] in {"incomplete", "rejected"} and "branches" not in unknown


@pytest.mark.parametrize("condition",["sleep","freeze"])
def test_missing_progression_and_wrong_identity_fail_closed(condition):
    snapshot,d0,g=gate(condition)
    state=deepcopy(snapshot["state"]);state["self_side"]["pokemon"][0].pop("champions_status_progression")
    snapshot=_snapshot(state);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=g["actor"])
    assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,actor=g["actor"],action_id="a",move_id="tackle",action_order={})["status"]=="incomplete"
    actor={**g["actor"],"pokemon_id":"foreign"}
    assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,action_id="a",move_id="tackle",action_order={})["status"]=="rejected"


@pytest.mark.parametrize("forgery",["probability","third_blocked","move","progression","status_clear","duration"])
def test_forged_gate_rejected(forgery):
    _,_,g=gate("freeze" if forgery in {"probability","third_blocked","move"} else "sleep",prior=2 if forgery=="third_blocked" else 0)
    g=deepcopy(g)
    if forgery=="probability":g["branches"][0]["probability"]={"numerator":1,"denominator":5}
    if forgery=="third_blocked":g["branches"][0]["kind"]="cancelled_freeze"
    if forgery=="move":g["move_authority"]["self_thaw"]=True
    if forgery=="progression":g["progression"]["prior_attempts"]=1
    if forgery=="status_clear":g["branches"][0]["condition_after"]="none"
    if forgery=="duration":g["branches"][0]["sleep_duration"]=3
    assert not validate_status_gate(g)



def pair(condition="sleep", prior=0, duration=None, order="own_first", own_hp=100, move="tackle", ability="pressure", opponent_move="tackle"):
    from tests.test_fixed_two_hit_immediate_move_pair_integration import _fixed_two_action, _order
    from tests.test_detached_opponent_response_profile import _equal_speed_order
    from llm.advisor_runtime_d0_opponent_action_authority import freeze_runtime_d0_opponent_known_move_action_authority
    from llm.advisor_runtime_d0_complete_opponent_response_set_authority import freeze_runtime_d0_complete_opponent_response_set_authority
    from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
    snapshot,d0,owner=inputs(condition,prior=prior,duration=duration,ability=ability)
    state=deepcopy(snapshot["state"]);state["self_side"]["pokemon"][0]["current_hp"]=own_hp
    if opponent_move != "tackle":
        ids = [opponent_move, *MOVES[1:]]
        event = {"observation_id": "responses", "observation_sequence": 2, "planned_effect": "set_current_opponent_response_set", "trust": "user_confirmed_observation", **_owner(state, "opponent"), "move_ids": ids, "move_usability": {m: {"status": "known_usable", "reason": None} for m in ids}, "turn_number": 1}
        projected = project_atomic_transition(state, {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [event]}, state["session_id"])
        assert projected["status"] == "ready_with_projected_state", projected
        state = projected["projected_state"]
    if order=="tie":state["opponent_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"]=100
    snapshot=_snapshot(state);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=owner)
    own=_fixed_two_action(d0,move_id=move)
    own["move_metadata_authority"]["metadata"].pop("min_hits");own["move_metadata_authority"]["metadata"].pop("max_hits")
    if move == "scald": own["move_metadata_authority"]["metadata"].update(type="water", category="special", power=80, target="selected-pokemon", effect_chance=30, ailment="burn")
    known=freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0,runtime_snapshot=snapshot,canonical_move_metadata_authorities={m:_metadata(m) for m in (opponent_move, *MOVES)})
    responses=freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0,runtime_snapshot=snapshot,opponent_known_move_authority=known)
    opponent=next(a for a in responses["actions"] if a["action_id"]==f"opponent_attack:{opponent_move}")
    frozen_order=_equal_speed_order(d0,own,opponent) if order=="tie" else _order(d0,own,opponent,order)
    before=deepcopy((snapshot,d0))
    result=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=frozen_order)
    assert (snapshot,d0)==before
    return result


@pytest.mark.parametrize("condition,prior,duration",[("sleep",0,None),("freeze",0,None),("sleep",1,2),("freeze",2,None)])
def test_pair_cancellation_and_clear_before_attack(condition,prior,duration):
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
    result=pair(condition,prior,duration)
    assert result["status"]=="evaluable",result
    assert result["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    for path in result["terminal_paths"]:
        first=path["actions"][0]
        if first["state"].startswith("cancelled_"):
            assert "attack_leaf" not in first
        else:
            assert first["condition_after"]=="none" and "attack_leaf" in first
        assert path["actions"][1]["state"]=="executes"
    ledger=normalize_exact_immediate_action_pair_outcome_ledger(pair=result)
    assert ledger["status"]=="evaluable",ledger


def test_opponent_ko_prevents_later_attempt_and_equal_speed_composes():
    result=pair("freeze",order="opponent_first",own_hp=1)
    assert result["status"]=="evaluable",result
    assert all(path["actions"][1]["state"]=="cancelled_due_to_faint" and "gate" not in path["actions"][1] for path in result["terminal_paths"])
    result=pair("sleep",order="tie")
    assert result["status"]=="evaluable",result
    assert {p["order"] for p in result["terminal_paths"]}=={"own_first","opponent_first"}
    assert sum((fraction(p["probability"]) for p in result["terminal_paths"]),Fraction())==1

@pytest.mark.parametrize("condition", ["sleep", "freeze"])
def test_switch_out_and_reentry_preserve_pokemon_progression(condition):
    snapshot, d0, owner = inputs(condition, prior=1, duration=3 if condition == "sleep" else None)
    state = deepcopy(snapshot["state"])
    original = deepcopy(state["self_side"]["pokemon"][0]["champions_status_progression"])
    state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0])
    state["self_side"]["pokemon"][1]["pokemon_id"] = "bench-member"
    state["self_side"]["pokemon"][1].pop("champions_status_progression")
    for out_slot, in_slot, out_id, in_id in [(0, 1, owner["pokemon_id"], "bench-member"), (1, 0, "bench-member", owner["pokemon_id"])]:
        event = {"observation_id": f"switch-{in_slot}", "observation_sequence": in_slot+2, "planned_effect": "switch_active", "side": "self", "trust": "user_confirmed_observation", "turn_number": 2,
                 "switch_out_slot_index": out_slot, "switch_in_slot_index": in_slot, "switch_out_pokemon_id": out_id, "switch_in_pokemon_id": in_id}
        result = project_atomic_transition(state, {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [event]}, state["session_id"])
        assert result["status"] == "ready_with_projected_state", result
        state = result["projected_state"]
        assert state["self_side"]["pokemon"][0]["champions_status_progression"] == original
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    result = freeze(strategy_d0=d0, runtime_snapshot=snapshot, actor=owner, action_id="a", move_id="tackle", action_order={})
    assert result["status"] == "resolved", result
    assert all(b["attempt"] == 2 for b in result["branches"])


@pytest.mark.parametrize("field,value", [("prior_attempts", 0), ("sleep_duration", 2), ("origin_id", "new-origin"), ("turn_number", 0)])
def test_observer_rejects_decrease_stale_origin_and_duration_reroll(field, value):
    snapshot, _, owner = inputs(prior=1, duration=3)
    state = snapshot["state"]
    before = deepcopy(state)
    event = {"observation_id": "bad", "observation_sequence": 2, "planned_effect": "record_champions_status_progression", "trust": "user_confirmed_observation", **owner,
             "condition": "sleep", "origin_id": "status:origin:1", "established_turn": 1, "prior_attempts": 1, "sleep_duration": 3, "turn_number": 1, field: value}
    result = project_atomic_transition(state, {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [event]}, state["session_id"])
    assert result["status"] != "ready_with_projected_state"
    assert state == before


def test_new_condition_observation_invalidates_old_progression():
    snapshot, _, owner = inputs()
    state = deepcopy(snapshot["state"])
    state["self_side"]["pokemon"][0]["condition_provenance"]["turn_number"] = 2
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    assert freeze(strategy_d0=d0, runtime_snapshot=snapshot, actor=owner, action_id="a", move_id="tackle", action_order={})["status"] == "rejected"


def test_duration_adjustment_persists_when_suppression_later_changes():
    snapshot, d0, g = gate(ability="early-bird", opposing_ability="neutralizing-gas")
    branch = g["branches"][1]
    view = materialize(strategy_d0=d0, runtime_snapshot=snapshot, authority=g, branch=branch)
    state = deepcopy(view["runtime_snapshot"]["state"])
    state["opponent_side"]["pokemon"][0]["current_ability"] = "pressure"
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=g["actor"])
    nxt = freeze(strategy_d0=d0, runtime_snapshot=snapshot, actor=g["actor"], action_id="next", move_id="tackle", action_order={})
    assert nxt["branches"][0]["adjusted_duration"] == 3
    assert nxt["branches"][0]["kind"] == "cancelled_sleep"
    assert nxt["branches"][0]["duration_adjustment"]["suppressed"] is True


@pytest.mark.parametrize("condition,prior", [("sleep", 1), ("freeze", 2)])
def test_cleared_condition_reaches_guts_and_facade_existing_attack_owners(condition, prior):
    result = pair(condition, prior=prior, duration=2 if condition == "sleep" else None, ability="guts", move="facade")
    baseline = pair(condition, prior=prior, duration=2 if condition == "sleep" else None, ability="pressure", move="facade")
    assert result["status"] == baseline["status"] == "evaluable", result
    def damage_rows(value):
        return sorted((p["actions"][0]["attack_leaf"]["consequences"]["target_final_hp"], fraction(p["probability"])) for p in value["terminal_paths"])
    assert damage_rows(result) == damage_rows(baseline)
    assert all(p["actions"][0]["detached_after_state"]["self_side"]["pokemon"][0]["condition"] == "none" for p in result["terminal_paths"])


def test_early_bird_wake_executes_in_actual_pair():
    result = pair(ability="early-bird")
    assert result["status"] == "evaluable", result
    assert all(p["actions"][0]["state"] == "wakes_and_executes" and "attack_leaf" in p["actions"][0] for p in result["terminal_paths"])


def test_self_thaw_handoff_clears_before_existing_move_support_check(monkeypatch):
    import llm.advisor_immediate_move_vs_move_action_pair as owner
    native = owner._attack_ledger
    seen = []
    def observe(**kwargs):
        actor = kwargs["actor"]
        raw = kwargs["runtime_snapshot"]["state"][f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]
        seen.append(raw["condition"])
        return native(**kwargs)
    monkeypatch.setattr(owner, "_attack_ledger", observe)
    result = pair("freeze", move="scald")
    assert seen == ["none"]
    # This gate does not promote an unsupported secondary-effect/damage family.
    assert result["status"] == "unsupported"
    assert result["reason"] == "move_not_in_supported_critical_hit_catalog"


@pytest.fixture(scope="module")
def cancelled_pair():
    result = pair()
    assert result["status"] == "evaluable"
    return result


@pytest.mark.parametrize("forgery", ["attack_on_cancel", "status_clear", "actor", "action", "path", "order", "final_hp", "second_state", "runtime", "duration", "ability", "move_exception"])
def test_pair_ledger_rejects_tampered_provenance(cancelled_pair, forgery):
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger as normalize
    result = deepcopy(cancelled_pair)
    path = result["terminal_paths"][0]
    event = path["actions"][0]
    if forgery == "attack_on_cancel": event["attack_leaf"] = deepcopy(path["actions"][1]["attack_leaf"])
    elif forgery == "status_clear": event["detached_after_state"]["self_side"]["pokemon"][0]["condition"] = "none"
    elif forgery == "actor": event["actor"]["pokemon_id"] = "foreign"
    elif forgery == "action": event["action_id"] = "foreign"
    elif forgery == "path": event["gate"]["path"] = ("foreign",)
    elif forgery == "order": path["order_probability"] = {"numerator": 1, "denominator": 2}
    elif forgery == "final_hp": path["final_hp"]["self"] += 1
    elif forgery == "second_state": path["actions"][1]["detached_before_state"]["self_side"]["pokemon"][0]["current_hp"] -= 1
    elif forgery == "runtime": event["gate"]["source_runtime_fingerprint"] = "foreign"
    elif forgery == "duration": event["gate"]["progression"]["sleep_duration"] = 2
    elif forgery == "ability": event["gate"]["ability_authority"]["ability_id"] = "early-bird"
    elif forgery == "move_exception": event["gate"]["move_authority"]["sleep_exception"] = True
    assert normalize(pair=result)["status"] == "rejected"


def test_typed_ledger_remains_usable_by_existing_descriptive_metrics(cancelled_pair):
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
    from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=cancelled_pair)
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
    assert metrics["status"] == "resolved", metrics
    assert metrics["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all("attack_leaf" not in leaf["first_action"] for leaf in ledger["terminal_leaves"])


def test_flinch_cancels_pending_status_attempt_through_existing_owner():
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
    result = pair("sleep", order="opponent_first", opponent_move="iron-head")
    assert result["status"] == "evaluable", result
    flinched = [p for p in result["terminal_paths"] if p["actions"][1]["state"] == "cancelled_due_to_flinch"]
    assert flinched and all("gate" not in p["actions"][1] for p in flinched)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=result)["status"] == "evaluable"


def test_target_thaw_stays_distinct_and_unbound_extensions_fail_closed(cancelled_pair):
    from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
    target = pair("freeze", order="opponent_first", opponent_move="flame-charge")
    assert target["status"] == "incomplete" and target["reason"] == "target_thaw_effect_authority_required"
    request = deepcopy(cancelled_pair["validation_request"])
    request["first_action_sturdy_survival_authority"] = {"status": "resolved"}
    result = materialize_immediate_move_vs_move_action_pair(**request)
    assert result["status"] == "incomplete" and result["reason"] == "champions_status_pair_extension_binding_required"


def test_freeze_survival_path_composes_without_probability_loss():
    snapshot, d0, g = gate("freeze")
    weights = []
    surviving = Fraction(1)
    for attempt in (1, 2, 3):
        assert g["branches"][0]["attempt"] == attempt
        weights.append(surviving * fraction(g["branches"][0]["probability"]))
        if attempt < 3:
            cancelled = g["branches"][1]
            surviving *= fraction(cancelled["probability"])
            view = materialize(strategy_d0=d0, runtime_snapshot=snapshot, authority=g, branch=cancelled)
            snapshot, d0 = view["runtime_snapshot"], view["strategy_d0"]
            g = freeze(strategy_d0=d0, runtime_snapshot=snapshot, actor=g["actor"], action_id=f"attempt-{attempt+1}", move_id="tackle", action_order={}, path=(cancelled["branch_id"],))
    assert weights == [Fraction(1, 4), Fraction(3, 16), Fraction(9, 16)]
    assert sum(weights) == 1


@pytest.mark.parametrize("condition", ["sleep", "freeze"])
def test_equal_speed_status_paths_validate_and_ko_does_not_attempt(condition):
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
    result = pair(condition, order="tie", own_hp=1)
    assert result["status"] == "evaluable", result
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=result)["status"] == "evaluable"
    for path in result["terminal_paths"]:
        if path["order"] == "opponent_first":
            assert path["actions"][1]["state"] == "cancelled_due_to_faint"
            assert "gate" not in path["actions"][1]


def test_wake_then_thunderbolt_preserves_existing_second_action_paralysis():
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
    result = pair("sleep", prior=1, duration=2, move="thunderbolt")
    assert result["status"] == "evaluable", result
    cancelled = [p for p in result["terminal_paths"] if p["actions"][1]["state"] == "cancelled_due_to_paralysis"]
    assert sum((fraction(p["probability"]) for p in cancelled), Fraction()) == Fraction(1, 40)
    assert all("attack_leaf" not in p["actions"][1] for p in cancelled)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=result)["status"] == "evaluable"
