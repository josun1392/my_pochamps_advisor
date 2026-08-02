from __future__ import annotations

from copy import deepcopy

import pytest
from PySide6.QtWidgets import QApplication

from llm.advisor_battle_state_context import (
    build_current_type_context_from_confirmations,
    classify_current_type_dark_membership,
    normalize_current_type_authority,
)
from llm.advisor_candidate_contract import adapt_ui_battle_snapshot
from llm.advisor_turn_snapshot import capture_ui_current_state_provenance
from ui.widgets.current_type_dialog import CurrentTypeDialog


def _known(side: str = "self", types: list[str] | None = None) -> dict[str, object]:
    return {
        "side": side, "state": "known", "types": ["dark"] if types is None else types, "status": "user_confirmed",
        "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current",
    }


def _unknown(side: str = "self") -> dict[str, object]:
    return {"side": side, "state": "unknown", "status": "unknown", "source": "unknown", "authority_provenance": "unknown"}


@pytest.mark.parametrize("candidate", [
    _known(types=[]), _known(types=["dark", "dark"]), _known(types=["dark", "ghost", "fire"]),
    _known(types=["shadow"]), {**_known(), "authority_provenance": "unknown"},
    {**_unknown(), "types": ["dark"]},
])
def test_current_type_authority_rejects_invalid_and_never_infers(candidate: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        normalize_current_type_authority(candidate)


def test_current_type_context_distinguishes_known_dual_and_explicit_unknown() -> None:
    context = build_current_type_context_from_confirmations([_known(types=["dark", "ghost"]), _unknown("opponent")])
    assert context == {
        "current_types": [
            {**_known(types=["dark", "ghost"]), "confidence": "known"},
            {**_unknown("opponent"), "confidence": "unknown"},
        ]
    }
    assert classify_current_type_dark_membership(context, side="self") == "known_contains_dark"
    assert classify_current_type_dark_membership(context, side="opponent") == "unknown"
    assert classify_current_type_dark_membership(build_current_type_context_from_confirmations([_known(types=["fire"])]), side="self") == "known_does_not_contain_dark"


def _battle_input() -> dict[str, object]:
    return {"pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0, "types": ["electric"]}, "opponent_active": {"name_en": "umbreon", "slot_index": 1, "types": ["dark"]}}}


def _bound(entry: dict[str, object], *, slot: int, pokemon: str, session: str = "session-1") -> dict[str, object]:
    return {**entry, "provenance": {"side": entry["side"], "slot_index": slot, "pokemon_id": pokemon, "session_id": session, "source": entry["source"], "trust": entry["authority_provenance"]}}


def test_snapshot_uses_only_bound_current_types_and_is_detached_from_ui_or_species_types() -> None:
    raw = _battle_input()
    known = _bound(_known(), slot=0, pokemon="pikachu")
    captured = capture_ui_current_state_provenance(raw, session_id="session-1", current_type_confirmations=[known, _unknown("opponent")])
    raw["pokemon"]["my_active"]["types"] = ["fire"]  # type: ignore[index]
    known["types"] = ["fire"]
    assert captured["current_type_context"]["current_types"][0]["types"] == ["dark"]  # type: ignore[index]
    assert captured["current_type_context"]["current_types"][1]["state"] == "unknown"  # type: ignore[index]
    assert "current_type_context" not in capture_ui_current_state_provenance(_battle_input(), session_id="session-1")
    stale = capture_ui_current_state_provenance(_battle_input(), session_id="session-2", current_type_confirmations=[known])
    assert "current_type_context" not in stale


def test_candidate_adapter_passes_current_type_context_without_provider_or_species_fallback() -> None:
    snapshot = adapt_ui_battle_snapshot(battle_input={
        **_battle_input(),
        "current_type_context": {"current_types": [{**_known(types=["dark"]), "confidence": "known"}]},
    })
    assert snapshot["current_type_context"]["current_types"][0]["types"] == ["dark"]  # type: ignore[index]
    omitted = adapt_ui_battle_snapshot(battle_input=_battle_input())
    assert "current_type_context" not in omitted


def test_dark_classifier_fails_closed_for_malformed_or_duplicate_entries() -> None:
    assert classify_current_type_dark_membership({"current_types": [{**_known(), "types": ["dark", "dark"]}]}, side="self") == "malformed"
    assert classify_current_type_dark_membership({"current_types": [{**_known()}, deepcopy(_known())]}, side="self") == "malformed"


def test_current_type_dialog_requires_an_explicit_unknown_or_exact_type_input() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = CurrentTypeDialog()
    dialog._save_and_accept()
    assert dialog.current_type_confirmation == {**_unknown(), "confidence": "unknown"}
    dialog = CurrentTypeDialog()
    dialog.state_combo.setCurrentIndex(1)
    dialog.primary_type_edit.setText("Dark")
    dialog.secondary_type_edit.setText("Ghost")
    dialog._save_and_accept()
    assert dialog.current_type_confirmation == {**_known(types=["dark", "ghost"]), "confidence": "known"}
