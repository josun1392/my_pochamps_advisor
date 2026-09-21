from copy import deepcopy

import pytest

from llm.advisor_reducer_state_model import make_unknown_battle_fact, state_fingerprint
from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import (
    freeze_runtime_d0_standard_charge_participant_mechanics_authority,
    freeze_runtime_d0_standard_charge_terminal_mechanics_authority,
    validate_runtime_d0_standard_charge_participant_mechanics_authority,
    validate_runtime_d0_standard_charge_terminal_mechanics_authority,
)
from llm.advisor_runtime_strategy_d0 import build_runtime_d0_native_damage_context, freeze_runtime_strategy_d0
from llm.advisor_substitute import update_substitute_state_context
from tests.test_detached_intermediate_predictive_authority import _owner, _state


def _ready():
    state = _state()
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["stat_stages"].update(accuracy=0, evasion=0)
        pokemon["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "condition": "none", "turn_number": 1}
        pokemon["known_item"] = "leftovers"
        pokemon["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"}
        state[f"{side}_side"]["side_conditions"] = []
        state[f"{side}_side"]["side_conditions_provenance"] = {"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation"}
        pokemon["current_confusion"] = "none"
        pokemon["confusion_provenance"] = {"event_kind": "current_confusion_observed", "trust": "user_confirmed_observation", "turn_number": 1, "state": "none"}
        owner = _owner(state, side)
        state["substitute_state_context"] = update_substitute_state_context(context=state.get("substitute_state_context"), session_id=state["session_id"], owner=owner, state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1")
    state["field"]["terrain"] = "none"
    state["field"]["terrain_provenance"] = {"event_kind": "current_terrain_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {"event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation", "source_observation_id": "magic-room:1", "source_sequence": 1}
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return state, snapshot, d0


@pytest.mark.parametrize("move_id", ("sky-attack", "razor-wind", "freeze-shock", "ice-burn"))
def test_current_d0_terminal_bundle_is_mechanics_only_for_each_supported_move(move_id):
    state, snapshot, d0 = _ready(); actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": f"a:{move_id}", "identity": move_id}
    actor_row = freeze_runtime_d0_standard_charge_participant_mechanics_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, owner=actor, participant_role="actor", move_metadata={"move_id": move_id})
    target_row = freeze_runtime_d0_standard_charge_participant_mechanics_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, owner=target, participant_role="target", move_metadata={"move_id": move_id})
    assert actor_row["status"] == target_row["status"] == "resolved"
    assert {"owner", "current_level", "current_final_stats", "current_hp", "current_stages", "condition", "item", "ability", "types", "substitute", "critical_hit_volatiles", "lucky_chant", "field", "side_conditions", "direct_mechanics", "status_progression", "confusion_state", "confusion_progression"} <= set(actor_row)
    assert actor_row["current_final_stats"]["values"]["hp"] == actor_row["current_hp"]["maximum_hp"]
    assert actor_row["field"] == {"status": "known", "weather": "none", "terrain": "none"}
    assert isinstance(actor_row["types"]["value"], list)
    direct = actor_row["direct_mechanics"]["combatant"]
    assert direct["stats"] == actor_row["current_final_stats"]["values"]
    assert direct["boosts"] == {key: actor_row["current_stages"]["values"][key] for key in ("attack", "defense", "special-attack", "special-defense", "speed")}
    assert direct["item"] == actor_row["item"]["value"] and direct["ability"] == actor_row["ability"]["value"]
    bundle = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, move_metadata={"move_id": move_id})
    assert bundle["status"] == "resolved", {key: bundle[key].get("status") for key in ("target_sturdy_authority", "target_focus_sash_authority", "attacker_life_orb_authority", "actor_held_item_effect_applicability_authority", "target_held_item_effect_applicability_authority")}
    assert bundle["mechanics_only"] is True and bundle["execution_grant"] is False
    assert bundle["canonical_terminal_effect"]["move_id"] == move_id


