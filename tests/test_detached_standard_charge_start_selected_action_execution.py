from __future__ import annotations

from copy import deepcopy

import pytest

from llm.advisor_champions_gated_selected_action_execution import (
    execute_gated_selected_action,
)
from llm.advisor_detached_selected_action_execution_result import (
    materialize_detached_selected_action_execution_result,
)
from llm.advisor_detached_standard_charge_start import (
    materialize_detached_standard_charge_start,
    validate_detached_standard_charge_start,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import (
    freeze_runtime_d0_standard_charge_start_readiness_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_action_order_authority import (
    _actions,
    _owner,
    _snapshot,
    _state,
)


SUPPORTED = ("sky-attack", "razor-wind", "freeze-shock", "ice-burn")


def _inputs(
    move_id: str = "sky-attack",
    *,
    item_mode: str = "absent",
    item: str | None = None,
    actor_ability: str = "static",
    target_ability: str = "static",
    magic_room: str = "inactive",
):
    state = _state()
    for side, hp in (("self", 87), ("opponent", 73)):
        row = state[f"{side}_side"]["pokemon"][0]
        row["current_hp"] = hp
        row["max_hp"] = 100
        row["fainted"] = False
    actor_raw = state["self_side"]["pokemon"][0]
    target_raw = state["opponent_side"]["pokemon"][0]
    if item_mode == "absent":
        actor_raw["known_item"] = None
        actor_raw["known_item_provenance"] = {
            "event_kind": "current_item_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "status": "known_absent",
        }
    elif item_mode == "known":
        assert isinstance(item, str)
        actor_raw["known_item"] = item
        actor_raw["known_item_provenance"] = {
            "event_kind": "current_item_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "status": "known",
        }
    else:
        raise AssertionError(item_mode)
    actor_raw["current_ability"] = actor_ability
    actor_raw["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    target_raw["current_ability"] = target_ability
    target_raw["current_ability_provenance"] = {
        "event_kind": "current_ability_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
    }
    state["field"]["magic_room_status"] = magic_room
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": "charge-start-magic-room",
        "source_sequence": 1,
    }
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot,
        decision_owner=_owner(state, "self"),
    )
    action, _ = _actions(d0, own_move=move_id)
    actor = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
    )
    return state, snapshot, d0, action, actor, target, readiness


@pytest.mark.parametrize("move_id", SUPPORTED)
def test_supported_standard_charge_moves_materialize_exact_charge_start(move_id):
    state, snapshot, d0, action, actor, target, readiness = _inputs(move_id)
    before_snapshot, before_d0 = deepcopy(snapshot), deepcopy(d0)
    result = materialize_detached_standard_charge_start(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        readiness_authority=readiness,
    )
    assert result["status"] == "resolved", result
    assert result["outcome"] == "charge_started"
    assert result["probability"] == {"numerator": 1, "denominator": 1}
    leaf = result["action_leaf"]
    assert leaf["leaf_id"] == f"{action['action_id']}:charge-start"
    assert leaf["candidate_id"] == action["action_id"]
    assert leaf["hit_state"] == "not_applicable"
    assert leaf["critical_hit_state"] == "not_applicable"
    assert leaf["damage_roll"] == "not_applicable"
    assert leaf["contact_state"] == "not_applicable"
    assert leaf["secondary_effect_state"] == "none"
    assert leaf["damage"] == 0
    assert leaf["consequences"]["actor_final_hp"] == 87
    assert leaf["consequences"]["target_final_hp"] == 73
    assert leaf["consequences"]["actor_ko"] is False
    assert leaf["consequences"]["target_ko"] is False
    context = result["detached_charge_lifecycle_context"]
    assert context["schema_version"] == "detached-standard-charge-lifecycle-context-v1"
    assert context["state"] == "charging"
    assert context["phase"] == "turn_one_charge_started"
    assert context["actor"] == actor
    assert context["source_target_owner"] == target
    assert context["continuation_target_locator"] == {
        "session_id": target["session_id"],
        "side": target["side"],
        "slot_index": target["slot_index"],
    }
    assert "pokemon_id" not in context["continuation_target_locator"]
    assert context["turn_two_continuation_required"] is True
    assert context["immediate_damage_executed"] is False
    assert context["charge_turn_damage"] == 0
    assert context["pp_consumption_materialized"] is False
    assert result["post_action_runtime_snapshot"]["state"] == snapshot["state"]
    assert result["post_action_runtime_snapshot"]["detached_standard_charge_lifecycle_context"] == context
    assert validate_detached_standard_charge_start(
        result=result,
        strategy_d0=d0,
        source_runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
    )
    assert snapshot == before_snapshot
    assert d0 == before_d0
    assert state["self_side"]["pokemon"][0]["current_hp"] == 87
    assert state["opponent_side"]["pokemon"][0]["current_hp"] == 73


