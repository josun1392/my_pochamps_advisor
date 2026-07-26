"""Explicit runtime-bound persistence commands with no UI or lifecycle wiring."""
import os
from copy import deepcopy
from pathlib import Path

from llm.advisor_observation_replay_runtime import ObservationReplayRuntime


class ObservationReplayPersistenceCommands:
    """One-useful-only-with-its-owner command boundary for one runtime."""

    def __init__(self, runtime):
        self._runtime = runtime
        context = runtime._persistence_command_context()
        self._runtime_identity = context["runtime_identity"]
        self._session_id = context["session_id"]

    @classmethod
    def create(cls, runtime):
        if not isinstance(runtime, ObservationReplayRuntime):
            return {"status": "invalid_runtime", "commands": None, "session_id": None}
        return {"status": "ready", "commands": cls(runtime), "session_id": runtime.session_id}

    @property
    def session_id(self):
        return self._session_id

    def save(self, path):
        context = self._context()
        target = _save_target(path)
        if context is None:
            return {"status": "stale_runtime"}
        if target is None:
            return {"status": "invalid_path"}
        exported = context["persistence"].export_envelope(context["store"], context["coordinator"], self._session_id)
        if exported.get("status") != "ready":
            return {"status": exported.get("status", "invalid_envelope")}
        saved = context["persistence"].save(target, exported["envelope"])
        return {"status": "save_complete"} if saved.get("status") == "saved" else {"status": saved.get("status", "io_error")}

    def load(self, path):
        context = self._context()
        target = _load_target(path)
        if context is None:
            return {"status": "stale_runtime"}
        if target is None:
            return {"status": "invalid_path"}
        loaded = context["persistence"].load(target)
        if loaded.get("status") == "file_not_found":
            return {"status": "not_found"}
        return deepcopy(loaded)

    def restore(self, candidate, expected_runtime_fingerprint):
        context = self._context()
        if context is None:
            return {"status": "stale_runtime"}
        validated = _validated_candidate(context["persistence"], candidate)
        if validated.get("status") != "load_ready":
            return {"status": validated.get("status", "invalid_envelope")}
        envelope = validated["envelope"]
        if envelope.get("session_id") != self._session_id:
            return {"status": "session_mismatch"}
        current = context["store"].read_snapshot(self._session_id)
        if not isinstance(expected_runtime_fingerprint, str) or not expected_runtime_fingerprint or current.get("status") != "ready" or current.get("state_fingerprint") != expected_runtime_fingerprint:
            return {"status": "stale_runtime"}
        restored = context["persistence"].restore(context["store"], context["coordinator"], validated, expected_runtime_fingerprint)
        status = restored.get("status")
        return {"status": "restore_complete"} if status == "restored" else {"status": status or "critical_restore_inconsistency"}

    def _context(self):
        context = self._runtime._persistence_command_context()
        if context.get("runtime_identity") != self._runtime_identity or context.get("session_id") != self._session_id:
            return None
        return context


def _validated_candidate(persistence, candidate):
    if not isinstance(candidate, dict):
        return {"status": "invalid_envelope"}
    envelope = candidate.get("envelope") if candidate.get("status") == "load_ready" else candidate
    return persistence.validate(deepcopy(envelope))


def _save_target(path):
    target = _path(path)
    return target if target is not None and not target.is_dir() and target.parent.is_dir() else None


def _load_target(path):
    target = _path(path)
    return target if target is not None and not target.is_dir() else None


def _path(path):
    if not isinstance(path, (str, os.PathLike)) or isinstance(path, str) and not path.strip():
        return None
    try:
        return Path(path)
    except (TypeError, ValueError, OSError):
        return None
