from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_seismic_toss_predictive_input,
    freeze_runtime_strategy_d0,
)
from llm.advisor_substitute import update_substitute_state_context
from llm.advisor_predictive_attack_authority import build_predictive_fixed_damage_attack_authority
from llm.advisor_lifecycle_confirmation import (
    CURRENT_LEVEL_SOURCE,
    SUBSTITUTE_STATE_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


def _state(session: str = "runtime-seismic") -> dict:
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False)
    target = state["opponent_side"]["pokemon"][0]
    target["current_type"] = ["water"]
    target["current_type_provenance"] = {
        "event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1,
    }
    return state


def _snapshot(state: dict) -> dict:
    return {
        "status": "runtime_snapshot_ready", "session_id": state["session_id"],
        "state": deepcopy(state), "state_fingerprint": state_fingerprint(state),
    }


def _owner(state: dict, side: str = "self") -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def test_runtime_seismic_producer_freezes_known_hp_type_but_keeps_untracked_level_and_substitute_incomplete() -> None:
    state = _state(); snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))

    result = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="seismic-toss",
    )
    snapshot["state"]["opponent_side"]["pokemon"][0]["current_type"] = ["ghost"]

    assert result["status"] == "incomplete"
    assert result["target_hp_authority"] == {"status": "known", "current_hp": 100, "max_hp": 100}
    assert result["target_type_authority"]["value"] == ["water"]
    assert result["missing_authority"] == ["attacker_level_runtime_untracked", "substitute_state_unknown"]
    assert "observed" not in result["provenance"]


def test_runtime_seismic_producer_rejects_stale_foreign_or_unsupported_bindings() -> None:
    state = _state(); snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    advanced = deepcopy(state); advanced["last_applied_observation_sequence"] = 1

    assert freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=_snapshot(advanced), attacker=_owner(state), target=_owner(state, "opponent"), move_id="seismic-toss",
    )["status"] == "rejected"
    assert freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="night-shade",
    )["reason"] == "unsupported_predictive_move"
    assert freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_id="seismic-toss",
    )["reason"] == "runtime_predictive_identity_mismatch"


def test_runtime_seismic_producer_is_side_neutral_and_preserves_unknown_target_type() -> None:
    state = _state(); state["self_side"]["pokemon"][0]["current_type"] = {"knowledge": "unknown"}
    state["self_side"]["pokemon"][0]["current_type_provenance"] = None
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "opponent"))

    result = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state), move_id="seismic-toss",
    )

    assert result["status"] == "incomplete"
    assert result["target_type_authority"] == {"status": "unknown", "reason": "target_type_unknown"}
    assert result["attacker"] == _owner(state, "opponent")


def _observe_level_and_substitute(state: dict, *, substitute_state: str, substitute_hp: int | None = None) -> None:
    attacker = state["self_side"]["pokemon"][0]
    attacker["current_level"] = 50
    attacker["current_level_provenance"] = {
        "event_kind": "current_level_observed", "trust": "user_confirmed_observation", "turn_number": 1,
    }
    target = _owner(state, "opponent")
    state["substitute_state_context"] = update_substitute_state_context(
        context=None, session_id=state["session_id"], owner=target, state=substitute_state,
        substitute_hp=substitute_hp, provenance="runtime_observed_substitute_state_v1",
    )


def test_runtime_level_and_known_inactive_substitute_make_seismic_toss_exact_ready() -> None:
    state = _state()
    state["opponent_side"]["pokemon"][0].update(current_hp=42, max_hp=100)
    _observe_level_and_substitute(state, substitute_state="known_inactive")
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))

    frozen = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="seismic-toss",
    )
    authority = build_predictive_fixed_damage_attack_authority(
        branch_state=d0["strategy_state"], decision_owner=_owner(state), target_owner=_owner(state, "opponent"),
        move_id="seismic-toss", predictive_input=frozen["predictive_input"],
    )

    assert d0["strategy_state"]["active"]["self"]["current_level"] == 50
    assert frozen["status"] == "resolved"
    assert frozen["substitute_authority"] == {"status": "known", "state": "known_inactive"}
    assert authority["status"] == "resolved"
    assert authority["completeness"] == "exact_complete"
    assert authority["predicted_result"]["target_fainted"] is True


