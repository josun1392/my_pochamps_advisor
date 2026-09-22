from __future__ import annotations

from copy import deepcopy

from llm.advisor_detached_predictive_intermediate_state import (
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_immediate_move_vs_move_action_pair import (
    materialize_immediate_move_vs_move_action_pair,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_substitute import update_substitute_state_context
from tests.test_detached_opponent_response_profile import (
    _complete_state,
    _equal_speed_order,
    _inputs,
    _metadata,
    _owner,
    _snapshot,
    _state,
)


STANDARD = ("sky-attack", "razor-wind", "freeze-shock", "ice-burn", "solar-beam", "solar-blade", "meteor-beam", "skull-bash", "fly", "dig", "dive", "bounce")


def _charge_metadata(move_id: str) -> dict:
    category = "special" if move_id in {"razor-wind", "ice-burn", "solar-beam", "meteor-beam"} else "physical"
    power = {
        "sky-attack": 140,
        "razor-wind": 80,
        "freeze-shock": 140,
        "ice-burn": 140,
        "solar-beam": 120,
        "solar-blade": 125,
        "meteor-beam": 120,
        "skull-bash": 130,
        "fly": 90,
        "dig": 80,
        "dive": 80,
        "bounce": 85,
    }[move_id]
    move_type = {
        "sky-attack": "flying",
        "razor-wind": "normal",
        "freeze-shock": "ice",
        "ice-burn": "ice",
        "solar-beam": "grass",
        "solar-blade": "grass",
        "meteor-beam": "rock",
        "skull-bash": "normal",
        "fly": "flying",
        "dig": "ground",
        "dive": "water",
        "bounce": "flying",
    }[move_id]
    return {
        "move_id": move_id,
        "category": category,
        "power": power,
        "type": move_type,
        "accuracy": 95 if move_id == "fly" else 85 if move_id == "bounce" else 100 if move_id in {"solar-beam", "solar-blade", "razor-wind", "skull-bash", "dig", "dive"} else 90,
        "priority": 0,
        "target": "selected-pokemon",
    }


def _own_action(d0, actor, move_id: str, metadata: dict | None = None) -> dict:
    metadata = deepcopy(metadata or (_charge_metadata(move_id) if move_id in STANDARD else _metadata(move_id)["metadata"]))
    authority = {
        "status": "resolved",
        "candidate_id": f"attack:{move_id}",
        "active_attacker": deepcopy(actor),
        "move_id": move_id,
        "metadata": metadata,
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
    }
    return {
        "action_id": f"attack:{move_id}",
        "action_type": "attack",
        "identity": move_id,
        "move_metadata_authority": authority,
    }


def _opponent_action(d0, move_id: str, metadata: dict | None = None) -> dict:
    actor = d0["active_owners"]["opponent"]
    target = d0["active_owners"]["self"]
    metadata = deepcopy(metadata or (_charge_metadata(move_id) if move_id in STANDARD else _metadata(move_id)["metadata"]))
    return {
        "status": "resolved",
        "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": f"opponent_attack:{move_id}",
        "action_type": "attack",
        "move_id": move_id,
        "selectability": "selectable",
        "usability": {"status": "known_usable"},
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "opponent_actor": deepcopy(actor),
        "target_owner": deepcopy(target),
        "metadata_authority": {
            "status": "resolved",
            "move_id": move_id,
            "metadata": metadata,
        },
    }


def _order(d0, own_action, opponent_action, order: str) -> dict:
    if order == "tie":
        return _equal_speed_order(d0, own_action, opponent_action)
    return {
        "status": "resolved",
        "schema_version": "runtime-d0-action-order-authority-v1",
        "order": order,
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "own_action_id": own_action["action_id"],
        "opponent_action_id": opponent_action["action_id"],
        "own_actor": deepcopy(d0["active_owners"]["self"]),
        "opponent_actor": deepcopy(d0["active_owners"]["opponent"]),
        "order_engine": {
            "status": "speed_tie" if order == "tie" else order,
        },
    }


def _with_terminal_mechanics_facts(state):
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["stat_stages"].update(accuracy=0, evasion=0)
        pokemon["condition_provenance"] = {
            "event_kind": "current_condition_observed",
            "trust": "user_confirmed_observation",
            "condition": "none",
            "turn_number": 1,
        }
        state[f"{side}_side"]["side_conditions"] = []
        state[f"{side}_side"]["side_conditions_provenance"] = {
            "event_kind": "current_side_conditions_observed",
            "trust": "user_confirmed_observation",
        }
        pokemon["current_confusion"] = "none"
        pokemon["confusion_provenance"] = {
            "event_kind": "current_confusion_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "state": "none",
        }
        owner = _owner(state, side)
        state["substitute_state_context"] = update_substitute_state_context(
            context=state.get("substitute_state_context"),
            session_id=state["session_id"],
            owner=owner,
            state="known_inactive",
            substitute_hp=None,
            provenance="runtime_observed_substitute_state_v1",
        )
    state["field"]["terrain"] = "none"
    state["field"]["terrain_provenance"] = {
        "event_kind": "current_terrain_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    return state


def _case(
    *,
    own_move: str,
    opponent_move: str,
    order: str = "own_first",
    own_hp: int = 100,
    opponent_hp: int = 100,
):
    state = _complete_state(_state())
    state["self_side"]["pokemon"][0]["current_hp"] = own_hp
    state["self_side"]["pokemon"][0]["max_hp"] = 100
    state["self_side"]["pokemon"][0]["fainted"] = own_hp == 0
    state["opponent_side"]["pokemon"][0]["current_hp"] = opponent_hp
    state["opponent_side"]["pokemon"][0]["max_hp"] = 100
    state["opponent_side"]["pokemon"][0]["fainted"] = opponent_hp == 0
    if order == "tie":
        state["opponent_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = 100
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    own = _own_action(d0, d0["active_owners"]["self"], own_move)
    opponent = _opponent_action(d0, opponent_move)
    frozen_order = _order(d0, own, opponent, order)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=frozen_order,
    )
    return state, snapshot, d0, own, opponent, frozen_order, pair


def _charge_leaf(branch: dict, *, first: bool) -> dict | None:
    leaf = branch["first_action_leaf"] if first else branch["second_action"].get("leaf")
    if not isinstance(leaf, dict):
        return None
    context = leaf.get("consequences", {}).get("detached_standard_charge_lifecycle_context")
    return leaf if isinstance(context, dict) else None


def test_own_charge_first_then_ordinary_attack_executes_and_ledger_is_exact():
    _state0, snapshot, d0, _own, _opp, _order0, pair = _case(
        own_move="sky-attack", opponent_move="tackle", order="own_first",
    )
    assert pair["status"] == "evaluable", pair
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert pair["terminal_branches"]
    for branch in pair["terminal_branches"]:
        leaf = _charge_leaf(branch, first=True)
        assert leaf is not None
        assert leaf["hit_state"] == leaf["critical_state"] == leaf["damage_roll"] == "not_applicable"
        assert leaf["consequences"]["damage"] == 0
        assert leaf["consequences"]["own_final_hp"] == 100
        assert leaf["consequences"]["target_final_hp"] == 100
        assert branch["second_action"]["state"] == "executed"
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] == 100
    assert d0["decision_owner"]["side"] == "self"


def test_own_charge_second_after_ordinary_attack_uses_branch_local_hp():
    _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
        own_move="freeze-shock", opponent_move="tackle", order="opponent_first",
    )
    assert pair["status"] == "evaluable", pair
    executed = [b for b in pair["terminal_branches"] if b["second_action"]["state"] == "executed"]
    assert executed
    for branch in executed:
        leaf = _charge_leaf(branch, first=False)
        assert leaf is not None
        first_target_hp = branch["first_action_leaf"]["consequences"]["target_final_hp"]
        assert leaf["consequences"]["own_final_hp"] == first_target_hp
        assert leaf["consequences"]["target_final_hp"] == branch["first_action_leaf"]["consequences"]["own_final_hp"]
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_opponent_charge_first_uses_actor_neutral_branch_d0_and_source_action_id():
    _state0, _snapshot0, d0, _own, opponent, _order0, pair = _case(
        own_move="tackle", opponent_move="sky-attack", order="opponent_first",
    )
    assert pair["status"] == "evaluable", pair
    first = pair["terminal_branches"][0]["first_action_leaf"]
    context = first["consequences"]["detached_standard_charge_lifecycle_context"]
    readiness = context["readiness_authority"]
    assert readiness["actor"] == d0["active_owners"]["opponent"]
    assert readiness["decision_owner"] == d0["active_owners"]["opponent"]
    assert readiness["action_id"] == opponent["action_id"]
    assert context["action_id"] == opponent["action_id"]
    assert first["candidate_id"] == "attack:sky-attack"
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_charge_vs_charge_equal_speed_preserves_two_half_order_branches_and_mass():
    _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
        own_move="razor-wind", opponent_move="ice-burn", order="tie",
    )
    assert pair["status"] == "evaluable", pair
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert {b["action_order"] for b in pair["terminal_branches"]} == {"own_first", "opponent_first"}
    assert {tuple(b["probability"].values()) for b in pair["terminal_branches"]} == {(1, 2)}
    for branch in pair["terminal_branches"]:
        assert _charge_leaf(branch, first=True) is not None
        assert _charge_leaf(branch, first=False) is not None
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_charge_vs_ordinary_equal_speed_preserves_both_orders_without_renormalization():
    _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
        own_move="sky-attack", opponent_move="tackle", order="tie",
    )
    assert pair["status"] == "evaluable", pair
    assert {b["action_order"] for b in pair["terminal_branches"]} == {"own_first", "opponent_first"}
    order_mass = {}
    for branch in pair["terminal_branches"]:
        order_mass.setdefault(branch["action_order"], 0)
        order_mass[branch["action_order"]] += branch["probability"]["numerator"] / branch["probability"]["denominator"]
    assert round(order_mass["own_first"], 10) == round(order_mass["opponent_first"], 10) == 0.5
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_charge_first_leaf_is_accepted_by_detached_intermediate_projection():
    _state0, _snapshot0, d0, _own, _opp, _order0, pair = _case(
        own_move="sky-attack", opponent_move="tackle", order="own_first",
    )
    leaf = pair["terminal_branches"][0]["first_action_leaf"]
    projected = materialize_detached_predictive_intermediate_state(
        strategy_d0=d0,
        terminal_leaf=leaf,
    )
    assert projected["status"] == "resolved", projected
    assert projected["active"]["self"]["hypothetical_hp"]["value"] == 100
    assert projected["active"]["opponent"]["hypothetical_hp"]["value"] == 100
    assert projected["second_action_compatibility"]["flinch_cancellation"]["state"] == "not_flinched"


