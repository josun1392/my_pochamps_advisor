"""Focused contracts for the generic observed HP-zero faint lifecycle."""
import pytest

from llm.advisor_entry_hazard_ko_replacement_runtime_admission import (
    freeze_entry_hazard_ko_replacement_boundary,
)
from llm.advisor_exact_hp_zero_faint_runtime_lifecycle import (
    admit_exact_hp_zero_faint,
    build_exact_hp_zero_faint_confirmation_pair,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


def _manager(*, self_hp=100, opponent_hp=100, self_fainted=False, opponent_fainted=False):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    for side, hp, fainted in (("self", self_hp, self_fainted), ("opponent", opponent_hp, opponent_fainted)):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        if hp != "unknown":
            pokemon["current_hp"] = hp
            pokemon["max_hp"] = 100
        pokemon["fainted"] = fainted
    created = BattleObservationRuntimeSessionManager.create("s", state)
    assert created["status"] == "session_ready", created
    return created["manager"]


def _owner(manager, side):
    pokemon = manager.read_state()["state"][f"{side}_side"]["pokemon"][0]
    return {"session_id": "s", "side": side, "slot_index": 0, "pokemon_id": pokemon["pokemon_id"]}


def _seed_pair(manager, *, side="self", event="event:seed", turn=2, mutate=None):
    pair = build_exact_hp_zero_faint_confirmation_pair(
        session_id="s", owner=_owner(manager, side), hp_before=100,
        turn_number=turn, source_event_id=event,
    )
    assert pair is not None
    for confirmation in pair:
        confirmation["observation"]["observation_sequence"] = manager.allocate_observation_sequence()["observation_sequence"]
    if mutate:
        mutate(pair)
    assert manager.admit_confirmations_atomically("s", pair)["status"] == "added"
    return pair


def _admit(manager, *, side="self", event="event:zero", turn=2, session="s"):
    return admit_exact_hp_zero_faint(
        runtime_session_manager=manager, captured_session_id=session, side=side,
        source_event_id=event, turn_number=turn,
    )


def test_builder_is_pure_and_returns_ordered_deterministic_confirmation_pair():
    manager = _manager()
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    owner = _owner(manager, "self")
    pair = build_exact_hp_zero_faint_confirmation_pair(
        session_id="s", owner=owner, hp_before=37, turn_number=5, source_event_id="event:builder",
    )
    assert pair is not None and len(pair) == 2 and [row["status"] for row in pair] == ["confirmed", "confirmed"]
    hp, faint = (row["observation"] for row in pair)
    assert hp["event_kind"] == "exact_hp_transition_observed"
    assert faint["event_kind"] == "pokemon_faint_observed"
    assert hp["observation_id"] == "s:hp-zero-faint:event:builder:hp"
    assert faint["observation_id"] == "s:hp-zero-faint:event:builder:faint"
    assert (hp["side"], hp["slot_index"], hp["pokemon_id"], hp["turn_number"]) == ("self", 0, "pikachu", 5)
    assert hp["payload"] == {"hp_before": 37, "hp_after": 0}
    assert faint["related_observation_id"] == hp["observation_id"]
    assert manager.read_state() == before_state
    assert manager.read_collection_snapshot() == before_collection
    assert manager.last_allocated_sequence == before_sequence


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_fresh_admission_is_side_neutral_and_commits_ordered_provenance(side):
    manager = _manager()
    result = _admit(manager, side=side, event=f"event:{side}")
    assert result["status"] == "resolved" and result["idempotent"] is False and result["strategy_d0"] is None
    hp, faint = result["observations"]
    assert len(result["observations"]) == 2 and hp["observation_sequence"] < faint["observation_sequence"]
    assert result["owner"] == _owner(manager, side)
    assert result["replacement_boundary"] == {
        "status": "replacement_required_after_faint", "fainted_owner": _owner(manager, side),
        "hp_transition_observation_id": hp["observation_id"], "faint_observation_id": faint["observation_id"],
        "terminal_sequence": faint["observation_sequence"], "provenance": "runtime_exact_hp_zero_faint_lifecycle_v1",
    }
    pokemon = manager.read_state()["state"][f"{side}_side"]["pokemon"][0]
    assert pokemon["current_hp"] == 0 and pokemon["fainted"] is True
    assert pokemon["current_hp_provenance"]["source_observation_id"] == hp["observation_id"]
    assert pokemon["current_hp_provenance"]["source_sequence"] == hp["observation_sequence"]
    assert pokemon["fainted_provenance"]["source_observation_id"] == faint["observation_id"]
    assert pokemon["fainted_provenance"]["source_sequence"] == faint["observation_sequence"]


def test_exact_committed_retry_reuses_without_any_mutation():
    manager = _manager()
    first = _admit(manager, event="event:retry")
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    retry = _admit(manager, event="event:retry")
    assert retry["status"] == "resolved" and retry["reason"] == "idempotent_reuse" and retry["idempotent"] is True
    assert retry["observations"] == first["observations"] and retry["replacement_boundary"] == first["replacement_boundary"]
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection
    assert manager.last_allocated_sequence == before_sequence


def test_complete_pair_without_committed_runtime_rejects_without_repair():
    manager = _manager()
    _seed_pair(manager, event="event:uncommitted")
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    result = _admit(manager, event="event:uncommitted")
    assert result["status"] == "rejected" and result.get("idempotent") is not True
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


@pytest.mark.parametrize("which", ["hp", "faint"])
def test_partial_historical_pair_is_rejected_without_repair(which):
    manager = _manager(); pair = _seed_pair(manager, event=f"event:{which}")
    # Recreate a separate manager so only the requested public confirmation is admitted.
    manager = _manager()
    assert manager.admit_confirmation("s", pair[0 if which == "hp" else 1])["status"] == "added"
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    result = _admit(manager, event=f"event:{which}")
    assert result["status"] == "rejected"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


def test_conflicting_complete_pair_is_rejected_without_repair():
    manager = _manager()
    _seed_pair(manager, event="event:conflict", mutate=lambda pair: pair[1]["observation"].update(related_observation_id="forged"))
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    assert _admit(manager, event="event:conflict")["status"] == "rejected"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


@pytest.mark.parametrize("kwargs", [
    {"session": "stale"}, {"side": "bad"}, {"event": "bad event"}, {"event": "bad_event"}, {"turn": 0},
])
def test_stale_and_malformed_requests_have_zero_mutation(kwargs):
    manager = _manager(); before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    result = _admit(manager, **kwargs)
    assert result["status"] == "rejected"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


def test_already_fainted_without_history_is_rejected_without_second_lifecycle():
    manager = _manager(self_hp=0, self_fainted=True)
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    assert _admit(manager, event="event:already")["reason"] == "already_fainted_without_matching_lifecycle"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


@pytest.mark.parametrize("hp", [0, -1, "unknown"])
def test_non_positive_or_unknown_current_hp_fails_closed(hp):
    manager = _manager(self_hp=hp)
    before_state, before_collection, before_sequence = manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence
    assert _admit(manager, event=f"event:hp{hp}")["status"] == "rejected"
    assert manager.read_state() == before_state and manager.read_collection_snapshot() == before_collection and manager.last_allocated_sequence == before_sequence


def test_hp_zero_alone_does_not_infer_faint_and_generic_pair_is_not_entry_hazard_boundary():
    manager = _manager()
    pair = _seed_pair(manager, event="event:hp-alone")
    # A fresh manager with only the valid canonical HP row proves the reducer does not infer faint.
    hp_only = _manager()
    assert hp_only.admit_confirmation("s", pair[0])["status"] == "added"
    assert hp_only.apply("s", hp_only.read_collection_snapshot())["status"] == "applied"
    pokemon = hp_only.read_state()["state"]["self_side"]["pokemon"][0]
    assert pokemon["current_hp"] == 0 and pokemon["fainted"] is False

    manager = _manager()
    result = _admit(manager, event="event:generic")
    boundary = freeze_entry_hazard_ko_replacement_boundary(
        runtime_snapshot=result["runtime_snapshot"], collection_snapshot=manager.read_collection_snapshot(),
    )
    assert boundary["status"] == "rejected" and boundary["reason"] == "entry_hazard_ko_provenance_unavailable"
