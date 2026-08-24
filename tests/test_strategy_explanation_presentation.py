from copy import deepcopy

from PySide6.QtWidgets import QApplication

import llm.advisor_detached_strategy_orchestration as orchestration_subject
from llm.advisor_strategy_explanation import explain_detached_strategy
from ui.strategy_explanation_presentation import (
    PRESENTATION_SCHEMA,
    present_strategy_explanation,
    render_strategy_explanation,
)
from ui.widgets.llm_advice_panel import LLMAdvicePanel


OWNER = {"session_id": "session-1", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}


def _orchestration(*, ranking_status: str = "resolved", selection: str = "complete", frontier: list[str] | None = None) -> dict:
    return {
        "schema_version": "deterministic-strategy-orchestration-result-v1",
        "status": "resolved",
        "session_id": "session-1",
        "decision_branch_fingerprint": "d0",
        "decision_owner": deepcopy(OWNER),
        "selection_completeness": selection,
        "candidates": [
            {
                "candidate_id": "attack:seismic-toss",
                "action_type": "attack",
                "evidence_class": "exact_outcome",
                "execution_readiness": "predictive_execution_ready",
                "facts": {"guaranteed_opponent_fainted": True, "exact_own_hp": 100},
                "provenance": "current_predictive_fixed_damage_v1",
            },
            {
                "candidate_id": "attack:water-gun",
                "action_type": "attack",
                "evidence_class": "guaranteed_facts",
                "execution_readiness": "interval_ready",
                "facts": {"possible_opponent_ko": True, "exact_own_hp": 100},
                "interval": {"min_damage": 90, "max_damage": 110},
                "provenance": "current_predictive_normal_formula_interval_v1",
            },
            {
                "candidate_id": "manual_switch:bench-one",
                "action_type": "manual_switch",
                "evidence_class": "exact_outcome",
                "execution_readiness": "execution_ready",
                "facts": {"guaranteed_opponent_fainted": False, "exact_own_hp": 100},
                "provenance": "current_execution_switch_v1",
            },
            {
                "candidate_id": "attack:tackle",
                "action_type": "attack",
                "evidence_class": "incomplete",
                "execution_readiness": "observation_required",
                "reason": "observation_required",
                "provenance": "current_execution_authority_v1",
            },
        ],
        "ranking": {
            "status": ranking_status,
            "preferred_frontier": frontier or ["attack:seismic-toss"],
            "pairwise_matrix": [
                {
                    "comparison": "preferred",
                    "preferred_candidate": "attack:seismic-toss",
                    "reason": "causes_opponent_ko",
                }
            ],
        },
    }


def _explanation(**kwargs: object) -> dict:
    return explain_detached_strategy(orchestration=_orchestration(**kwargs))


def test_presentation_maps_unique_candidate_evidence_and_preserves_input() -> None:
    explanation = _explanation()
    before = deepcopy(explanation)

    presentation = present_strategy_explanation(explanation=explanation)

    assert explanation == before
    assert presentation["status"] == "resolved"
    assert presentation["schema_version"] == PRESENTATION_SCHEMA
    assert presentation["overall_status"] == "uniquely_preferred"
    assert presentation["horizon"] == "immediate_action_consequence"
    rows = {row["candidate_id"]: row for row in presentation["candidates"]}
    assert rows["attack:seismic-toss"]["preferred_frontier_member"] is True
    assert rows["attack:seismic-toss"]["reason_labels"] == ["상대 기절 보장"]
    assert rows["manual_switch:bench-one"]["label"] == "교체: Bench One"
    assert rows["attack:tackle"]["incomplete_reason"] == "observation_required"
    assert present_strategy_explanation(explanation=explanation) == presentation


