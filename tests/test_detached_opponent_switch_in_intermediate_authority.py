from copy import deepcopy

from llm.advisor_current_opponent_switch_response_set_observation import admit_current_opponent_switch_response_set_observation
from llm.advisor_detached_opponent_switch_in_intermediate_authority import materialize_detached_opponent_switch_in_intermediate_authority
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_opponent_switch_response_authority import freeze_runtime_d0_opponent_switch_response_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_identity_groundedness import build_groundedness
from llm.advisor_prospective_entry_authority import build_prospective_entry_interactions
from llm.advisor_switch_hazard_authority import build_switch_hazard_context


def _manager(*, known_hp=True):
    state = create_unknown_bootstrap_battle_state("s", "self", "opponent")["state"]
    bench = deepcopy(state["opponent_side"]["pokemon"][0]); bench["pokemon_id"] = "bench"
    if known_hp:
        bench.update({"current_hp": 80, "max_hp": 100, "fainted": False, "current_type": ["normal"], "condition": "none", "known_item": None, "current_ability": "pressure", "stat_stages": {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}, "current_final_stats": {key: {"value": 100, "provenance": {"event_kind": "current_opponent_switch_target_combat_observed", "trust": "user_confirmed_observation", "turn_number": 1}} for key in ("attack", "defense", "special-attack", "special-defense", "speed")}})
        for field in ("current_hp", "max_hp", "fainted", "current_type", "condition", "known_item", "current_ability", "stat_stages"):
            bench[f"{field}_provenance"] = {"event_kind": "current_opponent_switch_target_combat_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        bench["condition_provenance"]["condition"] = "none"
    state["opponent_side"]["pokemon"][1] = bench
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="s", affected_side="opponent", stealth_rock="absent", spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent")
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _inputs(manager, state=None):
    provided_state = state is not None
    assert admit_current_opponent_switch_response_set_observation(runtime_session_manager=manager, captured_session_id="s", permission="permitted", targets=[{"slot_index": 1, "pokemon_id": "bench", "availability": "alive"}], turn_number=1)["status"] == "resolved"
    state = manager.read_state()["state"] if state is None else state
    snapshot = {"status": "runtime_snapshot_ready", "session_id": "s", "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner={"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "self"})
    if not provided_state:
        switch = freeze_runtime_d0_opponent_switch_response_authority(strategy_d0=d0, runtime_snapshot=snapshot)
    else:
        target = {"session_id": "s", "side": "opponent", "slot_index": 1, "pokemon_id": "bench"}
        action_id = "opponent_switch:s:1:bench"
        switch = {
            "status": "resolved", "session_id": d0["session_id"],
            "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
            "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
            "decision_owner": d0["decision_owner"], "own_actor": d0["active_owners"]["self"],
            "opponent_actor": d0["active_owners"]["opponent"],
            "actions": ({"action_id": action_id, "action_type": "manual_switch", "acting_side": "opponent", "target_side": "self", "selectability": "selectable", "target_owner": target},),
            "selectable_response_action_ids": (action_id,), "response_set_provenance": {"source": "strict_test_fixture"},
        }
    return d0, snapshot, switch


def test_selectable_opponent_target_materializes_detached_switch_in_with_exact_known_facts():
    manager = _manager(); d0, snapshot, switch = _inputs(manager)
    before = deepcopy(manager.read_state()["state"])
    result = materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch, selected_response_action_id="opponent_switch:s:1:bench")

    assert result["status"] == "resolved"
    hypothetical = result["hypothetical_switch_in_state"]
    assert hypothetical["hypothetical"] is True
    assert hypothetical["active_owner"]["pokemon_id"] == "bench"
    assert hypothetical["replaced_active_owner"]["pokemon_id"] == "opponent"
    assert hypothetical["hp_authority"]["current_hp"] == 80
    assert hypothetical["condition_authority"]["status"] == "known"
    assert hypothetical["stage_authority"]["status"] == "known"
    assert hypothetical["entry_consequence"]["effect"] == "known_absent_entry_hazards"
    assert hypothetical["entry_consequence"]["toxic_spikes_consequence"]["outcome"] == "absent"
    assert manager.read_state()["state"] == before


