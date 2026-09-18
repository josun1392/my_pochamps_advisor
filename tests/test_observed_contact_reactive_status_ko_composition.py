"""KO-only composition contracts for contact-reactive status receipts."""
from copy import deepcopy

import pytest

from llm.advisor_observed_contact_reactive_status_runtime_admission import (
    _confirmations, _payload, admit_observed_contact_reactive_status_result,
)
from tests.test_observed_contact_reactive_status_runtime_admission import _runtime_manager


def _admit(manager, *, attacker_side="self", ability="static", outcome="activation", action="action:ko"):
    return admit_observed_contact_reactive_status_result(
        runtime_session_manager=manager, captured_session_id="contact-runtime",
        attacker_side=attacker_side, move_id="tackle", source_action_id=action,
        target_hp_after=0, outcome=outcome, turn_number=2,
    )


def _owners(attacker_side="self"):
    defender_side = "opponent" if attacker_side == "self" else "self"
    return (
        {"session_id": "contact-runtime", "side": attacker_side, "slot_index": 0, "pokemon_id": f"{attacker_side}-a"},
        {"session_id": "contact-runtime", "side": defender_side, "slot_index": 0, "pokemon_id": f"{defender_side}-a"},
    )


def _seed(manager, *, outcome="activation", action="action:seed", rows=None, mutate=None):
    attacker, defender = _owners()
    payload = _payload(attacker, defender, action, "tackle", "static", outcome, 100, 0)
    confirmations = _confirmations("contact-runtime", attacker, defender, payload, 2, True)
    assert confirmations is not None
    for confirmation in confirmations:
        confirmation["observation"]["observation_sequence"] = manager.allocate_observation_sequence()["observation_sequence"]
    if mutate:
        mutate(confirmations)
    selected = confirmations if rows is None else [confirmation for confirmation in confirmations if confirmation["observation"]["event_kind"] in rows]
    assert manager.admit_confirmations_atomically("contact-runtime", selected)["status"] == "added"
    return confirmations


@pytest.mark.parametrize(("ability", "outcome", "condition"), [
    ("static", "activation", "paralysis"), ("static", "no_activation", None),
    ("flame-body", "activation", "burn"), ("poison-point", "activation", "poison"),
])
def test_supported_ko_results_commit_one_hp_then_faint_and_status(ability, outcome, condition):
    manager = _runtime_manager(ability)
    before_actor = deepcopy(manager.read_state()["state"]["self_side"]["pokemon"][0])
    result = _admit(manager, ability=ability, outcome=outcome, action=f"action:{ability}:{outcome.replace('_', '')}")
    assert result["status"] == "resolved" and result["strategy_d0"] is None and result["replacement_boundary"]["status"] == "replacement_required_after_faint"
    rows = result["observations"]
    hp = next(row for row in rows if row["event_kind"] == "exact_hp_transition_observed")
    faint = next(row for row in rows if row["event_kind"] == "pokemon_faint_observed")
    assert sum(row["event_kind"] == "exact_hp_transition_observed" for row in rows) == 1
    assert hp["observation_sequence"] < faint["observation_sequence"] and faint["related_observation_id"] == hp["observation_id"]
    defender = manager.read_state()["state"]["opponent_side"]["pokemon"][0]
    actor = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert defender["current_hp"] == 0 and defender["fainted"] is True
    assert (defender["current_hp_provenance"]["source_observation_id"], defender["current_hp_provenance"]["source_sequence"]) == (hp["observation_id"], hp["observation_sequence"])
    assert (defender["fainted_provenance"]["source_observation_id"], defender["fainted_provenance"]["source_sequence"]) == (faint["observation_id"], faint["observation_sequence"])
    assert actor["condition"] == condition
    if outcome == "no_activation":
        assert actor["condition_provenance"] == before_actor["condition_provenance"]


def test_opponent_to_self_ko_is_side_neutral():
    manager = _runtime_manager(self_ability="static")
    result = _admit(manager, attacker_side="opponent", action="action:opponent-ko")
    assert result["status"] == "resolved" and result["owner"]["side"] == "self" and result["strategy_d0"] is None
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["current_hp"] == 0 and state["self_side"]["pokemon"][0]["fainted"] is True
    assert state["opponent_side"]["pokemon"][0]["condition"] == "paralysis"


def test_exact_ko_retry_reuses_full_committed_transaction_without_mutation():
    manager = _runtime_manager()
    first = _admit(manager, action="action:retry")
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    retry = _admit(manager, action="action:retry")
    assert retry["status"] == "resolved" and retry["reason"] == "idempotent_reuse" and retry["idempotent"] is True
    assert retry["strategy_d0"] is None and retry["replacement_boundary"] == first["replacement_boundary"]
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


@pytest.mark.parametrize("rows", [
    {"executed_move_observed", "contact_reactive_status_result_observed", "exact_hp_transition_observed", "current_condition_observed"},
    {"executed_move_observed", "contact_reactive_status_result_observed", "pokemon_faint_observed", "current_condition_observed"},
    {"executed_move_observed", "contact_reactive_status_result_observed", "exact_hp_transition_observed", "pokemon_faint_observed"},
])
def test_partial_ko_history_is_rejected_without_repair(rows):
    manager = _runtime_manager(); _seed(manager, action="action:partial", rows=rows)
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    assert _admit(manager, action="action:partial")["status"] == "rejected"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


@pytest.mark.parametrize("mutate", [
    lambda rows: next(row for row in rows if row["observation"]["event_kind"] == "pokemon_faint_observed")["observation"].update(related_observation_id="forged"),
    lambda rows: next(row for row in rows if row["observation"]["event_kind"] == "pokemon_faint_observed")["observation"].update(turn_number=3),
])
def test_conflicting_ko_faint_history_is_rejected_without_repair(mutate):
    manager = _runtime_manager(); _seed(manager, action="action:conflict", mutate=mutate)
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    assert _admit(manager, action="action:conflict")["status"] == "rejected"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


def test_complete_ko_collection_without_runtime_commit_is_rejected():
    manager = _runtime_manager(); _seed(manager, action="action:uncommitted")
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    assert _admit(manager, action="action:uncommitted")["status"] == "rejected"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence
