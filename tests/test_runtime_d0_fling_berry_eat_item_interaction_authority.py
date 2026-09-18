from copy import deepcopy

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
)
from llm.advisor_runtime_d0_fling_item_execution_authority import (
    freeze_runtime_d0_fling_item_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _inputs


def _fixture(*, item="cheri-berry", source_ability="pressure", target_ability="pressure"):
    state, _snapshot, _d0, _own, _responses, _orders = _inputs()
    own = state["self_side"]["pokemon"][0]
    foe = state["opponent_side"]["pokemon"][0]
    own["known_item"] = item
    own["known_item_provenance"] = {
        "event_kind": "current_item_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "status": "known", "source_observation_id": "berry-item", "source_sequence": 1,
    }
    for row, ability, label in ((own, source_ability, "source"), (foe, target_ability, "target")):
        if ability is None:
            row["current_ability"] = {"knowledge": "unknown"}
            row.pop("current_ability_provenance", None)
        else:
            row["current_ability"] = ability
            row["current_ability_provenance"] = {
                "event_kind": "current_ability_observed", "trust": "user_confirmed_observation",
                "turn_number": 1, "source_observation_id": f"{label}-ability", "source_sequence": 1,
            }
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation",
        "source_observation_id": "mr", "source_sequence": 1,
    }
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }
    owner = {
        "session_id": state["session_id"], "side": "self", "slot_index": 0,
        "pokemon_id": own["pokemon_id"],
    }
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    actor = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    metadata = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
    action = {
        "action_id": "attack:fling", "action_type": "attack", "identity": "fling",
        "move_metadata_authority": {"status": "resolved", "metadata": metadata},
    }
    execution = freeze_runtime_d0_fling_item_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
    )
    return state, snapshot, d0, actor, target, execution


def _leaf(d0, actor, target, execution, *, hit_state="hit", damage=20, routing="target", hp=80, ko=False):
    return {
        "leaf_id": "fling:leaf",
        "candidate_id": execution["action_id"],
        "action_type": "attack",
        "branch_path": ("hit",),
        "probability": {"numerator": 1, "denominator": 1},
        "hit_state": hit_state,
        "critical_state": "non_critical",
        "damage_roll": 0,
        "consequences": {
            "source_hit_context": {
                "source_action_id": execution["action_id"],
                "source_move_id": "fling",
                "target_routing": routing,
                "actual_damage": damage,
            },
            "own_final_hp": 100,
            "target_final_hp": hp,
            "target_ko": ko,
        },
        "provenance": {
            "session_id": d0["session_id"],
            "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
            "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
            "decision_owner": deepcopy(d0["decision_owner"]),
            "attacker": deepcopy(actor),
            "target": deepcopy(target),
            "move_id": "fling",
            "fling_execution_authority": deepcopy(execution),
        },
    }


def _freeze(snapshot, d0, actor, target, execution, phase, source_leaf=None):
    return freeze_runtime_d0_fling_berry_eat_item_interaction_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        fling_execution_authority=execution,
        actor=actor,
        target=target,
        phase=phase,
        source_leaf=source_leaf,
    )


def test_binding_rejects_non_berry_wrong_item_foreign_owner_and_stale_runtime():
    _state, snapshot, d0, actor, target, execution = _fixture(item="light-ball")
    nonberry = _freeze(snapshot, d0, actor, target, execution, "pre_hit_source_berry_interaction")
    assert nonberry["status"] == "rejected"
    assert nonberry["reason"] == "fling_item_not_berry_effect"

    _state, snapshot, d0, actor, target, execution = _fixture()
    forged = deepcopy(execution)
    forged["user_item_before"]["value"] = "aspear-berry"
    wrong = _freeze(snapshot, d0, actor, target, forged, "pre_hit_source_berry_interaction")
    assert wrong["status"] == "rejected"

    foreign = deepcopy(execution)
    foreign["source_branch_fingerprint"] = "foreign"
    assert _freeze(snapshot, d0, actor, target, foreign, "pre_hit_source_berry_interaction")["status"] == "rejected"

    assert _freeze(snapshot, d0, target, actor, execution, "pre_hit_source_berry_interaction")["status"] == "rejected"

    stale = deepcopy(snapshot)
    stale["state_fingerprint"] = "stale"
    assert _freeze(stale, d0, actor, target, execution, "pre_hit_source_berry_interaction")["status"] == "rejected"


