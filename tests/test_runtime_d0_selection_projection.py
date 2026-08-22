from copy import deepcopy

from llm.advisor_current_state_candidate_discovery import discover_candidates
from llm.advisor_candidate_contract import build_provider_recommendation_payload, prepare_ui_recommendation_cycle
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_selection_projection import (
    build_runtime_d0_selection_capture,
    freeze_runtime_d0_bound_selection_projection,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_strategy_d0,
    freeze_runtime_strategy_selection_authority,
)


def _state(session: str = "selection-runtime") -> dict:
    state = create_unknown_bootstrap_battle_state(session, "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0])
    state["self_side"]["pokemon"][1]["pokemon_id"] = "bench"
    return state


def _snapshot(state: dict) -> dict:
    return {
        "status": "runtime_snapshot_ready", "session_id": state["session_id"],
        "state": deepcopy(state), "state_fingerprint": state_fingerprint(state),
    }


def _owner(state: dict) -> dict:
    active = state["self_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": "self", "slot_index": active, "pokemon_id": state["self_side"]["pokemon"][active]["pokemon_id"]}


def _prepared(d0: dict, *, moves=None, switches=None) -> dict:
    owner = d0["decision_owner"]
    return {
        "status": "ready",
        "_runtime_d0_selection_capture": build_runtime_d0_selection_capture(strategy_d0=d0),
        "_combined_action_turn_snapshot": {
            "battle_state": {"active_player": {"slot_index": owner["slot_index"], "species_id": owner["pokemon_id"]}},
            "current_state": {"current_state_session_id": owner["session_id"]},
        },
        "recommendation_request": {"candidate_comparisons": moves if moves is not None else [
            {"move": "water-gun", "eligibility": "eligible"},
            {"move": "tackle", "eligibility": "not_selectable"},
        ]},
        "evidence_bundle": {"switch_candidates": switches if switches is not None else [
            {"target_pokemon_id": "bench", "selectable": True, "availability_supportability": "complete", "legality_supportability": "complete"},
        ]},
    }


def test_freezes_existing_structured_move_and_switch_selection_for_exact_runtime_d0() -> None:
    state = _state(); d0 = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state), decision_owner=_owner(state))
    source = _prepared(d0)

    projection = freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=source)
    selection = freeze_runtime_strategy_selection_authority(strategy_d0=d0, selection_projection=projection)
    source["recommendation_request"]["candidate_comparisons"][0]["eligibility"] = "not_selectable"
    source["evidence_bundle"]["switch_candidates"][0]["selectable"] = False

    assert projection["status"] == "resolved"
    assert projection["schema_version"] == "runtime-d0-bound-selection-projection-v1"
    assert projection["moves"] == [{"move_id": "tackle", "selection": "not_selectable"}, {"move_id": "water-gun", "selection": "selectable"}]
    assert projection["switches"] == [{"pokemon_id": "bench", "selection": "selectable"}]
    assert selection["status"] == "resolved"
    assert {row["action_id"] for row in selection["actions"]} == {"attack:water-gun", "attack:tackle", "manual_switch:bench"}


def test_rejects_post_hoc_runtime_fingerprint_and_active_identity_binding() -> None:
    state_a = _state(); d0_a = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state_a), decision_owner=_owner(state_a))
    source_a = _prepared(d0_a)
    state_b = deepcopy(state_a); state_b["last_applied_observation_sequence"] = 1
    d0_b = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state_b), decision_owner=_owner(state_b))

    assert freeze_runtime_d0_bound_selection_projection(strategy_d0=d0_b, prepared_cycle=source_a) == {"status": "rejected", "reason": "selection_cycle_runtime_d0_mismatch"}
    bad_identity = _prepared(d0_a)
    bad_identity["_combined_action_turn_snapshot"]["battle_state"]["active_player"]["species_id"] = "foreign"
    assert freeze_runtime_d0_bound_selection_projection(strategy_d0=d0_a, prepared_cycle=bad_identity)["reason"] == "selection_cycle_active_identity_mismatch"
    bad_owner = _prepared(d0_a)
    bad_owner["_runtime_d0_selection_capture"]["decision_owner"]["side"] = "opponent"
    assert freeze_runtime_d0_bound_selection_projection(strategy_d0=d0_a, prepared_cycle=bad_owner)["reason"] == "selection_cycle_runtime_d0_mismatch"
    bad_session = _prepared(d0_a)
    bad_session["_runtime_d0_selection_capture"]["session_id"] = "foreign-session"
    assert freeze_runtime_d0_bound_selection_projection(strategy_d0=d0_a, prepared_cycle=bad_session)["reason"] == "selection_cycle_runtime_d0_mismatch"


