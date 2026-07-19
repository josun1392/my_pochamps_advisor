from llm import advisor_client as client


SCOPE = "direct-max-hp-proportional-healing-only"


def _context(status: str = "resolved") -> dict[str, object]:
    result: dict[str, object] = {"move": "recover", "status": status, "scope": SCOPE}
    if status == "resolved": result.update(healing_percent=50, raw_healing=150, actual_healing=80, current_hp=221, maximum_hp=301, resulting_hp=301)
    elif status == "no_effect": result.update(healing_percent=50, raw_healing=150, actual_healing=0, current_hp=301, maximum_hp=301, resulting_hp=301, reason="already_at_full_hp")
    else: result.update(reason="unsupported_direct_healing_rule")
    return {"deterministic_calculation_context": {"direct_healing_assessment": result}}


def _response(line: str, advice: str = "Current HP supports the limited healing assessment.") -> str:
    return f"[Trusted Context]\n[Deterministic Results]\n{line}\n[Advice]\n{advice}"


def test_mocked_resolved_production_acknowledgement_is_exact() -> None:
    expected = client.build_deterministic_result_acknowledgement_entries(_context())
    response = _response("- Direct healing | self | recover | 50% | 80 HP | 301/301 | direct-max-hp-proportional-healing-only")
    assert client.validate_deterministic_result_acknowledgement(response, expected) is None


def test_mocked_full_hp_and_unsupported_paths_are_exact() -> None:
    full = _response("- Direct healing | self | recover | 50% | 0 HP | already-at-full-hp | direct-max-hp-proportional-healing-only")
    unsupported = _response("- Direct healing | self | synthesis | unavailable | unsupported-direct-healing-rule")
    assert client.validate_deterministic_result_acknowledgement(full, client.build_deterministic_result_acknowledgement_entries(_context("no_effect"))) is None
    unsupported_context = {"deterministic_calculation_context": {"direct_healing_assessment": {"move": "synthesis", "status": "unavailable", "reason": "unsupported_direct_healing_rule", "scope": SCOPE}}}
    assert client.validate_deterministic_result_acknowledgement(unsupported, client.build_deterministic_result_acknowledgement_entries(unsupported_context)) is None


def test_acknowledgement_mutations_are_rejected() -> None:
    expected = client.build_deterministic_result_acknowledgement_entries(_context())
    good = _response("- Direct healing | self | recover | 50% | 80 HP | 301/301 | direct-max-hp-proportional-healing-only")
    for old, new in (("50%", "25%"), ("80 HP", "81 HP"), ("301/301", "300/301"), ("recover", "roost"), (SCOPE, "wrong-scope")):
        assert client.validate_deterministic_result_acknowledgement(good.replace(old, new), expected) is not None


def test_status_reason_missing_duplicate_and_gate_off_insertions_are_rejected() -> None:
    expected = client.build_deterministic_result_acknowledgement_entries(_context())
    good = _response("- Direct healing | self | recover | 50% | 80 HP | 301/301 | direct-max-hp-proportional-healing-only")
    assert client.validate_deterministic_result_acknowledgement(good.replace("[Deterministic Results]\n", "[Deterministic Results]\n- Direct healing | self | recover | 50% | 80 HP | 301/301 | direct-max-hp-proportional-healing-only\n"), expected) is not None
    assert client.validate_deterministic_result_acknowledgement(_response("- Direct healing | self | recover | unavailable | unsupported-direct-healing-rule"), expected) is not None
    assert client.validate_deterministic_result_acknowledgement(good.replace("- Direct healing", ""), expected) is not None
    assert client.validate_deterministic_result_acknowledgement(good, ()) is not None


def test_semantic_ability_weather_and_delayed_claims_are_rejected() -> None:
    expected = client.build_deterministic_result_acknowledgement_entries(_context())
    line = "- Direct healing | self | recover | 50% | 80 HP | 301/301 | direct-max-hp-proportional-healing-only"
    for claim in ("Big Root adds more healing.", "Synthesis will heal more in rain.", "Wish heals next turn.", "This is expected healing after hit chance."):
        assert client.evaluate_deterministic_result_response(_response(line, claim), (), expected) == "deterministic-results semantic boundary violation"
