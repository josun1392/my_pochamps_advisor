import pytest

import llm.advisor_runtime_d0_reactive_shield_common_block_context as subject
from llm.advisor_detached_opponent_response_profile import _bundle_kwargs


def _owner(side, pokemon_id):
    return {"session_id": "s", "side": side, "slot_index": 0, "pokemon_id": pokemon_id}


def _d0():
    return {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "branch", "decision_owner": _owner("self", "attacker"), "active_owners": {"self": _owner("self", "attacker"), "opponent": _owner("opponent", "shield")}}


def _response(move_id):
    return {"action_id": f"opponent_attack:{move_id}", "action_type": "attack", "move_id": move_id, "metadata_authority": {"metadata": {"move_id": move_id, "category": "status"}}}


def _action():
    return {"action_id": "attack:tackle", "identity": "tackle"}


def _success():
    return {"status": "resolved", "protection_success_authority": {"schema_version": "branch-protection-success-v1", "owner": _owner("opponent", "shield"), "previous_successful_protection_count": 0, "provenance": "explicit_branch_nonconsecutive_protection"}}


@pytest.mark.parametrize("move_id", ("silk-trap", "kings-shield", "obstruct", "spiky-shield", "baneful-bunker", "burning-bulwark"))
def test_all_canonical_reactive_shields_resolve_common_contact_facts(monkeypatch, move_id):
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    monkeypatch.setattr(subject, "freeze_runtime_d0_nonconsecutive_protection_success_authority", lambda **_: _success())
    monkeypatch.setattr(subject, "freeze_runtime_d0_canonical_contact_classification_authority", lambda **_: {"status": "resolved", "contact_state": "contact"})
    result = subject.freeze_runtime_d0_reactive_shield_common_block_context(
        strategy_d0=_d0(), runtime_snapshot={}, shield_owner=_owner("opponent", "shield"), shield_action=_response(move_id),
        blocked_attacker=_owner("self", "attacker"), blocked_action=_action(),
        frozen_move_metadata={"move_id": "tackle", "category": "physical", "protection_bypass": False},
    )
    assert result["outcome"] == "protection_applies_contact"
    assert "action_blocked" not in result


def test_non_contact_keeps_protection_applicable_but_marks_reactive_contact_inapplicable(monkeypatch):
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    monkeypatch.setattr(subject, "freeze_runtime_d0_nonconsecutive_protection_success_authority", lambda **_: _success())
    monkeypatch.setattr(subject, "freeze_runtime_d0_canonical_contact_classification_authority", lambda **_: {"status": "resolved", "contact_state": "non_contact"})
    result = subject.freeze_runtime_d0_reactive_shield_common_block_context(
        strategy_d0=_d0(), runtime_snapshot={}, shield_owner=_owner("opponent", "shield"), shield_action=_response("spiky-shield"),
        blocked_attacker=_owner("self", "attacker"), blocked_action=_action(), frozen_move_metadata={"move_id": "tackle", "category": "physical", "protection_bypass": False},
    )
    assert result["outcome"] == "protection_applies_non_contact"


def test_unknown_bypass_and_missing_history_fail_closed(monkeypatch):
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    unknown = subject.freeze_runtime_d0_reactive_shield_common_block_context(
        strategy_d0=_d0(), runtime_snapshot={}, shield_owner=_owner("opponent", "shield"), shield_action=_response("silk-trap"),
        blocked_attacker=_owner("self", "attacker"), blocked_action=_action(), frozen_move_metadata={"move_id": "tackle", "category": "physical"},
    )
    assert unknown["status"] == "incomplete"
    monkeypatch.setattr(subject, "freeze_runtime_d0_nonconsecutive_protection_success_authority", lambda **_: {"status": "incomplete", "reason": "last_executed_move_missing"})
    missing = subject.freeze_runtime_d0_reactive_shield_common_block_context(
        strategy_d0=_d0(), runtime_snapshot={}, shield_owner=_owner("opponent", "shield"), shield_action=_response("silk-trap"),
        blocked_attacker=_owner("self", "attacker"), blocked_action=_action(), frozen_move_metadata={"move_id": "tackle", "category": "physical", "protection_bypass": False},
    )
    assert missing["status"] == "incomplete"