def test_standard_charge_excluded_counterpart_families_fail_closed_before_special_dispatch():
    for move_id, metadata in (
        ("protect", {"move_id": "protect", "category": "status", "target": "self", "priority": 4, "accuracy": None, "power": None}),
        ("u-turn", {"move_id": "u-turn", "category": "physical", "target": "selected-pokemon", "priority": 0, "accuracy": 100, "power": 70, "type": "bug"}),
        ("fling", {"move_id": "fling", "category": "physical", "target": "selected-pokemon", "priority": 0, "accuracy": 100, "power": 1, "type": "dark"}),
        ("final-gambit", {"move_id": "final-gambit", "category": "special", "target": "selected-pokemon", "priority": 0, "accuracy": 100, "power": 0, "type": "fighting"}),
        ("bullet-seed", {"move_id": "bullet-seed", "category": "physical", "target": "selected-pokemon", "priority": 0, "accuracy": 100, "power": 25, "type": "grass", "min_hits": 2, "max_hits": 5}),
    ):
        state = _complete_state(_state())
        snapshot = _snapshot(state)
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
        own = _own_action(d0, d0["active_owners"]["self"], "sky-attack")
        opponent = _opponent_action(d0, move_id, metadata)
        pair = materialize_immediate_move_vs_move_action_pair(
            strategy_d0=d0, runtime_snapshot=snapshot,
            own_action=own, opponent_action=opponent,
            action_order_authority=_order(d0, own, opponent, "own_first"),
        )
        assert pair["status"] == "unsupported"
        assert pair["reason"] == "standard_charge_pair_counterpart_family_unrepresented"


