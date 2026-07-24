"""Offline inventory contracts for the existing structured runtime boundary."""
import inspect

import llm.advisor_client as client
from llm.advisor_candidate_contract import build_recommendation_presentation_model
from ui.main_window import MainWindow, StructuredRecommendationWorker


RUNTIME_BOUNDARY_INVENTORY = (
    {"stage_id": "ui_start", "symbol": "MainWindow._start_structured_recommendation", "trust": "ui_input", "production_connected": True, "offline_coverage": True, "gap": "same_owner_request_sequence_not_consumed"},
    {"stage_id": "worker", "symbol": "StructuredRecommendationWorker.run", "trust": "copied_ui_input", "production_connected": True, "offline_coverage": True, "gap": None},
    {"stage_id": "prepare", "symbol": "prepare_ui_recommendation_cycle", "trust": "deterministic", "production_connected": True, "offline_coverage": True, "gap": None},
    {"stage_id": "provider", "symbol": "call_structured_recommendation_provider", "trust": "unvalidated_provider_mapping", "production_connected": True, "offline_coverage": True, "gap": "actual_provider_budget_closed"},
    {"stage_id": "adapter", "symbol": "adapt_provider_recommendation_response", "trust": "six_field_schema", "production_connected": True, "offline_coverage": True, "gap": None},
    {"stage_id": "completion", "symbol": "complete_recommendation_cycle", "trust": "semantic_validated", "production_connected": True, "offline_coverage": True, "gap": None},
    {"stage_id": "presentation", "symbol": "build_recommendation_presentation_model", "trust": "ui_neutral_validated", "production_connected": True, "offline_coverage": True, "gap": None},
    {"stage_id": "panel", "symbol": "MainWindow._on_structured_recommendation_finished", "trust": "formatted_sanitized_text", "production_connected": True, "offline_coverage": True, "gap": "same_owner_request_sequence_not_consumed"},
)


def _completed(status, *, move=None, slot=None, errors=()):
    return {
        "status": status,
        "candidates": [],
        "errors": list(errors),
        "recommendation_result": {
            "status": status,
            "recommended_move": move,
            "recommended_slot_index": slot,
            "primary_reasons": [],
            "risks": [],
            "alternatives": [],
            "errors": [],
        },
    }


def test_runtime_inventory_covers_production_stages_and_explicitly_records_remaining_gaps():
    assert [entry["stage_id"] for entry in RUNTIME_BOUNDARY_INVENTORY] == [
        "ui_start", "worker", "prepare", "provider", "adapter", "completion", "presentation", "panel",
    ]
    assert all(entry["production_connected"] and entry["offline_coverage"] for entry in RUNTIME_BOUNDARY_INVENTORY)
    assert {entry["gap"] for entry in RUNTIME_BOUNDARY_INVENTORY if entry["gap"]} == {
        "same_owner_request_sequence_not_consumed", "actual_provider_budget_closed",
    }


def test_structured_runtime_orders_validation_before_presentation_and_has_no_legacy_fallback():
    source = inspect.getsource(client.run_structured_ui_recommendation)
    assert source.index("prepare_ui_recommendation_cycle") < source.index("build_provider_recommendation_payload")
    assert source.index("call_structured_recommendation_provider") < source.index("adapt_provider_recommendation_response")
    assert source.index("adapt_provider_recommendation_response") < source.index("complete_recommendation_cycle")
    assert source.index("complete_recommendation_cycle") < source.rindex("build_recommendation_presentation_model")
    assert "run_ui_selected_advice" not in source and "call_gemini" not in source


def test_invalid_and_nonresolved_completion_models_cannot_expose_resolved_pair():
    invalid = build_recommendation_presentation_model(
        completed_cycle=_completed("validation_failed", move="outside", slot=9, errors=("provider_response_validation_failed",)),
    )
    insufficient = build_recommendation_presentation_model(
        completed_cycle=_completed("insufficient_context", move=None, slot=None),
    )
    no_usable = build_recommendation_presentation_model(
        completed_cycle=_completed("no_usable_candidate", move=None, slot=None),
    )
    assert invalid["status"] == "validation_failed" and invalid["recommended_move"] is None
    assert invalid["recommended_slot_index"] is None and invalid["errors"] == ["provider_response_validation_failed"]
    assert insufficient["recommended_move"] is None and insufficient["recommended_slot_index"] is None
    assert no_usable["recommended_move"] is None and no_usable["recommended_slot_index"] is None


def test_structured_worker_sanitizes_exceptions_and_panel_callback_requires_structured_owner():
    worker_source = inspect.getsource(StructuredRecommendationWorker.run)
    callback_source = inspect.getsource(MainWindow._on_structured_recommendation_finished)
    assert "self.failed.emit(" in worker_source and "except Exception" in worker_source
    assert "str(exc)" not in worker_source and "traceback" not in worker_source
    assert 'self._active_advice_owner != "structured"' in callback_source
    assert "format_recommendation_presentation_text" in callback_source


def test_preparation_failure_cannot_create_provider_or_retain_raw_response(monkeypatch):
    calls = []
    monkeypatch.setattr(client, "call_structured_recommendation_provider", lambda **_: calls.append("called"))
    result = client.run_structured_ui_recommendation(
        selected_moves=[], battle_input={"scenario": {"mode": "advisor"}, "pokemon": {}}, move_repository={}, model="offline",
    )
    assert result["status"] == "preparation_not_ready"
    assert calls == [] and "raw_response" not in result and "response_payload" not in result