def test_runtime_and_d0_are_immutable():
    _state, snapshot, d0, actor, target, execution = _fixture(source_ability="cud-chew")
    before_snapshot, before_d0 = deepcopy(snapshot), deepcopy(d0)
    result = _freeze(snapshot, d0, actor, target, execution, "pre_hit_source_berry_interaction")
    assert result["status"] == "resolved"
    assert snapshot == before_snapshot
    assert d0 == before_d0


def test_source_cud_chew_is_exact_pre_hit_and_does_not_depend_on_target_hit():
    _state, snapshot, d0, actor, target, execution = _fixture(source_ability="cud-chew")
    result = _freeze(snapshot, d0, actor, target, execution, "pre_hit_source_berry_interaction")
    assert result["status"] == "resolved"
    assert result["outcome"] == "pre_hit_source_cud_chew_eat_item_dispatched"
    assert result["source_cud_chew_dispatch"] is True
    assert result["target_hit_required"] is False
    assert result["future_cud_chew_lifecycle"] == "deferred"
    assert result["intrinsic_berry_effect"] == "deferred"

    miss = _leaf(d0, actor, target, execution, hit_state="miss")
    blocked = _leaf(d0, actor, target, execution, damage=0)
    assert _freeze(snapshot, d0, actor, target, execution, "pre_hit_source_berry_interaction", miss) == result
    assert _freeze(snapshot, d0, actor, target, execution, "pre_hit_source_berry_interaction", blocked) == result


def test_known_non_cud_chew_skips_source_branch_and_unknown_source_fails_closed():
    _state, snapshot, d0, actor, target, execution = _fixture(source_ability="pressure")
    result = _freeze(snapshot, d0, actor, target, execution, "pre_hit_source_berry_interaction")
    assert result["status"] == "resolved"
    assert result["outcome"] == "pre_hit_source_no_cud_chew_dispatch"
    assert result["source_cud_chew_dispatch"] is False

    _state, snapshot, d0, actor, target, execution = _fixture(source_ability=None)
    result = _freeze(snapshot, d0, actor, target, execution, "pre_hit_source_berry_interaction")
    assert result["status"] == "incomplete"
    assert result["reason"] == "fling_berry_source_ability_unknown"


def test_source_cud_chew_neutralizing_gas_composition_fails_closed():
    _state, snapshot, d0, actor, target, execution = _fixture(
        source_ability="cud-chew", target_ability="neutralizing-gas",
    )
    result = _freeze(snapshot, d0, actor, target, execution, "pre_hit_source_berry_interaction")
    assert result["status"] == "incomplete"
    assert result["reason"] == "fling_berry_source_cud_chew_neutralizing_gas_composition_unresolved"


def test_successful_target_hit_authenticates_direct_eat_then_eat_item_without_intrinsic_effect():
    _state, snapshot, d0, actor, target, execution = _fixture()
    leaf = _leaf(d0, actor, target, execution)
    result = _freeze(snapshot, d0, actor, target, execution, "post_hit_target_berry_interaction", leaf)
    assert result["status"] == "resolved"
    assert result["outcome"] == "post_hit_target_eat_item_dispatched"
    assert result["target_eat_occurred"] is True
    assert result["target_eat_item_dispatched"] is True
    assert result["ordinary_held_berry_trigger_used"] is False
    assert result["target_ability_interaction"] == "not_applicable"
    assert result["intrinsic_berry_effect"] == "deferred"
    forbidden = {
        "hypothetical_target_condition", "hypothetical_target_condition_removal",
        "heal_amount", "final_hp", "restored_pp",
    }
    assert forbidden.isdisjoint(result)


def test_target_eat_is_not_reached_for_current_exact_no_target_boundaries():
    _state, snapshot, d0, actor, target, execution = _fixture()
    cases = [
        (_leaf(d0, actor, target, execution, hit_state="miss"), "fling_miss_or_pre_execution_cancellation"),
        (_leaf(d0, actor, target, execution, damage=0), "fling_protect_or_immunity_or_no_damage"),
        (_leaf(d0, actor, target, execution, routing="substitute"), "fling_target_effect_substitute_or_non_target_route"),
        (_leaf(d0, actor, target, execution, hp=0, ko=True), "fling_target_fainted_before_effect"),
    ]
    for leaf, reason in cases:
        result = _freeze(snapshot, d0, actor, target, execution, "post_hit_target_berry_interaction", leaf)
        assert result["status"] == "resolved"
        assert result["outcome"] == "post_hit_target_eat_not_reached"
        assert result["reason"] == reason
        assert result["target_eat_occurred"] is False
        assert result["target_eat_item_dispatched"] is False


