from llm.advisor_battle_state_store import BattleStateStore
from llm.advisor_reducer_state_model import make_unknown_battle_fact
from llm.advisor_switch_permission_capture import capture_switch_permission
from llm.advisor_switch_candidates import build_switch_candidate_context_projection


def _state(session="s"):
    row = lambda pid: {"pokemon_id": pid, "current_hp": make_unknown_battle_fact(), "max_hp": make_unknown_battle_fact(), "fainted": False, "condition": make_unknown_battle_fact(), "known_item": make_unknown_battle_fact()}
    return {"state_version": "battle-state-v1", "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": {0: row("a"), 1: row("b")}, "side_conditions": make_unknown_battle_fact()}, "opponent_side": {"active_slot_index": 0, "pokemon": {0: row("x")}, "side_conditions": make_unknown_battle_fact()}, "field": {"weather": make_unknown_battle_fact(), "terrain": make_unknown_battle_fact()}, "last_applied_observation_sequence": None}


def test_manual_capture_permitted_blocked_unknown_and_identity_guards():
    store = BattleStateStore(_state())
    assert build_switch_candidate_context_projection(store.read_snapshot()["state"])["switch_permission_context"]["status"] == "unknown"
    assert capture_switch_permission(store=store, session_id="s", active_slot_index=0, active_pokemon_id="a", permission="permitted", observation_id="p", observation_sequence=1)["status"] == "captured"
    assert build_switch_candidate_context_projection(store.read_snapshot()["state"])["switch_permission_context"]["status"] == "permitted"
    assert capture_switch_permission(store=store, session_id="s", active_slot_index=0, active_pokemon_id="a", permission="unknown", observation_id="u", observation_sequence=2)["status"] == "captured"
    assert build_switch_candidate_context_projection(store.read_snapshot()["state"])["switch_permission_context"]["status"] == "unknown"
    assert capture_switch_permission(store=store, session_id="old", active_slot_index=0, active_pokemon_id="a", permission="blocked", observation_id="x", observation_sequence=3)["status"] == "stale_or_unavailable"
    assert capture_switch_permission(store=store, session_id="s", active_slot_index=1, active_pokemon_id="b", permission="blocked", observation_id="x", observation_sequence=3)["status"] == "active_identity_mismatch"
