from copy import deepcopy

import pytest

from llm.advisor_detached_reflected_status_routing_authority import (
    freeze_detached_reflected_status_routing_authority as freeze_route,
    validate_detached_reflected_status_routing_authority as validate_route,
)
from llm.advisor_detached_taunt_action_restriction import (
    materialize_detached_reflected_taunt_application,
    materialize_detached_taunt_application,
)
from llm.advisor_runtime_d0_status_special_application_authority import (
    freeze_runtime_d0_status_special_application_authority,
    freeze_runtime_d0_status_special_reflection_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _owner, _snapshot, _state


def _inputs(*, actor_ability="pressure", target_ability="magic-bounce"):
    state = _state()
    actor_raw = state["self_side"]["pokemon"][0]
    target_raw = state["opponent_side"]["pokemon"][0]
    actor_raw["current_ability"] = actor_ability
    target_raw["current_ability"] = target_ability
    snapshot = _snapshot(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    bindings = {
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": d0["decision_owner"],
    }
    metadata = {
        "move_id": "taunt",
        "category": "status",
        "type": "dark",
        "target": "selected-pokemon",
        "accuracy": 100,
        "power": None,
        "priority": 0,
    }
    action = {
        "action_id": "attack:taunt",
        "action_type": "attack",
        "identity": "taunt",
        "opponent_actor": actor,
        **bindings,
        "move_metadata_authority": {
            "status": "resolved",
            "candidate_id": "attack:taunt",
            "move_id": "taunt",
            "active_attacker": actor,
            **bindings,
            "metadata": metadata,
        },
    }
    target_selected_action = {
        "action_id": "opponent_attack:tackle",
        "metadata_authority": {"metadata": {"move_id": "tackle", "category": "physical"}},
    }
    produced = freeze_runtime_d0_status_special_application_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        target_selected_action=target_selected_action,
        canonical_move_metadata_authorities={},
    )
    detection = produced.get("reflection_authority")
    return state, snapshot, d0, actor, target, action, produced, detection


def _route(*, actor_ability="pressure", target_ability="magic-bounce"):
    state, snapshot, d0, actor, target, action, produced, detection = _inputs(
        actor_ability=actor_ability, target_ability=target_ability
    )
    route = freeze_route(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        original_actor=actor,
        original_target=target,
        reflection_detection_authority=detection,
    )
    return state, snapshot, d0, actor, target, action, produced, detection, route


def test_magic_bounce_detection_retains_authenticated_reflector_evidence():
    _, _, _, actor, target, action, produced, detection = _inputs()
    assert produced["status"] == "incomplete"
    assert produced["reason"] == "taunt_reflection_execution_unsupported"
    assert detection["status"] == "resolved" and detection["outcome"] == "reflected"
    assert detection["actor"] == actor and detection["target"] == target
    assert detection["action_id"] == action["action_id"] and detection["move_id"] == "taunt"
    assert detection["reflection_kind"] == "ability"
    assert detection["reflection_ability_id"] == "magic-bounce"
    assert detection["reflector"] == target
    ability = detection["reflector_ability_authority"]
    assert ability["ability"] == "magic-bounce" and ability["target"] == target
    assert ability["ability_provenance"]["event_kind"] == "current_ability_observed"
    assert ability["ability_provenance"]["trust"] == "user_confirmed_observation"


def test_exact_single_hop_route_inverts_a_to_b_into_b_to_a_and_preserves_lineage():
    _, snapshot, d0, actor, target, action, _, detection, route = _route()
    before = deepcopy((snapshot, d0))
    assert route["status"] == "resolved"
    assert route["original_actor"] == actor and route["original_target"] == target
    assert route["reflector"] == target
    assert route["reflected_source"] == target and route["reflected_target"] == actor
    assert route["original_action_id"] == action["action_id"]
    assert route["action_id"] == action["action_id"] and route["move_id"] == "taunt"
    assert route["selected_action_lineage"] == {
        "selected_action_id": action["action_id"],
        "selected_move_id": "taunt",
    }
    assert route["reflection_detection_authority"] == detection
    assert route["route_depth"] == 1 and route["reflection_consumed"] is True
    assert route["execution_mode"] == "reflected_original_action"
    assert route["detached_hypothetical"] is True
    assert validate_route(route)["status"] == "resolved"
    assert (snapshot, d0) == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda route, actor, target: route.__setitem__("source_runtime_fingerprint", "stale"),
        lambda route, actor, target: route.__setitem__("source_branch_fingerprint", "foreign"),
        lambda route, actor, target: route.__setitem__("original_actor", target),
        lambda route, actor, target: route.__setitem__("original_target", actor),
        lambda route, actor, target: route.__setitem__("reflector", actor),
        lambda route, actor, target: route.__setitem__("reflected_source", actor),
        lambda route, actor, target: route.__setitem__("reflected_target", target),
        lambda route, actor, target: route.__setitem__("original_action_id", "forged"),
        lambda route, actor, target: route.__setitem__("move_id", "encore"),
        lambda route, actor, target: route.__setitem__("route_depth", 2),
        lambda route, actor, target: route.__setitem__("reflection_consumed", False),
    ],
)
def test_tampered_resolved_route_rejects(mutation):
    _, _, _, actor, target, _, _, _, route = _route()
    forged = deepcopy(route)
    mutation(forged, actor, target)
    assert validate_route(forged)["status"] == "rejected"


