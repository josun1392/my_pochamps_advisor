from copy import deepcopy

import pytest

from llm.advisor_detached_disable_action_restriction import (
    materialize_detached_reflected_disable_application,
)
from llm.advisor_detached_reflected_status_routing_authority import (
    freeze_detached_reflected_status_routing_authority,
    validate_detached_reflected_status_routing_authority,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_status_special_application_authority import (
    freeze_runtime_d0_status_special_application_authority,
    freeze_runtime_d0_status_special_current_known_moves_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _owner, _state


DISABLE_META = {
    "move_id": "disable",
    "category": "status",
    "type": "normal",
    "target": "selected-pokemon",
    "accuracy": 100,
    "power": None,
    "priority": 0,
}


def _provenance(sequence, observation):
    return {
        "event_kind": "used_move_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": observation,
        "source_sequence": sequence,
    }


def _set_known_moves(state, side, moves, *, authenticated=True):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    pokemon["known_move_ids"] = list(moves)
    pokemon["known_move_ids_provenance"] = (
        {move: _provenance(index + 10, f"{side}-known-{move}") for index, move in enumerate(moves)}
        if authenticated
        else None
    )


def _set_history(state, side, move, execution_id):
    owner = _owner(state, side)
    state[f"{side}_side"]["pokemon"][0]["last_executed_move"] = {
        "schema_version": "reducer-last-executed-move-v1",
        "owner": deepcopy(owner),
        "move_id": move,
        "source_action_id": f"{side}_attack:{move}",
        "execution_id": execution_id,
        "provenance": {
            "source_observation_id": execution_id,
            "source_sequence": 2 if side == "self" else 3,
            "trust": "user_confirmed_observation",
        },
    }


def _disable_row(state, side, *, active=False, owner=None, disabled_move="thunderbolt", execution_id="old-used"):
    owner = deepcopy(owner if owner is not None else _owner(state, side))
    provenance = {
        "source_observation_id": f"{side}-disable-old",
        "source_sequence": 4 if side == "self" else 5,
        "trust": "user_confirmed_observation",
    }
    return {
        "schema_version": "reducer-action-restriction-lifecycle-v1",
        "owner": owner,
        "restriction": "disable",
        "activation_id": f"{side}-disable-old",
        "source_action_id": f"{side}_attack:disable",
        "source_move_id": "disable",
        "disabled_move_id": disabled_move,
        "last_used_execution_id": execution_id,
        "state": "active" if active else "not_active",
        "remaining_target_turns": 4 if active else None,
        "applied_turn": 1,
        "last_completed_turn": None if active else 5,
        "retired_reason": None if active else "expired",
        "application_provenance": deepcopy(provenance),
        "lifecycle_provenance": deepcopy(provenance),
    }


def _snapshot(state):
    return {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }


def _case(
    *,
    actor_ability="pressure",
    actor_history="thunderbolt",
    actor_known=("thunderbolt",),
    actor_known_authenticated=True,
    actor_disable="inactive",
    original_target_history="tackle",
    original_target_known=("tackle",),
):
    state = _state()
    actor = _owner(state, "self")
    target = _owner(state, "opponent")
    state["self_side"]["pokemon"][0]["current_ability"] = actor_ability
    state["opponent_side"]["pokemon"][0]["current_ability"] = "magic-bounce"

    _set_known_moves(state, "self", actor_known, authenticated=actor_known_authenticated)
    _set_known_moves(state, "opponent", original_target_known)
    if actor_history is not None:
        _set_history(state, "self", actor_history, "self-used")
    if original_target_history is not None:
        _set_history(state, "opponent", original_target_history, "opponent-used")

    rows = {}
    if actor_disable == "inactive":
        rows["self"] = _disable_row(state, "self", active=False, disabled_move=actor_history or "thunderbolt", execution_id="self-used")
    elif actor_disable == "active":
        rows["self"] = _disable_row(state, "self", active=True, disabled_move=actor_history or "thunderbolt", execution_id="self-used")
    elif actor_disable == "foreign_inactive":
        rows["self"] = _disable_row(
            state,
            "self",
            active=False,
            owner={"session_id": state["session_id"], "side": "self", "slot_index": 1, "pokemon_id": "retired-self"},
            disabled_move=actor_history or "thunderbolt",
            execution_id="self-used",
        )
    elif actor_disable != "missing":
        raise AssertionError(actor_disable)

    # B deliberately has different family facts, including an active Disable.
    rows["opponent"] = _disable_row(state, "opponent", active=True, disabled_move=original_target_history or "tackle", execution_id="opponent-used")
    state["current_disable_restrictions"] = rows

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
        "action_id": "attack:disable",
        "action_type": "attack",
        "identity": "disable",
        "opponent_actor": deepcopy(actor),
        **bindings,
        "move_metadata_authority": {
            "status": "resolved",
            "candidate_id": "attack:disable",
            "move_id": "disable",
            "active_attacker": deepcopy(actor),
            **bindings,
            "metadata": deepcopy(DISABLE_META),
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
    produced = freeze_runtime_d0_status_special_application_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        target_selected_action=target_selected_action,
        canonical_move_metadata_authorities={},
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
    application = materialize_detached_reflected_disable_application(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        routing_authority=route,
    )
    return {
        "state": state,
        "snapshot": snapshot,
        "d0": d0,
        "actor": actor,
        "target": target,
        "action": action,
        "produced": produced,
        "detection": detection,
        "route": route,
        "application": application,
    }


def test_reflected_disable_rebinds_a_to_b_into_b_to_a_and_uses_a_family_facts_only():
    case = _case()
    before = deepcopy((case["snapshot"], case["d0"]))
    route, app = case["route"], case["application"]
    assert route["status"] == "resolved"
    assert route["original_actor"] == case["actor"]
    assert route["original_target"] == case["target"]
    assert route["reflector"] == case["target"]
    assert route["reflected_source"] == case["target"]
    assert route["reflected_target"] == case["actor"]
    assert route["original_action_id"] == case["action"]["action_id"]
    assert route["move_id"] == "disable"
    assert route["route_depth"] == 1 and route["reflection_consumed"] is True

    assert app["status"] == "resolved" and app["outcome"] == "applicable"
    assert app["actor"] == case["target"] and app["target"] == case["actor"]
    assert app["original_actor"] == case["actor"] and app["original_target"] == case["target"]
    assert app["action_id"] == case["action"]["action_id"] and app["move_id"] == "disable"
    assert app["execution_mode"] == "reflected_original_action"
    assert app["reflected_status_routing_authority"] == route
    assert app["disabled_move_id"] == "thunderbolt"
    assert app["disabled_move_id"] != "tackle"
    assert app["last_used_execution_id"] == "self-used"
    assert app["remaining_target_turns"] == 4
    assert (case["snapshot"], case["d0"]) == before


def test_reflected_disable_uses_a_known_moves_not_b_known_moves():
    case = _case(actor_known=("thunderbolt",), original_target_known=("tackle", "water-gun", "protect", "rest"))
    assert case["application"]["status"] == "resolved"
    assert case["application"]["outcome"] == "applicable"
    assert case["application"]["disabled_move_id"] == "thunderbolt"


def test_reflected_disable_already_active_on_a_is_canonical_failure_even_b_context_differs():
    case = _case(actor_disable="active")
    app = case["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "canonical_failure"
    assert app["reason"] == "disable_target_already_disabled"
    assert app["target"] == case["actor"]


def test_reflected_disable_re_evaluates_aroma_veil_on_a_not_magic_bounce_b():
    case = _case(actor_ability="aroma-veil")
    app = case["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "canonical_failure"
    assert app["reason"] == "disable_target_protected_by_aroma_veil"
    assert app["target"] == case["actor"]
    assert case["target"] == case["route"]["reflector"]


def test_missing_a_last_move_preserves_disable_family_canonical_failure():
    case = _case(actor_history=None, actor_known=("tackle",))
    app = case["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "canonical_failure"
    assert app["reason"] == "disable_target_last_executed_move_missing"


def test_partial_a_known_moves_without_last_move_fail_closed():
    case = _case(actor_history="thunderbolt", actor_known=("tackle",))
    app = case["application"]
    assert app["status"] == "incomplete"
    assert app["reason"] == "disable_current_known_moves_incomplete"


def test_complete_a_moveset_proving_last_move_absent_is_canonical_failure():
    case = _case(actor_history="thunderbolt", actor_known=("tackle", "water-gun", "protect", "rest"))
    app = case["application"]
    assert app["status"] == "resolved"
    assert app["outcome"] == "canonical_failure"
    assert app["reason"] == "disable_target_no_longer_knows_last_move"
    assert app["disabled_move_id"] == "thunderbolt"


def test_missing_and_foreign_current_disable_authority_fail_closed():
    missing = _case(actor_disable="missing")["application"]
    assert missing["status"] == "incomplete"
    assert missing["reason"] == "current_disable_authority_missing"

    foreign = _case(actor_disable="foreign_inactive")["application"]
    assert foreign["status"] == "incomplete"
    assert foreign["reason"] == "current_disable_authority_missing"


def test_unauthenticated_a_known_moves_fail_closed_without_species_inference():
    case = _case(actor_known=("thunderbolt",), actor_known_authenticated=False)
    authority = freeze_runtime_d0_status_special_current_known_moves_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        owner=case["actor"],
    )
    assert authority["status"] == "incomplete"
    assert case["application"]["status"] == "incomplete"
    assert case["application"]["reason"] == "disable_current_known_moves_authority_missing"


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
        lambda route, case: route.__setitem__("move_id", "encore"),
    ],
)
def test_tampered_reflected_disable_route_rejects(mutator):
    case = _case()
    forged = deepcopy(case["route"])
    mutator(forged, case)
    assert validate_detached_reflected_status_routing_authority(forged)["status"] == "rejected"
    result = materialize_detached_reflected_disable_application(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        action=case["action"],
        routing_authority=forged,
    )
    assert result["status"] == "rejected"


def test_stale_runtime_rejects_reflected_disable_route_at_consumption():
    case = _case()
    stale = deepcopy(case["snapshot"])
    stale["state_fingerprint"] = "stale-runtime"
    result = materialize_detached_reflected_disable_application(
        strategy_d0=case["d0"],
        runtime_snapshot=stale,
        action=case["action"],
        routing_authority=case["route"],
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "reflected_disable_current_binding_invalid"


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


def test_legacy_disable_reflected_detector_remains_fail_closed():
    case = _case()
    assert case["produced"]["status"] == "incomplete"
    assert case["produced"]["reason"] == "disable_reflection_execution_unsupported"
    assert case["produced"]["reflection_authority"] == case["detection"]
