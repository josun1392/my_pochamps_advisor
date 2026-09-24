"""Production-shaped C6 capture remains separate from advice and execution."""
from copy import deepcopy
from types import MappingProxyType
from types import SimpleNamespace

import pytest

import ui.main_window as main_window_module
from llm.advisor_c6_production_decision_capture import ProductionDecisionCapture
from ui.main_window import MainWindow
from tests.test_v36_main_window_session_lifecycle_wiring import _Harness, _core_values


CONTEXT = {"ruleset_id": "explicit-rules", "mechanics_version": "explicit-mechanics",
           "protocol_version": "explicit-protocol", "battle_format_id": "explicit-singles"}


def _window():
    window = _Harness()
    window._c6_decision_capture_owners = {}
    window._c6_explicit_context_reference = None
    window._current_trusted_turn_number = 1
    assert MainWindow.set_c6_decision_capture_context(window, deepcopy(CONTEXT))
    return window


def _begin(window, *, legal=None):
    snapshot = window._observation_runtime_session_manager.capture_runtime_state_snapshot("ui-session-0")
    return MainWindow.begin_c6_decision_capture(
        window, runtime_snapshot=snapshot, legal_action_set=legal)


def test_production_capture_precedes_command_and_preserves_unknowns():
    window = _window()
    before = _core_values(window)
    record = _begin(window)
    assert record["status"] == "captured", record
    boundary = record["opportunity"]["certificate"]
    assert boundary["channel"] == "actor_first_person"
    assert record["opportunity"]["legal_action_set"]["status"] == "unknown"
    public = record["public_information"]["public_snapshot"]
    private = record["private_information"]["private_snapshot"]
    assert public["active"]["self"]["pokemon_id"] == "pikachu"
    assert public["active"]["opponent"]["pokemon_id"] == "eevee"
    assert public["active"]["opponent"]["current_hp"] == {"availability": "unavailable"}
    assert public["active"]["self"]["stat_stages"]["attack"] == {"availability": "unavailable"}
    assert private["own_roster"][0]["known_item"] == {"availability": "unavailable"}
    assert record["private_information"]["completeness"] == "incomplete"
    captured = MainWindow.read_c6_decision_capture_snapshot(window)
    assert captured["actor_captures"][0]["submitted_commands"]["command_evidence"] == ()
    assert boundary["boundary_id"] in captured["actor_captures"][0]["submitted_commands"]["command_unknown_boundary_ids"]
    assert _core_values(window) == before


def test_explicit_attack_and_switch_confirmation_are_direct_and_separate():
    window = _window()
    first = _begin(window)
    boundary = first["opportunity"]["certificate"]["boundary_id"]
    # Recommendation, highlighted move and execution contain no command admission.
    window._panels[("team_my", 0)].selected_move_index = 2
    assert MainWindow.read_c6_decision_capture_snapshot(window)["actor_captures"][0]["submitted_commands"]["command_evidence"] == ()
    args = dict(captured_session_id="ui-session-0", captured_battle_id="ui-session-0",
                boundary_id=boundary, confirmation_event_id="explicit-command-1",
                command_payload={"kind": "attack", "move_id": "thunderbolt"})
    attack = MainWindow.confirm_c6_submitted_command(window, **args)
    assert attack["status"] == "admitted", attack
    assert attack["evidence"]["command_payload"] == {"kind": "attack", "move_id": "thunderbolt"}
    assert MainWindow.confirm_c6_submitted_command(window, **args)["status"] == "duplicate"
    assert MainWindow.confirm_c6_submitted_command(window, **{**args, "command_payload": {"kind": "attack", "move_id": "protect"}})["reason"] == "conflicting_submitted_command"
    assert _begin(window)["status"] == "duplicate"
    window._current_trusted_turn_number = 2
    second = _begin(window)
    assert second["status"] == "captured"
    assert second["opportunity"]["certificate"]["boundary_id"] != boundary
    switch = MainWindow.confirm_c6_submitted_command(
        window, captured_session_id="ui-session-0", captured_battle_id="ui-session-0",
        boundary_id=second["opportunity"]["certificate"]["boundary_id"],
        confirmation_event_id="explicit-command-2",
        command_payload={"kind": "switch", "incoming_pokemon_id": "bench-a"})
    assert switch["status"] == "admitted", switch
    assert switch["evidence"]["command_payload"]["kind"] == "switch"
    assert isinstance(first["public_information"], MappingProxyType)
    assert first["public_information"]["public_snapshot"]["active"]["self"]["pokemon_id"] == "pikachu"


