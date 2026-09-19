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
from llm.advisor_runtime_d0_fling_persim_confusion_cure_target_effect_authority import (
    freeze_runtime_d0_fling_persim_confusion_cure_target_effect_authority,
    materialize_detached_fling_persim_confusion_cure_target_effect,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import (
    _fixture,
    _leaf,
)


def _confusion_row(owner, provenance, *, duration=3, prior=0):
    return {
        "schema_version": "champions-confusion-progression-v1",
        "owner": deepcopy(owner),
        "state": "confused",
        "origin_id": "persim:confusion:1",
        "established_turn": 1,
        "prior_opportunities": prior,
        "duration": duration,
        "confusion_observation": deepcopy(provenance),
        "observed_turn": 1,
        "provenance": "observed_champions_confusion_progression_v1",
    }


def _case(
    *,
    confusion="confused",
    target_ability="pressure",
    source_ability="pressure",
    progression=True,
    stale_progression=False,
    hit_state="hit",
    damage=20,
    routing="target",
    hp=80,
    ko=False,
):
    state, _snapshot, _d0, _actor, _target, _execution = _fixture(
        item="persim-berry",
        source_ability=source_ability,
        target_ability=target_ability,
    )
    own = state["self_side"]["pokemon"][0]
    foe = state["opponent_side"]["pokemon"][0]
    target_owner = {
        "session_id": state["session_id"],
        "side": "opponent",
        "slot_index": 0,
        "pokemon_id": foe["pokemon_id"],
    }
    if confusion == "unknown":
        foe["current_confusion"] = "unknown"
        foe.pop("confusion_provenance", None)
        foe["champions_confusion_progression"] = None
    else:
        prov = {
            "event_kind": "current_confusion_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "state": confusion,
        }
        foe["current_confusion"] = confusion
        foe["confusion_provenance"] = deepcopy(prov)
        if confusion == "confused" and progression:
            row = _confusion_row(target_owner, prov)
            if stale_progression:
                row["confusion_observation"] = {**prov, "turn_number": 0}
            foe["champions_confusion_progression"] = row
        else:
            foe["champions_confusion_progression"] = None
    own["current_confusion"] = "none"
    own["confusion_provenance"] = {
        "event_kind": "current_confusion_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "state": "none",
    }
    own["champions_confusion_progression"] = None
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
        "pokemon_id": own["pokemon_id"],
    }
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
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
    authority = freeze_runtime_d0_fling_persim_confusion_cure_target_effect_authority(
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
        "actor": actor, "target": target, "action": action,
        "execution": execution, "leaf": leaf,
        "interaction": interaction, "authority": authority,
    }


def test_confused_pressure_applies_typed_confusion_cure_and_retires_progression():
    case = _case()
    authority = case["authority"]
    assert authority["status"] == "resolved"
    assert authority["outcome"] == "applied_confusion_cure"
    assert authority["confusion_before"] == "confused"
    assert authority["confusion_after"] == "none"
    assert authority["confusion_progression_before"]["state"] == "confused"
    assert authority["confusion_progression_after"] is None
    detached = materialize_detached_fling_persim_confusion_cure_target_effect(
        authority=authority,
    )
    removal = detached["hypothetical_target_confusion_removal"]
    assert removal["schema_version"] == "detached-hypothetical-target-confusion-removal-v1"
    assert removal["confusion_before"] == "confused"
    assert removal["confusion_after"] == "none"
    assert removal["confusion_progression_after"] is None


def test_not_confused_pressure_is_exact_none_to_none_without_false_removal():
    case = _case(confusion="none", progression=False)
    authority = case["authority"]
    assert authority["status"] == "resolved"
    assert authority["outcome"] == "no_transition_not_confused"
    assert authority["confusion_before"] == authority["confusion_after"] == "none"
    detached = materialize_detached_fling_persim_confusion_cure_target_effect(
        authority=authority,
    )
    assert detached["status"] == "resolved"
    assert "hypothetical_target_confusion_removal" not in detached
    assert detached["confusion_progression_before"] is None
    assert detached["confusion_progression_after"] is None


def test_unknown_confusion_fails_closed():
    case = _case(confusion="unknown", progression=False)
    assert case["authority"]["status"] == "incomplete"
    assert case["authority"]["reason"] == "fling_persim_target_confusion_unknown"


