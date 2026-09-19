from copy import deepcopy

import pytest

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_detached_berry_eaten_transition import (
    materialize_detached_fling_berry_eaten_transition,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
)
from llm.advisor_runtime_d0_fling_item_execution_authority import (
    freeze_runtime_d0_fling_item_execution_authority,
)
from llm.advisor_runtime_d0_fling_leppa_pp_restore_target_effect_authority import (
    freeze_runtime_d0_fling_leppa_pp_restore_target_effect_authority,
    materialize_detached_fling_leppa_pp_restore_target_effect,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import (
    _TARGET_ITEM_UNSET,
    _fixture,
    _leaf,
)


MOVES = ["water-gun", "tackle", "growl", "tail-whip"]


def _slots(values):
    return [
        {"slot_index": index, "move_id": MOVES[index], "current_pp": current, "max_pp": maximum}
        for index, (current, maximum) in enumerate(values)
    ]


def _case(
    *,
    pp_values=None,
    target_ability="pressure",
    target_item=_TARGET_ITEM_UNSET,
    source_ability="pressure",
    hit_state="hit",
    damage=20,
    routing="target",
    hp=80,
    ko=False,
):
    state, _snapshot, _d0, _actor, _target, _execution = _fixture(
        item="leppa-berry",
        source_ability=source_ability,
        target_ability=target_ability,
        target_item=target_item,
    )
    foe = state["opponent_side"]["pokemon"][0]
    sequence = 77
    if pp_values is not None:
        pp = _slots(pp_values)
        provenance = {
            "event_kind": "current_opponent_response_set_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "source_observation_id": "leppa-pp",
            "source_sequence": sequence,
        }
        usability = {}
        for row in pp:
            if row["current_pp"] == 0:
                usability[row["move_id"]] = {
                    "status": "known_unusable",
                    "reason": "no_pp",
                    "provenance": deepcopy(provenance),
                }
            else:
                usability[row["move_id"]] = {
                    "status": "known_usable",
                    "reason": None,
                    "provenance": deepcopy(provenance),
                }
        foe["known_move_ids"] = list(MOVES)
        foe["known_move_ids_provenance"] = {
            move: deepcopy(provenance) for move in MOVES
        }
        foe["current_move_usability"] = usability
        foe["current_opponent_response_set"] = {
            "moveset_completeness": "complete",
            "move_ids": list(MOVES),
            "move_pp_slots": pp,
            "provenance": deepcopy(provenance),
        }
        state["last_applied_observation_sequence"] = sequence

    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }
    owner = {
        "session_id": state["session_id"],
        "side": "self",
        "slot_index": 0,
        "pokemon_id": state["self_side"]["pokemon"][0]["pokemon_id"],
    }
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
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
        hit_state=hit_state, damage=damage, routing=routing, hp=hp, ko=ko,
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
    effect = freeze_runtime_d0_fling_leppa_pp_restore_target_effect_authority(
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


def test_zero_pp_priority_beats_earlier_partial_slot():
    case = _case(pp_values=[(4, 10), (0, 15), (10, 10), (10, 10)])
    effect = case["effect"]
    assert effect["status"] == "resolved"
    assert effect["outcome"] == "pp_restored"
    assert effect["selected_slot_index"] == 1
    assert effect["selected_move_id"] == "tackle"
    assert effect["selection_reason"] == "first_zero_pp"
    assert (effect["pp_before"], effect["nominal_restore"], effect["actual_restore"], effect["pp_after"]) == (0, 10, 10, 10)


def test_multiple_zero_slots_choose_first_zero_and_cap_to_max_pp():
    case = _case(pp_values=[(5, 10), (0, 5), (0, 20), (10, 10)])
    effect = case["effect"]
    assert effect["outcome"] == "pp_restored"
    assert effect["selected_slot_index"] == 1
    assert effect["selection_reason"] == "first_zero_pp"
    assert effect["nominal_restore"] == 10
    assert effect["actual_restore"] == 5
    assert effect["pp_after"] == 5


def test_no_zero_selects_first_partial_slot_and_restores_ten_capped():
    case = _case(pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)])
    effect = case["effect"]
    assert effect["outcome"] == "pp_restored"
    assert effect["selected_slot_index"] == 1
    assert effect["selected_move_id"] == "tackle"
    assert effect["selection_reason"] == "first_missing_pp"
    assert effect["pp_before"] == 7
    assert effect["actual_restore"] == 8
    assert effect["pp_after"] == 15


def test_all_full_is_exact_no_effect_but_keeps_staleness_and_ateberry():
    case = _case(pp_values=[(10, 10), (15, 15), (20, 20), (30, 30)])
    effect = case["effect"]
    assert effect["status"] == "resolved"
    assert effect["outcome"] == "no_effect_all_pp_full"
    assert effect["selected_slot_index"] is None
    assert effect["actual_restore"] == 0
    assert effect["external_staleness"] == {
        "value": True,
        "source": "fling_leppa_successful_target_eat",
        "timing": "after_target_eat_item_dispatch",
    }
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "resolved"
    assert eaten["resulting_state"] == "known_true"


