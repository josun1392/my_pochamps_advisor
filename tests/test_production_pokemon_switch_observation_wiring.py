from copy import deepcopy
from types import SimpleNamespace

from llm.advisor_ability_interaction_authority import build_ability_applicability_context
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_pokemon_switch_observation import admit_pokemon_switch_observation
import llm.advisor_pokemon_switch_observation as switch_subject
from llm.advisor_reducer_state_model import is_trusted_current_weather
from llm.advisor_identity_groundedness import build_groundedness
from llm.advisor_prospective_entry_authority import build_prospective_entry_interactions, build_prospective_speed_stage
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from llm.advisor_switch_entry_intimidate_authority import build_switch_entry_intimidate_authority
from llm.advisor_switch_entry_download_authority import build_switch_entry_download_authority
from llm.advisor_switch_entry_trace_authority import build_switch_entry_trace_authority
from llm.advisor_prospective_entry_authority import build_prospective_offensive_stages
from ui.main_window import MainWindow


def _manager():
    state = create_unknown_bootstrap_battle_state(
        "s", "pikachu", "eevee",
        self_roster={0: "pikachu", 1: "raichu"},
        opponent_roster={0: "eevee", 1: "vaporeon"},
    )["state"]
    for side in ("self_side", "opponent_side"):
        for pokemon in state[side]["pokemon"].values():
            pokemon["current_hp"] = 90
            pokemon["max_hp"] = 100
            pokemon["fainted"] = False
            pokemon["current_ability"] = "static"
            pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
            pokemon["stat_stages"] = {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="s", affected_side="self", stealth_rock="absent", spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent")
    state["field"]["weather"] = "none"
    state["field"]["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _switch(manager, *, side="self", slot=1, pokemon="raichu", session="s"):
    return admit_pokemon_switch_observation(
        runtime_session_manager=manager,
        captured_session_id=session,
        side=side,
        switch_in_slot_index=slot,
        switch_in_pokemon_id=pokemon,
        turn_number=4,
    )


def _exact_entry_manager(*, hazards, ability="static", item=None):
    state = _manager().read_state()["state"]
    incoming = state["self_side"]["pokemon"][1]
    incoming.update(current_type=["electric"], current_ability=ability, known_item=item, condition=None)
    incoming["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    incoming["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    incoming["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    incoming["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
    incoming["prospective_groundedness_context"] = build_groundedness(session_id="s", side="self", slot_index=1, pokemon_id="raichu", status="grounded")
    incoming["prospective_speed_stage_context"] = build_prospective_speed_stage(session_id="s", side="self", slot_index=1, pokemon_id="raichu", stage=0)
    incoming["prospective_entry_interactions_context"] = build_prospective_entry_interactions(session_id="s", side="self", slot_index=1, pokemon_id="raichu", toxic_spikes="applicable", sticky_web="applicable")
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="s", affected_side="self", **hazards)
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def test_explicit_switch_observation_previews_admits_and_applies_exact_runtime_identity():
    manager = _manager()
    before = manager.read_state()["state"]
    before["self_side"]["pokemon"][0]["stat_stages"]["attack"] = 3
    # The runtime owns stage state, so use an explicit initial manager with it.
    manager = BattleObservationRuntimeSessionManager.create("s", before)["manager"]
    result = _switch(manager)
    assert result["status"] == "resolved"
    assert result["observation"]["event_kind"] == "pokemon_switch_observed"
    assert result["observation"]["payload"] == {
        "switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu",
        "switch_in_slot_index": 1, "switch_in_pokemon_id": "raichu",
    }
    assert result["observation"]["observation_sequence"] == 1
    assert result["preview"]["status"] == "preview_ready"
    state = manager.read_state()["state"]
    assert state["self_side"]["active_slot_index"] == 1
    assert state["self_side"]["pokemon"][0]["stat_stages"] == {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}
    assert manager.read_collection_snapshot()["ordered_observations"] == [result["observation"]]


def test_opponent_switch_is_side_neutral_and_does_not_change_self_active_owner():
    manager = _manager()
    result = _switch(manager, side="opponent", slot=1, pokemon="vaporeon")
    state = manager.read_state()["state"]
    assert result["status"] == "resolved"
    assert state["opponent_side"]["active_slot_index"] == 1
    assert state["self_side"]["active_slot_index"] == 0


def test_production_switch_runs_outgoing_regenerator_and_natural_cure_lifecycles():
    state = _manager().read_state()["state"]
    outgoing = state["self_side"]["pokemon"][0]
    outgoing.update(current_hp=30, max_hp=90, fainted=False, current_ability="regenerator")
    outgoing["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["ability_applicability_context"] = build_ability_applicability_context(
        session_id="s", source={"side": "self", "slot_index": 0, "pokemon_id": "pikachu"}, ability_id="regenerator", status="applicable",
    )
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    assert _switch(manager)["status"] == "resolved"
    retired = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert retired["current_hp"] == 60 and retired["current_ability"] == {"knowledge": "unknown"}

    state = _manager().read_state()["state"]
    outgoing = state["self_side"]["pokemon"][0]
    outgoing.update(current_ability="natural-cure", condition="burn")
    outgoing["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    outgoing["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "burn"}
    state["ability_applicability_context"] = build_ability_applicability_context(
        session_id="s", source={"side": "self", "slot_index": 0, "pokemon_id": "pikachu"}, ability_id="natural-cure", status="applicable",
    )
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    assert _switch(manager)["status"] == "resolved"
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["condition"] is None


def test_switch_rejects_stale_session_mismatched_or_fainted_incoming_without_runtime_mutation():
    manager = _manager()
    before = manager.read_state()
    assert _switch(manager, session="stale")["reason"] == "runtime_snapshot_unavailable"
    assert _switch(manager, pokemon="wrong")["reason"] == "switch_in_identity_mismatch"
    state = manager.read_state()["state"]
    state["self_side"]["pokemon"][1]["fainted"] = True
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    assert _switch(manager)["reason"] == "switch_in_fainted"
    assert manager.read_state()["state"]["self_side"]["active_slot_index"] == 0
    assert before["state"]["self_side"]["active_slot_index"] == 0


def test_duplicate_cannot_double_apply_and_same_active_identity_fails_closed():
    manager = _manager()
    first = _switch(manager)
    assert first["status"] == "resolved"
    assert _switch(manager, slot=1, pokemon="raichu")["reason"] == "switch_in_matches_active_owner"
    assert manager.read_state()["state"]["last_applied_observation_sequence"] == 1


def test_production_switch_commits_exact_hazard_damage_and_fresh_d0_through_one_batch():
    manager = _exact_entry_manager(hazards={"stealth_rock": "present", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"})
    result = _switch(manager)
    assert result["status"] == "resolved"
    assert [row["event_kind"] for row in result["derived_observations"]] == ["switch_entry_hp_transition_derived"]
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][1]["current_hp"] == 78
    assert result["strategy_d0"]["status"] == "resolved"
    assert result["strategy_d0"]["decision_owner"]["pokemon_id"] == "raichu"
    assert result["runtime_snapshot"]["status"] == "runtime_snapshot_ready"
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    assert result["post_commit_verification_failure"] is None


def test_unknown_entry_hazard_authority_fails_closed_without_switching():
    manager = _manager()
    state = manager.read_state()["state"]
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="s", affected_side="self")
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    result = _switch(manager)
    assert result["status"] == "incomplete"
    assert manager.read_state()["state"]["self_side"]["active_slot_index"] == 0


def test_production_switch_commits_toxic_spikes_and_sticky_web_in_same_batch():
    manager = _exact_entry_manager(hazards={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 2, "sticky_web": "present"})
    result = _switch(manager)
    assert result["status"] == "resolved"
    assert [row["event_kind"] for row in result["derived_observations"]] == ["switch_entry_condition_applied_derived", "switch_entry_stat_stage_transition_derived"]
    incoming = manager.read_state()["state"]["self_side"]["pokemon"][1]
    assert (incoming["condition"], incoming["stat_stages"]["speed"]) == ("toxic", -1)


def test_production_switch_poison_absorbs_only_toxic_spikes():
    manager = _exact_entry_manager(hazards={"stealth_rock": "present", "spikes_layers": 1, "toxic_spikes_layers": 2, "sticky_web": "present"})
    state = manager.read_state()["state"]
    state["self_side"]["pokemon"][1]["current_type"] = ["poison"]
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    result = _switch(manager)
    assert result["status"] == "resolved"
    assert [row["event_kind"] for row in result["derived_observations"]] == ["switch_entry_hp_transition_derived", "switch_entry_stat_stage_transition_derived", "switch_entry_hazard_transition_derived"]
    hazards = manager.read_state()["state"]["switch_hazard_context"]
    assert (hazards["stealth_rock"], hazards["spikes_layers"], hazards["toxic_spikes_layers"], hazards["sticky_web"]) == ("present", 1, 0, "present")


def test_entry_hazard_ko_commits_faint_but_stops_at_replacement_boundary():
    manager = _exact_entry_manager(hazards={"stealth_rock": "present", "spikes_layers": 3, "toxic_spikes_layers": 0, "sticky_web": "absent"})
    state = manager.read_state()["state"]
    state["self_side"]["pokemon"][1]["current_hp"] = 20
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    result = _switch(manager)
    assert result["status"] == "resolved"
    assert result["boundary"] == "replacement_required_after_entry_hazard_ko"
    assert result["strategy_d0"] is None
    incoming = manager.read_state()["state"]["self_side"]["pokemon"][1]
    assert (incoming["current_hp"], incoming["fainted"]) == (0, True)


def test_production_switch_commits_weather_setter_and_missing_weather_fails_closed():
    manager = _exact_entry_manager(hazards={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}, ability="drizzle")
    result = _switch(manager)
    assert result["status"] == "resolved"
    assert [row["event_kind"] for row in result["derived_observations"]] == ["switch_entry_weather_transition_derived"]
    assert manager.read_state()["state"]["field"]["weather"] == "rain"

    state = _exact_entry_manager(hazards={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}, ability="drizzle").read_state()["state"]
    for raw_weather in (None, "rain"):
        candidate = _exact_entry_manager(hazards={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}, ability="drizzle").read_state()["state"]
        candidate["field"]["weather"] = raw_weather
        candidate["field"].pop("weather_provenance", None)
        manager = BattleObservationRuntimeSessionManager.create("s", candidate)["manager"]
        result = _switch(manager)
        assert result["status"] == "incomplete" and result["reason"] == "current_weather_unknown_or_unsupported"
        assert manager.read_state()["state"]["self_side"]["active_slot_index"] == 0


def test_production_switch_commits_exact_intimidate_once():
    manager = _exact_entry_manager(hazards={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}, ability="intimidate")
    state = manager.read_state()["state"]
    source = {"side": "self", "slot_index": 1, "pokemon_id": "raichu"}
    target = {"side": "opponent", "slot_index": 0, "pokemon_id": "eevee"}
    state["switch_entry_intimidate_authority"] = build_switch_entry_intimidate_authority(session_id="s", source=source, target=target, interaction="lowered", target_attack_stage=0)
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    result = _switch(manager)
    assert result["status"] == "resolved"
    derived = [row for row in result["derived_observations"] if row["event_kind"] == "switch_entry_stat_stage_transition_derived"]
    assert len(derived) == 1 and derived[0]["payload"]["mechanic"] == "intimidate"
    assert manager.read_state()["state"]["opponent_side"]["pokemon"][0]["stat_stages"]["attack"] == -1
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    assert result["strategy_d0"]["current_stage_authority"]["opponent"]["stages"]["attack"]["status"] == "known"
    assert result["strategy_d0"]["current_stage_authority"]["opponent"]["stages"]["attack"]["value"] == -1


def test_production_switch_commits_exact_download_attack_boost():
    manager = _exact_entry_manager(hazards={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}, ability="download")
    state = manager.read_state()["state"]
    source = {"side": "self", "slot_index": 1, "pokemon_id": "raichu"}; target = {"side": "opponent", "slot_index": 0, "pokemon_id": "eevee"}
    state["self_side"]["pokemon"][1]["prospective_offensive_stages_context"] = build_prospective_offensive_stages(session_id="s", side="self", slot_index=1, pokemon_id="raichu", attack=0, special_attack=0)
    state["switch_entry_download_authority"] = build_switch_entry_download_authority(session_id="s", source=source, target=target, applicability="applicable", target_defense=90, target_special_defense=100)
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    result = _switch(manager)
    assert result["status"] == "resolved"
    derived = [row for row in result["derived_observations"] if row["event_kind"] == "switch_entry_stat_stage_transition_derived"]
    assert len(derived) == 1 and all(derived[0]["payload"][key] == value for key, value in {"mechanic": "download", "stat": "attack", "stage_before": 0, "stage_after": 1}.items())
    assert manager.read_state()["state"]["self_side"]["pokemon"][1]["stat_stages"]["attack"] == 1
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    assert result["strategy_d0"]["current_stage_authority"]["self"]["stages"]["attack"]["status"] == "known"
    assert result["strategy_d0"]["current_stage_authority"]["self"]["stages"]["attack"]["value"] == 1


def test_download_unknown_and_trace_copy_fail_closed_without_prefix():
    base = {"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}
    manager = _exact_entry_manager(hazards=base, ability="download")
    state = manager.read_state()["state"]
    state["self_side"]["pokemon"][1]["prospective_offensive_stages_context"] = build_prospective_offensive_stages(session_id="s", side="self", slot_index=1, pokemon_id="raichu", attack=0, special_attack=0)
    state["switch_entry_download_authority"] = build_switch_entry_download_authority(session_id="s", source={"side": "self", "slot_index": 1, "pokemon_id": "raichu"}, target={"side": "opponent", "slot_index": 0, "pokemon_id": "eevee"})
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    assert _switch(manager)["status"] == "incomplete"
    assert manager.read_state()["state"]["self_side"]["active_slot_index"] == 0 and not manager.read_collection_snapshot()["ordered_observations"]

    manager = _exact_entry_manager(hazards=base, ability="trace")
    state = manager.read_state()["state"]
    state["switch_entry_trace_authority"] = build_switch_entry_trace_authority(session_id="s", source={"side": "self", "slot_index": 1, "pokemon_id": "raichu"}, target={"side": "opponent", "slot_index": 0, "pokemon_id": "eevee"}, target_ability="water-absorb", traceability="traceable")
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    result = _switch(manager)
    assert result["reason"] == "trace_runtime_writeback_unsupported"
    assert manager.read_state()["state"]["self_side"]["active_slot_index"] == 0 and not manager.read_collection_snapshot()["ordered_observations"]


def test_heavy_duty_boots_preserves_hp_without_derived_damage():
    manager = _exact_entry_manager(hazards={"stealth_rock": "present", "spikes_layers": 3, "toxic_spikes_layers": 2, "sticky_web": "present"}, item="heavy-duty-boots")
    result = _switch(manager)
    assert result["status"] == "resolved"
    assert manager.read_state()["state"]["self_side"]["pokemon"][1]["current_hp"] == 90
    assert "switch_entry_hp_transition_derived" not in [row["event_kind"] for row in result["derived_observations"]]
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]


def test_forged_batch_and_failed_sequence_reservation_leave_no_prefix(monkeypatch):
    manager = _exact_entry_manager(hazards={"stealth_rock": "present", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"})
    real = switch_subject.derive_live_manual_switch_entry_consequences
    def forged(**kwargs):
        result = real(**kwargs)
        result["confirmations"][0]["observation"]["payload"]["source_switch_observation_id"] = "stale"
        return result
    monkeypatch.setattr(switch_subject, "derive_live_manual_switch_entry_consequences", forged)
    before = deepcopy(manager.read_state()["state"])
    assert _switch(manager)["status"] == "rejected"
    assert manager.read_state()["state"] == before and not manager.read_collection_snapshot()["ordered_observations"]
    monkeypatch.setattr(switch_subject, "derive_live_manual_switch_entry_consequences", lambda **kwargs: (kwargs["allocate_sequence"](), {"status": "incomplete", "reason": "test_reserved"})[1])
    assert _switch(manager)["status"] == "incomplete"
    monkeypatch.setattr(switch_subject, "derive_live_manual_switch_entry_consequences", real)
    recovered = _switch(manager)
    assert recovered["status"] == "resolved" and recovered["strategy_d0"]["status"] == "resolved"


def test_drizzle_weather_provenance_is_trusted_downstream():
    manager = _exact_entry_manager(hazards={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}, ability="drizzle")
    result = _switch(manager); field = result["runtime_snapshot"]["state"]["field"]
    assert field["weather"] == "rain" and field["weather_provenance"]["event_kind"] == "current_weather_observed"
    assert field["weather_provenance"]["trust"] == "mechanics_derived_runtime"
    assert is_trusted_current_weather(field["weather"], field["weather_provenance"])


def test_mainwindow_switch_helper_only_updates_presentation_after_success(monkeypatch):
    manager = _manager()
    selections = []
    cleared = []
    window = SimpleNamespace(
        _observation_runtime_session_manager=manager,
        _current_trusted_turn_number=4,
        _recommendation_readiness_owner=("s", 0, "pikachu"),
        center_column=SimpleNamespace(llm_advice_panel=SimpleNamespace(clear_recommendation_readiness=lambda: cleared.append(True))),
        select_slot=lambda column, slot: selections.append((column, slot)),
        _retire_advice_presentation_authority=lambda: cleared.append("retired"),
    )
    window._active_session_id = lambda: "s"
    result = MainWindow._confirm_pokemon_switch(window, side="self", switch_in_slot_index=1, switch_in_pokemon_id="raichu")
    assert result["status"] == "resolved"
    assert selections == [("team_my", 1)]
    assert cleared == ["retired", True]
    assert window._recommendation_readiness_owner is None

    failed = SimpleNamespace(**window.__dict__)
    failed._observation_runtime_session_manager = _manager()
    failed._active_session_id = lambda: "s"
    selections.clear(); cleared.clear()
    result = MainWindow._confirm_pokemon_switch(failed, side="self", switch_in_slot_index=1, switch_in_pokemon_id="wrong")
    assert result["status"] == "rejected"
    assert selections == [] and cleared == []


def test_slot_navigation_does_not_reference_or_emit_switch_observation():
    source = MainWindow.select_slot.__code__.co_names
    assert "_confirm_pokemon_switch" not in source
    assert "admit_pokemon_switch_observation" not in source


def test_bootstrap_can_seed_exact_loaded_roster_identities_without_filling_battle_facts():
    created = create_unknown_bootstrap_battle_state(
        "s", "pikachu", "eevee",
        self_roster={0: "pikachu", 1: "raichu"},
        opponent_roster={0: "eevee", 1: "vaporeon"},
    )
    assert created["status"] == "initial_state_ready"
    assert created["state"]["self_side"]["pokemon"][1]["pokemon_id"] == "raichu"
    assert created["state"]["self_side"]["pokemon"][1]["current_hp"] == {"knowledge": "unknown"}