def test_nonstandard_charge_moves_keep_global_guard():
    for move_id in ("geomancy",):
        state = _complete_state(_state())
        snapshot = _snapshot(state)
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
        metadata = _metadata(move_id)["metadata"]
        metadata["category"] = "status" if move_id == "geomancy" else metadata["category"]
        own = _own_action(d0, d0["active_owners"]["self"], move_id, metadata)
        opponent = _opponent_action(d0, "tackle")
        pair = materialize_immediate_move_vs_move_action_pair(
            strategy_d0=d0, runtime_snapshot=snapshot,
            own_action=own, opponent_action=opponent,
            action_order_authority=_order(d0, own, opponent, "own_first"),
        )
        assert pair["status"] == "unsupported"
        assert pair["reason"] == "two_turn_execution_unrepresented"

def test_opponent_charge_second_after_ordinary_own_attack_uses_branch_local_hp_and_ledger_mapping():
    _state0, _snapshot0, d0, _own, _opp, _order0, pair = _case(
        own_move="tackle", opponent_move="ice-burn", order="own_first",
    )
    assert pair["status"] == "evaluable", pair
    executed = [b for b in pair["terminal_branches"] if b["second_action"]["state"] == "executed"]
    assert executed
    for branch in executed:
        leaf = _charge_leaf(branch, first=False)
        assert leaf is not None
        assert leaf["provenance"]["attacker"] == d0["active_owners"]["opponent"]
        assert leaf["provenance"]["target"] == d0["active_owners"]["self"]
        assert leaf["consequences"]["own_final_hp"] == branch["first_action_leaf"]["consequences"]["target_final_hp"]
        assert leaf["consequences"]["target_final_hp"] == branch["first_action_leaf"]["consequences"]["own_final_hp"]
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger
    for terminal in ledger["terminal_leaves"]:
        final = terminal["final_consequences"]
        assert final["own_final_hp"] <= 100
        assert final["opponent_final_hp"] <= 100