def test_foreign_lifecycle_and_explicit_context_gate_fail_closed():
    window = _window()
    record = _begin(window, legal={"status": "partial", "action_ids": ["attack:thunderbolt"]})
    assert record["status"] == "captured"
    assert record["opportunity"]["legal_action_set"]["status"] == "partial"
    boundary = record["opportunity"]["certificate"]["boundary_id"]
    bad = MainWindow.confirm_c6_submitted_command(
        window, captured_session_id="foreign", captured_battle_id="ui-session-0",
        boundary_id=boundary, confirmation_event_id="x", command_payload={"kind": "attack", "move_slot": 1})
    assert bad["reason"] == "stale_or_foreign_battle"
    assert MainWindow.confirm_c6_submitted_command(
        window, captured_session_id="ui-session-0", captured_battle_id="ui-session-0",
        boundary_id="foreign", confirmation_event_id="x",
        command_payload={"kind": "attack", "move_slot": 1})["reason"] == "boundary_not_retained"
    window._c6_explicit_context_reference = None
    assert _begin(window)["reason"] == "explicit_decision_context_unavailable"
    assert MainWindow.begin_new_battle(window) == "ui-session-1"
    assert MainWindow.read_c6_decision_capture_snapshot(window)["actor_captures"] == ()
    assert MainWindow.confirm_c6_submitted_command(
        window, captured_session_id="ui-session-0", captured_battle_id="ui-session-0",
        boundary_id=boundary, confirmation_event_id="late",
        command_payload={"kind": "attack", "move_slot": 1})["reason"] == "stale_or_foreign_battle"


def test_source_standalone_requires_existing_pre_command_evidence():
    actor = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}
    source = ProductionDecisionCapture.create(session_id="s", battle_id="b", actor=actor, source_id="production-s")
    assert source["status"] == "source_ready"
    owner = source["source"]
    assert owner.confirm_submitted_command(
        captured_session_id="s", captured_battle_id="b", boundary_id="none", actor=actor,
        confirmation_event_id="command", command_payload={"kind": "attack", "move_slot": 1})["reason"] == "boundary_not_retained"
    assert owner.read_capture_snapshot(captured_session_id="s", captured_battle_id="b")["status"] == "ready"


def test_confirmed_own_move_is_private_and_later_ui_mutation_cannot_rewrite_it():
    window = _window()
    panel = window._panels[("team_my", 0)]
    panel.selected_moves = [SimpleNamespace(move_id="thunderbolt")]
    record = _begin(window, legal={"status": "exact", "action_ids": ["attack:thunderbolt", "manual_switch:bench-a"]})
    assert record["status"] == "captured", record
    assert record["opportunity"]["legal_action_set"]["status"] == "exact"
    moves = record["private_information"]["private_snapshot"]["own_roster"][0]["moves"]
    assert moves[0]["move_id"] == {"availability": "available", "value": "thunderbolt"}
    assert moves[0]["current_pp"] == {"availability": "unavailable"}
    panel.selected_moves[0].move_id = "protect"
    assert moves[0]["move_id"]["value"] == "thunderbolt"
    assert _begin(window)["status"] == "rejected"  # same boundary cannot absorb later UI edits


def _begin_with_reducer_known_opponent_moves(window, move_ids):
    snapshot = window._observation_runtime_session_manager.capture_runtime_state_snapshot("ui-session-0")
    snapshot["state"]["opponent_side"]["pokemon"][0]["known_move_ids"] = list(move_ids)
    return MainWindow.begin_c6_decision_capture(window, runtime_snapshot=snapshot)


def test_panel_selected_opponent_move_alone_is_not_public_revealed_evidence():
    window = _window()
    panel = window._panels[("team_enemy", 0)]
    panel.selected_moves = [SimpleNamespace(move_id="shadow-ball")]
    record = _begin(window)
    assert record["status"] == "captured"
    assert record["public_information"]["public_snapshot"]["opponent_revealed_moves"] == {
        "status": "unknown", "move_ids": ()}
    assert panel.selected_moves[0].move_id == "shadow-ball"


