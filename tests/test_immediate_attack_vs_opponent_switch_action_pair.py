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
from llm.advisor_switch_entry_intimidate_authority import build_switch_entry_intimidate_authority
from llm.advisor_switch_entry_sturdy_authority import build_switch_entry_sturdy_authority


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


def _intimidate_ready(state, *, interaction="lowered", self_attack_stage=0):
    state["self_side"]["pokemon"][0]["stat_stages"]["attack"] = self_attack_stage
    state["opponent_side"]["pokemon"][1]["current_ability"] = "intimidate"
    state["switch_entry_intimidate_authority"] = build_switch_entry_intimidate_authority(
        session_id=state["session_id"], source=_owner(state, "opponent", 1),
        target=_owner(state, "self"), interaction=interaction,
        target_attack_stage=self_attack_stage,
    )
    return state


def _weather_setter_ready(state, ability):
    state["opponent_side"]["pokemon"][1]["current_ability"] = ability
    return state


def _sturdy_ready(state, *, applicability="applicable"):
    state["opponent_side"]["pokemon"][1]["current_ability"] = "sturdy"
    state["switch_entry_sturdy_authority"] = build_switch_entry_sturdy_authority(
        session_id=state["session_id"], source=_owner(state, "opponent", 1),
        target=_owner(state, "self"), applicability=applicability,
    )
    return state


def _water_gun_action(action):
    result = deepcopy(action)
    result["action_id"] = "attack:water-gun"
    result["identity"] = "water-gun"
    result["move_metadata_authority"].update(candidate_id="attack:water-gun", move_id="water-gun")
    result["move_metadata_authority"]["metadata"] = {
        "move_id": "water-gun", "category": "special", "power": 40,
        "type": "water", "accuracy": 100, "priority": 0,
    }
    return result


def _hit_rolls(pair):
    return tuple(
        leaf["attack_leaf"]["damage_roll"]["damage"]
        for leaf in pair["terminal_branches"]
        if leaf["attack_leaf"]["hit_state"] == "hit" and leaf["attack_leaf"]["critical_state"] == "non_critical"
    )


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


def test_toxic_spikes_hypothetical_condition_reaches_private_switch_first_calculator_view():
    for layers, expected in ((1, "poison"), (2, "toxic")):
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
            toxic_spikes_layers=layers, sticky_web="absent",
        )
        d0, snapshot, action, switch, switch_id = _inputs(state)
        before = deepcopy(snapshot)
        pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
            strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
            switch_response_authority=switch, selected_switch_response_action_id=switch_id,
        )
        assert pair["status"] == "evaluable", pair.get("reason")
        assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        consumer = pair["switch_first_condition_consumer"]
        assert consumer["hypothetical"] is True
        assert consumer["condition"] == expected
        assert consumer["condition_changed"] is True
        assert consumer["provenance"] == "exact_detached_switch_in_condition_private_calculator_view_v1"
        assert snapshot == before


def test_switch_entry_condition_dependent_attack_stays_fail_closed_without_existing_pair_catalog_coverage():
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
    venoshock = deepcopy(action)
    venoshock["action_id"] = "attack:venoshock"
    venoshock["identity"] = "venoshock"
    venoshock["move_metadata_authority"].update(candidate_id="attack:venoshock", move_id="venoshock")
    venoshock["move_metadata_authority"]["metadata"] = {
        "move_id": "venoshock", "category": "special", "power": 65,
        "type": "poison", "accuracy": 100, "priority": 0,
    }
    pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=venoshock,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert pair["status"] in {"incomplete", "unsupported"}
    assert pair["status"] != "evaluable"


def test_sticky_web_hypothetical_speed_stage_flows_through_condition_neutral_switch_pair():
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
        toxic_spikes_layers=0, sticky_web="present",
    )
    d0, snapshot, action, switch, switch_id = _inputs(state)
    before = deepcopy(snapshot)
    pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert pair["switch_in_authority"]["hypothetical_switch_in_state"]["stage_authority"]["value"]["speed"] == -1
    assert snapshot == before


def test_intimidate_switch_in_overlays_exact_own_attack_stage_before_physical_attack():
    baseline_state = _state()
    d0, snapshot, action, switch, switch_id = _inputs(baseline_state)
    baseline = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    state = _intimidate_ready(_state(), interaction="lowered", self_attack_stage=0)
    d0, snapshot, action, switch, switch_id = _inputs(state)
    before = deepcopy(snapshot)
    lowered = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )

    assert lowered["status"] == "evaluable", lowered.get("reason")
    assert lowered["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    entry = lowered["switch_in_authority"]["hypothetical_switch_in_state"]["entry_consequence"]
    assert entry["intimidate_consequence"]["outcome"] == "attack_stage_lowered"
    assert entry["own_attack_stage_overlay"]["after"] == -1
    assert lowered["switch_first_condition_consumer"]["strategy_d0"]["current_stage_authority"]["self"]["stages"]["attack"]["value"] == -1
    assert max(_hit_rolls(lowered)) < max(_hit_rolls(baseline))
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=lowered)
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
    assert ledger["status"] == "evaluable" and ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert metrics["status"] == "resolved"
    assert snapshot == before