def test_explicit_bypass_is_not_protection_and_foreign_owner_rejects(monkeypatch):
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    bypassed = subject.freeze_runtime_d0_reactive_shield_common_block_context(
        strategy_d0=_d0(), runtime_snapshot={}, shield_owner=_owner("opponent", "shield"), shield_action=_response("obstruct"),
        blocked_attacker=_owner("self", "attacker"), blocked_action=_action(), frozen_move_metadata={"move_id": "tackle", "category": "physical", "protection_bypass": True},
    )
    assert bypassed["outcome"] == "protection_not_applicable"
    rejected = subject.freeze_runtime_d0_reactive_shield_common_block_context(
        strategy_d0=_d0(), runtime_snapshot={}, shield_owner=_owner("opponent", "foreign"), shield_action=_response("obstruct"),
        blocked_attacker=_owner("self", "attacker"), blocked_action=_action(), frozen_move_metadata={"move_id": "tackle", "category": "physical", "protection_bypass": False},
    )
    assert rejected["status"] == "rejected"


def test_stale_runtime_and_unknown_contact_fail_closed(monkeypatch):
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "stale", "reason": "stale_runtime_d0"})
    stale = subject.freeze_runtime_d0_reactive_shield_common_block_context(
        strategy_d0=_d0(), runtime_snapshot={}, shield_owner=_owner("opponent", "shield"), shield_action=_response("baneful-bunker"),
        blocked_attacker=_owner("self", "attacker"), blocked_action=_action(), frozen_move_metadata={"move_id": "tackle", "category": "physical", "protection_bypass": False},
    )
    assert stale["status"] == "rejected"
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    monkeypatch.setattr(subject, "freeze_runtime_d0_nonconsecutive_protection_success_authority", lambda **_: _success())
    monkeypatch.setattr(subject, "freeze_runtime_d0_canonical_contact_classification_authority", lambda **_: {"status": "incomplete", "reason": "contact_unknown"})
    unknown_contact = subject.freeze_runtime_d0_reactive_shield_common_block_context(
        strategy_d0=_d0(), runtime_snapshot={}, shield_owner=_owner("opponent", "shield"), shield_action=_response("baneful-bunker"),
        blocked_attacker=_owner("self", "attacker"), blocked_action=_action(), frozen_move_metadata={"move_id": "tackle", "category": "physical", "protection_bypass": False},
    )
    assert unknown_contact["status"] == "incomplete"


def test_common_context_stays_in_live_bundle_and_only_supported_stage_inputs_reach_ordinary_pair_kwargs():
    d0 = _d0()
    bundle = {"status": "resolved", "schema_version": "live-opponent-response-authority-bundle-v1", "session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": d0["decision_owner"], "own_action_id": "attack:tackle", "opponent_response_action_id": "opponent_attack:silk-trap", "ordinary_pair_authorities": {"reactive_shield_common_block_context": {"status": "resolved"}, "opponent_protection_success_authority": {"schema_version": "branch-protection-success-v1"}, "incoming_contact_authority": {"status": "resolved"}, "silk_trap_reactive_interaction_authority": {"schema_version": "silk-trap-speed-drop-interaction-resolution-v1"}}}
    base = {"session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": d0["decision_owner"], "own_action_id": "attack:tackle", "target_owner": d0["decision_owner"], "opponent_actor": _owner("opponent", "shield")}
    snapshot = {"state": {"self_side": {"pokemon": {0: {"condition": "none", "current_confusion": None}}}, "opponent_side": {"pokemon": {0: {"condition": "none", "current_confusion": None}}}}}
    kwargs = _bundle_kwargs(bundle=bundle, base=base, opponent_action={"action_id": "opponent_attack:silk-trap"}, runtime_snapshot=snapshot, ordinary_pair=True)
    assert set(kwargs) == {"opponent_protection_success_authority", "incoming_contact_authority", "silk_trap_reactive_interaction_authority"}
    assert _bundle_kwargs(bundle=bundle, base=base, opponent_action={"action_id": "opponent_attack:silk-trap"}, runtime_snapshot=snapshot, ordinary_pair=False) == {}
