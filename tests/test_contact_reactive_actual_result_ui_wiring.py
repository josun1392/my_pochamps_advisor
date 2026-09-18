"""Focused production UI wiring for actual observed contact-reactive results."""
from __future__ import annotations

import inspect
from copy import deepcopy
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit

import ui.main_window as main_window_module
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_reducer_state_model import project_atomic_transition
from ui.main_window import MainWindow
from ui.widgets.contact_reactive_result_dialog import (
    ContactReactiveDamageResultDialog,
    ContactStatusResultDialog,
)
from ui.widgets.current_observed_damage_dialog import CurrentObservedDamageDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


SESSION = "contact-ui"


class _Button:
    def __init__(self) -> None:
        self.disabled: list[bool] = []

    def setDisabled(self, value: bool) -> None:
        self.disabled.append(value)


class _Panel:
    def __init__(self) -> None:
        self.clear_readiness_calls = 0
        self.running: list[bool] = []
        self.structured_request_button = _Button()

    def clear_recommendation_readiness(self) -> None:
        self.clear_readiness_calls += 1

    def set_running(self, value: bool) -> None:
        self.running.append(value)


class _Status:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def showMessage(self, message: str) -> None:
        self.messages.append(message)


class _Harness:
    _active_session_id = MainWindow._active_session_id
    _selected_identity = MainWindow._selected_identity
    _loaded_roster_identities = MainWindow._loaded_roster_identities
    _begin_new_battle_session = MainWindow._begin_new_battle_session
    begin_new_battle = MainWindow.begin_new_battle
    _retire_advice_presentation_authority = MainWindow._retire_advice_presentation_authority
    _reset_battle_presentation = MainWindow._reset_battle_presentation
    _open_contact_status_result_dialog = MainWindow._open_contact_status_result_dialog
    _open_contact_reactive_damage_dialog = MainWindow._open_contact_reactive_damage_dialog
    _submit_contact_status_result = MainWindow._submit_contact_status_result
    _submit_contact_reactive_damage_result = MainWindow._submit_contact_reactive_damage_result
    _resolve_contact_source_action_id = MainWindow._resolve_contact_source_action_id
    _finalize_contact_result = MainWindow._finalize_contact_result
    _retire_stale_contact_current_state_mirrors = MainWindow._retire_stale_contact_current_state_mirrors
    _present_contact_result_status = MainWindow._present_contact_result_status

    def __init__(self, manager: BattleObservationRuntimeSessionManager) -> None:
        self._observation_runtime_session_manager = manager
        self._current_trusted_turn_number = 2
        self._contact_result_action_ids: dict[tuple[str, str, int, str], str] = {}
        self._recommendation_readiness_owner = (manager.session_id, 0, "self-a")
        self._active_advice_owner = "structured"
        self._active_advice_request_token = 7
        self._active_advice_terminal_token = 7
        self._current_hp_confirmations = {
            "self": {"current_hp": 80},
            "opponent": {"current_hp": 100},
        }
        self._current_hp_confirmation_owners = {
            "self": (manager.session_id, 0, "self-a"),
            "opponent": (manager.session_id, 0, "opponent-a"),
        }
        self._current_condition_confirmations = {
            "self": {"condition_type": "none"},
            "opponent": {"condition_type": "none"},
        }
        self.panel = _Panel()
        self.center_column = SimpleNamespace(llm_advice_panel=self.panel)
        self.status = _Status()
        self._battle_session_sequence = 0
        self.selected_slots = {"team_my": 0, "team_enemy": 0}
        self._panels = {
            ("team_my", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en="self-a")),
            ("team_enemy", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en="opponent-a")),
        }
        self._structured_ability_confirmations = {}
        self._current_persistent_effect_confirmations = {}
        self._current_type_confirmations = {}
        self._structured_type_confirmations = {}
        self._current_stat_stage_confirmations = {}
        self._current_final_stat_confirmations = {}
        self._structured_final_stat_confirmations = {}
        self._current_observed_damage_confirmation = {"damage": 9}
        self._structured_observed_damage_confirmations = [{"legacy": True}]
        self._item_event_confirmations = [{"legacy": True}]
        self._current_field_state_confirmation = {"legacy": True}
        self._grounded_context_confirmation = {
            "self": {"status": "unknown", "provenance": "unknown"},
            "opponent": {"status": "unknown", "provenance": "unknown"},
        }
        self._battle_counter_confirmation = {"legacy": 1}
        self._consecutive_use_confirmation = {"legacy": 1}

    def statusBar(self) -> _Status:
        return self.status

    def _slot_panel(self, column: str, slot: int):
        return self._panels[(column, slot)]


