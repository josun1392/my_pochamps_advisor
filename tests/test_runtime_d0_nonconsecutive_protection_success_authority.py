from copy import deepcopy

from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_nonconsecutive_protection_success_authority import (
    freeze_runtime_d0_nonconsecutive_protection_success_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_native_damage_context import _state


def _owner(state, side="self"):
    row = state[f"{side}_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": row["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _record(state, move_id):
    owner = _owner(state, "opponent")
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "replay_policy_version": "v1", "ordered_steps": [{"observation_id": f"used-{move_id}", "observation_sequence": 1, "planned_effect": "record_executed_move", "trust": "user_confirmed_observation", **owner, "turn_number": 1, "move_id": move_id, "source_action_id": f"opponent_attack:{move_id}"}]}
    return project_atomic_transition(state, plan, state["session_id"])["projected_state"]


def _freeze(state, move_id="protect"):
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    action = {"action_id": f"opponent_attack:{move_id}", "action_type": "attack", "move_id": move_id,
              "metadata_authority": {"metadata": {"move_id": move_id, "category": "status", "target": "user", "accuracy": None}}}
    return snapshot, d0, action


def test_known_non_protection_history_proves_zero_count_for_ordinary_and_reactive_shields():
    for move_id in ("protect", "detect", "silk-trap", "kings-shield", "obstruct", "spiky-shield", "baneful-bunker", "burning-bulwark"):
        state = _record(_state(f"nonconsecutive-{move_id}"), "tackle")
        snapshot, d0, action = _freeze(state, move_id)
        result = freeze_runtime_d0_nonconsecutive_protection_success_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, protection_owner=_owner(state, "opponent"), protection_action=action,
        )
        assert result["status"] == "resolved"
        assert result["protection_success_authority"] == {
            "schema_version": "branch-protection-success-v1", "owner": _owner(state, "opponent"),
            "previous_successful_protection_count": 0, "provenance": "explicit_branch_nonconsecutive_protection",
        }


def test_missing_or_chain_history_never_infers_nonconsecutive_success():
    state = _state("missing-protection-history")
    snapshot, d0, action = _freeze(state)
    missing = freeze_runtime_d0_nonconsecutive_protection_success_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, protection_owner=_owner(state, "opponent"), protection_action=action,
    )
    assert missing["status"] == "incomplete"
    for prior in ("protect", "detect", "kings-shield"):
        chained = _record(_state(f"prior-{prior}"), prior)
        snapshot, d0, action = _freeze(chained)
        result = freeze_runtime_d0_nonconsecutive_protection_success_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, protection_owner=_owner(chained, "opponent"), protection_action=action,
        )
        assert result["status"] == "incomplete"
        assert result["reason"] == "previous_protection_success_chain_state_unproven"


def test_foreign_owner_or_unsupported_response_rejects():
    state = _record(_state("foreign-protection-history"), "tackle")
    snapshot, d0, action = _freeze(state)
    foreign = freeze_runtime_d0_nonconsecutive_protection_success_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, protection_owner={**_owner(state, "opponent"), "pokemon_id": "foreign"}, protection_action=action,
    )
    assert foreign["status"] == "rejected"
    unsupported = freeze_runtime_d0_nonconsecutive_protection_success_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, protection_owner=_owner(state, "opponent"), protection_action={**action, "move_id": "kings-shield", "metadata_authority": {"metadata": {"move_id": "kings-shield", "category": "status", "target": "user", "accuracy": None}}},
    )
    assert unsupported["status"] == "resolved"
