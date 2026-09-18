"""Focused production contracts for observed contact-reactive damage admission."""
from copy import deepcopy

import pytest

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_observed_contact_reactive_damage_runtime_admission import (
    admit_observed_contact_reactive_damage_result,
)
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SESSION = "contact-damage-runtime"


def _runtime_manager(
    *,
    attacker_side="self",
    attacker_hp=80,
    attacker_max_hp=80,
    attacker_ability="pressure",
    attacker_item=None,
    defender_ability="rough-skin",
    defender_item=None,
):
    state = create_unknown_bootstrap_battle_state(SESSION, "self-a", "opponent-a")["state"]
    defender_side = "opponent" if attacker_side == "self" else "self"
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        if side == attacker_side:
            if attacker_hp != "unknown" and attacker_max_hp != "unknown":
                pokemon["current_hp"] = attacker_hp
                pokemon["max_hp"] = attacker_max_hp
            pokemon["fainted"] = False
        else:
            pokemon["current_hp"] = 100
            pokemon["max_hp"] = 100
            pokemon["fainted"] = False

    config = {
        attacker_side: (attacker_ability, attacker_item),
        defender_side: (defender_ability, defender_item),
    }
    steps = []
    sequence = 0
    for side in ("self", "opponent"):
        pokemon_id = state[f"{side}_side"]["pokemon"][0]["pokemon_id"]
        ability, item = config[side]
        if ability != "unknown":
            sequence += 1
            steps.append(
                {
                    "observation_id": f"seed:{sequence}",
                    "observation_sequence": sequence,
                    "planned_effect": "set_current_ability",
                    "trust": "user_confirmed_observation",
                    "turn_number": 1,
                    "side": side,
                    "slot_index": 0,
                    "pokemon_id": pokemon_id,
                    "ability": ability,
                }
            )
        if item != "unknown":
            sequence += 1
            steps.append(
                {
                    "observation_id": f"seed:{sequence}",
                    "observation_sequence": sequence,
                    "planned_effect": "set_current_item",
                    "trust": "user_confirmed_observation",
                    "turn_number": 1,
                    "side": side,
                    "slot_index": 0,
                    "pokemon_id": pokemon_id,
                    **({"status": "known", "item": item} if item is not None else {"status": "known_absent"}),
                }
            )
    projected = project_atomic_transition(
        state,
        {"session_id": SESSION, "status": "planned", "conflicts": [], "ordered_steps": steps},
        SESSION,
    )
    assert projected["status"] == "ready_with_projected_state", projected
    created = BattleObservationRuntimeSessionManager.create(SESSION, projected["projected_state"])
    assert created["status"] == "session_ready", created
    return created["manager"]


def _admit(
    manager,
    *,
    attacker_side="self",
    move_id="tackle",
    action="action:tackle",
    after=70,
    hit_damage=10,
    routing="target",
):
    return admit_observed_contact_reactive_damage_result(
        runtime_session_manager=manager,
        captured_session_id=SESSION,
        attacker_side=attacker_side,
        move_id=move_id,
        source_action_id=action,
        attacker_hp_after=after,
        source_hit_actual_damage=hit_damage,
        source_hit_target_routing=routing,
        turn_number=2,
    )


def _state_pokemon(manager, side):
    return manager.read_state()["state"][f"{side}_side"]["pokemon"][0]


def _kind(result, event_kind):
    return next(row for row in result["observations"] if row["event_kind"] == event_kind)


def _seed_rows(manager, rows):
    for row in rows:
        admitted = manager.admit_confirmation(
            SESSION,
            {"status": "confirmed", "observation": deepcopy(row)},
        )
        assert admitted["status"] == "added", admitted


def _source_result(*, hp=80, max_hp=80, ability="rough-skin", item=None, after=70, action="action:seed"):
    manager = _runtime_manager(
        attacker_hp=hp,
        attacker_max_hp=max_hp,
        defender_ability=ability,
        defender_item=item,
    )
    result = _admit(manager, action=action, after=after)
    assert result["status"] == "resolved", result
    return result


def test_rough_skin_non_ko_commits_evidence_hp_and_fresh_d0():
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    before = manager.capture_runtime_state_snapshot(SESSION)
    result = _admit(manager, after=70)
    assert result["status"] == "resolved" and result["idempotent"] is False
    assert _state_pokemon(manager, "self")["current_hp"] == 70
    receipt = _kind(result, "contact_reactive_damage_result_observed")
    assert receipt["reducer_eligibility"] == "evidence_only"
    assert [(row["source_kind"], row["reactive_damage"]) for row in receipt["payload"]["ordered_sources"]] == [("rough-skin", 10)]
    plan = build_replay_plan({"session_id": SESSION}, result["observations"])
    assert receipt in plan["evidence_only_events"]
    assert result["strategy_d0"]["source_runtime_fingerprint"] == result["runtime_snapshot"]["state_fingerprint"]
    assert result["strategy_d0"]["source_runtime_fingerprint"] != before["state_fingerprint"]