def test_non_reflected_missing_magic_bounce_and_wrong_reflector_detection_reject():
    _, snapshot, d0, actor, target, action, _, detection = _inputs()
    _, plain_snapshot, plain_d0, plain_actor, plain_target, plain_action, _, _ = _inputs(target_ability="pressure")
    not_reflected = freeze_runtime_d0_status_special_reflection_authority(
        strategy_d0=plain_d0, runtime_snapshot=plain_snapshot, action=plain_action, actor=plain_actor, target=plain_target
    )
    rejected = freeze_route(strategy_d0=plain_d0, runtime_snapshot=plain_snapshot, action=plain_action, original_actor=plain_actor, original_target=plain_target, reflection_detection_authority=not_reflected)
    assert rejected["status"] == "rejected" and rejected["reason"] == "reflection_detection_not_reflected"

    missing = deepcopy(detection); missing.pop("reflector_ability_authority")
    assert freeze_route(strategy_d0=d0, runtime_snapshot=snapshot, action=action, original_actor=actor, original_target=target, reflection_detection_authority=missing)["status"] == "rejected"

    wrong = deepcopy(detection); wrong["reflector"] = actor
    assert freeze_route(strategy_d0=d0, runtime_snapshot=snapshot, action=action, original_actor=actor, original_target=target, reflection_detection_authority=wrong)["status"] == "rejected"


def test_stale_runtime_foreign_branch_wrong_identity_and_altered_lineage_reject():
    state, snapshot, d0, actor, target, action, _, detection = _inputs()
    stale_state = deepcopy(state); stale_state["self_side"]["pokemon"][0]["current_hp"] -= 1
    stale_snapshot = _snapshot(stale_state)
    assert freeze_route(strategy_d0=d0, runtime_snapshot=stale_snapshot, action=action, original_actor=actor, original_target=target, reflection_detection_authority=detection)["reason"] == "stale_reflected_status_runtime"

    foreign = deepcopy(detection); foreign["source_branch_fingerprint"] = "foreign"
    assert freeze_route(strategy_d0=d0, runtime_snapshot=snapshot, action=action, original_actor=actor, original_target=target, reflection_detection_authority=foreign)["status"] == "rejected"

    assert freeze_route(strategy_d0=d0, runtime_snapshot=snapshot, action=action, original_actor=target, original_target=actor, reflection_detection_authority=detection)["reason"] == "reflection_detection_binding_mismatch"

    bad_action = deepcopy(action); bad_action["action_id"] = "attack:forged"
    assert freeze_route(strategy_d0=d0, runtime_snapshot=snapshot, action=bad_action, original_actor=actor, original_target=target, reflection_detection_authority=detection)["reason"] == "reflection_detection_binding_mismatch"

    bad_move = deepcopy(action); bad_move["identity"] = "encore"; bad_move["move_metadata_authority"]["metadata"]["move_id"] = "encore"
    assert freeze_route(strategy_d0=d0, runtime_snapshot=snapshot, action=bad_move, original_actor=actor, original_target=target, reflection_detection_authority=detection)["reason"] == "reflection_detection_binding_mismatch"