def test_unknown_target_hp_or_hazards_fail_closed_without_defaulting():
    manager = _manager(known_hp=False); d0, snapshot, switch = _inputs(manager)
    hp_unknown = materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch, selected_response_action_id="opponent_switch:s:1:bench")
    assert hp_unknown["status"] == "incomplete"

    manager = _manager(); d0, snapshot, switch = _inputs(manager)
    snapshot["state"].pop("switch_hazard_context")
    snapshot["state_fingerprint"] = state_fingerprint(snapshot["state"])
    # The original D0 cannot be paired with a changed snapshot.
    assert materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch, selected_response_action_id="opponent_switch:s:1:bench")["status"] == "rejected"


def test_unselectable_or_mismatched_response_never_materializes():
    manager = _manager(); d0, snapshot, switch = _inputs(manager)
    assert materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch, selected_response_action_id="unknown")["status"] == "rejected"
    foreign = deepcopy(switch); foreign["source_branch_fingerprint"] = "foreign"
    assert materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=foreign, selected_response_action_id="opponent_switch:s:1:bench")["status"] == "rejected"


def _toxic_ready(state, *, layers, types=("normal",), condition="none", grounded="grounded", interaction="applicable", sticky_web="absent", sticky_interaction="applicable", speed_stage=0):
    bench = state["opponent_side"]["pokemon"][1]
    bench["current_type"] = list(types)
    bench["condition"] = condition
    bench["condition_provenance"]["condition"] = condition
    bench["stat_stages"]["speed"] = speed_stage
    bench["prospective_groundedness_context"] = build_groundedness(
        session_id="s", side="opponent", slot_index=1, pokemon_id="bench", status=grounded,
    )
    bench["prospective_entry_interactions_context"] = build_prospective_entry_interactions(
        session_id="s", side="opponent", slot_index=1, pokemon_id="bench",
        toxic_spikes=interaction, sticky_web=sticky_interaction,
    )
    state["switch_hazard_context"] = build_switch_hazard_context(
        session_id="s", affected_side="opponent", stealth_rock="absent", spikes_layers=0,
        toxic_spikes_layers=layers, sticky_web=sticky_web,
    )
    return state


def test_toxic_spikes_entry_projects_exact_hypothetical_poison_and_toxic_conditions():
    for layers, expected in ((1, "poison"), (2, "toxic")):
        manager = _manager()
        state = _toxic_ready(manager.read_state()["state"], layers=layers)
        d0, snapshot, switch = _inputs(manager, state)
        before = deepcopy(manager.read_state()["state"])
        result = materialize_detached_opponent_switch_in_intermediate_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
            selected_response_action_id="opponent_switch:s:1:bench",
        )
        assert result["status"] == "resolved", result.get("reason")
        hypothetical = result["hypothetical_switch_in_state"]
        assert hypothetical["condition_authority"]["value"] == expected
        assert hypothetical["entry_consequence"]["toxic_spikes_consequence"] == {
            "status": "complete", "outcome": "status_applied", "post_condition": expected,
        }
        assert manager.read_state()["state"] == before