def test_iron_barbs_non_ko():
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="iron-barbs")
    result = _admit(manager, after=70, action="action:iron")
    assert result["status"] == "resolved"
    assert _kind(result, "contact_reactive_damage_result_observed")["payload"]["ordered_sources"][0]["source_kind"] == "iron-barbs"


def test_rocky_helmet_non_ko():
    manager = _runtime_manager(attacker_hp=60, attacker_max_hp=60, defender_ability="pressure", defender_item="rocky-helmet")
    result = _admit(manager, after=50, action="action:helmet")
    assert result["status"] == "resolved"
    row = _kind(result, "contact_reactive_damage_result_observed")["payload"]["ordered_sources"][0]
    assert (row["source_kind"], row["reactive_damage"], row["pre_hp"], row["post_hp"]) == ("rocky-helmet", 10, 60, 50)


@pytest.mark.parametrize("ability", ["rough-skin", "iron-barbs"])
def test_stacked_ability_then_rocky_helmet_preserves_exact_order_and_rows(ability):
    manager = _runtime_manager(attacker_hp=120, attacker_max_hp=120, defender_ability=ability, defender_item="rocky-helmet")
    result = _admit(manager, after=85, action=f"action:{ability}")
    assert result["status"] == "resolved"
    ordered = _kind(result, "contact_reactive_damage_result_observed")["payload"]["ordered_sources"]
    assert [(row["order_index"], row["source_kind"], row["pre_hp"], row["reactive_damage"], row["post_hp"]) for row in ordered] == [
        (1, ability, 120, 15, 105),
        (2, "rocky-helmet", 105, 20, 85),
    ]


def test_opponent_attacker_to_self_defender_is_side_neutral():
    manager = _runtime_manager(
        attacker_side="opponent",
        attacker_hp=80,
        attacker_max_hp=80,
        defender_ability="rough-skin",
    )
    result = _admit(manager, attacker_side="opponent", after=70, action="action:opponent")
    assert result["status"] == "resolved"
    assert _state_pokemon(manager, "opponent")["current_hp"] == 70
    payload = _kind(result, "contact_reactive_damage_result_observed")["payload"]
    assert payload["attacker_side"] == "opponent" and payload["defender_side"] == "self"


def test_reactive_damage_attacker_ko_composes_hp_before_faint_and_no_d0():
    manager = _runtime_manager(attacker_hp=10, attacker_max_hp=80, defender_ability="rough-skin")
    result = _admit(manager, after=0, action="action:ko")
    assert result["status"] == "resolved" and result["strategy_d0"] is None
    hp = _kind(result, "exact_hp_transition_observed")
    faint = _kind(result, "pokemon_faint_observed")
    assert hp["observation_sequence"] < faint["observation_sequence"]
    actor = _state_pokemon(manager, "self")
    assert actor["current_hp"] == 0 and actor["fainted"] is True
    assert actor["current_hp_provenance"]["source_observation_id"] == hp["observation_id"]
    assert actor["fainted_provenance"]["source_observation_id"] == faint["observation_id"]
    assert result["replacement_boundary"]["status"] == "replacement_required_after_faint"
    assert result["replacement_boundary"]["fainted_owner"]["side"] == "self"


def test_exact_retry_is_idempotent_without_sequence_collection_or_runtime_mutation():
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    kwargs = dict(action="action:retry", after=70)
    first = _admit(manager, **kwargs)
    assert first["status"] == "resolved"
    before_state = manager.read_state()
    before_collection = manager.read_collection_snapshot()
    before_sequence = manager.last_allocated_sequence
    retry = _admit(manager, **kwargs)
    assert retry["status"] == "resolved" and retry["idempotent"] is True and retry["reason"] == "idempotent_reuse"
    assert manager.read_state() == before_state
    assert manager.read_collection_snapshot() == before_collection
    assert manager.last_allocated_sequence == before_sequence


def test_ko_exact_retry_is_idempotent_and_keeps_no_d0():
    manager = _runtime_manager(attacker_hp=10, attacker_max_hp=80, defender_ability="rough-skin")
    first = _admit(manager, action="action:ko-retry", after=0)
    assert first["status"] == "resolved"
    before_sequence = manager.last_allocated_sequence
    retry = _admit(manager, action="action:ko-retry", after=0)
    assert retry["status"] == "resolved" and retry["idempotent"] is True and retry["strategy_d0"] is None
    assert manager.last_allocated_sequence == before_sequence


