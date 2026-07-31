from llm.advisor_candidate_contract import _comparison_facts, build_recommendation_request, evaluate_move_candidate
from llm.advisor_client import format_recommendation_presentation_text
from core.pokeapi_fetcher import PokeAPIFetcher


def _status_candidate(slot, move, metadata):
    return evaluate_move_candidate(slot_index=slot, move=move, battle_snapshot={}, repositories={move: {"category": "status", **metadata}})


def test_pokeapi_normalizer_retains_only_bounded_role_metadata_fields():
    normalized = PokeAPIFetcher._normalize_move({
        "id": 105, "name": "recover", "names": [], "type": {"name": "normal"}, "damage_class": {"name": "status"},
        "power": None, "accuracy": None, "pp": 5, "priority": 0, "effect_chance": None, "target": {"name": "user"},
        "meta": {"ailment": {"name": "none"}, "category": {"name": "heal"}, "healing": 50, "drain": 0, "min_hits": None, "max_hits": None},
        "stat_changes": [{"stat": {"name": "attack"}, "change": 1}],
    })
    assert normalized["target"] == "user"
    assert normalized["meta"] == {"ailment": "none", "category": "heal", "drain": 0, "healing": 50, "min_hits": None, "max_hits": None}
    assert normalized["stat_changes"] == [{"stat": "attack", "change": 1}]


def test_canonical_status_metadata_produces_only_proven_roles_and_keeps_damage_not_applicable():
    recover = _status_candidate(0, "recover", {"target": "user", "healing": 50, "effect_category": "heal"})
    will_o_wisp = _status_candidate(1, "will-o-wisp", {"target": "selected-pokemon", "ailment": "burn", "effect_category": "ailment"})
    swords_dance = _status_candidate(2, "swords-dance", {"target": "user", "stat_changes": [{"stat": "attack", "change": 2}], "effect_category": "net-good-stats"})
    assert recover["damage"] == {"status": "not_applicable"}
    assert recover["status_move_evidence"]["role_tags"] == ["recovery"]
    assert will_o_wisp["status_move_evidence"]["role_tags"] == ["status_infliction"]
    assert swords_dance["status_move_evidence"]["role_tags"] == ["self_stat_raise"]
    assert all(candidate["action_order"]["status"] == "insufficient_context" for candidate in (recover, will_o_wisp, swords_dance))


def test_status_role_unknown_and_malformed_metadata_never_become_known_utility():
    missing = _status_candidate(0, "mystery", {})
    malformed = _status_candidate(1, "broken", {"target": "user", "stat_changes": "not-a-list"})
    assert missing["status_move_evidence"]["status"] == "insufficient_context"
    assert missing["status_move_evidence"]["role_tags"] == []
    assert malformed["status_move_evidence"]["status"] == "unsupported_mechanic"
    assert malformed["status_move_evidence"]["role_tags"] == []


def test_status_comparison_facts_are_candidate_local_without_damage_ranking():
    candidates = [
        _status_candidate(0, "recover", {"target": "user", "healing": 50, "effect_category": "heal"}),
        _status_candidate(1, "will-o-wisp", {"target": "selected-pokemon", "ailment": "burn", "effect_category": "ailment"}),
    ]
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})
    rows = request["candidate_comparisons"]
    assert [row["mechanics_comparison"]["rank"] for row in rows] == [None, None]
    assert "known_recovery_role" in rows[0]["comparison_facts"]["comparison_tags"]
    assert "known_status_infliction_role" in rows[1]["comparison_facts"]["comparison_tags"]
    assert rows[0]["comparison_facts"]["candidate_id"] == {"slot_index": 0, "move": "recover"}
    assert rows[1]["comparison_facts"]["candidate_id"] == {"slot_index": 1, "move": "will-o-wisp"}
    assert all("damage_range" not in row["mechanics_result"] for row in rows)


def test_status_presentation_uses_only_bounded_role_labels_and_hides_internal_metadata():
    presentation = {
        "status": "resolved",
        "recommended_move": "recover",
        "recommended_slot_index": 1,
        "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [], "errors": [],
        "selected_candidate": {
            "selected_action": {"slot_index": 1, "move": "recover"},
            "evidence": {
                "mechanics_result": {"status": "unsupported_mechanic"},
                "action_order": {"status": "insufficient_context"},
                "status_move_evidence": {"status": "known_role", "role_tags": ["recovery"], "canonical_effect_tags": ["canonical_healing"], "target_scope": "user", "uncertainty": []},
                "comparison_facts": {"comparison_tags": ["known_recovery_role"]},
            },
        },
    }
    text = format_recommendation_presentation_text(presentation_model=presentation)
    assert "기술 역할: 회복" in text
    assert "canonical_healing" not in text and "target_scope" not in text and "damage_range" not in text