def test_first_ordinary_attack_ko_cancels_second_charge_without_context():
    _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
        own_move="tackle", opponent_move="sky-attack", order="own_first", opponent_hp=1,
    )
    assert pair["status"] == "evaluable", pair
    assert pair["terminal_branches"]
    assert all(branch["second_action"]["state"] == "cancelled_due_to_faint" for branch in pair["terminal_branches"])
    assert all(branch["second_action"].get("leaf") is None for branch in pair["terminal_branches"])
    assert all(_charge_leaf(branch, first=False) is None for branch in pair["terminal_branches"])
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_iron_head_flinch_cancels_only_flinch_charge_branches_and_other_branches_charge():
    _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
        own_move="iron-head", opponent_move="sky-attack", order="own_first",
    )
    assert pair["status"] == "evaluable", pair
    states = {branch["second_action"]["state"] for branch in pair["terminal_branches"]}
    assert states == {"executed", "cancelled_due_to_flinch"}
    cancelled = [b for b in pair["terminal_branches"] if b["second_action"]["state"] == "cancelled_due_to_flinch"]
    executed = [b for b in pair["terminal_branches"] if b["second_action"]["state"] == "executed"]
    assert cancelled and executed
    assert all(_charge_leaf(branch, first=False) is None for branch in cancelled)
    assert all(_charge_leaf(branch, first=False) is not None for branch in executed)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_thunderbolt_paralysis_cancel_branch_has_no_charge_and_execute_branch_charges():
    _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
        own_move="thunderbolt", opponent_move="sky-attack", order="own_first",
    )
    assert pair["status"] == "evaluable", pair
    states = {branch["second_action"]["state"] for branch in pair["terminal_branches"]}
    assert {"executed", "cancelled_due_to_paralysis"} <= states
    cancelled = [b for b in pair["terminal_branches"] if b["second_action"]["state"] == "cancelled_due_to_paralysis"]
    executed = [b for b in pair["terminal_branches"] if b["second_action"]["state"] == "executed"]
    assert cancelled and executed
    assert all(_charge_leaf(branch, first=False) is None for branch in cancelled)
    assert any(_charge_leaf(branch, first=False) is not None for branch in executed)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_active_power_herb_charge_pair_executes_same_turn_without_charge_context():
    state = _with_terminal_mechanics_facts(_complete_state(_state()))
    actor_raw = state["self_side"]["pokemon"][0]
    actor_raw["known_item"] = "power-herb"
    actor_raw["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": "known",
    }
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": "charge-pair-power-herb",
        "source_sequence": 1,
    }
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = _own_action(d0, d0["active_owners"]["self"], "sky-attack")
    opponent = _opponent_action(d0, "tackle")
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "own_first"),
    )
    assert pair["status"] == "evaluable", (pair.get("status"), pair.get("reason"))
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert pair["terminal_branches"]
    first_leaves = [branch["first_action_leaf"] for branch in pair["terminal_branches"]]
    assert all(leaf["provenance"]["move_id"] == "sky-attack" for leaf in first_leaves)
    assert all("detached_standard_charge_lifecycle_context" not in leaf["consequences"] for leaf in first_leaves)
    executing = [leaf for leaf in first_leaves if "power_herb_consumption" in leaf["consequences"]]
    assert executing
    assert all(leaf["consequences"]["actor_item_after"] == {"status": "known_absent", "value": None} for leaf in executing)