def test_runtime_known_active_substitute_routes_existing_seismic_toss_authority() -> None:
    state = _state()
    _observe_level_and_substitute(state, substitute_state="known_active", substitute_hp=30)
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    frozen = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="seismic-toss",
    )
    authority = build_predictive_fixed_damage_attack_authority(
        branch_state=d0["strategy_state"], decision_owner=_owner(state), target_owner=_owner(state, "opponent"),
        move_id="seismic-toss", predictive_input=frozen["predictive_input"],
    )

    assert frozen["status"] == "resolved"
    assert frozen["substitute_authority"] == {"status": "known", "state": "known_active", "substitute_hp": 30}
    assert authority["status"] == "resolved"
    assert authority["completeness"] == "exact_complete"
    assert authority["predicted_result"]["damage_route"] == "substitute"
    assert authority["predicted_result"]["target_fainted"] is False


def test_runtime_level_or_substitute_unknown_remains_explicitly_incomplete() -> None:
    level_unknown = _state()
    _observe_level_and_substitute(level_unknown, substitute_state="known_inactive")
    level_unknown["self_side"]["pokemon"][0]["current_level"] = {"knowledge": "unknown"}
    level_unknown["self_side"]["pokemon"][0]["current_level_provenance"] = None
    unknown_level_snapshot = _snapshot(level_unknown)
    unknown_level_d0 = freeze_runtime_strategy_d0(runtime_snapshot=unknown_level_snapshot, decision_owner=_owner(level_unknown))
    unknown_level = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=unknown_level_d0, runtime_snapshot=unknown_level_snapshot, attacker=_owner(level_unknown), target=_owner(level_unknown, "opponent"), move_id="seismic-toss",
    )

    substitute_unknown = _state()
    substitute_unknown["self_side"]["pokemon"][0].update(
        current_level=50,
        current_level_provenance={"event_kind": "current_level_observed", "trust": "user_confirmed_observation", "turn_number": 1},
    )
    substitute_unknown_snapshot = _snapshot(substitute_unknown)
    substitute_unknown_d0 = freeze_runtime_strategy_d0(runtime_snapshot=substitute_unknown_snapshot, decision_owner=_owner(substitute_unknown))
    unknown_substitute = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=substitute_unknown_d0, runtime_snapshot=substitute_unknown_snapshot, attacker=_owner(substitute_unknown), target=_owner(substitute_unknown, "opponent"), move_id="seismic-toss",
    )

    assert unknown_level["status"] == "incomplete"
    assert unknown_level["missing_authority"] == ["attacker_level_runtime_untracked"]
    assert unknown_substitute["status"] == "incomplete"
    assert unknown_substitute["missing_authority"] == ["substitute_state_unknown"]


def test_runtime_reducer_captures_identity_bound_level_and_substitute_observations() -> None:
    state = _state("captured-runtime")
    manager = BattleObservationRuntimeSessionManager.create("captured-runtime", state)["manager"]
    boundary = LifecycleConfirmationBoundary("captured-runtime", {
        "self": {"slot_index": 0, "pokemon_id": "attacker"},
        "opponent": {"slot_index": 0, "pokemon_id": "target"},
    })
    for confirmation in (
        boundary.confirm(event_kind="current_level_observed", payload={"level": 50}, session_id="captured-runtime", source=CURRENT_LEVEL_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="attacker", turn_number=1),
        boundary.confirm(event_kind="substitute_state_observed", payload={"state": "known_inactive", "substitute_hp": None}, session_id="captured-runtime", source=SUBSTITUTE_STATE_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=0, pokemon_id="target", turn_number=1),
    ):
        assert manager.admit_confirmation("captured-runtime", confirmation)["status"] == "added"
        assert manager.apply("captured-runtime", manager.read_collection_snapshot())["status"] == "applied"

    captured = manager.capture_runtime_state_snapshot("captured-runtime")
    current = captured["state"]
    assert current["self_side"]["pokemon"][0]["current_level"] == 50
    assert current["substitute_state_context"]["states"] == [{
        "owner": _owner(current, "opponent"), "state": "known_inactive", "substitute_hp": None,
    }]