def test_unknown_participant_fact_is_incomplete_not_defaulted():
    state, snapshot, d0 = _ready(); actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": "a", "identity": "sky-attack"}
    state2 = deepcopy(state); state2["self_side"]["pokemon"][0].pop("known_item")
    snapshot2 = {**snapshot, "state": state2, "state_fingerprint": state_fingerprint(state2)}
    row = freeze_runtime_d0_standard_charge_participant_mechanics_authority(strategy_d0=d0, runtime_snapshot=snapshot2, action=action, actor=actor, target=target, owner=actor, participant_role="actor", move_metadata={"move_id": "sky-attack"})
    assert row["status"] == "rejected"  # changed runtime cannot be silently reused.


def test_participant_role_and_binding_tampering_rejects():
    state, snapshot, d0 = _ready(); actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": "a", "identity": "sky-attack"}
    assert freeze_runtime_d0_standard_charge_participant_mechanics_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, owner=target, participant_role="actor", move_metadata={"move_id": "sky-attack"})["status"] == "rejected"
    assert freeze_runtime_d0_standard_charge_terminal_mechanics_authority(strategy_d0=d0, runtime_snapshot=snapshot, action={**action, "identity": "ice-burn"}, actor=actor, target=target, move_metadata={"move_id": "sky-attack"})["status"] == "rejected"


def _refresh(state):
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return snapshot, d0


def _participant(state, *, side="self", move_id="sky-attack"):
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    owner = _owner(state, side)
    action = {"action_type": "attack", "action_id": f"a:{move_id}", "identity": move_id}
    row = freeze_runtime_d0_standard_charge_participant_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        owner=owner, participant_role="actor" if side == "self" else "target",
        move_metadata={"move_id": move_id},
    )
    return snapshot, d0, action, actor, target, row


@pytest.mark.parametrize(
    ("mutate", "expected"),
    (
        (lambda s: (s["self_side"]["pokemon"][0].update(current_level=make_unknown_battle_fact()), s["self_side"]["pokemon"][0].pop("current_level_provenance")), "current_level"),
        (lambda s: s["self_side"]["pokemon"][0]["current_final_stats"].pop("attack"), "final_stat.attack"),
        (lambda s: s["self_side"]["pokemon"][0]["stat_stages"].pop("accuracy"), "current_stages"),
        (lambda s: s["self_side"]["pokemon"][0].pop("known_item_provenance"), "item"),
        (lambda s: (s["self_side"]["pokemon"][0].update(current_ability=make_unknown_battle_fact()), s["self_side"]["pokemon"][0].pop("current_ability_provenance")), "ability"),
        (lambda s: (s["self_side"]["pokemon"][0].update(current_type=make_unknown_battle_fact()), s["self_side"]["pokemon"][0].pop("current_type_provenance")), "types"),
        (lambda s: (s["self_side"]["pokemon"][0].update(current_crit_volatiles=make_unknown_battle_fact()), s["self_side"]["pokemon"][0].pop("current_crit_volatiles_provenance")), "critical_state"),
        (lambda s: s["field"].pop("terrain_provenance"), "field"),
        (lambda s: s["self_side"].pop("side_conditions_provenance"), "side_conditions"),
    ),
)
def test_fresh_d0_unknown_participant_facts_remain_incomplete(mutate, expected):
    state, _snapshot0, _d00 = _ready()
    mutate(state)
    _snapshot, _d0, _action, _actor, _target, row = _participant(state)
    assert row["status"] == "incomplete", {"row": row, "d0_status": _d0.get("status"), "d0_reason": _d0.get("reason")}
    assert expected in row["missing_authority"]


def test_unknown_hp_is_incomplete_on_fresh_d0():
    state, _snapshot0, _d00 = _ready()
    pokemon = state["self_side"]["pokemon"][0]
    pokemon["current_hp"] = {"knowledge": "unknown"}
    pokemon["fainted"] = {"knowledge": "unknown"}
    _snapshot, _d0, _action, _actor, _target, row = _participant(state)
    assert row["status"] == "incomplete"
    assert "current_hp" in row["missing_authority"]


