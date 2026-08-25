from copy import deepcopy

from llm.advisor_detached_opponent_switch_in_intermediate_authority import SCHEMA_VERSION as SWITCH_IN_SCHEMA
from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_attack_vs_opponent_switch_action_pair import materialize_immediate_attack_vs_opponent_switch_action_pair
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_identity_groundedness import build_groundedness
from llm.advisor_prospective_entry_authority import build_prospective_entry_interactions
from llm.advisor_substitute import update_substitute_state_context
from llm.advisor_switch_hazard_authority import build_switch_hazard_context


MOVE = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}


def _state():
    state = create_unknown_bootstrap_battle_state("attack-switch", "self", "opponent") ["state"]
    bench = deepcopy(state["opponent_side"]["pokemon"][0]); bench["pokemon_id"] = "bench"
    state["opponent_side"]["pokemon"][1] = bench
    for side in ("self", "opponent"):
        for pokemon in state[f"{side}_side"]["pokemon"].values():
            pokemon.update(current_hp=100, max_hp=100, fainted=False, current_level=50, stat_stages={name: 0 for name in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}, condition="none", current_ability="pressure", known_item=None, current_type=["normal"], current_crit_volatiles=[])
            pokemon["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
            pokemon["current_level_provenance"] = {"event_kind": "current_level_observed", "trust": "user_confirmed_observation", "turn_number": 1}
            pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
            pokemon["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
            pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
            pokemon["current_crit_volatiles_provenance"] = {"event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": 1}
            pokemon["current_final_stats"] = {stat: {"value": 100, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": "user_confirmed_observation", "turn_number": 1}} for stat in ("attack", "defense", "special-attack", "special-defense", "speed")}
        state[f"{side}_side"]["side_conditions"] = []
        state[f"{side}_side"]["side_conditions_provenance"] = {"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"].update(weather="none", terrain="none", battle_format="singles")
    for key, event in (("weather", "current_weather_observed"), ("terrain", "current_terrain_observed"), ("battle_format", "current_battle_format_observed")):
        state["field"][f"{key}_provenance"] = {"event_kind": event, "trust": "user_confirmed_observation", "turn_number": 1}
    for side in ("self", "opponent"):
        state["substitute_state_context"] = update_substitute_state_context(context=state.get("substitute_state_context"), session_id=state["session_id"], owner=_owner(state, side), state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1")
    state["substitute_state_context"] = update_substitute_state_context(context=state.get("substitute_state_context"), session_id=state["session_id"], owner=_owner(state, "opponent", 1), state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1")
    state["switch_hazard_context"] = build_switch_hazard_context(session_id=state["session_id"], affected_side="opponent", stealth_rock="absent", spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent")
    bench = state["opponent_side"]["pokemon"][1]
    for field in ("current_hp", "current_type", "condition", "known_item", "current_ability"):
        bench[f"{field}_provenance"] = {"event_kind": "current_opponent_switch_target_combat_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    bench["condition_provenance"]["condition"] = "none"
    return state


def _owner(state, side, slot=0):
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _inputs(state):
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = _owner(state, "self"); opponent = _owner(state, "opponent"); incoming = _owner(state, "opponent", 1)
    meta = {"status": "resolved", "schema_version": "canonical-normalized-move-metadata-authority-v1", "candidate_id": "attack:tackle", "move_id": "tackle", "metadata": deepcopy(MOVE), "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": own, "active_attacker": own}
    own_action = {"action_id": "attack:tackle", "action_type": "attack", "identity": "tackle", "move_metadata_authority": meta}
    switch_id = "opponent_switch:attack-switch:1:bench"
    switch = {"status": "resolved", "schema_version": "runtime-d0-opponent-switch-response-authority-v1", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": own, "own_actor": own, "opponent_actor": opponent, "actions": ({"action_id": switch_id, "action_type": "manual_switch", "acting_side": "opponent", "target_side": "self", "selectability": "selectable", "target_owner": incoming, "availability": "alive"},), "selectable_response_action_ids": (switch_id,), "response_set_provenance": {"source": "test"}}
    return d0, snapshot, own_action, switch, switch_id


def test_switch_first_pair_uses_incoming_target_and_preserves_exact_attack_leaves():
    state = _state(); d0, snapshot, action, switch, switch_id = _inputs(state); before = deepcopy(snapshot)
    result = materialize_immediate_attack_vs_opponent_switch_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, switch_response_authority=switch, selected_switch_response_action_id=switch_id)

    assert result["status"] == "evaluable", result.get("reason")
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all(row["incoming_target"]["pokemon_id"] == "bench" for row in result["terminal_branches"])
    assert all(row["attack_leaf"]["damage_roll"] is not None for row in result["terminal_branches"] if row["attack_leaf"]["hit_state"] == "hit")
    assert result["switch_in_authority"]["schema_version"] == SWITCH_IN_SCHEMA
    assert snapshot == before and state["opponent_side"]["active_slot_index"] == 0


def test_unknown_hazards_and_stale_or_unknown_switches_fail_closed():
    state = _state(); d0, snapshot, action, switch, switch_id = _inputs(state)
    snapshot["state"].pop("switch_hazard_context"); snapshot["state_fingerprint"] = state_fingerprint(snapshot["state"])
    assert materialize_immediate_attack_vs_opponent_switch_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, switch_response_authority=switch, selected_switch_response_action_id=switch_id)["status"] == "rejected"

    state = _state(); d0, snapshot, action, switch, switch_id = _inputs(state)
    assert materialize_immediate_attack_vs_opponent_switch_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, switch_response_authority=switch, selected_switch_response_action_id="missing")["status"] == "rejected"


def test_switch_pair_reuses_canonical_ledger_and_metrics_with_leaf_provenance():
    state = _state(); d0, snapshot, action, switch, switch_id = _inputs(state)
    pair = materialize_immediate_attack_vs_opponent_switch_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, switch_response_authority=switch, selected_switch_response_action_id=switch_id)
    before = deepcopy(pair)
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)

    assert ledger["status"] == "evaluable" and ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["opponent_switch_response_action_id"] == switch_id
    assert all(leaf["switch_response"]["incoming_target"]["pokemon_id"] == "bench" for leaf in ledger["terminal_leaves"])
    assert metrics["status"] == "resolved" and metrics["ranking_influence"] == "none"
    assert metrics["opponent"]["final_hp_distribution"]["probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all(outcome["pair_leaf_ids"] for outcome in metrics["opponent"]["final_hp_distribution"]["outcomes"])
    assert pair == before


def test_non_evaluable_switch_pair_remains_fail_closed_for_ledger_and_metrics():
    pair = {"status": "unsupported", "reason": "replacement_required_after_switch_entry_ko"}
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "unsupported"
    assert project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)["status"] == "unsupported"


def test_toxic_spikes_hypothetical_condition_never_falls_back_to_stale_switch_target_condition():
    state = _state()
    bench = state["opponent_side"]["pokemon"][1]
    bench["prospective_groundedness_context"] = build_groundedness(
        session_id=state["session_id"], side="opponent", slot_index=1, pokemon_id="bench", status="grounded",
    )
    bench["prospective_entry_interactions_context"] = build_prospective_entry_interactions(
        session_id=state["session_id"], side="opponent", slot_index=1, pokemon_id="bench",
        toxic_spikes="applicable", sticky_web="applicable",
    )
    state["switch_hazard_context"] = build_switch_hazard_context(
        session_id=state["session_id"], affected_side="opponent", stealth_rock="absent", spikes_layers=0,
        toxic_spikes_layers=1, sticky_web="absent",
    )
    d0, snapshot, action, switch, switch_id = _inputs(state)
    pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert pair["status"] == "incomplete"
    assert pair["reason"] == "hypothetical_switch_in_condition_consumer_unavailable"
