from copy import deepcopy
from fractions import Fraction

from llm.advisor_detached_next_turn_action_intent import materialize_detached_next_turn_action_intents
from llm.advisor_detached_next_turn_ordinary_attack_execution import _move, _secondary, execute_detached_next_turn_ordinary_attack, materialize_detached_next_turn_ordinary_attack_execution_authority
from llm.advisor_exact_immediate_pair_to_eot_phase_input import materialize_exact_immediate_pair_to_eot_phase_input
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from tests.test_next_turn_predictive_mechanics_state_transport import _predictive
from tests.test_standard_charge_lifecycle_eot_next_turn_transport import _ledger_case, _post_branch, _terminal_authorities


def _metadata(**changes):
    value = {"status": "resolved", "move_id": "tackle", "category": "physical", "power": 40, "accuracy": 100, "priority": 0, "type": "normal"}
    value.update(changes)
    return value


def test_tackle_is_a_supported_single_hit_normal_formula_descriptor():
    move = _move(_metadata(), "tackle")
    assert {key: move[key] for key in ("move_id", "power", "accuracy", "category", "type", "priority")} == {"move_id": "tackle", "power": 40, "accuracy": 100, "category": "physical", "type": "normal", "priority": 0}


def test_special_families_and_unknown_secondaries_fail_closed():
    assert _move(_metadata(min_hits=2, max_hits=2), "tackle") == "ordinary_attack_special_family_unsupported"
    assert _secondary(_move(_metadata(ailment="poison", effect_chance=30), "tackle")) == "ordinary_attack_secondary_unowned"
    assert _secondary(_move(_metadata(ailment="flinch", effect_chance=30), "tackle")) == {"kind": "flinch", "chance": 30}
    assert execute_detached_next_turn_ordinary_attack(execution_authority={"status": "resolved"})["status"] == "rejected"


def _ordinary_source():
    ledger, leaf = _ledger_case(own_move="tackle", opponent_move="tackle", order="own_first")
    terminal = _terminal_authorities(ledger, leaf)
    stages = {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0, "accuracy": 0, "evasion": 0}
    for side in ("self", "opponent"):
        terminal[side]["predictive_mechanics"] = _predictive(ledger, leaf, terminal[side], stages=stages)
    phase = materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id=leaf["pair_leaf_id"], terminal_active_authorities=terminal)
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    branch = _post_branch(eot)
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch={"status":"resolved","boundary":{"phase":"end_of_turn"},"next_state":deepcopy(branch["state"]),"resulting_branch_fingerprint":branch["state_fingerprint"]})
    return handoff["next_state"], handoff["resulting_branch_fingerprint"], handoff["next_turn_predictive_mechanics_authority"]


def _chain(side):
    state, fingerprint, predictive = _ordinary_source()
    other = "opponent" if side == "self" else "self"
    metadata = _metadata()
    actions = {name: {"actor": predictive["active_owners"][name], "target": predictive["active_owners"]["opponent" if name == "self" else "self"], "action_id": f"{name}-tackle", "move_id": "tackle", "canonical_move_metadata_authority": metadata} for name in ("self", "opponent")}
    intents = materialize_detached_next_turn_action_intents(next_decision_state=state, next_decision_fingerprint=fingerprint, hypothetical_actions=actions)
    authority = materialize_detached_next_turn_ordinary_attack_execution_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, action_intents=intents, side=side)
    return state, fingerprint, intents, authority


def test_authenticated_self_and_opponent_tackle_execute_exact_single_action_ledgers():
    for side in ("self", "opponent"):
        _state, _fingerprint, intents, authority = _chain(side)
        assert intents["status"] == authority["status"] == "resolved"
        assert authority["action"]["actor"] == intents["intents"][side]["actor"]
        assert authority["action"]["target"] == intents["intents"][side]["target"]
        assert authority["action"]["continuation_action_id"] == f"{side}-tackle"
        result = execute_detached_next_turn_ordinary_attack(execution_authority=authority)
        ledger = result["action_ledger"]
        assert result["status"] == ledger["status"] == "resolved"
        assert ledger["hit_probability"] == {"numerator": 1, "denominator": 1}
        assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        leaves = ledger["terminal_leaves"]
        assert {leaf["critical_state"] for leaf in leaves} == {"critical", "non_critical"}
        assert all({"own_final_hp", "target_final_hp", "target_ko", "self_fainted"} <= set(leaf["consequences"]) for leaf in leaves)
        assert sum((Fraction(leaf["probability"]["numerator"], leaf["probability"]["denominator"]) for leaf in leaves), Fraction()) == Fraction(1)


def test_ordinary_execution_rejects_stale_and_post_materialization_move_tampering():
    state, fingerprint, _intents, authority = _chain("self")
    forged = deepcopy(authority); forged["action"]["move_id"] = "thunderbolt"
    assert execute_detached_next_turn_ordinary_attack(execution_authority=forged)["status"] == "rejected"
    assert materialize_detached_next_turn_ordinary_attack_execution_authority(next_decision_state=state, next_decision_fingerprint="stale", predictive_mechanics=authority["predictive_mechanics"], action_intents=authority["action_intents"], side="self")["status"] == "rejected"
