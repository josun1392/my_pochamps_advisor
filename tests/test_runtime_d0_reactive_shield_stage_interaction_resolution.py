import pytest

import llm.advisor_runtime_d0_reactive_shield_stage_interaction_resolution as subject
from llm.advisor_runtime_d0_silk_trap_speed_drop_interaction_authority import (
    freeze_runtime_d0_silk_trap_speed_drop_interaction_authority,
    freeze_runtime_d0_kings_shield_attack_drop_interaction_authority,
    freeze_runtime_d0_obstruct_defense_drop_interaction_authority,
)
from llm.advisor_runtime_d0_canonical_contact_classification_authority import freeze_runtime_d0_canonical_contact_classification_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_reducer_state_model import state_fingerprint
from tests.test_detached_immediate_protection_response_pair import _own_action
from tests.test_detached_opponent_response_profile import _inputs


def _owner(side, pokemon_id):
    return {"session_id": "s", "side": side, "slot_index": 0, "pokemon_id": pokemon_id}


def _d0():
    return {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "branch", "decision_owner": _owner("self", "attacker"), "active_owners": {"self": _owner("self", "attacker"), "opponent": _owner("opponent", "shield")}}


def _common(family="silk_trap", outcome="protection_applies_contact"):
    move, stat, delta = {"silk_trap": ("silk-trap", "speed", -1), "kings_shield": ("kings-shield", "attack", -1), "obstruct": ("obstruct", "defense", -2)}[family]
    d0 = _d0(); owner = d0["active_owners"]["opponent"]; attacker = d0["active_owners"]["self"]
    base = {"status": "resolved", "schema_version": "runtime-d0-reactive-shield-common-block-context-v1", "session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": attacker, "shield_owner": owner, "shield_action_id": f"opponent_attack:{move}", "shield_move_id": move, "shield_family": family, "blocked_attacker": attacker, "blocked_action_id": "attack:tackle", "blocked_move_id": "tackle", "outcome": outcome}
    base["protection_success_authority"] = {"schema_version": "branch-protection-success-v1", "owner": owner, "previous_successful_protection_count": 0, "provenance": "explicit_branch_nonconsecutive_protection"}
    base["bypass_authority"] = {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": attacker, "blocked_attacker": attacker, "blocked_action_id": "attack:tackle", "blocked_move_id": "tackle", "bypassed": False}
    base["contact_authority"] = {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": attacker, "action_id": "attack:tackle", "move_id": "tackle", "attacker": attacker, "target": owner, "contact_state": "contact"}
    return base, stat, delta


def _modifiers(ability="pressure", item=None):
    return {"ability_authority": {"status": "known", "value": ability}, "item_authority": {"status": "known_absent"} if item is None else {"status": "known", "value": item}}


@pytest.mark.parametrize(("family", "ability", "outcome", "delta"), (("silk_trap", "pressure", "applies", -1), ("silk_trap", "clear-body", "prevented", 0), ("silk_trap", "contrary", "reversed", 1), ("kings_shield", "pressure", "applies", -1), ("kings_shield", "white-smoke", "prevented", 0), ("kings_shield", "contrary", "reversed", 1), ("obstruct", "pressure", "applies", -2), ("obstruct", "full-metal-body", "prevented", 0), ("obstruct", "contrary", "reversed", 2)))
def test_stage_shield_resolver_produces_exact_existing_resolution_shapes(monkeypatch, family, ability, outcome, delta):
    common, stat, _ = _common(family); d0 = _d0()
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    monkeypatch.setattr(subject, "freeze_runtime_current_stage_authority", lambda **_: {"status": "resolved", "stages": {stat: {"status": "known", "value": 0}}})
    calls = []
    def modifiers(*_):
        calls.append(True)
        return _modifiers(ability if len(calls) == 1 else "pressure")
    monkeypatch.setattr(subject, "_current_modifier_authorities", modifiers)
    result = subject.freeze_runtime_d0_reactive_shield_stage_interaction_resolution(strategy_d0=d0, runtime_snapshot={}, common_block_context=common)
    assert (result["status"], result["outcome"], result["resulting_delta"]) == ("resolved", outcome, delta)
    assert result["interaction_resolution"]["resulting_delta"] == delta


def test_noncontact_unknown_modifier_item_and_stale_context_fail_closed(monkeypatch):
    common, stat, _ = _common(); d0 = _d0()
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "current"})
    monkeypatch.setattr(subject, "freeze_runtime_current_stage_authority", lambda **_: {"status": "resolved", "stages": {stat: {"status": "known", "value": 0}}})
    common["outcome"] = "protection_applies_non_contact"
    assert subject.freeze_runtime_d0_reactive_shield_stage_interaction_resolution(strategy_d0=d0, runtime_snapshot={}, common_block_context=common)["outcome"] == "not_applicable"
    common, _, _ = _common()
    monkeypatch.setattr(subject, "_current_modifier_authorities", lambda *_: _modifiers("unknown-ability"))
    assert subject.freeze_runtime_d0_reactive_shield_stage_interaction_resolution(strategy_d0=d0, runtime_snapshot={}, common_block_context=common)["status"] == "incomplete"
    monkeypatch.setattr(subject, "_current_modifier_authorities", lambda *_: _modifiers("pressure", "clear-amulet"))
    assert subject.freeze_runtime_d0_reactive_shield_stage_interaction_resolution(strategy_d0=d0, runtime_snapshot={}, common_block_context=common)["status"] == "incomplete"
    monkeypatch.setattr(subject, "runtime_strategy_d0_freshness", lambda **_: {"status": "stale", "reason": "stale_runtime_d0"})
    assert subject.freeze_runtime_d0_reactive_shield_stage_interaction_resolution(strategy_d0=d0, runtime_snapshot={}, common_block_context=common)["status"] == "rejected"