def test_power_herb_active_readiness_bypasses_charge_start_materializer():
    _state0, snapshot, d0, action, actor, target, readiness = _inputs(
        "sky-attack",
        item_mode="known",
        item="power-herb",
        actor_ability="static",
        target_ability="static",
        magic_room="inactive",
    )
    assert readiness["status"] == "resolved"
    assert readiness["outcome"] == "power_herb_charge_skip_ready"
    assert readiness["next_semantic_phase"] == "current_turn_charge_skip_terminal_execution"
    result = materialize_detached_standard_charge_start(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        readiness_authority=readiness,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "standard_charge_start_readiness_semantics_invalid"


@pytest.mark.parametrize("move_id", ("solar-beam", "meteor-beam", "fly", "geomancy"))
def test_unsupported_charge_families_cannot_use_standard_charge_start(move_id):
    _state0, snapshot, d0, action, actor, target, readiness = _inputs(move_id)
    result = materialize_detached_standard_charge_start(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        readiness_authority=readiness,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "standard_charge_start_action_identity_invalid"


def test_stale_or_foreign_readiness_and_identity_reject():
    state, snapshot, d0, action, actor, target, readiness = _inputs("sky-attack")
    stale_state = deepcopy(state)
    stale_state["condition"] = stale_state.get("condition")
    stale_state["self_side"]["pokemon"][0]["condition"] = "burn"
    stale_state["self_side"]["pokemon"][0]["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 2,
        "condition": "burn",
    }
    branch_snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": stale_state["session_id"],
        "state": stale_state,
        "state_fingerprint": state_fingerprint(stale_state),
    }
    branch_d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=branch_snapshot,
        decision_owner=actor,
    )
    stale = materialize_detached_standard_charge_start(
        strategy_d0=branch_d0,
        runtime_snapshot=branch_snapshot,
        action=action,
        actor=actor,
        target=target,
        readiness_authority=readiness,
    )
    assert stale["status"] == "rejected"
    assert stale["reason"] == "standard_charge_start_readiness_binding_mismatch"

    foreign_action = deepcopy(action)
    foreign_action["action_id"] = "attack:foreign"
    assert materialize_detached_standard_charge_start(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=foreign_action,
        actor=actor,
        target=target,
        readiness_authority=readiness,
    )["status"] == "rejected"

    foreign_actor = deepcopy(actor)
    foreign_actor["pokemon_id"] = "foreign"
    assert materialize_detached_standard_charge_start(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=foreign_actor,
        target=target,
        readiness_authority=readiness,
    )["status"] == "rejected"

    foreign_target = deepcopy(target)
    foreign_target["pokemon_id"] = "foreign"
    assert materialize_detached_standard_charge_start(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=foreign_target,
        readiness_authority=readiness,
    )["status"] == "rejected"


def test_validator_rejects_forged_bindings_locator_damage_hp_probability_and_pp():
    _state0, snapshot, d0, action, actor, target, readiness = _inputs("sky-attack")
    valid = materialize_detached_standard_charge_start(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        readiness_authority=readiness,
    )
    assert valid["status"] == "resolved"

    def rejected(mutator):
        forged = deepcopy(valid)
        mutator(forged)
        assert not validate_detached_standard_charge_start(
            result=forged,
            strategy_d0=d0,
            source_runtime_snapshot=snapshot,
            action=action,
            actor=actor,
            target=target,
        )

    rejected(lambda x: x["detached_charge_lifecycle_context"].update(actor={"side": "foreign"}))
    rejected(lambda x: x["detached_charge_lifecycle_context"].update(action_id="foreign"))
    rejected(lambda x: x["detached_charge_lifecycle_context"].update(move_id="razor-wind"))
    rejected(lambda x: x["detached_charge_lifecycle_context"].update(source_target_owner=actor))
    rejected(lambda x: x["detached_charge_lifecycle_context"]["continuation_target_locator"].update(pokemon_id="frozen-victim"))
    rejected(lambda x: x["detached_charge_lifecycle_context"].update(source_runtime_fingerprint="forged"))
    rejected(lambda x: x["detached_charge_lifecycle_context"].update(source_branch_fingerprint="forged"))
    rejected(lambda x: x["detached_charge_lifecycle_context"].update(readiness_authority={"status": "resolved"}))
    rejected(lambda x: x["detached_charge_lifecycle_context"].update(canonical_lifecycle_family="weather_sensitive_charge_then_damage"))
    rejected(lambda x: x.update(probability={"numerator": 1, "denominator": 2}))
    rejected(lambda x: x["action_leaf"].update(damage=1))
    rejected(lambda x: x["action_leaf"]["consequences"].update(actor_final_hp=86))
    rejected(lambda x: x["action_leaf"]["provenance"].update(immediate_damage_execution_grant=True))
    rejected(lambda x: x["detached_charge_lifecycle_context"]["power_herb_applicability_state"].update(status="active"))
    rejected(lambda x: x["detached_charge_lifecycle_context"].update(pp_consumption_materialized=True))


