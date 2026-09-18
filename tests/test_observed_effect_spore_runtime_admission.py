"""Actual observed Effect Spore outcomes use the shared contact transaction."""
from copy import deepcopy

import pytest

from llm.advisor_observed_contact_reactive_status_runtime_admission import (
    _confirmations, _payload, admit_observed_contact_reactive_status_result,
)
from llm.advisor_lifecycle_confirmation import CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from tests.test_observed_contact_reactive_status_runtime_admission import _runtime_manager


def _admit(manager, *, outcome="sleep", action="action:spore", attacker_side="self", hp_after=90):
    return admit_observed_contact_reactive_status_result(
        runtime_session_manager=manager, captured_session_id="contact-runtime", attacker_side=attacker_side,
        move_id="tackle", source_action_id=action, target_hp_after=hp_after, outcome=outcome, turn_number=2,
    )


def _owners(attacker_side="self"):
    defender_side = "opponent" if attacker_side == "self" else "self"
    return ({"session_id":"contact-runtime","side":attacker_side,"slot_index":0,"pokemon_id":f"{attacker_side}-a"}, {"session_id":"contact-runtime","side":defender_side,"slot_index":0,"pokemon_id":f"{defender_side}-a"})


def _seed(manager, *, outcome="sleep", action="action:seed", hp_after=90, rows=None, mutate=None):
    attacker, defender = _owners(); payload = _payload(attacker, defender, action, "tackle", "effect-spore", outcome, 100, hp_after)
    confirmations = _confirmations("contact-runtime", attacker, defender, payload, 2, True)
    assert confirmations is not None
    for row in confirmations: row["observation"]["observation_sequence"] = manager.allocate_observation_sequence()["observation_sequence"]
    if mutate: mutate(confirmations)
    selected = confirmations if rows is None else [row for row in confirmations if row["observation"]["event_kind"] in rows]
    assert manager.admit_confirmations_atomically("contact-runtime", selected)["status"] == "added"


@pytest.mark.parametrize("outcome", ["sleep", "paralysis", "poison", "none"])
def test_each_explicit_effect_spore_outcome_commits_non_ko(outcome):
    manager = _runtime_manager("effect-spore"); before = deepcopy(manager.read_state()["state"]["self_side"]["pokemon"][0])
    result = _admit(manager, outcome=outcome, action=f"action:{outcome}")
    assert result["status"] == "resolved" and result["strategy_d0"]["status"] == "resolved"
    actor = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert actor["condition"] == (None if outcome == "none" else outcome)
    assert any(row["event_kind"] == "current_condition_observed" for row in result["observations"]) is (outcome != "none")
    if outcome == "none": assert actor["condition_provenance"] == before["condition_provenance"]


def test_effect_spore_is_side_neutral_and_ko_is_atomic_without_fresh_d0():
    manager = _runtime_manager("pressure", self_ability="effect-spore")
    result = _admit(manager, attacker_side="opponent", outcome="sleep", action="action:opponent-ko", hp_after=0)
    assert result["status"] == "resolved" and result["strategy_d0"] is None and result["replacement_boundary"]["status"] == "replacement_required_after_faint"
    rows = result["observations"]; hp = next(row for row in rows if row["event_kind"] == "exact_hp_transition_observed"); faint = next(row for row in rows if row["event_kind"] == "pokemon_faint_observed")
    assert sum(row["event_kind"] == "exact_hp_transition_observed" for row in rows) == 1 and hp["observation_sequence"] < faint["observation_sequence"]
    state = manager.read_state()["state"]; defender = state["self_side"]["pokemon"][0]
    assert defender["current_hp"] == 0 and defender["fainted"] is True and state["opponent_side"]["pokemon"][0]["condition"] == "sleep"


def test_effect_spore_none_ko_has_no_condition_and_exact_retry_is_idempotent():
    manager = _runtime_manager("effect-spore")
    first = _admit(manager, outcome="none", action="action:none-ko", hp_after=0)
    assert first["status"] == "resolved" and first["strategy_d0"] is None
    assert not any(row["event_kind"] == "current_condition_observed" for row in first["observations"])
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    retry = _admit(manager, outcome="none", action="action:none-ko", hp_after=0)
    assert retry["status"] == "resolved" and retry["idempotent"] is True and retry["reason"] == "idempotent_reuse"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


