"""Focused contract coverage for observed contact-reactive receipts."""
import pytest

from llm.advisor_lifecycle_confirmation import (
    CONTACT_REACTIVE_STATUS_RESULT_SOURCE, CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE, EXECUTED_MOVE_SOURCE, HP_TRANSITION_SOURCE, USER_TRUST, LifecycleConfirmationBoundary,
)
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_observed_contact_reactive_status_runtime_admission import admit_observed_contact_reactive_status_result
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0, runtime_strategy_d0_freshness
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation


def _owner(side, pokemon):
    return {"session_id": "s", "side": side, "slot_index": 0, "pokemon_id": pokemon}


def _receipt(*, ability="static", outcome="activation", after=90):
    owner = _owner("opponent", "eevee")
    return LifecycleConfirmationBoundary("s", {"opponent": owner}).confirm(
        event_kind="contact_reactive_status_result_observed",
        payload={"source_action_id": "action:tackle", "move_id": "tackle",
                 "reactive_ability": ability, "outcome": outcome,
                 "attacker_side": "self", "attacker_slot_index": 0, "attacker_pokemon_id": "pikachu",
                 "defender_side": "opponent", "defender_slot_index": 0, "defender_pokemon_id": "eevee",
                 "hp_before": 100, "hp_after": after},
        session_id="s", source=CONTACT_REACTIVE_STATUS_RESULT_SOURCE, trust=USER_TRUST,
        confirmed=True, side="opponent", slot_index=0, pokemon_id="eevee",
        observation_id="s:contact-reactive:action:tackle:result", turn_number=1,
    )


@pytest.mark.parametrize("ability", ["static", "flame-body", "poison-point"])
@pytest.mark.parametrize("outcome", ["activation", "no_activation"])
def test_supported_receipts_are_production_evidence_only(ability, outcome):
    result = _receipt(ability=ability, outcome=outcome)
    assert result["status"] == "confirmed"
    row = result["observation"]
    assert row["reducer_eligibility"] == "evidence_only"
    collection = ObservationCollection("s")
    row["observation_sequence"] = 1
    assert collection.add_confirmation_result(result)["status"] == "added"
    plan = build_replay_plan({"session_id": "s"}, collection.snapshot()["ordered_observations"])
    assert plan["accepted_events"] == [] and plan["evidence_only_events"] == [row]


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(reactive_ability="effect-spore"),
    lambda p: p.update(outcome="unknown"),
    lambda p: p.update(hp_after=100),
    lambda p: p.update(move_id="Bad Move"),
])
def test_receipt_payload_fails_closed(mutate):
    result = _receipt()
    payload = result["observation"]["payload"]; mutate(payload)
    owner = _owner("opponent", "eevee")
    retry = LifecycleConfirmationBoundary("s", {"opponent": owner}).confirm(
        event_kind="contact_reactive_status_result_observed", payload=payload,
        session_id="s", source=CONTACT_REACTIVE_STATUS_RESULT_SOURCE, trust=USER_TRUST,
        confirmed=True, side="opponent", slot_index=0, pokemon_id="eevee", turn_number=1,
    )
    assert retry["status"] == "invalid_provenance"