def _event_charge_context(event):
    leaf = event.get("attack_leaf") if isinstance(event, dict) else None
    return (
        leaf.get("consequences", {}).get("detached_standard_charge_lifecycle_context")
        if isinstance(leaf, dict)
        else None
    )


def test_sleep_gate_blocks_charge_and_wake_execute_branch_starts_charge():
    from tests.test_champions_sleep_freeze_action_gate import pair as status_pair

    blocked = status_pair("sleep", prior=0, duration=2, move="sky-attack")
    assert blocked["status"] == "evaluable", blocked
    blocked_events = [
        path["actions"][0]
        for path in blocked["terminal_paths"]
        if path["actions"][0]["state"] == "cancelled_sleep"
    ]
    assert blocked_events
    assert all(_event_charge_context(event) is None for event in blocked_events)

    wake = status_pair("sleep", prior=1, duration=2, move="sky-attack")
    assert wake["status"] == "evaluable", wake
    execute_events = [
        path["actions"][0]
        for path in wake["terminal_paths"]
        if path["actions"][0]["state"] in {"wakes_and_executes", "status_selected_action_executes"}
        or "attack_leaf" in path["actions"][0]
    ]
    assert execute_events
    assert all(_event_charge_context(event) is not None for event in execute_events)


def test_confusion_self_hit_has_no_charge_and_selected_execution_starts_charge():
    from tests.test_champions_confusion_action_gate import inputs as confusion_inputs

    snapshot, _d0, owner = confusion_inputs(duration=3)
    refreshed_state = deepcopy(snapshot["state"])
    opponent_raw = refreshed_state["opponent_side"]["pokemon"][0]
    opponent_raw["current_confusion"] = "none"
    opponent_raw["confusion_provenance"] = {
        "event_kind": "current_confusion_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "state": "none",
    }
    snapshot = _snapshot(refreshed_state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    own = _own_action(d0, d0["active_owners"]["self"], "sky-attack")
    opponent = _opponent_action(d0, "tackle")
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "own_first"),
    )
    assert pair["status"] == "evaluable", pair
    self_hit = [
        path["actions"][0]
        for path in pair["terminal_paths"]
        if path["actions"][0]["state"] == "confusion_self_hit"
    ]
    executed = [
        path["actions"][0]
        for path in pair["terminal_paths"]
        if path["actions"][0]["state"] == "confusion_selected_action_executes"
    ]
    assert self_hit and executed
    assert all(_event_charge_context(event) is None for event in self_hit)
    assert all(_event_charge_context(event) is not None for event in executed)


