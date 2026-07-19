from llm.advisor_battle_state_context import build_hp_based_special_damage_assessment
def test_only_endeavor_and_final_gambit_have_hp_special_results():
 assert build_hp_based_special_damage_assessment({"move_id":"tackle"},None) is None
