from __future__ import annotations

from copy import deepcopy

import pytest

from llm.advisor_battle_state_store import BattleStateStore
from llm.advisor_candidate_contract import (
    build_provider_recommendation_payload,
    prepare_ui_recommendation_cycle,
)
from llm.advisor_lifecycle_confirmation import (
    CONDITION_APPLICATION_SOURCE,
    HAZARD_STATE_SOURCE,
    HP_RECOVERY_SOURCE,
    STAT_STAGE_SOURCE,
    LifecycleConfirmationBoundary,
    USED_MOVE_SOURCE,
    USER_TRUST,
)
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_observation_replay_coordinator import ObservationReplayCoordinator
from llm.advisor_turn_snapshot import (
    build_known_move_context_projection,
    build_request_start_recommendation_snapshot,
)


class _MoveRepository:
    def __init__(self, move_ids: set[str]):
        self._move_ids = move_ids

    def get(self, move_id: str):
        if move_id not in self._move_ids:
            raise KeyError(move_id)
        return {"move_id": move_id}


def _state(session_id: str = "session-1") -> dict[str, object]:
    return {
        "state_version": "battle-state-v1", "session_id": session_id,
        "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": 80, "max_hp": 100, "fainted": False, "condition": None, "known_item": None}}},
        "opponent_side": {"active_slot_index": 1, "pokemon": {
            1: {"pokemon_id": "garchomp", "current_hp": 100, "max_hp": 100, "fainted": False, "condition": None, "known_item": None},
            2: {"pokemon_id": "umbreon", "current_hp": 100, "max_hp": 100, "fainted": False, "condition": None, "known_item": None},
        }},
        "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": None,
    }


def _owners() -> dict[str, dict[str, object]]:
    return {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 1, "pokemon_id": "garchomp"}}


def _observe(boundary, collection, *, move_id: str, side: str = "opponent", slot_index: int = 1, pokemon_id: str = "garchomp", observation_id: str | None = None):
    confirmed = boundary.confirm(
        event_kind="used_move_observed", payload={"move_id": move_id}, session_id="session-1",
        source=USED_MOVE_SOURCE, trust=USER_TRUST, confirmed=True, side=side,
        slot_index=slot_index, pokemon_id=pokemon_id, observation_id=observation_id,
    )
    assert confirmed["status"] in {"confirmed", "duplicate"}
    if confirmed["status"] == "confirmed":
        assert collection.add_confirmation_result(confirmed)["status"] == "added"


def _apply(coordinator, collection):
    return coordinator.apply_confirmed_observations(collection.snapshot())


def test_observed_canonical_moves_are_identity_bound_partial_complete_and_idempotent():
    store = BattleStateStore(_state()); boundary = LifecycleConfirmationBoundary("session-1", _owners()); collection = ObservationCollection("session-1")
    repository = _MoveRepository({"earthquake", "protect", "swords-dance", "stone-edge"})
    coordinator = ObservationReplayCoordinator(store, move_repository=repository)
    for index, move_id in enumerate(("earthquake", "protect", "swords-dance", "stone-edge"), 1):
        _observe(boundary, collection, move_id=move_id, observation_id=f"move-{index}")
        applied = _apply(coordinator, collection)
        assert applied["status"] == "applied"
        context = build_known_move_context_projection(store.read_snapshot()["state"])
        assert context["opponent"]["state"] == ("complete" if index == 4 else "partially_known")
        assert context["opponent"]["unknown_slot_count"] == 4 - index

    _observe(boundary, collection, move_id="earthquake", observation_id="repeat")
    assert _apply(coordinator, collection)["status"] == "applied"
    assert build_known_move_context_projection(store.read_snapshot()["state"])["opponent"]["known_move_ids"] == ["earthquake", "protect", "swords-dance", "stone-edge"]


def test_invalid_inferred_stale_wrong_owner_and_fifth_move_fail_closed():
    store = BattleStateStore(_state()); boundary = LifecycleConfirmationBoundary("session-1", _owners()); collection = ObservationCollection("session-1")
    repository = _MoveRepository({"earthquake", "protect", "swords-dance", "stone-edge", "fire-fang"})
    coordinator = ObservationReplayCoordinator(store, move_repository=repository)
    assert boundary.confirm(event_kind="used_move_observed", payload={"move_id": "earthquake"}, session_id="session-1", source="provider", trust=USER_TRUST, confirmed=True, side="opponent", slot_index=1, pokemon_id="garchomp")["status"] == "invalid_provenance"
    assert boundary.confirm(event_kind="used_move_observed", payload={"move_id": "earthquake"}, session_id="old", source=USED_MOVE_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=1, pokemon_id="garchomp")["status"] == "stale_session"
    assert boundary.confirm(event_kind="used_move_observed", payload={"move_id": "earthquake"}, session_id="session-1", source=USED_MOVE_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=2, pokemon_id="umbreon")["status"] == "invalid_provenance"
    for index, move_id in enumerate(("earthquake", "protect", "swords-dance", "stone-edge", "fire-fang"), 1):
        _observe(boundary, collection, move_id=move_id, observation_id=f"move-{index}")
    assert _apply(coordinator, collection)["status"] == "transition_invalid"
    assert store.read_snapshot()["state"]["opponent_side"]["pokemon"][1].get("known_move_ids") is None


