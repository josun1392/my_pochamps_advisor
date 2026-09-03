from copy import deepcopy

from llm.advisor_damage_pivot_continuation import freeze_damage_pivot_continuation_authority
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair


def _d0():
    own = {"session_id": "pivot", "side": "self", "slot_index": 0, "pokemon_id": "lead"}
    foe = {"session_id": "pivot", "side": "opponent", "slot_index": 0, "pokemon_id": "foe"}
    return {"status": "resolved", "session_id": "pivot", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "branch", "decision_owner": own, "active_owners": {"self": own, "opponent": foe}}


def _leaf(d0, *, hit="hit", damage=20, own_hp=80, target_hp=80):
    return {"leaf_id": "u-turn:hit", "candidate_id": "attack:u-turn", "hit_state": hit, "consequences": {"damage": damage, "own_final_hp": own_hp, "target_final_hp": target_hp}, "provenance": {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "attacker": d0["decision_owner"], "target": d0["active_owners"]["opponent"], "move_id": "u-turn"}}


def _replacement(d0):
    return {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "owner": {"session_id": "pivot", "side": "self", "slot_index": 1, "pokemon_id": "bench"}}


def test_canonical_pivot_family_binds_exact_terminal_and_replacement():
    d0 = _d0()
    for move_id in ("u-turn", "volt-switch", "flip-turn"):
        leaf = _leaf(d0); leaf["candidate_id"] = f"attack:{move_id}"; leaf["provenance"]["move_id"] = move_id
        result = freeze_damage_pivot_continuation_authority(strategy_d0=d0, action={"action_id": f"attack:{move_id}"}, move_metadata={"move_id": move_id}, attack_terminal_leaf=leaf, replacement_authority=_replacement(d0))
        assert result["status"] == "applies"
        assert result["canonical_pivot_capability"] == "self_switch_after_successful_attack"
        assert result["selected_replacement_owner"]["pokemon_id"] == "bench"


def test_miss_no_effect_fainted_and_no_replacement_never_apply_pivot():
    d0 = _d0()
    action, move, replacement = {"action_id": "attack:u-turn"}, {"move_id": "u-turn"}, _replacement(d0)
    assert freeze_damage_pivot_continuation_authority(strategy_d0=d0, action=action, move_metadata=move, attack_terminal_leaf=_leaf(d0, hit="miss", damage=0), replacement_authority=replacement)["status"] == "not_applicable"
    assert freeze_damage_pivot_continuation_authority(strategy_d0=d0, action=action, move_metadata=move, attack_terminal_leaf=_leaf(d0, damage=0), replacement_authority=replacement)["status"] == "not_applicable"
    assert freeze_damage_pivot_continuation_authority(strategy_d0=d0, action=action, move_metadata=move, attack_terminal_leaf=_leaf(d0, own_hp=0), replacement_authority=replacement)["reason"] == "pivot_user_fainted_during_attack"
    assert freeze_damage_pivot_continuation_authority(strategy_d0=d0, action=action, move_metadata=move, attack_terminal_leaf=_leaf(d0), replacement_authority={**_replacement(d0), "status": "known_none"})["reason"] == "pivot_no_exact_legal_replacement"


def test_target_ko_keeps_a_successful_pivot_eligible():
    d0 = _d0()
    result = freeze_damage_pivot_continuation_authority(
        strategy_d0=d0, action={"action_id": "attack:u-turn"}, move_metadata={"move_id": "u-turn"},
        attack_terminal_leaf=_leaf(d0, target_hp=0), replacement_authority=_replacement(d0),
    )
    assert result["status"] == "applies"
    assert result["target_fainted"] is True


