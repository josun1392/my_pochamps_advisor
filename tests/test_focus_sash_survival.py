from copy import deepcopy

from llm.advisor_focus_sash_survival import apply_focus_sash_to_hit
from llm.advisor_detached_deterministic_fixed_damage_attack_leaf import materialize_detached_deterministic_fixed_damage_attack_leaf
from llm.advisor_predictive_attack_authority import build_predictive_fixed_damage_attack_authority
from llm.advisor_predictive_normal_formula_post_hit import compose_predictive_normal_formula_post_hit
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_focus_sash_survival_authority import freeze_runtime_d0_focus_sash_survival_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_strategy_d0 import freeze_runtime_seismic_toss_predictive_input
from tests.test_detached_opponent_response_profile import _fixed_damage_inputs
from tests.test_immediate_attack_vs_opponent_switch_action_pair import _owner, _state
from tests.test_predictive_normal_formula_post_hit import _interval


def _d0_inputs(*, item="focus-sash", hp=100, max_hp=100):
    state = _state()
    target = state["opponent_side"]["pokemon"][0]
    target["current_hp"] = hp
    target["max_hp"] = max_hp
    target["known_item"] = item
    target["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": "known" if item is not None else "known_absent",
    }
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }
    own, foe = _owner(state, "self"), _owner(state, "opponent")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=own)
    move = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}
    action = {"action_id": "attack:tackle", "action_type": "attack", "identity": "tackle"}
    return d0, snapshot, own, foe, action, move


def _authority(interval, *, hp=20, max_hp=20, move_id="giga-drain"):
    return {
        "status": "ready",
        "schema_version": "runtime-d0-focus-sash-survival-authority-v1",
        "session_id": interval["session_id"],
        "source_runtime_fingerprint": "runtime",
        "source_branch_fingerprint": interval["source_branch_fingerprint"],
        "decision_owner": deepcopy(interval["decision_owner"]),
        "holder": deepcopy(interval["target"]),
        "attacker": deepcopy(interval["attacker"]),
        "action_id": f"attack:{move_id}",
        "move_id": move_id,
        "current_hp": hp,
        "maximum_hp": max_hp,
        "current_item_authority": {"status": "known", "value": "focus-sash"},
        "outcome": "available",
        "focus_sash_available": True,
        "eligible": True,
        "item_before": "focus-sash",
        "provenance": "test_focus_sash_authority",
    }


def test_runtime_focus_sash_authority_distinguishes_available_absent_unknown_and_stale():
    d0, snapshot, own, foe, action, move = _d0_inputs()
    ready = freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, holder=foe, attacker=own, action=action, move_metadata=move,
    )
    assert ready["status"] == "ready"
    assert ready["current_hp"] == ready["maximum_hp"] == 100
    assert ready["current_item_authority"]["value"] == "focus-sash"

    d0, snapshot, own, foe, action, move = _d0_inputs(item=None)
    absent = freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, holder=foe, attacker=own, action=action, move_metadata=move,
    )
    assert absent["status"] == "resolved" and absent["outcome"] == "known_no_effect"

    d0, snapshot, own, foe, action, move = _d0_inputs(item=None)
    snapshot["state"]["opponent_side"]["pokemon"][0]["known_item_provenance"]["status"] = "unknown"
    snapshot["state_fingerprint"] = state_fingerprint(snapshot["state"])
    unknown_d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=own)
    unknown = freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=unknown_d0, runtime_snapshot=snapshot, holder=foe, attacker=own, action=action, move_metadata=move,
    )
    assert unknown["status"] == "incomplete" and unknown["reason"] == "focus_sash_item_unknown"

    stale = deepcopy(snapshot)
    stale["state"]["self_side"]["pokemon"][0]["current_hp"] = 99
    stale["state_fingerprint"] = state_fingerprint(stale["state"])
    rejected = freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=unknown_d0, runtime_snapshot=stale, holder=foe, attacker=own, action=action, move_metadata=move,
    )
    assert rejected["status"] == "rejected"
    assert rejected["reason"] in {"stale_runtime_d0", "runtime_fingerprint_changed"}

    d0, snapshot, own, foe, action, move = _d0_inputs(item="leftovers")
    non_sash = freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, holder=foe, attacker=own, action=action, move_metadata=move,
    )
    assert non_sash["status"] == "resolved" and non_sash["reason"] == "known_non_focus_sash_item"

    d0, snapshot, own, foe, action, move = _d0_inputs(hp=99, max_hp=100)
    below_full = freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, holder=foe, attacker=own, action=action, move_metadata=move,
    )
    assert below_full["status"] == "resolved" and below_full["reason"] == "hp_not_full"

    foreign = deepcopy(foe)
    foreign["pokemon_id"] = "not-the-holder"
    assert freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, holder=foreign, attacker=own, action=action, move_metadata=move,
    )["status"] == "rejected"

    d0, snapshot, own, foe, action, move = _d0_inputs(hp=120, max_hp=100)
    hp_mismatch = freeze_runtime_d0_focus_sash_survival_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, holder=foe, attacker=own, action=action, move_metadata=move,
    )
    assert hp_mismatch["status"] == "incomplete" and hp_mismatch["reason"] == "focus_sash_hp_unknown"


