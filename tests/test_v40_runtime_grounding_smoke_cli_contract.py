from scripts.run_sanitized_runtime_grounding_smoke import DEFAULT_MODEL, EXIT, REQUIRED_FIXTURES, run_smoke


def test_smoke_runner_defaults_to_offline_no_network():
    assert run_smoke()["provider_calls"] == run_smoke()["network_calls"] == 0


def test_actual_requires_explicit_valid_contract_and_no_retry():
    assert run_smoke(actual=True)["exit_code"] == EXIT["usage"]
    assert run_smoke(actual=True, model=DEFAULT_MODEL, fixtures=REQUIRED_FIXTURES, max_calls=2, no_retry=False)["exit_code"] == EXIT["usage"]


def test_fake_provider_is_budgeted_and_stops_after_failure():
    calls = []
    def fake(value): calls.append(value); return {"grounding": {"schema_version": "grounding-v1", "confirmed_facts": [{"path": "field.weather", "status": "known", "value": "sun"}], "unknown_facts": [], "evidence_only": [], "conflicts": [], "conditional_dependencies": []}}
    result = run_smoke(actual=True, model=DEFAULT_MODEL, fixtures=REQUIRED_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=fake)
    assert result["exit_code"] == EXIT["semantic"] and calls == [REQUIRED_FIXTURES[0]] and result["network_calls"] == 0


def test_credential_is_injected_boolean_only():
    assert run_smoke(actual=True, model=DEFAULT_MODEL, fixtures=REQUIRED_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: False)["exit_code"] == EXIT["credential"]


def test_smoke_runner_maps_parse_failure_to_exit_5():
    result = run_smoke(actual=True, model=DEFAULT_MODEL, fixtures=REQUIRED_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=lambda _: [])
    assert result["exit_code"] == EXIT["parse"] and result["provider_calls"] == 1


def test_smoke_runner_maps_grounding_structure_failure_to_exit_6():
    result = run_smoke(actual=True, model=DEFAULT_MODEL, fixtures=REQUIRED_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=lambda _: {"grounding": {"schema_version": "wrong"}})
    assert result["exit_code"] == EXIT["structural"] and result["provider_calls"] == 1