class _FakeDialog:
    def __init__(self, result: QDialog.DialogCode, confirmation: dict | None) -> None:
        self._result = result
        self.confirmation = deepcopy(confirmation)

    def exec(self) -> QDialog.DialogCode:
        return self._result


def _runtime_manager(
    *,
    session_id: str = SESSION,
    attacker_side: str = "self",
    attacker_hp: int | str = 80,
    attacker_max_hp: int | str = 80,
    defender_hp: int = 100,
    defender_max_hp: int = 100,
    attacker_ability: str = "pressure",
    defender_ability: str = "static",
    attacker_item: str | None = None,
    defender_item: str | None = None,
    attacker_type: str = "normal",
    defender_type: str = "normal",
    unknown_defender_item: bool = False,
    unknown_defender_ability: bool = False,
) -> BattleObservationRuntimeSessionManager:
    state = create_unknown_bootstrap_battle_state(session_id, "self-a", "opponent-a")["state"]
    defender_side = "opponent" if attacker_side == "self" else "self"

    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        if side == attacker_side:
            if attacker_hp != "unknown" and attacker_max_hp != "unknown":
                pokemon["current_hp"] = attacker_hp
                pokemon["max_hp"] = attacker_max_hp
            pokemon["fainted"] = False
        else:
            pokemon["current_hp"] = defender_hp
            pokemon["max_hp"] = defender_max_hp
            pokemon["fainted"] = False

    config = {
        attacker_side: {
            "ability": attacker_ability,
            "item": attacker_item,
            "type": attacker_type,
            "unknown_item": False,
            "unknown_ability": False,
        },
        defender_side: {
            "ability": defender_ability,
            "item": defender_item,
            "type": defender_type,
            "unknown_item": unknown_defender_item,
            "unknown_ability": unknown_defender_ability,
        },
    }

    steps: list[dict] = []
    sequence = 0
    for side in ("self", "opponent"):
        pokemon_id = state[f"{side}_side"]["pokemon"][0]["pokemon_id"]
        facts: list[tuple[str, dict]] = [
            ("set_current_condition", {"condition": "none"}),
            ("set_current_type", {"types": [config[side]["type"]]}),
        ]
        if not config[side]["unknown_ability"]:
            facts.append(("set_current_ability", {"ability": config[side]["ability"]}))
        if not config[side]["unknown_item"]:
            facts.append(
                (
                    "set_current_item",
                    {"status": "known", "item": config[side]["item"]}
                    if config[side]["item"] is not None
                    else {"status": "known_absent"},
                )
            )
        for effect, data in facts:
            sequence += 1
            steps.append(
                {
                    "observation_id": f"seed:{sequence}",
                    "observation_sequence": sequence,
                    "planned_effect": effect,
                    "trust": "user_confirmed_observation",
                    "turn_number": 1,
                    "side": side,
                    "slot_index": 0,
                    "pokemon_id": pokemon_id,
                    **data,
                }
            )

    projected = project_atomic_transition(
        state,
        {"session_id": session_id, "status": "planned", "conflicts": [], "ordered_steps": steps},
        session_id,
    )
    assert projected["status"] == "ready_with_projected_state", projected
    created = BattleObservationRuntimeSessionManager.create(session_id, projected["projected_state"])
    assert created["status"] == "session_ready", created
    return created["manager"]


def _status_confirmation(
    *,
    attacker_side: str = "self",
    move_id: str = "tackle",
    turn_number: int = 2,
    target_hp_after: int = 90,
    outcome: str = "activation",
) -> dict:
    return {
        "attacker_side": attacker_side,
        "move_id": move_id,
        "turn_number": turn_number,
        "target_hp_after": target_hp_after,
        "outcome": outcome,
    }


