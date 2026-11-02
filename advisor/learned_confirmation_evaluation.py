"""Opt-in 288-case confirmation admission; the existing game kernel is unchanged."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

from advisor.learned_encoder import fingerprint
from advisor.learned_response_predictor import team_signature
from advisor.learned_selfplay_pilot import StartBudget
from advisor.learned_prospective_evaluation import (
    ProspectiveEvaluationSource, file_sha, _seed, SHOWDOWN_COMMIT, FORMAT_ID, OWNERS, SEATS, OPPONENTS,
)
from advisor.learned_prospective_runner import ApprovedSealedRunner, ReceiptStore, FOUNDATION, CANDIDATE

VERSION = "showdown-independent-confirmation-source-v1"
READY_VERSION = "showdown-independent-confirmation-readiness-v1"
CASES, POINTS, STARTS = 288, 3456, 6912
CASE_START = 161102000


class IndependentConfirmationSource(ProspectiveEvaluationSource):
    """Same maintained scenario/seat mapping, distinct fixed source identity."""
    def __init__(self, path, expected_sha256, *, readiness=None, readiness_sha256=None):
        self.path = Path(path).resolve()
        if file_sha(self.path) != expected_sha256:
            raise ValueError("confirmation_manifest_hash_mismatch")
        m = json.loads(self.path.read_text(encoding="utf-8"))
        if (m.get("schema_version") != VERSION or m.get("engine_commit") != SHOWDOWN_COMMIT
                or m.get("format_id") != FORMAT_ID or m.get("native_team_validated") is not True):
            raise ValueError("confirmation_authority_mismatch")
        batch = json.loads(self._asset(m["team_asset"]).read_text(encoding="utf-8"))
        teams = batch.get("teams", [])
        if (len(teams) != 576 or any(not isinstance(t, list) or len(t) != 6 for t in teams)
                or batch.get("engine_commit") != SHOWDOWN_COMMIT or batch.get("format_id") != FORMAT_ID
                or len({team_signature(t) for t in teams}) != 576):
            raise ValueError("confirmation_team_asset_or_duplicate_identity")
        bindings = m.get("native_batches", [])
        if len(bindings) != 3:
            raise ValueError("confirmation_exact_three_batches_required")
        joined = []
        generation_seeds = []
        for binding in bindings:
            part = json.loads(self._asset(binding).read_text(encoding="utf-8"))
            if (part.get("schema_version") != "showdown-full-domain-generated-teams-v1"
                    or part.get("engine_commit") != SHOWDOWN_COMMIT or part.get("format_id") != FORMAT_ID
                    or len(part.get("teams", [])) != 192 or not _seed(part.get("seed"))
                    or part.get("inventory_sha256") != batch.get("inventory_sha256")):
                raise ValueError("confirmation_native_batch_authority")
            joined.extend(part["teams"])
            generation_seeds.append(tuple(part["seed"]))
        if joined != teams or len(set(generation_seeds)) != 3:
            raise ValueError("confirmation_batch_membership_mismatch")
        cases = m.get("cases", [])
        if (len(cases) != CASES or [c.get("index") for c in cases] != list(range(CASE_START, CASE_START + CASES))
                or any(c.get("case_id") != "independent-confirmation-v1-" + str(c["index"])
                       or c.get("partition") != "independent_confirmation" for c in cases)):
            raise ValueError("confirmation_fixed_case_support")
        seeds = []
        for i, case in enumerate(cases):
            if case.get("team_indices") != {"a": 2*i, "b": 2*i+1} or type(case.get("admitted")) is not bool:
                raise ValueError("confirmation_pair_binding")
            for owner in OWNERS:
                order = case["ordered3"][owner]
                if (not isinstance(order, list) or len(order) != 3 or len(set(order)) != 3
                        or any(type(n) is not int or not 1 <= n <= 6 for n in order)):
                    raise ValueError("confirmation_ordered_three")
                for seat in SEATS:
                    vector = case["native_seeds"][owner + ":" + seat]
                    if not _seed(vector):
                        raise ValueError("confirmation_native_seed")
                    seeds.append(tuple(vector))
        if len(set(seeds)) != 1152:
            raise ValueError("confirmation_duplicate_native_seed")
        if tuple(m.get("opponent_order", [])) != OPPONENTS or set(m.get("opponents", {})) != set(OPPONENTS):
            raise ValueError("confirmation_opponent_support")
        if m.get("measure") != {"name": "Q_independent_confirmation_v1", "cases": CASES,
                "owners": list(OWNERS), "seats": list(SEATS), "opponents": list(OPPONENTS),
                "points": POINTS, "point_mass": "1/3456", "case_mass": "1/288",
                "renormalize": False, "historical_TRAIN_prior": False}:
            raise ValueError("confirmation_probability_contract")
        self._manifest, self._teams, self._sha256, self._ready = deepcopy(m), deepcopy(teams), expected_sha256, False
        if readiness is not None:
            if readiness_sha256 is None or file_sha(readiness) != readiness_sha256:
                raise ValueError("confirmation_readiness_hash")
            ready = json.loads(Path(readiness).read_text(encoding="utf-8"))
            if (ready.get("schema_version") != READY_VERSION or ready.get("status") != "CONFIRMATION_SOURCE_READY"
                    or ready.get("manifest_sha256") != expected_sha256):
                raise ValueError("confirmation_readiness_authority")
            novelty = json.loads(self._asset(ready["novelty_audit"]).read_text(encoding="utf-8"))
            if (novelty.get("status") != "PASS" or novelty.get("manifest_sha256") != expected_sha256
                    or any(novelty.get(k) != v for k, v in {
                        "cases": CASES, "all_cases_admitted": True, "unique_teams": 576,
                        "old_semantic_team_overlap": 0, "old_raw_team_overlap": 0,
                        "old_case_id_overlap": 0, "old_case_index_overlap": 0,
                        "old_seed_overlap": 0, "catalog_all_sets_supported": True}.items())):
                raise ValueError("confirmation_novelty_not_established")
            self._ready = True

    def protocol_scenarios(self):
        raise ValueError("confirmation_has_no_extra_protocol_battle_budget")

    def points(self):
        if not self.ready or any(not c["admitted"] for c in self._manifest["cases"]):
            raise ValueError("confirmation_source_not_ready_no_replacement")
        for case in self._manifest["cases"]:
            for owner in OWNERS:
                for seat in SEATS:
                    for opponent in OPPONENTS:
                        identity = {"manifest_sha256": self.sha256, "case_id": case["case_id"],
                                    "candidate_team": owner, "seat": seat, "opponent": opponent}
                        yield {**identity, "point_key": fingerprint(identity), "case_index": case["index"],
                               "mass": Fraction(1, POINTS), "scenario": self._scenario(case, owner, seat)}


class ConfirmationReceiptStore(ReceiptStore):
    def __init__(self, directory):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.budget = StartBudget(self.root / "starts", STARTS, self.root / "STOP")


class IndependentConfirmationRunner(ApprovedSealedRunner):
    """Only admission dimensions differ; run() is inherited without override."""
    def __init__(self, source, directory, checkout, catalog, candidate_sha256, *,
                 authorization=None, authorization_sha256=None, evaluator=None):
        if authorization is None or authorization_sha256 is None:
            raise ValueError("separate_T1_confirmation_approval_required")
        if file_sha(authorization) != authorization_sha256:
            raise ValueError("confirmation_authorization_hash")
        approval = json.loads(Path(authorization).read_text(encoding="utf-8"))
        expected = {"schema_version": "independent-confirmation-authorization-v1", "authority": "T1",
            "status": "APPROVED", "source_sha256": source.sha256,
            "Foundation_sha256": source.manifest["reference_policy"]["sha256"],
            "candidate_sha256": candidate_sha256, "mode": "T1_argmax", "cases": CASES,
            "points_per_model": POINTS, "models": 2, "native_starts_max": STARTS,
            "replacement": False, "replay": False, "primary": "paired_terminal_return_16K_minus_Foundation"}
        if (type(source) is not IndependentConfirmationSource or not source.ready
                or any(approval.get(k) != v for k, v in expected.items())
                or not isinstance(approval.get("authority_ref"), str) or not approval["authority_ref"]):
            raise ValueError("confirmation_authorization_contract")
        from scripts.evaluate_showdown_policy import evaluate
        self.source, self.checkout, self.catalog, self.evaluator = source, checkout, catalog, evaluator or evaluate
        self.model_ids = {FOUNDATION: expected["Foundation_sha256"], CANDIDATE: candidate_sha256}
        self.allowed = {}
        for point in source.points():
            point = deepcopy(point)
            point["mass"] = str(point["mass"])
            self.allowed[point["point_key"]] = point
        if len(self.allowed) != POINTS:
            raise ValueError("confirmation_source_support_mismatch")
        self.store = ConfirmationReceiptStore(directory)


def confirmation_panel_analysis(points, records, reference_sha256, candidate_sha256):
    """Predeclared new-panel return contrast; never consumes the old 96 results."""
    import numpy as np
    if reference_sha256 == candidate_sha256:
        raise ValueError("confirmation_two_distinct_policies_required")
    if len(points) != POINTS or len({p["point_key"] for p in points}) != POINTS:
        raise ValueError("confirmation_full_points_required")
    cases = sorted({p["case_id"] for p in points})
    if len(cases) != CASES:
        raise ValueError("confirmation_cluster_count")
    expected = {(p["point_key"], m) for p in points for m in (reference_sha256, candidate_sha256)}
    by = {}
    for row in records:
        key = row["point_key"], row["model_sha256"]
        if key in by or key not in expected:
            raise ValueError("confirmation_duplicate_or_unexpected_result")
        r = row["record"]
        if (row.get("terminated") is not True or r["truncated"] or r["return"] not in (-1, 0, 1)
                or r["winner"] != ("self" if r["return"] == 1 else "opponent" if r["return"] == -1 else None)):
            raise ValueError("confirmation_invalid_terminal_no_imputation")
        by[key] = r
    if set(by) != expected:
        raise ValueError("confirmation_incomplete_panel_no_reweight")
    d_return, d_win = [], []
    for case in cases:
        keys = [p["point_key"] for p in points if p["case_id"] == case]
        if len(keys) != 12:
            raise ValueError("confirmation_twelve_cells_per_cluster_required")
        d_return.append(np.mean([by[k, candidate_sha256]["return"] - by[k, reference_sha256]["return"] for k in keys]))
        d_win.append(np.mean([int(by[k, candidate_sha256]["return"] == 1) - int(by[k, reference_sha256]["return"] == 1) for k in keys]))
    draws = np.random.default_rng(1611022026).integers(0, CASES, (20000, CASES))
    out = {"case_clusters": CASES, "cells_per_case": 12, "resamples": 20000,
           "bootstrap_seed": 1611022026, "primary": "paired_terminal_return_16K_minus_Foundation",
           "scope": "fixed_models_and_new_288_case_source_not_training_seed_population", "native_or_model_calls": 0}
    for name, values in (("return", d_return), ("win_fraction", d_win)):
        x = np.asarray(values)
        out["candidate_minus_Foundation_" + name] = {"difference": float(x.mean()),
            "case_cluster_95": np.quantile(x[draws].mean(1), [.025, .975]).tolist()}
    out["independent_confirmation_passed"] = out["candidate_minus_Foundation_return"]["case_cluster_95"][0] > 0
    return out
