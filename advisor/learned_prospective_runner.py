"""Protocol-only admission runner using the maintained native evaluator.

The CLI exposes protocol smoke only; the sealed API requires separate future
T1 authorization. Model/native calls follow exact membership admission.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic

import numpy as np
from advisor.learned_encoder import fingerprint
from advisor.learned_execution_alignment import durable_json
from advisor.learned_prospective_evaluation import OPPONENTS, file_sha
from advisor.learned_response_predictor import public_input, FEATURE_KEYS, FORBIDDEN
from advisor.learned_selfplay_pilot import StartBudget
from advisor.learned_selfplay_retry import ResolvedRequestRateGuard
from scripts.evaluate_showdown_policy import evaluate, seat_scenario, NATIVE_SEAT_CONTRACT, FIXTURE_SEAT_CONTRACT

VERSION = "showdown-prospective-protocol-comparison-runner-v1"
FOUNDATION = "Foundation"
CANDIDATE = "Fixed16K"


def protocol_points(source):
    """Two non-evaluation cases, both actual seats; never enumerate sealed cases."""
    manifest = source.manifest
    protocol = {c["case_id"]: c for c in manifest["cases"][:4]}
    for fixture in source.protocol_scenarios():
        case = protocol[fixture["case_id"]]
        for seat in ("self", "opponent"):
            scenario = deepcopy(fixture["scenario"])
            if seat != fixture["seat"]:
                scenario = seat_scenario(scenario, "p2", NATIVE_SEAT_CONTRACT)
            scenario["seed"] = list(case["native_seeds"][fixture["owner"] + ":" + seat])
            scenario["scenario_id"] = case["case_id"] + ":" + fixture["owner"] + ":" + seat
            for opponent in OPPONENTS:
                identity = {"manifest_sha256": source.sha256, "case_id": case["case_id"],
                            "candidate_team": fixture["owner"], "seat": seat, "opponent": opponent}
                yield {**identity, "point_key": fingerprint(identity), "case_index": case["index"],
                       "scenario": deepcopy(scenario)}


def execution_identity(point, model_sha256, purpose):
    if purpose not in ("base", "replay"):
        raise ValueError("unknown_protocol_purpose")
    return {"point_key": point["point_key"], "model_sha256": model_sha256, "purpose": purpose}


class ReceiptStore:
    """Existing durable writer/start budget with fail-closed incomplete intents."""
    def __init__(self, directory, maximum=36):
        if maximum not in (36, 2304):
            raise ValueError("unsupported_finite_evaluation_budget")
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.budget = StartBudget(self.root / "starts", maximum, self.root / "STOP")

    def paths(self, identity):
        key = fingerprint(identity)
        return self.root / ("intent_" + key + ".json"), self.root / ("result_" + key + ".json")

    def existing(self, identity):
        intent, result = self.paths(identity)
        if result.exists():
            data = json.loads(result.read_text(encoding="utf-8"))
            if (not intent.exists() or data["identity"] != identity
                    or json.loads(intent.read_text(encoding="utf-8"))["identity"] != identity
                    or data["payload_sha256"] != fingerprint(data["payload"])):
                raise ValueError("protocol_receipt_corrupt_or_misbound")
            return data["payload"]
        if intent.exists():
            raise ValueError("protocol_incomplete_intent_no_automatic_replay")
        return None

    def begin(self, identity):
        if self.existing(identity) is not None:
            raise ValueError("protocol_already_complete")
        ordinal = self.budget.reserve({"schema_version": VERSION, "identity": identity})
        intent, _ = self.paths(identity)
        durable_json(intent, {"ordinal": ordinal, "identity": identity})
        return ordinal

    def complete(self, identity, payload):
        intent, result = self.paths(identity)
        if not intent.exists():
            raise ValueError("protocol_result_without_intent")
        durable_json(result, {"identity": identity, "payload": payload, "payload_sha256": fingerprint(payload)})


def normalized_public(view):
    if any(view.get("action_mask", [])):
        return public_input(view)
    # An ended execution observation has no executable actions. This is not
    # a policy decision input, and must never be supplied to infer().
    role = {"self": "p1", "opponent": "p2"}.get(view.get("side"))
    if (not (view.get("terminated") or view.get("truncated")) or FORBIDDEN & set(view)
            or len(view.get("action_mask", [])) != 35 or any(type(x) is not int or x != 0 for x in view["action_mask"])
            or len(view.get("choices", [])) != 35 or any(view["choices"])
            or role is None or view.get("own_request", {}).get("side", {}).get("id", role) != role):
        raise ValueError("invalid_ended_public_trace_observation")
    return {k: deepcopy(view[k]) for k in FEATURE_KEYS if k in view}


def inference_public_view(view):
    """Public features plus authenticated receipt metadata, not model features.

    The predictor helper deliberately omits these fields. LearnedPolicy and
    VisibleBaseline need them for evidence/episode-cache binding.
    """
    public = public_input(view)
    if not isinstance(view.get("episode_id"), str) or type(view.get("revision")) is not int:
        raise ValueError("inference_public_receipt_metadata_missing")
    return {**public, "episode_id": view["episode_id"], "revision": view["revision"],
            "events": deepcopy(view.get("events", []))}


class PublicTraceAudit:
    """Public-only native progress/rejection evidence; never changes a choice."""
    def __init__(self, event_sink=None):
        self.hash = sha256()
        self.steps = self.last_decisions = self.consecutive_rejections = 0
        self.rate = ResolvedRequestRateGuard()
        self.final = None
        self.first = None
        self.event_sink = event_sink

    def observe(self, event):
        before, after, result = event["before"], event["after"], event["result"]
        if self.event_sink and (self.steps == 0 or result["terminated"] or result["truncated"] or result["action_rejected"]):
            self.event_sink(deepcopy(event))
        if set(before) != {"self", "opponent"} or set(after) != set(before):
            raise ValueError("protocol_missing_native_seat")
        for side, view in before.items():
            public_input(view)
            action = event["actions"][side]
            if type(action) is not int or not 0 <= action < 35 or not view["action_mask"][action]:
                raise ValueError("protocol_illegal_native_submission")
            normalized_public(after[side])
            if (view["side"] != side or after[side]["side"] != side
                    or view["episode_id"] != after[side]["episode_id"]
                    or after[side]["revision"] != view["revision"] + 1):
                raise ValueError("protocol_observer_owner_or_revision")
        rejected = result["action_rejected"]
        expected = self.last_decisions if rejected else self.last_decisions + 1
        if result["decisions"] != expected:
            raise ValueError("protocol_native_progress_mismatch")
        self.consecutive_rejections = self.consecutive_rejections + 1 if rejected else 0
        if self.consecutive_rejections >= 8:
            raise ValueError("protocol_eight_rejections_without_native_progress")
        self.last_decisions = result["decisions"]
        if result["rewards"]["self"] != -result["rewards"]["opponent"]:
            raise ValueError("protocol_reward_perspective")
        if rejected and (result["rewards"] != {"self": 0, "opponent": 0}
                         or result["terminated"] or result["truncated"]):
            raise ValueError("protocol_rejected_attempt_executed")
        self.rate.observe(event)
        row = {"before": {s: normalized_public(v) for s, v in before.items()},
               "actions": event["actions"], "result": result,
               "after": {s: normalized_public(v) for s, v in after.items()}}
        payload = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        self.hash.update(payload + b"\n")
        self.steps += 1
        self.first = self.first or {s: fingerprint(normalized_public(v)) for s, v in before.items()}
        self.final = deepcopy(result)

    def proof(self):
        return {"steps": self.steps, "native_decisions": self.last_decisions,
                "public_trace_sha256": self.hash.hexdigest(), "first_public": self.first,
                "terminal": deepcopy(self.final), "request_refresh": self.rate.statistics()}


def validate_terminal_record(point, record, trace):
    side, other = point["seat"], "opponent" if point["seat"] == "self" else "self"
    final = trace["terminal"]
    if (final is None or not final["terminated"] or final["truncated"] or record["truncated"]
            or trace["request_refresh"]["unresolved_rejections"] or trace["request_refresh"]["pending_is_unresolved"]):
        raise ValueError("protocol_nonterminal_or_unresolved_not_a_valid_result")
    winner = final["winner"]
    expected_return = 1 if winner == side else -1 if winner == other else 0
    expected_winner = "self" if expected_return == 1 else "opponent" if expected_return == -1 else None
    if (record["return"] != expected_return or final["rewards"][side] != expected_return
            or record["winner"] != expected_winner or record["raw_native_winner"] != winner
            or record["candidate_seat"] != ("p1" if side == "self" else "p2")
            or record["case"] != point["case_index"] or record["opponent"] != point["opponent"]
            or record["canonical_scenario_sha256"] != fingerprint(point["scenario"])
            or record["native_scenario_sha256"] != fingerprint(point["scenario"])
            or record["initial_native_seed"] != point["scenario"]["seed"]):
        raise ValueError("protocol_terminal_result_identity_or_perspective")
    return True


class ProtocolRunner:
    """Admits only exact protocol cells, before inference or native reset."""
    def __init__(self, source, directory, checkout, catalog, candidate_sha256, *, evaluator=evaluate):
        self.source, self.checkout, self.catalog = source, checkout, catalog
        self.model_ids = {FOUNDATION: source.manifest["reference_policy"]["sha256"], CANDIDATE: candidate_sha256}
        self.allowed = {p["point_key"]: p for p in protocol_points(source)}
        if len(self.allowed) != 12:
            raise ValueError("protocol_support_mismatch")
        self.store = ReceiptStore(directory)
        self.evaluator = evaluator

    def run(self, point, label, actor, rival, *, purpose="base"):
        expected = self.allowed.get(point.get("point_key"))
        if expected is None or point != expected:
            raise ValueError("sealed_or_changed_point_not_admitted")
        if label not in self.model_ids or actor.model_id != self.model_ids[label]:
            raise ValueError("protocol_model_not_admitted")
        if purpose == "replay" and label != FOUNDATION:
            raise ValueError("protocol_replay_only_predeclared_Foundation_cells")
        if point["opponent"] in OPPONENTS[:2]:
            if rival != point["opponent"]:
                raise ValueError("protocol_rival_not_admitted")
        elif getattr(rival, "model_id", None) != self.source.manifest["opponents"][OPPONENTS[2]]["sha256"]:
            raise ValueError("protocol_rival_not_admitted")
        identity = execution_identity(point, actor.model_id, purpose)
        saved = self.store.existing(identity)
        if saved is not None:
            if saved["label"] != label or saved["point"] != point:
                raise ValueError("protocol_saved_result_binding_mismatch")
            if saved["valid_terminal"]:
                validate_terminal_record(point, saved["record"], saved["trace"])
            elif not (saved["record"]["truncated"] and saved["trace"]["terminal"]["truncated"]):
                raise ValueError("protocol_invalid_saved_result_not_resumable")
            return saved, False
        ordinal = self.store.begin(identity)
        journal = self.store.root / ("public_events_" + fingerprint(identity) + ".jsonl")
        def save_event(event):
            import os
            with journal.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, allow_nan=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        trace = PublicTraceAudit(save_event)
        committed, callback_duplicates = None, 0

        class CaseProvider:
            identity = {"source_sha256": point["manifest_sha256"], "protocol_point": point["point_key"]}
            def __call__(self, split, index):
                if split != "validation" or index != point["case_index"]:
                    raise ValueError("unexpected_protocol_case_request")
                return deepcopy(point["scenario"])

        def progress(rows):
            nonlocal committed, callback_duplicates
            if len(rows) != 1:
                raise ValueError("protocol_one_result_required")
            record = rows[0]
            proof = trace.proof()
            invalid_reason = None
            try:
                validate_terminal_record(point, record, proof)
            except ValueError as error:
                invalid_reason = str(error)
            if committed is not None:
                if fingerprint(record) != fingerprint(committed["record"]):
                    raise ValueError("protocol_duplicate_callback_conflict")
                callback_duplicates += 1
                return
            committed = {"ordinal": ordinal, "label": label, "point": point,
                         "record": record, "trace": proof, "valid_terminal": invalid_reason is None,
                         "invalid_reason": invalid_reason}
            self.store.complete(identity, committed)
            if invalid_reason and (not proof["terminal"]["truncated"] or
                    invalid_reason != "protocol_nonterminal_or_unresolved_not_a_valid_result"):
                raise ValueError(invalid_reason)

        deadline = monotonic() + 120
        def observe(event):
            trace.observe(event)
            if (not event["result"]["terminated"] and not event["result"]["truncated"]
                    and ((self.store.root / "STOP").exists() or monotonic() > deadline)):
                raise TimeoutError("protocol_STOP_or_wall_limit_at_native_boundary")
        result = self.evaluator(self.checkout, self.catalog, {label: actor},
            split="validation", cases=1, offset=point["case_index"],
            curriculum_version="showdown-prospective-protocol-source-v1",
            rivals={point["opponent"]: rival}, candidate_seat="p1" if point["seat"] == "self" else "p2",
            seat_contract=FIXTURE_SEAT_CONTRACT, case_provider=CaseProvider(),
            transition_observer=observe, progress=progress, per_game_progress=True,
            stopping=lambda: (self.store.root / "STOP").exists() or monotonic() > deadline)
        if committed is None or result["records"] != [committed["record"]] or callback_duplicates != 1:
            raise ValueError("protocol_evaluator_result_commit_mismatch")
        return committed, True


class ApprovedSealedRunner(ProtocolRunner):
    """Same native kernel, requiring a separately approved future T1 contract.

    Hash/authority fields validate a trusted coordinator receipt; they do not
    authenticate a human or grant permission on their own. This task does not
    create such an approval. There is no sealed execution CLI in this version.
    """
    def __init__(self, source, directory, checkout, catalog, candidate_sha256, *,
                 authorization=None, authorization_sha256=None, evaluator=evaluate):
        if authorization is None or authorization_sha256 is None:
            raise ValueError("separate_T1_approval_required_before_sealed_access")
        if file_sha(authorization) != authorization_sha256:
            raise ValueError("sealed_authorization_hash_mismatch")
        approval = json.loads(Path(authorization).read_text(encoding="utf-8"))
        expected = {"schema_version": "prospective-sealed-comparison-authorization-v1",
                    "authority": "T1", "status": "APPROVED", "source_sha256": source.sha256,
                    "Foundation_sha256": source.manifest["reference_policy"]["sha256"],
                    "candidate_sha256": candidate_sha256, "mode": "T1_argmax",
                    "points_per_model": 1152, "models": 2, "native_starts_max": 2304,
                    "replacement": False, "replay": False}
        if (not source.ready or any(approval.get(k) != v for k, v in expected.items())
                or not isinstance(approval.get("authority_ref"), str) or not approval["authority_ref"]):
            raise ValueError("separate_T1_approval_contract_mismatch")
        self.source, self.checkout, self.catalog, self.evaluator = source, checkout, catalog, evaluator
        self.model_ids = {FOUNDATION: expected["Foundation_sha256"], CANDIDATE: candidate_sha256}
        indices = {c["case_id"]: c["index"] for c in source.manifest["cases"][4:]}
        self.allowed = {}
        for point in source.points():
            point = deepcopy(point)
            point["case_index"] = indices[point["case_id"]]
            point["mass"] = str(point["mass"])  # exact rational JSON transport
            self.allowed[point["point_key"]] = point
        if len(self.allowed) != 1152:
            raise ValueError("sealed_source_support_mismatch")
        self.store = ReceiptStore(directory, maximum=2304)

    def run(self, point, label, actor, rival, *, purpose="base"):
        if purpose != "base":
            raise ValueError("sealed_replay_not_authorized")
        return super().run(point, label, actor, rival, purpose=purpose)


def paired_panel_analysis(points, records, reference_sha256, candidate_sha256):
    """Future full-panel statistics only; no model/native calls or inference."""
    if reference_sha256 == candidate_sha256:
        raise ValueError("two_distinct_frozen_model_identities_required")
    if len(points) != 1152 or len({p["point_key"] for p in points}) != 1152:
        raise ValueError("full_source_points_required")
    cases = sorted({p["case_id"] for p in points})
    if len(cases) != 96:
        raise ValueError("case_cluster_contract_mismatch")
    expected = {(p["point_key"], model) for p in points for model in (reference_sha256, candidate_sha256)}
    by = {}
    for row in records:
        key = row["point_key"], row["model_sha256"]
        if key in by or key not in expected:
            raise ValueError("duplicate_or_unexpected_panel_result")
        record = row["record"]
        if (row.get("terminated") is not True or record["truncated"] or record["return"] not in (-1, 0, 1)
                or record["winner"] != ("self" if record["return"] == 1 else
                                        "opponent" if record["return"] == -1 else None)):
            raise ValueError("invalid_panel_result_no_imputation")
        by[key] = record
    if set(by) != expected:
        raise ValueError("incomplete_panel_no_reweight")
    delta_win, delta_return = [], []
    for case in cases:
        keys = [p["point_key"] for p in points if p["case_id"] == case]
        if len(keys) != 12:
            raise ValueError("all_twelve_cells_must_stay_in_case")
        delta_win.append(np.mean([int(by[k, candidate_sha256]["return"] == 1)
                                  - int(by[k, reference_sha256]["return"] == 1) for k in keys]))
        delta_return.append(np.mean([by[k, candidate_sha256]["return"] - by[k, reference_sha256]["return"] for k in keys]))
    draws = np.random.default_rng(1610312026).integers(0, 96, (20000, 96))
    out = {"case_clusters": 96, "cells_per_case": 12, "resamples": 20000,
           "scope": "fixed_models_and_source_case_mix_not_training_seed_population",
           "primary": "candidate_minus_Foundation_win_fraction", "native_or_model_calls": 0}
    for name, values in (("win_fraction", delta_win), ("return", delta_return)):
        x = np.asarray(values)
        ci = np.quantile(x[draws].mean(1), [.025, .975])
        out["candidate_minus_Foundation_" + name] = {"difference": float(x.mean()), "case_cluster_95": ci.tolist()}
        out["Foundation_minus_candidate_" + name] = {"difference": float(-x.mean()), "case_cluster_95": [-float(ci[1]), -float(ci[0])]}
    return out
