"""Seat-balanced paired native preview evaluation, never checkpoint selection."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter
from hashlib import sha256
import json
import multiprocessing as mp
import random
from time import perf_counter
import numpy as np
import torch
from advisor.learned_preview import public_preview, selection
from advisor.learned_preview_policy import LearnedPreviewPolicy
from advisor.learned_preview_env import freeze_battle_policy, execute_preview_battle
from advisor.learned_baselines import VisibleBaseline
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_encoder import fingerprint
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, enforce_local_network_only
from scripts.evaluate_showdown_policy import FIXTURE_SEAT_CONTRACT, seat_scenario


def initialize(config, models):
    global NATIVE, BATTLE, POLICIES
    enforce_local_network_only()
    torch.set_num_threads(1)
    BATTLE = freeze_battle_policy(config["battle_model"], config["catalog"], config["battle_model_sha256"])
    NATIVE = ShowdownEnvironment(config["checkout"], max_decisions=4096)
    POLICIES = {name: LearnedPreviewPolicy(row["path"], config["catalog"], expected_sha256=row["sha256"])
                for name, row in models.items() if name != "random"}


def game(task):
    case_id, canonical, side, rival_kind, kind = task
    # Both real seats and both teams; no winner-label pseudo-swap.
    case = seat_scenario(canonical, "p1" if side == "self" else "p2", FIXTURE_SEAT_CONTRACT)
    observation = public_preview(NATIVE.preview(case, side))
    if kind == "random":
        rng = random.Random(int.from_bytes(sha256(f"preview-eval-random:{case_id}:{side}:{rival_kind}".encode()).digest(), "big"))
        action, value, entropy = rng.randrange(120), None, float(np.log(120))
    else:
        proof = POLICIES[kind].infer(observation)
        action, value = proof["action"], proof["terminal_return_estimate"]
        p = np.asarray(proof["probabilities"])
        entropy = float(-(p * np.log(p.clip(1e-30))).sum())
    rival = VisibleBaseline(rival_kind, case_id + 919)
    result = execute_preview_battle(NATIVE, case, side, action, BATTLE, rival)
    return {"case": case_id, "case_sha256": fingerprint(canonical), "seat": side, "rival": rival_kind,
        "policy": kind, "preview_action": action, "selected_slots": selection(action),
        "preview_public_sha256": fingerprint(observation), "entropy": entropy,
        "value": value, **result}


def summarize(records):
    policies = sorted({r["policy"] for r in records})
    cases = sorted({r["case"] for r in records})
    scores, results = {}, {}
    for kind in policies:
        rows = [r for r in records if r["policy"] == kind]
        results[kind] = {"outcomes": dict(Counter(r["outcome"] for r in rows)),
            "by_rival": {rival: dict(Counter(r["outcome"] for r in rows if r["rival"] == rival)) for rival in sorted({r["rival"] for r in rows})},
            "by_seat": {seat: dict(Counter(r["outcome"] for r in rows if r["seat"] == seat)) for seat in ("self", "opponent")},
            "mean_entropy": float(np.mean([r["entropy"] for r in rows])),
            "actions": dict(Counter(r["preview_action"] for r in rows)),
            "native_rejections": sum(r["native_rejections"] for r in rows),
            "native_decisions": sum(r["native_decisions"] for r in rows), "truncations": 0}
        scores[kind] = np.asarray([np.mean([r["outcome"] == "win" for r in rows if r["case"] == c]) for c in cases])
    bootstrap = np.random.default_rng(7501101).integers(len(cases), size=(5000, len(cases)))
    paired = {}
    if "trained" in scores:
        for baseline in ("random", "initial"):
            if baseline in scores:
                delta = scores["trained"] - scores[baseline]
                paired[baseline] = {"win_fraction_difference": float(delta.mean()),
                    "case_cluster_seat_rival_95": np.quantile(delta[bootstrap].mean(1), [.025, .975]).tolist(),
                    "case_clusters": len(cases), "resamples": 5000}
    return {"policies": results, "trained_minus_baseline": paired,
        "interpretation": "single_preview_training_seed_deterministic_policy_selection_not_species_unseen_not_exact_probability"}


def run(plan_path, output, models):
    plan = json.loads(Path(plan_path).read_text())
    config = plan["runtime"]
    cases_raw = Path(plan["cases_path"]).read_bytes()
    if sha256(cases_raw).hexdigest() != plan["cases_sha256"]:
        raise ValueError("frozen_preview_cases_mismatch")
    cases = json.loads(cases_raw)
    output = Path(output).resolve()
    if output.is_relative_to(ROOT) or output.exists():
        raise ValueError("new_external_preview_evaluation_directory_required")
    output.mkdir(parents=True)
    job = WindowsJob(memory_mib=12288, cpu_percent=50, active_process_limit=40)
    limit = RuntimeLimit(output, 3600)
    start = perf_counter()
    atomic_json(output / "frozen_manifest.json", {"plan_sha256": sha256(Path(plan_path).read_bytes()).hexdigest(),
        "models": models, "seat_contract": FIXTURE_SEAT_CONTRACT})
    tasks = [(int(i), case, side, rival, kind) for kind in models for i, case in cases.items()
             for side in ("self", "opponent") for rival in plan["rivals"]]
    records = []
    try:
        with mp.get_context("spawn").Pool(8, initializer=initialize, initargs=(config, models)) as pool:
            with (output / "records.jsonl").open("w", encoding="utf-8") as f:
                for row in pool.imap(game, tasks, chunksize=4):
                    if limit.stopping():
                        raise TimeoutError("bounded_preview_evaluation_stopped")
                    records.append(row); f.write(json.dumps(row) + "\n"); f.flush()
        result = {"status": "completed", "battles": len(records), "elapsed_seconds": perf_counter() - start,
            "resources": job.usage(), **summarize(records)}
        atomic_json(output / "summary.json", result)
        return result
    finally:
        limit.finished.set()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True); parser.add_argument("--models", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.plan, args.output, json.loads(Path(args.models).read_text()))))
