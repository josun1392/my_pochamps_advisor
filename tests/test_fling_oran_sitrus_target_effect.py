from copy import deepcopy

import pytest

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_detached_berry_eaten_transition import (
    materialize_detached_fling_berry_eaten_transition,
)

from llm.advisor_detached_predictive_intermediate_state import (
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_detached_sitrus_berry_immediate_consumption import (
    materialize_detached_sitrus_berry_immediate_consumption,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
)
from llm.advisor_runtime_d0_fling_hp_restore_berry_target_effect_authority import (
    freeze_runtime_d0_fling_hp_restore_berry_target_effect_authority,
    materialize_detached_fling_hp_restore_berry_target_effect,
    validate_detached_fling_hp_restore_berry_target_effect,
)
from llm.advisor_runtime_d0_fling_item_execution_authority import (
    freeze_runtime_d0_fling_item_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import _leaf


_UNSET = object()


def _case(
    *,
    item="oran-berry",
    post_hp=40,
    max_hp=100,
    healing_prevented="inactive",
    target_ability="pressure",
    target_item=_UNSET,
    hit_state="hit",
    damage=20,
    routing="target",
    ko=False,
):
    state, _snapshot, _old_d0, _old_own, _responses, _orders = _inputs()
    own = state["self_side"]["pokemon"][0]
    foe = state["opponent_side"]["pokemon"][0]
    own["known_item"] = item
    own["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": "known",
        "source_observation_id": "source-berry",
        "source_sequence": 1,
    }
    own["current_ability"] = "pressure"
    own["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "source_observation_id": "source-ability",
        "source_sequence": 1,
    }
    foe["current_ability"] = target_ability
    foe["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "source_observation_id": "target-ability",
        "source_sequence": 1,
    }
    foe["current_hp"] = max_hp if isinstance(max_hp, int) else 100
    foe["max_hp"] = max_hp
    foe["fainted"] = False
    if target_item is not _UNSET:
        if target_item == "__unknown__":
            foe["known_item"] = {"knowledge": "unknown"}
            foe.pop("known_item_provenance", None)
        elif target_item is None:
            foe["known_item"] = None
            foe["known_item_provenance"] = {
                "event_kind": "current_item_observed",
                "trust": "user_confirmed_observation",
                "turn_number": 1,
                "status": "known_absent",
                "source_observation_id": "target-item",
                "source_sequence": 1,
            }
        else:
            foe["known_item"] = target_item
            foe["known_item_provenance"] = {
                "event_kind": "current_item_observed",
                "trust": "user_confirmed_observation",
                "turn_number": 1,
                "status": "known",
                "source_observation_id": "target-item",
                "source_sequence": 1,
            }
    if healing_prevented == "__unknown__":
        foe["healing_prevented_status"] = {"knowledge": "unknown"}
        foe.pop("healing_prevented_status_provenance", None)
    else:
        foe["healing_prevented_status"] = healing_prevented
        foe["healing_prevented_status_provenance"] = {
            "event_kind": "current_healing_prevented_observed",
            "trust": "user_confirmed_observation",
            "status": healing_prevented,
            "turn_number": 1,
            "source_observation_id": "target-healing-prevented",
            "source_sequence": 1,
        }
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": "magic-room",
        "source_sequence": 1,
    }
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }
    decision_owner = {
        "session_id": state["session_id"],
        "side": "self",
        "slot_index": 0,
        "pokemon_id": own["pokemon_id"],
    }
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=decision_owner,
    )
    actor = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    metadata = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
    action = {
        "action_id": "attack:fling",
        "action_type": "attack",
        "identity": "fling",
        "move_metadata_authority": {"status": "resolved", "metadata": metadata},
    }
    execution = freeze_runtime_d0_fling_item_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
    )
    leaf = _leaf(
        d0, actor, target, execution,
        hit_state=hit_state, damage=damage, routing=routing,
        hp=post_hp, ko=ko,
    )
    interaction = freeze_runtime_d0_fling_berry_eat_item_interaction_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        fling_execution_authority=execution,
        actor=actor,
        target=target,
        phase="post_hit_target_berry_interaction",
        source_leaf=leaf,
    )
    effect = freeze_runtime_d0_fling_hp_restore_berry_target_effect_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        fling_execution_authority=execution,
        source_leaf=leaf,
        berry_eat_item_interaction_authority=interaction,
        actor=actor,
        target=target,
    )
    return {
        "state": state, "snapshot": snapshot, "d0": d0,
        "actor": actor, "target": target, "execution": execution,
        "leaf": leaf, "interaction": interaction, "effect": effect,
    }


