from copy import deepcopy

from llm.advisor_ability_interaction_authority import build_ability_applicability_context
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_sturdy_survival_authority import freeze_runtime_d0_sturdy_survival_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_direct_damage_modifier_authority import _apply, _base, _confirmations, _owner


_MOVE = {"move_id": "water-gun", "category": "special", "power": 40, "type": "water"}


def _inputs(*, ability: str = "sturdy", hp: int = 100, maximum: int = 100, applicability: str | None = "applicable"):
    base = _base()
    state = _apply(base, _confirmations(
        base, attacker_item={"status": "known_absent"}, target_item={"status": "known_absent"},
        attacker_ability="pressure", target_ability=ability,
    ))
    target = state["opponent_side"]["pokemon"][0]
    target.update(current_hp=hp, max_hp=maximum, fainted=hp == 0)
    if applicability is not None:
        state["ability_applicability_context"] = build_ability_applicability_context(
            session_id=state["session_id"], source={"side": "opponent", "slot_index": 0, "pokemon_id": target["pokemon_id"]},
            ability_id="sturdy", status=applicability,
        )
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    attacker, defender = _owner(state, "self"), _owner(state, "opponent")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=attacker)
    action = {"action_id": "attack:water-gun", "action_type": "attack", "identity": "water-gun"}
    return state, snapshot, d0, attacker, defender, action


def test_runtime_d0_sturdy_authority_requires_exact_current_effective_full_hp_target() -> None:
    _state, snapshot, d0, attacker, defender, action = _inputs()
    ready = freeze_runtime_d0_sturdy_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, defender=defender, attacker=attacker, action=action, move_metadata=_MOVE,
    )
    assert ready["status"] == "ready"
    assert ready["eligible"] is True and ready["current_hp"] == ready["maximum_hp"] == 100
    assert ready["defender"] == defender and ready["attacker"] == attacker

    _state, snapshot, d0, attacker, defender, action = _inputs(hp=99)
    nonfull = freeze_runtime_d0_sturdy_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, defender=defender, attacker=attacker, action=action, move_metadata=_MOVE,
    )
    assert nonfull["status"] == "resolved" and nonfull["outcome"] == "known_no_effect"

    _state, snapshot, d0, attacker, defender, action = _inputs(applicability=None)
    unknown = freeze_runtime_d0_sturdy_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, defender=defender, attacker=attacker, action=action, move_metadata=_MOVE,
    )
    assert unknown["status"] == "incomplete" and unknown["reason"] == "sturdy_applicability_unknown"


def test_runtime_d0_sturdy_authority_rejects_stale_or_foreign_bindings() -> None:
    state, snapshot, d0, attacker, defender, action = _inputs()
    stale = deepcopy(snapshot)
    stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 99
    stale["state_fingerprint"] = state_fingerprint(stale["state"])
    rejected = freeze_runtime_d0_sturdy_survival_authority(
        strategy_d0=d0, runtime_snapshot=stale, defender=defender, attacker=attacker, action=action, move_metadata=_MOVE,
    )
    assert rejected["status"] == "rejected"

    foreign = {**defender, "pokemon_id": "foreign"}
    rejected = freeze_runtime_d0_sturdy_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, defender=foreign, attacker=attacker, action=action, move_metadata=_MOVE,
    )
    assert rejected["status"] == "rejected" and rejected["reason"] == "invalid_sturdy_survival_request"