def test_substitute_active_inactive_unknown_are_not_collapsed():
    state, _snapshot0, _d00 = _ready()
    owner = _owner(state, "self")
    _, _, _, _, _, inactive = _participant(state)
    assert inactive["substitute"] == {"status": "known_inactive"}

    active_state = deepcopy(state)
    active_state["substitute_state_context"] = update_substitute_state_context(
        context=active_state["substitute_state_context"], session_id=active_state["session_id"],
        owner=owner, state="known_active", substitute_hp=25, provenance="runtime_observed_substitute_state_v1",
    )
    _, _, _, _, _, active = _participant(active_state)
    assert active["status"] == "resolved"
    assert active["substitute"] == {"status": "known_active", "substitute_hp": 25}

    unknown_state = deepcopy(state)
    unknown_state["substitute_state_context"] = update_substitute_state_context(
        context=unknown_state["substitute_state_context"], session_id=unknown_state["session_id"],
        owner=owner, state="unknown", substitute_hp=None, provenance="runtime_observed_substitute_state_v1",
    )
    _, _, _, _, _, unknown = _participant(unknown_state)
    assert unknown["status"] == "incomplete"
    assert unknown["substitute"]["status"] == "unknown"


def test_exact_no_critical_volatiles_and_lucky_chant_inactive_are_transported():
    state, _snapshot0, _d00 = _ready()
    _, _, _, _, _, row = _participant(state)
    assert row["status"] == "resolved"
    assert row["critical_hit_volatiles"] == {"status": "known", "value": []}
    assert row["lucky_chant"] == {"status": "known_inactive"}


def test_exact_critical_volatiles_and_lucky_chant_are_transported_and_unknown_fails_closed():
    state, _snapshot0, _d00 = _ready()
    pokemon = state["self_side"]["pokemon"][0]
    pokemon["current_crit_volatiles"] = ["focus-energy"]
    state["self_side"]["side_conditions"] = ["lucky-chant"]
    _, _, _, _, _, row = _participant(state)
    assert row["status"] == "resolved"
    assert row["critical_hit_volatiles"] == {"status": "known", "value": ["focus-energy"]}
    assert row["lucky_chant"] == {"status": "known_active"}

    unknown = deepcopy(state)
    unknown["self_side"]["pokemon"][0]["current_crit_volatiles"] = make_unknown_battle_fact()
    unknown["self_side"]["pokemon"][0].pop("current_crit_volatiles_provenance")
    _, _, _, _, _, row2 = _participant(unknown)
    assert row2["status"] == "incomplete"
    assert row2["critical_hit_volatiles"]["status"] == "unknown"


