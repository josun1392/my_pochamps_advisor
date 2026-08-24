from llm.advisor_predictive_normal_formula_post_hit import compose_predictive_normal_formula_post_hit
from tests.test_predictive_normal_formula_interval import _run


def _interval(move, *, hp=100, sub="known_inactive", sub_hp=None): return _run(move, hp=hp, substitute=sub, substitute_hp=sub_hp)


def test_recoil_uses_actual_capped_damage_and_preserves_possible_own_ko() -> None:
    move={"move_id":"brave-bird","category":"physical","power":120,"type":"flying","drain":-33}
    interval=_interval(move,hp=20)
    result=compose_predictive_normal_formula_post_hit(interval=interval,move_metadata=move,attacker_hp={"current_hp":6,"max_hp":100},attacker_item=None,attacker_ability="pressure",target_ability="pressure")
    assert result["status"]=="resolved" and all(row["actual_damage"]==20 for row in result["branches"])
    assert result["guaranteed_attacker_faint"] and result["ordering"]==["direct_damage","move_native_hp_effect","life_orb_post_hit"]
    possible=compose_predictive_normal_formula_post_hit(interval=_interval(move),move_metadata=move,attacker_hp={"current_hp":16,"max_hp":100},attacker_item=None,attacker_ability="pressure",target_ability="pressure")
    assert possible["possible_attacker_faint"] and not possible["guaranteed_attacker_faint"]


def test_drain_caps_healing_and_life_orb_applies_after_move_native_effect() -> None:
    move={"move_id":"giga-drain","category":"special","power":75,"type":"grass","drain":50}
    interval=_interval(move,hp=100)
    result=compose_predictive_normal_formula_post_hit(interval=interval,move_metadata=move,attacker_hp={"current_hp":95,"max_hp":100},attacker_item="life-orb",attacker_ability="pressure",target_ability="pressure")
    assert result["status"]=="resolved"
    assert all(row["attacker_post_hit_hp"]==90 and row["life_orb_recoil"]==10 for row in result["branches"])
    assert result["guaranteed_attacker_survival"]


def test_immunity_substitute_and_unknown_hp_fail_closed_without_forcing_post_hit_effects() -> None:
    move={"move_id":"giga-drain","category":"special","power":75,"type":"grass","drain":50}
    sub=compose_predictive_normal_formula_post_hit(interval=_interval(move,sub="known_active",sub_hp=30),move_metadata=move,attacker_hp={"current_hp":50,"max_hp":100},attacker_item=None,attacker_ability="pressure",target_ability="pressure")
    unknown=compose_predictive_normal_formula_post_hit(interval=_interval(move),move_metadata=move,attacker_hp={},attacker_item=None,attacker_ability="pressure",target_ability="pressure")
    item_unknown=compose_predictive_normal_formula_post_hit(interval=_interval(move),move_metadata=move,attacker_hp={"current_hp":50,"max_hp":100},attacker_item=None,attacker_item_known=False,attacker_ability="pressure",target_ability="pressure")
    assert sub["reason"]=="substitute_damage_dealt_authority_unavailable" and unknown["reason"]=="attacker_hp_unknown"
    assert item_unknown["reason"]=="attacker_item_authority_unknown"