def test_weather_setter_switch_in_overlays_exact_weather_for_following_attack_without_d0_writeback():
    baseline_state = _state()
    d0, snapshot, action, switch, switch_id = _inputs(baseline_state)
    baseline = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=_water_gun_action(action),
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    baseline_maximum = max(_hit_rolls(baseline))

    for ability, weather, relation in (
        ("drizzle", "rain", "greater"), ("drought", "sun", "less"),
        ("sand-stream", "sandstorm", "equal"), ("snow-warning", "snow", "equal"),
    ):
        state = _weather_setter_ready(_state(), ability)
        d0, snapshot, action, switch, switch_id = _inputs(state)
        before = deepcopy(snapshot)
        pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
            strategy_d0=d0, runtime_snapshot=snapshot, own_action=_water_gun_action(action),
            switch_response_authority=switch, selected_switch_response_action_id=switch_id,
        )
        assert pair["status"] == "evaluable", pair.get("reason")
        assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        entry = pair["switch_in_authority"]["hypothetical_switch_in_state"]["entry_consequence"]
        assert entry["weather_consequence"] == {
            "status": "complete", "outcome": "weather_set", "weather_before": "none", "weather_after": weather,
        }
        private_snapshot = pair["switch_first_condition_consumer"]["runtime_snapshot"]
        assert private_snapshot["state"]["field"]["weather"] == weather
        maximum = max(_hit_rolls(pair))
        if relation == "greater":
            assert maximum > baseline_maximum
        elif relation == "less":
            assert maximum < baseline_maximum
        else:
            assert maximum == baseline_maximum
        assert snapshot == before


def test_weather_setter_does_not_activate_after_entry_hazard_ko():
    state = _weather_setter_ready(_state(), "drizzle")
    state["opponent_side"]["pokemon"][1]["current_hp"] = 1
    state["switch_hazard_context"] = build_switch_hazard_context(
        session_id=state["session_id"], affected_side="opponent", stealth_rock="present",
        spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent",
    )
    d0, snapshot, action, switch, switch_id = _inputs(state)
    pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert pair["status"] == "unsupported"
    assert pair["switch_in_authority"]["entry_consequence"]["weather_consequence"]["outcome"] == "not_activated_hazard_ko"


def test_sturdy_switch_in_caps_lethal_normal_formula_leaves_without_losing_roll_provenance():
    state = _sturdy_ready(_state())
    bench = state["opponent_side"]["pokemon"][1]
    bench["current_hp"] = bench["max_hp"] = 10
    d0, snapshot, action, switch, switch_id = _inputs(state)
    before = deepcopy(snapshot)
    pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    sturdy = pair["switch_in_authority"]["hypothetical_switch_in_state"]["sturdy_survival_authority"]
    assert sturdy["status"] == "ready" and sturdy["post_entry_hp"] == sturdy["maximum_hp"] == 10
    hits = [row["attack_leaf"] for row in pair["terminal_branches"] if row["attack_leaf"]["hit_state"] == "hit"]
    assert {row["damage_roll"]["roll_index"] for row in hits if row["damage_roll"] is not None} == set(range(16))
    activated = [row for row in hits if row["consequences"]["sturdy_survival"]["outcome"] == "applied"]
    assert activated
    assert all(row["damage_roll"]["damage"] >= 10 and row["consequences"]["damage"] == 9 for row in activated)
    assert all(row["consequences"]["target_final_hp"] == 1 and row["consequences"]["target_ko"] is False for row in activated)
    misses = [row["attack_leaf"] for row in pair["terminal_branches"] if row["attack_leaf"]["hit_state"] == "miss"]
    assert all(row["consequences"]["target_final_hp"] == 10 and row["consequences"]["sturdy_survival"] is None for row in misses)
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
    assert ledger["status"] == "evaluable" and ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert metrics["status"] == "resolved"
    assert snapshot == before


