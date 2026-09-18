from copy import deepcopy

import pytest

from llm.advisor_detached_encore_action_restriction import (
    materialize_detached_reflected_encore_application,
)
from llm.advisor_detached_reflected_status_routing_authority import (
    freeze_detached_reflected_status_routing_authority,
    validate_detached_reflected_status_routing_authority,
)
from llm.advisor_runtime_d0_status_special_application_authority import (
    freeze_runtime_d0_status_special_application_authority,
    freeze_runtime_d0_status_special_last_move_metadata_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _owner, _state


ENCORE_META = {
    "move_id": "encore",
    "category": "status",
    "type": "normal",
    "target": "selected-pokemon",
    "accuracy": 100,
    "power": None,
    "priority": 0,
}


def _metadata(move_id, *, priority=0, category="physical", encore_eligible=None):
    row = {
        "move_id": move_id,
        "category": category,
        "type": "normal",
        "target": "selected-pokemon",
        "accuracy": 100,
        "power": None if category == "status" else 40,
        "priority": priority,
    }
    if encore_eligible is not None:
        row["encore_eligible"] = encore_eligible
    return {"status": "resolved", "move_id": move_id, "metadata": row}


def _history(state, side, move_id, execution_id):
    owner = _owner(state, side)
    state[f"{side}_side"]["pokemon"][0]["last_executed_move"] = {
        "schema_version": "reducer-last-executed-move-v1",
        "owner": deepcopy(owner),
        "move_id": move_id,
        "source_action_id": f"{side}_attack:{move_id}",
        "execution_id": execution_id,
        "provenance": {
            "source_observation_id": execution_id,
            "source_sequence": 2 if side == "self" else 3,
            "trust": "user_confirmed_observation",
        },
    }


def _known_move(state, side, move_id):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    pokemon["known_move_ids"] = [move_id]
    pokemon["known_move_ids_provenance"] = {
        move_id: {
            "event_kind": "used_move_observed",
            "trust": "user_confirmed_observation",
            "source_observation_id": f"{side}-known-{move_id}",
            "source_sequence": 1,
        }
    }


def _pp(state, side, move_id, *, usable=True, missing=False, reason=None):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    if missing:
        pokemon["current_move_usability"] = None
        return
    pokemon["current_move_usability"] = {
        move_id: {
            "status": "known_usable" if usable else "known_unusable",
            "reason": None if usable else reason,
            "provenance": {
                "event_kind": "current_move_usability_observed",
                "trust": "user_confirmed_observation",
                "turn_number": 1,
                "source_observation_id": f"{side}-pp-{move_id}",
                "source_sequence": 10,
            },
        }
    }


def _encore_row(state, side, *, active=False, owner=None, locked_move="quick-attack", execution_id="used"):
    owner = deepcopy(owner if owner is not None else _owner(state, side))
    provenance = {
        "source_observation_id": f"{side}-encore-old",
        "source_sequence": 4 if side == "self" else 5,
        "trust": "user_confirmed_observation",
    }
    return {
        "schema_version": "reducer-action-restriction-lifecycle-v1",
        "owner": owner,
        "restriction": "encore",
        "activation_id": f"{side}-encore-old",
        "source_action_id": f"{side}_attack:encore",
        "source_move_id": "encore",
        "locked_move_id": locked_move,
        "last_used_execution_id": execution_id,
        "state": "active" if active else "not_active",
        "remaining_target_turns": 3 if active else None,
        "applied_turn": 1,
        "last_completed_turn": None if active else 4,
        "retired_reason": None if active else "expired",
        "application_provenance": deepcopy(provenance),
        "lifecycle_provenance": deepcopy(provenance),
    }


def _snapshot(state):
    from llm.advisor_reducer_state_model import state_fingerprint
    return {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }


def _case(
    *,
    actor_ability="pressure",
    actor_history="quick-attack",
    target_history="tackle",
    actor_encore="inactive",
    actor_pp="usable",
    target_pp="no_pp",
    include_actor_metadata=True,
    actor_metadata_eligible=None,
):
    state = _state()
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    state["self_side"]["pokemon"][0]["current_ability"] = actor_ability
    state["opponent_side"]["pokemon"][0]["current_ability"] = "magic-bounce"
    state["last_applied_observation_sequence"] = 10

    if actor_history is not None:
        _history(state, "self", actor_history, "self-used")
        _known_move(state, "self", actor_history)
    if target_history is not None:
        _history(state, "opponent", target_history, "opponent-used")
        _known_move(state, "opponent", target_history)

    if actor_history is not None:
        if actor_pp == "usable":
            _pp(state, "self", actor_history, usable=True)
        elif actor_pp == "no_pp":
            _pp(state, "self", actor_history, usable=False, reason="no_pp")
        elif actor_pp == "missing":
            _pp(state, "self", actor_history, missing=True)
        elif actor_pp == "other_restriction":
            _pp(state, "self", actor_history, usable=False, reason="disabled")
        else:
            raise AssertionError(actor_pp)
    if target_history is not None:
        if target_pp == "usable":
            _pp(state, "opponent", target_history, usable=True)
        elif target_pp == "no_pp":
            _pp(state, "opponent", target_history, usable=False, reason="no_pp")
        else:
            _pp(state, "opponent", target_history, missing=True)

    rows = {}
    if actor_encore == "inactive":
        rows["self"] = _encore_row(state, "self", active=False, locked_move=actor_history or "quick-attack", execution_id="self-used")
    elif actor_encore == "active":
        rows["self"] = _encore_row(state, "self", active=True, locked_move=actor_history or "quick-attack", execution_id="self-used")
    elif actor_encore != "missing":
        raise AssertionError(actor_encore)
    rows["opponent"] = _encore_row(state, "opponent", active=True, locked_move=target_history or "tackle", execution_id="opponent-used")
    state["current_encore_restrictions"] = rows

    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    assert d0["status"] == "resolved"
    bindings = {
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": d0["decision_owner"],
    }
    action = {
        "action_id": "attack:encore",
        "action_type": "attack",
        "identity": "encore",
        "opponent_actor": deepcopy(actor),
        **bindings,
        "move_metadata_authority": {
            "status": "resolved",
            "candidate_id": "attack:encore",
            "move_id": "encore",
            "active_attacker": deepcopy(actor),
            **bindings,
            "metadata": deepcopy(ENCORE_META),
        },
    }
    target_selected_action = {
        "action_id": "opponent_attack:tackle",
        "metadata_authority": {
            "metadata": {
                "move_id": "tackle",
                "category": "physical",
                "type": "normal",
                "power": 40,
                "accuracy": 100,
                "priority": 0,
            }
        },
    }

    catalog = {
        "tackle": _metadata("tackle", priority=0),
        "encore": _metadata("encore", priority=0, category="status"),
    }
    if include_actor_metadata and actor_history is not None:
        catalog[actor_history] = _metadata(
            actor_history,
            priority=1 if actor_history == "quick-attack" else 0,
            category="status" if actor_history == "encore" else "physical",
            encore_eligible=actor_metadata_eligible,
        )

    produced = freeze_runtime_d0_status_special_application_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        target_selected_action=target_selected_action,
        canonical_move_metadata_authorities=catalog,
    )
    detection = produced["reflection_authority"]
    route = freeze_detached_reflected_status_routing_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        original_actor=actor,
        original_target=target,
        reflection_detection_authority=detection,
    )
    application = materialize_detached_reflected_encore_application(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        routing_authority=route,
        canonical_move_metadata_authorities=catalog,
    )
    return {
        "state": state,
        "snapshot": snapshot,
        "d0": d0,
        "actor": actor,
        "target": target,
        "action": action,
        "catalog": catalog,
        "produced": produced,
        "detection": detection,
        "route": route,
        "application": application,
    }