def test_combined_status_confusion_keeps_status_then_confusion_order_before_charge():
    from tests.test_champions_sleep_freeze_action_gate import inputs as status_inputs
    from llm.advisor_reducer_state_model import state_fingerprint

    snapshot, _d0, owner = status_inputs("sleep", prior=0, duration=2)
    state = deepcopy(snapshot["state"])
    raw = state["self_side"]["pokemon"][0]
    opponent_raw = state["opponent_side"]["pokemon"][0]
    opponent_raw["current_confusion"] = "none"
    opponent_raw["confusion_provenance"] = {
        "event_kind": "current_confusion_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "state": "none",
    }
    raw["current_confusion"] = "confused"
    raw["confusion_provenance"] = {
        "event_kind": "current_confusion_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "state": "confused",
    }
    raw["champions_confusion_progression"] = {
        "schema_version": "champions-confusion-progression-v1",
        "owner": deepcopy(owner),
        "state": "confused",
        "origin_id": "charge-combined-confusion",
        "established_turn": 1,
        "prior_opportunities": 0,
        "duration": 3,
        "confusion_observation": deepcopy(raw["confusion_provenance"]),
        "observed_turn": 1,
        "provenance": "test",
    }
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": state,
        "state_fingerprint": state_fingerprint(state),
    }
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    own = _own_action(d0, d0["active_owners"]["self"], "sky-attack")
    opponent = _opponent_action(d0, "tackle")
    blocked = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "own_first"),
    )
    assert blocked["status"] == "evaluable", blocked
    sleep_cancelled = [
        path for path in blocked["terminal_paths"]
        if path["actions"][0]["state"] == "cancelled_sleep"
    ]
    assert sleep_cancelled
    assert all(
        not any(event.get("state") == "confusion_self_hit" for event in path["actions"])
        for path in sleep_cancelled
    )
    assert all(
        _event_charge_context(path["actions"][0]) is None
        for path in sleep_cancelled
    )

    wake_snapshot, _wake_d0, wake_owner = status_inputs("sleep", prior=1, duration=2)
    wake_state = deepcopy(wake_snapshot["state"])
    wake_raw = wake_state["self_side"]["pokemon"][0]
    wake_opponent_raw = wake_state["opponent_side"]["pokemon"][0]
    wake_opponent_raw["current_confusion"] = "none"
    wake_opponent_raw["confusion_provenance"] = {
        "event_kind": "current_confusion_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "state": "none",
    }
    wake_raw["current_confusion"] = "confused"
    wake_raw["confusion_provenance"] = deepcopy(raw["confusion_provenance"])
    wake_raw["champions_confusion_progression"] = {
        **deepcopy(raw["champions_confusion_progression"]),
        "owner": deepcopy(wake_owner),
    }
    wake_snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": wake_state["session_id"],
        "state": wake_state,
        "state_fingerprint": state_fingerprint(wake_state),
    }
    wake_d0 = freeze_runtime_strategy_d0(runtime_snapshot=wake_snapshot, decision_owner=wake_owner)
    wake_own = _own_action(wake_d0, wake_d0["active_owners"]["self"], "sky-attack")
    wake_opponent = _opponent_action(wake_d0, "tackle")
    wake = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=wake_d0,
        runtime_snapshot=wake_snapshot,
        own_action=wake_own,
        opponent_action=wake_opponent,
        action_order_authority=_order(wake_d0, wake_own, wake_opponent, "own_first"),
    )
    assert wake["status"] == "evaluable", wake
    confusion_self_hit_paths = [
        path for path in wake["terminal_paths"]
        if any(event.get("state") == "confusion_self_hit" for event in path["actions"])
    ]
    charge_execute_paths = [
        path for path in wake["terminal_paths"]
        if any(
            event.get("state") == "selected_action_executes"
            and _event_charge_context(event) is not None
            for event in path["actions"]
        )
    ]
    assert confusion_self_hit_paths and charge_execute_paths
    assert all(
        all(_event_charge_context(event) is None for event in path["actions"])
        for path in confusion_self_hit_paths
    )
    for path in charge_execute_paths:
        states = [event.get("state") for event in path["actions"]]
        assert "wakes_and_executes" in states
        assert "confusion_selected_action_executes" in states
        assert "selected_action_executes" in states
        assert states.index("wakes_and_executes") < states.index("confusion_selected_action_executes") < states.index("selected_action_executes")