@pytest.mark.parametrize("condition", ("sleep", "freeze"))
def test_sleep_freeze_progression_requires_exact_valid_row(condition):
    state, _snapshot0, _d00 = _ready()
    owner = _owner(state, "self")
    pokemon = state["self_side"]["pokemon"][0]
    pokemon["condition"] = condition
    pokemon["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "condition": condition, "turn_number": 1}
    pokemon["champions_status_progression"] = {
        "schema_version": "champions-sleep-freeze-progression-v1", "owner": owner,
        "condition": condition, "origin_id": f"{condition}:episode", "established_turn": 1,
        "prior_attempts": 0, "sleep_duration": 2 if condition == "sleep" else None,
        "condition_observation": deepcopy(pokemon["condition_provenance"]), "observed_turn": 1,
        "provenance": "observed_champions_status_progression_v1",
    }
    _, _, _, _, _, row = _participant(state)
    assert row["status"] == "resolved"
    assert row["status_progression"]["status"] == "known"

    missing = deepcopy(state)
    missing["self_side"]["pokemon"][0].pop("champions_status_progression")
    _, _, _, _, _, row2 = _participant(missing)
    assert row2["status"] == "incomplete"
    assert row2["status_progression"]["status"] == "unknown"


def test_confusion_exact_none_and_confused_progression_are_distinct():
    state, _snapshot0, _d00 = _ready()
    _, _, _, _, _, none_row = _participant(state)
    assert none_row["confusion_state"] == {"status": "known_none"}
    assert none_row["confusion_progression"] == {"status": "not_applicable"}

    confused = deepcopy(state)
    owner = _owner(confused, "self")
    pokemon = confused["self_side"]["pokemon"][0]
    pokemon["current_confusion"] = "confused"
    pokemon["confusion_provenance"] = {"event_kind": "current_confusion_observed", "trust": "user_confirmed_observation", "turn_number": 1, "state": "confused"}
    pokemon["champions_confusion_progression"] = {
        "schema_version": "champions-confusion-progression-v1", "owner": owner, "state": "confused",
        "origin_id": "confusion:episode", "established_turn": 1, "prior_opportunities": 0,
        "duration": 3, "confusion_observation": deepcopy(pokemon["confusion_provenance"]),
        "observed_turn": 1, "provenance": "observed_champions_confusion_progression_v1",
    }
    _, _, _, _, _, confused_row = _participant(confused)
    assert confused_row["status"] == "resolved"
    assert confused_row["confusion_state"]["status"] == "known_confused"
    assert confused_row["confusion_progression"]["status"] == "known"

    missing = deepcopy(confused)
    missing["self_side"]["pokemon"][0].pop("champions_confusion_progression")
    _, _, _, _, _, missing_row = _participant(missing)
    assert missing_row["status"] == "incomplete"
    assert missing_row["confusion_state"]["status"] == "unknown"


def test_terminal_bundle_reuses_support_owners_and_power_herb_does_not_fabricate_life_orb():
    state, snapshot, d0 = _ready()
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": "a:sky-attack", "identity": "sky-attack"}
    bundle = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "sky-attack"},
    )
    assert bundle["target_sturdy_authority"]["status"] == "resolved"
    assert bundle["target_focus_sash_authority"]["status"] == "resolved"
    assert bundle["attacker_life_orb_authority"]["status"] == "resolved"
    assert bundle["attacker_life_orb_authority"]["outcome"] == "known_no_effect"

    power = deepcopy(state)
    power["self_side"]["pokemon"][0]["known_item"] = "power-herb"
    snapshot2, d02 = _refresh(power)
    actor2, target2 = _owner(power, "self"), _owner(power, "opponent")
    power_bundle = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d02, runtime_snapshot=snapshot2, action=action, actor=actor2, target=target2,
        move_metadata={"move_id": "sky-attack"},
    )
    assert power_bundle["status"] == "resolved"
    assert power_bundle["attacker_life_orb_authority"]["outcome"] == "known_no_effect"
    assert power_bundle["attacker_life_orb_authority"]["damage_modifier"]["applies"] is False
    assert power_bundle["actor_held_item_effect_applicability_authority"]["current_item_authority"]["item_id"] == "power-herb"


def test_life_orb_preexecution_authority_carries_modifier_without_claiming_recoil():
    state, _snapshot0, _d00 = _ready()
    state["self_side"]["pokemon"][0]["known_item"] = "life-orb"
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": "a:sky-attack", "identity": "sky-attack"}
    bundle = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "sky-attack"},
    )
    life = bundle["attacker_life_orb_authority"]
    assert bundle["status"] == "resolved"
    assert life["damage_modifier"]["applies"] is True
    assert life["outcome"] == "not_triggered"
    assert life["recoil"]["eligible"] is False