def _damage_confirmation(
    *,
    attacker_side: str = "self",
    move_id: str = "tackle",
    turn_number: int = 2,
    attacker_hp_after: int = 70,
    source_hit_actual_damage: int = 10,
    routing: str | None = "target",
) -> dict:
    return {
        "attacker_side": attacker_side,
        "move_id": move_id,
        "turn_number": turn_number,
        "attacker_hp_after": attacker_hp_after,
        "source_hit_actual_damage": source_hit_actual_damage,
        "source_hit_target_routing": routing,
    }


def _pokemon(manager: BattleObservationRuntimeSessionManager, side: str) -> dict:
    return manager.read_state()["state"][f"{side}_side"]["pokemon"][0]


def _rows(manager: BattleObservationRuntimeSessionManager, kind: str) -> list[dict]:
    return [
        row
        for row in manager.read_collection_snapshot()["ordered_observations"]
        if row["event_kind"] == kind
    ]


def test_status_ui_explicit_confirmation_reaches_real_canonical_owner_self_attacker():
    manager = _runtime_manager(defender_ability="static")
    window = _Harness(manager)
    result = window._submit_contact_status_result(_status_confirmation())

    assert result["status"] == "resolved", result
    assert _pokemon(manager, "opponent")["current_hp"] == 90
    assert _pokemon(manager, "self")["condition"] == "paralysis"
    assert len(_rows(manager, "contact_reactive_status_result_observed")) == 1
    assert window._active_advice_owner is None
    assert window.panel.clear_readiness_calls == 1


def test_status_ui_opponent_attacker_path_is_side_neutral():
    manager = _runtime_manager(attacker_side="opponent", defender_ability="flame-body")
    window = _Harness(manager)
    result = window._submit_contact_status_result(
        _status_confirmation(attacker_side="opponent", target_hp_after=90)
    )

    assert result["status"] == "resolved", result
    assert _pokemon(manager, "self")["current_hp"] == 90
    assert _pokemon(manager, "opponent")["condition"] == "burn"


def test_effect_spore_exact_outcome_is_forwarded_without_ui_rng_logic():
    manager = _runtime_manager(defender_ability="effect-spore")
    window = _Harness(manager)
    result = window._submit_contact_status_result(
        _status_confirmation(outcome="sleep")
    )

    assert result["status"] == "resolved", result
    receipt = _rows(manager, "contact_reactive_status_result_observed")[0]
    assert receipt["payload"]["reactive_ability"] == "effect-spore"
    assert receipt["payload"]["outcome"] == "sleep"
    assert _pokemon(manager, "self")["condition"] == "sleep"


def test_status_ui_forwards_defender_ko_zero_hp_and_preserves_replacement_boundary():
    manager = _runtime_manager(defender_hp=10, defender_max_hp=100, defender_ability="static")
    window = _Harness(manager)
    result = window._submit_contact_status_result(
        _status_confirmation(target_hp_after=0)
    )

    assert result["status"] == "resolved" and result["strategy_d0"] is None
    assert _pokemon(manager, "opponent")["current_hp"] == 0
    assert _pokemon(manager, "opponent")["fainted"] is True
    assert result["replacement_boundary"]["status"] == "replacement_required_after_faint"


def test_damage_ui_explicit_confirmation_reaches_real_canonical_owner_self_attacker():
    manager = _runtime_manager(defender_ability="rough-skin")
    window = _Harness(manager)
    result = window._submit_contact_reactive_damage_result(_damage_confirmation())

    assert result["status"] == "resolved", result
    assert _pokemon(manager, "self")["current_hp"] == 70
    receipt = _rows(manager, "contact_reactive_damage_result_observed")[0]
    assert [row["source_kind"] for row in receipt["payload"]["ordered_sources"]] == ["rough-skin"]


def test_damage_ui_opponent_attacker_path_is_side_neutral():
    manager = _runtime_manager(attacker_side="opponent", defender_ability="iron-barbs")
    window = _Harness(manager)
    result = window._submit_contact_reactive_damage_result(
        _damage_confirmation(attacker_side="opponent")
    )

    assert result["status"] == "resolved", result
    assert _pokemon(manager, "opponent")["current_hp"] == 70
    receipt = _rows(manager, "contact_reactive_damage_result_observed")[0]
    assert receipt["payload"]["attacker_side"] == "opponent"
    assert receipt["payload"]["defender_side"] == "self"


