from copy import deepcopy

from llm.advisor_detached_current_healing_prevented_at_item_check_authority import (
    CURRENT_SCHEMA_VERSION,
    PSYCHIC_NOISE_TRANSITION_SCHEMA_VERSION,
    materialize_detached_current_healing_prevented_at_item_check_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _complete_state, _owner, _snapshot, _state


def _inputs(move_id="tackle"):
    state = _complete_state(_state())
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    attacker, recipient = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    binding = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    leaf = {"action_type": "attack", "consequences": {"target_final_hp": 40}, "provenance": {**binding, "attacker": attacker, "target": recipient, "move_id": move_id}}
    current = {"status": "resolved", "schema_version": CURRENT_SCHEMA_VERSION, **binding, "recipient": recipient, "state": "known_absent"}
    return d0, leaf, recipient, current, binding


def test_preserves_exact_current_absence_for_non_psychic_noise_leaf():
    d0, leaf, recipient, current, _ = _inputs()
    result = materialize_detached_current_healing_prevented_at_item_check_authority(strategy_d0=d0, terminal_leaf=leaf, recipient=recipient, current_healing_prevented_authority=current)
    assert result["status"] == "resolved"
    assert result["state"] == "known_absent"
    assert result["same_hit_transition"] is None


def test_psychic_noise_same_hit_transition_overrides_current_absence():
    d0, leaf, recipient, current, binding = _inputs("psychic-noise")
    leaf["consequences"]["healing_prevented_transition"] = {"status": "resolved", "schema_version": PSYCHIC_NOISE_TRANSITION_SCHEMA_VERSION, **binding, "outcome": "applied", "recipient": recipient, "state_after": "known_present"}
    result = materialize_detached_current_healing_prevented_at_item_check_authority(strategy_d0=d0, terminal_leaf=leaf, recipient=recipient, current_healing_prevented_authority=current)
    assert result["status"] == "resolved"
    assert result["state"] == "known_present"
    assert result["same_hit_transition"]["outcome"] == "applied"


def test_unknown_current_state_and_missing_psychic_noise_transition_fail_closed():
    d0, leaf, recipient, current, _ = _inputs()
    unknown = deepcopy(current) | {"status": "incomplete", "state": "unknown"}
    result = materialize_detached_current_healing_prevented_at_item_check_authority(strategy_d0=d0, terminal_leaf=leaf, recipient=recipient, current_healing_prevented_authority=unknown)
    assert result["status"] == "incomplete"
    assert result["reason"] == "current_healing_prevented_unknown"

    d0, psychic, recipient, current, _ = _inputs("psychic-noise")
    result = materialize_detached_current_healing_prevented_at_item_check_authority(strategy_d0=d0, terminal_leaf=psychic, recipient=recipient, current_healing_prevented_authority=current)
    assert result["status"] == "incomplete"
    assert result["reason"] == "psychic_noise_healing_prevented_transition_unavailable"


def test_rejects_foreign_recipient_or_transition_binding():
    d0, leaf, recipient, current, binding = _inputs("psychic-noise")
    leaf["consequences"]["healing_prevented_transition"] = {"status": "resolved", "schema_version": PSYCHIC_NOISE_TRANSITION_SCHEMA_VERSION, **binding, "outcome": "applied", "recipient": recipient, "state_after": "known_present"}
    forged = deepcopy(leaf)
    forged["consequences"]["healing_prevented_transition"]["source_branch_fingerprint"] = "foreign"
    result = materialize_detached_current_healing_prevented_at_item_check_authority(strategy_d0=d0, terminal_leaf=forged, recipient=recipient, current_healing_prevented_authority=current)
    assert result["status"] == "rejected"
    assert result["reason"] == "psychic_noise_healing_prevented_transition_binding_mismatch"
