from copy import deepcopy

import pytest

from llm.advisor_detached_disable_action_restriction import (
    materialize_detached_reflected_disable_application,
)
from llm.advisor_detached_reflected_status_routing_authority import (
    freeze_detached_reflected_status_routing_authority,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_immediate_move_vs_move_action_pair import (
    materialize_immediate_move_vs_move_action_pair,
)
from llm.advisor_runtime_d0_pure_status_action_execution_authority import (
    freeze_runtime_d0_pure_status_action_execution_authority,
)
from llm.advisor_runtime_d0_status_special_application_authority import (
    freeze_runtime_d0_status_special_application_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _owner, _state
from tests.test_reflected_disable_detached_application import (
    DISABLE_META,
    _disable_row,
    _set_history,
    _set_known_moves,
    _snapshot,
)


TAIL_META = {
    "move_id": "tail-whip",
    "category": "status",
    "type": "normal",
    "target": "selected-pokemon",
    "accuracy": 100,
    "power": None,
    "priority": 0,
}


def _own_action(move_id, metadata, owner, bindings):
    action_id = f"attack:{move_id}"
    return {
        "action_id": action_id,
        "action_type": "attack",
        "identity": move_id,
        **bindings,
        "move_metadata_authority": {
            "status": "resolved",
            "candidate_id": action_id,
            "move_id": move_id,
            "active_attacker": deepcopy(owner),
            **bindings,
            "metadata": deepcopy(metadata),
        },
    }


def _opponent_action(move_id, metadata, actor, target, bindings):
    action_id = f"opponent_attack:{move_id}"
    return {
        "status": "resolved",
        "action_id": action_id,
        "action_type": "attack",
        "move_id": move_id,
        "identity": move_id,
        "opponent_actor": deepcopy(actor),
        "target_owner": deepcopy(target),
        **bindings,
        "metadata_authority": {
            "status": "resolved",
            "move_id": move_id,
            "metadata": deepcopy(metadata),
        },
        "usability": {"status": "known_usable"},
        "selectability": "selectable",
    }


def _case(*, disable_side="self", order="own_first"):
    state = _state()
    own, foe = _owner(state, "self"), _owner(state, "opponent")
    selected_side = disable_side
    reflector_side = "opponent" if disable_side == "self" else "self"
    state[f"{selected_side}_side"]["pokemon"][0]["current_ability"] = "pressure"
    state[f"{reflector_side}_side"]["pokemon"][0]["current_ability"] = "magic-bounce"

    _set_history(state, selected_side, "thunderbolt", f"{selected_side}-used")
    _set_history(state, reflector_side, "tail-whip", f"{reflector_side}-used")
    _set_known_moves(state, selected_side, ("thunderbolt",))
    _set_known_moves(state, reflector_side, ("tail-whip",))
    state["current_disable_restrictions"] = {
        selected_side: _disable_row(
            state,
            selected_side,
            active=False,
            disabled_move="thunderbolt",
            execution_id=f"{selected_side}-used",
        ),
        reflector_side: _disable_row(
            state,
            reflector_side,
            active=False,
            disabled_move="tail-whip",
            execution_id=f"{reflector_side}-used",
        ),
    }

    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=own)
    assert d0["status"] == "resolved"
    bindings = {
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": d0["decision_owner"],
    }

    if disable_side == "self":
        own_action = _own_action("disable", DISABLE_META, own, bindings)
        opponent_action = _opponent_action("tail-whip", TAIL_META, foe, own, bindings)
        special_action, special_actor, special_target = own_action, own, foe
        pending_action, pending_actor, pending_target = opponent_action, foe, own
    else:
        own_action = _own_action("tail-whip", TAIL_META, own, bindings)
        opponent_action = _opponent_action("disable", DISABLE_META, foe, own, bindings)
        special_action, special_actor, special_target = opponent_action, foe, own
        pending_action, pending_actor, pending_target = own_action, own, foe

    produced = freeze_runtime_d0_status_special_application_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=special_action,
        actor=special_actor,
        target=special_target,
        target_selected_action=pending_action,
        canonical_move_metadata_authorities={},
    )
    detection = produced["reflection_authority"]
    route = freeze_detached_reflected_status_routing_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=special_action,
        original_actor=special_actor,
        original_target=special_target,
        reflection_detection_authority=detection,
    )
    application = materialize_detached_reflected_disable_application(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=special_action,
        routing_authority=route,
    )
    assert application["status"] == "resolved"
    assert application["outcome"] == "applicable"

    accuracy = {
        "status": "resolved",
        **bindings,
        "actor": deepcopy(pending_actor),
        "target": deepcopy(pending_target),
        "action_id": pending_action["action_id"],
        "move_id": "tail-whip",
        "outcome": "hit",
    }
    pure = freeze_runtime_d0_pure_status_action_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=pending_action,
        actor=pending_actor,
        target=pending_target,
        status_accuracy_authority=accuracy,
    )
    order_authority = {
        "status": "resolved",
        "schema_version": "runtime-d0-action-order-authority-v1",
        "order": order,
        **bindings,
        "own_action_id": own_action["action_id"],
        "opponent_action_id": opponent_action["action_id"],
        "own_actor": deepcopy(own),
        "opponent_actor": deepcopy(foe),
    }
    if order == "unresolved_tie":
        order_authority["order_engine"] = {"status": "speed_tie"}

    return {
        "snapshot": snapshot,
        "d0": d0,
        "own": own,
        "foe": foe,
        "own_action": own_action,
        "opponent_action": opponent_action,
        "special_action": special_action,
        "special_actor": special_actor,
        "special_target": special_target,
        "pending_action": pending_action,
        "pending_actor": pending_actor,
        "pending_target": pending_target,
        "route": route,
        "application": application,
        "pure": {pending_action["action_id"]: pure},
        "order": order_authority,
    }


