"""Supreme Overlord must bind damage authority to the attacking active side."""
from copy import deepcopy

from llm.advisor_detached_predictive_intermediate_state import freeze_detached_actor_neutral_root_predictive_authority
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_supreme_overlord_damage_authority import freeze_runtime_d0_supreme_overlord_damage_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


_MOVE = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal"}


def _state(*, self_ability="pressure", opponent_ability="pressure", fallen=0):
    state = create_unknown_bootstrap_battle_state("supreme-neutral", "self-a", "opponent-a")["state"]
    for side, ability in (("self", self_ability), ("opponent", opponent_ability)):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False, current_ability=ability)
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1, "source_sequence": 1}
    owner = _owner(state, "opponent")
    state["supreme_overlord_entry_snapshots"] = [{
        "schema_version": "supreme-overlord-entry-snapshot-v1", "session_id": state["session_id"],
        "owner": owner, "entry_token": "opponent-entry", "entry_kind": "initial_active",
        "raw_allied_faint_count": fallen, "fallen_allies_count": min(fallen, 5),
        "source_sequence": 1, "source_state_fingerprint": "fixture", "status": "resolved", "active": True,
        "provenance": {"event_kind": "fixture", "source_sequence": 1},
    }]
    return state


def _owner(state, side):
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _opponent_root(state):
    snapshot = _snapshot(state); original = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    action = {
        "status": "resolved", "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "session_id": original["session_id"], "source_runtime_fingerprint": original["source_runtime_fingerprint"],
        "source_branch_fingerprint": original["strategy_preview_fingerprint"], "decision_owner": original["decision_owner"],
        "opponent_actor": _owner(state, "opponent"), "target_owner": _owner(state, "self"),
        "action_id": "opponent:tackle", "move_id": "tackle", "selectability": "selectable",
        "usability": {"status": "known_usable"},
        "metadata_authority": {"status": "resolved", "move_id": "tackle", "metadata": deepcopy(_MOVE)},
    }
    root = freeze_detached_actor_neutral_root_predictive_authority(strategy_d0=original, runtime_snapshot=snapshot, opponent_action=action)
    assert root["status"] == "resolved", root
    return root


def test_self_root_remains_exact_and_opponent_root_uses_opponent_ability_and_snapshot():
    self_state = _state(self_ability="supreme-overlord", fallen=2)
    self_state["supreme_overlord_entry_snapshots"][0]["owner"] = _owner(self_state, "self")
    self_state["supreme_overlord_entry_snapshots"][0]["entry_token"] = "self-entry"
    self_snapshot = _snapshot(self_state); self_d0 = freeze_runtime_strategy_d0(runtime_snapshot=self_snapshot, decision_owner=_owner(self_state, "self"))
    self_authority = freeze_runtime_d0_supreme_overlord_damage_authority(strategy_d0=self_d0, runtime_snapshot=self_snapshot, attacker=_owner(self_state, "self"), target=_owner(self_state, "opponent"), move_metadata=_MOVE)
    assert self_authority["status"] == "resolved" and self_authority["modifier_q12"] == 4915

    opponent_state = _state(opponent_ability="supreme-overlord", fallen=3); root = _opponent_root(opponent_state)
    authority = freeze_runtime_d0_supreme_overlord_damage_authority(strategy_d0=root["predictive_strategy_d0"], runtime_snapshot=root["predictive_runtime_snapshot"], attacker=_owner(opponent_state, "opponent"), target=_owner(opponent_state, "self"), move_metadata=_MOVE)
    assert authority["status"] == "resolved", authority
    assert authority["attacker_ability"] == "supreme-overlord" and authority["entry_token"] == "opponent-entry" and authority["modifier_q12"] == 5325


def test_opponent_root_zero_and_capped_counts_preserve_existing_modifier_map():
    for fallen, expected, outcome in ((0, 4096, "known_neutral"), (7, 6144, "applicable")):
        state = _state(opponent_ability="supreme-overlord", fallen=fallen); root = _opponent_root(state)
        authority = freeze_runtime_d0_supreme_overlord_damage_authority(strategy_d0=root["predictive_strategy_d0"], runtime_snapshot=root["predictive_runtime_snapshot"], attacker=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata=_MOVE)
        assert authority["status"] == "resolved" and authority["fallen_allies_count"] == min(fallen, 5)
        assert authority["modifier_q12"] == expected and authority["outcome"] == outcome


def test_opponent_authority_never_borrows_self_ability_and_rejects_invalid_bindings():
    state = _state(self_ability="supreme-overlord", opponent_ability="pressure", fallen=2); root = _opponent_root(state)
    d0, snapshot = root["predictive_strategy_d0"], root["predictive_runtime_snapshot"]
    absent = freeze_runtime_d0_supreme_overlord_damage_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata=_MOVE)
    assert absent["status"] == "incomplete" and absent["reason"] == "supreme_overlord_attacker_ability_unknown_or_changed"
    wrong_target = freeze_runtime_d0_supreme_overlord_damage_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state, "opponent"), move_metadata=_MOVE)
    assert wrong_target["status"] == "rejected"
    stale = deepcopy(d0); stale["source_runtime_fingerprint"] = "forged"
    assert freeze_runtime_d0_supreme_overlord_damage_authority(strategy_d0=stale, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata=_MOVE)["status"] == "rejected"
    mismatch = deepcopy(state); mismatch["supreme_overlord_entry_snapshots"][0]["owner"] = _owner(mismatch, "self")
    root = _opponent_root(mismatch)
    assert freeze_runtime_d0_supreme_overlord_damage_authority(strategy_d0=root["predictive_strategy_d0"], runtime_snapshot=root["predictive_runtime_snapshot"], attacker=_owner(mismatch, "opponent"), target=_owner(mismatch, "self"), move_metadata=_MOVE)["status"] == "incomplete"
