from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_critical_hit_authority, freeze_runtime_strategy_d0,
)


def _state(session="runtime-critical-hit"):
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    for side, types in (("self", ["normal"]), ("opponent", ["normal"])):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False, condition="none", current_ability="pressure", known_item=None, current_type=types, current_crit_volatiles=[])
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
        pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_crit_volatiles_provenance"] = {"event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        state[f"{side}_side"].update(side_conditions=[], side_conditions_provenance={"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation", "turn_number": 1})
    return state


def _owner(state, side="self"):
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _d0(state):
    snapshot = _snapshot(state)
    return snapshot, freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))


def _resolve(state, move_id="tackle"):
    snapshot, d0 = _d0(state)
    return freeze_runtime_d0_critical_hit_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": move_id})


def test_runtime_projects_fully_neutral_base_high_and_always_crit_capabilities():
    base = _resolve(_state())
    thunderbolt = _resolve(_state(), "thunderbolt")
    high = _resolve(_state(), "slash")
    always = _resolve(_state(), "flower-trick")
    assert (base["status"], base["capability_resolution"]["crit_stage"]) == ("resolved", 0)
    assert (thunderbolt["status"], thunderbolt["capability_resolution"]["move_rule"], thunderbolt["capability_resolution"]["crit_stage"]) == ("resolved", "base", 0)
    assert (high["status"], high["capability_resolution"]["move_rule"], high["capability_resolution"]["crit_stage"]) == ("resolved", "high-crit", 1)
    assert (always["status"], always["capability_resolution"]["move_rule"], always["capability_resolution"]["crit_stage"]) == ("resolved", "always-crit", 3)


def test_runtime_projects_supported_crit_contributors_from_current_authority():
    super_luck = _state(); super_luck["self_side"]["pokemon"][0]["current_ability"] = "super-luck"
    scope_lens = _state(); scope_lens["self_side"]["pokemon"][0].update(known_item="scope-lens", known_item_provenance={"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"})
    focus = _state(); focus["self_side"]["pokemon"][0]["current_crit_volatiles"] = ["focus-energy"]
    lansat = _state(); lansat["self_side"]["pokemon"][0]["current_crit_volatiles"] = ["lansat"]
    dragon = _state(); dragon["self_side"]["pokemon"][0].update(current_type=["dragon"], current_crit_volatiles=["dragon-cheer"])
    merciless = _state(); merciless["self_side"]["pokemon"][0]["current_ability"] = "merciless"; merciless["opponent_side"]["pokemon"][0]["condition"] = "poison"
    assert all(_resolve(state)["capability_resolution"]["crit_stage"] == stage for state, stage in ((super_luck, 1), (scope_lens, 1), (focus, 2), (lansat, 2), (dragon, 2), (merciless, 3)))


def test_runtime_projects_lucky_chant_and_supported_ability_blockers():
    lucky = _state(); lucky["opponent_side"]["side_conditions"] = ["lucky-chant"]
    armor = _state(); armor["opponent_side"]["pokemon"][0]["current_ability"] = "battle-armor"
    shell = _state(); shell["opponent_side"]["pokemon"][0]["current_ability"] = "shell-armor"
    assert all(_resolve(state)["capability_resolution"]["crit_blocker"]["status"] == "known_present" for state in (lucky, armor, shell))


def test_runtime_unknown_and_known_uncataloged_sources_fail_closed():
    unknown = _state(); unknown["self_side"]["pokemon"][0]["current_crit_volatiles"] = {"knowledge": "unknown"}; unknown["self_side"]["pokemon"][0].pop("current_crit_volatiles_provenance")
    unsupported_ability = _state(); unsupported_ability["self_side"]["pokemon"][0]["current_ability"] = "compound-eyes"
    unsupported_item = _state(); unsupported_item["self_side"]["pokemon"][0].update(known_item="stick", known_item_provenance={"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"})
    assert (_resolve(unknown)["status"], _resolve(unknown)["reason"]) == ("incomplete", "focus-energy_unknown")
    assert _resolve(unsupported_ability)["status"] == _resolve(unsupported_item)["status"] == "unsupported"
    assert _resolve(_state(), "aqua-cutter")["status"] == "unsupported"


def test_runtime_rejects_stale_identity_target_and_move_mismatches_without_mutation():
    state = _state(); snapshot, d0 = _d0(state)
    resolved = freeze_runtime_d0_critical_hit_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": "tackle"})
    state["self_side"]["pokemon"][0]["current_ability"] = "mutated"
    assert resolved["source_authority"]["attacker_ability"]["value"] == "pressure"
    assert freeze_runtime_d0_critical_hit_authority(strategy_d0=d0, runtime_snapshot=_snapshot(state), attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": "tackle"})["status"] == "rejected"
    assert freeze_runtime_d0_critical_hit_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_metadata={"move_id": "tackle"})["status"] == "rejected"
    assert freeze_runtime_d0_critical_hit_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_metadata={"move_id": ""})["status"] == "rejected"