def _pair(case, *, application=None):
    app = case["application"] if application is None else application
    return materialize_immediate_move_vs_move_action_pair(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        own_action=case["own_action"],
        opponent_action=case["opponent_action"],
        action_order_authority=case["order"],
        pure_status_execution_authorities=case["pure"],
        disable_application_authorities={case["special_action"]["action_id"]: app},
    )


def _reflected_leaf(branch):
    first = branch["first_action_leaf"]
    second = branch["second_action"].get("leaf")
    if first.get("consequences", {}).get("reflected_status_routing_authority") is not None:
        return first
    assert isinstance(second, dict)
    return second


@pytest.mark.parametrize(
    ("disable_side", "order"),
    [
        ("self", "own_first"),
        ("self", "opponent_first"),
        ("opponent", "opponent_first"),
        ("opponent", "own_first"),
    ],
)
def test_reflected_disable_first_second_are_side_neutral_and_do_not_gate_reflector(disable_side, order):
    case = _case(disable_side=disable_side, order=order)
    before = deepcopy((case["snapshot"], case["d0"]))
    pair = _pair(case)
    assert pair["status"] == "evaluable"
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    branch = pair["terminal_branches"][0]
    leaf = _reflected_leaf(branch)
    app = case["application"]

    assert leaf["candidate_id"] == case["special_action"]["action_id"]
    assert leaf["provenance"]["attacker"] == case["special_actor"]
    assert leaf["provenance"]["target"] == case["special_target"]
    assert leaf["provenance"]["selected_actor"] == case["special_actor"]
    assert leaf["provenance"]["selected_target"] == case["special_target"]
    assert leaf["provenance"]["effective_source"] == case["special_target"]
    assert leaf["provenance"]["effective_target"] == case["special_actor"]
    assert leaf["consequences"]["disable_application"] == app
    assert leaf["consequences"]["reflected_status_routing_authority"] == case["route"]
    assert leaf["consequences"]["disabled_move_id"] == "thunderbolt"
    assert leaf["consequences"]["last_used_execution_id"] == f"{disable_side}-used"
    assert leaf["consequences"]["remaining_target_turns"] == 4
    assert leaf["consequences"]["damage"] == 0
    assert leaf["consequences"]["contact"] == "not_applicable"
    assert leaf["hit_state"] == leaf["critical_state"] == leaf["damage_roll"] == "not_applicable"

    special_first = (order == "own_first") == (case["special_actor"] == case["own"])
    pending_leaf = branch["second_action"]["leaf"] if special_first else branch["first_action_leaf"]
    assert pending_leaf["candidate_id"] == case["pending_action"]["action_id"]
    assert pending_leaf["provenance"]["attacker"] == case["pending_actor"]
    assert pending_leaf.get("consequences", {}).get("execution_failure") != "disable_action_restriction"
    assert "disable_execution_gate" not in pending_leaf.get("consequences", {})
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
    assert (case["snapshot"], case["d0"]) == before