def test_sturdy_hazard_chip_suppression_unknown_and_foreign_authority_fail_closed_or_stay_inactive():
    state = _sturdy_ready(_state())
    state["opponent_side"]["pokemon"][1]["prospective_groundedness_context"] = build_groundedness(
        session_id=state["session_id"], side="opponent", slot_index=1, pokemon_id="bench", status="grounded",
    )
    state["switch_hazard_context"] = build_switch_hazard_context(
        session_id=state["session_id"], affected_side="opponent", stealth_rock="absent",
        spikes_layers=1, toxic_spikes_layers=0, sticky_web="absent",
    )
    d0, snapshot, action, switch, switch_id = _inputs(state)
    chipped = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert chipped["status"] == "evaluable"
    assert chipped["switch_in_authority"]["hypothetical_switch_in_state"]["sturdy_survival_authority"]["status"] == "not_applicable"

    state = _sturdy_ready(_state(), applicability="suppressed")
    d0, snapshot, action, switch, switch_id = _inputs(state)
    suppressed = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert suppressed["status"] == "evaluable"
    assert suppressed["switch_in_authority"]["hypothetical_switch_in_state"]["sturdy_survival_authority"]["status"] == "not_applicable"

    state = _sturdy_ready(_state(), applicability="unknown")
    d0, snapshot, action, switch, switch_id = _inputs(state)
    assert materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )["status"] == "incomplete"

    state = _sturdy_ready(_state())
    state["switch_entry_sturdy_authority"]["source"]["pokemon_id"] = "foreign"
    d0, snapshot, action, switch, switch_id = _inputs(state)
    assert materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )["status"] == "rejected"


def _target_secondary_action(action, move_id, *, power, move_type, **metadata_extra):
    result = _water_gun_action(action)
    result["action_id"] = f"attack:{move_id}"
    result["identity"] = move_id
    result["move_metadata_authority"].update(candidate_id=f"attack:{move_id}", move_id=move_id)
    result["move_metadata_authority"]["metadata"] = {
        "move_id": move_id, "category": "special", "power": power,
        "type": move_type, "accuracy": 100, "priority": 0, "target": "selected-pokemon", **metadata_extra,
    }
    return result


def test_sturdy_ready_nonlethal_and_target_secondary_paths_remain_exact():
    state = _sturdy_ready(_state())
    d0, snapshot, action, switch, switch_id = _inputs(state)
    nonlethal = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert nonlethal["status"] == "evaluable"
    hits = [row["attack_leaf"] for row in nonlethal["terminal_branches"] if row["attack_leaf"]["hit_state"] == "hit"]
    assert all(row["consequences"]["sturdy_survival"]["outcome"] == "not_triggered" for row in hits)
    assert all(row["consequences"]["target_final_hp"] == 100 - row["consequences"]["damage"] for row in hits)

    state["opponent_side"]["pokemon"][1]["current_hp"] = state["opponent_side"]["pokemon"][1]["max_hp"] = 10
    state["opponent_side"]["pokemon"][1]["condition_provenance"] = {
        "event_kind": "current_opponent_switch_target_combat_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "condition": "none",
    }
    d0, snapshot, fresh_action, switch, switch_id = _inputs(state)
    thunderbolt = _target_secondary_action(fresh_action, "thunderbolt", power=90, move_type="electric", effect_chance=10, ailment="paralysis")
    thunder_pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=thunderbolt,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert thunder_pair["status"] == "evaluable", thunder_pair.get("reason")
    assert thunder_pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    thunder_saved = [row["attack_leaf"] for row in thunder_pair["terminal_branches"]
                     if row["attack_leaf"]["hit_state"] == "hit"
                     and row["attack_leaf"]["consequences"]["sturdy_survival"]["outcome"] == "applied"]
    assert {row["consequences"]["secondary"]["branch"] for row in thunder_saved} == {"effect", "no_effect"}
    assert all(row["consequences"]["target_final_hp"] == 1 and row["consequences"]["target_ko"] is False for row in thunder_saved)

    state = _sturdy_ready(_state())
    state["opponent_side"]["pokemon"][1].update(current_hp=10, max_hp=10, current_type=["water"])
    state["opponent_side"]["pokemon"][1]["condition_provenance"] = {
        "event_kind": "current_opponent_switch_target_combat_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "condition": "none",
    }
    d0, snapshot, fresh_action, switch, switch_id = _inputs(state)
    shadow_pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot,
        own_action=_target_secondary_action(fresh_action, "shadow-ball", power=80, move_type="ghost", effect_chance=20, stat_changes=[{"stat": "special-defense", "change": -1}]),
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert shadow_pair["status"] == "evaluable", shadow_pair.get("reason")
    shadow_saved = [row["attack_leaf"] for row in shadow_pair["terminal_branches"]
                    if row["attack_leaf"]["hit_state"] == "hit"
                    and row["attack_leaf"]["consequences"]["sturdy_survival"]["outcome"] == "applied"]
    assert {row["consequences"]["secondary"]["branch"] for row in shadow_saved} == {"effect", "no_effect"}
    assert all(row["consequences"]["target_final_hp"] == 1 for row in shadow_saved)

    state = _sturdy_ready(_state())
    state["opponent_side"]["pokemon"][1].update(current_hp=10, max_hp=10)
    state["opponent_side"]["pokemon"][1]["condition_provenance"] = {
        "event_kind": "current_opponent_switch_target_combat_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "condition": "none",
    }
    d0, snapshot, fresh_action, switch, switch_id = _inputs(state)
    acid_pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot,
        own_action=_target_secondary_action(fresh_action, "acid-spray", power=40, move_type="poison", effect_chance=100, stat_changes=[{"stat": "special-defense", "change": -2}]),
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert acid_pair["status"] == "evaluable", acid_pair.get("reason")
    acid_saved = [row["attack_leaf"] for row in acid_pair["terminal_branches"]
                  if row["attack_leaf"]["hit_state"] == "hit"
                  and row["attack_leaf"]["consequences"]["sturdy_survival"]["outcome"] == "applied"]
    assert acid_saved and all(row["consequences"]["target_final_hp"] == 1 for row in acid_saved)
    assert all(row["consequences"]["deterministic_stage_effect"]["branches"][row["damage_roll"]["roll_index"]]["effects"] for row in acid_saved)

    for pair in (thunder_pair, shadow_pair, acid_pair):
        ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
        metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
        assert ledger["status"] == "evaluable" and ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert metrics["status"] == "resolved"