def test_damage_ui_attacker_reactive_ko_returns_generic_replacement_boundary_without_d0():
    manager = _runtime_manager(attacker_hp=10, attacker_max_hp=80, defender_ability="rough-skin")
    window = _Harness(manager)
    result = window._submit_contact_reactive_damage_result(
        _damage_confirmation(attacker_hp_after=0)
    )

    assert result["status"] == "resolved" and result["strategy_d0"] is None
    assert _pokemon(manager, "self")["current_hp"] == 0
    assert _pokemon(manager, "self")["fainted"] is True
    assert result["replacement_boundary"]["status"] == "replacement_required_after_faint"
    assert "replacement required" in window.status.messages[-1]


def test_exact_ui_retry_reuses_same_source_action_and_allocates_nothing_new():
    manager = _runtime_manager(defender_ability="rough-skin")
    window = _Harness(manager)
    first = window._submit_contact_reactive_damage_result(_damage_confirmation())
    assert first["status"] == "resolved"
    execution = _rows(manager, "executed_move_observed")[0]
    source_action_id = execution["payload"]["source_action_id"]
    before_collection = manager.read_collection_snapshot()
    before_sequence = manager.last_allocated_sequence

    retry = window._submit_contact_reactive_damage_result(_damage_confirmation())

    assert retry["status"] == "resolved" and retry["idempotent"] is True
    assert _rows(manager, "executed_move_observed")[0]["payload"]["source_action_id"] == source_action_id
    assert manager.read_collection_snapshot() == before_collection
    assert manager.last_allocated_sequence == before_sequence
    assert len(_rows(manager, "contact_reactive_damage_result_observed")) == 1
    assert len(_rows(manager, "exact_hp_transition_observed")) == 1


def test_status_ui_retry_reuses_action_without_duplicate_receipt_hp_or_condition():
    manager = _runtime_manager(defender_ability="static")
    window = _Harness(manager)
    first = window._submit_contact_status_result(_status_confirmation())
    assert first["status"] == "resolved"
    before_collection = manager.read_collection_snapshot()
    before_sequence = manager.last_allocated_sequence

    retry = window._submit_contact_status_result(_status_confirmation())

    assert retry["status"] == "resolved" and retry["idempotent"] is True
    assert manager.read_collection_snapshot() == before_collection
    assert manager.last_allocated_sequence == before_sequence
    assert len(_rows(manager, "executed_move_observed")) == 1
    assert len(_rows(manager, "contact_reactive_status_result_observed")) == 1
    assert len(_rows(manager, "exact_hp_transition_observed")) == 1
    assert len(_rows(manager, "current_condition_observed")) == 1


def test_damage_ko_ui_retry_does_not_duplicate_hp_faint_or_receipt():
    manager = _runtime_manager(attacker_hp=10, attacker_max_hp=80, defender_ability="rough-skin")
    window = _Harness(manager)
    confirmation = _damage_confirmation(attacker_hp_after=0)
    first = window._submit_contact_reactive_damage_result(confirmation)
    assert first["status"] == "resolved"
    before_collection = manager.read_collection_snapshot()
    before_sequence = manager.last_allocated_sequence

    retry = window._submit_contact_reactive_damage_result(confirmation)

    assert retry["status"] == "resolved" and retry["idempotent"] is True
    assert manager.read_collection_snapshot() == before_collection
    assert manager.last_allocated_sequence == before_sequence
    assert len(_rows(manager, "contact_reactive_damage_result_observed")) == 1
    assert len(_rows(manager, "exact_hp_transition_observed")) == 1
    assert len(_rows(manager, "pokemon_faint_observed")) == 1


def test_status_and_damage_surfaces_share_unique_existing_execution_identity():
    manager = _runtime_manager(
        attacker_hp=80,
        attacker_max_hp=80,
        defender_ability="static",
        defender_item="rocky-helmet",
    )
    window = _Harness(manager)
    status = window._submit_contact_status_result(_status_confirmation())
    assert status["status"] == "resolved", status
    source_action_id = _rows(manager, "executed_move_observed")[0]["payload"]["source_action_id"]

    damage = window._submit_contact_reactive_damage_result(
        _damage_confirmation(attacker_hp_after=67)
    )
    assert damage["status"] == "resolved", damage
    executions = _rows(manager, "executed_move_observed")
    assert len(executions) == 1
    assert executions[0]["payload"]["source_action_id"] == source_action_id
    assert _rows(manager, "contact_reactive_damage_result_observed")[0]["payload"]["source_action_id"] == source_action_id


