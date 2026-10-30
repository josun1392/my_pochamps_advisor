"""Default-off, coordinator-only TRAIN initial reserve proposals; never a teacher.

No model, optimizer, native step, or ordinary learning/advisor integration lives
here. A complete receipt admits snapshots only to the declared proposal support.
"""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import gzip
import importlib.metadata
import itertools
import json
import os
import platform
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import time

from advisor.learned_decision_snapshots import outside_git, write_new, digest
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID, silent_process_options

VERSION = "showdown-train-initial-reserve-proposal-v1"
ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_mc_domain_v1/catalog.json"
MAX_STARTS, MAX_BYTES = 21, 4 * 1024 * 1024
FORBIDDEN = {"native_state", "teams", "scenario", "checkpoint", "seed", "future_seed",
             "input_log", "opponent_request", "coordinator_v5_supervision", "auxiliary_labels"}
EXTRA_SOURCES = (
    "advisor/learned_initial_reserves.py", "scripts/sample_foundation_initial_reserves.py",
    "advisor/learned_decision_snapshots.py", "advisor/learned_full_roster.py",
    "advisor/learned_full_domain.py", "advisor/learned_native_curriculum.py",
    "advisor/showdown_environment.py", "advisor/showdown_observation.py",
    "advisor/showdown_worker.py", "advisor/showdown_bridge.py", "advisor/learning_resources.py",
    "tools/showdown_bridge/engine.cjs", "tools/showdown_bridge/worker.cjs",
    "tools/showdown_bridge/bridge.cjs", "tools/showdown_bridge/environment.cjs",
    "tools/showdown_bridge/legal-battle.cjs", "models/showdown_full_roster_v8/manifest.json",
    "models/showdown_public_categories_v1/catalog.json",
)


