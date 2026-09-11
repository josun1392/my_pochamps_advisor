from llm.advisor_exact_pair_native_two_turn_lifecycle_execution import execute_exact_pair_native_two_turn_lifecycle
from llm.advisor_two_turn_execution import LEGACY_SCHEMA_VERSION, execute_explicit_two_turn
from tests.test_end_of_turn_residual_phase import _ledger
from tests.test_exact_eot_post_action_lifecycle_coordinator import _teams
from tests.test_exact_immediate_pair_to_eot_phase_input import _authorities
from tests.test_exact_pair_native_two_turn_lifecycle_execution import _eot, _hazards, _turn
from tests.test_two_turn_execution import _plan, _snapshot


def test_legacy_transition_preview_result_is_explicitly_legacy_and_cannot_be_exact_pair_source():
    snapshot = _snapshot(); first = _plan(snapshot)
    legacy = execute_explicit_two_turn(starting_turn_snapshot=snapshot, turn_one=first, turn_two={**first, "start_branch_fingerprint": "foreign"})
    assert legacy["schema_version"] == LEGACY_SCHEMA_VERSION
    assert legacy["provenance"] == "legacy_bounded_transition_preview_two_turn_execution_v1"

    authorities, hazards = _authorities(), _hazards(_ledger())
    rejected = execute_exact_pair_native_two_turn_lifecycle(
        turn_one=_turn(legacy, authorities, _teams(_eot(_ledger(), authorities, hazards)), hazards), turn_two=None,
    )
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "exact_immediate_pair_terminal_source_invalid"


def test_exact_executor_never_calls_legacy_bounded_eot(monkeypatch):
    import llm.advisor_two_turn_execution as legacy_module
    monkeypatch.setattr(legacy_module, "_project_bounded_eot", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy EOT called")))
    ledger, authorities, hazards = _ledger(), _authorities(), _hazards(_ledger())
    result = execute_exact_pair_native_two_turn_lifecycle(
        turn_one=_turn(ledger, authorities, _teams(_eot(ledger, authorities, hazards)), hazards), turn_two=None,
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "turn_two_exact_pair_required"
