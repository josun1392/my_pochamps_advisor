"""Additive immediate-pair owner for exact Champions confusion opportunities."""
from copy import deepcopy
from fractions import Fraction
from llm.advisor_champions_sleep_freeze_action_gate import fd, fraction
from llm.advisor_champions_confusion_action_gate import freeze_champions_confusion_action_gate, materialize_confusion_branch
from llm.advisor_champions_confusion_self_hit import materialize_confusion_self_hit

SCHEMA="champions-confusion-gated-immediate-action-pair-v1"

def materialize_champions_confusion_gated_pair(*,strategy_d0,runtime_snapshot,base,own_action,opponent_action,own_meta,opponent_meta,orders,action_order_authority,quick_claw_action_order_authority=None):
    from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger, _metadata_for_inputs, _pending_second_action_flinch
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
    from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
    terminals=[]; error=None
    def finish(plan,prob,events,hp): terminals.append({"path_id":f"confusion_pair:{len(terminals)}","order":plan["order"],"order_probability":fd(plan["probability"]),"probability":fd(prob),"actions":tuple(events),"final_hp":deepcopy(hp)})
    def walk(plan,lineup,index,snapshot,prob,events,hp):
        nonlocal error
        actor,action,meta=lineup[index]; target=lineup[1-index][0]
        if hp[actor["side"]]==0 or hp[target["side"]]==0: finish(plan,prob,[*events,{"state":"cancelled_due_to_faint","actor":deepcopy(actor),"action_id":action["action_id"]}],hp);return
        if index==1 and events and _pending_second_action_flinch(materialize_detached_predictive_intermediate_state(strategy_d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=lineup[0][0]),terminal_leaf=events[0].get("attack_leaf",{})),actor):
            finish(plan,prob,[*events,{"state":"cancelled_due_to_flinch","actor":deepcopy(actor),"action_id":action["action_id"]}],hp);return
        d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=actor)
        gate=freeze_champions_confusion_action_gate(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,action_id=action["action_id"],move_id=meta["metadata"]["move_id"],action_order={"order":plan["order"],"authority":action_order_authority},path=tuple(e.get("branch",{}).get("branch_id",e["state"]) for e in events))
        if gate.get("status")!="resolved": error=gate;return
        for branch in gate["branches"]:
            view=materialize_confusion_branch(strategy_d0=d0,runtime_snapshot=snapshot,authority=gate,branch=branch)
            if view.get("status")!="resolved": error=view;return
            event={"state":branch["kind"],"actor":deepcopy(actor),"action_id":action["action_id"],"gate":gate,"branch":branch,"detached_before_state":snapshot["state"],"detached_after_state":view["runtime_snapshot"]["state"]}
            weight=prob*fraction(branch["probability"])
            if branch["kind"]=="confusion_self_hit":
                selfhit=materialize_confusion_self_hit(runtime_snapshot=view["runtime_snapshot"],actor=actor,gate=gate,branch=branch)
                if selfhit.get("status")!="resolved": error=selfhit;return
                for roll in selfhit["damage_rolls"]:
                    after={**deepcopy(view["runtime_snapshot"]["state"])}; raw=after[f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]; raw["current_hp"]=roll["hp_after"];raw["fainted"]=roll["self_fainted"]
                    if roll["disguise"]["status"]=="broken": raw["disguise_state"]="broken"
                    row={**event,"self_hit":selfhit,"self_hit_roll":roll}; next_hp={**hp,actor["side"]:roll["hp_after"]}
                    if index==1 or roll["self_fainted"]: finish(plan,weight*Fraction(1,16),[*events,row] if index==1 else [*events,row,{"state":"cancelled_due_to_faint","actor":deepcopy(target),"action_id":lineup[1][1]["action_id"]}],next_hp)
                    else: walk(plan,lineup,1,{"status":"runtime_snapshot_ready","session_id":after["session_id"],"state":after,"state_fingerprint":__import__('llm.advisor_reducer_state_model',fromlist=['state_fingerprint']).state_fingerprint(after)},weight*Fraction(1,16),[*events,row],next_hp)
                continue
            rebound={"status":"resolved","schema_version":"runtime-d0-selectable-move-metadata-authority-v1","candidate_id":f"attack:{gate['move_id']}","move_id":gate["move_id"],"metadata":_metadata_for_inputs(meta,None),"session_id":d0["session_id"],"source_runtime_fingerprint":view["strategy_d0"]["source_runtime_fingerprint"],"source_branch_fingerprint":view["strategy_d0"]["strategy_preview_fingerprint"],"decision_owner":deepcopy(actor),"active_attacker":deepcopy(actor)}
            ledger=_attack_ledger(strategy_d0=view["strategy_d0"],runtime_snapshot=view["runtime_snapshot"],actor=actor,target=target,metadata_authority=rebound,action={"action_id":action["action_id"],"action_type":"attack","identity":gate["move_id"],"move_metadata_authority":rebound})
            if ledger.get("status")!="evaluable": error=ledger;return
            for leaf in ledger["terminal_leaves"]:
                final={actor["side"]:leaf["consequences"]["own_final_hp"],target["side"]:leaf["consequences"]["target_final_hp"]}; row={**event,"attack_leaf":leaf}
                if index==1 or 0 in final.values(): finish(plan,weight*fraction(leaf["probability"]),[*events,row] if index==1 else [*events,row,{"state":"cancelled_due_to_faint","actor":deepcopy(target),"action_id":lineup[1][1]["action_id"]}],final)
                else: walk(plan,lineup,1,view["runtime_snapshot"],weight*fraction(leaf["probability"]),[*events,row],final)
    hp={side:runtime_snapshot["state"][f"{side}_side"]["pokemon"][owner["slot_index"]]["current_hp"] for side,owner in strategy_d0["active_owners"].items()}
    for plan in orders:
        line=((base["own_actor"],own_action,own_meta),(base["opponent_actor"],opponent_action,opponent_meta)) if plan["order"]=="own_first" else ((base["opponent_actor"],opponent_action,opponent_meta),(base["own_actor"],own_action,own_meta));walk(plan,line,0,runtime_snapshot,plan["probability"],[],hp)
        if error:return {"status":error.get("status","incomplete"),"schema_version":SCHEMA,"reason":error.get("reason","confusion_pair_unavailable")}
    if sum((fraction(row["probability"]) for row in terminals),Fraction())!=1:return {"status":"rejected","reason":"confusion_pair_mass_invalid"}
    return {"status":"evaluable","schema_version":SCHEMA,"horizon":"immediate_action_pair",**deepcopy(base),"action_order":deepcopy(action_order_authority),"terminal_paths":tuple(terminals),"terminal_probability_mass":fd(Fraction(1)),"validation_request":deepcopy({"strategy_d0":strategy_d0,"runtime_snapshot":runtime_snapshot,"own_action":own_action,"opponent_action":opponent_action,"action_order_authority":action_order_authority,"quick_claw_action_order_authority":quick_claw_action_order_authority}),"provenance":"champions_confusion_gate_pair_v1"}