def test_receipt_without_hp_companion_rejects_without_repair():
    source = _source_result(action="action:receipt-only")
    target = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    _seed_rows(target, [row for row in source["observations"] if row["event_kind"] in {"executed_move_observed", "contact_reactive_damage_result_observed"}])
    before = (target.read_state(), target.read_collection_snapshot(), target.last_allocated_sequence)
    result = _admit(target, action="action:receipt-only", after=70)
    assert result["status"] == "rejected"
    assert (target.read_state(), target.read_collection_snapshot(), target.last_allocated_sequence) == before


def test_hp_without_receipt_rejects_without_repair():
    source = _source_result(action="action:hp-only")
    target = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    _seed_rows(target, [_kind(source, "exact_hp_transition_observed")])
    before = (target.read_state(), target.read_collection_snapshot(), target.last_allocated_sequence)
    result = _admit(target, action="action:hp-only", after=70)
    assert result["status"] == "rejected"
    assert (target.read_state(), target.read_collection_snapshot(), target.last_allocated_sequence) == before


def test_ko_receipt_and_hp_without_faint_rejects_without_repair():
    source_manager = _runtime_manager(attacker_hp=10, attacker_max_hp=80, defender_ability="rough-skin")
    source = _admit(source_manager, action="action:missing-faint", after=0)
    target = _runtime_manager(attacker_hp=10, attacker_max_hp=80, defender_ability="rough-skin")
    _seed_rows(target, [row for row in source["observations"] if row["event_kind"] != "pokemon_faint_observed"])
    before = (target.read_state(), target.read_collection_snapshot(), target.last_allocated_sequence)
    result = _admit(target, action="action:missing-faint", after=0)
    assert result["status"] == "rejected"
    assert (target.read_state(), target.read_collection_snapshot(), target.last_allocated_sequence) == before


def test_faint_without_related_hp_rejects_without_repair():
    source_manager = _runtime_manager(attacker_hp=10, attacker_max_hp=80, defender_ability="rough-skin")
    source = _admit(source_manager, action="action:faint-only", after=0)
    target = _runtime_manager(attacker_hp=10, attacker_max_hp=80, defender_ability="rough-skin")
    _seed_rows(target, [row for row in source["observations"] if row["event_kind"] in {"executed_move_observed", "contact_reactive_damage_result_observed", "pokemon_faint_observed"}])
    before = target.read_collection_snapshot()
    result = _admit(target, action="action:faint-only", after=0)
    assert result["status"] == "rejected" and target.read_collection_snapshot() == before


def test_wrong_ordered_source_receipt_rejects():
    source = _source_result(hp=120, max_hp=120, ability="rough-skin", item="rocky-helmet", after=85, action="action:wrong-order")
    forged = deepcopy(source["observations"])
    receipt = next(row for row in forged if row["event_kind"] == "contact_reactive_damage_result_observed")
    receipt["payload"]["ordered_sources"][0]["source_kind"] = "rocky-helmet"
    receipt["payload"]["ordered_sources"][1]["source_kind"] = "rough-skin"
    target = _runtime_manager(attacker_hp=120, attacker_max_hp=120, defender_ability="rough-skin", defender_item="rocky-helmet")
    _seed_rows(target, forged)
    assert _admit(target, action="action:wrong-order", after=85)["status"] == "rejected"


def test_wrong_observed_post_hp_rejects_without_mutation():
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    before = (manager.read_state(), manager.read_collection_snapshot())
    result = _admit(manager, action="action:wrong-hp", after=69)
    assert result["status"] == "rejected"
    assert (manager.read_state(), manager.read_collection_snapshot()) == before


@pytest.mark.parametrize("mutation", ["source_action", "attacker", "defender", "hp"])
def test_conflicting_complete_receipt_identity_or_hp_rejects(mutation):
    action = f"action:corrupt-{mutation.replace('_', '-')}"
    source = _source_result(action=action)
    forged = deepcopy(source["observations"])
    receipt = next(row for row in forged if row["event_kind"] == "contact_reactive_damage_result_observed")
    if mutation == "source_action":
        receipt["payload"]["source_action_id"] = "action:other"
    elif mutation == "attacker":
        receipt["payload"]["attacker_pokemon_id"] = "other"
    elif mutation == "defender":
        receipt["payload"]["defender_pokemon_id"] = "other"
    else:
        receipt["payload"]["hp_before"] = 79
    target = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    _seed_rows(target, forged)
    before = target.read_state()
    assert _admit(target, action=action, after=70)["status"] == "rejected"
    assert target.read_state() == before


