from copy import deepcopy

from advisor.critical_hit_capabilities import resolve_critical_hit_capabilities
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_critical_state_authority, freeze_runtime_strategy_d0,
)


def _owner(side, pokemon_id):
    return {"session_id": "crit-capability", "side": side, "slot_index": 0, "pokemon_id": pokemon_id}


def _critical(owner, *, volatiles=(), lucky="known_absent", runtime="runtime", branch="preview"):
    states = {name: {"status": "known_present" if name in volatiles else "known_absent"} for name in ("focus-energy", "lansat", "dragon-cheer")}
    return {
        "status": "resolved", "schema_version": "runtime-current-critical-state-authority-v1",
        "session_id": "crit-capability", "source_runtime_fingerprint": runtime,
        "source_branch_fingerprint": branch, "owner": owner,
        "crit_volatiles": {"status": "resolved", "schema_version": "runtime-current-crit-volatile-authority-v1", "session_id": "crit-capability", "source_runtime_fingerprint": runtime, "source_branch_fingerprint": branch, "owner": owner, "volatiles": states},
        "lucky_chant": {"status": "resolved", "schema_version": "runtime-current-lucky-chant-authority-v1", "session_id": "crit-capability", "source_runtime_fingerprint": runtime, "source_branch_fingerprint": branch, "side": owner["side"], "lucky_chant": {"status": lucky}},
    }


def _state(*, volatiles=(), lucky="known_absent", runtime="runtime", branch="preview"):
    return {"attacker": _critical(_owner("self", "attacker"), volatiles=volatiles, runtime=runtime, branch=branch), "target": _critical(_owner("opponent", "target"), lucky=lucky, runtime=runtime, branch=branch)}


def _source(*, attacker_ability="pressure", defender_ability="pressure", item_status="known_absent", item="scope-lens", condition="known_absent", types="unknown"):
    return {
        "attacker_ability": {"status": "known", "value": attacker_ability} if attacker_ability is not None else {"status": "unknown"},
        "defender_ability": {"status": "known", "value": defender_ability} if defender_ability is not None else {"status": "unknown"},
        "attacker_item": {"status": "known", "value": item} if item_status == "known" else {"status": item_status},
        "target_condition": {"status": "known", "value": condition} if condition not in {"unknown", "known_absent"} else {"status": condition},
        "attacker_types": {"status": "known", "value": types} if types != "unknown" else {"status": "unknown"},
    }


def _resolve(move_id="tackle", **kwargs):
    return resolve_critical_hit_capabilities(move={"move_id": move_id}, source_authority=_source(**kwargs), critical_state_authority=_state())


def test_base_high_and_always_crit_rules_resolve_exact_engine_stages():
    base = _resolve()
    thunderbolt = _resolve("thunderbolt")
    facade = _resolve("facade")
    guts = _resolve(attacker_ability="guts")
    high = _resolve("slash")
    always = _resolve("flower-trick")
    assert (base["status"], base["move_rule"], base["crit_stage"]) == ("resolved", "base", 0)
    assert (thunderbolt["status"], thunderbolt["move_rule"], thunderbolt["crit_stage"]) == ("resolved", "base", 0)
    assert (facade["status"], facade["move_rule"], facade["crit_stage"]) == ("resolved", "base", 0)
    assert (guts["status"], guts["crit_stage"]) == ("resolved", 0)
    assert (high["status"], high["move_rule"], high["crit_stage"]) == ("resolved", "high-crit", 1)
    assert (always["status"], always["move_rule"], always["crit_stage"]) == ("resolved", "always-crit", 3)


def test_supported_current_contributors_reuse_canonical_crit_engine():
    focus = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=_source(), critical_state_authority=_state(volatiles=("focus-energy",)))
    lansat = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=_source(), critical_state_authority=_state(volatiles=("lansat",)))
    dragon = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=_source(types=["dragon"]), critical_state_authority=_state(volatiles=("dragon-cheer",)))
    scope_lens = _resolve(item_status="known", item="scope-lens")
    super_luck = _resolve(attacker_ability="super-luck")
    assert all(result["status"] == "resolved" and result["crit_stage"] == 2 for result in (focus, lansat, dragon))
    assert scope_lens["crit_stage"] == super_luck["crit_stage"] == 1
    assert super_luck["damage_compatibility"]["attacker_sniper"] is False


