from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    DOUBLES_ACTIVE_TOPOLOGY_SOURCE,
    SELECTED_ACTION_TARGETING_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_doubles_action_target_set_authority import (
    SCHEMA_VERSION,
    freeze_runtime_d0_doubles_action_target_set_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state(*, battle_format="doubles"):
    state = create_unknown_bootstrap_battle_state("doubles-targets", "self-a", "opponent-a", battle_format={"battle_format": battle_format, "source": "user_confirmed_battle_format"})["state"]
    for side in ("self", "opponent"):
        roster = state[f"{side}_side"]["pokemon"]
        roster[0].update(current_hp=100, max_hp=100, fainted=False)
        roster[1] = deepcopy(roster[0]); roster[1]["pokemon_id"] = f"{side}-b"
    return state


def _owner(state, side, slot=0):
    pokemon = state[f"{side}_side"]["pokemon"][slot]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _boundary(state):
    return LifecycleConfirmationBoundary(state["session_id"], {side: _owner(state, side) for side in ("self", "opponent")})


def _topology_observation(state, *, boundary=None, sequence=None):
    rows = [{"side": side, "active_slot_index": slot, "pokemon_id": _owner(state, side, slot)["pokemon_id"], "active": True} for side in ("self", "opponent") for slot in (0, 1)]
    result = (boundary or _boundary(state)).confirm(event_kind="doubles_active_topology_observed", payload={"active_owners": rows}, session_id=state["session_id"], source=DOUBLES_ACTIVE_TOPOLOGY_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=1)
    assert result["status"] == "confirmed", result
    if sequence is not None: result["observation"]["observation_sequence"] = sequence
    return result["observation"]


def _targeting_observation(state, *, target=None, boundary=None, action_id="attack:spread", move_id="spread", decision_point="turn:1", sequence=None):
    actor = _owner(state, "self")
    payload = {"decision_point": decision_point, "action_id": action_id, "move_id": move_id, "selected_target": None if target is None else {"side": target["side"], "active_slot_index": target["slot_index"], "pokemon_id": target["pokemon_id"]}}
    result = (boundary or _boundary(state)).confirm(event_kind="selected_action_targeting_observed", payload=payload, session_id=state["session_id"], source=SELECTED_ACTION_TARGETING_SOURCE, trust=USER_TRUST, confirmed=True, side=actor["side"], slot_index=actor["slot_index"], pokemon_id=actor["pokemon_id"], turn_number=1)
    assert result["status"] == "confirmed", result
    if sequence is not None: result["observation"]["observation_sequence"] = sequence
    return result["observation"]


def _project(state, observations):
    result = project_atomic_transition(state, build_replay_plan(state, observations), state["session_id"])
    assert result["status"] == "ready_with_projected_state", result
    return result["projected_state"]


def _action(d0, *, move_id="spread", target="all-opponents"):
    metadata = {"move_id": move_id, "category": "special", "power": 80, "type": "water", "accuracy": 100, "priority": 0, "target": target}
    authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": metadata, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "active_attacker": deepcopy(d0["decision_owner"])}
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}


def _freeze(state, *, action=None, decision_point="turn:1"):
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return freeze_runtime_d0_doubles_action_target_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action or _action(d0), acting_owner=_owner(state, "self"), decision_point=decision_point)


def test_exact_doubles_topology_expands_selected_and_spread_recipients_without_mutation():
    state = _state(); before = deepcopy(state); boundary = _boundary(state)
    topology = _topology_observation(state, boundary=boundary)
    targeting = _targeting_observation(state, boundary=boundary)
    state = _project(state, [topology, targeting])
    spread = _freeze(state)
    assert spread["status"] == "resolved" and spread["schema_version"] == SCHEMA_VERSION
    assert spread["recipient_classification"] == "spread_multi_target"
    assert [(row["side"], row["active_slot_index"]) for row in spread["recipients"]] == [("opponent", 0), ("opponent", 1)]

    selected_target = _owner(state, "opponent", 1)
    target = _targeting_observation(state, target=selected_target, action_id="attack:single", move_id="single", decision_point="turn:2", sequence=3)
    state = _project(state, [target])
    single = _freeze(state, action=_action(freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state), decision_owner=_owner(state, "self")), move_id="single", target="selected-pokemon"), decision_point="turn:2")
    assert single["status"] == "resolved" and len(single["recipients"]) == 1
    assert single["recipients"][0]["owner"] == selected_target and single["recipients"][0]["selected"] is True
    assert before["self_side"]["pokemon"][0]["pokemon_id"] == "self-a"


def test_missing_and_invalid_targeting_facts_fail_closed():
    state = _state(); assert _freeze(state)["status"] == "incomplete"
    boundary = _boundary(state); state = _project(state, [_topology_observation(state, boundary=boundary), _targeting_observation(state, boundary=boundary, action_id="attack:single", move_id="single")])
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state), decision_owner=_owner(state, "self"))
    selected = _action(d0, move_id="single", target="selected-pokemon")
    assert _freeze(state, action=selected)["status"] == "incomplete"

    foreign = _owner(state, "opponent", 0) | {"slot_index": 9, "pokemon_id": "not-active"}
    observation = _targeting_observation(state, target=foreign, action_id="attack:single", move_id="single", decision_point="turn:2", sequence=3)
    invalid = _project(state, [observation])
    assert _freeze(invalid, action=_action(freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(invalid), decision_owner=_owner(invalid, "self")), move_id="single", target="selected-pokemon"), decision_point="turn:2")["status"] == "rejected"


def test_stale_and_conflicting_topology_or_action_bindings_reject():
    state = _state(); boundary = _boundary(state)
    topology, targeting = _topology_observation(state, boundary=boundary), _targeting_observation(state, boundary=boundary)
    state = _project(state, [topology, targeting])
    stale = deepcopy(state); stale["last_applied_observation_sequence"] += 1
    assert _freeze(stale)["status"] == "rejected"
    assert _freeze(state, decision_point="other")["status"] == "rejected"

    duplicate = deepcopy(topology); duplicate["observation_id"] = "conflict"; duplicate["observation_sequence"] = 1; duplicate["payload"]["active_owners"][1] = deepcopy(duplicate["payload"]["active_owners"][0])
    result = project_atomic_transition(_state(), build_replay_plan(_state(), [topology, duplicate]), "doubles-targets")
    assert result["status"] == "blocked_by_semantic_conflict"


def test_singles_never_resolves_the_doubles_target_set_authority():
    state = _state(battle_format="singles")
    assert _freeze(state)["status"] == "incomplete"
