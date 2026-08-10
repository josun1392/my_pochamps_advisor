from copy import deepcopy
import json

from llm.advisor_candidate_contract import build_provider_recommendation_payload, prepare_ui_recommendation_cycle
from llm.advisor_reducer_state_model import make_unknown_battle_fact
from llm.advisor_switch_candidates import build_switch_candidate_context_projection, build_switch_candidates
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot
from scripts.run_sanitized_multi_move_mechanics_smoke import _battle


def _state(session="switch-session", roster=None):
    pokemon = roster or {
        0: {"pokemon_id": "pikachu-a", "fainted": False},
        1: {"pokemon_id": "pikachu-b", "fainted": False},
        2: {"pokemon_id": "eevee", "fainted": True},
        3: {"pokemon_id": "mew", "fainted": make_unknown_battle_fact()},
    }
    normalized = {
        slot: {"pokemon_id": row["pokemon_id"], "current_hp": make_unknown_battle_fact(), "max_hp": make_unknown_battle_fact(), "fainted": row["fainted"], "condition": make_unknown_battle_fact(), "known_item": make_unknown_battle_fact()}
        for slot, row in pokemon.items()
    }
    return {"state_version": "battle-state-v1", "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": normalized, "side_conditions": make_unknown_battle_fact()}, "opponent_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "opponent", "current_hp": make_unknown_battle_fact(), "max_hp": make_unknown_battle_fact(), "fainted": make_unknown_battle_fact(), "condition": make_unknown_battle_fact(), "known_item": make_unknown_battle_fact()}}, "side_conditions": make_unknown_battle_fact()}, "field": {"weather": make_unknown_battle_fact(), "terrain": make_unknown_battle_fact()}, "last_applied_observation_sequence": None}


def _snapshot(context):
    return build_request_start_recommendation_snapshot(
        {"current_state_session_id": context["session_id"], "switch_candidate_context": context, "pokemon": {"my_active": {"name_en": "pikachu-a", "slot_index": 0}, "opponent_active": {"name_en": "opponent", "slot_index": 0}}, "moves": {"my_available_moves": []}},
        selectable_moves=(),
    )


def test_projection_enumerates_only_frozen_bench_in_slot_order_with_distinct_session_identity():
    context = build_switch_candidate_context_projection(_state())
    candidates = build_switch_candidates(turn_snapshot=_snapshot(context))
    assert [(row["target_slot_index"], row["target_pokemon_id"]) for row in candidates] == [(1, "pikachu-b"), (2, "eevee"), (3, "mew")]
    assert [row["candidate_id"] for row in candidates] == ["self-switch:switch-session:1:pikachu-b", "self-switch:switch-session:2:eevee", "self-switch:switch-session:3:mew"]
    assert all(row["action_kind"] == "switch" and not row["candidate_id"].startswith("self:") for row in candidates)
    other = build_switch_candidates(turn_snapshot=_snapshot(build_switch_candidate_context_projection(_state("next-session"))))
    assert candidates[0]["candidate_id"] != other[0]["candidate_id"]


def test_availability_tri_state_and_unsupported_prospective_legality_are_conservative():
    candidates = {row["target_pokemon_id"]: row for row in build_switch_candidates(turn_snapshot=_snapshot(build_switch_candidate_context_projection(_state())))}
    assert candidates["pikachu-b"]["availability_supportability"] == "complete"
    assert candidates["pikachu-b"]["legality_supportability"] == "unsupported_mechanic"
    assert candidates["pikachu-b"]["selectable"] is False and candidates["pikachu-b"]["reason_code"] == "switch_legality_unsupported"
    assert candidates["eevee"]["selectable"] is False and candidates["eevee"]["reason_code"] == "target_fainted"
    assert candidates["mew"]["availability_supportability"] == "insufficient_context"
    assert candidates["mew"]["selectable"] is False and candidates["mew"]["reason_code"] == "target_availability_unknown"


def test_snapshot_is_detached_and_historical_or_hp_data_cannot_promote_switch_legality():
    state = _state()
    context = build_switch_candidate_context_projection(state)
    snapshot = _snapshot(context)
    before = build_switch_candidates(turn_snapshot=snapshot)
    state["self_side"]["pokemon"][3]["fainted"] = False
    state["self_side"]["pokemon"][3]["current_hp"] = 100
    after = build_switch_candidates(turn_snapshot=snapshot)
    assert before == after
    assert next(row for row in after if row["target_pokemon_id"] == "mew")["selectable"] is False
    assert all("historical_switch" not in row and "current_hp" not in row for row in after)
    detached = deepcopy(after); detached[0]["selectable"] = True
    assert build_switch_candidates(turn_snapshot=snapshot)[0]["selectable"] is False


def test_cycle_keeps_switch_candidates_internal_and_move_provider_contract_unchanged():
    battle = _battle(known_action_order=True)
    state = _state("multi-smoke", {0: {"pokemon_id": "pikachu", "fainted": False}, 1: {"pokemon_id": "pikachu-b", "fainted": False}})
    battle["switch_candidate_context"] = build_switch_candidate_context_projection(state)
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "tackle"}]
    prepared = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=battle, move_repository={"tackle": {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "target": "selected-pokemon", "priority": 0}})
    payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    serialized = json.dumps(payload, sort_keys=True)
    assert prepared["status"] == "ready"
    assert prepared["evidence_bundle"]["switch_candidates"][0]["target_pokemon_id"] == "pikachu-b"
    assert payload["selectable_candidate_exact_set"] == [{"slot_index": 0, "move": "tackle"}]
    assert not any(key in serialized for key in ("switch_candidates", "switch_candidate_context", "target_pokemon_id", "legality_supportability"))
