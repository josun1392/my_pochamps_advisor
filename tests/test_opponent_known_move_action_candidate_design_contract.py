from __future__ import annotations

from copy import deepcopy


def _candidate(*, session: str, pokemon: str, move: str, state: str, index: int) -> dict[str, object]:
    return {
        "candidate_id": f"opponent-action:{session}:{pokemon}:{move}:{index}",
        "acting_side": "opponent", "target_side": "self", "opponent_pokemon_id": pokemon,
        "move_id": move, "move_identity_authority": "frozen_known_move_context",
        "moveset_state": state,
    }


def test_candidate_source_contract_preserves_unknown_partial_complete_and_deterministic_identity():
    unknown: list[str] = []
    partial = ["earthquake", "protect"]
    complete = ["earthquake", "protect", "swords-dance", "stone-edge"]
    build = lambda moves, state, pokemon: [_candidate(session="s", pokemon=pokemon, move=move, state=state, index=index) for index, move in enumerate(moves)]

    assert build(unknown, "unknown", "garchomp") == []
    partial_candidates = build(partial, "partially_known", "garchomp")
    assert [item["move_id"] for item in partial_candidates] == partial
    assert all(item["moveset_state"] == "partially_known" for item in partial_candidates)
    assert len(build(complete, "complete", "garchomp")) == 4
    assert _candidate(session="s", pokemon="garchomp", move="earthquake", state="partial", index=0)["candidate_id"] != _candidate(session="s", pokemon="rhyperior", move="earthquake", state="partial", index=0)["candidate_id"]


def test_known_identity_and_mechanics_supportability_are_independent_layers():
    candidate = _candidate(session="s", pokemon="garchomp", move="earthquake", state="partially_known", index=0)
    incomplete = {**candidate, "damage_supportability": "insufficient_context"}
    unsupported = {**candidate, "damage_supportability": "unsupported_mechanic"}

    assert incomplete["move_identity_authority"] == unsupported["move_identity_authority"] == "frozen_known_move_context"
    assert incomplete["damage_supportability"] != unsupported["damage_supportability"]
    assert candidate["acting_side"] == "opponent" and candidate["target_side"] == "self"


def test_frozen_active_identity_excludes_inactive_and_post_snapshot_known_moves():
    frozen = {"active": "garchomp", "known": {"garchomp": ["earthquake"], "umbreon": ["wish"]}}
    current = deepcopy(frozen)
    current["active"] = "umbreon"; current["known"]["garchomp"].append("protect")

    assert frozen["known"][frozen["active"]] == ["earthquake"]
    assert current["known"][current["active"]] == ["wish"]
    assert "wish" not in frozen["known"][frozen["active"]]


def test_design_excludes_species_legacy_provider_and_self_selection_as_candidate_sources():
    forbidden_sources = {"species_learnset", "common_set", "legacy_opponent_move_context", "provider", "self_ui_selection"}
    assert forbidden_sources.isdisjoint({"frozen_known_move_context"})
