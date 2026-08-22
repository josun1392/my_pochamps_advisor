from copy import deepcopy

from llm.advisor_current_execution_authority import freeze_current_execution_authority
from llm.advisor_detached_strategy_orchestration import run_detached_strategy_orchestration
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_incoming_authority_boundary,
    freeze_runtime_strategy_d0,
    freeze_runtime_strategy_selection_authority,
    runtime_strategy_d0_freshness,
)
from llm.advisor_strategy_explanation import explain_detached_strategy


def _state(session: str = "runtime-d0") -> dict:
    return create_unknown_bootstrap_battle_state(session, "pikachu", "eevee")["state"]


def _snapshot(state: dict) -> dict:
    return {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }


def _owner(state: dict, side: str = "self") -> dict:
    slot = state[f"{side}_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _selection(d0: dict, *, source_fingerprint: str | None = None) -> dict:
    owner = d0["decision_owner"]
    return {
        "session_id": owner["session_id"],
        "source_runtime_fingerprint": source_fingerprint or d0["source_runtime_fingerprint"],
        "decision_owner": deepcopy(owner),
        "active_owner": deepcopy(owner),
        "moves": [
            {"move_id": "water-gun", "selection": "selectable", "execution_authority": {"forbidden": "selection_only"}},
            {"move_id": "tackle", "selection": "selection_unknown"},
        ],
        "switches": [{"pokemon_id": "bench", "selection": "not_selectable"}],
    }


def test_freezes_runtime_d0_with_both_fingerprints_exact_identities_and_known_hp() -> None:
    state = _state()
    state["self_side"]["pokemon"][0].update(current_hp=80, max_hp=100, fainted=False)
    state["opponent_side"]["pokemon"][0].update(current_hp=50, max_hp=100, fainted=False)
    snapshot = _snapshot(state)

    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))

    assert d0["status"] == "resolved"
    assert d0["source_runtime_fingerprint"] == snapshot["state_fingerprint"]
    assert d0["strategy_preview_fingerprint"] != d0["source_runtime_fingerprint"]
    assert d0["strategy_state"]["active"]["self"] == {**_owner(state), "current_hp": 80, "max_hp": 100, "fainted": False}
    assert d0["strategy_state"]["active"]["opponent"] == {**_owner(state, "opponent"), "current_hp": 50, "max_hp": 100, "fainted": False}
    assert runtime_strategy_d0_freshness(strategy_d0=d0, runtime_snapshot=snapshot)["status"] == "current"


def test_unknown_runtime_facts_remain_untracked_and_snapshot_is_detached() -> None:
    state = _state()
    snapshot = _snapshot(state)
    before = deepcopy(snapshot)

    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    snapshot["state"]["self_side"]["pokemon"][0]["pokemon_id"] = "changed"

    active = d0["strategy_state"]["active"]["self"]
    assert snapshot != before
    assert d0["decision_owner"] == _owner(state)
    assert set(active) == {"session_id", "side", "slot_index", "pokemon_id"}
    summary = d0["strategy_state"]["current_state"]["runtime_strategy_d0_authority"]
    assert summary["active"]["self"]["current_hp"] == {"status": "unknown"}
    assert summary["field"]["weather"] == {"status": "unknown"}
    assert "substitute" not in summary["active"]["self"]


def test_rejects_foreign_session_or_owner_and_detects_same_visible_state_new_revision() -> None:
    state = _state()
    snapshot = _snapshot(state)
    assert freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner={**_owner(state), "pokemon_id": "foreign"})["status"] == "rejected"
    foreign_snapshot = _snapshot(_state("foreign"))
    assert freeze_runtime_strategy_d0(runtime_snapshot=foreign_snapshot, decision_owner=_owner(state))["status"] == "rejected"
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    advanced = deepcopy(state)
    advanced["last_applied_observation_sequence"] = 1
    advanced_snapshot = _snapshot(advanced)
    assert runtime_strategy_d0_freshness(strategy_d0=d0, runtime_snapshot=advanced_snapshot) == {"status": "stale", "reason": "runtime_fingerprint_changed"}


def test_selection_join_is_d0_bound_detached_and_drops_execution_payload() -> None:
    state = _state()
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=_snapshot(state), decision_owner=_owner(state))
    projection = _selection(d0)

    selection = freeze_runtime_strategy_selection_authority(strategy_d0=d0, selection_projection=projection)
    projection["moves"][0]["selection"] = "not_selectable"

    assert selection["status"] == "resolved"
    attack = next(row for row in selection["actions"] if row["action_id"] == "attack:water-gun")
    assert attack["selection"] == "selectable"
    assert attack["execution_authority"] is None
    assert selection["selection_completeness"]["candidate_set"] == "partial"
    assert freeze_runtime_strategy_selection_authority(strategy_d0=d0, selection_projection=_selection(d0, source_fingerprint="stale"))["reason"] == "selection_projection_runtime_d0_mismatch"


def test_incoming_boundary_requires_current_runtime_d0_and_never_fabricates_execution_authority() -> None:
    state = _state()
    state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0])
    state["self_side"]["pokemon"][1]["pokemon_id"] = "bench"
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    incoming = {"session_id": state["session_id"], "side": "self", "slot_index": 1, "pokemon_id": "bench"}

    boundary = freeze_runtime_incoming_authority_boundary(strategy_d0=d0, runtime_snapshot=snapshot, incoming_owner=incoming)
    stale = deepcopy(state)
    stale["last_applied_observation_sequence"] = 1

    assert boundary["status"] == "resolved"
    assert boundary["execution_readiness"] == "execution_incomplete"
    assert boundary["reason"] == "runtime_incoming_current_state_adapter_unavailable"
    assert "authority" not in boundary
    assert freeze_runtime_incoming_authority_boundary(strategy_d0=d0, runtime_snapshot=_snapshot(stale), incoming_owner=incoming)["status"] == "rejected"


def test_detached_runtime_d0_can_flow_to_selection_execution_orchestration_and_explanation() -> None:
    state = _state()
    state["self_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    state["opponent_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    projection = _selection(d0)
    projection["moves"] = [{"move_id": "water-gun", "selection": "selectable"}]
    projection["switches"] = []
    selection = freeze_runtime_strategy_selection_authority(strategy_d0=d0, selection_projection=projection)
    execution = freeze_current_execution_authority(selection_snapshot=selection, switch_incoming=[])

    orchestration = run_detached_strategy_orchestration(
        decision_state=d0["strategy_state"], decision_owner=d0["decision_owner"],
        selection_snapshot=selection, execution_bundle=execution,
    )
    explanation = explain_detached_strategy(orchestration=orchestration)

    assert orchestration["status"] == "incomplete_comparison_set"
    assert orchestration["candidates"][0]["candidate_id"] == "attack:water-gun"
    assert orchestration["candidates"][0]["evidence_class"] == "incomplete"
    assert explanation["status"] == "resolved"
