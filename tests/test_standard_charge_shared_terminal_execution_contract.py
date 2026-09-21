from copy import deepcopy
from fractions import Fraction

import pytest

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation
from llm.advisor_detached_standard_charge_turn_two_attack_execution import (
    execute_detached_standard_charge_turn_two_attacks,
    materialize_detached_standard_charge_turn_two_execution_authority,
    materialize_detached_standard_charge_turn_two_terminal_execution_contract,
    validate_detached_standard_charge_turn_two_terminal_execution_contract,
)
from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import (
    freeze_runtime_d0_standard_charge_terminal_mechanics_authority,
)
from llm.advisor_standard_charge_terminal_execution import (
    FORCED_TURN_TWO_EXECUTION_MODE,
    POWER_HERB_CURRENT_TURN_SKIP_MODE,
    execute_standard_charge_terminal_attack,
    materialize_standard_charge_terminal_execution_contract,
    validate_standard_charge_terminal_execution_contract,
    validate_standard_charge_terminal_mechanics_shape,
)
from tests.test_detached_next_turn_action_order_temporal_state import _production_temporal_handoff
from tests.test_runtime_d0_standard_charge_terminal_mechanics_authority import _ready
from tests.test_detached_intermediate_predictive_authority import _owner
from tests.test_standard_charge_turn_two_pair_secondary_interactions import _execution_inputs
from llm.advisor_detached_next_turn_pair_local_predictive_mechanics import materialize_detached_next_turn_pair_local_predictive_mechanics


def _forced_case(*, own_move="sky-attack", opponent_move="ice-burn", self_final_stats=None, opponent_final_stats=None):
    handoff = _production_temporal_handoff(
        own_move=own_move,
        opponent_move=opponent_move,
        self_final_stats=self_final_stats,
        opponent_final_stats=opponent_final_stats,
    )
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    predictive = handoff["next_turn_predictive_mechanics_authority"]
    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
    )
    authority = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        forced_continuation=forced,
        predictive_mechanics=predictive,
    )
    assert authority["status"] == "resolved", authority
    contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=authority,
        side="self",
    )
    return state, fingerprint, authority, contract


@pytest.mark.parametrize("move_id", ("sky-attack", "razor-wind", "freeze-shock", "ice-burn"))
def test_forced_turn_two_materializes_valid_shared_contract_and_normalized_kernel(move_id):
    _state, fingerprint, authority, contract = _forced_case(
        own_move=move_id,
        opponent_move="razor-wind" if move_id != "razor-wind" else "ice-burn",
    )
    assert contract["status"] == "resolved", contract
    assert contract["execution_mode"] == FORCED_TURN_TWO_EXECUTION_MODE
    assert contract["source_state_fingerprint"] == fingerprint
    assert contract["move_id"] == move_id
    assert contract["canonical_terminal_effect"] == resolve_canonical_standard_charge_turn_two_effect(move_id)
    assert validate_standard_charge_terminal_execution_contract(contract) is None
    assert validate_detached_standard_charge_turn_two_terminal_execution_contract(
        contract=contract,
        execution_authority=authority,
        side="self",
    ) is None

    kernel = execute_standard_charge_terminal_attack(execution_contract=contract)
    assert kernel["status"] == "resolved", kernel
    assert kernel["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert sum(
        (
            Fraction(leaf["probability"]["numerator"], leaf["probability"]["denominator"])
            for leaf in kernel["terminal_leaves"]
        ),
        Fraction(),
    ) == Fraction(1, 1)

    public = execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    legacy = public["actions"]["self"]
    normalized_kernel = deepcopy(kernel)
    normalized_kernel["schema_version"] = legacy["schema_version"]
    normalized_kernel["provenance"] = legacy["provenance"]
    assert normalized_kernel == legacy


@pytest.mark.parametrize("move_id", ("sky-attack", "razor-wind"))
def test_high_critical_charge_moves_keep_nonzero_critical_branch(move_id):
    _state, _fingerprint, _authority, contract = _forced_case(
        own_move=move_id,
        opponent_move="ice-burn",
    )
    kernel = execute_standard_charge_terminal_attack(execution_contract=contract)
    crit = Fraction(kernel["critical_probability"]["numerator"], kernel["critical_probability"]["denominator"])
    assert crit > Fraction(1, 24)
    assert any(leaf["critical_state"] == "critical" for leaf in kernel["terminal_leaves"])