def test_presentation_preserves_ties_and_selection_or_comparison_incompleteness() -> None:
    tie = present_strategy_explanation(explanation=_explanation(frontier=["attack:seismic-toss", "manual_switch:bench-one"]))
    partial_selection = present_strategy_explanation(explanation=_explanation(selection="partial"))
    incomplete = present_strategy_explanation(explanation=_explanation(ranking_status="incomplete_comparison_set"))

    assert tie["overall_status"] == "tied_preferred_set"
    assert tie["preferred_frontier"] == ["attack:seismic-toss", "manual_switch:bench-one"]
    assert partial_selection["overall_status"] == "selection_incomplete"
    assert incomplete["overall_status"] == "incomplete_comparison_set"
    assert "선택 가능한 행동 정보가 불완전" in render_strategy_explanation(presentation=partial_selection)
    assert "비교가 불완전" in render_strategy_explanation(presentation=incomplete)


def test_water_gun_possible_ko_is_rendered_as_possible_not_guaranteed() -> None:
    presentation = present_strategy_explanation(explanation=_explanation())
    water_gun = next(row for row in presentation["candidates"] if row["candidate_id"] == "attack:water-gun")
    text = render_strategy_explanation(presentation=presentation)

    assert "상대 기절 가능" in water_gun["fact_labels"]
    assert "상대 기절 가능" in text
    assert "Water Gun [보장 사실]" in text
    assert "Water Gun [보장 사실]\n  상대 기절 보장" not in text


def test_hit_miss_uncertainty_survives_explanation_presentation_and_rendering() -> None:
    orchestration = _orchestration()
    water = next(row for row in orchestration["candidates"] if row["candidate_id"] == "attack:water-gun")
    water["evidence_class"] = "hit_miss_uncertainty"
    water["facts"] = {"guaranteed_opponent_fainted": None, "possible_opponent_ko": True, "exact_own_hp": None}
    water["uncertainty"] = {
        "status": "resolved", "schema_version": "deterministic-predictive-hit-miss-uncertainty-v1",
        "move_id": "water-gun", "probability_percent": 80, "raw_accuracy_threshold": 80,
        "branches": ({"branch": "hit", "probability_percent": 80, "consequences": {"stage_effects": {"effects": ("speed+1",)}}}, {"branch": "miss", "probability_percent": 20, "consequences": {"target_damage": 0, "hit_triggered_stage_effects": None}}),
        "guaranteed_facts": deepcopy(water["facts"]),
    }
    explanation = explain_detached_strategy(orchestration=orchestration)
    presentation = present_strategy_explanation(explanation=explanation)
    rendered = render_strategy_explanation(presentation=presentation)
    row = next(item for item in presentation["candidates"] if item["candidate_id"] == "attack:water-gun")

    explained = next(item for item in explanation["candidates"] if item["candidate_id"] == "attack:water-gun")
    assert explained["hit_miss_uncertainty"] == water["uncertainty"]
    assert row["hit_miss_uncertainty"] == water["uncertainty"]
    assert row["guaranteed_facts"]["guaranteed_opponent_fainted"] is None
    assert row["guaranteed_facts"]["possible_opponent_ko"] is True
    assert row["uncertainty_labels"] == ["명중 판정: 명중 80% / 실패 20%"]
    assert "Water Gun [명중/실패 분기]" in rendered
    assert "상대 기절 가능" in rendered
    assert "Water Gun [명중/실패 분기]\n  상대 기절 보장" not in rendered


def test_hit_only_and_miss_only_uncertainty_labels_remain_structured() -> None:
    for probability, branch, expected in ((100, "hit", "명중 전용"), (0, "miss", "실패 전용")):
        explanation = _explanation()
        candidate = next(row for row in explanation["candidates"] if row["candidate_id"] == "attack:water-gun")
        candidate["evidence_class"] = "hit_miss_uncertainty"
        candidate["hit_miss_uncertainty"] = None
        candidate["hit_miss_uncertainty"] = {"status": "resolved", "schema_version": "deterministic-predictive-hit-miss-uncertainty-v1", "move_id": "water-gun", "probability_percent": probability, "branches": ({"branch": branch},), "guaranteed_facts": {}}
        presentation = present_strategy_explanation(explanation=explanation)
        row = next(item for item in presentation["candidates"] if item["candidate_id"] == "attack:water-gun")
        assert expected in row["uncertainty_labels"][0]


