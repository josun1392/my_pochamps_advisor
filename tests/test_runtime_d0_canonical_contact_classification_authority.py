"""Strict D0 contact/non-contact classification coverage."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_canonical_contact_classification_authority import (
    SCHEMA_VERSION,
    canonical_move_contact_metadata,
    freeze_runtime_d0_canonical_contact_classification_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state():
    state = create_unknown_bootstrap_battle_state("contact-authority", "attacker", "target")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state, side):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": pokemon["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _action(d0, move_id="tackle", **overrides):
    metadata = {"move_id": move_id, "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}
    metadata.update(overrides)
    authority = {
        "status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1",
        "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": metadata,
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]), "active_attacker": deepcopy(d0["decision_owner"]),
    }
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}


def _freeze(d0, snapshot, action, state):
    return freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action,
        attacker=_owner(state, "self"), target=_owner(state, "opponent"),
    )


def test_exact_canonical_contact_and_non_contact_actions_resolve_without_mutation():
    state = _state(); before = deepcopy(state); snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    contact = _freeze(d0, snapshot, _action(d0, "tackle"), state)
    non_contact = _freeze(d0, snapshot, _action(d0, "flamethrower", category="special", power=90, type="fire"), state)
    assert contact["status"] == "resolved" and contact["schema_version"] == SCHEMA_VERSION
    assert contact["contact_state"] == "contact"
    assert non_contact["status"] == "resolved" and non_contact["contact_state"] == "non_contact"
    assert state == before


def test_missing_malformed_or_non_damaging_contact_metadata_fails_closed(monkeypatch):
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    assert _freeze(d0, snapshot, _action(d0, "water-gun", category="special", power=40, type="water"), state)["reason"] == "canonical_move_contact_metadata_missing"
    assert _freeze(d0, snapshot, _action(d0, "protect", category="status", power=None, type="normal", accuracy=None), state)["status"] == "incomplete"
    monkeypatch.setattr("llm.advisor_runtime_d0_canonical_contact_classification_authority._PATH", __import__("pathlib").Path("does-not-exist.json"))
    assert canonical_move_contact_metadata("tackle")["status"] == "rejected"


def test_stale_and_foreign_action_actor_target_or_metadata_bindings_reject():
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); action = _action(d0)
    state["self_side"]["pokemon"][0]["current_hp"] = 1
    assert _freeze(d0, _snapshot(state), action, state)["status"] == "rejected"

    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); action = _action(d0)
    foreign = {**_owner(state, "self"), "pokemon_id": "foreign"}
    assert freeze_runtime_d0_canonical_contact_classification_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, attacker=foreign, target=_owner(state, "opponent"))["status"] == "rejected"
    bad_target = deepcopy(action); bad_target["target_owner"] = _owner(state, "self")
    assert _freeze(d0, snapshot, bad_target, state)["status"] == "rejected"
    conflicting = deepcopy(action); conflicting["move_metadata_authority"]["metadata"]["move_id"] = "flamethrower"
    assert _freeze(d0, snapshot, conflicting, state)["status"] == "rejected"
