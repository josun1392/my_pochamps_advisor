from copy import deepcopy

from core.charge_move_repository import ChargeMoveRepository
from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    GRAVITY_SOURCE,
    LOCKED_ON_SOURCE,
    MAGIC_ROOM_SOURCE,
    TRICK_ROOM_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import (
    is_unknown_battle_fact,
    project_atomic_transition,
    validate_battle_state_unknown_markers,
)
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_locked_on_gravity_authority import (
    freeze_runtime_d0_gravity_field_authority,
    freeze_runtime_d0_locked_on_target_binding_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


SESSION = "locked-gravity"
SELF = {"session_id": SESSION, "side": "self", "slot_index": 0, "pokemon_id": "dragapult"}
OPP = {"session_id": SESSION, "side": "opponent", "slot_index": 0, "pokemon_id": "clefable"}
OPP_REPLACEMENT = {"session_id": SESSION, "side": "opponent", "slot_index": 1, "pokemon_id": "starmie"}


def _state():
    return create_unknown_bootstrap_battle_state(
        SESSION,
        "dragapult",
        "clefable",
        self_roster={0: "dragapult", 1: "pikachu"},
        opponent_roster={0: "clefable", 1: "starmie"},
    )["state"]


def _manager(state=None):
    created = BattleObservationRuntimeSessionManager.create(SESSION, deepcopy(state or _state()))
    assert created["status"] == "session_ready"
    return created["manager"]


def _boundary():
    return LifecycleConfirmationBoundary(
        SESSION,
        {
            "self": {"side": "self", "slot_index": 0, "pokemon_id": "dragapult"},
            "opponent": {"side": "opponent", "slot_index": 0, "pokemon_id": "clefable"},
        },
    )


def _confirm_locked(boundary, *, status, target=None, side="self", slot=0, pokemon="dragapult", session=SESSION, turn=4):
    payload = {"status": status}
    if target is not None:
        payload["bound_target"] = deepcopy(target)
    return boundary.confirm(
        event_kind="current_locked_on_state_observed",
        payload=payload,
        session_id=session,
        source=LOCKED_ON_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side=side,
        slot_index=slot,
        pokemon_id=pokemon,
        turn_number=turn,
    )


def _confirm_gravity(boundary, status, *, turn=4):
    return boundary.confirm(
        event_kind="gravity_field_observed",
        payload={"status": status},
        session_id=SESSION,
        source=GRAVITY_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        turn_number=turn,
    )


def _apply(manager, confirmation):
    assert confirmation["status"] == "confirmed"
    assert manager.admit_confirmation(SESSION, confirmation)["status"] == "added"
    snapshot = manager.read_collection_snapshot()
    result = manager.apply(SESSION, snapshot)
    assert result["status"] == "applied"
    return manager.read_state()["state"]


def _d0(manager):
    snapshot = manager.capture_runtime_state_snapshot(SESSION)
    assert snapshot["status"] == "runtime_snapshot_ready"
    result = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=SELF)
    assert result["status"] == "resolved"
    return snapshot, result


def test_bootstrap_preserves_locked_on_and_gravity_as_unknown():
    state = _state()
    assert is_unknown_battle_fact(state["self_side"]["pokemon"][0]["locked_on_state"])
    assert is_unknown_battle_fact(state["opponent_side"]["pokemon"][0]["locked_on_state"])
    assert is_unknown_battle_fact(state["field"]["gravity_status"])
    assert validate_battle_state_unknown_markers(state)


def test_locked_on_inactive_observation_replays_and_freezes_known_inactive():
    manager, boundary = _manager(), _boundary()
    state = _apply(manager, _confirm_locked(boundary, status="inactive"))
    assert state["self_side"]["pokemon"][0]["locked_on_state"] == {"status": "known_inactive"}
    snapshot, d0 = _d0(manager)
    authority = freeze_runtime_d0_locked_on_target_binding_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, source_owner=SELF,
    )
    assert authority["status"] == "resolved"
    assert authority["locked_on_state"] == {"status": "known_inactive"}
    assert "targetability_outcome" not in authority


def test_locked_on_active_observation_preserves_exact_bound_target_through_replay_and_d0():
    manager, boundary = _manager(), _boundary()
    state = _apply(manager, _confirm_locked(boundary, status="active", target=OPP))
    stored = state["self_side"]["pokemon"][0]["locked_on_state"]
    assert stored == {"status": "known_active", "bound_target": OPP}
    snapshot, d0 = _d0(manager)
    authority = freeze_runtime_d0_locked_on_target_binding_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, source_owner=SELF,
    )
    assert authority["status"] == "resolved"
    assert authority["locked_on_state"] == {"status": "known_active", "bound_target": OPP}
    assert authority["source_owner"] == SELF
    assert authority["source_runtime_fingerprint"] == snapshot["state_fingerprint"]
    assert authority["source_branch_fingerprint"] == d0["strategy_preview_fingerprint"]
    assert "targetability_outcome" not in authority


