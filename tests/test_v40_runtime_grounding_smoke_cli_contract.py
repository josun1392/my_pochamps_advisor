from pathlib import Path
import subprocess
import sys

from scripts.run_sanitized_runtime_grounding_smoke import DEFAULT_MODEL, EXIT, REQUIRED_FIXTURES, main, run_smoke


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = PROJECT_ROOT / "scripts" / "run_sanitized_runtime_grounding_smoke.py"


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


def test_cli_actual_constructs_adapters_only_after_valid_arguments():
    calls = []
    def factory(*, model):
        calls.append(model)
        return (lambda: False), (lambda _: {})
    assert main(["--actual", "--model", DEFAULT_MODEL, "--fixtures", *REQUIRED_FIXTURES, "--max-calls", "2", "--no-retry"], actual_adapter_factory=factory) == EXIT["credential"]
    assert calls == [DEFAULT_MODEL]
    assert main([], actual_adapter_factory=factory) == EXIT["ok"]


def test_smoke_runner_maps_parse_failure_to_exit_5():
    result = run_smoke(actual=True, model=DEFAULT_MODEL, fixtures=REQUIRED_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=lambda _: [])
    assert result["exit_code"] == EXIT["parse"] and result["provider_calls"] == 1


def test_smoke_runner_maps_grounding_structure_failure_to_exit_6():
    result = run_smoke(actual=True, model=DEFAULT_MODEL, fixtures=REQUIRED_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=lambda _: {"grounding": {"schema_version": "wrong"}})
    assert result["exit_code"] == EXIT["structural"] and result["provider_calls"] == 1 and result["diagnostic_code"] == "grounding_version_invalid"


def test_runtime_unknown_bootstrap_fake_provider_reaches_semantic_validation_after_structural_pass():
    calls = []
    def fake(fixture_id):
        calls.append(fixture_id)
        return {"grounding": {"schema_version": "grounding-v1", "confirmed_facts": [], "unknown_facts": [{"path": "field.weather"}], "evidence_only": [], "conflicts": [], "conditional_dependencies": []}}
    result = run_smoke(actual=True, model=DEFAULT_MODEL, fixtures=REQUIRED_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=fake)
    assert result["exit_code"] == EXIT["ok"] and calls == list(REQUIRED_FIXTURES)


def test_direct_script_subprocess_imports_project_and_stops_at_unavailable_credential():
    code = f"""
import os
import runpy
import sys
import types
import config
fake_loader = types.ModuleType('config.env_loader')
fake_loader.load_dotenv = lambda **kwargs: None
sys.modules['config.env_loader'] = fake_loader
os.environ.pop('GEMINI_API_KEY', None)
os.environ.pop('GOOGLE_API_KEY', None)
sys.argv = [{str(RUNNER)!r}, '--actual', '--model', {DEFAULT_MODEL!r}, '--fixtures', *{list(REQUIRED_FIXTURES)!r}, '--max-calls', '2', '--no-retry']
runpy.run_path({str(RUNNER)!r}, run_name='__main__')
"""
    process = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == EXIT["credential"]
    assert process.stdout == process.stderr == ""


def test_direct_script_subprocess_rejects_invalid_arguments_before_adapter_construction():
    process = subprocess.run(
        [sys.executable, str(RUNNER), "--actual", "--model", "not-allowlisted", "--no-retry"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == EXIT["usage"]
    assert process.stdout == process.stderr == ""


def test_direct_script_subprocess_allows_fake_provider_to_reach_grounding_validation():
    code = f"""
import runpy
import sys
import llm.advisor_client as client
client.call_structured_recommendation_provider = lambda **kwargs: ({{'grounding': {{'schema_version': 'grounding-v1', 'confirmed_facts': [], 'unknown_facts': [{{'path': 'field.weather'}}], 'evidence_only': [], 'conflicts': [], 'conditional_dependencies': []}}}}, {{}})
sys.argv = [{str(RUNNER)!r}, '--actual', '--model', {DEFAULT_MODEL!r}, '--fixtures', *{list(REQUIRED_FIXTURES)!r}, '--max-calls', '2', '--no-retry']
runpy.run_path({str(RUNNER)!r}, run_name='__main__')
"""
    process = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    assert process.returncode == EXIT["ok"]
    assert process.stdout == process.stderr == ""
