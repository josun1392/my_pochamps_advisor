"""Experimental learned UI evidence leaves exact recommendations and truth intact."""

from copy import deepcopy
from pathlib import Path
import json
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_learned_strategy import valid_learned_evidence
from tests.test_showdown_strategy_evaluation import configuration
from tests.test_showdown_shadow_ui import run
from ui.strategy_explanation_presentation import (
    present_strategy_explanation,
    render_strategy_explanation,
)

ROOT = Path(__file__).resolve().parents[1]


def config():
    root = ROOT / "models/showdown_initial_v1"
    return {
        "schema_version": "showdown-learned-config-v1",
        "enabled": True,
        "model_path": str(root / "model.zip"),
        "catalog_path": str(root / "catalog.json"),
        "expected_model_id": json.loads((root / "model.json").read_text())[
            "model_sha256"
        ],
    }


@pytest.fixture(scope="module")
def proof():
    pytest.importorskip("sb3_contrib")
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    snapshot, builder, context = configuration(horizon=1)
    context["learned_policy"] = config()
    original = deepcopy((snapshot, context))
    with ShowdownWorker(checkout) as worker:
        baseline = run(snapshot, builder)
        result = run(
            snapshot, builder, showdown_context=context, showdown_bridge=worker
        )
    assert (snapshot, context) == original
    return baseline, result


def test_actual_learned_inference_and_existing_recommendation_equal(proof):
    baseline, result = proof
    for key in (
        "orchestration",
        "exact_outcome_ledgers",
        "descriptive_metrics",
        "opponent_response_profiles",
        "execution_coverage",
    ):
        assert result[key] == baseline[key]
    explanation = result["explanation"]
    evidence = explanation["sampled_simulation"]
    assert (
        explanation["preferred_frontier"]
        == baseline["explanation"]["preferred_frontier"]
    )
    for row in evidence["scenarios"]:
        assert row["learned_policy"]["status"] == "evaluated", row["learned_policy"]
        assert valid_learned_evidence(row["learned_policy"], evidence, row)
    presentation = present_strategy_explanation(explanation=explanation)
    assert presentation["status"] == "resolved"
    text = render_strategy_explanation(presentation=presentation)
    assert (
        "실험 학습 정책 (기본 추천에 미적용)" in text
        and "정책 선택 확률" in text
        and "승률 아님" in text
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.update(evidence_class="exact_conditional_distribution"),
        lambda e: e.update(session_id="foreign"),
        lambda e: e.update(source_capture_fingerprint="0" * 64),
        lambda e: e.update(root_checkpoint_fingerprint="0" * 64),
        lambda e: e.update(model_id="0" * 64),
        lambda e: e["inference"].update(request_state="ended"),
        lambda e: e["inference"].update(turn=999),
        lambda e: e["inference"].update(side="opponent"),
        lambda e: e["inference"].update(native_choice="move 99"),
        lambda e: e["inference"].update(discounted_return_estimate=float("nan")),
        lambda e: e["inference"].update(action_probabilities=[1.0] * 35),
        lambda e: e.update(default_policy_changed=True),
    ],
)
def test_invalid_model_evidence_is_never_displayed(proof, mutate):
    explanation = deepcopy(proof[1]["explanation"])
    mutate(explanation["sampled_simulation"]["scenarios"][0]["learned_policy"])
    assert present_strategy_explanation(explanation=explanation)["status"] == "rejected"


def test_missing_model_preserves_native_and_legacy_fallback():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    snapshot, builder, context = configuration(horizon=1)
    context["learned_policy"] = {**config(), "model_path": "missing-local-model.zip"}
    with ShowdownWorker(checkout) as worker:
        baseline = run(snapshot, builder)
        result = run(
            snapshot, builder, showdown_context=context, showdown_bridge=worker
        )
    assert result["orchestration"] == baseline["orchestration"]
    evidence = result["explanation"]["sampled_simulation"]
    assert evidence["status"] == "evaluated"
    assert all(
        r["learned_policy"]["status"] == "unavailable" for r in evidence["scenarios"]
    )
    assert (
        present_strategy_explanation(explanation=result["explanation"])["status"]
        == "resolved"
    )


def test_disabled_config_never_loads_model(monkeypatch):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    monkeypatch.setattr(
        "llm.advisor_learned_strategy._load_model",
        lambda *a: pytest.fail("disabled model loaded"),
    )
    snapshot, builder, context = configuration(horizon=1)
    context["learned_policy"] = {**config(), "enabled": False}
    with ShowdownWorker(checkout) as worker:
        result = run(
            snapshot, builder, showdown_context=context, showdown_bridge=worker
        )
    assert all(
        "learned_policy" not in r
        for r in result["explanation"]["sampled_simulation"]["scenarios"]
    )
