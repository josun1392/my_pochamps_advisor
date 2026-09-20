from copy import deepcopy

from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation
from llm.advisor_detached_next_turn_action_intent import materialize_detached_next_turn_action_intents, validate_detached_next_turn_action_intents
from tests.test_next_turn_predictive_mechanics_state_transport import _rich_flow, _next_from_phase


def _source():
    _, _, _, phase = _rich_flow()
    _, _, handoff = _next_from_phase(phase)
    state, fingerprint = handoff["next_state"], handoff["resulting_branch_fingerprint"]
    forced = materialize_detached_standard_charge_forced_continuation(next_decision_state=state, next_decision_fingerprint=fingerprint)
    return state, fingerprint, forced


def test_exact_forced_continuation_is_authenticated_and_replayable():
    state, fingerprint, forced = _source()
    intents = materialize_detached_next_turn_action_intents(next_decision_state=state, next_decision_fingerprint=fingerprint, forced_continuation=forced)
    assert intents["status"] == "resolved"
    assert validate_detached_next_turn_action_intents(authority=intents, next_decision_state=state, next_decision_fingerprint=fingerprint) is None


def test_forged_forced_continuation_and_metadata_are_rejected():
    state, fingerprint, forced = _source()
    forged = deepcopy(forced)
    forged["forced_continuation_actions"]["self"]["move_id"] = "tackle"
    assert materialize_detached_next_turn_action_intents(next_decision_state=state, next_decision_fingerprint=fingerprint, forced_continuation=forged)["status"] == "rejected"
    intents = materialize_detached_next_turn_action_intents(next_decision_state=state, next_decision_fingerprint=fingerprint, forced_continuation=forced)
    forged_intents = deepcopy(intents)
    forged_intents["intents"]["self"]["canonical_move_metadata_authority"]["priority"] = 7
    assert validate_detached_next_turn_action_intents(authority=forged_intents, next_decision_state=state, next_decision_fingerprint=fingerprint) is not None