@pytest.mark.parametrize("disable_side", ["self", "opponent"])
def test_equal_speed_reflected_disable_preserves_two_halves_and_root_mass(disable_side):
    case = _case(disable_side=disable_side, order="unresolved_tie")
    pair = _pair(case)
    assert pair["status"] == "evaluable"
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    branches = {row["action_order"]: row for row in pair["terminal_branches"]}
    assert set(branches) == {"own_first", "opponent_first"}
    assert branches["own_first"]["probability"] == {"numerator": 1, "denominator": 2}
    assert branches["opponent_first"]["probability"] == {"numerator": 1, "denominator": 2}
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_reflected_disable_leaf_preserves_selected_hp_orientation():
    case = _case(disable_side="self", order="own_first")
    leaf = _pair(case)["terminal_branches"][0]["first_action_leaf"]
    active = case["d0"]["strategy_state"]["active"]
    assert leaf["consequences"]["own_final_hp"] == active["self"]["current_hp"]
    assert leaf["consequences"]["target_final_hp"] == active["opponent"]["current_hp"]
    assert leaf["consequences"]["self_fainted"] is False
    assert leaf["consequences"]["target_ko"] is False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda app, case: app["reflected_status_routing_authority"].__setitem__("reflected_target", case["special_target"]),
        lambda app, case: app.__setitem__("target", case["special_target"]),
        lambda app, case: app.__setitem__("actor", case["special_actor"]),
        lambda app, case: app.__setitem__("action_id", "forged-action"),
        lambda app, case: app.__setitem__("move_id", "encore"),
    ],
)
def test_pair_rejects_tampered_reflected_disable_application(mutator):
    case = _case()
    forged = deepcopy(case["application"])
    mutator(forged, case)
    assert _pair(case, application=forged)["status"] == "rejected"


