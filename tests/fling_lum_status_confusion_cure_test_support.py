if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import pytest
    raise SystemExit(pytest.main(sys.argv[1:]))

from copy import deepcopy

import pytest

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_detached_intermediate_paralysis_second_action_authority import (
    consume_detached_intermediate_paralysis_for_second_action,
)
from llm.advisor_detached_intermediate_predictive_authority import (
    freeze_detached_intermediate_predictive_authority,
)
from llm.advisor_detached_predictive_intermediate_state import (
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from llm.advisor_immediate_move_vs_move_action_pair import (
    _lum_gate_deferral_for_first_cure,
    materialize_immediate_move_vs_move_action_pair,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order
from tests.test_runtime_d0_fling_item_execution_authority import _production_fling_pair


def _set_condition(raw, value):
    raw["condition"] = value
    raw["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "condition": value,
    }


def _owner(state, side):
    raw = state[f"{side}_side"]["pokemon"][0]
    return {
        "session_id": state["session_id"],
        "side": side,
        "slot_index": 0,
        "pokemon_id": raw["pokemon_id"],
    }


def _set_confusion(raw, owner, value):
    raw["current_confusion"] = value
    raw["confusion_provenance"] = {
        "event_kind": "current_confusion_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "state": value,
    }
    if value == "confused":
        raw["champions_confusion_progression"] = {
            "schema_version": "champions-confusion-progression-v1",
            "owner": deepcopy(owner),
            "state": "confused",
            "origin_id": f"lum-pair:{owner['side']}:confusion",
            "established_turn": 1,
            "prior_opportunities": 0,
            "duration": 3,
            "confusion_observation": deepcopy(raw["confusion_provenance"]),
            "observed_turn": 1,
            "provenance": "observed_champions_confusion_progression_v1",
        }
    else:
        raw["champions_confusion_progression"] = None


def _pair(
    *,
    item="lum-berry",
    order="own_first",
    own_condition="none",
    target_condition="none",
    own_confusion="none",
    target_confusion="none",
    own_move="fling",
    opponent_hp=100,
    target_ability="pressure",
    toxic_progression=False,
):
    state, _snapshot, old_d0, old_own, responses, _orders = _inputs(
        opponent_hp=opponent_hp,
    )
    own_raw = state["self_side"]["pokemon"][0]
    foe_raw = state["opponent_side"]["pokemon"][0]
    own_owner, foe_owner = _owner(state, "self"), _owner(state, "opponent")
    _set_condition(own_raw, own_condition)
    _set_condition(foe_raw, target_condition)
    _set_confusion(own_raw, own_owner, own_confusion)
    _set_confusion(foe_raw, foe_owner, target_confusion)
    if toxic_progression:
        foe_raw["toxic_progression"] = {
            "next_stage": 4,
            "initialized_turn": 1,
            "last_processed_turn": 1,
            "condition_observation_id": "lum-toxic",
            "provenance": {
                "event_kind": "condition_applied_observed",
                "trust": "user_confirmed_observation",
            },
        }

    own_raw["known_item"] = item
    own_raw["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": "known",
    }
    for raw, ability, label in (
        (own_raw, "pressure", "self"),
        (foe_raw, target_ability, "target"),
    ):
        raw["current_ability"] = ability
        raw["current_ability_provenance"] = {
            "event_kind": "current_ability_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "source_observation_id": f"lum-{label}-ability",
        }
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed",
        "trust": "user_confirmed_observation",
        "source_observation_id": "lum-pair-mr",
        "source_sequence": 1,
    }
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }
    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot, decision_owner=own_owner,
    )
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    if own_move == "fling":
        metadata = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
        own = {
            "action_id": "attack:fling",
            "action_type": "attack",
            "identity": "fling",
            "move_metadata_authority": {
                "status": "resolved",
                "candidate_id": "attack:fling",
                "active_attacker": actor,
                "session_id": d0["session_id"],
                "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
                "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
                "decision_owner": d0["decision_owner"],
                "move_id": "fling",
                "metadata": metadata,
            },
        }
    else:
        own = deepcopy(old_own)
        own["action_id"] = f"attack:{own_move}"
        own["identity"] = own_move
        own["move_metadata_authority"]["candidate_id"] = own["action_id"]
        own["move_metadata_authority"]["move_id"] = own_move
        own["move_metadata_authority"]["metadata"]["move_id"] = own_move
        own["move_metadata_authority"].update(
            active_attacker=actor,
            session_id=d0["session_id"],
            source_runtime_fingerprint=d0["source_runtime_fingerprint"],
            source_branch_fingerprint=d0["strategy_preview_fingerprint"],
            decision_owner=d0["decision_owner"],
        )
    opponent = deepcopy(
        next(
            row for row in responses["actions"]
            if row["action_id"] == "opponent_attack:water-gun"
        )
    )
    opponent.update(
        session_id=d0["session_id"],
        source_runtime_fingerprint=d0["source_runtime_fingerprint"],
        source_branch_fingerprint=d0["strategy_preview_fingerprint"],
        decision_owner=d0["decision_owner"],
    )
    order_authority = _order(d0, own, opponent, order)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        own_action=own,
        opponent_action=opponent,
        action_order_authority=order_authority,
    )
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    return {
        "state": state,
        "snapshot": snapshot,
        "d0": d0,
        "own": own,
        "opponent": opponent,
        "order": order_authority,
        "pair": pair,
        "ledger": ledger,
    }


def _assert_lum_first_exact(case, outcome):
    pair, ledger = case["pair"], case["ledger"]
    assert pair["status"] == "evaluable", pair.get("reason", pair)
    assert pair["schema_version"] == "immediate-move-vs-move-action-pair-v1"
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["status"] == "evaluable", ledger
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert {row["action_order"] for row in pair["terminal_branches"]} == {"own_first"}
    assert {row["second_action"]["state"] for row in pair["terminal_branches"]} == {"executed"}
    for branch in pair["terminal_branches"]:
        payload = branch["first_action_leaf"]["consequences"][
            "fling_lum_major_status_confusion_cure_target_effect"
        ]
        assert payload["outcome"] == outcome
        assert branch["first_action_leaf"]["consequences"][
            "fling_berry_eaten_transition"
        ]["resulting_state"] == "known_true"
        assert payload["authority"]["fling_execution_authority"]["resolved_base_power"] == 10