@pytest.mark.parametrize(
    ("move_id", "secondary_token"),
    (
        ("sky-attack", "secondary:flinch"),
        ("freeze-shock", "secondary:paralysis"),
        ("ice-burn", "secondary:burn"),
    ),
)
def test_shared_kernel_preserves_charge_secondaries(move_id, secondary_token):
    kwargs = {}
    if move_id == "ice-burn":
        kwargs = {
            "self_final_stats": {"hp": 100, "attack": 120, "defense": 1000, "special-attack": 1, "special-defense": 105, "speed": 100},
            "opponent_final_stats": {"hp": 100, "attack": 120, "defense": 110, "special-attack": 130, "special-defense": 10000, "speed": 100},
        }
    _state, _fingerprint, _authority, contract = _forced_case(
        own_move=move_id,
        opponent_move="razor-wind",
        **kwargs,
    )
    kernel = execute_standard_charge_terminal_attack(execution_contract=contract)
    assert any(secondary_token in leaf["branch_path"] for leaf in kernel["terminal_leaves"])


def _recontract(contract, *, actor_mechanics=None, execution_mode=FORCED_TURN_TWO_EXECUTION_MODE):
    actor_mechanics = deepcopy(actor_mechanics if actor_mechanics is not None else contract["actor_mechanics"])
    auth = deepcopy(contract["caller_authentication"])
    auth["execution_mode"] = execution_mode
    auth["actor_mechanics"] = deepcopy(actor_mechanics)
    return materialize_standard_charge_terminal_execution_contract(
        execution_mode=execution_mode,
        source_state_fingerprint=contract["source_state_fingerprint"],
        decision_owner=contract["decision_owner"],
        actor=contract["actor"],
        target=contract["target"],
        action_id=contract["action_id"],
        move_id=contract["move_id"],
        canonical_terminal_effect=contract["canonical_terminal_effect"],
        actor_mechanics=actor_mechanics,
        target_mechanics=contract["target_mechanics"],
        attacker_held_item_effect_authority=contract["attacker_held_item_effect_authority"],
        target_held_item_effect_authority=contract["target_held_item_effect_authority"],
        target_sturdy_authority=contract["target_sturdy_authority"],
        target_focus_sash_authority=contract["target_focus_sash_authority"],
        attacker_life_orb_authority=contract["attacker_life_orb_authority"],
        caller_action_authority=contract["caller_action_authority"],
        caller_authentication=auth,
    )


def test_shared_kernel_preserves_fainted_and_paralysis_pre_action_gates():
    _state, _fingerprint, _authority, base = _forced_case()

    fainted = deepcopy(base["actor_mechanics"])
    fainted["current_hp"]["current_hp"] = 0
    fainted["fainted"] = True
    fainted["direct_mechanics"]["combatant"]["current_hp"] = 0
    fainted_contract = _recontract(base, actor_mechanics=fainted)
    cancelled = execute_standard_charge_terminal_attack(execution_contract=fainted_contract)
    assert cancelled["status"] == "resolved"
    assert cancelled["pre_action_gate"] == {"status": "resolved", "outcome": "cancelled", "reason": "fainted_actor"}
    assert cancelled["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}

    paralyzed = deepcopy(base["actor_mechanics"])
    paralyzed["condition"] = {"status": "known_present", "condition": "paralysis"}
    paralyzed["direct_mechanics"]["combatant"]["status"] = "paralysis"
    paralysis_contract = _recontract(base, actor_mechanics=paralyzed)
    result = execute_standard_charge_terminal_attack(execution_contract=paralysis_contract)
    assert result["status"] == "resolved"
    branches = result["pre_action_gate"]["branches"]
    assert any(row["kind"] == "cancelled_due_to_paralysis" and row["probability"] == {"numerator": 1, "denominator": 8} for row in branches)
    assert any(row["kind"] == "executes_after_paralysis" and row["probability"] == {"numerator": 7, "denominator": 8} for row in branches)
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_power_herb_execution_mode_cannot_be_forged_from_turn_two_caller():
    _state, _fingerprint, _authority, contract = _forced_case()
    rejected = _recontract(contract, execution_mode=POWER_HERB_CURRENT_TURN_SKIP_MODE)
    assert rejected["status"] == "rejected"
    assert rejected["reason"] in {
        "standard_charge_terminal_power_herb_consumption_authority_required",
        "standard_charge_terminal_caller_authentication_mismatch",
    }


def test_execution_mode_and_nested_contract_tampering_reject():
    _state, _fingerprint, _authority, contract = _forced_case()
    forged_mode = deepcopy(contract)
    forged_mode["execution_mode"] = POWER_HERB_CURRENT_TURN_SKIP_MODE
    assert validate_standard_charge_terminal_execution_contract(forged_mode) is not None
    assert execute_standard_charge_terminal_attack(execution_contract=forged_mode)["status"] == "rejected"

    for key in (
        "session_id",
        "source_state_fingerprint",
        "decision_owner",
        "actor",
        "target",
        "action_id",
        "move_id",
        "canonical_terminal_effect",
        "actor_mechanics",
        "target_mechanics",
        "attacker_held_item_effect_authority",
        "target_held_item_effect_authority",
        "target_sturdy_authority",
        "target_focus_sash_authority",
        "attacker_life_orb_authority",
        "caller_authentication",
    ):
        tampered = deepcopy(contract)
        tampered[key] = {"tampered": True}
        assert validate_standard_charge_terminal_execution_contract(tampered) is not None, key
        assert validate_detached_standard_charge_turn_two_terminal_execution_contract(
            contract=tampered,
            execution_authority=_authority,
            side="self",
        ) is not None, key
        assert execute_standard_charge_terminal_attack(execution_contract=tampered)["status"] == "rejected", key



def test_turn_two_adapter_honors_pair_local_mechanics_and_rejects_tampering():
    state, fingerprint, _order, authority = _execution_inputs(
        own_move="sky-attack",
        opponent_move="ice-burn",
    )
    first = execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    first_ledger = first["actions"]["self"]
    source_leaf = next(leaf for leaf in first_ledger["terminal_leaves"] if leaf["hit_state"] == "hit")
    overlay = materialize_detached_next_turn_pair_local_predictive_mechanics(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        predictive_mechanics=authority["predictive_mechanics"],
        first_action_execution=authority,
        first_action_ledger=first,
        first_leaf_id=source_leaf["leaf_id"],
    )
    assert overlay["status"] == "resolved", overlay

    contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=authority,
        side="opponent",
        pair_local_predictive_mechanics=overlay,
    )
    assert contract["status"] == "resolved", contract
    assert contract["actor_mechanics"] == overlay["sides"]["opponent"]
    assert contract["target_mechanics"] == overlay["sides"]["self"]

    forged = deepcopy(overlay)
    forged["sides"]["opponent"]["current_hp"]["current_hp"] = 1
    rejected = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=authority,
        side="opponent",
        pair_local_predictive_mechanics=forged,
    )
    assert rejected["status"] == "incomplete"
    assert rejected["reason"] == "pair_local_predictive_mechanics_invalid"


