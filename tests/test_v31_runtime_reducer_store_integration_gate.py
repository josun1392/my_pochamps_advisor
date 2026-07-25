from copy import deepcopy

from llm.advisor_battle_state_store import BattleStateStore
from llm.advisor_observation_replay_coordinator import ObservationReplayCoordinator
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION


def state(session="s"):
    return {"state_version": STATE_MODEL_VERSION, "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": 80, "max_hp": 100, "fainted": False, "condition": None, "known_item": "berry"}}, "side_conditions": []}, "opponent_side": {"active_slot_index": 0, "pokemon": {}}, "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": None, "q12": {"damage": 99}}
def event(oid="hp", seq=1, **x):
    return {"event_kind": "exact_hp_transition_observed", "reducer_eligibility": "candidate", "observation_id": oid, "observation_sequence": seq, "session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "hp_before": 80, "hp_after": 40, "payload": {"hp_before": 80, "hp_after": 40}, **x}
def snapshot(*events, session="s"): return {"status": "ready", "session_id": session, "ordered_observations": list(events)}

def test_preview_is_detached_and_damage_only_never_infers_hp():
    store=BattleStateStore(state()); coordinator=ObservationReplayCoordinator(store); before=store.read_snapshot()
    result=coordinator.preview(snapshot(event()))
    assert result["status"]=="preview_ready" and result["projected_state"]["self_side"]["pokemon"][0]["current_hp"]==40
    assert store.read_snapshot()==before
    damage={"event_kind":"direct_move_damage_observed","reducer_eligibility":"evidence_only","observation_id":"damage","observation_sequence":1,"session_id":"s","payload":{"damage_amount":31}}
    assert coordinator.preview(snapshot(damage))["status"]=="no_eligible_observations"

def test_apply_is_explicit_idempotent_atomic_and_session_safe():
    store=BattleStateStore(state()); coordinator=ObservationReplayCoordinator(store); frozen=snapshot(event())
    applied=coordinator.apply_confirmed_observations(frozen)
    assert applied["status"]=="applied" and store.read_snapshot()["state"]["q12"]=={"damage":99}
    assert coordinator.apply_confirmed_observations(frozen)["status"]=="already_applied"
    changed=deepcopy(frozen); changed["ordered_observations"][0]["hp_after"]=1
    assert coordinator.preview(changed)["status"]=="transition_invalid"
    assert coordinator.preview(snapshot(event(),session="old"))["status"]=="session_mismatch"

def test_cas_conflict_and_invalid_batch_do_not_commit_or_update_ledger():
    store=BattleStateStore(state()); coordinator=ObservationReplayCoordinator(store); frozen=snapshot(event())
    store.compare_and_replace=lambda *args, **kwargs: {"status":"stale_state"}
    assert coordinator.apply_confirmed_observations(frozen)["status"]=="cas_conflict"
    bad=snapshot(event("ok",1),event("bad",2,hp_before=79,hp_after=20))
    assert ObservationReplayCoordinator(BattleStateStore(state())).apply_confirmed_observations(bad)["status"]=="transition_invalid"
