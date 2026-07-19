import llm.advisor_client as client


def test_drain_effect_acknowledgement_is_exact() -> None:
    expected = (("drain_recoil", "drain", "giga-drain", "50%", "30-35 HP", "damage-dealt-proportional-drain-recoil-only"),)
    response = "[Trusted Context]\n[Deterministic Results]\n- Drain effect | self | giga-drain | 50% | 30-35 HP | damage-dealt-proportional-drain-recoil-only\n[Advice]\nRecovery is limited to the calculated damage dealt."
    assert client.validate_deterministic_result_acknowledgement(response, expected) is None
    assert client.validate_deterministic_result_acknowledgement(response.replace("50%", "60%"), expected) is not None