@pytest.mark.parametrize(
    "move",
    (
        {"move_id": "sky-attack", "power": 140, "category": "physical", "type": "flying", "accuracy": 90, "target": "selected-pokemon"},
        {"move_id": "razor-wind", "power": 80, "category": "special", "type": "normal", "accuracy": 100, "target": "selected-pokemon"},
        {"move_id": "freeze-shock", "power": 140, "category": "physical", "type": "ice", "accuracy": 90, "target": "selected-pokemon"},
        {"move_id": "ice-burn", "power": 140, "category": "special", "type": "ice", "accuracy": 90, "target": "selected-pokemon"},
    ),
)
def test_generic_native_damage_guard_still_blocks_raw_charge_execution(move):
    state, snapshot, d0 = _ready()
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    result = build_runtime_d0_native_damage_context(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=actor, target=target,
        move_metadata=move,
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "two_turn_execution_unrepresented"


def test_unsupported_charge_move_rejects_and_stale_runtime_rejects():
    state, snapshot, d0 = _ready()
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": "a:solar-beam", "identity": "solar-beam"}
    assert freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"},
    )["status"] == "rejected"

    stale = deepcopy(state)
    stale["last_applied_observation_sequence"] = 99
    stale_snapshot = {"status": "runtime_snapshot_ready", "session_id": stale["session_id"], "state": stale, "state_fingerprint": state_fingerprint(stale)}
    action2 = {"action_type": "attack", "action_id": "a:sky-attack", "identity": "sky-attack"}
    assert freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=stale_snapshot, action=action2, actor=actor, target=target,
        move_metadata={"move_id": "sky-attack"},
    )["status"] == "rejected"


def test_participant_replay_rejects_binding_and_mechanics_tampering():
    state, snapshot, d0 = _ready()
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": "a:sky-attack", "identity": "sky-attack"}
    row = freeze_runtime_d0_standard_charge_participant_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        owner=actor, participant_role="actor", move_metadata={"move_id": "sky-attack"},
    )
    assert validate_runtime_d0_standard_charge_participant_mechanics_authority(
        authority=row, strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        owner=actor, participant_role="actor", move_metadata={"move_id": "sky-attack"},
    )["status"] == "resolved"

    for key in (
        "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner",
        "actor", "target", "owner", "participant_role", "action_id", "move_id",
        "current_hp", "current_final_stats", "current_stages", "condition", "item", "ability",
        "types", "substitute", "critical_hit_volatiles", "lucky_chant", "field", "side_conditions",
        "direct_mechanics", "status_progression", "confusion_state", "confusion_progression",
        "fainted", "source_action_id", "source_move_id",
    ):
        tampered = deepcopy(row)
        tampered[key] = {"tampered": True}
        replay = validate_runtime_d0_standard_charge_participant_mechanics_authority(
            authority=tampered, strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
            owner=actor, participant_role="actor", move_metadata={"move_id": "sky-attack"},
        )
        assert replay["status"] == "rejected", key


def test_terminal_replay_rejects_nested_support_and_canonical_effect_tampering():
    state, snapshot, d0 = _ready()
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": "a:sky-attack", "identity": "sky-attack"}
    bundle = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "sky-attack"},
    )
    assert validate_runtime_d0_standard_charge_terminal_mechanics_authority(
        authority=bundle, strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "sky-attack"},
    )["status"] == "resolved"

    for key in (
        "canonical_terminal_effect", "target_sturdy_authority", "target_focus_sash_authority",
        "attacker_life_orb_authority", "actor_held_item_effect_applicability_authority",
        "target_held_item_effect_applicability_authority", "authenticated_move_metadata",
    ):
        tampered = deepcopy(bundle)
        tampered[key] = {"tampered": True}
        assert validate_runtime_d0_standard_charge_terminal_mechanics_authority(
            authority=tampered, strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
            move_metadata={"move_id": "sky-attack"},
        )["status"] == "rejected", key

    actor_row = deepcopy(bundle["actor_participant_mechanics_authority"])
    actor_row["current_hp"] = {"status": "known", "current_hp": 1, "maximum_hp": 100}
    assert freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target,
        move_metadata={"move_id": "sky-attack"}, actor_participant_mechanics_authority=actor_row,
    )["status"] == "rejected"
