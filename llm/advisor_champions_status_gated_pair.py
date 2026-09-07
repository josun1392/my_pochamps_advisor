"""Additive status-gated pair owner; existing ordering and attack owners remain."""
from copy import deepcopy
from fractions import Fraction
from typing import Mapping

from llm.advisor_champions_sleep_freeze_action_gate import (
    freeze_champions_status_action_gate, materialize_status_gate_branch,
    validate_status_gate, fd, fraction,
)

SCHEMA = "champions-status-gated-immediate-action-pair-v1"


def materialize_champions_status_gated_pair(*, strategy_d0, runtime_snapshot, base, own_action, opponent_action, own_meta, opponent_meta, orders, action_order_authority, quick_claw_action_order_authority=None):
    from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger, _metadata_for_inputs, _pending_second_action_flinch
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
    from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
    from llm.advisor_detached_intermediate_predictive_authority import freeze_detached_intermediate_predictive_authority
    from llm.advisor_detached_intermediate_paralysis_second_action_authority import consume_detached_intermediate_paralysis_for_second_action

    terminals = []
    error = None

    def finish(plan, probability, events, hp):
        terminals.append({"path_id": f"status_pair:{len(terminals)}", "order": plan["order"], "order_probability": fd(plan["probability"]),
                          "probability": fd(probability), "actions": tuple(events), "final_hp": deepcopy(hp)})

    def walk(plan, lineup, index, snapshot, probability, events, hp, execution=None):
        nonlocal error
        if error is not None: return
        actor, action, metadata = lineup[index]
        target = lineup[1-index][0]
        if hp[actor["side"]] == 0 or hp[target["side"]] == 0:
            finish(plan, probability, [*events, {"state": "cancelled_due_to_faint", "actor": deepcopy(actor), "action_id": action["action_id"]}], hp)
            return
        if isinstance(execution, Mapping) and execution.get("state") == "cancelled_due_to_paralysis":
            finish(plan, probability, [*events, {"state": "cancelled_due_to_paralysis", "actor": deepcopy(actor), "action_id": action["action_id"], "execution": deepcopy(execution)}], hp)
            return
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
        gate = freeze_champions_status_action_gate(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor,
            action_id=action["action_id"], move_id=metadata["metadata"]["move_id"], action_order={"order": plan["order"], "authority": action_order_authority},
            path=tuple(e.get("branch", {}).get("branch_id", e.get("state")) for e in events))
        if gate.get("status") != "resolved": error = gate; return
        for branch in gate["branches"]:
            view = materialize_status_gate_branch(strategy_d0=d0, runtime_snapshot=snapshot, authority=gate, branch=branch)
            if view.get("status") != "resolved": error = view; return
            event = {"state": branch["kind"], "actor": deepcopy(actor), "action_id": action["action_id"], "gate": gate, "branch": branch,
                     "condition_before": gate["condition"], "condition_after": branch["condition_after"],
                     "detached_before_state": snapshot["state"], "detached_after_state": view["runtime_snapshot"]["state"],
                     "execution_probability": deepcopy(execution["conditional_probability"]) if isinstance(execution, Mapping) else fd(Fraction(1))}
            weight = probability * fraction(branch["probability"])
            if not branch["executes"]:
                if index == 1: finish(plan, weight, [*events, event], hp)
                else: walk(plan, lineup, 1, view["runtime_snapshot"], weight, [*events, event], hp)
                continue
            if branch["kind"] == "move_specific_sleep_exception_executes" or gate["move_id"] in {"sleep-talk", "snore"}:
                error = {"status": "unsupported", "reason": "sleep_exception_move_execution_handoff_required"}; return
            if gate["move_id"] in {"u-turn", "volt-switch", "flip-turn"}:
                error = {"status": "incomplete", "reason": "status_gated_pivot_continuation_authority_required"}; return
            target_raw = view["runtime_snapshot"]["state"][f"{target['side']}_side"]["pokemon"][target["slot_index"]]
            if target_raw.get("condition") == "freeze" and (metadata["metadata"].get("type") == "fire" or gate["move_authority"]["self_thaw"]):
                error = {"status": "incomplete", "reason": "target_thaw_effect_authority_required"}; return
            inputs = {"strategy_d0": view["strategy_d0"], "runtime_snapshot": view["runtime_snapshot"], "attacker": actor, "target": target}
            rebound = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1",
                       "candidate_id": f"attack:{gate['move_id']}", "move_id": gate["move_id"], "metadata": _metadata_for_inputs(metadata, None),
                       "session_id": d0["session_id"], "source_runtime_fingerprint": view["strategy_d0"]["source_runtime_fingerprint"],
                       "source_branch_fingerprint": view["strategy_d0"]["strategy_preview_fingerprint"], "decision_owner": deepcopy(actor), "active_attacker": deepcopy(actor)}
            # Selected identity is retained while metadata gets the detached D0 bindings.
            bound_action = {"action_id": f"attack:{gate['move_id']}", "action_type": "attack", "identity": gate["move_id"], "move_metadata_authority": rebound}
            ledger = _attack_ledger(**{k: inputs[k] for k in ("strategy_d0", "runtime_snapshot")}, actor=actor, target=target, metadata_authority=rebound, action=bound_action)
            if ledger.get("status") != "evaluable": error = ledger; return
            for leaf in ledger["terminal_leaves"]:
                next_weight = weight * fraction(leaf["probability"])
                row = {**event, "attack_leaf": leaf}
                final_hp = {actor["side"]: leaf["consequences"]["own_final_hp"], target["side"]: leaf["consequences"]["target_final_hp"]}
                if index == 1:
                    finish(plan, next_weight, [*events, row], final_hp); continue
                if 0 in final_hp.values():
                    finish(plan, next_weight, [*events, row, {"state": "cancelled_due_to_faint", "actor": deepcopy(target), "action_id": lineup[1][1]["action_id"]}], final_hp); continue
                intermediate = materialize_detached_predictive_intermediate_state(strategy_d0=inputs["strategy_d0"], terminal_leaf=leaf)
                flinch = _pending_second_action_flinch(intermediate, target)
                if isinstance(flinch, str): error = {"status": "rejected", "reason": flinch}; return
                if flinch:
                    finish(plan, next_weight, [*events, row, {"state": "cancelled_due_to_flinch", "actor": deepcopy(target), "action_id": lineup[1][1]["action_id"]}], final_hp)
                    continue
                pending_metadata = {**deepcopy(lineup[1][2]), "session_id": view["strategy_d0"]["session_id"],
                    "source_runtime_fingerprint": view["strategy_d0"]["source_runtime_fingerprint"],
                    "source_branch_fingerprint": view["strategy_d0"]["strategy_preview_fingerprint"], "decision_owner": deepcopy(actor)}
                pending = freeze_detached_intermediate_predictive_authority(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"],
                    intermediate_state=intermediate, actor=target, target=actor, move_metadata_authority=pending_metadata)
                if pending.get("status") != "resolved": error = pending; return
                next_execution = consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=pending)
                if next_execution.get("status") != "resolved": error = next_execution; return
                for opportunity in next_execution["second_action_execution_branches"]:
                    walk(plan, lineup, 1, next_execution["builder_inputs"]["runtime_snapshot"], next_weight * fraction(opportunity["conditional_probability"]), [*events, row], final_hp, opportunity)

    hp = {side: runtime_snapshot["state"][f"{side}_side"]["pokemon"][owner["slot_index"]]["current_hp"] for side, owner in strategy_d0["active_owners"].items()}
    for plan in orders:
        own = (base["own_actor"], own_action, own_meta)
        opponent = (base["opponent_actor"], opponent_action, opponent_meta)
        walk(plan, (own, opponent) if plan["order"] == "own_first" else (opponent, own), 0, runtime_snapshot, plan["probability"], [], hp)
        if error is not None: return {"status": error.get("status", "incomplete"), "schema_version": SCHEMA, "reason": error.get("reason", "status_pair_execution_unavailable")}
    if sum((fraction(row["probability"]) for row in terminals), Fraction()) != 1:
        return {"status": "rejected", "reason": "champions_status_pair_mass_invalid"}
    return {"status": "evaluable", "schema_version": SCHEMA, "horizon": "immediate_action_pair", **deepcopy(base),
            "action_order": deepcopy(action_order_authority), "terminal_paths": tuple(terminals), "terminal_probability_mass": fd(Fraction(1)),
            "validation_request": deepcopy({"strategy_d0": strategy_d0, "runtime_snapshot": runtime_snapshot, "own_action": own_action,
                "opponent_action": opponent_action, "action_order_authority": action_order_authority,
                "quick_claw_action_order_authority": quick_claw_action_order_authority}),
            "provenance": "champions_status_gate_to_existing_attack_pair_v1"}