def test_shared_kernel_cancellation_paths_preserve_caller_action_provenance():
    _state, _fingerprint, _authority, contract = _forced_case()

    fainted = deepcopy(contract)
    fainted["actor_mechanics"]["current_hp"]["current_hp"] = 0
    fainted["actor_mechanics"]["fainted"] = True
    fainted["caller_authentication"]["actor_mechanics"] = deepcopy(fainted["actor_mechanics"])
    cancelled = execute_standard_charge_terminal_attack(execution_contract=fainted)
    assert cancelled["status"] == "resolved"
    assert cancelled["pre_action_gate"]["reason"] == "fainted_actor"
    assert cancelled["execution_authority"] == contract["caller_action_authority"]
    assert cancelled["terminal_leaves"][0]["provenance"]["execution_authority"] == contract["caller_action_authority"]

    paralyzed = deepcopy(contract)
    paralyzed["actor_mechanics"]["condition"] = {"status": "known_present", "condition": "paralysis"}
    paralyzed["caller_authentication"]["actor_mechanics"] = deepcopy(paralyzed["actor_mechanics"])
    branched = execute_standard_charge_terminal_attack(execution_contract=paralyzed)
    assert branched["status"] == "resolved"
    cancelled_leaves = [
        leaf for leaf in branched["terminal_leaves"]
        if leaf["consequences"].get("execution_failure") == "cancelled_due_to_paralysis"
    ]
    assert cancelled_leaves
    assert all(
        leaf["provenance"]["execution_authority"] == contract["caller_action_authority"]
        for leaf in cancelled_leaves
    )


def test_current_d0_mechanics_are_shape_compatible_but_remain_non_executable():
    state, snapshot, d0 = _ready()
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_type": "attack", "action_id": "a:sky-attack", "identity": "sky-attack"}
    bundle = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata={"move_id": "sky-attack"},
    )
    assert bundle["status"] == "resolved", bundle
    assert bundle["mechanics_only"] is True
    assert bundle["execution_grant"] is False
    assert validate_standard_charge_terminal_mechanics_shape(
        actor_mechanics=bundle["actor_participant_mechanics_authority"],
        target_mechanics=bundle["target_participant_mechanics_authority"],
        canonical_terminal_effect=bundle["canonical_terminal_effect"],
    ) is None
    assert execute_standard_charge_terminal_attack(execution_contract=bundle)["status"] == "rejected"
