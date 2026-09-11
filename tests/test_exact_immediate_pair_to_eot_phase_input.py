from copy import deepcopy

from llm.advisor_detached_end_of_turn_post_action_branch_authority import (
    materialize_detached_end_of_turn_post_action_branch_authority,
)
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_exact_immediate_pair_to_eot_phase_input import (
    SCHEMA_VERSION,
    materialize_exact_immediate_pair_to_eot_phase_input,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_end_of_turn_residual_phase import _ledger, _owner, _row, _weather


def _authorities(*, self_hp=50, opponent_hp=50, self_row=None, opponent_row=None):
    rows = {"self": self_row or _row("self", "a", self_hp), "opponent": opponent_row or _row("opponent", "b", opponent_hp)}
    out = {}
    for side, row in rows.items():
        owner = row["owner"]
        out[side] = {
            "status": "resolved", "schema_version": SCHEMA_VERSION,
            "pair_id": "pair", "session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch",
            "decision_owner": _owner("self", "a"), "terminal_leaf_id": "leaf", "owner": owner,
            "maximum_hp": row["hp"]["maximum_hp"],
            **{key: deepcopy(row[key]) for key in ("condition", "item", "toxic_progression", "speed", "ability", "persistent_effects")},
            **({"types": deepcopy(row["types"])} if "types" in row else {}),
        }
    return out


def _phase(*, ledger=None, authorities=None, **kwargs):
    return materialize_exact_immediate_pair_to_eot_phase_input(
        terminal_ledger=ledger or _ledger(), terminal_leaf_id="leaf",
        terminal_active_authorities=authorities or _authorities(), **kwargs,
    )


def test_terminal_pair_hp_is_the_only_post_action_hp_source_and_eot_accepts_output():
    before = _ledger(self_hp=44, opponent_hp=33)
    phase = _phase(ledger=before, authorities=_authorities(self_hp=44, opponent_hp=33))
    assert phase["status"] == "resolved"
    assert phase["active_states"]["self"]["hp"]["current_hp"] == 44
    assert phase["active_states"]["opponent"]["fainted"]["value"] is False
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["status"] == "evaluable"
    branch = materialize_detached_end_of_turn_post_action_branch_authority(
        eot_ledger=eot, source_eot_fingerprint=fingerprint_transition_preview_state(eot),
    )
    assert branch["status"] == "known"
    assert before == _ledger(self_hp=44, opponent_hp=33)


def test_path_local_sitrus_consumption_overrides_root_item_authority():
    ledger = _ledger(opponent_hp=75)
    base = {key: ledger[key] for key in ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")}
    effect = {"status": "resolved", "outcome": "activated", **base, "holder": _owner("opponent", "b"), "source_leaf_id": "attack/1", "item_after": {"status": "known_absent", "value": None, "consumption_cause": "sitrus_berry"}}
    ledger = deepcopy(ledger)
    ledger["terminal_leaves"] = ({**ledger["terminal_leaves"][0], "first_action": {"leaf_id": "attack/1", "provenance": base, "consequences": {"sitrus_berry_immediate_consumption": effect}}},)
    opponent = _row("opponent", "b", 75, item="sitrus-berry")
    phase = _phase(ledger=ledger, authorities=_authorities(opponent_hp=75, opponent_row=opponent))
    assert phase["status"] == "resolved"
    assert phase["active_states"]["opponent"]["item"]["status"] == "known_absent"
    assert phase["active_states"]["opponent"]["item"]["source_terminal_leaf_id"] == "leaf"


def test_path_local_condition_application_overrides_root_condition_authority():
    ledger = deepcopy(_ledger()); base = {key: ledger[key] for key in ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")}
    ledger["terminal_leaves"] = ({**ledger["terminal_leaves"][0], "first_action": {
        "leaf_id": "attack/1", "provenance": {**base, "target": _owner("opponent", "b")},
        "consequences": {"secondary": {"branch": "effect", "hypothetical_target_condition": {"resulting_condition": "paralysis"}}},
    }},)
    phase = _phase(ledger=ledger)
    assert phase["status"] == "resolved"
    condition = phase["active_states"]["opponent"]["condition"]
    assert condition["status"] == "known_present" and condition["condition"] == "paralysis"


def test_weather_persistent_speed_and_leech_seed_authorities_preserve_their_exact_bindings():
    self_row = _row("self", "a", 50, speed=90, persistent={"aqua_ring": "known_active", "ingrain": "known_inactive"})
    foe_row = _row("opponent", "b", 50, speed=120, persistent={"aqua_ring": "known_inactive", "ingrain": "known_active"})
    phase = _phase(authorities=_authorities(self_row=self_row, opponent_row=foe_row), weather_authority=_weather("rain"))
    assert phase["status"] == "resolved"
    assert phase["active_states"]["self"]["persistent_effects"]["aqua_ring"]["status"] == "known_active"
    assert phase["weather_authority"]["weather"] == "rain"
    result = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert [event["event_kind"] for event in result["events"]] == ["aqua_ring", "ingrain"]


def test_existing_leech_seed_transfer_is_forwarded_without_recomputation():
    trace = {"effect": "leech_seed", "owner": _owner("self", "a"), "recipient": _owner("opponent", "b"), "source_slot": {"session_id": "s", "side": "opponent", "slot_index": 0}, "target_pre_hp": 50, "target_post_hp": 38, "target_damage": 12, "recipient_pre_hp": 50, "recipient_post_hp": 62, "recipient_modifier": "none", "liquid_ooze": False, "attempted_recovery": 12, "recipient_outcome": "recovered", "execution_status": "executed", "provenance": "detached_branch_leech_seed_v1"}
    phase = _phase(leech_seed_transfers=(trace,))
    assert phase["status"] == "resolved" and phase["leech_seed_transfers"][0]["linked_transfer"] == trace
    assert materialize_end_of_turn_residual_phase(phase_input=phase)["events"][0]["event_kind"] == "leech_seed"


def test_foreign_leaf_owner_or_unknown_terminal_authority_fail_closed():
    unknown = _authorities(); unknown["self"]["item"] = {"status": "unknown", "source_binding": unknown["self"]["item"]["source_binding"]}
    assert _phase(authorities=unknown)["status"] == "incomplete"
    stale = _authorities(); stale["self"]["source_runtime_fingerprint"] = "foreign"
    assert _phase(authorities=stale)["status"] == "rejected"
    foreign = _authorities(); foreign["opponent"]["owner"] = _owner("opponent", "foreign")
    assert _phase(authorities=foreign)["status"] == "rejected"
    assert _phase(ledger=_ledger(), authorities=_authorities(), weather_authority={"status": "known", "weather": "rain", "source_binding": {}})["status"] == "rejected"


def test_unrepresented_item_mutation_does_not_fall_back_to_root_item():
    ledger = _ledger(); ledger = deepcopy(ledger)
    ledger["terminal_leaves"] = ({**ledger["terminal_leaves"][0], "first_action": {"leaf_id": "attack/1", "consequences": {"knock_off_item_removal": {"status": "resolved"}}}},)
    assert _phase(ledger=ledger, authorities=_authorities())["reason"] == "exact_eot_terminal_item_mutation_unrepresented"