def test_intimidate_blocked_reversed_and_stage_bounds_preserve_exact_stage_outcomes():
    for interaction, stage, expected, after in (
        ("blocked", 0, "attack_drop_prevented", 0),
        ("reversed", 0, "attack_stage_reversed", 1),
        ("lowered", -6, "attack_stage_minimum", -6),
        ("reversed", 6, "attack_stage_maximum", 6),
    ):
        state = _intimidate_ready(_state(), interaction=interaction, self_attack_stage=stage)
        d0, snapshot, action, switch, switch_id = _inputs(state)
        pair = materialize_immediate_attack_vs_opponent_switch_action_pair(
            strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
            switch_response_authority=switch, selected_switch_response_action_id=switch_id,
        )
        assert pair["status"] == "evaluable", pair.get("reason")
        entry = pair["switch_in_authority"]["hypothetical_switch_in_state"]["entry_consequence"]
        assert entry["intimidate_consequence"]["outcome"] == expected
        assert entry["own_attack_stage_overlay"]["after"] == after


def test_intimidate_unknown_or_foreign_authority_fails_closed_before_prediction():
    state = _intimidate_ready(_state(), interaction="lowered")
    state["switch_entry_intimidate_authority"] = build_switch_entry_intimidate_authority(
        session_id=state["session_id"], source=_owner(state, "opponent", 1),
        target=_owner(state, "self"), interaction="unknown", target_attack_stage="unknown",
    )
    d0, snapshot, action, switch, switch_id = _inputs(state)
    incomplete = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert incomplete["status"] == "incomplete"

    state = _intimidate_ready(_state(), interaction="lowered")
    state["switch_entry_intimidate_authority"]["source"]["pokemon_id"] = "foreign"
    d0, snapshot, action, switch, switch_id = _inputs(state)
    rejected = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert rejected["status"] == "rejected"

    state = _intimidate_ready(_state(), interaction="lowered")
    state["opponent_side"]["pokemon"][1]["current_ability"] = "unknown"
    d0, snapshot, action, switch, switch_id = _inputs(state)
    unknown_ability = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert unknown_ability["status"] == "incomplete"

    state = _intimidate_ready(_state(), interaction="lowered")
    state["self_side"]["pokemon"][0]["stat_stages"]["attack"] = "unknown"
    d0, snapshot, action, switch, switch_id = _inputs(state)
    unknown_stage = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert unknown_stage["status"] == "incomplete"


def test_entry_hazard_ko_does_not_activate_intimidate_or_mutate_current_state():
    state = _intimidate_ready(_state(), interaction="lowered")
    bench = state["opponent_side"]["pokemon"][1]
    bench["current_hp"] = 1
    bench["current_type"] = ["fire"]
    state["switch_hazard_context"] = build_switch_hazard_context(
        session_id=state["session_id"], affected_side="opponent", stealth_rock="present",
        spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent",
    )
    d0, snapshot, action, switch, switch_id = _inputs(state)
    before = deepcopy(snapshot)
    result = materialize_immediate_attack_vs_opponent_switch_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=action,
        switch_response_authority=switch, selected_switch_response_action_id=switch_id,
    )
    assert result["status"] == "unsupported"
    assert result["reason"] == "replacement_required_after_switch_entry_ko"
    assert snapshot == before