def normalize_champions_status_gated_pair(pair):
    """Validate typed paths and replay this additive owner from frozen inputs."""
    from llm.advisor_reducer_state_model import state_fingerprint
    from llm.advisor_ability_item_steal_ledger_validation import validate_ability_item_steal_leaf
    try:
        paths = pair["terminal_paths"]
        if pair.get("status") != "evaluable" or pair.get("schema_version") != SCHEMA or not paths: raise ValueError()
        ids = set()
        for path in paths:
            if path["path_id"] in ids or len(path["actions"]) != 2: raise ValueError()
            ids.add(path["path_id"])
            weight = fraction(path["order_probability"])
            expected_actors = (pair["own_actor"], pair["opponent_actor"]) if path["order"] == "own_first" else (pair["opponent_actor"], pair["own_actor"])
            history = []
            for index, event in enumerate(path["actions"]):
                if event["actor"] != expected_actors[index]: raise ValueError()
                expected_action = pair["own_action_id"] if event["actor"] == pair["own_actor"] else pair["opponent_action_id"]
                if event["action_id"] != expected_action: raise ValueError()
                if event["state"] == "cancelled_due_to_faint":
                    if "gate" in event or "attack_leaf" in event or index != 1 or 0 not in path["final_hp"].values(): raise ValueError()
                    continue
                if event["state"] == "cancelled_due_to_flinch":
                    if "gate" in event or "attack_leaf" in event or index != 1: raise ValueError()
                    continue
                if event["state"] == "cancelled_due_to_paralysis":
                    if "attack_leaf" in event or index != 1: raise ValueError()
                    weight *= fraction(event["execution"]["conditional_probability"])
                    continue
                gate, branch = event["gate"], event["branch"]
                if not validate_status_gate(gate) or branch not in gate["branches"] or gate["actor"] != event["actor"] or gate["action_id"] != event["action_id"] or gate["path"] != tuple(history): raise ValueError()
                if gate["session_id"] != pair["session_id"] or gate["action_order"] != {"order": path["order"], "authority": pair["action_order"]}: raise ValueError()
                if state_fingerprint(event["detached_before_state"]) != gate["source_runtime_fingerprint"]: raise ValueError()
                if index == 0 and gate["source_runtime_fingerprint"] != pair["source_runtime_fingerprint"]: raise ValueError()
                before = deepcopy(event["detached_before_state"])
                actor = gate["actor"]
                raw = before[f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]
                if gate["condition"] in {"sleep", "freeze"}:
                    if raw.get("champions_status_progression") != gate["progression"]: raise ValueError()
                    raw["condition"] = branch["condition_after"]
                    raw["champions_status_progression"] = deepcopy(branch["progression_after"])
                    if branch["condition_after"] == "none": raw["condition_provenance"] = {**raw["condition_provenance"], "condition": "none", "hypothetical_provenance": "champions_status_gate_clear_v1"}
                for owner in expected_actors: before[f"{owner['side']}_side"]["pokemon"][owner["slot_index"]]["detached_champions_status_gate_view"] = True
                if before != event["detached_after_state"] or event["condition_after"] != branch["condition_after"] or event["condition_before"] != gate["condition"] or event["state"] != branch["kind"]: raise ValueError()
                weight *= fraction(branch["probability"]) * fraction(event["execution_probability"])
                leaf = event.get("attack_leaf")
                if branch["executes"]:
                    if not isinstance(leaf, Mapping) or leaf["provenance"]["attacker"] != actor or leaf["provenance"]["move_id"] != gate["move_id"] or leaf["provenance"]["source_runtime_fingerprint"] != state_fingerprint(before) or validate_ability_item_steal_leaf(leaf) is not None: raise ValueError()
                    weight *= fraction(leaf["probability"])
                elif leaf is not None: raise ValueError()
                history.append(branch["branch_id"])
            if weight != fraction(path["probability"]): raise ValueError()
        if sum((fraction(row["probability"]) for row in paths), Fraction()) != 1 or pair["terminal_probability_mass"] != fd(Fraction(1)): raise ValueError()
        # Canonical replay binds order weights, both detached states, HP/items,
        # ability evidence, attack leaves and subsequent opportunity to one
        # frozen request. Internal agreement alone cannot authenticate a path.
        from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
        if materialize_immediate_move_vs_move_action_pair(**pair["validation_request"]) != pair: raise ValueError()
        from llm.advisor_exact_immediate_action_pair_outcome_ledger import _base, _final
        base = _base(pair)
        if base is None: raise ValueError()
        leaves = []
        for path in paths:
            attacks = [event["attack_leaf"] for event in path["actions"] if "attack_leaf" in event]
            final = _final(attacks[-1], base) if attacks else {}
            if isinstance(final, str): raise ValueError()
            final.update(own_final_hp=path["final_hp"]["self"], opponent_final_hp=path["final_hp"]["opponent"],
                         own_fainted=path["final_hp"]["self"] == 0, opponent_fainted=path["final_hp"]["opponent"] == 0)
            leaves.append({"pair_leaf_id": path["path_id"], "action_order": path["order"], "probability": deepcopy(path["probability"]),
                "first_action": deepcopy(path["actions"][0]), "second_action": deepcopy(path["actions"][1]),
                "final_consequences": final, "source_pair_branch": deepcopy(path)})
        return {"status": "evaluable", "schema_version": "exact-immediate-action-pair-outcome-ledger-v1", "horizon": "immediate_action_pair",
                **base, "terminal_leaves": tuple(leaves), "aggregation": "none_preserve_pair_branch_and_roll_identity",
                "champions_status_gated_pair": deepcopy(pair), "terminal_probability_mass": fd(Fraction(1)), "provenance": "validated_champions_status_gated_pair_v1"}
    except (KeyError, TypeError, ValueError, ZeroDivisionError, AttributeError, IndexError):
        return {"status": "rejected", "reason": "champions_status_pair_provenance_invalid"}
