from __future__ import annotations

from copy import deepcopy

import pytest


TRUSTED_PROVENANCE = {"user_confirmed", "observed_in_battle", "trusted_reducer_event"}


def _move(move_id: str, provenance: str = "observed_in_battle") -> dict[str, str]:
    return {"move_id": move_id, "provenance": provenance}


def _active(*, side: str, pokemon_id: str, slot_index: int, moves: list[dict[str, str]]) -> dict[str, object]:
    """Fixture-only canonical design validator; production integration is deferred."""
    identifiers = [move.get("move_id") for move in moves]
    if (
        side not in {"self", "opponent"}
        or not pokemon_id
        or not isinstance(slot_index, int)
        or any(not isinstance(move_id, str) or not move_id for move_id in identifiers)
        or any(move.get("provenance") not in TRUSTED_PROVENANCE for move in moves)
        or len(set(identifiers)) != len(identifiers)
        or len(identifiers) > 4
    ):
        raise ValueError("malformed_known_move_context")
    state = "unknown" if not identifiers else "complete" if len(identifiers) == 4 else "partially_known"
    return {
        "side": side,
        "slot_index": slot_index,
        "pokemon_id": pokemon_id,
        "state": state,
        "known_move_ids": tuple(identifiers),
        "unknown_slot_count": 4 - len(identifiers),
    }


@pytest.mark.parametrize(
    ("moves", "state", "unknown_slots"),
    [([], "unknown", 4), ([_move("protect")], "partially_known", 3), ([_move("protect"), _move("recover")], "partially_known", 2), ([_move("protect"), _move("recover"), _move("toxic")], "partially_known", 1), ([_move("protect"), _move("recover"), _move("toxic"), _move("wish")], "complete", 0)],
)
def test_known_move_set_design_preserves_unknown_partial_and_complete_semantics(moves, state, unknown_slots):
    context = _active(side="opponent", pokemon_id="umbreon", slot_index=1, moves=moves)

    assert context["state"] == state
    assert context["unknown_slot_count"] == unknown_slots
    assert len(context["known_move_ids"]) + unknown_slots == 4


@pytest.mark.parametrize(
    "moves",
    [
        [_move("protect"), _move("protect")],
        [_move("a"), _move("b"), _move("c"), _move("d"), _move("e")],
        [{"move_id": "protect", "provenance": "species_learnset"}],
        [{"move_id": "", "provenance": "user_confirmed"}],
    ],
)
def test_known_move_design_rejects_duplicate_over_capacity_invalid_or_inferred_bulk_authority(moves):
    with pytest.raises(ValueError, match="malformed_known_move_context"):
        _active(side="opponent", pokemon_id="umbreon", slot_index=1, moves=moves)


def test_repeated_single_observation_is_idempotent_but_does_not_complete_or_create_negative_inference():
    observed = _active(side="opponent", pokemon_id="umbreon", slot_index=1, moves=[_move("protect")])
    repeated_observation = _active(side="opponent", pokemon_id="umbreon", slot_index=1, moves=[_move("protect")])

    assert repeated_observation == observed
    assert observed["state"] == "partially_known"
    assert observed["unknown_slot_count"] == 3
    assert "wish" not in observed["known_move_ids"]


def test_side_and_pokemon_identity_keep_known_move_sets_independent_across_switches():
    active_umbreon = _active(side="opponent", pokemon_id="umbreon", slot_index=1, moves=[_move("protect")])
    switched_gengar = _active(side="opponent", pokemon_id="gengar", slot_index=2, moves=[_move("shadow-ball")])
    self_pikachu = _active(side="self", pokemon_id="pikachu", slot_index=0, moves=[_move("thunderbolt")])

    assert active_umbreon["known_move_ids"] == ("protect",)
    assert switched_gengar["known_move_ids"] == ("shadow-ball",)
    assert self_pikachu["known_move_ids"] == ("thunderbolt",)
    assert active_umbreon["pokemon_id"] != switched_gengar["pokemon_id"]
    assert active_umbreon["side"] != self_pikachu["side"]


def test_request_start_context_is_detached_and_stale_session_or_ui_selection_is_not_move_authority():
    captured = {
        "session_id": "session-1",
        "self": _active(side="self", pokemon_id="pikachu", slot_index=0, moves=[]),
        "opponent": _active(side="opponent", pokemon_id="umbreon", slot_index=1, moves=[_move("protect")]),
    }
    request_start = deepcopy(captured)
    captured["opponent"] = _active(side="opponent", pokemon_id="umbreon", slot_index=1, moves=[_move("protect"), _move("wish")])

    assert request_start["opponent"]["known_move_ids"] == ("protect",)
    assert captured["opponent"]["known_move_ids"] == ("protect", "wish")
    assert request_start["session_id"] != "session-2"
    # A UI candidate selection is recommendation input, not an observed moveset event.
    assert request_start["self"]["state"] == "unknown"
