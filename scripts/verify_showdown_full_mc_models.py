"""Offline reload/mask/Qt rollback proof for validation-selected study artifacts."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from copy import deepcopy
import json
from time import perf_counter

from PySide6.QtWidgets import QApplication
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.showdown_environment import ShowdownEnvironment
from advisor.showdown_worker import ShowdownWorker
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    atomic_json,
    enforce_local_network_only,
)
from tests.test_showdown_strategy_evaluation import configuration
from tests.test_showdown_shadow_ui import run
from llm.advisor_learned_strategy import valid_learned_evidence
from ui.widgets.llm_advice_panel import LLMAdvicePanel

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "models/showdown_full_mc_study_v1"


def verify(checkout):
    job = WindowsJob(memory_mib=4096, cpu_percent=12.5)
    budget = RuntimeLimit(ARTIFACT, 180)
    network = enforce_local_network_only()
    started = perf_counter()
    catalog = ROOT / "models/showdown_mc_domain_v1/catalog.json"
    training = json.loads((ARTIFACT / "training.json").read_text())
    rows = []
    with ShowdownEnvironment(checkout) as env:
        env.reset(
            scenario("validation", 1521097, version="showdown-learning-curriculum-v8")
        )
        view = env.observation("self", include_history=True)
        original = deepcopy(view)
        for path in sorted((ARTIFACT / "selected").glob("*/model.zip")):
            policy = LearnedPolicy(path, catalog)
            proof = policy.infer(view)
            assert view == original and view["action_mask"][proof["action_index"]]
            assert sum(proof["action_probabilities"]) > 0.999
            rows.append(
                {
                    "model": path.parent.name,
                    "sha256": policy.model_id,
                    "legal_action": proof["native_choice"],
                    "missing_public_catalog_species": proof["public_catalog_coverage"][
                        "missing_species"
                    ],
                }
            )
    eligible = {
        name: row
        for name, row in training["selected"].items()
        if name.startswith("roster_")
        and name.endswith("warm")
        and "excluded" not in row
    }
    best = max(eligible, key=lambda name: eligible[name]["score"])
    path = ARTIFACT / "selected" / best / "model.zip"
    policy = LearnedPolicy(path, catalog)
    snapshot, builder, context = configuration(horizon=1)
    original = deepcopy((snapshot, context))
    with ShowdownWorker(checkout) as worker:
        baseline = run(snapshot, builder)
        context["learned_policy"] = {
            "schema_version": "showdown-learned-config-v1",
            "enabled": True,
            "model_path": str(path),
            "catalog_path": str(catalog),
            "expected_model_id": policy.model_id,
        }
        after_config = deepcopy(context)
        result = run(
            snapshot, builder, showdown_context=context, showdown_bridge=worker
        )
    assert snapshot == original[0] and context == after_config
    for key in (
        "orchestration",
        "exact_outcome_ledgers",
        "descriptive_metrics",
        "opponent_response_profiles",
        "execution_coverage",
    ):
        assert result[key] == baseline[key]
    assert (
        result["explanation"]["preferred_frontier"]
        == baseline["explanation"]["preferred_frontier"]
    )
    evidence = result["explanation"]["sampled_simulation"]
    assert all(
        s["learned_policy"]["status"] == "evaluated"
        and valid_learned_evidence(s["learned_policy"], evidence, s)
        for s in evidence["scenarios"]
    )
    app = QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    emitted = []
    panel.advice_requested.connect(lambda: emitted.append(True))
    assert panel.set_strategy_explanation(result["explanation"])["status"] == "resolved"
    assert "기본 추천에 미적용" in panel.output_edit.toPlainText() and emitted == []
    panel.close()
    app.processEvents()
    atomic_json(
        ARTIFACT / "compatibility.json",
        {
            "selected_reload_results": rows,
            "ui_model": best,
            "ui_scenarios": len(evidence["scenarios"]),
            "runtime_truth_immutable": True,
            "exact_ledgers_and_preferred_frontier_equal": True,
            "external_provider_requests": 0,
            "network": network,
            "elapsed_s": perf_counter() - started,
            "preview_policy_implemented": False,
            "production_default_changed": False,
            "resources": job.usage(),
        },
    )
    budget.finished.set()
    print(
        json.dumps(
            {
                "reloads": len(rows),
                "ui_scenarios": len(evidence["scenarios"]),
                "default_unchanged": True,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    verify(parser.parse_args().checkout)
