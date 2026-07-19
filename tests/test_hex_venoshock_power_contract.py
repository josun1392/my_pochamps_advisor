from llm.advisor_battle_state_context import build_binary_condition_power_assessment


def test_hex_and_venoshock_conditions():
    poison = {"current_conditions": [{"side": "opponent", "condition_type": "poison"}]}
    burn = {"current_conditions": [{"side": "opponent", "condition_type": "burn"}]}
    assert build_binary_condition_power_assessment({"move_id": "hex"}, burn, None)["effective_power"] == 130
    assert build_binary_condition_power_assessment({"move_id": "venoshock"}, poison, None)["effective_power"] == 130
*** Add File: C:\Users\jsp33\OneDrive\Desktop\내 파일\project\대학\파이썬\tests\test_brine_power_contract.py
from llm.advisor_battle_state_context import build_binary_condition_power_assessment


def test_brine_exact_half_doubles():
    hp = {"current_hp": [{"side": "opponent", "current_hp": 100, "maximum_hp": 200}]}
    assert build_binary_condition_power_assessment({"move_id": "brine"}, None, hp)["effective_power"] == 130
