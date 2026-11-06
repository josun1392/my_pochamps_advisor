"""Build one frozen experimental team source, never battles or policy inputs."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import gzip
import json
import time
import traceback

from advisor.learned_development_team_source import (
    VERSION, FORMAT_ID, SHOWDOWN_COMMIT, admit, compare_distribution, composition,
    digest, file_sha, load_candidates, native_validate, set_reuse, team_identity,
)
from advisor.learning_resources import WindowsJob, atomic_json, enforce_local_network_only


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def verify_bindings(bindings):
    for path, expected in bindings.items():
        normalized = str(path).replace("\\", "/").lower()
        if any(x in normalized for x in ("config/env.example", "config/.env", "logs/token_usage.jsonl",
                                         "docs/handoff_capsule_v1.1.md")):
            raise ValueError("protected_file_not_an_allowed_input")
        if file_sha(path) != expected:
            raise ValueError("preserved_input_hash_changed:" + str(path))


def load_exclusions(specs):
    reference, records, bindings = [], [], {}
    primary = None
    for spec in specs:
        path = Path(spec["path"]); bindings[str(path)] = spec["sha256"]
        if "manifest" in spec:
            bindings[spec["manifest"]] = spec["manifest_sha256"]
        verify_bindings(bindings)
        if spec["kind"] == "native_bank":
            raw = gzip.decompress(path.read_bytes()); bank = json.loads(raw)
            manifest = read(spec["manifest"])
            if (bank["schema_version"] != "showdown-native-team-bank-v1"
                    or manifest["bank_sha256"] != spec["sha256"]
                    or sha256(raw).hexdigest() != manifest["content_sha256"]
                    or bank.get("engine_commit") != SHOWDOWN_COMMIT or bank.get("format_id") != FORMAT_ID):
                raise ValueError("native_bank_binding_mismatch")
            if file_sha(path) != manifest["bank_sha256"]:
                raise ValueError("native_bank_hash_mismatch")
            teams = [t for group in bank["teams"].values() for t in group]
            if spec["name"] == "showdown_full_roster_v8":
                primary = bank["teams"]["train"]
        elif spec["kind"] == "team_asset":
            source = read(spec["manifest"])
            if source["team_asset"]["sha256"] != spec["sha256"]:
                raise ValueError("sealed_identity_binding_mismatch")
            teams = read(path)["teams"]  # Identity assets only, never results.
        elif spec["kind"] == "pilot_plan":
            plan = read(path)
            teams = [t for key in ("training_templates", "development_templates")
                     for row in plan[key] for t in row["scenario"]["teams"].values()]
        else:
            raise ValueError("unknown_exclusion_source")
        records.append({"name": spec["name"], "kind": spec["kind"], "team_entries": len(teams),
                        "unique_semantic_teams": len({team_identity(t)["semantic"] for t in teams})})
        reference.extend(teams)
    if primary is None or len(primary) != 4096:
        raise ValueError("verified_V8_TRAIN_reference_required")
    keys = [team_identity(t) for t in reference]
    excluded = {kind: {k[kind] for k in keys} for kind in ("semantic", "joint_movesets")}
    return reference, primary, excluded, records, bindings


def invalid_fixtures(team):
    fixtures = {}
    p = deepcopy(team); p[1] = deepcopy(p[0]); fixtures["species_clause"] = p
    p = deepcopy(team); p[0]["moves"] = ["not-a-real-move-11606"]; fixtures["unknown_move"] = p
    p = deepcopy(team); p[0]["ability"] = "not-a-real-ability-11606"; fixtures["unknown_ability"] = p
    p = deepcopy(team); p[0]["evs"]["hp"] = 999; fixtures["invalid_stat_points"] = p
    fixtures["not_full_six"] = deepcopy(team[:5])
    return fixtures


def run(root):
    root = Path(root).resolve(); plan = read(root / "plan.json")
    if (plan["schema_version"] != "independent-train-development-team-source-plan-v1"
            or plan["candidate_count"] != 160 or plan["minimum_eligible_teams"] != 128
            or plan["battle_authorization"] is not False or plan["evaluation_distribution_approved"] is not False):
        raise ValueError("frozen_source_only_plan_required")
    output = root / "source"
    if output.exists():
        raise ValueError("existing_source_do_not_regenerate")
    started = time.perf_counter()
    job = WindowsJob(memory_mib=plan["memory_mib"], cpu_percent=plan["CPU_percent"], active_process_limit=12)
    output.mkdir()
    network = enforce_local_network_only()
    forbidden = Counter()

    def no_learning(frame, event, arg):
        if event != "call":
            return
        name = frame.f_code.co_name; filename = frame.f_code.co_filename.replace("\\", "/")
        if ((filename.endswith("advisor/showdown_environment.py") and name in ("__init__", "reset", "step", "fork"))
                or (filename.endswith("torch/nn/modules/module.py") and name == "_call_impl")
                or ("torch/optim/" in filename and name == "step")
                or (filename.endswith("advisor/learned_policy.py") and name == "__init__")):
            forbidden[filename + ":" + name] += 1
            raise RuntimeError("source_only_forbidden_execution")
    sys.setprofile(no_learning)
    try:
        registry = plan["preservation_registry"]
        if file_sha(registry["path"]) != registry["sha256"]:
            raise ValueError("preservation_registry_changed")
        preserved = read(registry["path"]); verify_bindings(preserved)
        runtime_path = Path(plan["runtime_manifest"])
        if file_sha(runtime_path) != plan["runtime_manifest_sha256"]:
            raise ValueError("pinned_runtime_manifest_changed")
        runtime = read(runtime_path)
        if Path(runtime["root"]).resolve() != Path(plan["checkout"]).resolve():
            raise ValueError("pinned_runtime_path_mismatch")
        runtime_files = {str(Path(runtime["root"]) / k): v for k, v in runtime["files"].items()}
        verify_bindings(runtime_files)
        reference, v8, excluded, sources, source_bindings = load_exclusions(plan["exclusion_specs"])
        owned = ["advisor/learned_development_team_source.py", "scripts/build_independent_development_teams.py",
                 "tools/showdown_bridge/validate-teams.cjs"]
        code = {p: file_sha(ROOT / p) for p in owned}
        atomic_json(root / "implementation_binding.json", {"plan_SHA256": file_sha(root/"plan.json"), "sources": code})
        from advisor.learned_prospective_evaluation import generate_team_batch
        first = generate_team_batch(plan["checkout"], seed=plan["seed"], count=plan["candidate_count"])
        atomic_json(output / "generation.json", first)
        replay = generate_team_batch(plan["checkout"], seed=plan["seed"], count=plan["candidate_count"])
        if first != replay:
            raise ValueError("native_generation_reproducibility_failed")
        validation = native_validate(plan["checkout"], first["teams"])
        atomic_json(output / "validation.json", validation)
        if any(not r["valid"] or r["errors"] for r in validation["results"]):
            raise ValueError("native_generated_candidate_invalid")
        bad = invalid_fixtures(first["teams"][0])
        negatives = native_validate(plan["checkout"], list(bad.values()))
        atomic_json(output / "invalid_input_validation.json", {"names": list(bad), "receipt": negatives})
        if any(r["valid"] or not r["errors"] for r in negatives["results"]):
            raise ValueError("native_invalid_input_not_rejected")
        teams, indices, admissions = admit(first["teams"], excluded)
        atomic_json(output / "admissions.json", admissions)
        if len(teams) < plan["minimum_eligible_teams"]:
            atomic_json(root / "completion.json", {"status": "SOURCE_DESIGN_BLOCKED", "eligible_teams": len(teams),
                                                    "native_battles": 0, "PPO": 0, "Adam": 0})
            return
        atomic_json(output / "teams.json", {"teams": teams})
        new_keys = [team_identity(t) for t in teams]
        statistics = {"composition": composition(teams), "V8_TRAIN_composition": composition(v8),
                      "descriptive_distribution_difference": compare_distribution(teams, v8),
                      "individual_set_reuse_vs_V8_TRAIN": set_reuse(teams, v8),
                      "individual_set_reuse_vs_all_exclusions": set_reuse(teams, reference),
                      "new_roster_identities": len({k["roster"] for k in new_keys}),
                      "roster_only_overlap_with_exclusions": len({k["roster"] for k in new_keys} &
                                                                 {team_identity(t)["roster"] for t in reference}),
                      "interpretation": "Finite-source composition differences, not proof of equal distributions or playing strength."}
        atomic_json(output / "statistics.json", statistics)
        audit = {"exclusion_sources": sources, "source_bindings": source_bindings,
                 "old_unique_semantic_teams": len(excluded["semantic"]),
                 "semantic_full_team_overlap": 0, "joint_moveset_full_team_overlap": 0,
                 "duplicate_new_teams": 0, "reproducible_batch_SHA256": digest(first),
                 "native_accepted": len(validation["results"]), "native_invalid_fixtures_rejected": len(bad),
                 "rejections": dict(Counter(r for a in admissions for r in a["reasons"]))}
        atomic_json(output / "novelty_audit.json", audit)
        assets = {name: {"path": filename, "sha256": file_sha(output / filename)} for name, filename in
                  {"teams": "teams.json", "generation": "generation.json", "validation": "validation.json",
                   "admissions": "admissions.json", "audit": "novelty_audit.json", "statistics": "statistics.json"}.items()}
        manifest = {"schema_version": VERSION, "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
                    "inventory_SHA256": first["inventory_sha256"], "generation_seed": plan["seed"],
                    "generation_indices": indices, "teams": len(teams), "minimum_teams": 128,
                    "team_identities": new_keys, "pairs": [{"pair": i, "team_indices": [2*i, 2*i+1]}
                                                           for i in range(len(teams)//2)],
                    "unpaired_team_indices": list(range(2*(len(teams)//2), len(teams))),
                    "assets": assets, "plan_SHA256": file_sha(root / "plan.json"), "source_SHA256": code,
                    "evaluation_approved": False, "battle_execution_approved": False,
                    "role": "experimental TRAIN-domain development source candidates; requires T1 distribution admission",
                    "distribution": "Maintained uniform eligible base/form generator with native upstream/domain set modes; newly seeded finite source, not declared identical to V8 TRAIN."}
        atomic_json(output / "manifest.json", manifest)
        manifest_sha = file_sha(output / "manifest.json")
        _, loaded = load_candidates(output / "manifest.json", manifest_sha)
        assert loaded == teams
        verify_bindings(preserved); verify_bindings(runtime_files); verify_bindings(source_bindings)
        verify_bindings({str(ROOT / k): h for k, h in code.items()})
        atomic_json(root / "completion.json", {"status": "SOURCE_CANDIDATES_READY", "teams": len(teams),
            "pairs": len(manifest["pairs"]), "manifest_SHA256": manifest_sha,
            "generation_calls": 2, "native_validation_teams": len(first["teams"]) + len(bad),
            "native_battles": 0, "PPO": 0, "Adam": 0, "model_forwards": 0, "terminal": 0,
            "forbidden_calls": dict(forbidden), "network": network,
            "preserved_original_files": len(preserved), "pinned_runtime_files": len(runtime_files),
            "resources": job.usage(), "source_execution_seconds": time.perf_counter()-started,
            "completed_KST": datetime.now().astimezone().isoformat()})
    finally:
        sys.setprofile(None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.output)
    except Exception as exc:
        failure = args.output / "failure.json"
        if failure.exists():
            failure = args.output / f"failure_{time.time_ns()}.json"
        atomic_json(failure, {"type": type(exc).__name__, "message": str(exc),
                    "trace": traceback.format_exc(), "automatic_retry": False})
        raise