def test_reflected_encore_rebinds_a_to_b_into_b_to_a_and_uses_only_a_restriction_facts():
    case = _case()
    before = deepcopy((case["snapshot"], case["d0"]))
    route, app = case["route"], case["application"]
    assert route["status"] == "resolved"
    assert route["original_actor"] == case["actor"]
    assert route["original_target"] == case["target"]
    assert route["reflector"] == case["target"]
    assert route["reflected_source"] == case["target"]
    assert route["reflected_target"] == case["actor"]
    assert route["move_id"] == "encore"
    assert route["original_action_id"] == case["action"]["action_id"]
    assert route["route_depth"] == 1 and route["reflection_consumed"] is True

    assert app["status"] == "resolved" and app["outcome"] == "applicable"
    assert app["actor"] == case["target"] and app["target"] == case["actor"]
    assert app["original_actor"] == case["actor"] and app["original_target"] == case["target"]
    assert app["action_id"] == case["action"]["action_id"] and app["move_id"] == "encore"
    assert app["execution_mode"] == "reflected_original_action"
    assert app["reflected_status_routing_authority"] == route
    assert app["locked_move_id"] == "quick-attack"
    assert app["locked_move_id"] != "tackle"
    assert app["locked_move_metadata"] == case["catalog"]["quick-attack"]["metadata"]
    assert app["last_used_execution_id"] == "self-used"
    assert app["remaining_target_turns"] == 3
    assert (case["snapshot"], case["d0"]) == before


def test_reflected_encore_uses_a_pp_not_b_pp():
    case = _case(actor_pp="usable", target_pp="no_pp")
    assert case["application"]["status"] == "resolved"
    assert case["application"]["outcome"] == "applicable"
    assert case["application"]["locked_move_id"] == "quick-attack"