def test_pivot_continuation_consumes_rebound_replacement_on_the_execution_branch():
    d0 = _d0() | {"source_runtime_fingerprint": "post-runtime", "strategy_preview_fingerprint": "post-branch"}
    rebound = {
        "status": "resolved", "schema_version": "detached-pending-action-intent-rebinding-authority-v1",
        "session_id": d0["session_id"], "source_runtime_fingerprint": "post-runtime",
        "source_branch_fingerprint": "post-branch", "decision_owner": d0["decision_owner"],
        "selected_replacement_owner": _replacement(_d0())["owner"],
        "original_intent": {"action_id": "attack:u-turn", "move_id": "u-turn"},
    }
    result = freeze_damage_pivot_continuation_authority(
        strategy_d0=d0, action={"action_id": "attack:u-turn"}, move_metadata={"move_id": "u-turn"},
        attack_terminal_leaf=_leaf(d0), replacement_authority=rebound,
    )
    assert result["status"] == "applies"
    assert result["selected_replacement_owner"] == rebound["selected_replacement_owner"]


def test_forged_leaf_or_replacement_fails_closed():
    d0 = _d0(); leaf = _leaf(d0); replacement = _replacement(d0)
    forged = deepcopy(replacement); forged["owner"] = d0["active_owners"]["opponent"]
    assert freeze_damage_pivot_continuation_authority(strategy_d0=d0, action={"action_id": "attack:u-turn"}, move_metadata={"move_id": "u-turn"}, attack_terminal_leaf=leaf, replacement_authority=forged)["status"] == "incomplete"
    forged_leaf = deepcopy(leaf); forged_leaf["provenance"]["target"] = d0["decision_owner"]
    assert freeze_damage_pivot_continuation_authority(strategy_d0=d0, action={"action_id": "attack:u-turn"}, move_metadata={"move_id": "u-turn"}, attack_terminal_leaf=forged_leaf, replacement_authority=replacement)["status"] == "rejected"


def test_pivot_first_rebinds_pending_second_action_to_the_exact_incoming_owner(monkeypatch):
    """The shared pair seam must never reuse the departed pivot target."""
    d0 = _d0() | {"schema_version": "deterministic-runtime-strategy-d0-v1"}
    own, foe = d0["decision_owner"], d0["active_owners"]["opponent"]
    incoming = {"session_id": "pivot", "side": "self", "slot_index": 1, "pokemon_id": "bench"}
    own_meta = {"status": "resolved", "move_id": "u-turn", "metadata": {"move_id": "u-turn", "category": "physical", "power": 70, "type": "bug", "accuracy": 100, "priority": 0}}
    own_action = {"action_id": "attack:u-turn", "action_type": "attack", "identity": "u-turn", "move_metadata_authority": own_meta}
    opponent_action = {"status": "resolved", "action_id": "opponent_attack:tackle", "move_id": "tackle", "selectability": "selectable", "usability": {"status": "known_usable"}, "metadata_authority": {"status": "resolved", "metadata": {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}}, "session_id": "pivot", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own}
    order = {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "own_first", "session_id": "pivot", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own, "own_action_id": own_action["action_id"], "opponent_action_id": opponent_action["action_id"], "own_actor": own, "opponent_actor": foe}
    first = _leaf(d0) | {"action_type": "attack", "branch_path": ("hit",), "probability": {"numerator": 1, "denominator": 1}}
    second = deepcopy(first) | {"leaf_id": "tackle:hit", "candidate_id": "attack:tackle", "provenance": {**first["provenance"], "attacker": foe, "target": incoming, "move_id": "tackle"}}
    intermediate = {"status": "resolved", "active": {"self": {"hypothetical_fainted": {"value": False}}, "opponent": {"hypothetical_fainted": {"value": False}}}, "second_action_compatibility": {"flinch_cancellation": {"status": "resolved", "affected_owner": foe, "state": "not_flinched"}}}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.resolve_runtime_d0_selectable_move_metadata_authority", lambda **_: own_meta)
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.materialize_detached_predictive_intermediate_state", lambda **_: intermediate)
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_damage_pivot_continuation_authority", lambda **_: {"status": "applies"})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_detached_intermediate_predictive_authority", lambda **_: {"status": "resolved"})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.materialize_detached_damage_pivot_switch", lambda **_: {"status": "resolved", "resulting_active_owner": incoming, "runtime_snapshot": {"status": "runtime_snapshot_ready", "state": {}}})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_runtime_strategy_d0", lambda **_: {"status": "resolved"})
    def ledger(*, actor, target, **_):
        return {"status": "evaluable", "terminal_leaves": (first if actor == own else second,)}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._attack_ledger", ledger)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot={"state": {}}, own_action=own_action, opponent_action=opponent_action, action_order_authority=order, pivot_replacement_authorities={first["leaf_id"]: _replacement(d0)}, pivot_entry_authorities={first["leaf_id"]: {}})
    assert pair["status"] == "evaluable", pair.get("reason")
    branch = pair["terminal_branches"][0]
    assert branch["second_action"]["leaf"]["provenance"]["target"] == incoming
    assert branch["second_action"]["leaf"]["provenance"]["target"] != own


