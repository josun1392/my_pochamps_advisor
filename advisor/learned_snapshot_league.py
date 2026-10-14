"""Small coordinator-only generation pool; no opponent identity in observations."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

VERSION = "showdown-generation-snapshot-league-v1"


def checkpoint_identity(path, expected_sha=None):
    path = Path(path).resolve().with_suffix(".zip")
    digest = sha256(path.read_bytes()).hexdigest()
    metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if metadata.get("model_sha256") != digest or expected_sha is not None and digest != expected_sha:
        raise ValueError("league_checkpoint_identity_mismatch")
    return {"path": str(path), "sha256": digest, "model_timesteps": metadata["total_steps"],
            "optimizer_steps": metadata["optimizer_steps"],
            "encoder_version": metadata["encoder_version"],
            "catalog_fingerprint": metadata["catalog_fingerprint"],
            "training_objective": metadata.get("training_objective"),
            "training_regularizer": metadata.get("training_regularizer")}


def generation_mixture(fixed, snapshots):
    """Five cyclic fixed slots + five snapshot slots; S0 retained as anchor.

    Completed snapshots only, coordinator must verify chain lineage. Recent
    generations get remaining slots; no nonexistent snapshot at generation zero.
    """
    if len(fixed) != 5 or len(set(fixed)) != 5 or not 1 <= len(snapshots) <= 4:
        raise ValueError("bounded_five_slot_snapshot_mixture_required")
    if len({s["sha256"] for s in snapshots}) != len(snapshots):
        raise ValueError("duplicate_snapshot_identity")
    names = [f"league_s{i}" for i in range(len(snapshots))]
    slots = names[:-1] + [names[-1]] * (6 - len(names))
    sequence = list(fixed) + slots
    return {"schema_version": VERSION, "opponents": sequence,
            "frozen_opponents": {n: s["path"] for n, s in zip(names, snapshots)},
            "frozen_opponent_ids": {n: s["sha256"] for n, s in zip(names, snapshots)},
            "nominal_episode_probabilities": {n: count / len(sequence) for n, count in Counter(sequence).items()},
            "sampling": "cyclic_episode_index_modulo_slots_not_iid_or_decision_weighting"}


def validate_child(parent, child, trained_transitions, collected_transitions=None):
    if (child["sha256"] == parent["sha256"]
            or child["model_timesteps"] - parent["model_timesteps"] != (collected_transitions if collected_transitions is not None else trained_transitions)
            or (collected_transitions is not None and collected_transitions < trained_transitions)
            or child["optimizer_steps"] <= parent["optimizer_steps"]
            or child["encoder_version"] != parent["encoder_version"]
            or child["catalog_fingerprint"] != parent["catalog_fingerprint"]
            or child["training_objective"] != parent["training_objective"]):
        raise ValueError("league_generation_lineage_mismatch")


def append_generation_event(path, event):
    """Append-only identity-bound events, separate from mutable resume state."""
    path = Path(path)
    previous = "0" * 64
    if path.exists():
        previous = read_generation_events(path)[-1]["event_sha256"]
    payload = {"schema_version": VERSION, "previous_event_sha256": previous, **event}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({**payload, "event_sha256": digest}, allow_nan=False) + "\n")
        stream.flush()
    return digest


def read_generation_events(path):
    rows, previous = [], "0" * 64
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        digest = row.pop("event_sha256")
        if (row.get("previous_event_sha256") != previous or digest != sha256(
                json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()):
            raise ValueError("league_event_chain_corrupted")
        rows.append({**row, "event_sha256": digest})
        previous = digest
    return rows