def test_confused_state_requires_exact_current_progression():
    missing = _case(progression=False)
    assert missing["authority"]["status"] == "incomplete"
    assert missing["authority"]["reason"] == "fling_persim_confusion_progression_missing"
    stale = _case(stale_progression=True)
    assert stale["authority"]["status"] == "rejected"
    assert stale["authority"]["reason"] == "fling_persim_confusion_progression_stale"


@pytest.mark.parametrize("ability", ["cheek-pouch", "ripen", "cud-chew"])
def test_direct_target_eat_item_hooks_remain_incomplete(ability):
    case = _case(target_ability=ability)
    assert case["interaction"]["status"] == "resolved"
    assert case["interaction"]["ability_consequence_materialization"] == "deferred"
    assert case["authority"]["status"] == "incomplete"
    assert case["authority"]["reason"] == "fling_berry_direct_target_eat_item_consequence_deferred"


def test_neutralizing_gas_unresolved_composition_remains_incomplete_and_pressure_is_ready():
    gas = _case(source_ability="neutralizing-gas", target_ability="cheek-pouch")
    assert gas["interaction"]["status"] == "incomplete"
    assert gas["authority"]["status"] == "incomplete"
    pressure = _case()
    assert pressure["interaction"]["status"] == "resolved"
    assert pressure["authority"]["status"] == "resolved"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hit_state": "miss"},
        {"damage": 0},
        {"routing": "substitute"},
        {"hp": 0, "ko": True},
    ],
)
def test_no_eat_boundaries_are_not_applicable_and_create_no_ateberry(kwargs):
    case = _case(**kwargs)
    assert case["interaction"]["status"] == "resolved"
    assert case["interaction"]["outcome"] == "post_hit_target_eat_not_reached"
    assert case["authority"]["status"] == "resolved"
    assert case["authority"]["outcome"] == "not_applicable"
    assert materialize_detached_fling_persim_confusion_cure_target_effect(
        authority=case["authority"],
    )["status"] == "rejected"
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "not_applicable"


def test_successful_persim_eat_sets_ateberry_true_and_true_to_true_is_idempotent():
    case = _case(confusion="none", progression=False)
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "resolved"
    assert eaten["resulting_state"] == "known_true"

    d0 = deepcopy(case["d0"])
    d0["current_berry_eaten_authority"]["opponent"] = {
        "status": "resolved",
        "schema_version": "runtime-d0-current-berry-eaten-authority-v1",
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "owner": deepcopy(case["target"]),
        "state": "known_true",
        "value": True,
        "state_provenance": {"basis": "observed_berry_consumption"},
    }
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=d0,
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "resolved"
    assert eaten["prior_state"] == "known_true"
    assert eaten["resulting_state"] == "known_true"
    assert eaten["transition"] == "true_to_true"


def test_authority_rejects_forged_action_leaf_item_and_target_bindings():
    case = _case()
    for kind in ("execution_item", "interaction_target", "leaf_action"):
        execution = deepcopy(case["execution"])
        interaction = deepcopy(case["interaction"])
        leaf = deepcopy(case["leaf"])
        if kind == "execution_item":
            execution["user_item_before"]["value"] = "lum-berry"
        elif kind == "interaction_target":
            interaction["target"] = deepcopy(case["actor"])
        else:
            leaf["candidate_id"] = "attack:foreign"
        result = freeze_runtime_d0_fling_persim_confusion_cure_target_effect_authority(
            strategy_d0=case["d0"],
            runtime_snapshot=case["snapshot"],
            fling_execution_authority=execution,
            source_leaf=leaf,
            berry_eat_item_interaction_authority=interaction,
            actor=case["actor"],
            target=case["target"],
        )
        assert result["status"] == "rejected"


def test_target_effect_reasoning_does_not_mutate_runtime_or_d0():
    case = _case()
    snapshot_before = deepcopy(case["snapshot"])
    d0_before = deepcopy(case["d0"])
    detached = materialize_detached_fling_persim_confusion_cure_target_effect(
        authority=case["authority"],
    )
    assert detached["status"] == "resolved"
    assert case["snapshot"] == snapshot_before
    assert case["d0"] == d0_before
