from fractions import Fraction

from llm.advisor_detached_next_turn_action_intent import materialize_detached_next_turn_action_intents
from llm.advisor_detached_next_turn_action_order_authority import materialize_detached_next_turn_action_order_authority
from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation
from llm.advisor_detached_standard_charge_turn_two_attack_execution import materialize_detached_standard_charge_turn_two_execution_authority, execute_detached_standard_charge_turn_two_attacks
from llm.advisor_detached_next_turn_pair_local_predictive_mechanics import materialize_detached_next_turn_pair_local_predictive_mechanics
from llm.advisor_standard_charge_turn_two_ordered_pair_secondary_interactions import _second_terminal
from tests.test_detached_next_turn_action_order_temporal_state import _production_temporal_handoff


def _execution_inputs(*, own_move="sky-attack", opponent_move="ice-burn", opponent_ability=None, opponent_grounded=None, self_final_stats=None, opponent_final_stats=None):
    handoff = _production_temporal_handoff(own_move=own_move, opponent_move=opponent_move, opponent_ability=opponent_ability, opponent_grounded=opponent_grounded, self_final_stats=self_final_stats, opponent_final_stats=opponent_final_stats)
    state, fp = handoff["next_state"], handoff["resulting_branch_fingerprint"]
    predictive = handoff["next_turn_predictive_mechanics_authority"]
    forced = materialize_detached_standard_charge_forced_continuation(next_decision_state=state, next_decision_fingerprint=fp)
    intents = materialize_detached_next_turn_action_intents(next_decision_state=state, next_decision_fingerprint=fp, forced_continuation=forced)
    order = materialize_detached_next_turn_action_order_authority(next_decision_state=state, next_decision_fingerprint=fp, predictive_mechanics=predictive, action_intents=intents, action_order_temporal_state_authority=handoff["next_turn_action_order_temporal_state_authority"])
    authority = materialize_detached_standard_charge_turn_two_execution_authority(next_decision_state=state, next_decision_fingerprint=fp, forced_continuation=forced, predictive_mechanics=predictive)
    return state, fp, order, authority


def _selected_pair_secondary(*, secondary, **kwargs):
    state, fp, _order, authority = _execution_inputs(**kwargs)
    first_result = execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    first_ledger = first_result["actions"]["self"]
    first_leaf = next(
        leaf for leaf in first_ledger["terminal_leaves"]
        if f"secondary:{secondary}" in leaf["branch_path"]
    )
    overlay = materialize_detached_next_turn_pair_local_predictive_mechanics(
        next_decision_state=state,
        next_decision_fingerprint=fp,
        predictive_mechanics=authority["predictive_mechanics"],
        first_action_execution=authority,
        first_action_ledger=first_result,
        first_leaf_id=first_leaf["leaf_id"],
    )
    assert overlay["status"] == "resolved", overlay
    second = {"side": "opponent", "family": "standard_charge", "execution_authority": authority}
    return overlay, _second_terminal(second, overlay, "self", "opponent")


def test_sky_attack_first_action_flinch_cancels_the_second_action():
    overlay, second = _selected_pair_secondary(secondary="flinch")
    assert overlay["pending_action_flinch"]["status"] == "known_flinched"
    assert second == ({"leaf_id": "second_action:cancelled_due_to_flinch", "state": "cancelled_due_to_flinch", "reason": "second_action_cancelled_due_to_flinch", "probability": {"numerator": 1, "denominator": 1}, "leaf": None},)


def test_freeze_shock_first_action_paralysis_has_exact_second_action_mass():
    overlay, second = _selected_pair_secondary(secondary="paralysis", own_move="freeze-shock", opponent_move="sky-attack", opponent_grounded=False)
    assert overlay["sides"]["opponent"]["condition"] == {"status": "known_present", "condition": "paralysis"}
    cancelled = [row for row in second if row["state"] == "cancelled_due_to_paralysis"]
    executed = [row for row in second if row["state"] == "executed"]
    assert len(cancelled) == 1 and cancelled[0]["leaf"]["probability"] == {"numerator": 1, "denominator": 8}
    assert executed
    assert sum((Fraction(row["probability"]["numerator"], row["probability"]["denominator"]) for row in executed), Fraction()) == Fraction(7, 8)


def test_ice_burn_first_action_burn_reaches_second_physical_guts_execution():
    own_stats = {"hp": 100, "attack": 120, "defense": 1000, "special-attack": 1, "special-defense": 105, "speed": 100}
    opponent_stats = {"hp": 100, "attack": 120, "defense": 110, "special-attack": 130, "special-defense": 10000, "speed": 100}
    overlay, second = _selected_pair_secondary(secondary="burn", own_move="ice-burn", opponent_move="sky-attack", opponent_ability="guts", self_final_stats=own_stats, opponent_final_stats=opponent_stats)
    assert overlay["sides"]["opponent"]["condition"] == {"status": "known_present", "condition": "burn"}
    assert overlay["sides"]["opponent"]["ability"] == {"status": "known", "value": "guts"}
    assert any(row["state"] == "executed" and row["leaf"]["consequences"].get("damage") == 39 for row in second)
