"""Actual native attacks/switches → current captured explanation → Korean UI."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_shadow import valid_shadow_evidence
from llm.advisor_showdown_strategy_evaluation import experimental_ranking, fingerprint
from llm.advisor_ui_detached_strategy_bridge import run_current_ui_detached_strategy
from scripts.verify_showdown_integration import snapshot_from_state
from tests.test_showdown_shadow_ui import setup, run
from tests.test_showdown_rollout import policy
from tests.test_ui_detached_strategy_bridge import _RuntimeManager
from ui.strategy_explanation_presentation import present_strategy_explanation, render_strategy_explanation


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


def configuration(*, horizon=32):
    snapshot, builder, context = setup()
    context.update(schema_version="showdown-shadow-config-v2", seeds=[[7, 11, 17, n] for n in range(4)], rollout_policy=policy(horizon))
    for scenario in context["scenarios"]:
        scenario["opponent_actions"] = [{"action_id": "bullet-punch", "choice": "move 1"}, {"action_id": "swords-dance", "choice": "move 2"}]
    return snapshot, builder, context


def test_complete_attack_switch_grid_with_policy_win_estimates_and_unchanged_default(worker):
    snapshot, builder, context = configuration()
    before = deepcopy((snapshot, context))
    baseline = run(snapshot, builder)
    result = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)
    evidence = result["explanation"]["sampled_simulation"]
    assert evidence["status"] == "evaluated", evidence
    assert valid_shadow_evidence(evidence, result["explanation"])
    assert len(evidence["scenarios"]) == 8
    assert all(len(s["candidates"]) == 3 for s in evidence["scenarios"])
    for s in evidence["scenarios"]:
        for c in s["candidates"]:
            assert c["status"] == "evaluated", c
            assert sum(c[k] for k in ("self_win_samples", "opponent_win_samples", "draw_samples", "truncated_samples")) == 4
            assert c["win_rate"]["estimate"] == c["self_win_samples"] / 4
    assert "experimental_ranking" not in result["explanation"]
    assert result["orchestration"] == baseline["orchestration"]
    assert result["exact_outcome_ledgers"] == baseline["exact_outcome_ledgers"]
    text = render_strategy_explanation(presentation=present_strategy_explanation(explanation=result["explanation"]))
    assert "무승부" in text and "미완료" in text and "정확 확률 아님" in text
    assert "후속 무작위 정책" in text
    assert (snapshot, context) == before
    repeated = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)["explanation"]["sampled_simulation"]
    for row in evidence["scenarios"]: row.pop("root_checkpoint_fingerprint")
    for row in repeated["scenarios"]: row.pop("root_checkpoint_fingerprint")
    assert repeated == evidence


def test_explicit_experimental_ranking_changes_only_separate_display(worker):
    snapshot, builder, context = configuration(horizon=1)
    baseline = run(snapshot, builder)
    result = run(snapshot, builder, showdown_context=context, showdown_bridge=worker, showdown_experimental_ranking=True)
    experiment = result["explanation"]["experimental_ranking"]
    assert experiment["status"] == "evaluated", experiment
    assert experiment["default_policy_changed"] is False
    assert result["orchestration"] == baseline["orchestration"]
    assert result["explanation"]["preferred_frontier"] == baseline["explanation"]["preferred_frontier"]
    assert experiment["legacy_preferred_frontier"] == baseline["explanation"]["preferred_frontier"]
    assert all(-1 <= c["estimated_score"] <= 1 for c in experiment["candidates"])
    text = render_strategy_explanation(presentation=present_strategy_explanation(explanation=result["explanation"]))
    assert "실험 순위 (기본 추천에 미적용)" in text and "승률 아님" in text
    assert experimental_ranking(evidence=result["explanation"]["sampled_simulation"], explanation=result["explanation"]) is None


@pytest.mark.parametrize("mutate", [
    lambda e: e.update(evidence_class="exact_conditional_distribution"),
    lambda e: e.update(probability_scope="complete_action_probability"),
    lambda e: e.update(source_capture_fingerprint="stale"),
    lambda e: e["scenarios"].pop(),
    lambda e: e["scenarios"][0]["candidates"][0].update(truncated_samples=100),
    lambda e: e["scenarios"][0]["candidates"][0]["win_rate"].update(estimate=1.1),
    lambda e: e["scenarios"][0]["candidates"][0].update(mean_outcome_value=float("nan")),
    lambda e: e["scenarios"][0]["native_decision_phase"].update(interpretation="observed"),
    lambda e: e["scenarios"][0]["candidates"][0]["immediate"]["request_counts"].update(switch=100),
    lambda e: e["rollout_policy"].update(policy="optimal_policy"),
    lambda e: e["candidate_choices"].update({"attack:air-slash": "move protect"}),
])
def test_strict_evidence_class_mass_and_provenance_guard(worker, mutate):
    snapshot, builder, context = configuration(horizon=1)
    explanation = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)["explanation"]
    mutate(explanation["sampled_simulation"])
    assert present_strategy_explanation(explanation=explanation)["status"] == "rejected"


def test_incomplete_opponent_action_grid_does_not_bias_experimental_ranking(worker):
    snapshot, builder, context = configuration(horizon=1)
    context["scenarios"][0]["opponent_actions"][0]["choice"] = "move 99"
    result = run(snapshot, builder, showdown_context=context, showdown_bridge=worker, showdown_experimental_ranking=True)
    assert result["explanation"]["sampled_simulation"]["status"] == "evaluated"
    assert result["explanation"]["experimental_ranking"]["reason"] == "incomplete_scenario_candidate_coverage"
    assert present_strategy_explanation(explanation=result["explanation"])["status"] == "resolved"


def test_full_capture_freshness_includes_metadata_not_covered_by_old_state_fingerprint(worker):
    snapshot, builder, context = configuration(horizon=1)
    changed = deepcopy(snapshot)
    changed["capture_metadata"] = {"native_status_provenance": "changed"}
    assert changed["state_fingerprint"] == snapshot["state_fingerprint"]
    assert fingerprint(changed) != fingerprint(snapshot)
    result = run_current_ui_detached_strategy(runtime_session_manager=_RuntimeManager([snapshot, changed]),
        captured_session_id=snapshot["session_id"], selection_cycle_builder=builder,
        showdown_context=context, showdown_bridge=worker)
    assert result["status"] == "stale"


def test_known_state_conflict_falls_back_without_hypothesis_writeback(worker):
    snapshot, builder, context = configuration(horizon=1)
    for scenario in context["scenarios"]:
        scenario["teams"]["opponent"][0]["evs"] = {"hp": 32, "atk": 32, "spe": 2}
    before = deepcopy(snapshot)
    result = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)
    assert result["status"] == "resolved"
    assert result["explanation"]["sampled_simulation"]["status"] == "rejected"
    assert snapshot == before


def test_worker_recovery_and_rollback_return_identical_default(worker):
    snapshot, builder, context = configuration(horizon=1)
    baseline = run(snapshot, builder)
    result = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)
    assert result["explanation"]["sampled_simulation"]["status"] == "evaluated"
    worker._process.kill()
    worker._process.wait(timeout=2)
    assert run(snapshot, builder, showdown_context=context, showdown_bridge=worker)["status"] == "resolved"
    worker.close()
    assert run(snapshot, builder) == baseline


def test_full_registered_roster_stays_separate_from_hypothetical_chosen_three(worker):
    from llm.advisor_showdown_native_preview import build_conditional_native_preview
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
    from llm.advisor_runtime_d0_selection_projection import build_runtime_d0_selection_capture
    snapshot, builder, context = configuration(horizon=1)
    ids = ["charizard", "garchomp", "rotom-wash", "tyranitar", "dragonite", "gengar"]
    for slot, pid in enumerate(ids[2:], start=2):
        snapshot["state"]["self_side"]["pokemon"][slot] = {"pokemon_id": pid,
            "current_hp": {"knowledge": "unknown"}, "max_hp": {"knowledge": "unknown"}, "fainted": {"knowledge": "unknown"}}
    snapshot = snapshot_from_state(snapshot["state"])
    owner = {"session_id": snapshot["session_id"], "side": "self", "slot_index": 0, "pokemon_id": "charizard"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    intents = {"schema_version": "showdown-ui-candidate-intents-v1", "capture": build_runtime_d0_selection_capture(strategy_d0=d0),
        "moves": ["flamethrower", "protect"], "switches": ids[1:]}
    context["conditional_candidate_ids"] = ["attack:flamethrower", "attack:protect", "manual_switch:garchomp", "manual_switch:rotom-wash"]
    before = deepcopy(snapshot)
    result = build_conditional_native_preview(capture=snapshot, strategy_d0=d0, context=context, intents=intents,
        bridge=worker, deferred=False, experiment=True, legacy_reason="no_selectable_candidates")
    assert result["explanation"]["sampled_simulation"]["status"] == "evaluated", result
    assert result["explanation"]["experimental_ranking"]["status"] == "evaluated"
    assert present_strategy_explanation(explanation=result["explanation"])["status"] == "resolved"
    assert snapshot == before
    assert snapshot["state"]["self_side"]["pokemon"][2]["current_hp"] == {"knowledge": "unknown"}


def test_explicit_hypothetical_hp_enables_evidence_without_resolving_unknown_live_hp(worker):
    snapshot, builder, context = configuration(horizon=1)
    for side in ("self", "opponent"):
        snapshot["state"][f"{side}_side"]["pokemon"][0].update(
            current_hp={"knowledge": "unknown"}, max_hp={"knowledge": "unknown"}, fainted={"knowledge": "unknown"})
    snapshot = snapshot_from_state(snapshot["state"])
    for scenario in context["scenarios"]: scenario["hypothetical_active_hp"] = {"self": 155, "opponent": 147}
    before = deepcopy(snapshot)
    result = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)
    assert result["explanation"]["sampled_simulation"]["status"] == "evaluated", result
    assert snapshot == before
