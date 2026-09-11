from copy import deepcopy

from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_exact_eot_post_action_lifecycle_coordinator import coordinate_exact_eot_post_action_lifecycle
from llm.advisor_exact_immediate_pair_to_eot_phase_input import materialize_exact_immediate_pair_to_eot_phase_input
from llm.advisor_exact_pair_native_two_turn_lifecycle_execution import execute_exact_pair_native_two_turn_lifecycle
from llm.advisor_post_eot_replacement_transition import advance_post_eot_entry, freeze_replacement_intent, prepare_post_eot_replacements
from tests.test_end_of_turn_residual_phase import _ledger, _owner, _row
from tests.test_exact_eot_post_action_lifecycle_coordinator import _teams
from tests.test_exact_immediate_pair_to_eot_phase_input import _authorities
from tests.test_exact_post_eot_switch_hazard_authority_transport import _hazards
from tests.test_post_eot_replacement_transition import _entry, _member


def _eot(ledger, authorities, hazards):
    phase = materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=authorities, switch_hazard_authorities=hazards)
    return materialize_end_of_turn_residual_phase(phase_input=phase)


def _turn(ledger, authorities, teams, hazards, *, state=None, next_fingerprint=None):
    value = {"terminal_ledger": ledger, "terminal_leaf_id": "leaf", "terminal_active_authorities": authorities, "team_authorities": teams, "weather_authority": None, "leech_seed_transfers": (), "switch_hazard_authorities": hazards}
    if state is not None: value.update(next_decision_state=state, next_decision_fingerprint=next_fingerprint)
    return value


def _rebind(value, *, branch, own=None):
    original = _owner("self", "a")
    if isinstance(value, dict):
        result = {key: _rebind(item, branch=branch, own=own) for key, item in value.items()}
        if result == original and own is not None: return deepcopy(own)
        if result.get("source_branch_fingerprint") == "branch": result["source_branch_fingerprint"] = branch
        return result
    if isinstance(value, tuple): return tuple(_rebind(item, branch=branch, own=own) for item in value)
    if isinstance(value, list): return [_rebind(item, branch=branch, own=own) for item in value]
    return value


def _complete(transition):
    intents = {side: freeze_replacement_intent(transition=transition, side=side, incoming_owner=row["candidates"][0]) for side, row in transition["requirements"].items() if row["state"] == "replacement_required"}
    cursor = prepare_post_eot_replacements(transition=transition, intents=intents)
    while cursor["status"] == "entry_pending":
        cursor = advance_post_eot_entry(transition=cursor, entry_authority=_entry(cursor))
    return cursor


def test_exact_no_replacement_runs_two_coordinator_boundaries():
    first_ledger, first_authorities = _ledger(), _authorities(); first_hazards = _hazards(first_ledger)
    first = coordinate_exact_eot_post_action_lifecycle(terminal_ledger=first_ledger, terminal_leaf_id="leaf", terminal_active_authorities=first_authorities, team_authorities=_teams(_eot(first_ledger, first_authorities, first_hazards)), switch_hazard_authorities=first_hazards)
    second_ledger = _rebind(_ledger(), branch=first["next_decision_fingerprint"])
    second_authorities = _rebind(_authorities(), branch=first["next_decision_fingerprint"])
    second_hazards = _rebind(_hazards(_ledger()), branch=first["next_decision_fingerprint"])
    result = execute_exact_pair_native_two_turn_lifecycle(
        turn_one=_turn(first_ledger, first_authorities, _teams(_eot(first_ledger, first_authorities, first_hazards)), first_hazards),
        turn_two=_turn(second_ledger, second_authorities, _teams(_eot(second_ledger, second_authorities, second_hazards)), second_hazards, state=first["detached_next_decision_state"], next_fingerprint=first["next_decision_fingerprint"]),
    )
    assert result["status"] == "next_decision_ready", result
    assert result["turn_two_lifecycle"]["eot_phase_input"]["switch_hazard_authorities"] == second_hazards


