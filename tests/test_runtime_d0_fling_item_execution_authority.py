from copy import deepcopy

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fling_item_execution_authority import freeze_runtime_d0_fling_item_execution_authority
from llm.advisor_detached_fling_item_throw import materialize_detached_fling_item_throw
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_detached_opponent_response_profile import _inputs


def _state(*, item: object = "abomasite", ability: str = "pressure", magic_room: str = "inactive") -> dict:
    state = create_unknown_bootstrap_battle_state("fling-d0", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        row = state[f"{side}_side"]["pokemon"][0]
        row["current_ability"] = ability if side == "self" else "pressure"
        row["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    own = state["self_side"]["pokemon"][0]
    own["known_item"] = item
    if item is None:
        own["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
    elif isinstance(item, str):
        own["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known"}
    state["field"]["magic_room_status"] = magic_room
    state["field"]["magic_room_status_provenance"] = {"event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation", "source_observation_id": "mr-1", "source_sequence": 1}
    return state


def _owner(state: dict, side: str) -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _authority(state: dict) -> dict:
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    catalog = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
    action = {"action_id": "attack:fling", "action_type": "attack", "identity": "fling", "move_metadata_authority": {"status": "resolved", "metadata": catalog}}
    return freeze_runtime_d0_fling_item_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=_owner(state, "self"), target=_owner(state, "opponent"))


def test_catalog_and_supported_throw_bind_exact_manifest_power() -> None:
    catalog = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
    assert (catalog["type"], catalog["category"], catalog["accuracy"], catalog["priority"], catalog["contact"], catalog["protection_blockable"]) == ("dark", "physical", 100, 0, False, True)
    result = _authority(_state(item="abomasite"))
    assert result["status"] == "resolved" and result["outcome"] == "ready_throw"
    assert result["resolved_base_power"] == 80 and result["item_after"] == {"state": "known_absent", "item": None}
    assert result["fling_item_metadata"]["provenance"] == "frozen_pinned_showdown_fling_metadata_v1"


def test_unknown_absent_unsupported_magic_room_and_klutz_fail_closed() -> None:
    assert _authority(_state(item=None))["outcome"] == "failed_no_item"
    assert _authority(_state(item={"knowledge": "unknown"}))["status"] == "incomplete"
    assert _authority(_state(item="aspear-berry"))["status"] == "unsupported"
    assert _authority(_state(magic_room="active"))["outcome"] == "failed_item_suppressed"
    unknown_field = _state(); unknown_field["field"]["magic_room_status"] = {"knowledge": "unknown"}; unknown_field["field"].pop("magic_room_status_provenance")
    assert _authority(unknown_field)["status"] == "incomplete"
    assert _authority(_state(ability="klutz"))["outcome"] == "failed_klutz"
    gas = _state(ability="klutz"); gas["opponent_side"]["pokemon"][0]["current_ability"] = "neutralizing-gas"
    assert _authority(gas)["outcome"] == "ready_throw"


def test_throw_materialization_consumes_only_after_prepare_hit_boundary() -> None:
    authority = _authority(_state())
    leaf = {"leaf_id": "attack:fling:miss", "candidate_id": "attack:fling", "hit_state": "miss", "provenance": {"move_id": "fling", "attacker": authority["actor"]}}
    thrown = materialize_detached_fling_item_throw(authority=authority, source_leaf=leaf)
    assert thrown["status"] == "resolved" and thrown["item_after"] is None
    assert thrown["timing"] == "prepare_hit_before_accuracy_protection_immunity_damage"
    assert materialize_detached_fling_item_throw(authority=authority, source_leaf={**leaf, "hit_state": "not_applicable"})["status"] == "rejected"


def _production_fling_pair(*, item: str = "abomasite", target_ability: str = "pressure", opponent_hp: int = 100) -> tuple[dict, dict]:
    """Build the existing ordinary physical pair fixture with Fling selected."""
    state, snapshot, d0, _own, responses, _orders = _inputs(opponent_hp=opponent_hp)
    state["self_side"]["pokemon"][0]["known_item"] = item
    state["self_side"]["pokemon"][0]["known_item_provenance"]["status"] = "known"
    state["opponent_side"]["pokemon"][0]["current_ability"] = target_ability
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation",
        "source_observation_id": "fling-mr", "source_sequence": 1,
    }
    snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["active_owners"]["self"])
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    metadata = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
    own = {"action_id": "attack:fling", "action_type": "attack", "identity": "fling", "move_metadata_authority": {
        "status": "resolved", "candidate_id": "attack:fling", "active_attacker": actor,
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
        "move_id": "fling", "metadata": metadata,
    }}
    opponent = deepcopy(next(row for row in responses["actions"] if row["action_id"] == "opponent_attack:water-gun"))
    opponent.update(session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=d0["decision_owner"])
    order = {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "own_first",
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
        "own_action_id": own["action_id"], "opponent_action_id": opponent["action_id"], "own_actor": actor, "opponent_actor": target}
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=order)
    return pair, normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)


def test_supported_fling_reaches_ordinary_physical_pair_and_strict_ledger() -> None:
    pair, ledger = _production_fling_pair()
    assert pair["status"] == ledger["status"] == "evaluable"
    first = pair["terminal_branches"][0]["first_action_leaf"]
    throw = first["consequences"]["fling_item_throw"]
    assert throw["item_before"] == "abomasite" and throw["item_after"] is None
    assert first["provenance"]["fling_execution_authority"]["resolved_base_power"] == 80
    # Abomasite is not a supported ordinary held-item crit modifier; reaching
    # the ordinary physical leaf proves Fling projected it absent post-throw.
    assert first["hit_state"] in {"hit", "miss"}


def test_supported_fling_critical_projection_rejects_forged_post_throw_authority() -> None:
    pair, _ledger = _production_fling_pair()
    first = deepcopy(pair["terminal_branches"][0]["first_action_leaf"])
    first["provenance"]["fling_execution_authority"]["item_after"] = {"state": "known_present", "item": "abomasite"}
    pair["terminal_branches"] = tuple(
        {**branch, "first_action_leaf": first} if index == 0 else branch
        for index, branch in enumerate(pair["terminal_branches"])
    )
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "rejected"


def test_fling_is_explicitly_non_contact_against_contact_reactive_ability() -> None:
    pair, ledger = _production_fling_pair(target_ability="rough-skin", opponent_hp=1)
    assert pair["status"] == ledger["status"] == "evaluable"
    first = pair["terminal_branches"][0]["first_action_leaf"]
    reaction = first["consequences"]["contact_reactive_damage"]
    assert reaction["outcome"] == "not_applicable" and reaction.get("damage", 0) == 0