def test_switch_back_keeps_each_pokemon_known_moves_and_new_session_starts_unknown():
    state = _state(); state["opponent_side"]["active_slot_index"] = 2
    store = BattleStateStore(state); boundary = LifecycleConfirmationBoundary("session-1", {**_owners(), "opponent": {"slot_index": 2, "pokemon_id": "umbreon"}}); collection = ObservationCollection("session-1")
    repository = _MoveRepository({"wish"})
    coordinator = ObservationReplayCoordinator(store, move_repository=repository)
    _observe(boundary, collection, move_id="wish", slot_index=2, pokemon_id="umbreon", observation_id="wish")
    assert _apply(coordinator, collection)["status"] == "applied"
    state_after = store.read_snapshot()["state"]
    state_after["opponent_side"]["active_slot_index"] = 1
    assert build_known_move_context_projection(state_after)["opponent"]["state"] == "unknown"
    state_after["opponent_side"]["active_slot_index"] = 2
    assert build_known_move_context_projection(state_after)["opponent"]["known_move_ids"] == ["wish"]
    assert build_known_move_context_projection(_state("session-2"))["opponent"]["state"] == "unknown"


def test_observed_condition_application_replays_to_exact_owner_state():
    store = BattleStateStore(_state()); boundary = LifecycleConfirmationBoundary("session-1", _owners()); collection = ObservationCollection("session-1")
    coordinator = ObservationReplayCoordinator(store, move_repository=_MoveRepository(set()))
    confirmed = boundary.confirm(event_kind="condition_applied_observed", payload={"condition": "burn"}, session_id="session-1", source=CONDITION_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=1, pokemon_id="garchomp", related_observation_id="move-1")
    assert confirmed["status"] == "confirmed" and collection.add_confirmation_result(confirmed)["status"] == "added"
    assert _apply(coordinator, collection)["status"] == "applied"
    state = store.read_snapshot()["state"]
    assert state["opponent_side"]["pokemon"][1]["condition"] == "burn"
    assert state["opponent_side"]["pokemon"][2]["condition"] is None


def test_observed_absolute_stat_stage_replays_to_exact_owner_state():
    store = BattleStateStore(_state()); boundary = LifecycleConfirmationBoundary("session-1", _owners()); collection = ObservationCollection("session-1")
    coordinator = ObservationReplayCoordinator(store, move_repository=_MoveRepository(set()))
    confirmed = boundary.confirm(event_kind="stat_stage_observed", payload={"stat": "speed", "stage": -1}, session_id="session-1", source=STAT_STAGE_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=1, pokemon_id="garchomp")
    assert confirmed["status"] == "confirmed" and collection.add_confirmation_result(confirmed)["status"] == "added"
    assert _apply(coordinator, collection)["status"] == "applied"
    state = store.read_snapshot()["state"]
    assert state["opponent_side"]["pokemon"][1]["stat_stages"] == {"speed": -1}
    assert "stat_stages" not in state["opponent_side"]["pokemon"][2]


def test_observed_hazard_state_replaces_switch_authority_for_affected_side():
    store = BattleStateStore(_state()); boundary = LifecycleConfirmationBoundary("session-1", _owners()); collection = ObservationCollection("session-1")
    coordinator = ObservationReplayCoordinator(store, move_repository=_MoveRepository(set()))
    payload = {"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}
    confirmed = boundary.confirm(event_kind="switch_hazards_observed", payload=payload, session_id="session-1", source=HAZARD_STATE_SOURCE, trust=USER_TRUST, confirmed=True, side="self")
    assert confirmed["status"] == "confirmed" and collection.add_confirmation_result(confirmed)["status"] == "added"
    assert _apply(coordinator, collection)["status"] == "applied"
    assert store.read_snapshot()["state"]["switch_hazard_context"] == {"schema_version": "switch-hazard-context-v2", "session_id": "session-1", "affected_side": "self", **payload}


def test_observed_exact_hp_recovery_replays_to_exact_owner_state():
    store = BattleStateStore(_state()); boundary = LifecycleConfirmationBoundary("session-1", _owners()); collection = ObservationCollection("session-1")
    coordinator = ObservationReplayCoordinator(store, move_repository=_MoveRepository(set()))
    confirmed = boundary.confirm(event_kind="exact_hp_recovery_observed", payload={"hp_before": 80, "hp_after": 100}, session_id="session-1", source=HP_RECOVERY_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu")
    assert confirmed["status"] == "confirmed" and collection.add_confirmation_result(confirmed)["status"] == "added"
    assert _apply(coordinator, collection)["status"] == "applied"
    assert store.read_snapshot()["state"]["self_side"]["pokemon"][0]["current_hp"] == 100


def _battle_input(context):
    return {
        "current_state_session_id": "session-1", "known_move_context": context,
        "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]},
        "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "garchomp", "slot_index": 1}},
    }


def test_request_start_projection_is_detached_and_excluded_from_provider_payload_and_candidate_behavior():
    runtime_state = _state(); runtime_state["opponent_side"]["pokemon"][1]["known_move_ids"] = ["earthquake", "protect"]
    context = build_known_move_context_projection(runtime_state)
    battle_input = _battle_input(context)
    snapshot = build_request_start_recommendation_snapshot(battle_input, selectable_moves=(None, None, None, None))
    later_context = deepcopy(context); later_context["opponent"]["known_move_ids"].append("fire-fang")
    assert snapshot.to_dict()["current_state"]["known_move_context"]["opponent"]["known_move_ids"] == ["earthquake", "protect"]
    with pytest.raises(ValueError, match="invalid_known_move_context"):
        build_request_start_recommendation_snapshot(_battle_input({**build_known_move_context_projection(runtime_state), "session_id": "old"}), selectable_moves=(None, None, None, None))

    repository = {"tackle": {"move_id": "tackle", "category": "physical", "priority": 0, "power": 40, "type": "normal", "target": "selected-pokemon"}}
    prepared = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=battle_input, move_repository=repository)
    payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    assert prepared["status"] == "ready"
    assert "known_move_context" not in repr(payload)
    assert payload["selectable_candidate_exact_set"] == [{"slot_index": 0, "move": "tackle"}]
