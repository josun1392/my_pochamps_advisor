from copy import deepcopy

from llm.advisor_detached_end_of_turn_post_action_branch_authority import (
    materialize_detached_end_of_turn_post_action_branch_authority,
)
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_post_eot_replacement_transition import freeze_post_eot_transition, post_eot_source_binding
from llm.advisor_transition_preview import fingerprint_transition_preview_state as fp
from tests.test_end_of_turn_residual_phase import _input, _row
from tests.test_post_eot_replacement_transition import _source


def _ledger(*, self_hp=50, opponent_hp=50, self_row=None, opponent_row=None, weather=None):
    return materialize_end_of_turn_residual_phase(
        phase_input=_input(
            self_hp=self_hp, opponent_hp=opponent_hp, self_row=self_row,
            opponent_row=opponent_row, weather_authority=weather,
        )
    )


def _branch(ledger):
    return materialize_detached_end_of_turn_post_action_branch_authority(
        eot_ledger=ledger, source_eot_fingerprint=fp(ledger),
    )


def test_surviving_eot_projects_exact_state_and_existing_post_eot_consumer_accepts_it():
    source = _source(self_hp=50, opponent_hp=50)
    branch = _branch(source["eot_ledger"])
    assert branch["status"] == "known"
    assert branch["source_binding"] == post_eot_source_binding(source["eot_ledger"])
    assert branch["state"]["active"]["self"]["current_hp"] == 50
    assert branch["state"]["active"]["opponent"]["fainted"] is False
    result = freeze_post_eot_transition(
        eot_ledger=source["eot_ledger"], source_eot_fingerprint=fp(source["eot_ledger"]),
        branch_authority=branch, team_authorities=source["team_authorities"],
    )
    assert result["status"] == "next_decision_ready"


def test_residual_ko_keeps_exact_post_eot_zero_hp_for_replacement_consumer():
    row = _row("self", "a", 6, condition="burn")
    ledger = _ledger(self_hp=6, self_row=row)
    assert ledger["post_end_of_turn_active_states"]["self"]["current_hp"] == 0
    branch = _branch(ledger)
    assert branch["status"] == "known"
    assert branch["state"]["active"]["self"]["current_hp"] == 0
    assert branch["state"]["active"]["self"]["fainted"] is True
    source = _source(self_hp=0, opponent_hp=50)
    binding = post_eot_source_binding(ledger)
    for team in source["team_authorities"].values():
        team["source_binding"] = binding
    result = freeze_post_eot_transition(
        eot_ledger=ledger, source_eot_fingerprint=fp(ledger),
        branch_authority=branch, team_authorities=source["team_authorities"],
    )
    assert result["status"] == "replacement_required"


def test_post_eot_projection_uses_residual_hp_not_stale_pre_eot_hp_and_preserves_item():
    row = _row("self", "a", 50, item="leftovers")
    ledger = _ledger(self_hp=50, self_row=row)
    branch = _branch(ledger)
    assert branch["state"]["active"]["self"]["current_hp"] == 56
    item = branch["state"]["post_eot_active_item_authorities"]["self"]
    assert item["authority"]["status"] == "known" and item["authority"]["value"] == "leftovers"


def test_two_owner_and_known_weather_bindings_are_preserved_without_owner_swapping():
    self_row = _row("self", "a", 50)
    foe_row = _row("opponent", "b", 50)
    weather = {"status": "known", "weather": "rain", "source_binding": {"session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch"}}
    ledger = _ledger(self_row=self_row, opponent_row=foe_row, weather=weather)
    branch = _branch(ledger)
    assert [branch["state"]["active"][side]["side"] for side in ("self", "opponent")] == ["self", "opponent"]
    assert branch["state"]["current_state"]["field_state_context"]["current_field"]["weather"] == "rain"


def test_forged_or_foreign_eot_provenance_fails_closed_and_source_is_immutable():
    ledger = _ledger()
    before = deepcopy(ledger)
    assert materialize_detached_end_of_turn_post_action_branch_authority(
        eot_ledger=ledger, source_eot_fingerprint="foreign",
    )["reason"] == "stale_or_foreign_end_of_turn_ledger"
    forged = deepcopy(ledger)
    forged["post_end_of_turn_active_states"]["self"]["current_hp"] = 51
    assert _branch(forged)["status"] == "rejected"
    foreign_leaf = deepcopy(ledger)
    foreign_leaf["terminal_leaf_id"] = "foreign"
    assert _branch(foreign_leaf)["status"] == "rejected"
    assert ledger == before


def test_unknown_or_inconsistent_post_eot_facts_fail_closed():
    ledger = _ledger()
    unknown = deepcopy(ledger)
    unknown["phase_input"]["active_states"]["self"]["item"] = {"status": "unknown"}
    assert _branch(unknown)["status"] == "rejected"
    inconsistent = deepcopy(ledger)
    inconsistent["post_end_of_turn_active_states"]["self"]["fainted"] = True
    assert _branch(inconsistent)["status"] == "rejected"