def test_foreign_common_context_rejects_without_mutation(monkeypatch):
    common, _, _ = _common(); d0 = _d0(); before = dict(common)
    common["blocked_action_id"] = "foreign"
    assert subject.freeze_runtime_d0_reactive_shield_stage_interaction_resolution(strategy_d0=d0, runtime_snapshot={}, common_block_context=common)["status"] == "rejected"
    assert before["blocked_action_id"] == "attack:tackle"


@pytest.mark.parametrize(("family", "lower"), (("silk_trap", freeze_runtime_d0_silk_trap_speed_drop_interaction_authority), ("kings_shield", freeze_runtime_d0_kings_shield_attack_drop_interaction_authority), ("obstruct", freeze_runtime_d0_obstruct_defense_drop_interaction_authority)))
def test_resolved_shape_is_accepted_by_existing_family_lower_owner(family, lower):
    state, _snapshot_unused, _d0_unused, _own_unused, _responses, _orders = _inputs()
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner={"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": state["self_side"]["pokemon"][0]["pokemon_id"]})
    action = _own_action(d0, "tackle")
    common, _, _ = _common(family)
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner"):
        common[key] = d0["strategy_preview_fingerprint"] if key == "source_branch_fingerprint" else d0[key]
    common["shield_owner"] = d0["active_owners"]["opponent"]; common["blocked_attacker"] = d0["active_owners"]["self"]
    common["blocked_action_id"] = action["action_id"]; common["blocked_move_id"] = action["identity"]
    common["protection_success_authority"]["owner"] = d0["active_owners"]["opponent"]
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "blocked_attacker", "blocked_action_id", "blocked_move_id"):
        common["bypass_authority"][key] = common[key]
    common["contact_authority"] = freeze_runtime_d0_canonical_contact_classification_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, attacker=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"])
    resolved = subject.freeze_runtime_d0_reactive_shield_stage_interaction_resolution(strategy_d0=d0, runtime_snapshot=snapshot, common_block_context=common)
    lower_result = lower(strategy_d0=d0, runtime_snapshot=snapshot, shield_owner=d0["active_owners"]["opponent"], blocked_attacker=d0["active_owners"]["self"], blocked_action=action, contact_authority=common["contact_authority"], protection_authority=resolved["protection_authority"], interaction_resolution=resolved["interaction_resolution"])
    assert resolved["status"] == lower_result["status"] == "resolved"
