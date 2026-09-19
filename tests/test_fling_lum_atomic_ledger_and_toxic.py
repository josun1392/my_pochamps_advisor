from copy import deepcopy

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
from llm.advisor_reducer_state_model import make_unknown_battle_fact
from tests.fling_lum_status_confusion_cure_test_support import (
    _assert_lum_first_exact,
    _pair,
)
from tests.test_runtime_d0_fling_item_execution_authority import _production_fling_pair


def test_lum_first_toxic_and_confusion_atomically_cures_both():
    case = _pair(target_condition="toxic", target_confusion="confused")
    _assert_lum_first_exact(case, "applied_major_status_and_confusion_cure")
    for branch in case["pair"]["terminal_branches"]:
        payload = branch["first_action_leaf"]["consequences"][
            "fling_lum_major_status_confusion_cure_target_effect"
        ]
        assert payload["condition_before"] == "toxic"
        assert payload["condition_after"] == "none"
        assert payload["confusion_before"] == "confused"
        assert payload["confusion_after"] == "none"


def test_exact_ledger_rejects_forged_atomic_lum_components_and_ateberry():
    case = _pair(target_condition="toxic", target_confusion="confused")
    assert case["ledger"]["status"] == "evaluable", case["ledger"]
    mutations = (
        "condition_marker",
        "confusion_marker",
        "partial_atomic",
        "progression",
        "eat",
        "ateberry",
    )
    for mutation in mutations:
        forged = deepcopy(case["pair"])
        branch = deepcopy(forged["terminal_branches"][0])
        first = branch["first_action_leaf"]
        payload = first["consequences"][
            "fling_lum_major_status_confusion_cure_target_effect"
        ]
        if mutation == "condition_marker":
            payload["hypothetical_target_condition_removal"]["condition_removed"] = "burn"
        elif mutation == "confusion_marker":
            payload["hypothetical_target_confusion_removal"]["confusion_after"] = "confused"
        elif mutation == "partial_atomic":
            payload["confusion_after"] = "confused"
        elif mutation == "progression":
            payload["hypothetical_target_confusion_removal"][
                "confusion_progression_after"
            ] = {"state": "confused"}
        elif mutation == "eat":
            payload["authority"]["berry_eat_item_interaction_authority"][
                "target"
            ] = deepcopy(payload["authority"]["actor"])
        else:
            first["consequences"]["fling_berry_eaten_transition"][
                "resulting_state"
            ] = "known_false"
        forged["terminal_branches"] = (
            branch,
            *forged["terminal_branches"][1:],
        )
        normalized = normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)
        assert normalized["status"] == "rejected", (mutation, normalized)


def test_lum_toxic_cure_private_second_action_view_retires_stale_progression():
    case = _pair(target_condition="toxic", toxic_progression=True)
    assert case["pair"]["status"] == "evaluable", case["pair"].get("reason")
    first = next(
        branch["first_action_leaf"] for branch in case["pair"]["terminal_branches"]
        if "fling_lum_major_status_confusion_cure_target_effect"
        in branch["first_action_leaf"]["consequences"]
    )
    intermediate = materialize_detached_predictive_intermediate_state(
        strategy_d0=case["d0"], terminal_leaf=first,
    )
    pending_metadata = {
        "status": "resolved",
        "move_id": case["opponent"]["move_id"],
        "metadata": deepcopy(case["opponent"]["metadata_authority"]["metadata"]),
        "session_id": case["d0"]["session_id"],
        "source_runtime_fingerprint": case["d0"]["source_runtime_fingerprint"],
        "source_branch_fingerprint": case["d0"]["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(case["d0"]["decision_owner"]),
    }
    authority = freeze_detached_intermediate_predictive_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        intermediate_state=intermediate,
        actor=case["d0"]["active_owners"]["opponent"],
        target=case["d0"]["active_owners"]["self"],
        move_metadata_authority=pending_metadata,
    )
    assert authority["status"] == "resolved", authority
    consumed = consume_detached_intermediate_paralysis_for_second_action(
        intermediate_predictive_authority=authority,
    )
    assert consumed["status"] == "resolved", consumed
    private = consumed["builder_inputs"]["runtime_snapshot"]
    raw = private["state"]["opponent_side"]["pokemon"][0]
    assert raw["condition"] == "none"
    assert raw["toxic_progression"] == make_unknown_battle_fact()
    original = case["snapshot"]["state"]["opponent_side"]["pokemon"][0]
    assert original["condition"] == "toxic"
    assert original["toxic_progression"]["next_stage"] == 4


def test_pecha_toxic_cure_still_closes_pair_after_shared_private_progression_change():
    pair, ledger = _production_fling_pair(
        item="pecha-berry", target_condition="toxic",
    )
    assert pair["status"] == ledger["status"] == "evaluable"
    assert {row["second_action"]["state"] for row in pair["terminal_branches"]} == {"executed"}
