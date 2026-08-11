from llm.advisor_identity_groundedness import arena_trap_prerequisite, build_groundedness, normalize_groundedness
def test_exact_identity_unknown_and_arena_prerequisite():
    g=build_groundedness(session_id="s",side="self",slot_index=0,pokemon_id="a",status="grounded")
    ability={"ability_id":"arena-trap","applicability":"applicable","interaction":"affecting"}
    assert arena_trap_prerequisite(ability_authority=ability,groundedness=g)["status"]=="complete"
    assert normalize_groundedness(g,session_id="s",side="self",slot_index=0,pokemon_id="b")["status"]=="unknown"