def test_locked_on_malformed_active_and_inactive_payloads_are_rejected_at_lifecycle_boundary():
    boundary = _boundary()
    missing = _confirm_locked(boundary, status="active")
    forbidden = _confirm_locked(boundary, status="inactive", target=OPP)
    assert missing["status"] == "invalid_provenance"
    assert forbidden["status"] == "invalid_provenance"


def test_locked_on_foreign_target_session_and_source_identity_mismatch_are_rejected():
    boundary = _boundary()
    foreign = {**OPP, "session_id": "foreign"}
    assert _confirm_locked(boundary, status="active", target=foreign)["status"] == "invalid_provenance"
    assert _confirm_locked(
        boundary, status="inactive", side="self", slot=0, pokemon="not-dragapult",
    )["status"] == "invalid_provenance"


def test_locked_on_missing_observation_is_incomplete_not_inactive():
    manager = _manager()
    snapshot, d0 = _d0(manager)
    authority = freeze_runtime_d0_locked_on_target_binding_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, source_owner=SELF,
    )
    assert authority["status"] == "incomplete"
    assert authority["reason"] == "current_locked_on_state_unknown"
    assert authority["locked_on_state"] == {"status": "unknown"}


def test_locked_on_replacement_does_not_retarget_bound_identity():
    manager, boundary = _manager(), _boundary()
    _apply(manager, _confirm_locked(boundary, status="active", target=OPP))
    replaced = manager.read_state()["state"]
    replaced["opponent_side"]["active_slot_index"] = 1
    assert validate_battle_state_unknown_markers(replaced)
    replacement_manager = _manager(replaced)
    snapshot, d0 = _d0(replacement_manager)
    assert d0["active_owners"]["opponent"] == OPP_REPLACEMENT
    authority = freeze_runtime_d0_locked_on_target_binding_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, source_owner=SELF,
    )
    assert authority["status"] == "resolved"
    assert authority["locked_on_state"]["bound_target"] == OPP
    assert authority["locked_on_state"]["bound_target"] != d0["active_owners"]["opponent"]


def test_locked_on_source_switch_retires_current_fact_to_unknown():
    manager, boundary = _manager(), _boundary()
    state = _apply(manager, _confirm_locked(boundary, status="active", target=OPP))
    plan = {
        "session_id": SESSION,
        "status": "planned",
        "conflicts": [],
        "ordered_steps": [{
            "observation_id": "switch-source",
            "observation_sequence": 2,
            "planned_effect": "switch_active",
            "trust": USER_TRUST,
            "side": "self",
            "switch_out_slot_index": 0,
            "switch_out_pokemon_id": "dragapult",
            "switch_in_slot_index": 1,
            "switch_in_pokemon_id": "pikachu",
        }],
    }
    result = project_atomic_transition(state, plan, SESSION)
    assert result["status"] == "ready_with_projected_state"
    retired = result["projected_state"]["self_side"]["pokemon"][0]
    assert is_unknown_battle_fact(retired["locked_on_state"])
    assert "locked_on_state_provenance" not in retired


def test_locked_on_stale_runtime_and_source_owner_mismatch_are_rejected():
    manager, boundary = _manager(), _boundary()
    _apply(manager, _confirm_locked(boundary, status="inactive"))
    old_snapshot, old_d0 = _d0(manager)
    wrong_source = {**SELF, "pokemon_id": "wrong"}
    assert freeze_runtime_d0_locked_on_target_binding_authority(
        strategy_d0=old_d0, runtime_snapshot=old_snapshot, source_owner=wrong_source,
    )["status"] == "rejected"
    _apply(manager, _confirm_gravity(boundary, "inactive", turn=5))
    new_snapshot = manager.capture_runtime_state_snapshot(SESSION)
    stale = freeze_runtime_d0_locked_on_target_binding_authority(
        strategy_d0=old_d0, runtime_snapshot=new_snapshot, source_owner=SELF,
    )
    assert stale["status"] == "rejected"
    assert stale["reason"] == "runtime_fingerprint_changed"


def test_gravity_active_and_inactive_observations_replay_and_freeze_exactly():
    for expected in ("active", "inactive"):
        manager, boundary = _manager(), _boundary()
        state = _apply(manager, _confirm_gravity(boundary, expected))
        assert state["field"]["gravity_status"] == expected
        snapshot, d0 = _d0(manager)
        authority = freeze_runtime_d0_gravity_field_authority(
            strategy_d0=d0, runtime_snapshot=snapshot,
        )
        assert authority["status"] == "resolved"
        assert authority["gravity"] == {"status": expected}
        assert "remaining_duration" not in authority
        assert "targetability_outcome" not in authority


