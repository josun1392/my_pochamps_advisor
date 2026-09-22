from llm.advisor_multi_hit_graph_reconciliation import _parent_matches_leaf


def test_effect_spore_and_contact_reactive_terminal_reasons_remain_distinct():
    effect_parent = {
        "action_outcome": "landed",
        "landed_hit_count": 1,
        "terminal_reason": "effect_spore_sleep_cancels_remaining_hits",
    }
    attacker_ko_parent = {
        "action_outcome": "landed",
        "landed_hit_count": 1,
        "terminal_reason": "attacker_fainted_from_contact_reactive_damage",
    }
    target_ko_parent = {
        "action_outcome": "landed",
        "landed_hit_count": 1,
        "terminal_reason": "target_fainted",
    }
    effect_leaf = {
        "hit_state": "hit",
        "ordered_hits": ({"hit_index": 1},),
        "consequences": {"terminal_reason": "effect_spore_sleep_cancels_remaining_hits"},
    }
    attacker_ko_leaf = {
        "hit_state": "hit",
        "ordered_hits": ({"hit_index": 1},),
        "consequences": {"terminal_reason": "attacker_fainted_from_contact_reactive_damage"},
    }
    target_ko_leaf = {
        "hit_state": "hit",
        "ordered_hits": ({"hit_index": 1},),
        "consequences": {"terminal_reason": "target_fainted"},
    }
    assert _parent_matches_leaf(effect_parent, effect_leaf)
    assert not _parent_matches_leaf(effect_parent, attacker_ko_leaf)
    assert not _parent_matches_leaf(effect_parent, target_ko_leaf)
    assert _parent_matches_leaf(attacker_ko_parent, attacker_ko_leaf)
    assert not _parent_matches_leaf(attacker_ko_parent, target_ko_leaf)
    assert _parent_matches_leaf(target_ko_parent, target_ko_leaf)