def test_unknown_selection_is_preserved_partial_and_discovery_does_not_promote_it() -> None:
    state = _state(); d0 = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state), decision_owner=_owner(state))
    source = _prepared(d0, moves=[{"move": "water-gun", "eligibility": "eligible"}], switches=[
        {"target_pokemon_id": "unknown-bench", "selectable": False, "availability_supportability": "insufficient_context", "legality_supportability": "not_applicable"},
    ])

    projection = freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=source)
    selection = freeze_runtime_strategy_selection_authority(strategy_d0=d0, selection_projection=projection)
    discovery = discover_candidates(snapshot=selection)

    assert projection["selection_completeness"] == "partial"
    assert projection["switches"] == [{"pokemon_id": "unknown-bench", "selection": "selection_unknown"}]
    assert selection["selection_completeness"]["candidate_set"] == "partial"
    assert {row["candidate_id"] for row in discovery["candidates"]} == {"attack:water-gun"}


def test_duplicate_semantic_identities_reject_and_source_order_is_invariant() -> None:
    state = _state(); d0 = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state), decision_owner=_owner(state))
    first = _prepared(d0, moves=[{"move": "water-gun", "eligibility": "eligible"}, {"move": "tackle", "eligibility": "not_selectable"}], switches=[
        {"target_pokemon_id": "z", "selectable": False, "availability_supportability": "complete", "legality_supportability": "complete"},
        {"target_pokemon_id": "a", "selectable": True, "availability_supportability": "complete", "legality_supportability": "complete"},
    ])
    second = deepcopy(first)
    second["recommendation_request"]["candidate_comparisons"].reverse()
    second["evidence_bundle"]["switch_candidates"].reverse()
    duplicate = _prepared(d0, moves=[{"move": "water-gun", "eligibility": "eligible"}, {"move": "water-gun", "eligibility": "eligible"}])

    assert freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=first)["moves"] == freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=second)["moves"]
    assert freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=first)["switches"] == freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=second)["switches"]
    assert freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=duplicate)["reason"] == "duplicate_or_invalid_move_selection_identity"


def test_execution_shaped_and_historical_payloads_are_stripped_not_promoted() -> None:
    state = _state(); d0 = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state), decision_owner=_owner(state))
    source = _prepared(d0)
    source["recommendation_request"]["candidate_comparisons"][0]["observed_damage_result"] = {"damage": 99}
    source["evidence_bundle"]["switch_candidates"][0]["incoming_execution_authority"] = {"hp": 1}

    projection = freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=source)

    assert projection["moves"] == [{"move_id": "tackle", "selection": "not_selectable"}, {"move_id": "water-gun", "selection": "selectable"}]
    assert projection["switches"] == [{"pokemon_id": "bench", "selection": "selectable"}]
    assert "observed_damage_result" not in str(projection)
    assert "incoming_execution_authority" not in str(projection)


def test_capture_is_attached_while_the_existing_recommendation_cycle_is_prepared_and_is_provider_private() -> None:
    state = _state("captured-cycle")
    state["self_side"]["pokemon"][0]["pokemon_id"] = "a"
    state["opponent_side"]["pokemon"][0]["pokemon_id"] = "b"
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state), decision_owner=_owner(state))
    stats = [
        {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}
        for side, stat, value in (("self", "attack", 200), ("opponent", "defense", 150), ("self", "special-attack", 200), ("opponent", "special-defense", 150), ("self", "speed", 200), ("opponent", "speed", 100))
    ]
    battle = {
        "scenario": {"mode": "advisor", "known_limitations": []}, "current_state_session_id": state["session_id"],
        "pokemon": {"my_active": {"name_en": "a", "slot_index": 0}, "opponent_active": {"name_en": "b", "slot_index": 0}},
        "final_stat_context": {"current_final_stats": stats},
        "moves": {"my_selected_move_index": 0, "my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]},
    }

    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}], battle_input=battle,
        move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal"}},
        runtime_selection_capture=build_runtime_d0_selection_capture(strategy_d0=d0),
    )
    projection = freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=prepared)
    provider_payload = build_provider_recommendation_payload(prepared_cycle=prepared)

    assert prepared["status"] == "ready"
    assert projection["status"] == "resolved"
    assert projection["moves"] == [{"move_id": "tackle", "selection": "selectable"}]
    assert "_runtime_d0_selection_capture" not in provider_payload
