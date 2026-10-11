"""Actual Qt inference, native continuity, latency and rollback; no training."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse, json, statistics
from collections import Counter
from contextlib import redirect_stdout
import io
from time import perf_counter, process_time
from PySide6.QtWidgets import QApplication
from advisor.learned_policy import LearnedPolicy
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_scenarios import scenario
from advisor.showdown_environment import ShowdownEnvironment
from scripts.verify_showdown_strategy import configuration, demo_window, wait

ROOT = Path(__file__).resolve().parents[1]


def python_peak_rss_mib():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (key, ctypes.c_size_t)
                for key in (
                    "peak_working_set",
                    "working_set",
                    "peak_paged",
                    "paged",
                    "peak_nonpaged",
                    "nonpaged",
                    "pagefile",
                    "peak_pagefile",
                )
            ]

        data = Counters()
        data.cb = ctypes.sizeof(data)
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        call = ctypes.windll.psapi.GetProcessMemoryInfo
        call.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not call(kernel.GetCurrentProcess(), ctypes.byref(data), data.cb):
            return None
        return data.peak_working_set / 1048576
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (
        1048576 if sys.platform == "darwin" else 1024
    )


def learned_config(model, catalog):
    metadata = json.loads(Path(model).with_suffix(".json").read_text(encoding="utf-8"))
    return {
        "schema_version": "showdown-learned-config-v1",
        "enabled": True,
        "model_path": str(Path(model).resolve()),
        "catalog_path": str(Path(catalog).resolve()),
        "expected_model_id": metadata["model_sha256"],
    }


def verify(checkout, model, catalog, *, calls=1000):
    if not 10 <= calls <= 10000:
        raise ValueError("bounded_inference_calls_required")
    started = perf_counter()
    policy = LearnedPolicy(model, catalog)
    load_ms = (perf_counter() - started) * 1000
    counts = Counter()
    peak_rss = 0
    decisions = 0
    with ShowdownEnvironment(checkout, max_decisions=256) as env:
        for case in range(12):
            env.reset(scenario("test", case))
            rival = VisibleBaseline(
                ("random", "max_power", "heuristic")[case % 3], case
            )
            if case == 0:
                visible = env.observation("self")
                saved = env.save()
                timings = []
                cpu = process_time()
                for _ in range(calls):
                    start = perf_counter()
                    policy.infer(visible)
                    timings.append((perf_counter() - start) * 1000)
                inference_cpu_s = process_time() - cpu
                assert env.save() == saved
            while True:
                own = env.observation("self")
                action = policy.act(own)
                counts[
                    "own_wait"
                    if action == 26
                    else "forced_replacement"
                    if action < 6 and own["request_state"] == "switch"
                    else "switch"
                    if action < 6
                    else "attack"
                ] += 1
                step = env.step(
                    {
                        "self": action,
                        "opponent": rival.act(env.observation("opponent")),
                    },
                    revision=own["revision"],
                )
                decisions += 1
                peak_rss = max(peak_rss, env.resources["rss_bytes"])
                for line in env.observation("self")["events"]:
                    parts = line.split("|")
                    if len(parts) > 1 and parts[1] in {
                        "-status",
                        "-mega",
                        "faint",
                        "-weather",
                        "-enditem",
                        "-ability",
                    }:
                        counts[parts[1]] += 1
                if step["terminated"] or step["truncated"]:
                    assert step["terminated"] and not step["truncated"]
                    counts[
                        "win"
                        if step["winner"] == "self"
                        else "loss"
                        if step["winner"] == "opponent"
                        else "draw"
                    ] += 1
                    break
    app = QApplication.instance() or QApplication([])
    window, manager, snapshot = demo_window()
    context = configuration(seeds=2, horizon=8)
    context["learned_policy"] = learned_config(model, catalog)
    before = manager.capture_runtime_state_snapshot(snapshot["session_id"])
    try:
        window._start_deterministic_strategy_analysis()
        default = window.center_column.llm_advice_panel.output_edit.toPlainText()
        window.configure_showdown_shadow(checkout=checkout, context=context)
        start = perf_counter()
        window._start_deterministic_strategy_analysis()
        dispatch = (perf_counter() - start) * 1000
        wait(app, window)
        ui_ms = (perf_counter() - start) * 1000
        explanation = window._showdown_displayed_explanation
        rows = explanation["sampled_simulation"]["scenarios"]
        assert all(s["learned_policy"]["status"] == "evaluated" for s in rows), rows
        text = window.center_column.llm_advice_panel.output_edit.toPlainText()
        assert "실험 학습 정책 (기본 추천에 미적용)" in text and "승률 아님" in text
        comparison = [
            {
                "hypothesis": s["hypothesis_id"],
                "learned_action": s["learned_policy"]["action_label"],
                "policy_choice_probability": s["learned_policy"]["inference"][
                    "action_probabilities"
                ][s["learned_policy"]["inference"]["action_index"]],
                "discounted_return": s["learned_policy"]["inference"][
                    "discounted_return_estimate"
                ],
            }
            for s in rows
        ]
        legacy = explanation["preferred_frontier"]
        window.configure_showdown_shadow()
        window._start_deterministic_strategy_analysis()
        assert (
            window.center_column.llm_advice_panel.output_edit.toPlainText() == default
        )
        assert (
            manager.capture_runtime_state_snapshot(snapshot["session_id"]) == before
            and manager.read_applied_ledger() == {}
        )
    finally:
        window.configure_showdown_shadow()
        wait(app, window)
        window.close()
        app.processEvents()
    return {
        "schema_version": "showdown-learning-readiness-v1",
        "model_id": policy.model_id,
        "native_episodes": 12,
        "native_decisions": decisions,
        "public_native_events_and_actions": dict(counts),
        "node_peak_rss_mib": peak_rss / 1048576,
        "python_peak_rss_mib": python_peak_rss_mib(),
        "model_load_ms": load_ms,
        "inference_calls": calls,
        "inference_cpu_s": inference_cpu_s,
        "inference_p50_ms": statistics.median(timings),
        "inference_p95_ms": sorted(timings)[int(len(timings) * 0.95)],
        "ui_dispatch_ms": dispatch,
        "ui_end_to_end_ms": ui_ms,
        "legacy_preferred_frontier": legacy,
        "hypothetical_learned_choices": comparison,
        "runtime_immutable": True,
        "rollback_default_equal": True,
        "default_policy_changed": False,
        "interpretation": "learned_policy_distribution_and_uncalibrated_return_not_exact_win_probability",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path)
    p.add_argument(
        "--model", type=Path, default=ROOT / "models/showdown_initial_v1/model.zip"
    )
    p.add_argument(
        "--catalog", type=Path, default=ROOT / "models/showdown_initial_v1/catalog.json"
    )
    p.add_argument("--calls", type=int, default=1000)
    p.add_argument("--export-demo", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.export_demo:
        if a.export_demo.exists():
            raise ValueError("new_demo_output_required")
        context = configuration(seeds=4, horizon=16)
        context["learned_policy"] = learned_config(a.model, a.catalog)
        a.export_demo.write_text(json.dumps(context, indent=2), encoding="utf-8")
        return
    if not a.checkout:
        p.error("--checkout required")
    if a.output and a.output.exists():
        raise ValueError("new_verification_output_required")
    with redirect_stdout(io.StringIO()):
        result = verify(a.checkout, a.model, a.catalog, calls=a.calls)
    if a.output:
        a.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