def test_toxic_spikes_immunity_and_absorption_require_exact_target_authority():
    manager = _manager(); state = _toxic_ready(manager.read_state()["state"], layers=2, types=("steel",))
    d0, snapshot, switch = _inputs(manager, state)
    steel = materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )
    assert steel["status"] == "resolved"
    assert steel["hypothetical_switch_in_state"]["entry_consequence"]["toxic_spikes_consequence"]["outcome"] == "status_immune"

    manager = _manager(); state = _toxic_ready(manager.read_state()["state"], layers=2, types=("poison",))
    d0, snapshot, switch = _inputs(manager, state)
    absorbed = materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )
    assert absorbed["status"] == "resolved"
    state = absorbed["hypothetical_switch_in_state"]
    assert state["entry_consequence"]["toxic_spikes_consequence"]["outcome"] == "absorbed"
    assert state["post_entry_hazard_context"]["toxic_spikes_layers"] == 0

    manager = _manager(); state = _toxic_ready(manager.read_state()["state"], layers=1, grounded="ungrounded")
    d0, snapshot, switch = _inputs(manager, state)
    ungrounded = materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )
    assert ungrounded["status"] == "resolved"
    assert ungrounded["hypothetical_switch_in_state"]["entry_consequence"]["toxic_spikes_consequence"]["outcome"] == "ungrounded"

    manager = _manager(); state = _toxic_ready(manager.read_state()["state"], layers=1, condition="burn")
    d0, snapshot, switch = _inputs(manager, state)
    already_statused = materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )
    assert already_statused["status"] == "resolved"
    assert already_statused["hypothetical_switch_in_state"]["entry_consequence"]["toxic_spikes_consequence"]["outcome"] == "already_statused"

    manager = _manager(); state = _toxic_ready(manager.read_state()["state"], layers=1, interaction="unknown")
    d0, snapshot, switch = _inputs(manager, state)
    assert materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )["status"] == "incomplete"


def test_sticky_web_projects_exact_hypothetical_speed_stage_and_respects_bounds():
    manager = _manager()
    state = _toxic_ready(manager.read_state()["state"], layers=0, sticky_web="present", speed_stage=0)
    d0, snapshot, switch = _inputs(manager, state)
    lowered = materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )
    assert lowered["status"] == "resolved"
    hypothetical = lowered["hypothetical_switch_in_state"]
    assert hypothetical["stage_authority"]["value"]["speed"] == -1
    assert hypothetical["entry_consequence"]["sticky_web_consequence"] == {
        "status": "complete", "outcome": "speed_stage_lowered", "speed_stage_before": 0, "speed_stage_after": -1,
    }

    manager = _manager()
    state = _toxic_ready(manager.read_state()["state"], layers=0, sticky_web="present", speed_stage=-6)
    d0, snapshot, switch = _inputs(manager, state)
    bounded = materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )
    assert bounded["status"] == "resolved"
    assert bounded["hypothetical_switch_in_state"]["entry_consequence"]["sticky_web_consequence"]["outcome"] == "speed_stage_minimum"
    assert bounded["hypothetical_switch_in_state"]["stage_authority"]["value"]["speed"] == -6


def test_sticky_web_known_ungrounded_is_no_effect_and_unknown_authority_is_incomplete():
    manager = _manager()
    state = _toxic_ready(manager.read_state()["state"], layers=0, sticky_web="present", grounded="ungrounded")
    d0, snapshot, switch = _inputs(manager, state)
    ungrounded = materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )
    assert ungrounded["status"] == "resolved"
    assert ungrounded["hypothetical_switch_in_state"]["entry_consequence"]["sticky_web_consequence"]["outcome"] == "ungrounded"
    assert ungrounded["hypothetical_switch_in_state"]["stage_authority"]["value"]["speed"] == 0

    manager = _manager()
    state = _toxic_ready(manager.read_state()["state"], layers=0, sticky_web="present", grounded="unknown")
    d0, snapshot, switch = _inputs(manager, state)
    assert materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )["status"] == "incomplete"

    manager = _manager()
    state = _toxic_ready(manager.read_state()["state"], layers=0, sticky_web="present")
    state["opponent_side"]["pokemon"][1]["stat_stages"]["speed"] = "unknown"
    d0, snapshot, switch = _inputs(manager, state)
    assert materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch,
        selected_response_action_id="opponent_switch:s:1:bench",
    )["status"] == "incomplete"
