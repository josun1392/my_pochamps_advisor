import pytest

from llm.advisor_opponent_move_context import (
    OPPONENT_MOVE_CONTEXT_FORBIDDEN_FIELDS,
    OPPONENT_MOVE_CONTEXT_UNSUPPORTED_BOUNDARIES,
    build_opponent_move_context,
)


def test_empty_input_returns_unknown_limited_context_without_inference() -> None:
    context = build_opponent_move_context()

    assert context["kind"] == "opponent_move_context"
    assert context["confidence"] == "unknown"
    assert context["selected_opponent_move"] == {"status": "unknown"}
    assert context["known_opponent_moves"] == []
    assert context["candidate_moves"] == []
    assert context["priority_move_candidates"] == []
    assert "Candidate moves are not confirmed selected moves." in context["safety_notes"]
    _assert_no_forbidden_fields(context)


def test_known_move_with_trusted_source_becomes_confirmed() -> None:
    context = build_opponent_move_context(
        known_moves=[
            {
                "source": "user_confirmed",
                "move_id": "thunderbolt",
                "name": "Thunderbolt",
                "type": "electric",
                "category": "special",
                "power": 90,
                "accuracy": 100,
                "priority": 0,
            }
        ]
    )

    assert context["confidence"] == "limited"
    assert context["known_opponent_moves"] == [
        {
            "source": "user_confirmed",
            "move_id": "thunderbolt",
            "name": "Thunderbolt",
            "type": "electric",
            "category": "special",
            "power": 90,
            "accuracy": 100,
            "priority": 0,
            "confirmed": True,
        }
    ]


def test_known_move_with_untrusted_source_is_omitted() -> None:
    context = build_opponent_move_context(
        known_moves=[
            {
                "source": "species_common_set",
                "move_id": "earthquake",
                "name": "Earthquake",
            }
        ]
    )

    assert context["known_opponent_moves"] == []
    assert context["confidence"] == "unknown"


def test_candidate_move_remains_unconfirmed_and_unselected() -> None:
    context = build_opponent_move_context(
        candidate_moves=[
            {
                "source": "visible_or_cache_candidate",
                "move_id": "quick-attack",
                "name": "Quick Attack",
                "type": "normal",
                "category": "physical",
                "power": 40,
                "accuracy": 100,
                "priority": 1,
            }
        ]
    )

    assert context["candidate_moves"] == [
        {
            "source": "visible_or_cache_candidate",
            "move_id": "quick-attack",
            "name": "Quick Attack",
            "type": "normal",
            "category": "physical",
            "power": 40,
            "accuracy": 100,
            "priority": 1,
            "confirmed": False,
            "selected": False,
        }
    ]


@pytest.mark.parametrize(
    "unsafe_field",
    [
        "confirmed",
        "selected",
        "will_use",
        "likely_selected",
    ],
)
def test_candidate_move_with_selected_or_confirmed_semantics_is_omitted(unsafe_field: str) -> None:
    context = build_opponent_move_context(
        candidate_moves=[
            {
                "source": "visible_ui",
                "move_id": "quick-attack",
                "name": "Quick Attack",
                unsafe_field: True,
            }
        ]
    )

    assert context["candidate_moves"] == []
    assert context["priority_move_candidates"] == []
    _assert_no_forbidden_fields(context)


def test_selected_opponent_move_explicit_is_allowed() -> None:
    context = build_opponent_move_context(
        selected_opponent_move={
            "status": "explicit",
            "source": "explicit_input",
            "move_id": "protect",
            "name": "Protect",
        }
    )

    assert context["selected_opponent_move"] == {
        "status": "explicit",
        "source": "explicit_input",
        "move_id": "protect",
        "name": "Protect",
    }
    assert context["confidence"] == "limited"


@pytest.mark.parametrize("status", ["inferred", "predicted", "likely"])
def test_selected_opponent_move_inferred_predicted_or_likely_is_rejected(status: str) -> None:
    with pytest.raises(ValueError, match="unknown or explicit"):
        build_opponent_move_context(
            selected_opponent_move={
                "status": status,
                "source": "explicit_input",
                "move_id": "protect",
                "name": "Protect",
            }
        )


def test_selected_opponent_move_explicit_requires_trusted_source() -> None:
    with pytest.raises(ValueError, match="trusted source"):
        build_opponent_move_context(
            selected_opponent_move={
                "status": "explicit",
                "source": "usage_based_guess",
                "move_id": "protect",
                "name": "Protect",
            }
        )


def test_candidate_priority_move_creates_unconfirmed_priority_candidate() -> None:
    context = build_opponent_move_context(
        candidate_moves=[
            {
                "source": "visible_or_cache_candidate",
                "move_id": "quick-attack",
                "name": "Quick Attack",
                "priority": 1,
            },
            {
                "source": "visible_or_cache_candidate",
                "move_id": "tackle",
                "name": "Tackle",
                "priority": 0,
            },
        ]
    )

    assert context["priority_move_candidates"] == [
        {
            "source": "visible_or_cache_candidate",
            "move_id": "quick-attack",
            "name": "Quick Attack",
            "priority": 1,
            "confirmed": False,
            "selected": False,
        }
    ]


def test_helper_does_not_infer_moves_without_source_moves() -> None:
    context = build_opponent_move_context(known_moves=None, candidate_moves=None)

    assert context["known_opponent_moves"] == []
    assert context["candidate_moves"] == []
    assert context["selected_opponent_move"] == {"status": "unknown"}


def test_forbidden_fields_absent_from_full_output() -> None:
    context = build_opponent_move_context(
        known_moves=[
            {
                "source": "visible_ui",
                "move_id": "thunderbolt",
                "name": "Thunderbolt",
                "predicted_move": "quick-attack",
                "hidden_item": "quick-claw",
            }
        ],
        candidate_moves=[
            {
                "source": "visible_or_cache_candidate",
                "move_id": "quick-attack",
                "name": "Quick Attack",
                "EVs": {"speed": 252},
                "rng_resolved": True,
            }
        ],
    )

    _assert_no_forbidden_fields(context)


def test_unsupported_boundaries_included() -> None:
    context = build_opponent_move_context()

    assert set(OPPONENT_MOVE_CONTEXT_UNSUPPORTED_BOUNDARIES).issubset(set(context["unsupported"]))


def test_safety_notes_include_candidate_not_confirmed_meaning() -> None:
    context = build_opponent_move_context()

    assert "Candidate moves are not confirmed selected moves." in context["safety_notes"]
    assert "Only explicitly known or visible move data should be treated as known." in context["safety_notes"]


def _assert_no_forbidden_fields(value: object) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            assert key not in OPPONENT_MOVE_CONTEXT_FORBIDDEN_FIELDS
            _assert_no_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _assert_no_forbidden_fields(child_value)
