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
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot={"state": {}}, own_action=own_action, opponent_action=opponent_action, action_order_authority=order, pivot_replacement_authorities={first["leaf_id"]: _replacement(d0)})
    assert pair["status"] == "evaluable", pair.get("reason")
    branch = pair["terminal_branches"][0]
    assert branch["second_action"]["leaf"]["provenance"]["target"] == incoming
    assert branch["second_action"]["leaf"]["provenance"]["target"] != own