def test_selected_action_executor_uses_charge_family_and_never_attack_ledger(monkeypatch):
    import llm.advisor_immediate_move_vs_move_action_pair as pair_module

    def forbidden(*args, **kwargs):
        raise AssertionError("_attack_ledger must not run for charge start")

    monkeypatch.setattr(pair_module, "_attack_ledger", forbidden)
    _state0, snapshot, d0, action, actor, target, readiness = _inputs("sky-attack")
    result = materialize_detached_selected_action_execution_result(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata=action["move_metadata_authority"]["metadata"],
        family_authorities={
            "standard_charge_start_readiness_authority": readiness,
        },
    )
    assert result["status"] == "resolved", result
    assert result["execution_family"] == "standard_charge_start"
    assert len(result["paths"]) == 1
    assert result["paths"][0]["probability"] == {"numerator": 1, "denominator": 1}
    assert result["paths"][0]["action_leaf"]["damage"] == 0
    assert result["paths"][0]["detached_charge_lifecycle_context"]["state"] == "charging"

    missing = materialize_detached_selected_action_execution_result(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata=action["move_metadata_authority"]["metadata"],
    )
    assert missing["status"] == "incomplete"
    assert missing["reason"] == "standard_charge_start_readiness_authority_missing"


def test_gated_selected_action_refreezes_readiness_on_exact_branch_and_ignores_root_authority():
    state, snapshot, d0, action, actor, target, root_readiness = _inputs("sky-attack")
    branch_state = deepcopy(state)
    branch_state["self_side"]["pokemon"][0]["condition"] = "burn"
    branch_state["self_side"]["pokemon"][0]["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 2,
        "condition": "burn",
    }
    branch_snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": branch_state["session_id"],
        "state": branch_state,
        "state_fingerprint": state_fingerprint(branch_state),
    }
    branch_d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=branch_snapshot,
        decision_owner=actor,
    )
    assert branch_d0["source_runtime_fingerprint"] != d0["source_runtime_fingerprint"]

    result = execute_gated_selected_action(
        strategy_d0=branch_d0,
        runtime_snapshot=branch_snapshot,
        action=action,
        actor=actor,
        target=target,
        metadata_authority=action["move_metadata_authority"],
        extension_authorities={
            "standard_charge_start_readiness_authority": root_readiness,
        },
    )
    assert result["status"] == "resolved", result
    selected = result["execution_result"]
    assert selected["execution_family"] == "standard_charge_start"
    context = selected["paths"][0]["detached_charge_lifecycle_context"]
    rebound = context["readiness_authority"]
    assert rebound["source_runtime_fingerprint"] == branch_d0["source_runtime_fingerprint"]
    assert rebound["source_branch_fingerprint"] == branch_d0["strategy_preview_fingerprint"]
    assert rebound["source_runtime_fingerprint"] != root_readiness["source_runtime_fingerprint"]
    assert context["state"] == "charging"
    assert result["paths"][0]["final_hp"] == {"self": 87, "opponent": 73}


def test_actor_fainted_or_target_no_longer_current_rejects_structurally():
    state, snapshot, d0, action, actor, target, readiness = _inputs("sky-attack")

    fainted_state = deepcopy(state)
    row = fainted_state["self_side"]["pokemon"][0]
    row["current_hp"] = 0
    row["fainted"] = True
    fainted_snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": fainted_state,
        "state_fingerprint": state_fingerprint(fainted_state),
    }
    fainted_d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=fainted_snapshot,
        decision_owner=actor,
    )
    rebound_action, _ = _actions(fainted_d0, own_move="sky-attack")
    rebound_readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=fainted_d0,
        runtime_snapshot=fainted_snapshot,
        action=rebound_action,
        actor=actor,
        target=target,
    )
    result = materialize_detached_standard_charge_start(
        strategy_d0=fainted_d0,
        runtime_snapshot=fainted_snapshot,
        action=rebound_action,
        actor=actor,
        target=target,
        readiness_authority=rebound_readiness,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "standard_charge_actor_already_fainted"

    target_state = deepcopy(state)
    target_state["opponent_side"]["pokemon"][0]["pokemon_id"] = "replacement"
    target_snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": target_state,
        "state_fingerprint": state_fingerprint(target_state),
    }
    target_d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=target_snapshot,
        decision_owner=actor,
    )
    assert target_d0["active_owners"]["opponent"]["pokemon_id"] == "replacement"
    stale_target_result = materialize_detached_standard_charge_start(
        strategy_d0=target_d0,
        runtime_snapshot=target_snapshot,
        action=action,
        actor=actor,
        target=target,
        readiness_authority=readiness,
    )
    assert stale_target_result["status"] == "rejected"
