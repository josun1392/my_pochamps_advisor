"""Private JSON durability boundary for replay state and its applied ledger.

This module deliberately has no UI, autosave, startup, provider, or network
integration.  Loading only validates detached data; ``restore`` is explicit.
"""
import json
import os
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from llm.advisor_battle_state_store import _valid_state
from llm.advisor_reducer_state_model import state_fingerprint


SCHEMA_VERSION = "observation-replay-state-v1"
_METADATA = {"created_by": "offline_runtime_persistence"}


class ObservationReplayPersistence:
    def export_envelope(self, store, coordinator, session_id):
        read = store.read_snapshot(session_id)
        if read.get("status") != "ready":
            return {"status": "session_mismatch", "envelope": None}
        ledger = coordinator.export_applied_ledger(session_id)
        entries = [
            {
                "observation_id": observation_id,
                "canonical_fingerprint": canonical_fingerprint(observation),
                "canonical_observation": deepcopy(observation),
            }
            for observation_id, observation in sorted(ledger.items())
        ]
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "session_id": session_id,
            "store": {"fingerprint": read["state_fingerprint"], "state": deepcopy(read["state"])},
            "applied_observations": entries,
            "metadata": deepcopy(_METADATA),
        }
        return {"status": "ready", "envelope": envelope}

    def save(self, path, envelope):
        validated = self.validate(envelope)
        if validated["status"] != "load_ready":
            return {"status": "invalid_envelope"}
        target = Path(path)
        temporary = target.with_name(target.name + ".tmp")
        try:
            serialized = json.dumps(validated["envelope"], sort_keys=True, separators=(",", ":"))
            temporary.write_text(serialized, encoding="utf-8")
            os.replace(temporary, target)
            return {"status": "saved"}
        except (OSError, TypeError, ValueError):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return {"status": "io_error"}

    def load(self, path):
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"status": "file_not_found"}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"status": "invalid_json"}
        except OSError:
            return {"status": "io_error"}
        _restore_state_slot_key_types(value)
        return self.validate(value)

    def validate(self, value):
        required = {"schema_version", "session_id", "store", "applied_observations", "metadata"}
        if not isinstance(value, dict) or set(value) != required:
            return {"status": "invalid_envelope"}
        if value.get("schema_version") != SCHEMA_VERSION:
            return {"status": "unsupported_schema"}
        session = value.get("session_id")
        store = value.get("store")
        if (
            not isinstance(session, str)
            or not session
            or not isinstance(store, dict)
            or set(store) != {"fingerprint", "state"}
            or not isinstance(store.get("state"), dict)
            or not _valid_state(store["state"])
            or not isinstance(store.get("fingerprint"), str)
            or store["state"].get("session_id") != session
            or value.get("metadata") != _METADATA
        ):
            return {"status": "invalid_envelope"}
        try:
            if state_fingerprint(store["state"]) != store["fingerprint"]:
                return {"status": "fingerprint_mismatch"}
        except (TypeError, ValueError):
            return {"status": "invalid_envelope"}
        entries = value.get("applied_observations")
        if not isinstance(entries, list):
            return {"status": "invalid_envelope"}
        ledger = {}
        for entry in entries:
            if not _valid_ledger_entry(entry):
                return {"status": "invalid_envelope"}
            observation_id = entry["observation_id"]
            if entry["canonical_observation"].get("observation_id") != observation_id:
                return {"status": "invalid_envelope"}
            if observation_id in ledger:
                return {"status": "ledger_conflict"}
            if canonical_fingerprint(entry["canonical_observation"]) != entry["canonical_fingerprint"]:
                return {"status": "ledger_fingerprint_mismatch"}
            ledger[observation_id] = deepcopy(entry["canonical_observation"])
        return {"status": "load_ready", "envelope": deepcopy(value), "ledger": ledger}

    def restore(self, store, coordinator, candidate, expected_current_fingerprint):
        """Explicit same-session restore, with rollback only for ledger failure."""
        if not isinstance(candidate, dict) or candidate.get("status") != "load_ready":
            return {"status": "invalid_envelope"}
        envelope = candidate.get("envelope")
        ledger = candidate.get("ledger")
        if not isinstance(envelope, dict) or not isinstance(ledger, dict):
            return {"status": "invalid_envelope"}
        session = envelope["session_id"]
        read = store.read_snapshot(session)
        if read.get("status") == "session_mismatch":
            return {"status": "session_mismatch"}
        if read.get("status") != "ready" or read["state_fingerprint"] != expected_current_fingerprint:
            return {"status": "cas_conflict"}

        rollback_snapshot = store.capture_rollback_snapshot(session)
        old_ledger = coordinator.export_applied_ledger(session)
        replaced = store.compare_and_replace(
            envelope["store"]["state"],
            expected_session_id=session,
            expected_base_fingerprint=expected_current_fingerprint,
        )
        if replaced.get("status") not in {"replaced", "already_current"}:
            return {"status": "cas_conflict"}
        if coordinator.replace_applied_ledger(session, ledger):
            return {"status": "restored", "state_snapshot": deepcopy(replaced.get("state_snapshot"))}

        # Full-map replacement fails before its assignment.  Therefore the old
        # ledger remains intact; never attempt entry-by-entry repair here.
        if replaced["status"] == "already_current":
            return {"status": "restore_rolled_back"}
        rollback = store.compare_and_restore_snapshot(
            expected_current_fingerprint=envelope["store"]["fingerprint"],
            rollback_snapshot=rollback_snapshot,
        )
        if rollback.get("status") != "rollback_restored":
            return {"status": "critical_restore_inconsistency"}
        # ``old_ledger`` is intentionally only captured for recovery-unit
        # provenance: atomic replacement failure leaves it exact and unchanged.
        assert coordinator.export_applied_ledger(session) == old_ledger
        return {"status": "restore_rolled_back"}


def canonical_fingerprint(value):
    """Stable fingerprint of the canonical JSON-compatible observation."""
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _valid_ledger_entry(entry):
    return (
        isinstance(entry, dict)
        and set(entry) == {"observation_id", "canonical_fingerprint", "canonical_observation"}
        and isinstance(entry.get("observation_id"), str)
        and bool(entry["observation_id"])
        and isinstance(entry.get("canonical_fingerprint"), str)
        and isinstance(entry.get("canonical_observation"), dict)
        and _valid_canonical_observation(entry["canonical_observation"])
    )


def _restore_state_slot_key_types(envelope):
    """Reverse JSON's stringification of the state model's slot-map keys."""
    if not isinstance(envelope, dict):
        return
    state = envelope.get("store", {}).get("state") if isinstance(envelope.get("store"), dict) else None
    if not isinstance(state, dict):
        return
    for side_name in ("self_side", "opponent_side"):
        pokemon = state.get(side_name, {}).get("pokemon") if isinstance(state.get(side_name), dict) else None
        if isinstance(pokemon, dict):
            converted = {int(key) if isinstance(key, str) and key.isdigit() else key: value for key, value in pokemon.items()}
            pokemon.clear()
            pokemon.update(converted)


def _valid_canonical_observation(value):
    sequence = value.get("observation_sequence")
    turn_number = value.get("turn_number")
    return (
        isinstance(value.get("observation_id"), str)
        and bool(value["observation_id"])
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and isinstance(sequence, int)
        and not isinstance(sequence, bool)
        and sequence >= 1
        and isinstance(value.get("event_kind"), str)
        and bool(value["event_kind"])
        and (turn_number is None or (isinstance(turn_number, int) and not isinstance(turn_number, bool) and turn_number >= 1))
    )