def test_lucky_chant_and_supported_defender_abilities_are_exact_blockers():
    lucky = resolve_critical_hit_capabilities(move={"move_id": "flower-trick"}, source_authority=_source(), critical_state_authority=_state(lucky="known_present"))
    armor = _resolve(defender_ability="battle-armor")
    shell = _resolve(defender_ability="shell-armor")
    assert lucky["crit_blocker"]["status"] == armor["crit_blocker"]["status"] == shell["crit_blocker"]["status"] == "known_present"


def test_intimidate_is_a_known_neutral_defender_critical_hit_source():
    result = _resolve(defender_ability="intimidate")
    assert result["status"] == "resolved"
    assert result["crit_stage"] == 0
    assert result["crit_blocker"]["status"] == "known_absent"


def test_missing_authority_fails_closed_without_neutral_fabrication():
    state = _state(); state["attacker"]["crit_volatiles"]["volatiles"]["focus-energy"] = {"status": "unknown"}
    volatile = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=_source(), critical_state_authority=state)
    blocker = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=_source(), critical_state_authority=_state(lucky="unknown"))
    assert (volatile["status"], volatile["reason"]) == ("incomplete", "focus-energy_unknown")
    assert (blocker["status"], blocker["reason"]) == ("incomplete", "target_lucky_chant_unknown")
    assert all(row["state"] != "known_neutral" for row in volatile["ledger"] if row["slot"] == "focus-energy")


def test_irrelevant_condition_and_type_slots_do_not_block_base_crit_completeness():
    source = _source(); source.pop("target_condition"); source.pop("attacker_types")
    result = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=source, critical_state_authority=_state())
    assert result["status"] == "resolved" and result["crit_stage"] == 0


def test_merciless_requires_exact_target_condition_and_dragon_cheer_requires_types():
    merciless = _resolve(attacker_ability="merciless", condition="unknown")
    state = _state(volatiles=("dragon-cheer",))
    dragon = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=_source(), critical_state_authority=state)
    assert (merciless["status"], merciless["reason"]) == ("incomplete", "merciless_target_condition_unknown")
    assert (dragon["status"], dragon["reason"]) == ("incomplete", "dragon_cheer_attacker_types_unknown")


def test_known_uncataloged_mechanics_and_move_rules_are_unsupported():
    ability = _resolve(attacker_ability="compound-eyes")
    item = _resolve(item_status="known", item="stick")
    move = _resolve("aqua-cutter")
    assert ability["status"] == item["status"] == move["status"] == "unsupported"


def test_binding_mismatch_rejects_and_output_does_not_mutate_inputs():
    state = _state(); source = _source(); original = deepcopy((state, source))
    result = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=source, critical_state_authority=state)
    result["ledger"][0]["state"] = "mutated"
    assert (state, source) == original
    stale = _state(); stale["target"] = _critical(_owner("opponent", "target"), runtime="other")
    assert resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority=_source(), critical_state_authority=stale)["status"] == "rejected"


def test_resolver_consumes_completed_d0_critical_state_authority_without_runtime_mutation():
    state = create_unknown_bootstrap_battle_state("critical-runtime", "attacker", "target")["state"]
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False, current_crit_volatiles=[])
        pokemon["current_crit_volatiles_provenance"] = {"event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        state[f"{side}_side"].update(side_conditions=[], side_conditions_provenance={"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation", "turn_number": 1})
    own = {"session_id": "critical-runtime", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}
    foe = {"session_id": "critical-runtime", "side": "opponent", "slot_index": 0, "pokemon_id": "target"}
    snapshot = {"status": "runtime_snapshot_ready", "session_id": "critical-runtime", "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=own)
    result = resolve_critical_hit_capabilities(move={"move_id": "tackle"}, source_authority={"attacker_ability": {"status": "known", "value": "pressure"}, "defender_ability": {"status": "known", "value": "pressure"}, "attacker_item": {"status": "known_absent"}}, critical_state_authority={"attacker": freeze_runtime_current_critical_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=own), "target": freeze_runtime_current_critical_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=foe)})
    assert result["status"] == "resolved" and result["crit_stage"] == 0
    assert state["self_side"]["pokemon"][0]["current_crit_volatiles"] == []
