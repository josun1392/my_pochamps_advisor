from copy import deepcopy

from llm.advisor_battle_state_store import BattleStateStore
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, execute_atomic_transition


def state(session="s", sequence=None):
    return {"state_version": STATE_MODEL_VERSION, "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": 80, "max_hp": 100, "fainted": False, "condition": None, "known_item": "berry"}}}, "opponent_side": {"active_slot_index": 0, "pokemon": {}}, "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": sequence, "q12": {"roll": 10}, "ranking": ["tackle"]}


def plan():
    return {"session_id": "s", "status": "planned", "conflicts": [], "replay_policy_version": "v1", "ordered_steps": [{"observation_id": "hp", "observation_sequence": 1, "planned_effect": "apply_exact_hp_transition", "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "hp_before": 80, "hp_after": 40}]}


def test_initialization_uninitialized_and_detached_read():
    assert BattleStateStore().read_snapshot()["status"] == "uninitialized"
    initial = state(); store = BattleStateStore(initial); initial["self_side"]["pokemon"][0]["current_hp"] = 1
    first = store.read_snapshot(); first["state"]["self_side"]["pokemon"][0]["current_hp"] = 2
    assert store.read_snapshot()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80
    assert store.read_snapshot("old")["status"] == "session_mismatch"


def test_successful_cas_stale_writer_and_already_current():
    store = BattleStateStore(state()); a, b = store.read_snapshot(), store.read_snapshot()
    candidate = deepcopy(a["state"]); candidate["last_applied_observation_sequence"] = 1; candidate["self_side"]["pokemon"][0]["current_hp"] = 40
    replaced = store.compare_and_replace(candidate, expected_session_id="s", expected_base_fingerprint=a["state_fingerprint"])
    assert replaced["status"] == "replaced" and replaced["state_snapshot"]["self_side"]["pokemon"][0]["current_hp"] == 40
    assert store.compare_and_replace(candidate, expected_session_id="s", expected_base_fingerprint=b["state_fingerprint"])["status"] == "stale_state"
    current = store.read_snapshot()
    assert store.compare_and_replace(current["state"], expected_session_id="s", expected_base_fingerprint=current["state_fingerprint"])["status"] == "already_current"


def test_session_version_sequence_and_new_session_isolation():
    store = BattleStateStore(state(sequence=2)); current = store.read_snapshot()
    old = deepcopy(current["state"]); old["last_applied_observation_sequence"] = 1
    assert store.compare_and_replace(old, expected_session_id="s", expected_base_fingerprint=current["state_fingerprint"])["status"] == "sequence_regression"
    wrong = state(); wrong["state_version"] = "battle-state-v2"
    assert store.compare_and_replace(wrong, expected_session_id="s", expected_base_fingerprint=current["state_fingerprint"])["status"] == "unsupported_state_version"
    assert store.compare_and_replace(state("other", 3), expected_session_id="s", expected_base_fingerprint=current["state_fingerprint"])["status"] == "session_mismatch"
    old_snapshot = deepcopy(current["state"]); new = state("new")
    assert store.start_new_session(new, "new")["status"] == "session_started"
    assert store.read_snapshot("s")["status"] == "session_mismatch" and old_snapshot["session_id"] == "s"


def test_executor_parity_and_nonintegration_boundaries():
    initial = state(); store = BattleStateStore(initial); read = store.read_snapshot()
    execution = execute_atomic_transition(read["state"], plan(), expected_base_fingerprint=read["state_fingerprint"])
    result = store.compare_and_replace(execution["committed_state"], expected_session_id="s", expected_base_fingerprint=read["state_fingerprint"])
    assert result["status"] == "replaced" and result["state_snapshot"]["q12"] == {"roll": 10} and result["state_snapshot"]["ranking"] == ["tackle"]
    assert BattleStateStore({"state_version": STATE_MODEL_VERSION, "session_id": "s"}).read_snapshot()["status"] == "uninitialized"