@pytest.mark.parametrize("ability", ["ripen", "cheek-pouch", "cud-chew"])
def test_deferred_target_berry_hooks_remain_incomplete(ability):
    case = _case(
        pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)],
        target_ability=ability,
    )
    assert case["effect"]["status"] == "incomplete"


def test_neutralizing_gas_plus_ripen_composition_remains_incomplete():
    case = _case(
        pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)],
        source_ability="neutralizing-gas",
        target_ability="ripen",
    )
    assert case["effect"]["status"] == "incomplete"


def test_wrong_family_and_forged_fling_bp_are_rejected():
    case = _case(pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)])
    forged = deepcopy(case["execution"])
    forged["resolved_base_power"] = 20
    effect = freeze_runtime_d0_fling_leppa_pp_restore_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=forged,
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=case["interaction"],
        actor=case["actor"],
        target=case["target"],
    )
    assert effect["status"] == "rejected"

    oran = _case(pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)])
    wrong_execution = deepcopy(oran["execution"])
    wrong_execution["user_item_before"]["value"] = "oran-berry"
    wrong = freeze_runtime_d0_fling_leppa_pp_restore_target_effect_authority(
        strategy_d0=oran["d0"],
        runtime_snapshot=oran["snapshot"],
        fling_execution_authority=wrong_execution,
        source_leaf=oran["leaf"],
        berry_eat_item_interaction_authority=oran["interaction"],
        actor=oran["actor"],
        target=oran["target"],
    )
    assert wrong["status"] == "rejected"


def test_target_klutz_suppresses_without_requiring_pp_but_keeps_staleness_and_ateberry():
    case = _case(
        pp_values=None,
        target_ability="klutz",
        target_item=None,
    )
    effect = case["effect"]
    assert effect["status"] == "resolved"
    assert effect["outcome"] == "intrinsic_suppressed_by_target_klutz"
    assert effect["current_pp_authority"] is None
    assert effect["actual_restore"] == 0
    assert effect["external_staleness"]["value"] is True
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "resolved"


def test_klutz_ability_shield_executes_intrinsic_when_exact_pp_exists_and_item_is_preserved():
    case = _case(
        pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)],
        target_ability="klutz",
        target_item="ability-shield",
    )
    effect = case["effect"]
    assert effect["status"] == "resolved"
    assert effect["outcome"] == "pp_restored"
    assert effect["target_intrinsic_on_eat_readiness"]["readiness"] == "executes"
    assert case["snapshot"]["state"]["opponent_side"]["pokemon"][0]["known_item"] == "ability-shield"
    detached = materialize_detached_fling_leppa_pp_restore_target_effect(
        authority=effect, source_leaf=case["leaf"],
    )
    assert "target_item_after" not in detached["consequence"]


def test_pressure_without_pp_snapshot_makes_only_leppa_consequence_incomplete():
    case = _case(pp_values=None)
    assert case["execution"]["status"] == "resolved"
    assert case["interaction"]["status"] == "resolved"
    assert case["effect"]["status"] == "incomplete"
    assert case["effect"]["reason"] == "current_opponent_move_pp_snapshot_unknown"


def test_leftovers_target_item_is_unchanged_by_thrown_leppa():
    case = _case(
        pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)],
        target_item="leftovers",
    )
    assert case["effect"]["status"] == "resolved"
    assert case["snapshot"]["state"]["opponent_side"]["pokemon"][0]["known_item"] == "leftovers"
    detached = materialize_detached_fling_leppa_pp_restore_target_effect(
        authority=case["effect"], source_leaf=case["leaf"],
    )
    assert "target_item_after" not in detached["consequence"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hit_state": "miss", "damage": 0, "hp": 100},
        {"damage": 0, "hp": 100},
        {"routing": "substitute", "damage": 20, "hp": 100},
        {"ko": True, "hp": 0, "damage": 100},
    ],
)
def test_no_eat_paths_have_no_pp_effect_no_staleness_and_no_ateberry(kwargs):
    case = _case(
        pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)],
        **kwargs,
    )
    effect = case["effect"]
    assert effect["status"] == "resolved"
    assert effect["outcome"] == "not_applicable"
    assert effect["external_staleness"] is None
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "not_applicable"


def test_target_effect_and_materialization_leave_runtime_and_d0_immutable():
    case = _case(pp_values=[(10, 10), (7, 15), (3, 10), (10, 10)])
    before_snapshot = deepcopy(case["snapshot"])
    before_d0 = deepcopy(case["d0"])
    detached = materialize_detached_fling_leppa_pp_restore_target_effect(
        authority=case["effect"], source_leaf=case["leaf"],
    )
    assert detached["status"] == "resolved"
    assert detached["consequence"]["timing"] == "post_eat_pre_pending_action"
    assert case["snapshot"] == before_snapshot
    assert case["d0"] == before_d0
