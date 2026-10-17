"""Versioned operational guards; no policy, reward or optimizer modification."""

from copy import deepcopy
import json
import os
from pathlib import Path
from time import time
from uuid import uuid4

OPERATIONS_VERSION = "showdown-training-operations-v2"
ACCOUNTING_VERSION = "completed-optimizer-rollouts-v2"


class CompletedRollouts:
    def __init__(self):
        self.transitions = 0
        self.pending = None

    def collected(self, transitions, optimizer_clock):
        if self.pending is not None:
            raise ValueError("unsettled_rollout_accounting")
        self.pending = (int(transitions), int(optimizer_clock))

    def settle(self, optimizer_clock):
        if self.pending is not None:
            transitions, before = self.pending
            if optimizer_clock < before:
                raise ValueError("optimizer_clock_regressed")
            if optimizer_clock > before:
                self.transitions += transitions
            self.pending = None


class RetryMonitor:
    def __init__(self, state=None):
        self.pending = deepcopy(state or {})

    def inspect(self, records, episodes, collected_transitions):
        alerts = []
        unique = 0
        for record in records:
            key = f"{record['episode_id']}:{record['episode_case']}"
            entry = self.pending.setdefault(key, {"case": record["episode_case"], "revisions": []})
            revision = record["revision_before"]
            if revision in entry["revisions"]:
                continue
            entry["revisions"].append(revision)
            unique += 1
            if len(entry["revisions"]) == 8:
                alerts.append({"reason": "eight_retries_same_episode", "episode": key, "count": 8})
            for side, before in record["before"].items():
                index, mask = before["action_index"], before["action_mask"]
                if not 0 <= index < len(mask) or not mask[index]:
                    alerts.append({"reason": "mask_illegal_retry_choice", "episode": key, "side": side})
        if unique > .01 * collected_transitions:
            alerts.append({"reason": "interval_retry_rate_above_one_percent", "retries": unique,
                           "collected_transitions": collected_transitions})
        ended = {row["episode_identity"]["case_index"] for row in episodes}
        self.pending = {key: entry for key, entry in self.pending.items() if entry["case"] not in ended}
        return alerts


def read_journal(path):
    raw = Path(path).read_bytes()
    lines = raw.splitlines(keepends=True)
    partial_tail = bool(lines and not lines[-1].endswith(b"\n"))
    complete = lines[:-1] if partial_tail else lines
    records = [json.loads(line) for line in complete]
    for index, record in enumerate(records):
        if record["sequence"] != index or record["schema_version"] != OPERATIONS_VERSION:
            raise ValueError("invalid_training_journal_sequence_or_version")
    return {"records": records, "incomplete_tail_preserved": partial_tail}


class TrainingJournal:
    def __init__(self, output, durable):
        directory = Path(output) / "operations"
        directory.mkdir(exist_ok=True)
        previous = []
        for path in sorted(directory.glob("launch_*.jsonl")):
            history = read_journal(path)
            records = history["records"]
            if not records or records[-1]["phase"] not in {"launch_end", "launch_failed"}:
                previous.append({"path": str(path), "last_observation": records[-1] if records else None,
                    "incomplete_tail_preserved": history["incomplete_tail_preserved"],
                    "exit_cause": "unknown", "exact_uncommitted_training_work": None})
        self.path = directory / f"launch_{time():.6f}_{uuid4().hex[:8]}.jsonl"
        self.sequence = 0
        self.durable = self.counters(durable)
        self.append("launch_start", interrupted_launches=previous)

    @staticmethod
    def counters(state):
        return {key: state.get(key, 0) for key in
                ("transitions", "trained_rollout_transitions", "completed_battles", "optimizer_steps")} | {
                    "latest": state.get("latest"), "latest_model_sha256": state.get("latest_model_sha256")}

    def publish(self, state):
        self.durable = self.counters(state)

    def append(self, phase, **observed):
        record = {"schema_version": OPERATIONS_VERSION, "sequence": self.sequence,
            "unix_time": time(), "pid": os.getpid(), "phase": phase,
            "durable_checkpoint": self.durable,
            "observation_scope": "observed_not_checkpoint_committed_unless_published",
            "observed": observed}
        payload = json.dumps(record, allow_nan=False) + "\n"
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        self.sequence += 1