@pytest.mark.parametrize(
    ("item", "post_hp", "max_hp", "nominal", "actual", "final"),
    [
        ("oran-berry", 40, 100, 10, 10, 50),
        ("oran-berry", 95, 100, 10, 5, 100),
        ("oran-berry", 60, 100, 10, 10, 70),
        ("sitrus-berry", 40, 100, 25, 25, 65),
        ("sitrus-berry", 40, 101, 25, 25, 65),
        ("sitrus-berry", 95, 100, 25, 5, 100),
        ("sitrus-berry", 2, 3, 1, 1, 3),
        ("sitrus-berry", 60, 100, 25, 25, 85),
    ],
)
def test_exact_heal_math_and_no_held_threshold(item, post_hp, max_hp, nominal, actual, final):
    case = _case(item=item, post_hp=post_hp, max_hp=max_hp)
    effect = case["effect"]
    assert effect["status"] == "resolved", effect
    assert effect["outcome"] == "healed"
    assert effect["nominal_heal"] == nominal
    assert effect["actual_heal"] == actual
    assert effect["final_hp"] == final
    detached = materialize_detached_fling_hp_restore_berry_target_effect(
        authority=effect, source_leaf=case["leaf"],
    )
    assert detached["status"] == "resolved"
    assert detached["leaf"]["consequences"]["target_final_hp"] == final
    assert validate_detached_fling_hp_restore_berry_target_effect(
        consequence=detached["consequence"],
        source_leaf=detached["leaf"],
        expected_target=case["target"],
    )


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_healing_prevented_blocks_hp_only_but_eat_and_ateberry_remain(item):
    case = _case(item=item, post_hp=40, max_hp=100, healing_prevented="active")
    effect = case["effect"]
    assert effect["status"] == "resolved"
    assert effect["outcome"] == "healing_prevented"
    assert effect["actual_heal"] == 0
    assert effect["final_hp"] == 40
    assert case["interaction"]["target_eat_occurred"] is True
    assert case["interaction"]["target_eat_item_dispatched"] is True
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "resolved"
    assert eaten["resulting_state"] == "known_true"


def test_unknown_healing_prevention_fails_closed():
    case = _case(healing_prevented="__unknown__")
    assert case["effect"]["status"] == "incomplete"


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_target_klutz_known_absent_suppresses_heal_but_ateberry_remains(item):
    case = _case(
        item=item, target_ability="klutz", target_item=None,
        healing_prevented="__unknown__",
    )
    effect = case["effect"]
    assert effect["status"] == "resolved"
    assert effect["outcome"] == "intrinsic_suppressed_by_target_klutz"
    assert effect["actual_heal"] == 0
    assert effect["final_hp"] == 40
    assert effect["healing_prevented_at_item_check"] is None
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "resolved"


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_target_klutz_ability_shield_executes_and_target_item_is_preserved(item):
    case = _case(
        item=item, target_ability="klutz", target_item="ability-shield",
    )
    assert case["effect"]["status"] == "resolved"
    assert case["effect"]["outcome"] == "healed"
    assert case["snapshot"]["state"]["opponent_side"]["pokemon"][0]["known_item"] == "ability-shield"
    detached = materialize_detached_fling_hp_restore_berry_target_effect(
        authority=case["effect"], source_leaf=case["leaf"],
    )
    assert "target_item_after" not in detached["consequence"]


def test_target_klutz_unknown_item_is_incomplete():
    case = _case(target_ability="klutz", target_item="__unknown__")
    assert case["effect"]["status"] == "incomplete"


def test_leftovers_target_item_is_not_consumed_or_replaced():
    case = _case(target_item="leftovers")
    assert case["effect"]["status"] == "resolved"
    assert case["snapshot"]["state"]["opponent_side"]["pokemon"][0]["known_item"] == "leftovers"
    detached = materialize_detached_fling_hp_restore_berry_target_effect(
        authority=case["effect"], source_leaf=case["leaf"],
    )
    assert "target_item_after" not in detached["consequence"]