def test_completed_replacement_uses_transport_hazards_and_incoming_owner_for_turn_two():
    row = _row("self", "a", 6, condition="burn")
    first_ledger, first_authorities = _ledger(self_hp=6), _authorities(self_hp=6, self_row=row); first_hazards = _hazards(first_ledger, self_values=("present", 1, 0, "absent"))
    teams = _teams(_eot(first_ledger, first_authorities, first_hazards), bench=True); teams["self"]["members"][1] = _member("self", 1)
    first = coordinate_exact_eot_post_action_lifecycle(terminal_ledger=first_ledger, terminal_leaf_id="leaf", terminal_active_authorities=first_authorities, team_authorities=teams, switch_hazard_authorities=first_hazards)
    completed = _complete(first["post_eot_transition"])
    assert completed["status"] == "next_decision_ready", completed
    incoming = {**_owner("self", "self-1"), "slot_index": 1}
    second_ledger = _rebind(_ledger(), branch=completed["next_decision_fingerprint"], own=incoming)
    second_authorities = _rebind(_authorities(), branch=completed["next_decision_fingerprint"], own=incoming)
    second_hazards = _rebind(_hazards(_ledger()), branch=completed["next_decision_fingerprint"], own=incoming)
    result = execute_exact_pair_native_two_turn_lifecycle(
        turn_one=_turn(first_ledger, first_authorities, teams, first_hazards),
        turn_two=_turn(second_ledger, second_authorities, _teams(_eot(second_ledger, second_authorities, second_hazards)), second_hazards, state=completed["detached_next_decision_state"], next_fingerprint=completed["next_decision_fingerprint"]),
        completed_replacement_transition=completed,
    )
    assert result["status"] == "next_decision_ready", result
    assert result["next_turn_boundary"]["active_owners"]["self"] == incoming


def test_battle_terminal_stops_and_stale_or_incomplete_turn_two_sources_fail_closed():
    row = _row("self", "a", 6, condition="burn")
    ledger, authorities = _ledger(self_hp=6), _authorities(self_hp=6, self_row=row); hazards = _hazards(ledger)
    terminal = execute_exact_pair_native_two_turn_lifecycle(turn_one=_turn(ledger, authorities, _teams(_eot(ledger, authorities, hazards)), hazards), turn_two=None)
    assert terminal["status"] == "battle_terminal" and "turn_two_lifecycle" not in terminal

    first_ledger, first_authorities = _ledger(), _authorities(); first_hazards = _hazards(first_ledger)
    first = coordinate_exact_eot_post_action_lifecycle(terminal_ledger=first_ledger, terminal_leaf_id="leaf", terminal_active_authorities=first_authorities, team_authorities=_teams(_eot(first_ledger, first_authorities, first_hazards)), switch_hazard_authorities=first_hazards)
    stale_ledger, stale_authorities, stale_hazards = _ledger(), _authorities(), _hazards(_ledger())
    stale = execute_exact_pair_native_two_turn_lifecycle(turn_one=_turn(first_ledger, first_authorities, _teams(_eot(first_ledger, first_authorities, first_hazards)), first_hazards), turn_two=_turn(stale_ledger, stale_authorities, _teams(_eot(stale_ledger, stale_authorities, stale_hazards)), stale_hazards, state=first["detached_next_decision_state"], next_fingerprint=first["next_decision_fingerprint"]))
    assert stale["status"] == "rejected" and stale["reason"] == "turn_two_pair_branch_binding_invalid"


def test_incomplete_or_foreign_replacement_cursor_cannot_resume():
    row = _row("self", "a", 6, condition="burn")
    ledger, authorities = _ledger(self_hp=6), _authorities(self_hp=6, self_row=row); hazards = _hazards(ledger)
    teams = _teams(_eot(ledger, authorities, hazards), bench=True)
    result = execute_exact_pair_native_two_turn_lifecycle(turn_one=_turn(ledger, authorities, teams, hazards), turn_two=None, completed_replacement_transition=coordinate_exact_eot_post_action_lifecycle(terminal_ledger=ledger, terminal_leaf_id="leaf", terminal_active_authorities=authorities, team_authorities=teams, switch_hazard_authorities=hazards)["post_eot_transition"])
    assert result["status"] == "incomplete" and result["reason"] == "replacement_completion_not_ready"