def test_focus_sash_adapter_caps_lethal_full_hp_hit_and_consumes_once():
    authority = _authority(_interval({"move_id": "giga-drain", "category": "special", "power": 75, "type": "grass", "drain": 50}, hp=20))
    applied = apply_focus_sash_to_hit(authority=authority, consumed=False, hp_before=20, raw_damage=30, actual_damage=20, source_hit={"hit_index": 1})
    assert applied["activated"] is True
    assert applied["actual_damage"] == 19
    assert applied["post_hp"] == 1
    assert applied["consumed"] is True
    assert applied["survival"]["item_after"]["status"] == "known_absent"

    spent = apply_focus_sash_to_hit(authority=authority, consumed=True, hp_before=20, raw_damage=30, actual_damage=20, source_hit={"hit_index": 2})
    assert spent["activated"] is False
    assert spent["actual_damage"] == 20
    assert spent["survival"]["reason"] == "already_consumed"


def test_normal_formula_focus_sash_survival_preserves_roll_probability_and_blocks_sturdy_precedence():
    move = {"move_id": "giga-drain", "category": "special", "power": 75, "type": "grass", "drain": 50}
    interval = _interval(move, hp=20)
    authority = _authority(interval)
    result = compose_predictive_normal_formula_post_hit(
        interval=interval,
        move_metadata=move,
        attacker_hp={"current_hp": 50, "max_hp": 100},
        attacker_item=None,
        attacker_ability="pressure",
        target_ability="pressure",
        target_focus_sash_survival_authority=authority,
    )
    assert result["status"] == "resolved"
    assert len(result["branches"]) == 16
    assert all(row["actual_damage"] == 19 and row["focus_sash_survival"]["outcome"] == "applied" for row in result["branches"])

    nonlethal = compose_predictive_normal_formula_post_hit(
        interval=_interval(move, hp=100),
        move_metadata=move,
        attacker_hp={"current_hp": 50, "max_hp": 100},
        attacker_item=None,
        attacker_ability="pressure",
        target_ability="pressure",
        target_focus_sash_survival_authority=_authority(_interval(move, hp=100), hp=100, max_hp=100),
    )
    assert nonlethal["status"] == "resolved"
    assert all(row["focus_sash_survival"]["outcome"] == "not_triggered" for row in nonlethal["branches"])

    sturdy = {
        "schema_version": "detached-switch-in-sturdy-survival-authority-v1",
        "session_id": interval["session_id"],
        "source_runtime_fingerprint": "runtime",
        "source_branch_fingerprint": interval["source_branch_fingerprint"],
        "decision_owner": interval["decision_owner"],
        "defender": interval["target"],
        "attacker": interval["attacker"],
        "status": "ready",
        "post_entry_hp": 20,
        "maximum_hp": 20,
        "provenance": "test",
    }
    blocked = compose_predictive_normal_formula_post_hit(
        interval=interval,
        move_metadata=move,
        attacker_hp={"current_hp": 50, "max_hp": 100},
        attacker_item=None,
        attacker_ability="pressure",
        target_ability="sturdy",
        target_sturdy_survival_authority=sturdy,
        target_focus_sash_survival_authority=authority,
    )
    assert blocked["status"] == "unsupported"
    assert blocked["reason"] == "simultaneous_sturdy_focus_sash_survival_precedence_unsupported"


def test_fixed_damage_focus_sash_survival_caps_seismic_toss_leaf():
    _state0, _snapshot0, d0, _own_action, _opponent_action, _order = _fixed_damage_inputs(own_first=True, opponent_hp=50)
    attacker = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    frozen = freeze_runtime_seismic_toss_predictive_input(
        strategy_d0=d0, runtime_snapshot=_snapshot0, attacker=attacker, target=target, move_id="seismic-toss",
    )
    authority = build_predictive_fixed_damage_attack_authority(
        branch_state=d0["strategy_state"], decision_owner=attacker, target_owner=target,
        move_id="seismic-toss", predictive_input=frozen["predictive_input"],
    )
    focus = {
        "status": "ready",
        "schema_version": "runtime-d0-focus-sash-survival-authority-v1",
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": attacker,
        "holder": target,
        "attacker": attacker,
        "action_id": "attack:seismic-toss",
        "move_id": "seismic-toss",
        "current_hp": 50,
        "maximum_hp": 50,
        "current_item_authority": {"status": "known", "value": "focus-sash"},
        "outcome": "available",
        "focus_sash_available": True,
        "eligible": True,
        "item_before": "focus-sash",
        "provenance": "test",
    }
    leaf = materialize_detached_deterministic_fixed_damage_attack_leaf(
        strategy_d0=d0,
        attacker=attacker,
        target=target,
        move_id="seismic-toss",
        predictive_authority=authority,
        focus_sash_survival_authority=focus,
    )
    assert leaf["status"] == "evaluable", leaf.get("reason")
    terminal = leaf["terminal_leaves"][0]
    assert terminal["consequences"]["target_final_hp"] == 1
    assert terminal["consequences"]["target_ko"] is False
    assert terminal["consequences"]["focus_sash_survival"]["outcome"] == "applied"
