import llm.advisor_runtime_d0_mat_block_active_entry_eligibility_authority as subject


def _owner():
    return {"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "guard"}


def _d0():
    owner = _owner()
    return {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "branch", "decision_owner": owner, "active_owners": {"self": {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}, "opponent": owner}}


def _snapshot():
    owner = _owner()
    return {"state": {"session_id": "s", "last_applied_observation_sequence": 7, "mat_block_active_entry_eligibility_context": {"schema_version": "mat-block-active-entry-eligibility-context-v1", "session_id": "s", "actor": owner, "decision_point": "trusted-decision", "action_id": "opponent_attack:mat-block", "move_id": "mat-block", "eligibility": "eligible", "active_entry_token": "entry", "provenance": {"event_kind": "mat_block_active_entry_eligibility_observed", "trust": "user_confirmed_observation", "source_sequence": 7}}}}


def test_live_action_without_caller_decision_point_uses_trusted_observation_provenance(monkeypatch):
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    result = subject.freeze_runtime_d0_mat_block_active_entry_eligibility_authority(
        strategy_d0=_d0(), runtime_snapshot=_snapshot(), mat_block_user=_owner(),
        mat_block_action={"action_id": "opponent_attack:mat-block", "move_id": "mat-block"},
    )
    assert result["status"] == "resolved"
    assert result["decision_point"] == "trusted-decision"


def test_foreign_supplied_decision_point_cannot_override_trusted_observation(monkeypatch):
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    result = subject.freeze_runtime_d0_mat_block_active_entry_eligibility_authority(
        strategy_d0=_d0(), runtime_snapshot=_snapshot(), mat_block_user=_owner(),
        mat_block_action={"action_id": "opponent_attack:mat-block", "move_id": "mat-block", "decision_point": "foreign"},
    )
    assert result["status"] == "rejected"
