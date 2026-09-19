from copy import deepcopy

import pytest

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_detached_berry_eaten_transition import (
    materialize_detached_fling_berry_eaten_transition,
)
from llm.advisor_detached_predictive_intermediate_state import (
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_detached_target_condition_removal_validation import (
    validate_detached_target_condition_removal,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
)
from llm.advisor_runtime_d0_fling_item_execution_authority import (
    freeze_runtime_d0_fling_item_execution_authority,
)
from llm.advisor_runtime_d0_fling_lum_major_status_confusion_cure_target_effect_authority import (
    freeze_runtime_d0_fling_lum_major_status_confusion_cure_target_effect_authority,
    materialize_detached_fling_lum_major_status_confusion_cure_target_effect,
    validate_detached_fling_lum_major_status_confusion_cure_target_effect,
    validate_detached_lum_confusion_removal,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import (
    _fixture,
    _leaf,
)


def _confusion_row(owner, provenance):
    return {
        "schema_version": "champions-confusion-progression-v1",
        "owner": deepcopy(owner),
        "state": "confused",
        "origin_id": "lum:confusion:1",
        "established_turn": 1,
        "prior_opportunities": 0,
        "duration": 3,
        "confusion_observation": deepcopy(provenance),
        "observed_turn": 1,
        "provenance": "observed_champions_confusion_progression_v1",
    }


def lum_case(
    *,
    condition="none",
    confusion="none",
    condition_known=True,
    confusion_known=True,
    progression=True,
    stale_progression=False,
    target_ability="pressure",
    source_ability="pressure",
    hit_state="hit",
    damage=20,
    routing="target",
    hp=80,
    ko=False,
):
    state, _snapshot, _d0, _actor, _target, _execution = _fixture(
        item="lum-berry",
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

    foe["condition"] = None if condition == "none" else condition
    if condition_known:
        foe["condition_provenance"] = {
            "event_kind": "current_condition_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "condition": condition,
        }
    else:
        foe.pop("condition_provenance", None)

    if not confusion_known:
        foe["current_confusion"] = "unknown"
        foe.pop("confusion_provenance", None)
        foe["champions_confusion_progression"] = None
    else:
        conf_prov = {
            "event_kind": "current_confusion_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "state": confusion,
        }
        foe["current_confusion"] = confusion
        foe["confusion_provenance"] = deepcopy(conf_prov)
        if confusion == "confused" and progression:
            row = _confusion_row(target_owner, conf_prov)
            if stale_progression:
                row["confusion_observation"] = {**conf_prov, "turn_number": 0}
            foe["champions_confusion_progression"] = row
        else:
            foe["champions_confusion_progression"] = None

    own["condition"] = None
    own["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "condition": "none",
    }
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
    authority = freeze_runtime_d0_fling_lum_major_status_confusion_cure_target_effect_authority(
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


@pytest.mark.parametrize("condition", ["burn", "poison", "toxic", "paralysis", "sleep", "freeze"])
def test_all_six_major_conditions_cure_to_none(condition):
    case = lum_case(condition=condition)
    authority = case["authority"]
    assert authority["status"] == "resolved"
    assert authority["outcome"] == "applied_major_status_cure"
    assert authority["condition_before"] == condition
    assert authority["condition_after"] == "none"
    assert authority["confusion_before"] == authority["confusion_after"] == "none"
    detached = materialize_detached_fling_lum_major_status_confusion_cure_target_effect(
        authority=authority,
    )
    marker = detached["hypothetical_target_condition_removal"]
    assert validate_detached_target_condition_removal(
        marker,
        source_leaf_id=case["leaf"]["leaf_id"],
        source_leaf=case["leaf"],
        expected_target=case["target"],
    )
    assert "hypothetical_target_confusion_removal" not in detached


def test_confusion_only_cures_and_retires_progression():
    case = lum_case(confusion="confused")
    authority = case["authority"]
    assert authority["status"] == "resolved"
    assert authority["outcome"] == "applied_confusion_cure"
    assert authority["condition_before"] == authority["condition_after"] == "none"
    assert authority["confusion_before"] == "confused"
    assert authority["confusion_after"] == "none"
    assert authority["confusion_progression_before"]["state"] == "confused"
    assert authority["confusion_progression_after"] is None
    detached = materialize_detached_fling_lum_major_status_confusion_cure_target_effect(
        authority=authority,
    )
    marker = detached["hypothetical_target_confusion_removal"]
    assert validate_detached_lum_confusion_removal(
        marker, source_leaf=case["leaf"], expected_target=case["target"],
    )
    assert "hypothetical_target_condition_removal" not in detached


@pytest.mark.parametrize("condition", ["sleep", "freeze", "paralysis", "toxic"])
def test_simultaneous_major_status_and_confusion_cure_is_atomic(condition):
    case = lum_case(condition=condition, confusion="confused")
    authority = case["authority"]
    assert authority["status"] == "resolved"
    assert authority["outcome"] == "applied_major_status_and_confusion_cure"
    assert authority["condition_before"] == condition
    assert authority["condition_after"] == "none"
    assert authority["confusion_before"] == "confused"
    assert authority["confusion_after"] == "none"
    assert authority["confusion_progression_after"] is None
    detached = materialize_detached_fling_lum_major_status_confusion_cure_target_effect(
        authority=authority,
    )
    assert "hypothetical_target_condition_removal" in detached
    assert "hypothetical_target_confusion_removal" in detached
    assert validate_detached_fling_lum_major_status_confusion_cure_target_effect(
        consequence=detached, source_leaf=case["leaf"], expected_target=case["target"],
    )


def test_healthy_target_is_exact_no_transition_but_successful_eat_sets_ateberry():
    case = lum_case()
    authority = case["authority"]
    assert authority["status"] == "resolved"
    assert authority["outcome"] == "no_transition_no_curable_state"
    detached = materialize_detached_fling_lum_major_status_confusion_cure_target_effect(
        authority=authority,
    )
    assert "hypothetical_target_condition_removal" not in detached
    assert "hypothetical_target_confusion_removal" not in detached
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "resolved"
    assert eaten["resulting_state"] == "known_true"


def test_healthy_true_to_true_ateberry_is_idempotent():
    case = lum_case()
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
    assert eaten["transition"] == "true_to_true"


def test_unknown_condition_or_confusion_fails_closed_without_partial_atomic_claim():
    unknown_condition = lum_case(condition="burn", condition_known=False)
    assert unknown_condition["authority"]["status"] == "incomplete"
    assert unknown_condition["authority"]["reason"] == "fling_lum_target_condition_unknown"
    unknown_confusion = lum_case(condition="burn", confusion_known=False)
    assert unknown_confusion["authority"]["status"] == "incomplete"
    assert unknown_confusion["authority"]["reason"] == "fling_lum_target_confusion_unknown"


def test_confused_requires_current_bound_progression():
    missing = lum_case(confusion="confused", progression=False)
    assert missing["authority"]["status"] == "incomplete"
    assert missing["authority"]["reason"] == "fling_lum_confusion_progression_missing"
    stale = lum_case(confusion="confused", stale_progression=True)
    assert stale["authority"]["status"] == "rejected"
    assert stale["authority"]["reason"] == "fling_lum_confusion_progression_stale"


@pytest.mark.parametrize("ability", ["cheek-pouch", "ripen", "cud-chew"])
def test_deferred_direct_target_eatitem_hooks_keep_lum_incomplete(ability):
    case = lum_case(target_ability=ability)
    assert case["interaction"]["status"] == "resolved"
    assert case["authority"]["status"] == "incomplete"
    assert case["authority"]["reason"] == "fling_berry_direct_target_eat_item_consequence_deferred"


def test_pressure_is_ready_and_neutralizing_gas_unresolved_composition_is_incomplete():
    pressure = lum_case()
    assert pressure["authority"]["status"] == "resolved"
    gas = lum_case(source_ability="neutralizing-gas", target_ability="cheek-pouch")
    assert gas["interaction"]["status"] == "incomplete"
    assert gas["authority"]["status"] == "incomplete"


@pytest.mark.parametrize(
    ("label", "kwargs"),
    [
        ("miss", {"hit_state": "miss"}),
        ("protect_or_zero_damage", {"damage": 0}),
        ("immunity_no_damage", {"damage": 0}),
        ("substitute", {"routing": "substitute"}),
        ("ko_before_eat", {"hp": 0, "ko": True}),
    ],
)
def test_no_eat_boundaries_have_no_lum_transition_or_ateberry(label, kwargs):
    case = lum_case(condition="toxic", confusion="confused", **kwargs)
    assert case["interaction"]["status"] == "resolved", label
    assert case["interaction"]["outcome"] == "post_hit_target_eat_not_reached", label
    assert case["authority"]["status"] == "resolved", label
    assert case["authority"]["outcome"] == "not_applicable", label
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert eaten["status"] == "not_applicable"


def test_detached_projection_clears_both_dimensions_without_mutating_runtime_or_d0():
    case = lum_case(condition="toxic", confusion="confused")
    snapshot_before, d0_before = deepcopy(case["snapshot"]), deepcopy(case["d0"])
    terminal = deepcopy(case["leaf"])
    terminal["consequences"]["fling_lum_major_status_confusion_cure_target_effect"] = (
        materialize_detached_fling_lum_major_status_confusion_cure_target_effect(
            authority=case["authority"],
        )
    )
    intermediate = materialize_detached_predictive_intermediate_state(
        strategy_d0=case["d0"], terminal_leaf=terminal,
    )
    assert intermediate["status"] == "resolved"
    row = intermediate["active"]["opponent"]
    assert row["hypothetical_condition"]["status"] == "known_none"
    assert row["hypothetical_confusion"]["status"] == "known_none"
    assert row["hypothetical_confusion"]["current_confusion"] == "none"
    assert row["hypothetical_confusion"]["champions_confusion_progression"] is None
    assert case["snapshot"] == snapshot_before
    assert case["d0"] == d0_before


def test_atomic_validator_rejects_partial_or_forged_markers():
    case = lum_case(condition="toxic", confusion="confused")
    detached = materialize_detached_fling_lum_major_status_confusion_cure_target_effect(
        authority=case["authority"],
    )
    variants = []
    no_condition = deepcopy(detached)
    no_condition.pop("hypothetical_target_condition_removal")
    variants.append(no_condition)
    no_confusion = deepcopy(detached)
    no_confusion.pop("hypothetical_target_confusion_removal")
    variants.append(no_confusion)
    stale_confusion = deepcopy(detached)
    stale_confusion["hypothetical_target_confusion_removal"]["confusion_progression_after"] = {
        "state": "confused"
    }
    variants.append(stale_confusion)
    forged_eat = deepcopy(detached)
    forged_eat["authority"]["berry_eat_item_interaction_authority"]["target"] = deepcopy(case["actor"])
    variants.append(forged_eat)
    for forged in variants:
        assert not validate_detached_fling_lum_major_status_confusion_cure_target_effect(
            consequence=forged,
            source_leaf=case["leaf"],
            expected_target=case["target"],
        )


def test_stale_foreign_action_target_and_item_bindings_reject():
    case = lum_case()
    stale_snapshot = deepcopy(case["snapshot"])
    stale_snapshot["state"]["turn_number"] = 99
    stale_snapshot["state_fingerprint"] = state_fingerprint(stale_snapshot["state"])
    stale = freeze_runtime_d0_fling_lum_major_status_confusion_cure_target_effect_authority(
        strategy_d0=case["d0"], runtime_snapshot=stale_snapshot,
        fling_execution_authority=case["execution"], source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=case["interaction"],
        actor=case["actor"], target=case["target"],
    )
    assert stale["status"] == "rejected"

    for kind in ("item", "leaf_action", "target"):
        execution = deepcopy(case["execution"])
        leaf = deepcopy(case["leaf"])
        interaction = deepcopy(case["interaction"])
        target = deepcopy(case["target"])
        if kind == "item":
            execution["user_item_before"]["value"] = "persim-berry"
        elif kind == "leaf_action":
            leaf["candidate_id"] = "attack:foreign"
        else:
            target["pokemon_id"] = "foreign"
        result = freeze_runtime_d0_fling_lum_major_status_confusion_cure_target_effect_authority(
            strategy_d0=case["d0"], runtime_snapshot=case["snapshot"],
            fling_execution_authority=execution, source_leaf=leaf,
            berry_eat_item_interaction_authority=interaction,
            actor=case["actor"], target=target,
        )
        assert result["status"] == "rejected"