def test_gravity_missing_is_incomplete_and_malformed_status_is_rejected():
    manager = _manager()
    snapshot, d0 = _d0(manager)
    unknown = freeze_runtime_d0_gravity_field_authority(
        strategy_d0=d0, runtime_snapshot=snapshot,
    )
    assert unknown["status"] == "incomplete"
    assert unknown["reason"] == "current_gravity_state_unknown"
    bad = _boundary().confirm(
        event_kind="gravity_field_observed",
        payload={"status": "maybe"},
        session_id=SESSION,
        source=GRAVITY_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        turn_number=4,
    )
    assert bad["status"] == "invalid_provenance"


def test_gravity_stale_runtime_is_rejected():
    manager, boundary = _manager(), _boundary()
    _apply(manager, _confirm_gravity(boundary, "active"))
    old_snapshot, old_d0 = _d0(manager)
    _apply(manager, _confirm_gravity(boundary, "inactive", turn=5))
    new_snapshot = manager.capture_runtime_state_snapshot(SESSION)
    stale = freeze_runtime_d0_gravity_field_authority(
        strategy_d0=old_d0, runtime_snapshot=new_snapshot,
    )
    assert stale["status"] == "rejected"
    assert stale["reason"] == "runtime_fingerprint_changed"


def test_d0_freezers_reject_tampered_observation_provenance():
    manager, boundary = _manager(), _boundary()
    _apply(manager, _confirm_locked(boundary, status="active", target=OPP))
    _apply(manager, _confirm_gravity(boundary, "active", turn=5))
    state = manager.read_state()["state"]

    locked_tampered = deepcopy(state)
    locked_tampered["self_side"]["pokemon"][0]["locked_on_state_provenance"]["source"] = "forged"
    locked_manager = _manager(locked_tampered)
    locked_snapshot, locked_d0 = _d0(locked_manager)
    assert freeze_runtime_d0_locked_on_target_binding_authority(
        strategy_d0=locked_d0, runtime_snapshot=locked_snapshot, source_owner=SELF,
    )["reason"] == "locked_on_observation_provenance_invalid"

    gravity_tampered = deepcopy(state)
    gravity_tampered["field"]["gravity_status_provenance"]["source"] = "forged"
    gravity_manager = _manager(gravity_tampered)
    gravity_snapshot, gravity_d0 = _d0(gravity_manager)
    assert freeze_runtime_d0_gravity_field_authority(
        strategy_d0=gravity_d0, runtime_snapshot=gravity_snapshot,
    )["reason"] == "gravity_observation_provenance_invalid"


def test_lifecycle_collection_and_replay_registry_admit_both_new_production_events():
    boundary = _boundary()
    locked = _confirm_locked(boundary, status="active", target=OPP)
    gravity = _confirm_gravity(boundary, "active")
    assert locked["status"] == gravity["status"] == "confirmed"
    collection = ObservationCollection(SESSION)
    assert collection.add_confirmation_results((locked, gravity))["status"] == "added"
    snapshot = collection.snapshot(SESSION)
    assert [row["event_kind"] for row in snapshot["ordered_observations"]] == [
        "current_locked_on_state_observed", "gravity_field_observed",
    ]
    plan = build_replay_plan(_state(), snapshot["ordered_observations"])
    assert plan["status"] == "planned"
    assert [row["planned_effect"] for row in plan["ordered_steps"]] == [
        "set_current_locked_on_state", "set_observed_gravity",
    ]


def test_existing_trick_room_and_magic_room_lifecycle_contracts_are_unchanged():
    for event_kind, source, field_name in (
        ("trick_room_field_observed", TRICK_ROOM_SOURCE, "trick_room_status"),
        ("magic_room_field_observed", MAGIC_ROOM_SOURCE, "magic_room_status"),
    ):
        manager, boundary = _manager(), _boundary()
        result = boundary.confirm(
            event_kind=event_kind,
            payload={"status": "active"},
            session_id=SESSION,
            source=source,
            trust=USER_TRUST,
            confirmed=True,
            turn_number=4,
        )
        assert result["status"] == "confirmed"
        state = _apply(manager, result)
        assert state["field"][field_name] == "active"


def test_new_authorities_do_not_grant_targetability_or_generic_charge_execution():
    repo = ChargeMoveRepository()
    for move_id in ("fly", "dig", "dive", "bounce"):
        guard = repo.immediate_execution_guard(move_id)
        assert guard is not None
        assert guard["reason"] == "two_turn_execution_unrepresented"
        assert guard["canonical_recognition_grants_immediate_execution"] is False
        direct = evaluate_direct_damage_mechanics(
            {
                "battle_context": {
                    "current_state": {
                        "direct_mechanics_context": {"generation": "gen9"},
                    },
                },
                "move": {"move_id": move_id},
            },
            stat_provenance={},
            trusted_level=None,
        )
        assert direct["status"] == "unsupported_mechanic"
        assert direct["unsupported_reason"] == "two_turn_execution_unrepresented"