def test_complete_collection_with_inconsistent_runtime_rejects():
    source = _source_result(action="action:unapplied")
    target = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    _seed_rows(target, source["observations"])
    assert _state_pokemon(target, "self")["current_hp"] == 80
    before_sequence = target.last_allocated_sequence
    result = _admit(target, action="action:unapplied", after=70)
    assert result["status"] == "rejected"
    assert _state_pokemon(target, "self")["current_hp"] == 80
    assert target.last_allocated_sequence == before_sequence


@pytest.mark.parametrize(
    ("move_id", "hit_damage", "routing", "reason"),
    [
        ("water-gun", 10, "target", "source_hit_known_non_contact"),
        ("tackle", 10, "substitute", "source_hit_contacted_substitute_not_holder"),
        ("tackle", 0, "target", "source_hit_no_damage"),
    ],
)
def test_known_not_applicable_paths_do_not_mutate(move_id, hit_damage, routing, reason):
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin", defender_item="rocky-helmet")
    before = (manager.read_state(), manager.read_collection_snapshot())
    result = _admit(
        manager,
        move_id=move_id,
        action=f"action:no-effect-{move_id}-{routing}-{hit_damage}",
        after=80,
        hit_damage=hit_damage,
        routing=routing,
    )
    assert result["status"] == "resolved" and result["reason"] == reason and result["observations"] == []
    assert (manager.read_state(), manager.read_collection_snapshot()) == before


def test_no_supported_reactive_source_does_not_mutate():
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="pressure", defender_item=None)
    before = (manager.read_state(), manager.read_collection_snapshot())
    result = _admit(manager, action="action:no-source", after=80)
    assert result["status"] == "resolved" and result["reason"] == "no_reactive_source" and result["observations"] == []
    assert (manager.read_state(), manager.read_collection_snapshot()) == before


@pytest.mark.parametrize(
    ("ability", "item"),
    [("unknown", None), ("rough-skin", "unknown")],
)
def test_unknown_defender_item_or_ability_is_incomplete_without_mutation(ability, item):
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability=ability, defender_item=item)
    before = (manager.read_state(), manager.read_collection_snapshot())
    action = "action:unknown-ability" if ability == "unknown" else "action:unknown-item"
    result = _admit(manager, action=action, after=70)
    assert result["status"] == "incomplete"
    assert (manager.read_state(), manager.read_collection_snapshot()) == before


def test_unknown_attacker_hp_or_max_hp_is_incomplete():
    manager = _runtime_manager(attacker_hp="unknown", attacker_max_hp="unknown", defender_ability="rough-skin")
    before = manager.read_collection_snapshot()
    result = _admit(manager, action="action:unknown-hp", after=70)
    assert result["status"] == "incomplete"
    assert manager.read_collection_snapshot() == before


def test_magic_guard_remains_unsupported():
    manager = _runtime_manager(
        attacker_hp=80,
        attacker_max_hp=80,
        attacker_ability="magic-guard",
        defender_ability="rough-skin",
    )
    result = _admit(manager, action="action:magic-guard", after=80)
    assert result["status"] == "unsupported"
    assert result["reason"] == "contact_reactive_magic_guard_prevention_unsupported"


def test_compatible_executed_move_is_reused_without_duplicate():
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    existing = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id=SESSION,
        side="self",
        execution_move_id="tackle",
        selected_move_id="tackle",
        source_action_id="action:existing",
        result_class=None,
        turn_number=2,
    )
    assert existing["status"] == "resolved"
    result = _admit(manager, action="action:existing", after=70)
    rows = manager.read_collection_snapshot()["ordered_observations"]
    assert result["status"] == "resolved"
    assert len([row for row in rows if row["event_kind"] == "executed_move_observed" and row["payload"]["source_action_id"] == "action:existing"]) == 1


def test_conflicting_executed_move_rejects_without_mutation():
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    existing = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id=SESSION,
        side="self",
        execution_move_id="scratch",
        selected_move_id="scratch",
        source_action_id="action:conflict",
        result_class=None,
        turn_number=2,
    )
    assert existing["status"] == "resolved"
    before = (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence)
    result = _admit(manager, action="action:conflict", after=70)
    assert result["status"] == "rejected"
    assert (manager.read_state(), manager.read_collection_snapshot(), manager.last_allocated_sequence) == before


def test_non_ko_fresh_d0_makes_pre_commit_d0_stale():
    manager = _runtime_manager(attacker_hp=80, attacker_max_hp=80, defender_ability="rough-skin")
    before_snapshot = manager.capture_runtime_state_snapshot(SESSION)
    result = _admit(manager, action="action:freshness", after=70)
    assert result["status"] == "resolved"
    assert runtime_strategy_d0_freshness(
        strategy_d0=result["strategy_d0"],
        runtime_snapshot=result["runtime_snapshot"],
    )["status"] == "current"
    assert before_snapshot["state_fingerprint"] != result["runtime_snapshot"]["state_fingerprint"]
