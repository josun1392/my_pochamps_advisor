import pytest

from llm.advisor_runtime_d0_target_current_hp_power_authority import freeze_runtime_d0_target_current_hp_power_authority
from llm.advisor_direct_mechanics import _target_current_hp_power_context
from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger
from tests.test_detached_opponent_response_profile import _inputs


def _authority(move: str, current: int) -> dict:
    _state, snapshot, d0, _own, _responses, _orders = _inputs(opponent_hp=current)
    return freeze_runtime_d0_target_current_hp_power_authority(strategy_d0=d0, runtime_snapshot=snapshot, move={"move_id": move}, user=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"])


@pytest.mark.parametrize(("move", "current", "power"), [("hard-press", 100, 100), ("hard-press", 1, 1), ("crush-grip", 50, 61), ("wring-out", 1, 2)])
def test_execution_time_target_hp_authority_uses_exact_variant(move: str, current: int, power: int) -> None:
    authority = _authority(move, current)
    assert authority["status"] == "resolved" and authority["resolved_base_power"] == power
    assert _target_current_hp_power_context(move_id=move, current={"target_current_hp_power_authority": authority})["effective_power"] == power


def test_target_hp_authority_fails_closed_for_missing_or_forged_hp() -> None:
    assert _authority("hard-press", 0)["status"] != "resolved"
    authority = _authority("crush-grip", 50)
    forged = dict(authority); forged["resolved_base_power"] = 121
    assert _target_current_hp_power_context(move_id="crush-grip", current={"target_current_hp_power_authority": forged})["status"] == "insufficient_context"


def test_immediate_attack_binds_execution_time_hp_power_to_each_leaf() -> None:
    _state, snapshot, d0, _own, _responses, _orders = _inputs(opponent_hp=50)
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    metadata = {"move_id": "crush-grip", "category": "physical", "power": 1, "type": "normal", "accuracy": 100, "priority": 0, "contact": True, "protection_blockable": True, "family": "target_current_hp_power"}
    metadata_authority = {"status": "resolved", "metadata": metadata, "move_id": "crush-grip", "active_attacker": actor, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    ledger = _attack_ledger(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, metadata_authority=metadata_authority, action={"action_id": "attack:crush-grip", "action_type": "attack", "identity": "crush-grip"})
    assert ledger["status"] == "evaluable"
    assert {leaf["provenance"]["target_current_hp_power_authority"]["resolved_base_power"] for leaf in ledger["terminal_leaves"]} == {61}
