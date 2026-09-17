from copy import deepcopy
from types import SimpleNamespace

from llm.advisor_entry_hazard_ko_replacement_runtime_admission import (
    admit_entry_hazard_ko_replacement,
    freeze_entry_hazard_ko_replacement_boundary,
)
from llm.advisor_identity_groundedness import build_groundedness
from llm.advisor_lifecycle_confirmation import CURRENT_ABILITY_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_pokemon_switch_observation import admit_pokemon_switch_observation
from llm.advisor_prospective_entry_authority import (
    build_prospective_entry_interactions,
    build_prospective_speed_stage,
)
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from tests.test_production_pokemon_switch_observation_wiring import _exact_entry_manager
from ui.main_window import MainWindow


HAZARDS = {
    "stealth_rock": "present",
    "spikes_layers": 3,
    "toxic_spikes_layers": 0,
    "sticky_web": "absent",
}


def _candidate_record(template, *, slot, pokemon_id, hp=90, ability="static"):
    row = deepcopy(template)
    row.update(pokemon_id=pokemon_id, current_hp=hp, max_hp=100, fainted=False, current_ability=ability)
    row["current_type"] = ["electric"]
    row["condition"] = None
    row["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    row["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    row["known_item"] = None
    row["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    row["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
    row["stat_stages"] = {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}
    row["prospective_groundedness_context"] = build_groundedness(
        session_id="s", side="self", slot_index=slot, pokemon_id=pokemon_id, status="grounded",
    )
    row["prospective_speed_stage_context"] = build_prospective_speed_stage(
        session_id="s", side="self", slot_index=slot, pokemon_id=pokemon_id, stage=0,
    )
    row["prospective_entry_interactions_context"] = build_prospective_entry_interactions(
        session_id="s", side="self", slot_index=slot, pokemon_id=pokemon_id,
        toxic_spikes="applicable", sticky_web="applicable",
    )
    return row


def _manager(*, replacement_hp=90, replacement_ability="static", fourth=False):
    base = _exact_entry_manager(hazards=HAZARDS).read_state()["state"]
    base["self_side"]["pokemon"][1]["current_hp"] = 20
    template = base["self_side"]["pokemon"][1]
    base["self_side"]["pokemon"][2] = _candidate_record(
        template, slot=2, pokemon_id="pichu", hp=replacement_hp, ability=replacement_ability,
    )
    if fourth:
        base["self_side"]["pokemon"][3] = _candidate_record(
            template, slot=3, pokemon_id="plusle", hp=90,
        )
    base["switch_hazard_context"] = build_switch_hazard_context(session_id="s", affected_side="self", **HAZARDS)
    created = BattleObservationRuntimeSessionManager.create("s", base)
    assert created["status"] == "session_ready", created
    return created["manager"]


def _first_hazard_ko(manager):
    result = admit_pokemon_switch_observation(
        runtime_session_manager=manager, captured_session_id="s", side="self",
        switch_in_slot_index=1, switch_in_pokemon_id="raichu", turn_number=4,
    )
    assert result["status"] == "resolved", result
    assert result["boundary"] == "replacement_required_after_entry_hazard_ko"
    assert result["strategy_d0"] is None
    active = manager.read_state()["state"]["self_side"]["pokemon"][1]
    assert active["current_hp"] == 0 and active["fainted"] is True
    return result


def _replace(manager, *, slot=2, pokemon_id="pichu", turn=4):
    return admit_entry_hazard_ko_replacement(
        runtime_session_manager=manager, captured_session_id="s",
        switch_in_slot_index=slot, switch_in_pokemon_id=pokemon_id, turn_number=turn,
    )


def _admit_unrelated_observation(manager):
    state = manager.read_state()["state"]
    side = state["opponent_side"]
    slot = side["active_slot_index"]
    pokemon = side["pokemon"][slot]
    owner = {"session_id": "s", "side": "opponent", "slot_index": slot, "pokemon_id": pokemon["pokemon_id"]}
    allocated = manager.allocate_observation_sequence()
    boundary = LifecycleConfirmationBoundary("s", {"opponent": owner})
    confirmed = boundary.confirm(
        event_kind="current_ability_observed", payload={"ability": "run-away"},
        session_id="s", source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True,
        side="opponent", slot_index=slot, pokemon_id=pokemon["pokemon_id"],
        observation_id=f"s:unrelated:{allocated['observation_sequence']}", turn_number=4,
    )
    assert confirmed["status"] == "confirmed", confirmed
    confirmed["observation"]["observation_sequence"] = allocated["observation_sequence"]
    assert manager.admit_confirmation("s", confirmed)["status"] in {"added", "duplicate"}
    assert manager.apply("s", manager.read_collection_snapshot())["status"] in {"applied", "already_applied"}


def test_entry_hazard_ko_replacement_reuses_actual_switch_lifecycle_and_returns_fresh_d0():
    manager = _manager()
    first = _first_hazard_ko(manager)
    result = _replace(manager)
    assert result["status"] == "resolved", result
    assert result.get("boundary") is None
    assert result["replacement_source_owner"] == first["incoming_owner"]
    assert result["replacement_boundary"]["source_switch_observation_id"] == first["observation"]["observation_id"]
    assert result["observation"]["event_kind"] == "pokemon_switch_observed"
    state = manager.read_state()["state"]
    assert state["self_side"]["active_slot_index"] == 2
    replacement = state["self_side"]["pokemon"][2]
    assert replacement["pokemon_id"] == "pichu" and 0 < replacement["current_hp"] < 90 and replacement["fainted"] is False
    assert result["strategy_d0"]["status"] == "resolved"
    assert result["strategy_d0"]["decision_owner"]["pokemon_id"] == "pichu"
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]


def test_replacement_can_ko_to_hazards_again_and_same_owner_continues_next_replacement():
    manager = _manager(replacement_hp=20, fourth=True)
    _first_hazard_ko(manager)
    second = _replace(manager)
    assert second["status"] == "resolved" and second["boundary"] == "replacement_required_after_entry_hazard_ko"
    assert second["strategy_d0"] is None
    state = manager.read_state()["state"]
    assert state["self_side"]["active_slot_index"] == 2
    assert state["self_side"]["pokemon"][2]["fainted"] is True

    third = _replace(manager, slot=3, pokemon_id="plusle")
    assert third["status"] == "resolved", third
    assert third.get("boundary") is None and third["strategy_d0"]["status"] == "resolved"
    assert manager.read_state()["state"]["self_side"]["active_slot_index"] == 3


def test_replacement_requires_current_exact_hazard_ko_boundary():
    manager = _manager()
    _first_hazard_ko(manager)
    before = deepcopy(manager.read_state()["state"])
    _admit_unrelated_observation(manager)
    collection_size = len(manager.read_collection_snapshot()["ordered_observations"])
    result = _replace(manager)
    assert result["status"] == "rejected"
    assert result["reason"] == "stale_entry_hazard_ko_replacement_boundary"
    assert len(manager.read_collection_snapshot()["ordered_observations"]) == collection_size
    after = manager.read_state()["state"]
    assert after["self_side"]["active_slot_index"] == before["self_side"]["active_slot_index"]
    assert after["self_side"]["pokemon"][1]["fainted"] is True


def test_generic_fainted_active_cannot_masquerade_as_entry_hazard_replacement_boundary():
    manager = _manager()
    state = manager.read_state()["state"]
    state["self_side"]["pokemon"][0]["current_hp"] = 0
    state["self_side"]["pokemon"][0]["fainted"] = True
    created = BattleObservationRuntimeSessionManager.create("s", state)
    assert created["status"] == "session_ready"
    result = _replace(created["manager"])
    assert result["status"] == "rejected"
    assert result["reason"] == "entry_hazard_ko_provenance_unavailable"
    assert created["manager"].read_state()["state"]["self_side"]["active_slot_index"] == 0


def test_invalid_or_incomplete_replacement_candidate_leaves_hazard_ko_state_unchanged():
    manager = _manager()
    _first_hazard_ko(manager)
    before_state = deepcopy(manager.read_state()["state"])
    before_collection = deepcopy(manager.read_collection_snapshot()["ordered_observations"])
    result = _replace(manager, slot=99, pokemon_id="missing")
    assert result["status"] == "rejected"
    assert manager.read_state()["state"] == before_state
    assert manager.read_collection_snapshot()["ordered_observations"] == before_collection

    manager = _manager(replacement_ability="trace")
    _first_hazard_ko(manager)
    before_state = deepcopy(manager.read_state()["state"])
    before_collection = deepcopy(manager.read_collection_snapshot()["ordered_observations"])
    result = _replace(manager)
    assert result["status"] == "incomplete"
    assert manager.read_state()["state"] == before_state
    assert manager.read_collection_snapshot()["ordered_observations"] == before_collection


def test_mainwindow_routes_fainted_self_active_through_hazard_ko_replacement_owner():
    manager = _manager()
    _first_hazard_ko(manager)
    selections = []
    cleared = []
    window = SimpleNamespace(
        _observation_runtime_session_manager=manager,
        _current_trusted_turn_number=4,
        _recommendation_readiness_owner=("s", 1, "raichu"),
        center_column=SimpleNamespace(llm_advice_panel=SimpleNamespace(clear_recommendation_readiness=lambda: cleared.append(True))),
        select_slot=lambda column, slot: selections.append((column, slot)),
        _retire_advice_presentation_authority=lambda: cleared.append("retired"),
    )
    result = MainWindow._confirm_pokemon_switch(
        window, side="self", switch_in_slot_index=2, switch_in_pokemon_id="pichu",
    )
    assert result["status"] == "resolved", result
    assert result["replacement_provenance"] == "runtime_entry_hazard_ko_replacement_v1"
    assert selections == [("team_my", 2)]
    assert cleared == ["retired", True]
    assert window._recommendation_readiness_owner is None


def test_mainwindow_preserves_existing_generic_fainted_switch_path():
    manager = _manager()
    state = manager.read_state()["state"]
    active = state["self_side"]["pokemon"][0]
    active["current_hp"] = 0
    active["fainted"] = True
    active.pop("fainted_provenance", None)
    created = BattleObservationRuntimeSessionManager.create("s", state)
    assert created["status"] == "session_ready"
    selections = []
    window = SimpleNamespace(
        _observation_runtime_session_manager=created["manager"],
        _current_trusted_turn_number=4,
        _recommendation_readiness_owner=None,
        center_column=SimpleNamespace(llm_advice_panel=SimpleNamespace(clear_recommendation_readiness=lambda: None)),
        select_slot=lambda column, slot: selections.append((column, slot)),
        _retire_advice_presentation_authority=lambda: None,
    )
    result = MainWindow._confirm_pokemon_switch(
        window, side="self", switch_in_slot_index=2, switch_in_pokemon_id="pichu",
    )
    assert result["status"] == "resolved", result
    assert "replacement_provenance" not in result
    assert selections == [("team_my", 2)]


def test_boundary_validator_rejects_forged_source_binding():
    manager = _manager()
    first = _first_hazard_ko(manager)
    runtime = first["runtime_snapshot"]
    collection = manager.read_collection_snapshot()
    resolved = freeze_entry_hazard_ko_replacement_boundary(runtime_snapshot=runtime, collection_snapshot=collection)
    assert resolved["status"] == "resolved"

    forged = deepcopy(collection)
    faint = next(row for row in forged["ordered_observations"] if row["event_kind"] == "switch_entry_faint_derived")
    faint["payload"]["source_switch_observation_id"] = "forged"
    rejected = freeze_entry_hazard_ko_replacement_boundary(runtime_snapshot=runtime, collection_snapshot=forged)
    assert rejected["status"] == "rejected"