def test_target_cheek_pouch_ripen_and_cud_chew_hooks_are_classified_but_effects_deferred():
    for ability, expected_role in (
        ("cheek-pouch", "target_post_eat_item_consequence"),
        ("ripen", "berry_heal_modifier"),
        ("cud-chew", "target_post_eat_item_delayed_reuse"),
    ):
        _state, snapshot, d0, actor, target, execution = _fixture(target_ability=ability)
        result = _freeze(
            snapshot, d0, actor, target, execution,
            "post_hit_target_berry_interaction",
            _leaf(d0, actor, target, execution),
        )
        assert result["status"] == "resolved"
        assert result["target_ability_interaction"] == "applies"
        assert expected_role in result["target_ability_classification"]["classification"]["roles"]
        assert result["ability_consequence_materialization"] == "deferred"
        assert result["intrinsic_berry_effect"] == "deferred"


def test_unnerve_try_eat_blocker_is_explicitly_bypassed_by_fling_direct_eat():
    _state, snapshot, d0, actor, target, execution = _fixture(
        source_ability="unnerve", target_ability="pressure",
    )
    result = _freeze(
        snapshot, d0, actor, target, execution,
        "post_hit_target_berry_interaction",
        _leaf(d0, actor, target, execution),
    )
    assert result["status"] == "resolved"
    assert result["opposing_try_eat_blocker_bypassed"] is True
    source = result["source_ability_classification"]["classification"]
    assert source["try_eat_only"] is True
    assert source["fling_direct_eat_path"] == "try_eat_hook_not_invoked_by_fling_direct_eat"


def test_klutz_target_has_no_direct_eat_item_hook_and_neutralizing_gas_direct_hook_composition_is_unresolved():
    _state, snapshot, d0, actor, target, execution = _fixture(target_ability="klutz")
    result = _freeze(
        snapshot, d0, actor, target, execution,
        "post_hit_target_berry_interaction",
        _leaf(d0, actor, target, execution),
    )
    assert result["status"] == "resolved"
    assert result["target_ability_interaction"] == "not_applicable"
    assert result["target_ability_classification"]["classification"]["roles"] == [
        "source_item_suppression_external_to_eat_event"
    ]

    _state, snapshot, d0, actor, target, execution = _fixture(
        source_ability="neutralizing-gas", target_ability="cheek-pouch",
    )
    result = _freeze(
        snapshot, d0, actor, target, execution,
        "post_hit_target_berry_interaction",
        _leaf(d0, actor, target, execution),
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "fling_berry_target_eat_item_neutralizing_gas_composition_unresolved"
    assert result["target_eat_occurred"] is True
    assert result["target_eat_item_dispatched"] is True


def test_unknown_or_unproven_target_ability_fails_closed():
    _state, snapshot, d0, actor, target, execution = _fixture(target_ability=None)
    result = _freeze(
        snapshot, d0, actor, target, execution,
        "post_hit_target_berry_interaction",
        _leaf(d0, actor, target, execution),
    )
    assert result["status"] == "incomplete"

    _state, snapshot, d0, actor, target, execution = _fixture(target_ability="not-a-real-ability")
    result = _freeze(
        snapshot, d0, actor, target, execution,
        "post_hit_target_berry_interaction",
        _leaf(d0, actor, target, execution),
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "fling_berry_target_ability_interaction_unclassified"


def test_source_leaf_foreign_execution_and_wrong_target_reject():
    _state, snapshot, d0, actor, target, execution = _fixture()
    leaf = _leaf(d0, actor, target, execution)
    leaf["provenance"]["fling_execution_authority"] = {**execution, "action_id": "foreign"}
    assert _freeze(snapshot, d0, actor, target, execution, "post_hit_target_berry_interaction", leaf)["status"] == "rejected"

    leaf = _leaf(d0, actor, target, execution)
    leaf["provenance"]["target"] = actor
    assert _freeze(snapshot, d0, actor, target, execution, "post_hit_target_berry_interaction", leaf)["status"] == "rejected"
