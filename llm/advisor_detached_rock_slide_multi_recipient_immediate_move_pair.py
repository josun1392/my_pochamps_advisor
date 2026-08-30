"""Nested immediate pair composition for the immutable Rock Slide recipient DAG."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_predictive_intermediate_state import freeze_detached_actor_neutral_root_predictive_authority, materialize_detached_predictive_intermediate_state
from llm.advisor_detached_rock_slide_intermediate_state_vector import build_detached_rock_slide_vector_predictive_builder_view, freeze_detached_rock_slide_frozen_scope_graph_consumer_adapter, materialize_detached_rock_slide_intermediate_state_vector
from llm.advisor_detached_rock_slide_multi_recipient_predictive_graph_materialization import materialize_detached_rock_slide_multi_recipient_predictive_graph
from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger, _base, _metadata_for_inputs, _opponent_metadata, _orders, _status
from llm.advisor_rock_slide_multi_recipient_action_outcome_ledger import graph_terminal_rows, normalize_rock_slide_multi_recipient_action_outcome_ledger
from llm.advisor_runtime_strategy_d0 import resolve_runtime_d0_selectable_move_metadata_authority

SCHEMA_VERSION = "detached-rock-slide-multi-recipient-immediate-move-pair-v1"


def materialize_detached_rock_slide_multi_recipient_immediate_move_pair(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], own_action: Mapping[str, Any], opponent_action: Mapping[str, Any], action_order_authority: Mapping[str, Any], execution_scope_authority: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, own_action, opponent_action)
    if base is None or own_action.get("identity") != "rock-slide": return _result("rejected", "invalid_rock_slide_multi_recipient_pair_request", {})
    orders = _orders(action_order_authority, base)
    if isinstance(orders, tuple): return _result(*orders, base)
    own_meta = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=own_action)
    opponent_meta = _opponent_metadata(opponent_action, base)
    if own_meta.get("status") != "resolved" or isinstance(opponent_meta, tuple): return _result(_status(own_meta) if own_meta.get("status") != "resolved" else opponent_meta[0], own_meta.get("reason", "own_metadata_unavailable") if own_meta.get("status") != "resolved" else opponent_meta[1], base)
    graphs=[]; mass=Fraction()
    for plan in orders:
        result = _order(strategy_d0, runtime_snapshot, base, own_action, opponent_action, own_meta, opponent_meta, plan, execution_scope_authority)
        if result.get("status") != "evaluable": return _result(_status(result), result.get("reason", "rock_slide_pair_order_unavailable"), base)
        graphs.append(result); mass += _f(result["order_weighted_terminal_probability_mass"])
    if mass != 1: return _result("rejected", "rock_slide_pair_root_mass_invalid", base)
    return {"status":"evaluable","schema_version":SCHEMA_VERSION,"horizon":"immediate_action_pair",**base,"action_order":deepcopy(dict(action_order_authority)),"order_graphs":tuple(graphs),"terminal_leaf_representation":"immutable_rock_slide_graph_paths_with_attached_second_action_outcomes","terminal_probability_mass":_fd(mass),"legacy_flat_pair_ledger_compatibility":"not_applicable_requires_multi_recipient_pair_ledger","provenance":"strict_rock_slide_multi_recipient_graph_to_immediate_pair_v1"}


def _order(d0,snapshot,base,own,opponent,own_meta,opponent_meta,plan,scope):
    if plan["order"] == "own_first":
        graph=materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0,runtime_snapshot=snapshot,action=own,execution_scope_authority=scope)
        if graph.get("status") != "evaluable": return graph
        ledger=normalize_rock_slide_multi_recipient_action_outcome_ledger(graph=graph); rows=graph_terminal_rows(ledger=ledger)
        if isinstance(rows,str): return _result("rejected",rows,{})
        transitions=[]
        for source in rows:
            vector=materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0,runtime_snapshot=snapshot,execution_scope_authority=scope,source_terminal_path=source)
            if vector.get("status") != "resolved": return vector
            pending=base["opponent_actor"]; builder=build_detached_rock_slide_vector_predictive_builder_view(vector=vector,runtime_snapshot=snapshot,pending_actor=pending,pending_target=base["own_actor"])
            transition={"first_terminal_source_id":source["terminal_edge_id"],"incoming_path_probability":_fd(source["probability"]),"rock_slide_terminal_source":deepcopy(source),"recipient_vector":deepcopy(vector),"pending_actor":deepcopy(pending)}
            if builder.get("status") != "resolved": return builder
            if not builder["actor_can_act"]: transition["second_action"]={"state":"cancelled_due_to_faint","actor":deepcopy(pending),"conditional_probability":_fd(Fraction(1,1)),"reason":"second_action_cancelled_due_to_faint"}
            else:
                second=_attack_ledger(strategy_d0=builder["predictive_strategy_d0"],runtime_snapshot=builder["predictive_runtime_snapshot"],actor=builder["pending_actor"],target=builder["pending_target"],metadata_authority=opponent_meta)
                if second.get("status")!="evaluable": return second
                transition["second_action"]={"state":"outcome_ledger","actor":deepcopy(pending),"conditional_probability":_fd(Fraction(1,1)),"builder_view_provenance":builder["provenance"],"terminal_leaves":deepcopy(second["terminal_leaves"]),"terminal_probability_mass":deepcopy(second["terminal_probability_mass"])}
            _attach_probability_factorization(transition, plan)
            transitions.append(transition)
        conditional=sum((_f(x["incoming_path_probability"]) for x in transitions),Fraction())
        return _order_result(plan,graph,transitions,conditional)
    root=freeze_detached_actor_neutral_root_predictive_authority(strategy_d0=d0,runtime_snapshot=snapshot,opponent_action=opponent)
    if root.get("status")!="resolved": return root
    first=_attack_ledger(strategy_d0=root["predictive_strategy_d0"],runtime_snapshot=root["predictive_runtime_snapshot"],actor=base["opponent_actor"],target=base["own_actor"],metadata_authority=opponent_meta)
    if first.get("status")!="evaluable": return first
    transitions=[]
    for leaf in first["terminal_leaves"]:
        intermediate=materialize_detached_predictive_intermediate_state(strategy_d0=d0,terminal_leaf=leaf,root_predictive_authority=root)
        if intermediate.get("status")!="resolved": return intermediate
        vector=materialize_detached_rock_slide_intermediate_state_vector(strategy_d0=d0,runtime_snapshot=snapshot,execution_scope_authority=scope,scalar_intermediate_overlay=intermediate)
        if vector.get("status")!="resolved": return vector
        transition={"first_terminal_leaf":deepcopy(leaf),"incoming_path_probability":deepcopy(leaf["probability"]),"recipient_vector":deepcopy(vector),"pending_actor":deepcopy(base["own_actor"])}
        if vector["rock_slide_actor_state"]["fainted"]: transition["second_action"]={"state":"cancelled_due_to_faint","actor":deepcopy(base["own_actor"]),"conditional_probability":_fd(Fraction(1,1)),"reason":"second_action_cancelled_due_to_faint"}
        else:
            adapter=freeze_detached_rock_slide_frozen_scope_graph_consumer_adapter(vector=vector,runtime_snapshot=snapshot)
            graph=materialize_detached_rock_slide_multi_recipient_predictive_graph(strategy_d0=d0,runtime_snapshot=snapshot,action=own,execution_scope_authority=scope,frozen_scope_consumer_adapter=adapter)
            if graph.get("status")!="evaluable": return graph
            transition["second_action"]={"state":"rock_slide_graph","actor":deepcopy(base["own_actor"]),"conditional_probability":_fd(Fraction(1,1)),"frozen_scope_adapter_provenance":adapter.get("provenance"),"rock_slide_graph":deepcopy(graph)}
        _attach_probability_factorization(transition, plan)
        transitions.append(transition)
    return _order_result(plan,{"first_action_ledger":deepcopy(first)},transitions,sum((_f(x["incoming_path_probability"]) for x in transitions),Fraction()))

def _order_result(plan,first,transitions,mass):
    if mass != 1: return _result("rejected","rock_slide_pair_order_conditional_mass_invalid",{})
    p=_f(plan["probability"]); return {"status":"evaluable","schema_version":SCHEMA_VERSION,"action_order":plan["order"],"order_conditional_probability":_fd(p),**({"action_order_branch":deepcopy(plan["source_branch"])} if isinstance(plan.get("source_branch"),Mapping) else {}),"first_action":deepcopy(first),"terminal_transitions":tuple(transitions),"conditional_terminal_probability_mass":_fd(mass),"order_weighted_terminal_probability_mass":_fd(p*mass)}
def _f(v):
    """Accept the pair owner's internal Fraction as well as serialized mass."""
    if isinstance(v, Fraction):
        return v
    return Fraction(v["numerator"], v["denominator"])
def _fd(v): return {"numerator":v.numerator,"denominator":v.denominator}
def _attach_probability_factorization(transition, plan):
    first = _f(transition["incoming_path_probability"])
    order = _f(plan["probability"])
    transition["path_probability_factorization"] = {
        "order_probability": _fd(order),
        "first_action_path_probability": _fd(first),
        "second_action_conditional_probability_mass": _fd(Fraction(1, 1)),
        "order_weighted_source_probability": _fd(order * first),
    }
def _result(status,reason,base): return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