def _opponent_first_pair_inputs():
    d0 = _d0() | {"schema_version": "deterministic-runtime-strategy-d0-v1"}
    own, foe = d0["decision_owner"], d0["active_owners"]["opponent"]
    own_meta = {"status": "resolved", "move_id": "u-turn", "metadata": {"move_id": "u-turn", "category": "physical", "power": 70, "type": "bug", "accuracy": 100, "priority": 0}, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": own}
    own_action = {"action_id": "attack:u-turn", "action_type": "attack", "identity": "u-turn", "move_metadata_authority": own_meta}
    opponent_action = {"status": "resolved", "action_id": "opponent_attack:tackle", "move_id": "tackle", "selectability": "selectable", "usability": {"status": "known_usable"}, "metadata_authority": {"status": "resolved", "metadata": {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}}, "session_id": "pivot", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own}
    order = {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "opponent_first", "session_id": "pivot", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": own, "own_action_id": own_action["action_id"], "opponent_action_id": opponent_action["action_id"], "own_actor": own, "opponent_actor": foe}
    return d0, own, foe, own_meta, own_action, opponent_action, order


def test_opponent_first_u_turn_rebinds_original_intent_and_executes_from_post_opponent_branch(monkeypatch):
    d0, own, foe, own_meta, own_action, opponent_action, order = _opponent_first_pair_inputs()
    incoming = {"session_id": "pivot", "side": "self", "slot_index": 1, "pokemon_id": "bench"}
    first = _leaf(d0) | {"leaf_id": "tackle:hit", "candidate_id": opponent_action["action_id"], "action_type": "attack", "branch_path": ("hit",), "probability": {"numerator": 1, "denominator": 1}, "provenance": {**_leaf(d0)["provenance"], "attacker": foe, "target": own, "move_id": "tackle"}}
    second = _leaf(d0) | {"leaf_id": "u-turn:hit", "action_type": "attack", "branch_path": ("hit",), "probability": {"numerator": 1, "denominator": 1}}
    intermediate = {"status": "resolved", "active": {"self": {"hypothetical_fainted": {"value": False}}, "opponent": {"hypothetical_fainted": {"value": False}}}, "second_action_compatibility": {"flinch_cancellation": {"status": "resolved", "affected_owner": own, "state": "not_flinched"}}}
    post_d0 = {**d0, "source_runtime_fingerprint": "post-opponent-runtime", "strategy_preview_fingerprint": "post-opponent-branch"}
    post_snapshot = {"status": "runtime_snapshot_ready", "state": {"self_side": {"pokemon": {}}, "opponent_side": {"pokemon": {}}}, "state_fingerprint": "post-opponent-runtime-snapshot"}
    seen = {}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.resolve_runtime_d0_selectable_move_metadata_authority", lambda **_: own_meta)
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_detached_actor_neutral_root_predictive_authority", lambda **_: {"status": "resolved", "predictive_strategy_d0": d0, "predictive_runtime_snapshot": {"state": {}}})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.materialize_detached_predictive_intermediate_state", lambda **_: intermediate)
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_detached_intermediate_predictive_authority", lambda **_: {"status": "resolved", "schema_version": "detached-intermediate-predictive-authority-v1"})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.consume_detached_sleep_freeze_execution_for_second_action", lambda **_: {"status": "resolved", "builder_inputs": {"strategy_d0": d0, "runtime_snapshot": {"state": {}}, "attacker": own, "target": foe}, "second_action_execution_branches": ({"execution_branch_id": "second_action:executed", "state": "executed", "conditional_probability": {"numerator": 1, "denominator": 1}},)})
    def rebind(**kwargs):
        seen["rebind"] = kwargs
        return {"status": "resolved", "action_id": own_action["action_id"], "move_id": "u-turn", "move_metadata": own_meta["metadata"], "selected_replacement_owner": incoming, "current_actor": own, "current_target": foe, "predictive_strategy_d0": post_d0, "predictive_runtime_snapshot": post_snapshot}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_pending_action_intent_rebinding_authority", rebind)
    def ledger(*, strategy_d0, runtime_snapshot, actor, **_):
        seen["ledger"] = (strategy_d0, runtime_snapshot, actor)
        return {"status": "evaluable", "terminal_leaves": (first if actor == foe else second,)}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._attack_ledger", ledger)
    def pivot(**kwargs):
        seen["pivot"] = kwargs
        return {"status": "applies"}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_damage_pivot_continuation_authority", pivot)
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.materialize_detached_damage_pivot_switch", lambda **_: {"status": "resolved", "resulting_active_owner": incoming, "runtime_snapshot": post_snapshot, "next_state": {"active": {"self": incoming}}})
    replacement = _replacement(d0)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot={"state": {}}, own_action=own_action, opponent_action=opponent_action, action_order_authority=order, pivot_replacement_authorities={own_action["action_id"]: replacement}, pivot_entry_authorities={second["leaf_id"]: {}})
    assert pair["status"] == "evaluable", pair.get("reason")
    assert seen["rebind"]["action"] == own_action
    assert seen["rebind"]["move_metadata_authority"] == own_meta
    assert seen["rebind"]["replacement_authority"] == replacement
    assert seen["ledger"] == (post_d0, post_snapshot, own)
    assert seen["pivot"]["action"] == own_action
    assert seen["pivot"]["move_metadata"] == own_meta["metadata"]
    assert pair["terminal_branches"][0]["pivot_transition"]["resulting_active_owner"] == incoming