def test_pair_rejects_reflected_disable_downgraded_to_ordinary_shape():
    case = _case()
    forged = deepcopy(case["application"])
    forged.pop("execution_mode")
    forged["actor"] = case["special_actor"]
    forged["target"] = case["special_target"]
    assert _pair(case, application=forged)["status"] == "rejected"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda leaf, case: leaf["provenance"].__setitem__("selected_actor", case["special_target"]),
        lambda leaf, case: leaf["provenance"].__setitem__("selected_target", case["special_actor"]),
        lambda leaf, case: leaf["provenance"].__setitem__("effective_source", case["special_actor"]),
        lambda leaf, case: leaf["provenance"].__setitem__("effective_target", case["special_target"]),
        lambda leaf, case: leaf["consequences"]["disable_application"].__setitem__("target", case["special_target"]),
        lambda leaf, case: leaf["consequences"]["reflected_status_routing_authority"].__setitem__("reflected_target", case["special_target"]),
        lambda leaf, case: leaf.__setitem__("candidate_id", "forged-action"),
        lambda leaf, case: leaf["provenance"].__setitem__("move_id", "encore"),
        lambda leaf, case: leaf["consequences"].__setitem__("disabled_move_id", "tackle"),
        lambda leaf, case: leaf["consequences"].__setitem__("last_used_execution_id", "forged-used"),
        lambda leaf, case: leaf["consequences"].__setitem__("remaining_target_turns", 3),
    ],
)
def test_ledger_rejects_forged_reflected_disable_identity_or_family_consequence(mutator):
    case = _case()
    forged = deepcopy(_pair(case))
    leaf = forged["terminal_branches"][0]["first_action_leaf"]
    mutator(leaf, case)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_stripped_route_markers_from_reflected_disable_leaf():
    case = _case(disable_side="self", order="own_first")
    forged = deepcopy(_pair(case))
    leaf = forged["terminal_branches"][0]["first_action_leaf"]
    leaf["consequences"].pop("reflected_status_routing_authority")
    leaf["provenance"].pop("reflected_status_routing_authority")
    assert leaf["consequences"]["disable_application"]["execution_mode"] == "reflected_original_action"
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_false_disable_cancellation_on_reflector():
    case = _case(disable_side="self", order="own_first")
    forged = deepcopy(_pair(case))
    pending = forged["terminal_branches"][0]["second_action"]["leaf"]
    pending["consequences"]["execution_failure"] = "disable_action_restriction"
    pending["consequences"]["disable_execution_gate"] = {"execution_state": "restricted_by_disable"}
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ordinary_faster_disable_still_restricts_matching_pending_move():
    case = _case(disable_side="self", order="own_first")
    app = {
        "status": "resolved",
        "session_id": case["d0"]["session_id"],
        "source_runtime_fingerprint": case["d0"]["source_runtime_fingerprint"],
        "source_branch_fingerprint": case["d0"]["strategy_preview_fingerprint"],
        "decision_owner": case["d0"]["decision_owner"],
        "actor": case["special_actor"],
        "target": case["special_target"],
        "action_id": case["special_action"]["action_id"],
        "move_id": "disable",
        "outcome": "applicable",
        "disabled_move_id": "tail-whip",
        "last_used_execution_id": "opponent-used",
        "remaining_target_turns": 4,
    }
    pair = _pair(case, application=app)
    assert pair["status"] == "evaluable"
    second = pair["terminal_branches"][0]["second_action"]["leaf"]
    assert second["consequences"]["execution_failure"] == "disable_action_restriction"
    assert second["consequences"]["disable_execution_gate"]["execution_state"] == "restricted_by_disable"


def test_ordinary_slower_disable_does_not_retroactively_restrict_completed_action():
    case = _case(disable_side="self", order="opponent_first")
    app = {
        "status": "resolved",
        "session_id": case["d0"]["session_id"],
        "source_runtime_fingerprint": case["d0"]["source_runtime_fingerprint"],
        "source_branch_fingerprint": case["d0"]["strategy_preview_fingerprint"],
        "decision_owner": case["d0"]["decision_owner"],
        "actor": case["special_actor"],
        "target": case["special_target"],
        "action_id": case["special_action"]["action_id"],
        "move_id": "disable",
        "outcome": "applicable",
        "disabled_move_id": "tail-whip",
        "last_used_execution_id": "opponent-used",
        "remaining_target_turns": 4,
    }
    pair = _pair(case, application=app)
    assert pair["status"] == "evaluable"
    first = pair["terminal_branches"][0]["first_action_leaf"]
    assert first["candidate_id"] == case["pending_action"]["action_id"]
    assert first.get("consequences", {}).get("execution_failure") != "disable_action_restriction"


def test_reflected_disable_damaging_pending_path_fails_closed_without_broadening():
    case = _case(disable_side="self", order="own_first")
    damaging = deepcopy(case["opponent_action"])
    damaging["action_id"] = "opponent_attack:tackle"
    damaging["move_id"] = damaging["identity"] = "tackle"
    damaging["metadata_authority"]["move_id"] = "tackle"
    damaging["metadata_authority"]["metadata"] = {
        "move_id": "tackle",
        "category": "physical",
        "type": "normal",
        "target": "selected-pokemon",
        "accuracy": 100,
        "power": 40,
        "priority": 0,
    }
    order = deepcopy(case["order"])
    order["opponent_action_id"] = damaging["action_id"]
    result = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        own_action=case["own_action"],
        opponent_action=damaging,
        action_order_authority=order,
        disable_application_authorities={case["special_action"]["action_id"]: case["application"]},
    )
    assert result["status"] == "unsupported"
    assert result["reason"] == "reflected_disable_pair_requires_zero_hp_pending_status"