def test_unique_compatible_previous_action_execution_is_reused():
    manager = _runtime_manager(defender_ability="rough-skin")
    existing = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id=SESSION,
        side="self",
        execution_move_id="tackle",
        selected_move_id="tackle",
        source_action_id="action:existing",
        result_class=None,
        turn_number=2,
    )
    assert existing["status"] == "resolved"
    window = _Harness(manager)

    result = window._submit_contact_reactive_damage_result(_damage_confirmation())

    assert result["status"] == "resolved"
    assert len(_rows(manager, "executed_move_observed")) == 1
    assert _rows(manager, "contact_reactive_damage_result_observed")[0]["payload"]["source_action_id"] == "action:existing"


def test_opening_then_cancelling_both_surfaces_causes_no_runtime_or_sequence_mutation(monkeypatch: pytest.MonkeyPatch):
    manager = _runtime_manager(defender_ability="rough-skin")
    window = _Harness(manager)
    before = (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence)

    monkeypatch.setattr(
        main_window_module,
        "ContactStatusResultDialog",
        lambda *, default_turn, parent: _FakeDialog(QDialog.DialogCode.Rejected, _status_confirmation()),
    )
    window._open_contact_status_result_dialog()
    monkeypatch.setattr(
        main_window_module,
        "ContactReactiveDamageResultDialog",
        lambda *, default_turn, parent: _FakeDialog(QDialog.DialogCode.Rejected, _damage_confirmation()),
    )
    window._open_contact_reactive_damage_dialog()

    assert (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence) == before
    assert window._contact_result_action_ids == {}


def test_stale_captured_session_fails_closed_without_touching_new_session():
    manager = _runtime_manager(session_id="old-contact-ui", defender_ability="rough-skin")
    window = _Harness(manager)
    old = manager.session_id
    replacement = create_unknown_bootstrap_battle_state("new-contact-ui", "self-a", "opponent-a")["state"]
    rolled = manager.rollover("new-contact-ui", replacement)
    assert rolled["status"] == "session_replaced"
    before = (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence)

    result = window._submit_contact_reactive_damage_result(
        _damage_confirmation(),
        captured_session_id=old,
    )

    assert result["status"] == "rejected"
    assert (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence) == before
    assert window._contact_result_action_ids == {}


def test_missing_current_reactive_authority_fails_closed_without_retiring_recommendation():
    manager = _runtime_manager(
        defender_ability="rough-skin",
        unknown_defender_item=True,
    )
    window = _Harness(manager)
    before = (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence)
    owner_before = window._active_advice_owner
    readiness_before = window._recommendation_readiness_owner

    result = window._submit_contact_reactive_damage_result(_damage_confirmation())

    assert result["status"] == "incomplete"
    assert (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence) == before
    assert window._active_advice_owner == owner_before
    assert window._recommendation_readiness_owner == readiness_before
    assert window.panel.clear_readiness_calls == 0


def test_readiness_and_advice_retire_only_after_runtime_changing_success():
    manager = _runtime_manager(defender_ability="rough-skin")
    window = _Harness(manager)

    rejected = window._submit_contact_reactive_damage_result(
        _damage_confirmation(attacker_hp_after=69)
    )
    assert rejected["status"] == "rejected"
    assert window._active_advice_owner == "structured"
    assert window._recommendation_readiness_owner is not None
    assert window.panel.clear_readiness_calls == 0

    resolved = window._submit_contact_reactive_damage_result(_damage_confirmation())
    assert resolved["status"] == "resolved"
    assert window._active_advice_owner is None
    assert window._recommendation_readiness_owner is None
    assert window.panel.clear_readiness_calls == 1