def file_sha(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_identity():
    from advisor.learned_objective import categorical_learning_source_identity
    identity = categorical_learning_source_identity()
    identity.update({name: sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                     for name in EXTRA_SOURCES})
    return {"text_SHA256_LF": identity,
            "binary_SHA256": {"models/showdown_full_roster_v8/teams.json.gz":
                              file_sha(ROOT / "models/showdown_full_roster_v8/teams.json.gz")}}


def dependency_identity():
    packages = {}
    for name in ("numpy", "torch", "sb3-contrib", "stable-baselines3"):
        dist = importlib.metadata.distribution(name)
        records = {item: dist.read_text(item) for item in ("METADATA", "RECORD")}
        if any(value is None for value in records.values()):
            raise ValueError("reserve_dependency_manifest_unavailable")
        packages[name] = {"version": dist.version, "distribution_manifest_SHA256": {
            item: sha256(value.encode()).hexdigest() for item, value in records.items()}}
    return {"python": platform.python_version(), "python_executable_SHA256": file_sha(sys.executable),
            "stdlib_random_SHA256": file_sha(random.__file__), "packages": packages,
            "node_executable_SHA256": file_sha(shutil.which("node")),
            "node": subprocess.check_output(["node", "--version"], text=True,
                                             **silent_process_options()).strip()}


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _asset(path):
    path = outside_git(path)
    return {"path": str(path), "sha256": file_sha(path)}


def make_plan(*, subset_path, subset_sha256, checkout, runtime_manifest_path, case_index,
              side, initial_seed, proposal_seed, sample_size, public_path, checkpoint_path):
    """Freeze files/versions only: this neither creates nor admits a native state."""
    subset = _asset(subset_path)
    if subset["sha256"] != subset_sha256:
        raise ValueError("reserve_subset_provenance_conflict")
    return {"schema_version": VERSION, "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
            "subset": subset, "catalog": {"path": str(CATALOG.resolve()), "sha256": file_sha(CATALOG)},
            "runtime_manifest": _asset(runtime_manifest_path), "checkout": str(Path(checkout).resolve()),
            "reference_public": _asset(public_path), "reference_checkpoint": _asset(checkpoint_path),
            "case_index": case_index, "side": side, "initial_seed": list(initial_seed),
            "proposal_seed": proposal_seed, "sample_size": sample_size,
            "sources": source_identity(), "dependencies": dependency_identity()}


def strict_public(view):
    if FORBIDDEN & set(view):
        raise ValueError("reserve_privileged_public_input")
    return {key: deepcopy(value) for key, value in view.items() if key != "episode_id"}


def require_same_public(reference, candidate):
    if strict_public(reference) != strict_public(candidate):
        raise ValueError("reserve_public_input_mismatch")


def _same_feature_bytes(reference, candidate):
    return (reference.dtype == candidate.dtype and reference.shape == candidate.shape
            and reference.tobytes() == candidate.tobytes())


def candidate_orders(lead, proposal_seed, sample_size):
    if (type(lead) is not int or not 1 <= lead <= 6 or type(proposal_seed) is not int
            or not 0 <= proposal_seed < 2 ** 63 or type(sample_size) is not int
            or not 1 <= sample_size <= 20):
        raise ValueError("reserve_proposal_bounds")
    pool = [[lead, *tail] for tail in itertools.permutations([i for i in range(1, 7) if i != lead], 2)]
    # A local RNG, not the native seed, Torch stream, or global random state.
    selected = random.Random(proposal_seed).sample(pool, sample_size)
    if len({tuple(row) for row in selected}) != sample_size:
        raise ValueError("reserve_duplicate_proposal")
    return pool, selected


def probability_record(sample_size):
    if type(sample_size) is not int or not 1 <= sample_size <= 20:
        raise ValueError("reserve_proposal_bounds")
    return {"interpretation": "selected_proposal_only_not_TRAIN_posterior",
            "proposal_probability_scope": "declared_random_sample_design_not_empirical_seed_frequency",
            "selected_normalized_weight": str(Fraction(1, sample_size)),
            "proposal_inclusion_probability": str(Fraction(sample_size, 20)),
            "untested_pre_admission_proposal_mass": str(Fraction(20 - sample_size, 20)),
            "idealized_generator_structural_mass": {"value": "1/30720",
                "authority": "declared_256_team_uniform_choice_times_120_ordered3_not_actual_index_prior"},
            "actual_TRAIN_prior_mass": None, "conditional_TRAIN_prior_mass": None,
            "missing_TRAIN_mass": None, "TRAIN_mass_status": "unknown",
            "unknown_reason": "no_empirical_case_index_law_or_initial_seed_marginalization_proved",
            "full_hidden_state_space_complete": False}


def _validate_plan(plan):
    required = {"schema_version", "engine_commit", "format_id", "subset", "catalog", "runtime_manifest",
                "checkout", "reference_public", "reference_checkpoint", "case_index", "side", "initial_seed",
                "proposal_seed", "sample_size", "sources", "dependencies"}
    if (set(plan) != required or plan["schema_version"] != VERSION
            or plan["engine_commit"] != SHOWDOWN_COMMIT or plan["format_id"] != FORMAT_ID
            or plan["side"] not in ("self", "opponent") or type(plan["case_index"]) is not int
            or plan["case_index"] < 0 or not isinstance(plan["initial_seed"], list)
            or len(plan["initial_seed"]) != 4
            or any(type(n) is not int or not 0 <= n <= 65535 for n in plan["initial_seed"])):
        raise ValueError("reserve_plan_scope_mismatch")
    candidate_orders(1, plan["proposal_seed"], plan["sample_size"])
    if Path(plan["catalog"]["path"]).resolve() != CATALOG.resolve():
        raise ValueError("reserve_catalog_scope_conflict")
    for key in ("subset", "catalog", "runtime_manifest", "reference_public", "reference_checkpoint"):
        asset = plan[key]
        if set(asset) != {"path", "sha256"}:
            raise ValueError("reserve_asset_identity_required")
        if key != "catalog":
            outside_git(asset["path"])
        if file_sha(asset["path"]) != asset["sha256"]:
            raise ValueError("reserve_input_SHA_conflict:" + key)
    if plan["sources"] != source_identity() or plan["dependencies"] != dependency_identity():
        raise ValueError("reserve_source_or_dependency_conflict")


def _verify_runtime(plan):
    root = Path(plan["checkout"]).resolve()
    manifest = _read(plan["runtime_manifest"]["path"])
    if Path(manifest["root"]).resolve() != root or not manifest.get("files"):
        raise ValueError("reserve_runtime_manifest_conflict")
    for name, expected in manifest["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or file_sha(path) != expected:
            raise ValueError("reserve_runtime_file_conflict")


def _canonical_species(checkout, names):
    code = ("const path=require('node:path');const {Dex}=require(path.join(process.argv[1],'dist/sim'));"
            "process.stdout.write(JSON.stringify(JSON.parse(process.argv[2]).map(n=>"
            "({input:n,exists:Dex.mod('champions').species.get(n).exists,"
            "name:Dex.mod('champions').species.get(n).name}))));")
    result = json.loads(subprocess.check_output(["node", "-e", code, checkout, json.dumps(sorted(names))],
                                               text=True, **silent_process_options()))
    if not all(row["exists"] and row["input"] == row["name"] for row in result):
        raise ValueError("reserve_noncanonical_TRAIN_roster")
    return result


def _encoder(catalog):
    from advisor.learned_combat_foundation import FoundationCombatEncoder
    return FoundationCombatEncoder(catalog)


def _native(checkout):
    from advisor.showdown_environment import ShowdownEnvironment
    return ShowdownEnvironment(checkout, max_decisions=256)


def _context(plan):
    from advisor.learned_training_subset import NativeTrainingSubset, VERSION_256
    subset = NativeTrainingSubset(plan["subset"]["path"], plan["subset"]["sha256"])
    if (subset.contract["schema_version"] != VERSION_256 or len(subset.teams) != 256
            or subset.contract["selection_mode"] != "independent_random_ordered3"):
        raise ValueError("reserve_requires_original_TRAIN256")
    scenario = subset("train", plan["case_index"])
    reference = _read(plan["reference_public"]["path"])
    original = json.loads(gzip.decompress(Path(plan["reference_checkpoint"]["path"]).read_bytes()))
    side = plan["side"]
    other = "opponent" if side == "self" else "self"
    owner = "p1" if side == "self" else "p2"
    opposite = "p2" if side == "self" else "p1"
    if (scenario["seed"] != plan["initial_seed"] or reference["side"] != side
            or reference["turn"] != 1 or reference["revision"] != 0
            or reference["request_state"] != "move" or reference["terminated"] or reference["truncated"]
            or reference["events"] != reference["public_history"]
            or reference["own_request"].get("side", {}).get("id") != owner
            or original.get("schema_version") != "showdown-environment-checkpoint-v1"
            or original.get("engine_commit") != SHOWDOWN_COMMIT or original.get("format_id") != FORMAT_ID
            or original.get("decisions") != 0 or original.get("max_decisions") != 256
            or original.get("consecutive_rejections") != 0 or original["native_state"].get("turn") != 1
            or original.get("provenance", {}).get("scenario_id") != scenario["scenario_id"]):
        raise ValueError("reserve_initial_root_provenance_conflict")
    strict_public(reference)
    masks, choices = reference["action_mask"], reference["choices"]
    if (len(masks) != 35 or len(choices) != 35 or not any(masks)
            or any(type(m) is not int or m not in (0, 1) or m != int(c is not None)
                   for m, c in zip(masks, choices))):
        raise ValueError("reserve_reference_mask_invalid")
    if any(line.startswith(("|replace|", "|-transform|", "|detailschange|"))
           for line in reference["public_history"]):
        raise ValueError("reserve_transformed_introduction_unsupported")
    preview = tuple(line.split("|")[3].split(",")[0] for line in reference["public_history"]
                    if line.startswith("|poke|" + opposite + "|"))
    own_preview = [line for line in reference["public_history"] if line.startswith("|poke|" + owner + "|")]
    if len(preview) != 6 or len(own_preview) != 6:
        raise ValueError("reserve_complete_public_preview_required")
    canonical = _canonical_species(plan["checkout"], {p["species"] for t in subset.teams for p in t})
    matches = [i for i, team in enumerate(subset.teams) if tuple(p["species"] for p in team) == preview]
    if len(matches) != 1:
        raise ValueError("reserve_nonunique_public_TRAIN_roster")
    offset = matches[0]
    team = subset.teams[offset]
    if any(p.get("ability") == "Illusion" or p["species"].startswith("Zoroark")
           for t in (team, scenario["teams"][side]) for p in t):
        raise ValueError("reserve_Illusion_unsupported")
    active = reference["state"]["opponent_side"]["active_identity"]
    match = re.fullmatch(opposite + r"a: slot-([0-5])", active) if isinstance(active, str) else None
    if not match:
        raise ValueError("reserve_unambiguous_public_lead_required")
    lead = int(match.group(1)) + 1
    if team != scenario["teams"][other] or scenario["preview"][other][0] != lead:
        raise ValueError("reserve_generator_roster_or_lead_conflict")
    pool, selected = candidate_orders(lead, plan["proposal_seed"], plan["sample_size"])
    return {"subset": subset, "scenario": scenario, "reference": reference, "original": original,
            "side": side, "other": other, "lead": lead, "pool": pool, "selected": selected,
            "roster_offset": offset, "canonical": canonical,
            "excluded_rosters": [{"subset_offset": i, "team_SHA256": digest(t),
                                  "reason": "different_complete_public_ordered_species_preview"}
                                 for i, t in enumerate(subset.teams) if i != offset]}


class _Recorder:
    def __init__(self, output, stopping):
        self.output, self.stopping = output, stopping
        self.starts, self.bytes = 0, 0
        self.snapshots = {}

    def check(self):
        if self.stopping():
            raise TimeoutError("reserve_STOP_or_deadline")

    def append(self, row):
        with (self.output / "private/native_ledger.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def reset(self, env, key, scenario, side):
        self.check()
        if self.starts >= MAX_STARTS:
            raise ValueError("reserve_native_start_cap")
        self.starts += 1
        self.append({"phase": "started", "ordinal": self.starts, "key": key,
                     "scenario_SHA256": digest(scenario)})
        try:
            result = env.reset(deepcopy(scenario))
            view, cp = env.observation(side, include_history=True), env.save()
            if (result["terminated"] or result["truncated"] or result["action_rejected"]
                    or cp["decisions"] != 0 or cp["native_state"]["turn"] != 1):
                raise ValueError("reserve_generated_state_out_of_scope")
            self.append({"phase": "committed", "key": key, "checkpoint_digest": cp["digest"]})
            return view, cp
        except BaseException as error:
            self.append({"phase": "failed", "key": key, "error": repr(error)})
            raise

    def snapshot(self, cp):
        identity = digest(cp)
        if identity in self.snapshots:
            return {**self.snapshots[identity], "storage_reused": True}
        raw = gzip.compress(json.dumps(cp, allow_nan=False).encode(), mtime=0)
        if self.bytes + len(raw) > MAX_BYTES:
            raise ValueError("reserve_snapshot_storage_cap")
        path = self.output / "private/checkpoints" / (identity + ".json.gz")
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        self.bytes += len(raw)
        row = {"path": str(path), "file_SHA256": file_sha(path), "content_SHA256": identity,
               "native_digest": cp["digest"], "storage_reused": False}
        self.snapshots[identity] = row
        return row


def sample_initial_reserves(plan, output, *, enabled=False, stopping=None):
    """Run only in an explicitly enabled isolated coordinator, never in policy code.

    Returns a coordinator receipt handle; private hypotheses are not Gym info.
    Any admission failure poisons the whole batch. No existing output is retried.
    """
    if enabled is False:
        return {"schema_version": VERSION, "status": "disabled", "native_starts": 0}
    if enabled is not True:
        raise ValueError("reserve_explicit_boolean_enable_required")
    plan = deepcopy(plan)
    out = outside_git(output)
    out.mkdir(parents=True, exist_ok=False)
    for name in ("private", "private/checkpoints", "public"):
        (out / name).mkdir()
    write_new(out / "private/plan.json", plan)
    write_new(out / "private/started.json", {"schema_version": VERSION, "PID": os.getpid(),
                                            "plan_SHA256": digest(plan), "unix_time": time.time()})
    begin = time.monotonic()
    recorder = _Recorder(out, lambda: time.monotonic() - begin > 570
                         or (out / "STOP").exists() or (stopping is not None and stopping()))
    try:
        _validate_plan(plan)
        recorder.check()
        _verify_runtime(plan)
        ctx = _context(plan)
        reference, side, other = ctx["reference"], ctx["side"], ctx["other"]
        encoder = _encoder(plan["catalog"]["path"])
        import numpy as np
        expected = encoder.encode(deepcopy(reference))
        if not np.isfinite(expected).all():
            raise ValueError("reserve_nonfinite_public_features")
        feature_sha = sha256(expected.tobytes()).hexdigest()
        probabilities = probability_record(plan["sample_size"])
        candidates, native_seen = [], set()
        write_new(out / "public/reference.json", reference)
        with _native(plan["checkout"]) as env:
            source_view, source_cp = recorder.reset(env, "source_binding", ctx["scenario"], side)
            if source_cp != ctx["original"]:
                raise ValueError("reserve_native_source_checkpoint_conflict")
            require_same_public(reference, source_view)
            if not _same_feature_bytes(expected, encoder.encode(deepcopy(source_view))):
                raise ValueError("reserve_source_feature_conflict")
            source_storage = recorder.snapshot(source_cp)
            for i, ordered in enumerate(ctx["selected"]):
                recorder.check()
                original_pick = ctx["scenario"]["preview"][other]
                if ordered == original_pick:
                    view, cp, origin = source_view, source_cp, "reused_authenticated_source_binding"
                else:
                    scenario = deepcopy(ctx["scenario"])
                    scenario["teams"][other] = deepcopy(ctx["subset"].teams[ctx["roster_offset"]])
                    scenario["preview"][other] = list(ordered)
                    view, cp = recorder.reset(env, f"candidate_{i:02d}", scenario, side)
                    origin = "native_legal_reset_from_TRAIN_generator_with_reserved_order_substitution"
                require_same_public(reference, view)
                if not _same_feature_bytes(expected, encoder.encode(deepcopy(view))):
                    raise ValueError("reserve_candidate_feature_conflict")
                owner_index = 0 if side == "self" else 1
                if cp["native_state"]["sides"][owner_index] != source_cp["native_state"]["sides"][owner_index]:
                    raise ValueError("reserve_owner_native_state_conflict")
                other_side = cp["native_state"]["sides"][0 if other == "self" else 1]
                if [p["set"]["name"] for p in other_side["pokemon"]] != [f"slot-{s-1}" for s in ordered]:
                    raise ValueError("reserve_native_selection_binding_conflict")
                identity = digest(cp["native_state"])
                if identity in native_seen:
                    raise ValueError("reserve_duplicate_native_world")
                native_seen.add(identity)
                candidates.append({"ordered3": ordered, "draw_index": i,
                    "draw_conditional_probability": str(Fraction(1, 20 - i)),
                    "proposal_weight": probabilities["selected_normalized_weight"],
                    "proposal_inclusion_probability": probabilities["proposal_inclusion_probability"],
                    "actual_TRAIN_prior_mass": None, "TRAIN_mass_status": "unknown",
                    "admission": "verified_exact_public_h_native_legal_reset",
                    "snapshot_origin": origin, "snapshot": recorder.snapshot(cp),
                    "post_reset_PRNG_SHA256": digest(cp["native_state"]["prng"]),
                    "public_h_SHA256": digest(strict_public(view)), "Foundation_feature_SHA256": feature_sha})
        recorder.check()
        _validate_plan(plan)
        _verify_runtime(plan)
        selected = {tuple(row) for row in ctx["selected"]}
        manifest = {"schema_version": VERSION, "status": "complete", "scope": "coordinator_only_not_policy_features",
            "eligibility": "matching_complete_run_receipt_and_no_failure_required",
            "plan_SHA256": digest(plan), "source_binding": source_storage,
            "case_index": plan["case_index"], "side": side, "seed_stratum": plan["initial_seed"],
            "seed_condition": "fixed_initial_input_seed_not_equalized_post_reset_PRNG",
            "proposal_seed": plan["proposal_seed"], "owner_team_SHA256": digest(ctx["scenario"]["teams"][side]),
            "owner_ordered3": ctx["scenario"]["preview"][side],
            "opponent_roster": {"subset_offset": ctx["roster_offset"],
                "V8_train_index": ctx["subset"].contract["team_indices"][ctx["roster_offset"]],
                "team_SHA256": digest(ctx["subset"].teams[ctx["roster_offset"]]),
                "unique_public_roster_class_verified": True},
            "public_lead": ctx["lead"], "public_h_SHA256": digest(strict_public(reference)),
            "Foundation_feature_SHA256": feature_sha, "encoder_version": encoder.version,
            "encoder_feature_fingerprint": encoder.catalog_fingerprint,
            "enumeration_scope": "20_lead_conditioned_reserve_orders_at_fixed_owner_setup_and_initial_seed",
            "declared_proposal_support_size": 20, "selected_verified": len(candidates),
            "declared_support_fully_verified": len(candidates) == 20,
            "full_hidden_state_space_complete": False, "probabilities": probabilities,
            "candidates": candidates, "unvalidated_not_sampled": [x for x in ctx["pool"] if tuple(x) not in selected],
            "excluded_rosters": ctx["excluded_rosters"],
            "excluded_orders": [{"ordered3": list(t), "reason": "different_unambiguous_public_lead_in_no_Illusion_scope"}
                                for t in itertools.permutations(range(1, 7), 3) if t[0] != ctx["lead"]],
            "duplicate_candidate_policy": "fail_closed_no_silent_merge_or_reweight",
            "native_starts": recorder.starts, "snapshot_bytes": recorder.bytes,
            "native_steps": 0, "terminal_continuations": 0, "PPO": 0, "Adam": 0,
            "wall_seconds": time.monotonic() - begin}
        write_new(out / "private/manifest.json", manifest)
        result = {"schema_version": VERSION, "status": "complete", "coordinator_only": True,
                  "manifest_path": str(out / "private/manifest.json"),
                  "manifest_SHA256": file_sha(out / "private/manifest.json"),
                  "selected_verified": len(candidates), "native_starts": recorder.starts}
        write_new(out / "run.json", result)
        return result
    except BaseException as error:
        write_new(out / "private/failure.json", {"status": "failed_ineligible", "error": repr(error),
            "native_starts": recorder.starts, "automatic_retry": False,
            "prior_or_missing_mass": None, "partial_samples_usable": False})
        raise