def test_second_routing_and_malformed_validation_request_fail_closed():
    _, snapshot, d0, actor, target, action, _, detection, route = _route()
    second = freeze_route(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        original_actor=actor,
        original_target=target,
        reflection_detection_authority=detection,
        source_route=route,
    )
    assert second["status"] == "rejected" and second["reason"] == "reflected_status_route_already_consumed"
    malformed = deepcopy(route); malformed["validation_request"] = None
    assert validate_route(malformed)["status"] == "rejected"


def test_forged_magic_bounce_evidence_cannot_override_exact_runtime_truth():
    _, snapshot, d0, actor, target, action, _, detection = _inputs()
    forged = deepcopy(detection)
    forged["reflector_ability_authority"]["ability"] = "pressure"
    assert freeze_route(strategy_d0=d0, runtime_snapshot=snapshot, action=action, original_actor=actor, original_target=target, reflection_detection_authority=forged)["status"] == "rejected"


def test_unknown_ability_and_neutralizing_gas_remain_fail_closed():
    state = _state(); state["opponent_side"]["pokemon"][0]["current_ability"] = None
    snapshot = _snapshot(state); actor = _owner(state, "self")
    unknown_d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    assert unknown_d0["status"] != "resolved"

    _, _, _, _, _, _, gas, _ = _inputs(actor_ability="neutralizing-gas")
    assert gas["status"] == "incomplete" and gas["reason"] == "status_special_ability_suppression_unresolved"


def test_reflected_taunt_applies_to_original_actor_only_and_stays_detached():
    _, snapshot, d0, actor, target, action, _, _, route = _route()
    before = deepcopy((snapshot, d0))
    result = materialize_detached_reflected_taunt_application(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, routing_authority=route
    )
    assert result["status"] == "resolved" and result["outcome"] == "applied"
    assert result["actor"] == target and result["target"] == actor
    assert result["action_id"] == action["action_id"] and result["move_id"] == "taunt"
    assert result["execution_mode"] == "reflected_original_action"
    assert result["reflected_status_routing_authority"] == route
    assert result["remaining_target_turns"] == 3
    assert result["target"] != target
    assert (snapshot, d0) == before


@pytest.mark.parametrize(
    ("actor_ability", "reason"),
    [
        ("oblivious", "taunt_target_oblivious"),
        ("aroma-veil", "taunt_target_protected_by_aroma_veil"),
    ],
)
def test_reflected_taunt_re_evaluates_recipient_ability_on_original_actor(actor_ability, reason):
    _, snapshot, d0, actor, target, action, _, _, route = _route(actor_ability=actor_ability)
    result = materialize_detached_reflected_taunt_application(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, routing_authority=route
    )
    assert result["status"] == "resolved" and result["outcome"] == "no_effect"
    assert result["reason"] == reason
    assert result["actor"] == target and result["target"] == actor


def test_magic_bounce_holder_is_not_reused_as_reflected_taunt_recipient_blocker():
    _, snapshot, d0, actor, target, action, _, _, route = _route(actor_ability="pressure", target_ability="magic-bounce")
    result = materialize_detached_reflected_taunt_application(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, routing_authority=route
    )
    assert result["outcome"] == "applied"
    assert result["target"] == actor and result["target"] != target


def test_legacy_taunt_path_still_fails_closed_on_reflected_detector():
    _, snapshot, d0, actor, target, action, produced, detection = _inputs()
    ability = detection["reflector_ability_authority"]
    base = {
        "status": "resolved",
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": d0["decision_owner"],
        "actor": actor,
        "target": target,
        "action_id": action["action_id"],
        "move_id": "taunt",
    }
    legacy = materialize_detached_taunt_application(
        strategy_d0=d0,
        action=action,
        actor=actor,
        target=target,
        accuracy_authority={**base, "outcome": "hit"},
        target_ability_authority=ability,
        target_side_ability_authority=ability,
        protection_authority={**base, "outcome": "not_applicable"},
        reflection_authority=detection,
    )
    assert produced["reason"] == "taunt_reflection_execution_unsupported"
    assert legacy["status"] == "incomplete" and legacy["reason"] == "taunt_reflection_execution_unsupported"
    assert snapshot["state"]["self_side"]["pokemon"][0].get("current_taunt_restriction") is None
