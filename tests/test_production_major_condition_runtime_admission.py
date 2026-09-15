from copy import deepcopy

import pytest

from llm.advisor_current_condition_observation import admit_current_condition_observation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_production_paralysis_application import admit_observed_champions_paralysis_result
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _manager(*, target_type="normal", target_ability="pressure", condition="none"):
    state = create_unknown_bootstrap_battle_state("major-condition-production", "self-a", "opponent-a")["state"]
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


@pytest.mark.parametrize("condition", ["burn", "poison", "toxic", "paralysis", "sleep", "freeze", "none"])
def test_explicit_major_condition_admission_reaches_exact_runtime_and_d0(condition):
    manager = _manager()
    result = admit_current_condition_observation(runtime_session_manager=manager, captured_session_id="major-condition-production", side="self", condition=condition, turn_number=2)
    assert result["status"] == "resolved", result
    raw = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert raw["condition"] == (None if condition == "none" else condition)
    assert raw["condition_provenance"]["event_kind"] == "current_condition_observed"
    snapshot = manager.capture_runtime_state_snapshot("major-condition-production")
    owner = {"session_id": "major-condition-production", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    assert freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)["current_condition_authority"]["self"]["condition"]["status"] == ("known_none" if condition == "none" else "known_present")


def test_condition_admission_is_side_neutral_and_rejects_invalid_or_stale_owner_state():
    manager = _manager(); before = deepcopy(manager.read_state())
    assert admit_current_condition_observation(runtime_session_manager=manager, captured_session_id="wrong", side="self", condition="burn", turn_number=2)["status"] == "rejected"
    assert admit_current_condition_observation(runtime_session_manager=manager, captured_session_id="major-condition-production", side="self", condition="unknown", turn_number=2)["status"] == "rejected"
    assert manager.read_state() == before
    result = admit_current_condition_observation(runtime_session_manager=manager, captured_session_id="major-condition-production", side="opponent", condition="burn", turn_number=2)
    assert result["status"] == "resolved"
    assert manager.read_state()["state"]["opponent_side"]["pokemon"][0]["condition"] == "burn"


@pytest.mark.parametrize(("move_id", "outcome", "kwargs", "expected"), [
    ("thunder-wave", "hit", {}, "paralysis"),
    ("thunder-wave", "missed", {}, "none"),
    ("thunder-wave", "blocked_by_protection", {}, "none"),
    ("nuzzle", "hit", {"hp_after": 60}, "paralysis"),
])
def test_observed_paralysis_result_production_caller_reuses_canonical_owner(move_id, outcome, kwargs, expected):
    manager = _manager()
    result = admit_observed_champions_paralysis_result(runtime_session_manager=manager, captured_session_id="major-condition-production", target_side="opponent", move_id=move_id, outcome=outcome, turn_number=2, **kwargs)
    assert result["status"] == "resolved", result
    raw = manager.read_state()["state"]["opponent_side"]["pokemon"][0]
    assert raw["condition"] == ("paralysis" if expected == "paralysis" else None)
    if move_id == "nuzzle":
        assert [row["event_kind"] for row in result["observation_transaction"]] == ["exact_hp_transition_observed", "current_condition_observed"]
        assert raw["current_hp"] == 60


@pytest.mark.parametrize(("kwargs", "reason"), [
    ({"target_type": "electric"}, "blocked_by_electric_type"),
    ({"target_ability": "limber"}, "blocked_by_limber"),
    ({"condition": "burn"}, "target_already_major_statused"),
])
def test_observed_paralysis_result_preserves_prevention_without_mutation(kwargs, reason):
    manager = _manager(**kwargs); before = deepcopy(manager.read_state())
    result = admit_observed_champions_paralysis_result(runtime_session_manager=manager, captured_session_id="major-condition-production", target_side="opponent", move_id="thunder-wave", outcome="hit", turn_number=2)
    assert result["status"] == "resolved" and result["outcome"] == reason
    assert manager.read_state() == before


def test_nuzzle_requires_exact_post_hit_hp_and_never_partially_commits():
    manager = _manager(); before = deepcopy(manager.read_state())
    result = admit_observed_champions_paralysis_result(runtime_session_manager=manager, captured_session_id="major-condition-production", target_side="opponent", move_id="nuzzle", outcome="hit", turn_number=2)
    assert result["status"] == "rejected" and manager.read_state() == before


def test_nuzzle_prevention_preserves_exact_damage_without_a_condition():
    manager = _manager(target_type="electric")
    result = admit_observed_champions_paralysis_result(runtime_session_manager=manager, captured_session_id="major-condition-production", target_side="opponent", move_id="nuzzle", outcome="hit", turn_number=2, hp_after=60)
    assert result["status"] == "resolved" and result["outcome"] == "blocked_by_electric_type"
    assert [row["event_kind"] for row in result["observation_transaction"]] == ["exact_hp_transition_observed"]
    raw = manager.read_state()["state"]["opponent_side"]["pokemon"][0]
    assert raw["current_hp"] == 60 and raw["condition"] is None


def test_nuzzle_terminal_target_has_no_usable_paralysis():
    manager = _manager()
    result = admit_observed_champions_paralysis_result(runtime_session_manager=manager, captured_session_id="major-condition-production", target_side="opponent", move_id="nuzzle", outcome="hit", turn_number=2, hp_after=0)
    assert result["status"] == "resolved"
    raw = manager.read_state()["state"]["opponent_side"]["pokemon"][0]
    assert raw["current_hp"] == 0 and raw["condition"] is None
