from copy import deepcopy

import pytest

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_production_paralysis_application import admit_champions_paralysis_application
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _manager(*, target_type="normal", target_ability="pressure", condition="none"):
    state = create_unknown_bootstrap_battle_state("paralysis-production", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=80, max_hp=100, fainted=False)
    target = state["opponent_side"]["pokemon"][0]
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [
        {"observation_id": "condition", "observation_sequence": 1, "planned_effect": "set_current_condition", "trust": "user_confirmed_observation", "turn_number": 1, "side": "opponent", "slot_index": 0, "pokemon_id": target["pokemon_id"], "condition": condition},
        {"observation_id": "type", "observation_sequence": 2, "planned_effect": "set_current_type", "trust": "user_confirmed_observation", "turn_number": 1, "side": "opponent", "slot_index": 0, "pokemon_id": target["pokemon_id"], "types": [target_type]},
        {"observation_id": "target-ability", "observation_sequence": 3, "planned_effect": "set_current_ability", "trust": "user_confirmed_observation", "turn_number": 1, "side": "opponent", "slot_index": 0, "pokemon_id": target["pokemon_id"], "ability": target_ability},
        {"observation_id": "actor-ability", "observation_sequence": 4, "planned_effect": "set_current_ability", "trust": "user_confirmed_observation", "turn_number": 1, "side": "self", "slot_index": 0, "pokemon_id": "self-a", "ability": "pressure"},
    ]}
    projected = project_atomic_transition(state, plan, state["session_id"])["projected_state"]
    return BattleObservationRuntimeSessionManager.create(state["session_id"], projected)["manager"]


def _success(manager, move="thunder-wave", outcome="hit", **changes):
    snapshot = manager.capture_runtime_state_snapshot("paralysis-production")
    actor = {"session_id": "paralysis-production", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    target = {"session_id": "paralysis-production", "side": "opponent", "slot_index": 0, "pokemon_id": "opponent-a"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    return {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "actor": actor, "target": target, "action_id": f"attack:{move}", "move_id": move, "outcome": outcome, **changes}


def _admit(manager, move="thunder-wave", **kwargs):
    success = kwargs.pop("move_success_authority", _success(manager, move, **({"damage_resolved": True} if move == "nuzzle" else {})))
    return admit_champions_paralysis_application(runtime_session_manager=manager, captured_session_id="paralysis-production", target_side="opponent", move_id=move, action_id=f"attack:{move}", move_success_authority=success, turn_number=2, **kwargs)


def test_thunder_wave_exact_hit_writes_existing_current_condition_owner():
    manager = _manager(); before = manager.read_state()
    result = _admit(manager)
    assert result["status"] == "resolved", result
    raw = manager.read_state()["state"]["opponent_side"]["pokemon"][0]
    assert raw["condition"] == "paralysis"
    assert raw["condition_provenance"]["event_kind"] == "current_condition_observed"
    assert raw["condition_provenance"]["source_observation_id"].startswith("paralysis-production:paralysis:")
    assert manager.read_state()["state"] != before["state"]


@pytest.mark.parametrize(("outcome", "expected"), [("missed", "move_missed"), ("blocked_by_protection", "blocked_by_protection")])
def test_thunder_wave_prevented_outcomes_do_not_write_condition(outcome, expected):
    manager = _manager(); before = manager.read_state()
    assert _admit(manager, move_success_authority=_success(manager, outcome=outcome))["outcome"] == expected
    assert manager.read_state() == before


@pytest.mark.parametrize(("kwargs", "expected"), [({"target_type": "electric"}, "blocked_by_electric_type"), ({"target_ability": "limber"}, "blocked_by_limber"), ({"condition": "burn"}, "target_already_major_statused")])
def test_thunder_wave_exact_prevention_boundaries(kwargs, expected):
    manager = _manager(**kwargs); before = manager.read_state()
    assert _admit(manager)["outcome"] == expected and manager.read_state() == before


def test_nuzzle_commits_exact_hp_before_paralysis_atomically():
    manager = _manager(); result = _admit(manager, "nuzzle", hp_after=60)
    assert result["status"] == "resolved", result
    assert [row["event_kind"] for row in result["observation_transaction"]] == ["exact_hp_transition_observed", "current_condition_observed"]
    raw = manager.read_state()["state"]["opponent_side"]["pokemon"][0]
    assert raw["current_hp"] == 60 and raw["condition"] == "paralysis"


def test_nuzzle_missing_damage_authority_or_terminal_target_fails_closed_correctly():
    manager = _manager(); before = manager.read_state(); bad = _success(manager, "nuzzle")
    assert _admit(manager, "nuzzle", hp_after=60, move_success_authority=bad)["status"] == "rejected" and manager.read_state() == before
    result = _admit(manager, "nuzzle", hp_after=0)
    assert result["status"] == "resolved" and manager.read_state()["state"]["opponent_side"]["pokemon"][0]["condition"] is None


def test_stale_or_foreign_success_cannot_overwrite_runtime():
    manager = _manager(); before = manager.read_state(); stale = _success(manager)
    stale["source_runtime_fingerprint"] = "stale"
    assert _admit(manager, move_success_authority=stale)["status"] in {"incomplete", "rejected"}
    assert manager.read_state() == before