def test_resolved_known_no_effect_does_not_retire_recommendation_without_runtime_change():
    manager = _runtime_manager(defender_ability="pressure", defender_item=None)
    window = _Harness(manager)
    before_fingerprint = manager.read_state()["state_fingerprint"]

    result = window._submit_contact_reactive_damage_result(
        _damage_confirmation(attacker_hp_after=80)
    )

    assert result["status"] == "resolved" and result["observations"] == []
    assert manager.read_state()["state_fingerprint"] == before_fingerprint
    assert window._active_advice_owner == "structured"
    assert window._recommendation_readiness_owner is not None
    assert window.panel.clear_readiness_calls == 0


def test_unknown_damage_routing_is_not_fabricated_and_owner_is_not_called():
    manager = _runtime_manager(defender_ability="rough-skin")
    window = _Harness(manager)
    before = (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence)

    result = window._submit_contact_reactive_damage_result(
        _damage_confirmation(routing=None)
    )

    assert result == {"status": "incomplete", "reason": "contact_target_routing_unconfirmed"}
    assert (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence) == before
    assert window._contact_result_action_ids == {}


def test_new_battle_reset_clears_contact_action_identity_cache():
    manager = _runtime_manager(session_id="ui-session-0", defender_ability="rough-skin")
    window = _Harness(manager)
    window._contact_result_action_ids = {("ui-session-0", "self", 2, "tackle"): "contact:cached"}

    new_session = window.begin_new_battle()

    assert new_session == "ui-session-1"
    assert window._contact_result_action_ids == {}
    assert manager.session_id == "ui-session-1"


def test_legacy_previous_damage_dialog_semantics_are_unchanged():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = CurrentObservedDamageDialog(observed_damage=None)
    dialog.damage.setText("17")
    dialog.category.setCurrentIndex(dialog.category.findData("special"))
    dialog._save()

    assert dialog.observed_damage_confirmation == {
        "damage": 17,
        "damage_category": "special",
        "damage_kind": "direct_move_damage",
        "source_side": "opponent",
        "target_side": "self",
    }
    source = inspect.getsource(MainWindow._open_current_observed_damage_dialog)
    assert "CurrentObservedDamageDialog" in source
    assert "contact_reactive" not in source


def test_contact_dialogs_do_not_expose_manual_source_action_id_or_ability_choice():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    status = ContactStatusResultDialog(default_turn=2)
    damage = ContactReactiveDamageResultDialog(default_turn=2)

    assert not hasattr(status, "source_action_id")
    assert not hasattr(damage, "source_action_id")
    assert not hasattr(status, "ability_combo")
    assert status.move_id_edit in status.findChildren(QLineEdit)
    assert damage.move_id_edit in damage.findChildren(QLineEdit)
    assert all("source_action" not in child.objectName().lower() for child in status.findChildren(QLineEdit))
    assert all("source_action" not in child.objectName().lower() for child in damage.findChildren(QLineEdit))
    assert status.move_id_edit.placeholderText() == "e.g. tackle"
    assert damage.routing_combo.currentData() is None


def test_selection_and_button_surface_alone_are_not_observations():
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    emitted = []
    panel.contact_status_result_requested.connect(lambda: emitted.append("status"))
    panel.contact_reactive_damage_requested.connect(lambda: emitted.append("damage"))

    panel.contact_status_result_button.click()
    panel.contact_reactive_damage_button.click()

    assert emitted == ["status", "damage"]
    move_selection_source = inspect.getsource(MainWindow._on_move_selected)
    assert "admit_observed_contact_reactive" not in move_selection_source
    assert "_submit_contact_" not in move_selection_source


def test_ui_wiring_calls_only_runtime_owners_and_contains_no_reactive_formula():
    status_source = inspect.getsource(MainWindow._submit_contact_status_result)
    damage_source = inspect.getsource(MainWindow._submit_contact_reactive_damage_result)
    dialog_source = inspect.getsource(main_window_module.ContactReactiveDamageResultDialog)

    assert "admit_observed_contact_reactive_status_result" in status_source
    assert "admit_observed_contact_reactive_damage_result" in damage_source
    assert "rough-skin" not in damage_source
    assert "iron-barbs" not in damage_source
    assert "rocky-helmet" not in damage_source
    assert "// 6" not in damage_source and "// 8" not in damage_source
    assert "rough-skin" not in dialog_source
    assert "// 6" not in dialog_source and "// 8" not in dialog_source
