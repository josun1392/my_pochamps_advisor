from copy import deepcopy

import pytest

from llm.advisor_champions_confusion_action_gate import freeze_champions_confusion_action_gate
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import CONFUSION_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_production_confusion_integration import admit_current_confusion_state
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _manager():
    state = create_unknown_bootstrap_battle_state("confusion-production", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(fainted=False)
    return BattleObservationRuntimeSessionManager.create("confusion-production", state)["manager"]


def _admit(manager, **kwargs):
    values = {"state": "confused", "newly_established": False, **kwargs}
    return admit_current_confusion_state(
        runtime_session_manager=manager, captured_session_id="confusion-production",
        side="self", turn_number=1, **values,
    )


def test_newly_established_confusion_is_atomic_and_reaches_action_gate():
    manager = _manager()
    result = _admit(manager, newly_established=True)
    assert result["status"] == "resolved", result
    assert [row["event_kind"] for row in result["observation_transaction"]] == ["current_confusion_state_observed", "champions_confusion_progression_observed"]
    snapshot = manager.capture_runtime_state_snapshot("confusion-production")
    for side in ("self", "opponent"):
        pokemon = snapshot["state"][f"{side}_side"]["pokemon"][0]
        pokemon["current_ability"] = "pressure"
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    from llm.advisor_reducer_state_model import state_fingerprint
    snapshot["state_fingerprint"] = state_fingerprint(snapshot["state"])
    raw = snapshot["state"]["self_side"]["pokemon"][0]
    assert raw["current_confusion"] == "confused"
    assert raw["confusion_provenance"]["event_kind"] == "current_confusion_observed"
    assert raw["champions_confusion_progression"]["prior_opportunities"] == 0
    assert raw["champions_confusion_progression"]["duration"] is None
    owner = {"session_id": "confusion-production", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    gate = freeze_champions_confusion_action_gate(strategy_d0=d0, runtime_snapshot=snapshot, actor=owner, action_id="a", move_id="tackle", action_order={})
    assert gate["status"] == "resolved", gate
    assert {row["kind"] for row in gate["branches"]} >= {"confusion_self_hit", "confusion_selected_action_executes"}


def test_known_existing_confusion_does_not_invent_progression_and_clear_retires_it():
    manager = _manager()
    assert _admit(manager, newly_established=False)["status"] == "resolved"
    raw = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert raw["current_confusion"] == "confused" and raw.get("champions_confusion_progression") is None
    assert _admit(manager, state="none", newly_established=False)["status"] == "resolved"
    raw = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert raw["current_confusion"] == "none" and raw["champions_confusion_progression"] is None


def test_missing_history_fails_closed_while_explicit_none_executes_normally():
    manager = _manager(); snapshot = manager.capture_runtime_state_snapshot("confusion-production")
    owner = {"session_id": "confusion-production", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    assert freeze_champions_confusion_action_gate(strategy_d0=d0, runtime_snapshot=snapshot, actor=owner, action_id="a", move_id="tackle", action_order={})["status"] == "incomplete"
    assert _admit(manager, state="none")["status"] == "resolved"
    snapshot = manager.capture_runtime_state_snapshot("confusion-production")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    gate = freeze_champions_confusion_action_gate(strategy_d0=d0, runtime_snapshot=snapshot, actor=owner, action_id="a", move_id="tackle", action_order={})
    assert gate["status"] == "resolved" and gate["branches"][0]["kind"] == "executes"


def test_lifecycle_rejects_stale_wrong_or_malformed_confusion_observations():
    state = _manager().read_state()["state"]
    owners = {side: {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]} for side in ("self", "opponent")}
    boundary = LifecycleConfirmationBoundary(state["session_id"], owners)
    base = dict(event_kind="current_confusion_state_observed", payload={"state": "confused"}, session_id=state["session_id"], source=CONFUSION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="self-a", turn_number=1)
    assert boundary.confirm(**{**base, "session_id": "foreign"})["status"] == "stale_session"
    assert boundary.confirm(**{**base, "pokemon_id": "wrong"})["status"] == "invalid_provenance"
    assert boundary.confirm(**{**base, "payload": {"state": "unknown"}})["status"] == "invalid_provenance"


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_active_owner_side_binding_and_switch_retirement(side):
    manager = _manager()
    assert admit_current_confusion_state(runtime_session_manager=manager, captured_session_id="confusion-production", side=side, state="confused", newly_established=True, turn_number=1)["status"] == "resolved"
    state = manager.read_state()["state"]
    target = state[f"{side}_side"]
    bench = deepcopy(target["pokemon"][0]); bench["pokemon_id"] = f"{side}-bench"; bench["current_confusion"] = "none"; bench["champions_confusion_progression"] = None
    target["pokemon"][1] = bench
    # The existing reducer switch lifecycle is the only retirement owner.
    from llm.advisor_reducer_state_model import project_atomic_transition
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{"observation_id": "switch", "observation_sequence": 9, "planned_effect": "switch_active", "trust": USER_TRUST, "turn_number": 2, "side": side, "switch_out_slot_index": 0, "switch_out_pokemon_id": f"{side}-a", "switch_in_slot_index": 1, "switch_in_pokemon_id": f"{side}-bench"}]}
    projected = project_atomic_transition(state, plan, state["session_id"])["projected_state"]
    assert projected[f"{side}_side"]["pokemon"][0]["current_confusion"] == "none"
    assert projected[f"{side}_side"]["pokemon"][0]["champions_confusion_progression"] is None
    assert projected[f"{side}_side"]["pokemon"][1]["current_confusion"] == "none"


def test_fainted_or_stale_owner_fails_closed_without_mutation():
    manager = _manager(); before = manager.read_state()
    assert admit_current_confusion_state(runtime_session_manager=manager, captured_session_id="wrong", side="self", state="confused", newly_established=False, turn_number=1)["status"] == "rejected"
    state = manager.read_state()["state"]; state["self_side"]["pokemon"][0]["fainted"] = True
    fainted = BattleObservationRuntimeSessionManager.create("confusion-production", state)["manager"]
    assert _admit(fainted)["status"] == "rejected"
    assert manager.read_state() == before