def test_non_c6_opponent_move_selection_context_remains_available():
    window = _window()
    panel = window._panels[("team_enemy", 0)]
    panel.selected_moves = [SimpleNamespace(
        move_id="shadow-ball", name_en="Shadow Ball", name_ko=None, type="ghost",
        category="special", power=80, accuracy=100, pp=15, priority=0,
        drain=None, min_hits=None, max_hits=None, healing=None)]
    window.champions_move_pool_repo = SimpleNamespace(
        status_for_pokemon=lambda *_: {"status": "ready"})
    window._panel_moves_payload = MainWindow._panel_moves_payload
    window._opponent_candidate_moves = lambda *_: []
    payload = MainWindow._opponent_moves_payload(window, panel)
    assert payload["known_moves"][0]["move_id"] == "shadow-ball"
    assert payload["known_moves"][0]["source"] == "user_confirmed"


def test_reducer_known_opponent_move_is_preserved_without_panel_selection():
    window = _window()
    record = _begin_with_reducer_known_opponent_moves(window, ("shadow-ball",))
    assert record["status"] == "captured", record
    assert record["public_information"]["public_snapshot"]["opponent_revealed_moves"] == {
        "status": "partial", "move_ids": ("shadow-ball",)}


def test_panel_selection_and_candidate_cannot_expand_reducer_known_moves():
    window = _window()
    panel = window._panels[("team_enemy", 0)]
    panel.selected_moves = [SimpleNamespace(move_id="candidate-move")]
    window._opponent_candidate_moves = lambda *_: ["another-candidate"]
    record = _begin_with_reducer_known_opponent_moves(window, ("shadow-ball",))
    assert record["status"] == "captured", record
    assert record["public_information"]["public_snapshot"]["opponent_revealed_moves"] == {
        "status": "partial", "move_ids": ("shadow-ball",)}
    assert panel.selected_moves[0].move_id == "candidate-move"


def test_empty_reducer_known_moves_remain_unknown_despite_panel_selection():
    window = _window()
    window._panels[("team_enemy", 0)].selected_moves = [SimpleNamespace(move_id="candidate-move")]
    record = _begin_with_reducer_known_opponent_moves(window, ())
    assert record["status"] == "captured", record
    assert record["public_information"]["public_snapshot"]["opponent_revealed_moves"] == {
        "status": "unknown", "move_ids": ()}


def test_capture_snapshot_is_deeply_read_only_and_context_is_copied():
    window = _window()
    original = deepcopy(CONTEXT)
    assert _begin(window)["status"] == "captured"
    result = MainWindow.read_c6_decision_capture_snapshot(window)
    with pytest.raises(TypeError):
        result["actor_captures"][0]["opportunities"]["opportunities"][0]["certificate"]["turn_number"] = 99
    assert CONTEXT == original
    assert result == MainWindow.read_c6_decision_capture_snapshot(window)


def test_battle_menu_dialogs_capture_opportunity_then_explicit_submitted_command(monkeypatch):
    window = _window()
    window._c6_explicit_context_reference = None
    prompts = iter(CONTEXT.values())
    monkeypatch.setattr(main_window_module.QInputDialog, "getText", lambda *_: (next(prompts), True))
    ints = iter(((3, True), (2, True)))
    monkeypatch.setattr(main_window_module.QInputDialog, "getInt", lambda *_: next(ints))
    MainWindow._open_c6_decision_capture(window)
    snapshot = MainWindow.read_c6_decision_capture_snapshot(window)
    assert len(snapshot["actor_captures"]) == 1
    assert snapshot["actor_captures"][0]["opportunities"]["opportunities"][0]["certificate"]["turn_number"] == 3
    assert snapshot["actor_captures"][0]["submitted_commands"]["command_evidence"] == ()
    assert window._current_trusted_turn_number == 1  # C6 prompt does not mutate runtime turn authority
    choices = iter(((snapshot["actor_captures"][0]["submitted_commands"]["command_unknown_boundary_ids"][0], True),
                    ("attack", True)))
    monkeypatch.setattr(main_window_module.QInputDialog, "getItem", lambda *_: next(choices))
    MainWindow._open_c6_submitted_command_confirmation(window)
    commands = MainWindow.read_c6_decision_capture_snapshot(window)["actor_captures"][0]["submitted_commands"]["command_evidence"]
    assert len(commands) == 1
    assert commands[0]["command_payload"] == {"kind": "attack", "move_slot": 2}
