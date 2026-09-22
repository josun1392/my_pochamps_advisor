"""Production-shaped transport for trusted inactive next-turn order facts."""
from copy import deepcopy

from llm.advisor_detached_end_of_turn_post_action_branch_authority import materialize_detached_end_of_turn_post_action_branch_authority
from llm.advisor_detached_next_turn_action_intent import materialize_detached_next_turn_action_intents
from llm.advisor_detached_next_turn_action_order_authority import materialize_detached_next_turn_action_order_authority
from llm.advisor_detached_next_turn_action_order_temporal_state import freeze_detached_action_order_temporal_source_authority
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_exact_immediate_pair_to_eot_phase_input import materialize_exact_immediate_pair_to_eot_phase_input
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_identity_groundedness import build_groundedness
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_runtime_d0_action_order_authority import freeze_runtime_d0_action_order_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_next_turn_predictive_mechanics_state_transport import _predictive, STAGES
from llm.advisor_next_turn_predictive_mechanics_authority import _terminal_stage_expectations
from tests.test_standard_charge_lifecycle_eot_next_turn_transport import _terminal_authorities
from tests.test_standard_charge_start_immediate_pair_integration import _opponent_action, _own_action
from tests.test_standard_charge_turn_two_ordered_pair_core import _runtime_fixture