@pytest.mark.parametrize(
    ("kwargs",),
    [
        ({"hit_state": "miss", "damage": 0, "post_hp": 100},),
        ({"damage": 0, "post_hp": 100},),
        ({"routing": "substitute", "damage": 20, "post_hp": 100},),
        ({"ko": True, "post_hp": 0, "damage": 100},),
    ],
)
def test_no_eat_branches_do_not_heal_or_create_ateberry(kwargs):
    case = _case(**kwargs)
    assert case["effect"]["status"] == "resolved"
    assert case["effect"]["outcome"] == "not_applicable"
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "not_applicable"


@pytest.mark.parametrize("ability", ["cheek-pouch", "ripen", "cud-chew"])
def test_deferred_direct_eat_item_hooks_remain_incomplete(ability):
    case = _case(target_ability=ability)
    assert case["effect"]["status"] == "incomplete"


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_healed_leaf_projects_exact_hp_into_detached_pending_state_without_runtime_mutation(item):
    case = _case(item=item, post_hp=40, max_hp=100)
    detached = materialize_detached_fling_hp_restore_berry_target_effect(
        authority=case["effect"], source_leaf=case["leaf"],
    )
    expected = 50 if item == "oran-berry" else 65
    intermediate = materialize_detached_predictive_intermediate_state(
        strategy_d0=case["d0"], terminal_leaf=detached["leaf"],
    )
    assert intermediate["status"] == "resolved"
    assert intermediate["active"]["opponent"]["hypothetical_hp"]["value"] == expected
    assert case["snapshot"]["state"]["opponent_side"]["pokemon"][0]["current_hp"] == 100
    assert case["d0"]["strategy_state"]["active"]["opponent"]["current_hp"] == 100


def test_thrown_sitrus_and_existing_held_sitrus_are_distinct_sequential_consequences():
    case = _case(
        item="sitrus-berry",
        post_hp=20,
        max_hp=100,
        target_item="sitrus-berry",
    )
    assert case["effect"]["outcome"] == "healed"
    assert case["effect"]["final_hp"] == 45
    thrown = materialize_detached_fling_hp_restore_berry_target_effect(
        authority=case["effect"], source_leaf=case["leaf"],
    )
    thrown_leaf = deepcopy(thrown["leaf"])
    thrown_leaf["consequences"]["damage"] = 20
    held = materialize_detached_sitrus_berry_immediate_consumption(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        terminal_leaf=thrown_leaf,
        holder=case["target"],
        move_metadata=resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"],
    )
    assert held["status"] == "resolved", held
    assert held["outcome"] == "activated"
    assert held["sitrus_consequence"]["post_hit_hp"] == 45
    assert held["sitrus_consequence"]["heal_amount"] == 25
    assert held["sitrus_consequence"]["final_hp"] == 70
    assert held["sitrus_consequence"]["item_before"] == "sitrus-berry"
    assert case["effect"]["item_id"] == "sitrus-berry"
    assert case["snapshot"]["state"]["opponent_side"]["pokemon"][0]["known_item"] == "sitrus-berry"


def test_unknown_max_hp_fails_closed():
    case = _case(item="oran-berry", post_hp=40, max_hp=None)
    assert case["effect"]["status"] == "incomplete"
    assert case["effect"]["reason"] == "fling_hp_restore_max_hp_unknown"


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_ateberry_true_to_true_remains_idempotent(item):
    case = _case(item=item)
    case["d0"]["current_berry_eaten_authority"]["opponent"] = {
        "status": "resolved",
        "schema_version": "runtime-d0-current-berry-eaten-authority-v1",
        "session_id": case["d0"]["session_id"],
        "source_runtime_fingerprint": case["d0"]["source_runtime_fingerprint"],
        "source_branch_fingerprint": case["d0"]["strategy_preview_fingerprint"],
        "state": "known_true",
        "value": True,
        "owner": deepcopy(case["target"]),
    }
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "resolved"
    assert eaten["prior_state"] == "known_true"
    assert eaten["resulting_state"] == "known_true"
    assert eaten["transition"] == "true_to_true"