def _runtime_manager(ability="static", self_ability="pressure", self_type="normal", self_item=None):
    state = create_unknown_bootstrap_battle_state("contact-runtime", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    steps = []; sequence = 0
    for side, pokemon, types, current_ability in (("self", "self-a", [self_type] if self_type else None, self_ability), ("opponent", "opponent-a", ["normal"], ability)):
        facts = [("set_current_condition", {"condition": "none"})]
        if types is not None: facts.append(("set_current_type", {"types": types}))
        if current_ability is not None: facts.append(("set_current_ability", {"ability": current_ability}))
        if side != "self" or self_item != "unknown": facts.append(("set_current_item", {"status": "known", "item": self_item} if side == "self" and self_item else {"status": "known_absent"}))
        for effect, data in facts:
            sequence += 1; steps.append({"observation_id":f"x:{sequence}","observation_sequence":sequence,"planned_effect":effect,"trust":"user_confirmed_observation","turn_number":1,"side":side,"slot_index":0,"pokemon_id":pokemon,**data})
    projected = project_atomic_transition(state, {"session_id":"contact-runtime","status":"planned","conflicts":[],"ordered_steps":steps}, "contact-runtime")["projected_state"]
    return BattleObservationRuntimeSessionManager.create("contact-runtime", projected)["manager"]


@pytest.mark.parametrize(("ability", "outcome", "condition"), [("static","activation","paralysis"),("static","no_activation",None),("flame-body","activation","burn"),("flame-body","no_activation",None),("poison-point","activation","poison"),("poison-point","no_activation",None)])
def test_production_owner_commits_simple_family(ability, outcome, condition):
    manager = _runtime_manager(ability)
    result = admit_observed_contact_reactive_status_result(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:tackle", target_hp_after=90, outcome=outcome, turn_number=2)
    assert result["status"] == "resolved", result
    state = manager.read_state()["state"]
    assert state["opponent_side"]["pokemon"][0]["current_hp"] == 90
    assert state["self_side"]["pokemon"][0]["condition"] == condition
    kinds = [x["event_kind"] for x in result["observations"]]
    assert "contact_reactive_status_result_observed" in kinds and "exact_hp_transition_observed" in kinds
    assert ("current_condition_observed" in kinds) is (outcome == "activation")


@pytest.mark.parametrize(("ability", "outcome"), [("static", "activation"), ("static", "no_activation"), ("flame-body", "activation")])
def test_production_retry_is_idempotent(ability, outcome):
    manager = _runtime_manager(ability)
    kwargs = dict(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:retry", target_hp_after=90, outcome=outcome, turn_number=2)
    assert admit_observed_contact_reactive_status_result(**kwargs)["status"] == "resolved"
    before = manager.read_collection_snapshot(); state = manager.read_state()
    retry = admit_observed_contact_reactive_status_result(**kwargs)
    assert retry["status"] == "resolved" and retry["idempotent"] is True
    assert manager.read_collection_snapshot() == before and manager.read_state() == state


@pytest.mark.parametrize("change", [{"outcome":"no_activation"},{"move_id":"scratch"},{"target_hp_after":89}])
def test_production_conflicting_retry_rejects_without_mutation(change):
    manager = _runtime_manager()
    kwargs = dict(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:conflict", target_hp_after=90, outcome="activation", turn_number=2)
    assert admit_observed_contact_reactive_status_result(**kwargs)["status"] == "resolved"
    before = manager.read_state(); kwargs.update(change)
    assert admit_observed_contact_reactive_status_result(**kwargs)["status"] == "rejected"
    assert manager.read_state() == before


def test_ko_is_composed_with_the_required_faint_lifecycle():
    manager = _runtime_manager()
    result = admit_observed_contact_reactive_status_result(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:ko", target_hp_after=0, outcome="activation", turn_number=2)
    assert result["status"] == "resolved" and result["strategy_d0"] is None
    assert [row["event_kind"] for row in result["observations"]] == ["executed_move_observed", "contact_reactive_status_result_observed", "exact_hp_transition_observed", "pokemon_faint_observed", "current_condition_observed"]


def test_no_activation_preserves_canonical_condition_and_provenance():
    manager = _runtime_manager(); before = manager.read_state()["state"]["self_side"]["pokemon"][0]
    condition, provenance = before["condition"], before["condition_provenance"]
    result = admit_observed_contact_reactive_status_result(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:preserve", target_hp_after=90, outcome="no_activation", turn_number=2)
    actor = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert result["status"] == "resolved" and actor["condition"] == condition and actor["condition_provenance"] == provenance
    assert not any(x["observation_id"].endswith(":condition") for x in manager.read_collection_snapshot()["ordered_observations"])


def test_production_owner_is_side_neutral_for_opponent_attacker():
    manager = _runtime_manager(self_ability="static")
    result = admit_observed_contact_reactive_status_result(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="opponent", move_id="tackle", source_action_id="action:opponent", target_hp_after=90, outcome="activation", turn_number=2)
    assert result["status"] == "resolved", result
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["current_hp"] == 90
    assert state["opponent_side"]["pokemon"][0]["condition"] == "paralysis"
    receipt = next(x for x in result["observations"] if x["event_kind"] == "contact_reactive_status_result_observed")
    assert receipt["payload"]["attacker_side"] == "opponent" and receipt["payload"]["defender_side"] == "self"


def test_non_ko_result_returns_fresh_d0_with_exact_runtime_binding():
    manager = _runtime_manager(); before = manager.capture_runtime_state_snapshot("contact-runtime")
    owner = {"session_id":"contact-runtime","side":"self","slot_index":0,"pokemon_id":"self-a"}
    old = freeze_runtime_strategy_d0(runtime_snapshot=before, decision_owner=owner)
    result = admit_observed_contact_reactive_status_result(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:fresh", target_hp_after=90, outcome="no_activation", turn_number=2)
    assert result["status"] == "resolved"
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    assert runtime_strategy_d0_freshness(strategy_d0=old, runtime_snapshot=result["runtime_snapshot"])["status"] != "current"


def test_compatible_historical_execution_is_reused():
    manager = _runtime_manager()
    existing = admit_previous_action_history_observation(runtime_session_manager=manager, captured_session_id="contact-runtime", side="self", execution_move_id="tackle", selected_move_id="tackle", source_action_id="action:existing", result_class=None, turn_number=2)
    assert existing["status"] == "resolved"
    result = admit_observed_contact_reactive_status_result(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:existing", target_hp_after=90, outcome="activation", turn_number=2)
    rows = manager.read_collection_snapshot()["ordered_observations"]
    assert result["status"] == "resolved" and len([x for x in rows if x["event_kind"] == "executed_move_observed"]) == 1


def test_conflicting_historical_execution_rejects_before_mutation():
    manager = _runtime_manager()
    assert admit_previous_action_history_observation(runtime_session_manager=manager, captured_session_id="contact-runtime", side="self", execution_move_id="scratch", selected_move_id="scratch", source_action_id="action:existing", result_class=None, turn_number=2)["status"] == "resolved"
    before, collection = manager.read_state(), manager.read_collection_snapshot()
    result = admit_observed_contact_reactive_status_result(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:existing", target_hp_after=90, outcome="activation", turn_number=2)
    assert result["status"] == "rejected" and manager.read_state() == before and manager.read_collection_snapshot() == collection


@pytest.mark.parametrize("changes", [
    {"move_id":"growl"}, {"target_hp_after":100}, {"target_hp_after":101},
    {"target_hp_after":True}, {"move_id":"Bad Move"}, {"source_action_id":"bad action"},
    {"turn_number":0}, {"captured_session_id":"stale"},
])
def test_production_adapter_fail_closed_without_mutation(changes):
    manager = _runtime_manager()
    kwargs = {"runtime_session_manager":manager,"captured_session_id":"contact-runtime","attacker_side":"self","move_id":"tackle","source_action_id":"action:closed","target_hp_after":90,"outcome":"activation","turn_number":2}
    kwargs.update(changes); before, collection = manager.read_state(), manager.read_collection_snapshot()
    result = admit_observed_contact_reactive_status_result(**kwargs)
    assert result["status"] in {"rejected", "incomplete"}
    assert manager.read_state() == before and manager.read_collection_snapshot() == collection


@pytest.mark.parametrize(("ability", "self_type", "self_ability", "reason"), [
    ("static", "electric", "pressure", "attacker_electric_type_immune"),
    ("flame-body", "fire", "pressure", "attacker_fire_type_immune"),
    ("poison-point", "poison", "pressure", "attacker_poison_or_steel_type_immune"),
    ("poison-point", "steel", "pressure", "attacker_poison_or_steel_type_immune"),
    ("static", "normal", "limber", "attacker_limber_prevents_paralysis"),
    ("pressure", "normal", "pressure", "observed_contact_status_ineligible"),
])
def test_known_eligibility_blockers_resolve_without_admission(ability, self_type, self_ability, reason):
    manager = _runtime_manager(ability, self_ability=self_ability, self_type=self_type)
    before, collection = manager.read_state(), manager.read_collection_snapshot()
    result = admit_observed_contact_reactive_status_result(runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side="self", move_id="tackle", source_action_id="action:ineligible", target_hp_after=90, outcome="activation", turn_number=2)
    assert result["status"] == "resolved" and result["reason"] == reason and result["observations"] == []
    assert manager.read_state() == before and manager.read_collection_snapshot() == collection


@pytest.mark.parametrize(("with_hp", "condition"), [(False, None), (True, None), (True, "burn")])
def test_corrupt_historical_receipt_is_never_repaired(with_hp, condition):
    manager = _runtime_manager(); action = "action:corrupt"
    attacker = {"session_id":"contact-runtime","side":"self","slot_index":0,"pokemon_id":"self-a"}
    defender = {"session_id":"contact-runtime","side":"opponent","slot_index":0,"pokemon_id":"opponent-a"}
    boundary = LifecycleConfirmationBoundary("contact-runtime", {"self":attacker,"opponent":defender})
    payload = {"source_action_id":action,"move_id":"tackle","reactive_ability":"static","outcome":"activation","attacker_side":"self","attacker_slot_index":0,"attacker_pokemon_id":"self-a","defender_side":"opponent","defender_slot_index":0,"defender_pokemon_id":"opponent-a","hp_before":100,"hp_after":90}
    rows = [
        boundary.confirm(event_kind="executed_move_observed",payload={"move_id":"tackle","source_action_id":action},session_id="contact-runtime",source=EXECUTED_MOVE_SOURCE,trust=USER_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="self-a",observation_id=f"contact-runtime:contact-reactive:{action}:execution",turn_number=2),
        boundary.confirm(event_kind="contact_reactive_status_result_observed",payload=payload,session_id="contact-runtime",source=CONTACT_REACTIVE_STATUS_RESULT_SOURCE,trust=USER_TRUST,confirmed=True,side="opponent",slot_index=0,pokemon_id="opponent-a",observation_id=f"contact-runtime:contact-reactive:{action}:result",turn_number=2)]
    if with_hp: rows.append(boundary.confirm(event_kind="exact_hp_transition_observed",payload={"hp_before":100,"hp_after":90},session_id="contact-runtime",source=HP_TRANSITION_SOURCE,trust=USER_TRUST,confirmed=True,side="opponent",slot_index=0,pokemon_id="opponent-a",observation_id=f"contact-runtime:contact-reactive:{action}:hp",turn_number=2))
    if condition: rows.append(boundary.confirm(event_kind="current_condition_observed",payload={"condition":condition},session_id="contact-runtime",source=CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE,trust=USER_TRUST,confirmed=True,side="self",slot_index=0,pokemon_id="self-a",observation_id=f"contact-runtime:contact-reactive:{action}:condition",turn_number=2))
    for row in rows:
        seq=manager.allocate_observation_sequence()["observation_sequence"]; row["observation"]["observation_sequence"]=seq; assert manager.admit_confirmation("contact-runtime",row)["status"]=="added"
    state, collection = manager.read_state(), manager.read_collection_snapshot()
    result=admit_observed_contact_reactive_status_result(runtime_session_manager=manager,captured_session_id="contact-runtime",attacker_side="self",move_id="tackle",source_action_id=action,target_hp_after=90,outcome="activation",turn_number=2)
    assert result["status"]=="rejected" and manager.read_state()==state and manager.read_collection_snapshot()==collection