def _production_temporal_handoff(*, own_move="sky-attack", opponent_move="ice-burn", opponent_ability=None, opponent_grounded=None, self_final_stats=None, opponent_final_stats=None, weather=None, self_item=None):
    """Confirmation/reducer → D0 pair → EOT → handoff, with optional exact weather."""
    snapshot, d0, _old_own, _old_opponent, _old_order, _charge = _runtime_fixture()
    if own_move in {"fly", "dig", "dive", "bounce", "phantom-force", "shadow-force"}:
        state = snapshot["state"]
        if own_move in {"fly", "bounce"}:
            state["field"]["gravity_status"] = "inactive"
            state["field"]["gravity_status_provenance"] = {"event_kind": "gravity_field_observed", "trust": "user_confirmed_observation", "source": "ui_gravity_field_confirmation", "turn_number": 1, "source_observation_id": "temporal-gravity", "source_sequence": 1}
        opponent = state["opponent_side"]["pokemon"][0]
        opponent["locked_on_state"] = {"status": "known_inactive"}
        opponent["locked_on_state_provenance"] = {"event_kind": "current_locked_on_state_observed", "trust": "user_confirmed_observation", "source": "ui_current_locked_on_state_confirmation", "turn_number": 1, "source_observation_id": "temporal-locked-on", "source_sequence": 2}
        snapshot["state_fingerprint"] = state_fingerprint(state)
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["active_owners"]["self"])
    if weather is not None:
        state = snapshot["state"]
        state["field"]["weather"] = weather
        state["field"]["weather_provenance"] = {
            "event_kind": "current_weather_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
        }
        snapshot["state_fingerprint"] = state_fingerprint(state)
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["active_owners"]["self"])
    if self_item is not None:
        state = snapshot["state"]
        state["self_side"]["pokemon"][0]["known_item"] = self_item
        state["self_side"]["pokemon"][0]["known_item_provenance"] = {
            "event_kind": "current_item_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "status": "known",
        }
        state["field"]["magic_room_status"] = "inactive"
        state["field"]["magic_room_status_provenance"] = {
            "event_kind": "magic_room_field_observed",
            "trust": "user_confirmed_observation",
            "source_observation_id": "temporal-self-item-magic-room",
            "source_sequence": 1,
        }
        snapshot["state_fingerprint"] = state_fingerprint(state)
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["active_owners"]["self"])
    if opponent_grounded is not None:
        state = snapshot["state"]
        opponent_owner = d0["active_owners"]["opponent"]
        state["identity_groundedness_context"] = build_groundedness(
            session_id=state["session_id"],
            side="opponent",
            slot_index=opponent_owner["slot_index"],
            pokemon_id=opponent_owner["pokemon_id"],
            status="grounded" if opponent_grounded else "ungrounded",
        )
        snapshot["state_fingerprint"] = state_fingerprint(state)
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["active_owners"]["self"])
    if opponent_ability is not None:
        state = snapshot["state"]
        state["opponent_side"]["pokemon"][0]["current_ability"] = opponent_ability
        snapshot["state_fingerprint"] = state_fingerprint(state)
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["active_owners"]["self"])
    own = _own_action(d0, d0["active_owners"]["self"], own_move)
    opponent = _opponent_action(d0, opponent_move)
    order = freeze_runtime_d0_action_order_authority(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent)
    assert order["status"] == "resolved", order
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=order)
    assert pair["status"] == "evaluable", pair
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger
    source = freeze_detached_action_order_temporal_source_authority(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=order, evaluated_pair=ledger, source_move_ids={"self": own_move, "opponent": opponent_move})
    assert source["status"] == "resolved", source
    leaf = ledger["terminal_leaves"][0]
    terminal = _terminal_authorities(
        ledger, leaf,
        abilities={"opponent": opponent_ability} if opponent_ability is not None else None,
    )
    self_stages = deepcopy(STAGES)
    self_stages.update(_terminal_stage_expectations(leaf, terminal["self"]["owner"]))
    if self_item is not None:
        terminal["self"]["item"] = {**deepcopy(terminal["self"]["item"]), "status": "known", "value": self_item}
    terminal["self"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["self"], final_stats=self_final_stats, stages=self_stages,
        item={"status": "known", "value": self_item} if self_item is not None else None,
    )
    terminal["opponent"]["predictive_mechanics"] = _predictive(
        ledger, leaf, terminal["opponent"], final_stats=opponent_final_stats,
        ability={"status": "known", "value": opponent_ability or "pressure"},
    )
    if opponent_grounded is not None:
        terminal["opponent"]["predictive_mechanics"]["direct_mechanics"]["combatant"]["grounded"] = opponent_grounded
    phase = materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=ledger, terminal_leaf_id=leaf["pair_leaf_id"], terminal_active_authorities=terminal, action_order_temporal_source_authority=source)
    assert phase["status"] == "resolved", (phase.get("status"), phase.get("reason"))
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    assert eot["status"] == "evaluable", eot
    branch = materialize_detached_end_of_turn_post_action_branch_authority(eot_ledger=eot, source_eot_fingerprint=fingerprint_transition_preview_state(eot))
    assert branch["status"] == "known", branch
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch={"status": "resolved", "boundary": {"phase": "end_of_turn"}, "next_state": deepcopy(branch["state"]), "resulting_branch_fingerprint": branch["state_fingerprint"]})
    assert handoff["status"] == "resolved", handoff
    return handoff


def test_trusted_inactive_order_facts_cross_the_real_pair_eot_handoff_path():
    handoff = _production_temporal_handoff()
    temporal = handoff["next_turn_action_order_temporal_state_authority"]
    assert {key: row["state"] for key, row in temporal["temporal_facts"].items()} == {"self_tailwind": "inactive", "opponent_tailwind": "inactive", "trick_room": "inactive"}
    state, fingerprint = handoff["next_state"], handoff["resulting_branch_fingerprint"]
    predictive = handoff["next_turn_predictive_mechanics_authority"]
    intents = materialize_detached_next_turn_action_intents(next_decision_state=state, next_decision_fingerprint=fingerprint)
    order = materialize_detached_next_turn_action_order_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, action_intents=intents, action_order_temporal_state_authority=temporal)
    assert order["status"] == "resolved", order
    assert order["order_input_authority"]["self_tailwind"] == order["order_input_authority"]["opponent_tailwind"] == order["order_input_authority"]["trick_room"] == "inactive"