def normalize_champions_confusion_gated_pair(pair):
    """Authenticate all path data by replaying the frozen typed request."""
    try:
        if pair.get("status")!="evaluable" or pair.get("schema_version")!=SCHEMA or not pair.get("terminal_paths"): raise ValueError()
        from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
        if materialize_immediate_move_vs_move_action_pair(**pair["validation_request"]) != pair: raise ValueError()
        if sum((fraction(path["probability"]) for path in pair["terminal_paths"]),Fraction()) != 1: raise ValueError()
        for path in pair["terminal_paths"]:
            if len(path["actions"]) != 2: raise ValueError()
            for event in path["actions"]:
                if event["state"]=="confusion_self_hit":
                    hit=event.get("self_hit"); roll=event.get("self_hit_roll")
                    if not isinstance(hit,dict) or hit.get("critical") is not False or hit.get("stab") is not False or hit.get("contact") is not False or "attack_leaf" in event or roll not in hit.get("damage_rolls",()): raise ValueError()
                if event["state"]=="confusion_selected_action_executes" and "attack_leaf" not in event: raise ValueError()
        from llm.advisor_exact_immediate_action_pair_outcome_ledger import _base
        base=_base(pair)
        if base is None: raise ValueError()
        leaves=tuple({"pair_leaf_id":path["path_id"],"action_order":path["order"],"probability":deepcopy(path["probability"]),"first_action":deepcopy(path["actions"][0]),"second_action":deepcopy(path["actions"][1]),"final_consequences":{"own_final_hp":path["final_hp"]["self"],"opponent_final_hp":path["final_hp"]["opponent"],"own_fainted":path["final_hp"]["self"]==0,"opponent_fainted":path["final_hp"]["opponent"]==0},"source_pair_branch":deepcopy(path)} for path in pair["terminal_paths"])
        return {"status":"evaluable","schema_version":"exact-immediate-action-pair-outcome-ledger-v1","horizon":"immediate_action_pair",**base,"terminal_leaves":leaves,"terminal_probability_mass":fd(Fraction(1)),"champions_confusion_gated_pair":deepcopy(pair),"provenance":"validated_champions_confusion_pair_v1"}
    except (KeyError,TypeError,ValueError): return {"status":"rejected","reason":"champions_confusion_pair_provenance_invalid"}
