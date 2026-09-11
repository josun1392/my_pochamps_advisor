from copy import deepcopy

from llm.advisor_detached_end_of_turn_post_action_branch_authority import materialize_detached_end_of_turn_post_action_branch_authority
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_exact_eot_post_action_lifecycle_coordinator import coordinate_exact_eot_post_action_lifecycle
from llm.advisor_exact_immediate_pair_to_eot_phase_input import materialize_exact_immediate_pair_to_eot_phase_input
from llm.advisor_post_eot_replacement_transition import advance_post_eot_entry, freeze_replacement_intent, post_eot_source_binding, prepare_post_eot_replacements
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_end_of_turn_residual_phase import _ledger, _owner
from tests.test_exact_immediate_pair_to_eot_phase_input import _authorities
from tests.test_exact_eot_post_action_lifecycle_coordinator import _teams
from tests.test_post_eot_replacement_transition import _entry, _member


def _hazards(ledger, *, self_values=("absent", 0, 0, "absent"), opponent_values=("absent", 0, 0, "absent")):
    base = {key: ledger[key] for key in ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")}
    values = {"self": self_values, "opponent": opponent_values}
    return {
        side: {"status": "resolved", "schema_version": "detached-exact-pair-terminal-switch-hazard-authority-v1",
               "source_binding": {**base, "terminal_leaf_id": "leaf", "affected_side": side}, "path_outcome": "no_hazard_change",
               "hazards": build_switch_hazard_context(session_id="s", affected_side=side, stealth_rock=row[0], spikes_layers=row[1], toxic_spikes_layers=row[2], sticky_web=row[3])}
        for side, row in values.items()
    }


def _branch(ledger=None, hazards=None):
    ledger = ledger or _ledger()
    phase = materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=_authorities(), switch_hazard_authorities=hazards or _hazards(ledger))
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    branch = materialize_detached_end_of_turn_post_action_branch_authority(eot_ledger=eot, source_eot_fingerprint=fingerprint_transition_preview_state(eot))
    return phase, eot, branch


def test_all_canonical_hazard_components_survive_exact_pair_eot_post_eot_boundary():
    ledger = _ledger()
    supplied = _hazards(ledger, self_values=("present", 3, 2, "present"), opponent_values=("present", 1, 1, "absent"))
    phase, _eot, branch = _branch(ledger, supplied)
    assert phase["switch_hazard_authorities"] == supplied
    assert branch["status"] == "known"
    assert branch["state"]["post_eot_hazard_authorities"] == {side: supplied[side]["hazards"] for side in ("self", "opponent")}


def test_terminal_side_binding_unknown_and_malformed_hazards_fail_closed():
    ledger = _ledger()
    wrong = _hazards(ledger); wrong["self"]["source_binding"]["affected_side"] = "opponent"
    assert materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=_authorities(), switch_hazard_authorities=wrong)["status"] == "rejected"
    unknown = _hazards(ledger); unknown["self"] = {"status": "unknown", "schema_version": unknown["self"]["schema_version"], "source_binding": unknown["self"]["source_binding"]}
    phase = materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=_authorities(), switch_hazard_authorities=unknown)
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert materialize_detached_end_of_turn_post_action_branch_authority(eot_ledger=eot, source_eot_fingerprint=fingerprint_transition_preview_state(eot))["status"] == "incomplete"
    malformed = _hazards(ledger); malformed["self"]["hazards"]["spikes_layers"] = 4
    assert materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=_authorities(), switch_hazard_authorities=malformed)["status"] == "rejected"


def test_forged_phase_or_post_eot_hazard_data_cannot_cross_validated_boundary():
    phase, eot, branch = _branch()
    forged_phase = deepcopy(phase); forged_phase["switch_hazard_authorities"]["self"]["source_binding"]["terminal_leaf_id"] = "foreign"
    assert materialize_end_of_turn_residual_phase(phase_input=forged_phase)["status"] == "rejected"
    forged_branch = deepcopy(branch); forged_branch["state"]["post_eot_hazard_authorities"]["self"]["spikes_layers"] = 3
    assert forged_branch["state_fingerprint"] != fingerprint_transition_preview_state(forged_branch["state"])
    assert post_eot_source_binding(eot) == branch["source_binding"]


def test_path_local_outcome_is_allowed_without_root_hazard_resurrection():
    ledger = _ledger()
    supplied = _hazards(ledger, self_values=("present", 2, 2, "present"))
    supplied["self"]["path_outcome"] = "path_local_hazard_result"
    supplied["self"]["hazards"]["toxic_spikes_layers"] = 0
    _phase, _eot, branch = _branch(ledger, supplied)
    assert branch["state"]["post_eot_hazard_authorities"]["self"]["toxic_spikes_layers"] == 0


def test_declared_hazard_mutation_without_path_local_result_is_incomplete():
    ledger = _ledger(); ledger = deepcopy(ledger)
    ledger["terminal_leaves"] = ({**ledger["terminal_leaves"][0], "first_action": {"consequences": {"switch_hazard_removal": {"status": "resolved"}}}},)
    assert materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=_authorities(), switch_hazard_authorities=_hazards(ledger))["status"] == "incomplete"


def test_transport_is_accepted_unchanged_by_existing_replacement_entry_validator():
    from tests.test_end_of_turn_residual_phase import _row
    ledger = _ledger(self_hp=6)
    authorities = _authorities(self_hp=6, self_row=_row("self", "a", 6, condition="burn"))
    phase = materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=authorities, switch_hazard_authorities=_hazards(ledger))
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    teams = _teams(eot, bench=True); teams["self"]["members"][1] = _member("self", 1)
    result = coordinate_exact_eot_post_action_lifecycle(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=authorities, team_authorities=teams, switch_hazard_authorities=_hazards(ledger))
    intent = freeze_replacement_intent(transition=result["post_eot_transition"], side="self", incoming_owner=result["post_eot_transition"]["requirements"]["self"]["candidates"][0])
    cursor = prepare_post_eot_replacements(transition=result["post_eot_transition"], intents={"self": intent})
    advanced = advance_post_eot_entry(transition=cursor, entry_authority=_entry(cursor))
    assert advanced["status"] == "entry_pending", advanced