@pytest.mark.parametrize("outcome, rows", [
    ("sleep", {"executed_move_observed", "contact_reactive_status_result_observed", "exact_hp_transition_observed"}),
    ("none", {"executed_move_observed", "contact_reactive_status_result_observed", "exact_hp_transition_observed", "current_condition_observed"}),
    ("sleep", {"executed_move_observed", "contact_reactive_status_result_observed", "current_condition_observed"}),
    ("sleep", {"executed_move_observed", "contact_reactive_status_result_observed", "exact_hp_transition_observed", "current_condition_observed"}),
])
def test_partial_or_unexpected_effect_spore_history_rejects_without_repair(outcome, rows):
    manager = _runtime_manager("effect-spore"); _seed(manager, outcome=outcome, action="action:partial", hp_after=0 if outcome == "sleep" and "pokemon_faint_observed" not in rows else 90, rows=rows)
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    result = _admit(manager, outcome=outcome, action="action:partial", hp_after=0 if outcome == "sleep" and "pokemon_faint_observed" not in rows else 90)
    assert result["status"] == "rejected" and manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


def test_wrong_condition_and_complete_uncommitted_history_reject():
    manager = _runtime_manager("effect-spore")
    _seed(manager, outcome="sleep", action="action:wrong", mutate=lambda rows: next(row for row in rows if row["observation"]["event_kind"] == "current_condition_observed")["observation"]["payload"].update(condition="poison"))
    assert _admit(manager, outcome="sleep", action="action:wrong")["status"] == "rejected"
    manager = _runtime_manager("effect-spore"); _seed(manager, outcome="sleep", action="action:uncommitted", hp_after=0)
    assert _admit(manager, outcome="sleep", action="action:uncommitted", hp_after=0)["status"] == "rejected"


def test_none_history_with_unexpected_condition_and_ko_missing_only_faint_reject():
    manager = _runtime_manager("effect-spore"); _seed(manager, outcome="none", action="action:none-extra")
    attacker, _defender = _owners(); extra = LifecycleConfirmationBoundary("contact-runtime", {"self": attacker}).confirm(
        event_kind="current_condition_observed", payload={"condition":"sleep"}, session_id="contact-runtime",
        source=CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side="self",
        slot_index=0, pokemon_id="self-a", observation_id="contact-runtime:contact-reactive:action:none-extra:condition", turn_number=2,
    )
    extra["observation"]["observation_sequence"] = manager.allocate_observation_sequence()["observation_sequence"]
    assert manager.admit_confirmation("contact-runtime", extra)["status"] == "added"
    assert _admit(manager, outcome="none", action="action:none-extra")["status"] == "rejected"

    manager = _runtime_manager("effect-spore")
    _seed(manager, outcome="sleep", action="action:missing-faint", hp_after=0, rows={"executed_move_observed", "contact_reactive_status_result_observed", "exact_hp_transition_observed", "current_condition_observed"})
    assert _admit(manager, outcome="sleep", action="action:missing-faint", hp_after=0)["status"] == "rejected"


@pytest.mark.parametrize(("self_type", "self_ability", "self_item"), [("grass", "pressure", None), ("normal", "overcoat", None), ("normal", "pressure", "safety-goggles")])
def test_known_effect_spore_immunity_resolves_none_without_admission(self_type, self_ability, self_item):
    manager = _runtime_manager("effect-spore", self_ability=self_ability, self_type=self_type, self_item=self_item)
    before_state, before_collection = manager.read_state(), manager.read_collection_snapshot()
    result = _admit(manager, outcome="none", action="action:immune")
    assert result["status"] == "resolved" and result["observations"] == []
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection
    assert _admit(manager, outcome="sleep", action="action:immune-condition")["status"] == "rejected"


@pytest.mark.parametrize("manager", [
    lambda: _runtime_manager("effect-spore", self_type=None),
    lambda: _runtime_manager("effect-spore", self_item="unknown"),
    lambda: _runtime_manager(None),
])
def test_unknown_effect_spore_authority_is_incomplete(manager):
    result = _admit(manager(), outcome="sleep", action="action:unknown")
    assert result["status"] == "incomplete"


def test_outcome_specific_prevention_and_existing_major_status_reject_transition():
    manager = _runtime_manager("effect-spore", self_ability="limber")
    assert _admit(manager, outcome="paralysis", action="action:limber")["status"] == "rejected"
    manager = _runtime_manager("effect-spore")
    first = _admit(manager, outcome="sleep", action="action:first")
    assert first["status"] == "resolved"
    assert _admit(manager, outcome="poison", action="action:already")["status"] == "rejected"
