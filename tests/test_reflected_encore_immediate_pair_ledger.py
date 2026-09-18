from copy import deepcopy

import pytest

from llm.advisor_detached_encore_action_restriction import (
    materialize_detached_reflected_encore_application,
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
from tests.test_reflected_encore_detached_application import (
    ENCORE_META,
    _encore_row,
    _history,
    _known_move,
    _metadata,
    _pp,
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
        "opponent_actor": deepcopy(owner),
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


def _case(*, encore_side="self", order="own_first"):
    state = _state()
    own, foe = _owner(state, "self"), _owner(state, "opponent")
    selected_side = encore_side
    reflector_side = "opponent" if encore_side == "self" else "self"
    state[f"{selected_side}_side"]["pokemon"][0]["current_ability"] = "pressure"
    state[f"{reflector_side}_side"]["pokemon"][0]["current_ability"] = "magic-bounce"
    state["last_applied_observation_sequence"] = 10

    _history(state, selected_side, "quick-attack", f"{selected_side}-used")
    _history(state, reflector_side, "tail-whip", f"{reflector_side}-used")
    _known_move(state, selected_side, "quick-attack")
    _known_move(state, reflector_side, "tail-whip")
    _pp(state, selected_side, "quick-attack", usable=True)
    _pp(state, reflector_side, "tail-whip", usable=True)

    state["current_encore_restrictions"] = {
        selected_side: _encore_row(
            state,
            selected_side,
            active=False,
            locked_move="quick-attack",
            execution_id=f"{selected_side}-used",
        ),
        reflector_side: _encore_row(
            state,
            reflector_side,
            active=False,
            locked_move="tail-whip",
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

    if encore_side == "self":
        own_action = _own_action("encore", ENCORE_META, own, bindings)
        opponent_action = _opponent_action("tail-whip", TAIL_META, foe, own, bindings)
        special_action, special_actor, special_target = own_action, own, foe
        pending_action, pending_actor, pending_target = opponent_action, foe, own
    else:
        own_action = _own_action("tail-whip", TAIL_META, own, bindings)
        opponent_action = _opponent_action("encore", ENCORE_META, foe, own, bindings)
        special_action, special_actor, special_target = opponent_action, foe, own
        pending_action, pending_actor, pending_target = own_action, own, foe

    catalog = {
        "quick-attack": _metadata("quick-attack", priority=1),
        "tail-whip": _metadata("tail-whip", priority=0, category="status"),
    }
    produced = freeze_runtime_d0_status_special_application_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=special_action,
        actor=special_actor,
        target=special_target,
        target_selected_action=pending_action,
        canonical_move_metadata_authorities=catalog,
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
    application = materialize_detached_reflected_encore_application(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=special_action,
        routing_authority=route,
        canonical_move_metadata_authorities=catalog,
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
        "catalog": catalog,
        "route": route,
        "application": application,
        "pure": {pending_action["action_id"]: pure},
        "order": order_authority,
    }


def _pair(case, *, application=None, catalog=None):
    app = case["application"] if application is None else application
    metadata = case["catalog"] if catalog is None else catalog
    return materialize_immediate_move_vs_move_action_pair(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        own_action=case["own_action"],
        opponent_action=case["opponent_action"],
        action_order_authority=case["order"],
        pure_status_execution_authorities=case["pure"],
        encore_application_authorities={case["special_action"]["action_id"]: app},
        canonical_move_metadata_authorities=metadata,
    )


def _reflected_leaf(branch):
    first = branch["first_action_leaf"]
    second = branch["second_action"].get("leaf")
    if first.get("consequences", {}).get("reflected_status_routing_authority") is not None:
        return first
    assert isinstance(second, dict)
    return second


@pytest.mark.parametrize(
    ("encore_side", "order"),
    [
        ("self", "own_first"),
        ("self", "opponent_first"),
        ("opponent", "opponent_first"),
        ("opponent", "own_first"),
    ],
)
def test_reflected_encore_first_second_are_side_neutral_without_forced_execution(encore_side, order):
    case = _case(encore_side=encore_side, order=order)
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
    assert leaf["consequences"]["encore_application"] == app
    assert leaf["consequences"]["reflected_status_routing_authority"] == case["route"]
    assert leaf["consequences"]["canonical_move_metadata_authorities"] == case["catalog"]
    assert leaf["consequences"]["locked_move_id"] == "quick-attack"
    assert leaf["consequences"]["locked_move_metadata"] == case["catalog"]["quick-attack"]["metadata"]
    assert leaf["consequences"]["last_used_execution_id"] == f"{encore_side}-used"
    assert leaf["consequences"]["remaining_target_turns"] == 3
    assert leaf["consequences"]["damage"] == 0
    assert leaf["consequences"]["contact"] == "not_applicable"
    assert leaf["hit_state"] == leaf["critical_state"] == leaf["damage_roll"] == "not_applicable"

    special_first = (order == "own_first") == (case["special_actor"] == case["own"])
    pending_leaf = branch["second_action"]["leaf"] if special_first else branch["first_action_leaf"]
    assert pending_leaf["candidate_id"] == case["pending_action"]["action_id"]
    assert pending_leaf["provenance"]["attacker"] == case["pending_actor"]
    assert branch["second_action"].get("forced_execution_action") is None
    assert "encore_forced_execution" not in pending_leaf.get("consequences", {})
    assert "encore_forced_execution" not in pending_leaf.get("provenance", {})
    assert "encore_forced_execution" not in leaf.get("consequences", {})
    assert "encore_forced_execution" not in leaf.get("provenance", {})
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
    assert (case["snapshot"], case["d0"]) == before


@pytest.mark.parametrize("encore_side", ["self", "opponent"])
def test_equal_speed_reflected_encore_preserves_halves_and_root_mass(encore_side):
    case = _case(encore_side=encore_side, order="unresolved_tie")
    pair = _pair(case)
    assert pair["status"] == "evaluable"
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    branches = {row["action_order"]: row for row in pair["terminal_branches"]}
    assert set(branches) == {"own_first", "opponent_first"}
    assert branches["own_first"]["probability"] == {"numerator": 1, "denominator": 2}
    assert branches["opponent_first"]["probability"] == {"numerator": 1, "denominator": 2}
    assert all(branch["second_action"].get("forced_execution_action") is None for branch in branches.values())
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_reflected_encore_leaf_preserves_selected_hp_orientation():
    case = _case(encore_side="self", order="own_first")
    leaf = _pair(case)["terminal_branches"][0]["first_action_leaf"]
    active = case["d0"]["strategy_state"]["active"]
    assert leaf["consequences"]["own_final_hp"] == active["self"]["current_hp"]
    assert leaf["consequences"]["target_final_hp"] == active["opponent"]["current_hp"]
    assert leaf["consequences"]["self_fainted"] is False
    assert leaf["consequences"]["target_ko"] is False


def test_reflected_encore_requires_explicit_canonical_metadata_authorities():
    case = _case()
    result = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        own_action=case["own_action"],
        opponent_action=case["opponent_action"],
        action_order_authority=case["order"],
        pure_status_execution_authorities=case["pure"],
        encore_application_authorities={case["special_action"]["action_id"]: case["application"]},
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "reflected_encore_canonical_move_metadata_authorities_missing"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda app, case: app["reflected_status_routing_authority"].__setitem__("reflected_target", case["special_target"]),
        lambda app, case: app.__setitem__("target", case["special_target"]),
        lambda app, case: app.__setitem__("actor", case["special_actor"]),
        lambda app, case: app.__setitem__("action_id", "forged-action"),
        lambda app, case: app.__setitem__("move_id", "disable"),
        lambda app, case: app.__setitem__("locked_move_id", "tackle"),
        lambda app, case: app.__setitem__("last_used_execution_id", "forged-used"),
        lambda app, case: app.__setitem__("remaining_target_turns", 2),
    ],
)
def test_pair_rejects_tampered_reflected_encore_application(mutator):
    case = _case()
    forged = deepcopy(case["application"])
    mutator(forged, case)
    assert _pair(case, application=forged)["status"] == "rejected"


def test_pair_rejects_reflected_encore_downgraded_to_ordinary_shape():
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
        lambda leaf, case: leaf["consequences"]["encore_application"].__setitem__("target", case["special_target"]),
        lambda leaf, case: leaf["consequences"]["reflected_status_routing_authority"].__setitem__("reflected_target", case["special_target"]),
        lambda leaf, case: leaf.__setitem__("candidate_id", "forged-action"),
        lambda leaf, case: leaf["provenance"].__setitem__("move_id", "disable"),
        lambda leaf, case: leaf["consequences"].__setitem__("locked_move_id", "tackle"),
        lambda leaf, case: leaf["consequences"].__setitem__("locked_move_metadata", {"move_id": "tackle", "priority": 0}),
        lambda leaf, case: leaf["consequences"].__setitem__("last_used_execution_id", "forged-used"),
        lambda leaf, case: leaf["consequences"].__setitem__("remaining_target_turns", 2),
    ],
)
def test_ledger_rejects_forged_reflected_encore_identity_or_family_fields(mutator):
    case = _case()
    forged = deepcopy(_pair(case))
    leaf = forged["terminal_branches"][0]["first_action_leaf"]
    mutator(leaf, case)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_canonical_metadata_authority_tamper():
    case = _case()
    forged = deepcopy(_pair(case))
    leaf = forged["terminal_branches"][0]["first_action_leaf"]
    forged_catalog = deepcopy(case["catalog"])
    forged_catalog["quick-attack"]["metadata"]["priority"] = 0
    leaf["consequences"]["canonical_move_metadata_authorities"] = deepcopy(forged_catalog)
    leaf["provenance"]["canonical_move_metadata_authorities"] = deepcopy(forged_catalog)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_stripped_route_markers_from_reflected_encore_leaf():
    case = _case()
    forged = deepcopy(_pair(case))
    leaf = forged["terminal_branches"][0]["first_action_leaf"]
    leaf["consequences"].pop("reflected_status_routing_authority")
    leaf["provenance"].pop("reflected_status_routing_authority")
    assert leaf["consequences"]["encore_application"]["execution_mode"] == "reflected_original_action"
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_forced_execution_on_reflector():
    case = _case(encore_side="self", order="own_first")
    forged = deepcopy(_pair(case))
    forged["terminal_branches"][0]["second_action"]["forced_execution_action"] = {
        "status": "resolved",
        "replacement_reason": "encore",
    }
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_pending_leaf_encore_forced_execution_marker():
    case = _case(encore_side="self", order="own_first")
    forged = deepcopy(_pair(case))
    pending = forged["terminal_branches"][0]["second_action"]["leaf"]
    pending["consequences"]["encore_forced_execution"] = {"forged": True}
    pending["provenance"]["encore_forced_execution"] = {"forged": True}
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_self_retroactive_forced_execution_when_encore_resolves_second():
    case = _case(encore_side="self", order="opponent_first")
    forged = deepcopy(_pair(case))
    branch = forged["terminal_branches"][0]
    assert branch["second_action"]["leaf"]["candidate_id"] == case["special_action"]["action_id"]
    branch["second_action"]["forced_execution_action"] = {
        "status": "resolved",
        "replacement_reason": "encore",
    }
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_live_opponent_encore_bundle_forwards_same_canonical_metadata_catalog(monkeypatch):
    import llm.advisor_ui_detached_strategy_bridge as bridge_subject

    self_owner = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "self"}
    opponent_owner = {"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "opponent"}
    d0 = {
        "session_id": "s",
        "source_runtime_fingerprint": "runtime",
        "strategy_preview_fingerprint": "preview",
        "decision_owner": self_owner,
        "active_owners": {"self": self_owner, "opponent": opponent_owner},
    }
    selection = {
        "actions": (
            {"action_id": "attack:tail-whip", "action_type": "attack", "identity": "tail-whip", "selection": "selectable"},
        )
    }
    response = {
        "action_id": "opponent_attack:encore",
        "response_kind": "move",
        "action_type": "attack",
        "move_id": "encore",
        "metadata_authority": {"metadata": deepcopy(ENCORE_META)},
    }
    catalog = {
        "quick-attack": _metadata("quick-attack", priority=1),
        "encore": {"status": "resolved", "metadata": deepcopy(ENCORE_META)},
    }
    captured = []
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_opponent_known_move_action_authority", lambda **_: {"status": "resolved"})
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_complete_opponent_response_set_authority", lambda **_: {"status": "resolved"})
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_opponent_switch_response_authority", lambda **_: {"status": "resolved"})
    monkeypatch.setattr(
        bridge_subject,
        "freeze_runtime_d0_combined_opponent_response_universe_authority",
        lambda **_: {
            "status": "resolved",
            "selectable_response_action_ids": (response["action_id"],),
            "actions": (response,),
        },
    )
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_action_order_authority", lambda **_: {"status": "resolved"})
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_quick_claw_action_order_authority", lambda **_: {"status": "resolved"})
    monkeypatch.setattr(
        bridge_subject,
        "resolve_runtime_d0_selectable_move_metadata_authority",
        lambda **_: {"metadata": deepcopy(TAIL_META)},
    )
    monkeypatch.setattr(bridge_subject, "freeze_runtime_d0_focus_sash_survival_authority", lambda **_: {"status": "resolved"})
    monkeypatch.setattr(
        bridge_subject,
        "freeze_runtime_d0_status_special_application_authority",
        lambda **_: {"status": "incomplete", "reason": "encore_reflection_execution_unsupported"},
    )
    monkeypatch.setattr(
        bridge_subject,
        "materialize_detached_opponent_response_profile",
        lambda **kwargs: captured.append(kwargs["response_authority_bundles"]) or {"status": "evaluable"},
    )

    projected = bridge_subject._project_live_opponent_response_profiles(
        strategy_d0=d0,
        runtime_snapshot={},
        selection=selection,
        canonical_move_metadata_authorities=catalog,
    )
    assert projected["attack:tail-whip"]["status"] == "evaluable"
    payload = captured[0]["opponent_attack:encore"]["ordinary_pair_authorities"]
    assert set(payload) == {"encore_application_authorities", "canonical_move_metadata_authorities"}
    assert payload["canonical_move_metadata_authorities"] == catalog


def test_reflected_encore_damaging_pending_path_fails_closed_without_broadening():
    case = _case(encore_side="self", order="own_first")
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
        encore_application_authorities={case["special_action"]["action_id"]: case["application"]},
        canonical_move_metadata_authorities=case["catalog"],
    )
    assert result["status"] == "unsupported"
    assert result["reason"] == "reflected_encore_pair_requires_zero_hp_pending_status"