def test_remaining_supported_own_charge_routes_are_evaluable():
    for move_id in ("razor-wind", "ice-burn"):
        _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
            own_move=move_id, opponent_move="tackle", order="own_first",
        )
        assert pair["status"] == "evaluable", (move_id, pair)
        assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert all(_charge_leaf(branch, first=True) is not None for branch in pair["terminal_branches"])
        assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_exact_ledger_preserves_charge_context_and_opponent_charge_final_hp_mapping():
    _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
        own_move="tackle", opponent_move="ice-burn", order="own_first",
    )
    assert pair["status"] == "evaluable", pair
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    for terminal in ledger["terminal_leaves"]:
        source = terminal["source_pair_branch"]
        second_leaf = source["second_action"].get("leaf")
        if not isinstance(second_leaf, dict):
            continue
        context = second_leaf["consequences"].get("detached_standard_charge_lifecycle_context")
        if not isinstance(context, dict):
            continue
        assert terminal["second_action"]["leaf"]["consequences"]["detached_standard_charge_lifecycle_context"] == context
        first = source["first_action_leaf"]["consequences"]
        final = terminal["final_consequences"]
        assert final["own_final_hp"] == first["own_final_hp"]
        assert final["opponent_final_hp"] == first["target_final_hp"]


def test_exact_ledger_rejects_standard_charge_leaf_tampering():
    _state0, _snapshot0, _d0, _own, _opp, _order0, pair = _case(
        own_move="sky-attack", opponent_move="tackle", order="own_first",
    )
    assert pair["status"] == "evaluable", pair
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"

    def forged(mutator):
        value = deepcopy(pair)
        leaf = value["terminal_branches"][0]["first_action_leaf"]
        mutator(leaf)
        ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=value)
        assert ledger["status"] == "rejected", ledger

    forged(lambda leaf: leaf["consequences"].update(damage=1))
    forged(lambda leaf: leaf["consequences"].update(own_final_hp=99))
    forged(lambda leaf: leaf["provenance"]["attacker"].update(pokemon_id="forged"))
    forged(lambda leaf: leaf["provenance"].update(move_id="razor-wind"))
    forged(lambda leaf: leaf["provenance"]["standard_charge_start_readiness_authority"].update(action_id="forged"))
    forged(lambda leaf: leaf["consequences"]["detached_standard_charge_lifecycle_context"]["continuation_target_locator"].update(slot_index=9))
    forged(lambda leaf: leaf["consequences"]["detached_standard_charge_lifecycle_context"]["continuation_target_locator"].update(pokemon_id="frozen-victim"))
    forged(lambda leaf: leaf["consequences"]["detached_standard_charge_lifecycle_context"].update(pp_consumption_materialized=True))
    forged(lambda leaf: leaf["consequences"]["detached_standard_charge_lifecycle_context"]["power_herb_applicability_state"].update(status="active"))

