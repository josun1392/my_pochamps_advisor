from copy import deepcopy

from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _owner(side, slot, pokemon):
    return {"session_id": "switch-branch", "side": side, "slot_index": slot, "pokemon_id": pokemon}


def _branch():
    return {"schema_version": "deterministic-transition-preview-v1", "active": {
        "self": {**_owner("self", 0, "outgoing"), "current_hp": 91, "max_hp": 100, "fainted": False},
        "opponent": {**_owner("opponent", 0, "opponent"), "current_hp": 100, "max_hp": 100, "fainted": False},
    }, "current_state": {"current_state_session_id": "switch-branch", "outgoing_only": {"condition": "toxic", "item": "choice-band", "ability": "blaze", "type": ["fire"], "stage": 4}}}


def _incoming(*, owner=None, hp=70, condition="none"):
    owner = owner or _owner("self", 1, "incoming")
    absent = {"status": "known_absent"}
    side = lambda health: {"ability": absent, "item": absent, "boosts": {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0}, "current_hp": health, "max_hp": 100, "status": absent}
    current = {"current_state_session_id": "switch-branch", "current_hp_context": {"current_hp": [{"side": "self", "current_hp": hp, "maximum_hp": 100, "status": "incoming_authority", "source": "identity_bound_incoming_current_state"}, {"side": "opponent", "current_hp": 100, "maximum_hp": 100, "status": "incoming_authority", "source": "identity_bound_incoming_current_state"}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": condition, "status": "unknown" if condition == "unknown" else "incoming_authority", "source": "identity_bound_incoming_current_state"}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": side(hp), "defender": side(100)}}
    return {"owner": owner, "provenance": "identity_bound_incoming_current_state_v1", "hp_authority": {"status": "known", "current_hp": hp, "maximum_hp": 100, "provenance": "incoming_exact_hp"}, "fainted_authority": {"status": "known", "value": False}, "current_state": current, "incoming_type_authority": {"status": "known", "value": ["water"]}, "incoming_item_authority": {"status": "unknown"}, "incoming_ability_authority": {"status": "known", "value": "torrent"}}


def test_materializes_only_incoming_identity_authority_and_is_detached():
    source = _branch(); before = deepcopy(source)
    result = materialize_incoming_active_branch(source_branch=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), incoming_authority=_incoming())
    assert result["status"] == "resolved"
    state = result["next_state"]
    assert state["active"]["self"] == {**_owner("self", 1, "incoming"), "current_hp": 70, "max_hp": 100, "fainted": False}
    assert "outgoing_only" not in state["current_state"]
    assert state["current_state"]["condition_context"]["current_conditions"][0]["condition_type"] == "none"
    assert source == before and result["resulting_branch_fingerprint"] != result["source_branch_fingerprint"]


def test_unknown_nonmaterial_authority_is_preserved_and_stale_identity_rejects():
    source = _branch(); incoming = _incoming(condition="unknown")
    result = materialize_incoming_active_branch(source_branch=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), incoming_authority=incoming)
    assert result["status"] == "resolved"
    assert result["next_state"]["current_state"]["condition_context"]["current_conditions"][0]["status"] == "unknown"
    bad = _incoming(owner=_owner("self", 0, "outgoing"))
    assert materialize_incoming_active_branch(source_branch=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), incoming_authority=bad)["reason"] == "stale_or_mismatched_incoming_owner"
    assert materialize_incoming_active_branch(source_branch=source, source_branch_fingerprint="stale", incoming_authority=incoming)["reason"] == "stale_or_invalid_source_branch_fingerprint"


def test_existing_hypothetical_direct_consumes_materialized_incoming_branch_not_outgoing():
    source = _branch(); materialized = materialize_incoming_active_branch(source_branch=source, source_branch_fingerprint=fingerprint_transition_preview_state(source), incoming_authority=_incoming())["next_state"]
    action = {"owner": _owner("opponent", 0, "opponent"), "move": {"move_id": "seismic-toss", "slot_index": 0, "priority": 0, "category": "physical"}}
    descriptor = {"source_snapshot_fingerprint": "switch-direct-source", "owner": action["owner"], "move_metadata": {**action["move"], "type": "normal"}, "stat_provenance": {"attacker": {"pokemon_identity": "opponent", "types": {"available": True, "value": ["normal"]}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "incoming", "types": {"available": True, "value": ["water"]}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50}
    result = evaluate_hypothetical_direct_mechanics(branch_state=materialized, source_snapshot_fingerprint="switch-direct-source", action=action, expected_owner=action["owner"], direct_evaluation_input=descriptor)
    assert result["branch_state_fingerprint"] == fingerprint_transition_preview_state(materialized)
    assert result["status"] in {"known", "insufficient_context"}
    assert result["status"] != "rejected"