def test_malformed_or_inconsistent_explanation_rejects_without_repair() -> None:
    malformed = _explanation()
    malformed["decision_owner"]["session_id"] = "foreign-session"

    presentation = present_strategy_explanation(explanation=malformed)

    assert presentation["status"] == "rejected"
    assert presentation["reason"] == "inconsistent_strategy_explanation_d0"
    assert render_strategy_explanation(presentation=presentation) == "결정론적 전략 설명을 표시할 수 없습니다."


def test_panel_displays_precomputed_explanation_without_requesting_provider_or_strategy() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    requests: list[str] = []
    panel.advice_requested.connect(lambda: requests.append("advice"))
    panel.structured_advice_requested.connect(lambda: requests.append("structured"))
    explanation = _explanation()
    before = deepcopy(explanation)

    presentation = panel.set_strategy_explanation(explanation)

    assert explanation == before
    assert presentation["status"] == "resolved"
    assert "결정론적 전략 분석" in panel.output_edit.toPlainText()
    assert "즉시 행동 결과만" in panel.output_edit.toPlainText()
    assert "관측 결과 필요" in panel.output_edit.toPlainText()
    assert requests == []


def test_orchestration_to_explanation_to_panel_uses_only_the_presentation_boundary(
    monkeypatch,
) -> None:
    candidates = [
        {"schema_version": "deterministic-action-candidate-v1", "candidate_id": "attack:seismic-toss", "action_type": "attack", "decision_owner": OWNER, "source_branch_fingerprint": "d0", "execution_readiness": "execution_incomplete"},
        {"schema_version": "deterministic-action-candidate-v1", "candidate_id": "attack:water-gun", "action_type": "attack", "decision_owner": OWNER, "source_branch_fingerprint": "d0", "execution_readiness": "execution_incomplete"},
    ]
    selection = {"status": "resolved", "session_id": "session-1", "decision_branch_fingerprint": "d0", "decision_owner": OWNER}
    execution = {**selection, "schema_version": "deterministic-current-execution-authority-v1"}
    monkeypatch.setattr(orchestration_subject, "discover_candidates", lambda **_: {"status": "resolved", "candidates": deepcopy(candidates), "candidate_set_completeness": "complete"})
    monkeypatch.setattr(orchestration_subject, "enrich_discovered_candidates", lambda **_: {"status": "resolved", "candidates": deepcopy(candidates)})
    monkeypatch.setattr(orchestration_subject, "enrich_predictive_attack_candidate", lambda **kwargs: {"status": "resolved", "candidate": kwargs["candidate"]})
    monkeypatch.setattr(orchestration_subject, "materialize_predictive_fixed_damage_outcome", lambda **_: {"status": "complete", "outcome": {"candidate_id": "attack:seismic-toss"}})
    monkeypatch.setattr(orchestration_subject, "guaranteed_facts_from_exact_outcome", lambda **_: {"status": "resolved", "guaranteed_opponent_fainted": True})
    monkeypatch.setattr(orchestration_subject, "build_predictive_water_gun_interval", lambda **_: {"completeness": "exact_complete"})
    monkeypatch.setattr(orchestration_subject, "guaranteed_facts_from_water_gun_interval", lambda **_: {"status": "resolved", "possible_opponent_ko": True})
    monkeypatch.setattr(orchestration_subject, "rank_guaranteed_candidates", lambda **_: {"status": "resolved", "preferred_frontier": ["attack:seismic-toss"], "pairwise_matrix": []})

    orchestration = orchestration_subject.run_detached_strategy_orchestration(
        decision_state={"active": {"self": {"current_hp": 100}}},
        decision_owner=OWNER,
        selection_snapshot=selection,
        execution_bundle=execution,
        predictive_attacks={"attack:seismic-toss": {}},
        water_gun_inputs={"target_owner": {}, "snapshot_damage_input": {}, "stat_provenance": {}, "trusted_level": 50},
    )
    explanation = explain_detached_strategy(orchestration=orchestration)
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()

    presentation = panel.set_strategy_explanation(explanation)

    assert presentation["status"] == "resolved"
    assert "기술: Seismic Toss" in panel.output_edit.toPlainText()
    assert "기술: Water Gun" in panel.output_edit.toPlainText()