def test_opponent_first_faint_cancels_pending_pivot_before_rebinding(monkeypatch):
    d0, own, foe, own_meta, own_action, opponent_action, order = _opponent_first_pair_inputs()
    first = _leaf(d0) | {"leaf_id": "tackle:ko", "candidate_id": opponent_action["action_id"], "action_type": "attack", "branch_path": ("hit",), "probability": {"numerator": 1, "denominator": 1}, "provenance": {**_leaf(d0)["provenance"], "attacker": foe, "target": own, "move_id": "tackle"}}
    intermediate = {"status": "resolved", "active": {"self": {"hypothetical_fainted": {"value": True}}, "opponent": {"hypothetical_fainted": {"value": False}}}}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.resolve_runtime_d0_selectable_move_metadata_authority", lambda **_: own_meta)
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_detached_actor_neutral_root_predictive_authority", lambda **_: {"status": "resolved", "predictive_strategy_d0": d0, "predictive_runtime_snapshot": {"state": {}}})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.materialize_detached_predictive_intermediate_state", lambda **_: intermediate)
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._attack_ledger", lambda *, actor, **_: {"status": "evaluable", "terminal_leaves": (first,)})
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair.freeze_pending_action_intent_rebinding_authority", lambda **_: (_ for _ in ()).throw(AssertionError("rebind must not run after faint")))
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot={"state": {}}, own_action=own_action, opponent_action=opponent_action, action_order_authority=order)
    assert pair["status"] == "evaluable", pair.get("reason")
    assert pair["terminal_branches"][0]["second_action"]["state"] == "cancelled_due_to_faint"