def test_reflected_encore_already_active_on_a_is_existing_failed_result():
    app = _case(actor_encore="active")["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "failed"
    assert app["reason"] == "encore_target_already_encored"


def test_missing_a_current_encore_authority_fails_closed_even_b_has_active_state():
    app = _case(actor_encore="missing")["application"]
    assert app["status"] == "incomplete"
    assert app["reason"] == "current_encore_authority_missing"


def test_reflected_encore_rechecks_aroma_veil_on_a_not_magic_bounce_b():
    case = _case(actor_ability="aroma-veil")
    app = case["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "failed"
    assert app["reason"] == "encore_target_protected_by_aroma_veil"
    assert app["target"] == case["actor"]
    assert case["route"]["reflector"] == case["target"]


def test_reflected_encore_ineligible_last_move_preserves_existing_failed_result():
    app = _case(actor_history="encore", actor_pp="usable")["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "failed"
    assert app["reason"] == "encore_locked_move_ineligible"
    assert app["locked_move_id"] == "encore"


def test_reflected_encore_explicit_metadata_ineligibility_is_respected():
    app = _case(actor_metadata_eligible=False)["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "failed"
    assert app["reason"] == "encore_locked_move_ineligible"


def test_reflected_encore_no_pp_preserves_existing_failed_result():
    app = _case(actor_pp="no_pp")["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "failed"
    assert app["reason"] == "encore_locked_move_no_pp"
    assert app["locked_move_id"] == "quick-attack"


def test_missing_a_last_move_fails_closed_without_using_b_history():
    app = _case(actor_history=None, target_history="tackle")["application"]
    assert app["status"] == "incomplete"
    assert app["reason"] == "last_executed_move_authority_missing"


def test_missing_a_canonical_last_move_metadata_fails_closed():
    case = _case(include_actor_metadata=False)
    app = case["application"]
    assert app["status"] == "incomplete"
    assert app["reason"] == "last_executed_move_metadata_missing"


def test_missing_a_pp_authority_is_incomplete_even_b_has_current_pp():
    app = _case(actor_pp="missing", target_pp="usable")["application"]
    assert app["status"] == "incomplete"
    assert app["reason"] == "encore_locked_move_pp_authority_missing"


def test_a_pp_unusable_for_unrelated_reason_remains_incomplete():
    app = _case(actor_pp="other_restriction")["application"]
    assert app["status"] == "incomplete"
    assert app["reason"] == "encore_locked_move_pp_authority_missing"


def test_reusable_last_move_metadata_freezer_is_owner_and_exact_move_bound():
    case = _case()
    from llm.advisor_runtime_d0_last_executed_move_authority import freeze_runtime_d0_last_executed_move_authority
    history = freeze_runtime_d0_last_executed_move_authority(
        strategy_d0=case["d0"], runtime_snapshot=case["snapshot"], owner=case["actor"]
    )
    authority = freeze_runtime_d0_status_special_last_move_metadata_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        owner=case["actor"],
        last_used_move_authority=history,
        canonical_move_metadata_authorities=case["catalog"],
    )
    assert authority["status"] == "resolved"
    assert authority["owner"] == case["actor"]
    assert authority["metadata"]["move_id"] == "quick-attack"
    foreign = freeze_runtime_d0_status_special_last_move_metadata_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        owner=case["target"],
        last_used_move_authority=history,
        canonical_move_metadata_authorities=case["catalog"],
    )
    assert foreign["status"] == "incomplete"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda route, case: route.__setitem__("source_runtime_fingerprint", "stale"),
        lambda route, case: route.__setitem__("source_branch_fingerprint", "foreign"),
        lambda route, case: route.__setitem__("original_actor", case["target"]),
        lambda route, case: route.__setitem__("original_target", case["actor"]),
        lambda route, case: route.__setitem__("reflected_source", case["actor"]),
        lambda route, case: route.__setitem__("reflected_target", case["target"]),
        lambda route, case: route.__setitem__("original_action_id", "forged-action"),
        lambda route, case: route.__setitem__("move_id", "disable"),
    ],
)
def test_tampered_reflected_encore_route_rejects(mutator):
    case = _case()
    forged = deepcopy(case["route"])
    mutator(forged, case)
    assert validate_detached_reflected_status_routing_authority(forged)["status"] == "rejected"
    result = materialize_detached_reflected_encore_application(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        action=case["action"],
        routing_authority=forged,
        canonical_move_metadata_authorities=case["catalog"],
    )
    assert result["status"] == "rejected"


def test_stale_runtime_rejects_reflected_encore_at_consumption():
    case = _case()
    stale = deepcopy(case["snapshot"])
    stale["state_fingerprint"] = "stale-runtime"
    result = materialize_detached_reflected_encore_application(
        strategy_d0=case["d0"],
        runtime_snapshot=stale,
        action=case["action"],
        routing_authority=case["route"],
        canonical_move_metadata_authorities=case["catalog"],
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "reflected_encore_current_binding_invalid"


def test_second_reflection_attempt_rejects():
    case = _case()
    second = freeze_detached_reflected_status_routing_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        action=case["action"],
        original_actor=case["actor"],
        original_target=case["target"],
        reflection_detection_authority=case["detection"],
        source_route=case["route"],
    )
    assert second["status"] == "rejected"
    assert second["reason"] == "reflected_status_route_already_consumed"


def test_legacy_encore_reflected_detector_remains_fail_closed():
    case = _case()
    assert case["produced"]["status"] == "incomplete"
    assert case["produced"]["reason"] == "encore_reflection_execution_unsupported"
    assert case["produced"]["reflection_authority"] == case["detection"]