def test_opponent_charge_action_identity_contradiction_rejects_strict_normalization():
    state = _complete_state(_state())
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = _own_action(d0, d0["active_owners"]["self"], "tackle")
    opponent = _opponent_action(d0, "sky-attack")
    opponent["identity"] = "razor-wind"
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "opponent_first"),
    )
    assert pair["status"] == "rejected"
    assert "branch_selected_action_move_identity_conflict" in pair["reason"]


def test_opponent_charge_second_rejects_forged_source_opponent_actor():
    state = _complete_state(_state())
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    own = _own_action(d0, d0["active_owners"]["self"], "tackle")
    opponent = _opponent_action(d0, "sky-attack")
    opponent["opponent_actor"] = {
        **deepcopy(opponent["opponent_actor"]),
        "pokemon_id": "forged-opponent",
    }
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=_order(d0, own, opponent, "own_first"),
    )
    assert pair["status"] == "rejected"
    assert "branch_selected_action_source_actor_binding_mismatch" in pair["reason"]
    assert "terminal_branches" not in pair


def test_opponent_charge_second_rejects_malformed_or_wrong_explicit_target_owner():
    state = _complete_state(_state())
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    own = _own_action(d0, d0["active_owners"]["self"], "tackle")

    malformed = _opponent_action(d0, "sky-attack")
    malformed["target_owner"] = "not-an-owner"
    malformed_pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=malformed,
        action_order_authority=_order(d0, own, malformed, "own_first"),
    )
    assert malformed_pair["status"] == "rejected"
    assert "branch_selected_action_target_binding_mismatch" in malformed_pair["reason"]

    wrong = _opponent_action(d0, "sky-attack")
    wrong["target_owner"] = {
        **deepcopy(wrong["target_owner"]),
        "pokemon_id": "forged-target",
    }
    wrong_pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=wrong,
        action_order_authority=_order(d0, own, wrong, "own_first"),
    )
    assert wrong_pair["status"] == "rejected"
    assert "branch_selected_action_target_binding_mismatch" in wrong_pair["reason"]


def test_opponent_charge_second_rejects_embedded_metadata_actor_or_candidate_claim():
    state = _complete_state(_state())
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    own = _own_action(d0, d0["active_owners"]["self"], "tackle")

    forged_actor = _opponent_action(d0, "sky-attack")
    forged_actor["metadata_authority"]["active_attacker"] = {
        **deepcopy(d0["active_owners"]["opponent"]),
        "pokemon_id": "forged-metadata-actor",
    }
    actor_pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=forged_actor,
        action_order_authority=_order(d0, own, forged_actor, "own_first"),
    )
    assert actor_pair["status"] == "rejected"
    assert "branch_selected_action_metadata_actor_binding_mismatch" in actor_pair["reason"]

    forged_candidate = _opponent_action(d0, "sky-attack")
    forged_candidate["metadata_authority"]["candidate_id"] = "opponent_attack:razor-wind"
    candidate_pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=forged_candidate,
        action_order_authority=_order(d0, own, forged_candidate, "own_first"),
    )
    assert candidate_pair["status"] == "rejected"
    assert "branch_selected_action_metadata_candidate_binding_mismatch" in candidate_pair["reason"]


def test_standard_charge_pair_action_ledger_never_promotes_unresolved_source_metadata():
    from llm.advisor_immediate_move_vs_move_action_pair import _pair_action_ledger

    state = _complete_state(_state())
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    actor = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    action = _own_action(d0, actor, "sky-attack")
    raw_metadata = deepcopy(action["move_metadata_authority"]["metadata"])

    for status in ("incomplete", "rejected"):
        source = {
            "status": status,
            "reason": f"fixture_{status}",
            "move_id": "sky-attack",
            "metadata": deepcopy(raw_metadata),
        }
        result = _pair_action_ledger(
            strategy_d0=d0,
            runtime_snapshot=snapshot,
            actor=actor,
            target=target,
            metadata_authority=raw_metadata,
            source_metadata_authority=source,
            action=action,
        )
        assert result["status"] == status
        assert result["reason"] == f"fixture_{status}"
        assert "terminal_leaves" not in result
        assert "component_manifest" not in result
