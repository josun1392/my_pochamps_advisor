"""Hypothetical candidate intents cannot create legacy selection/guarantee truth."""
from copy import deepcopy
import pytest
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_d0_selection_projection import build_runtime_d0_selection_capture, freeze_runtime_d0_bound_selection_projection
from llm.advisor_showdown_native_preview import build_conditional_native_preview
from llm.advisor_ui_detached_strategy_bridge import run_current_ui_detached_strategy
from tests.test_showdown_strategy_evaluation import configuration
from tests.test_ui_detached_strategy_bridge import _RuntimeManager
from ui.strategy_explanation_presentation import present_strategy_explanation


def fixture():
    snapshot, builder, context = configuration(horizon=1)
    owner = {"session_id": snapshot["session_id"], "side": "self", "slot_index": 0, "pokemon_id": "charizard"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    assert d0["status"] == "resolved"
    intents = {"schema_version": "showdown-ui-candidate-intents-v1", "capture": build_runtime_d0_selection_capture(strategy_d0=d0),
        "moves": ["flamethrower", "protect"], "switches": ["garchomp"]}
    return snapshot, d0, context, intents


def preview(**kwargs):
    snapshot, d0, context, intents = fixture()
    return build_conditional_native_preview(capture=snapshot, strategy_d0=d0, context=context, intents=intents,
        bridge=None, deferred=True, experiment=False, legacy_reason="no_selectable_candidates", **kwargs)


def test_native_intents_have_no_current_selection_or_exact_ledger_authority():
    result = preview()
    assert result["native_conditional_only"] is True
    assert result["exact_outcome_ledgers"] == result["descriptive_metrics"] == {}
    selection = result["native_evaluation_job"]["selection"]
    assert all(a["selection"] == "conditional" for a in selection["actions"])
    assert result["explanation"]["preferred_frontier"] == []
    assert present_strategy_explanation(explanation=result["explanation"])["status"] == "resolved"
    snapshot, d0, context, intents = fixture()
    assert freeze_runtime_d0_bound_selection_projection(strategy_d0=d0, prepared_cycle=selection)["status"] == "rejected"


def test_explicit_candidate_filter_is_conditional_and_cannot_invent_actions():
    snapshot, d0, context, intents = fixture()
    context["conditional_candidate_ids"] = ["attack:flamethrower", "manual_switch:garchomp"]
    result = build_conditional_native_preview(capture=snapshot, strategy_d0=d0, context=context, intents=intents,
        bridge=None, deferred=True, experiment=False, legacy_reason="no_selectable_candidates")
    assert {c["candidate_id"] for c in result["explanation"]["candidates"]} == set(context["conditional_candidate_ids"])
    context["conditional_candidate_ids"].append("attack:invented")
    with pytest.raises(ValueError):
        build_conditional_native_preview(capture=snapshot, strategy_d0=d0, context=context, intents=intents,
            bridge=None, deferred=True, experiment=False, legacy_reason="no_selectable_candidates")


@pytest.mark.parametrize("mutate", [
    lambda e: e.update(preferred_frontier=["attack:flamethrower"]),
    lambda e: e["candidates"][0].update(guaranteed_facts={"guaranteed_opponent_fainted": True}),
    lambda e: e["candidates"][0].update(evidence_class="guaranteed"),
    lambda e: e.update(candidate_scope="observed_legality"),
    lambda e: e.update(candidates=[None]),
])
def test_conditional_explanation_cannot_masquerade_as_guaranteed_recommendation(mutate):
    result = preview()
    mutate(result["explanation"])
    assert present_strategy_explanation(explanation=result["explanation"])["status"] == "rejected"


@pytest.mark.parametrize("mutate", [
    lambda i: i["capture"].update(session_id="foreign"),
    lambda i: i.update(switches=["invented-bench"]), lambda i: i.update(switches=["charizard"]),
    lambda i: i.update(moves=["protect", "protect"]),
])
def test_source_identity_or_duplicate_intent_rejected(mutate):
    snapshot, d0, context, intents = fixture()
    before = deepcopy(snapshot)
    mutate(intents)
    with pytest.raises(ValueError):
        build_conditional_native_preview(capture=snapshot, strategy_d0=d0, context=context, intents=intents,
            bridge=None, deferred=True, experiment=False, legacy_reason="no_selectable_candidates")
    assert snapshot == before


def test_conditional_fallback_requires_v2_opt_in_and_cannot_bypass_bad_identity():
    snapshot, d0, context, intents = fixture()
    def run(context=None, status="no_selectable_candidates"):
        return run_current_ui_detached_strategy(runtime_session_manager=_RuntimeManager([snapshot]),
            captured_session_id=snapshot["session_id"], selection_cycle_builder=lambda *a: {"status": status},
            showdown_context=context, defer_showdown_evaluation=True, native_candidate_intent_builder=lambda *a: intents)
    assert run()["status"] == "rejected"
    assert run(context)["native_conditional_only"] is True
    assert run(context, "invalid_snapshot")["status"] == "rejected"


def test_invalid_shadow_config_does_not_crash_or_change_default_policy():
    snapshot, builder, context = configuration()
    baseline = run_current_ui_detached_strategy(runtime_session_manager=_RuntimeManager([snapshot]),
        captured_session_id=snapshot["session_id"], selection_cycle_builder=builder)
    result = run_current_ui_detached_strategy(runtime_session_manager=_RuntimeManager([snapshot]),
        captured_session_id=snapshot["session_id"], selection_cycle_builder=builder, showdown_context=[])
    assert result["status"] == "resolved"
    assert result["orchestration"] == baseline["orchestration"]
    assert result["explanation"]["sampled_simulation"]["status"] == "rejected"
