"""Composite status-then-confusion action opportunity owner.

It is deliberately additive: status cancels are terminal for that opportunity;
only a status execution view is eligible to consume confusion.
"""
from copy import deepcopy
from fractions import Fraction
from llm.advisor_champions_sleep_freeze_action_gate import fd, fraction, freeze_champions_status_action_gate, materialize_status_gate_branch
from llm.advisor_champions_confusion_action_gate import freeze_champions_confusion_action_gate, materialize_confusion_branch
from llm.advisor_champions_confusion_self_hit import materialize_confusion_self_hit

SCHEMA = "champions-status-confusion-gated-immediate-action-pair-v1"

def materialize_champions_status_confusion_gated_pair(*,strategy_d0,runtime_snapshot,base,own_action,opponent_action,own_meta,opponent_meta,orders,action_order_authority,quick_claw_action_order_authority=None):
    from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger,_metadata_for_inputs,_pending_second_action_flinch
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
    from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
    from llm.advisor_detached_intermediate_predictive_authority import freeze_detached_intermediate_predictive_authority
    from llm.advisor_detached_intermediate_paralysis_second_action_authority import consume_detached_intermediate_paralysis_for_second_action
    terminals=[]; error=None
    def snapshot_for(state):
        from llm.advisor_reducer_state_model import state_fingerprint
        return {"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)}
    def finish(plan,p,events,hp): terminals.append({"path_id":f"status_confusion:{len(terminals)}","order":plan["order"],"order_probability":fd(plan["probability"]),"probability":fd(p),"actions":tuple(events),"final_hp":deepcopy(hp)})
    def opportunities(plan,actor,action,meta,snapshot,path):
        """Return execution/cancellation outcomes after status then confusion."""
        d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=actor)
        sg=freeze_champions_status_action_gate(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,action_id=action["action_id"],move_id=meta["metadata"]["move_id"],action_order={"order":plan["order"],"authority":action_order_authority},path=path)
        if sg.get("status")!="resolved": return sg
        rows=[]
        for sb in sg["branches"]:
            sv=materialize_status_gate_branch(strategy_d0=d0,runtime_snapshot=snapshot,authority=sg,branch=sb)
            if sv.get("status")!="resolved": return sv
            se={"state":sb["kind"],"actor":deepcopy(actor),"action_id":action["action_id"],"status_gate":sg,"status_branch":sb,"detached_before_state":snapshot["state"],"detached_after_state":sv["runtime_snapshot"]["state"]}
            if not sb["executes"]: rows.append({"probability":fraction(sb["probability"]),"events":[se],"snapshot":sv["runtime_snapshot"],"executes":False});continue
            raw=sv["runtime_snapshot"]["state"][f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]
            if raw.get("current_confusion")!="confused": rows.append({"probability":fraction(sb["probability"]),"events":[se],"snapshot":sv["runtime_snapshot"],"executes":True});continue
            cg=freeze_champions_confusion_action_gate(strategy_d0=sv["strategy_d0"],runtime_snapshot=sv["runtime_snapshot"],actor=actor,action_id=action["action_id"],move_id=meta["metadata"]["move_id"],action_order={"order":plan["order"],"authority":action_order_authority},path=(*path,sb["branch_id"]))
            if cg.get("status")!="resolved": return cg
            for cb in cg["branches"]:
                cv=materialize_confusion_branch(strategy_d0=sv["strategy_d0"],runtime_snapshot=sv["runtime_snapshot"],authority=cg,branch=cb)
                if cv.get("status")!="resolved": return cv
                ce={"state":cb["kind"],"actor":deepcopy(actor),"action_id":action["action_id"],"confusion_gate":cg,"confusion_branch":cb,"detached_before_state":sv["runtime_snapshot"]["state"],"detached_after_state":cv["runtime_snapshot"]["state"]}
                if cb["kind"]=="confusion_self_hit":
                    hit=materialize_confusion_self_hit(runtime_snapshot=cv["runtime_snapshot"],actor=actor,gate=cg,branch=cb)
                    if hit.get("status")!="resolved": return hit
                    for roll in hit["damage_rolls"]:
                        state=deepcopy(cv["runtime_snapshot"]["state"]); own=state[f"{actor['side']}_side"]["pokemon"][actor["slot_index"]];own["current_hp"]=roll["hp_after"];own["fainted"]=roll["self_fainted"]
                        if roll["disguise"]["status"]=="broken": own["disguise_state"]="broken"
                        rows.append({"probability":fraction(sb["probability"])*fraction(cb["probability"])*Fraction(1,16),"events":[se,{**ce,"self_hit":hit,"self_hit_roll":roll}],"snapshot":snapshot_for(state),"executes":False,"self_fainted":roll["self_fainted"]})
                else: rows.append({"probability":fraction(sb["probability"])*fraction(cb["probability"]),"events":[se,ce],"snapshot":cv["runtime_snapshot"],"executes":True})
        return {"status":"resolved","rows":rows}
    def walk(plan,lineup,index,snapshot,prob,events,hp,execution=None):
        nonlocal error
        actor,action,meta=lineup[index];target=lineup[1-index][0]
        if hp[actor["side"]]==0 or hp[target["side"]]==0: finish(plan,prob,[*events,{"state":"cancelled_due_to_faint","actor":deepcopy(actor),"action_id":action["action_id"]}],hp);return
        if isinstance(execution,dict) and execution.get("state")=="cancelled_due_to_paralysis": finish(plan,prob,[*events,{"state":"cancelled_due_to_paralysis","actor":deepcopy(actor),"action_id":action["action_id"],"execution":deepcopy(execution)}],hp);return
        if index==1 and events and events[-1].get("attack_leaf"):
            inter=materialize_detached_predictive_intermediate_state(strategy_d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=lineup[0][0]),terminal_leaf=events[-1]["attack_leaf"])
            if _pending_second_action_flinch(inter,actor): finish(plan,prob,[*events,{"state":"cancelled_due_to_flinch","actor":deepcopy(actor),"action_id":action["action_id"]}],hp);return
        result=opportunities(plan,actor,action,meta,snapshot,tuple(e.get("status_branch",e.get("confusion_branch",{})).get("branch_id",e["state"]) for e in events))
        if result.get("status")!="resolved": error=result;return
        for outcome in result["rows"]:
            weight=prob*outcome["probability"]; rows=[*events,*outcome["events"]]
            if not outcome["executes"]:
                ownhp=outcome["snapshot"]["state"][f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]["current_hp"]; next_hp={**hp,actor["side"]:ownhp}
                if index==1 or outcome.get("self_fainted"): finish(plan,weight,rows if index==1 else [*rows,{"state":"cancelled_due_to_faint","actor":deepcopy(target),"action_id":lineup[1][1]["action_id"]}],next_hp)
                else: walk(plan,lineup,1,outcome["snapshot"],weight,rows,next_hp)
                continue
            d0=freeze_runtime_strategy_d0(runtime_snapshot=outcome["snapshot"],decision_owner=actor); rebound={"status":"resolved","schema_version":"runtime-d0-selectable-move-metadata-authority-v1","candidate_id":f"attack:{meta['metadata']['move_id']}","move_id":meta["metadata"]["move_id"],"metadata":_metadata_for_inputs(meta,None),"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(actor),"active_attacker":deepcopy(actor)}
            ledger=_attack_ledger(strategy_d0=d0,runtime_snapshot=outcome["snapshot"],actor=actor,target=target,metadata_authority=rebound,action={"action_id":action["action_id"],"action_type":"attack","identity":meta["metadata"]["move_id"],"move_metadata_authority":rebound})
            if ledger.get("status")!="evaluable": error=ledger;return
            for leaf in ledger["terminal_leaves"]:
                final={actor["side"]:leaf["consequences"]["own_final_hp"],target["side"]:leaf["consequences"]["target_final_hp"]}; event={"state":"selected_action_executes","actor":deepcopy(actor),"action_id":action["action_id"],"attack_leaf":leaf}
                if index==1 or 0 in final.values(): finish(plan,weight*fraction(leaf["probability"]),[*rows,event] if index==1 else [*rows,event,{"state":"cancelled_due_to_faint","actor":deepcopy(target),"action_id":lineup[1][1]["action_id"]}],final)
                else:
                    inter=materialize_detached_predictive_intermediate_state(strategy_d0=d0,terminal_leaf=leaf); pending=freeze_detached_intermediate_predictive_authority(strategy_d0=d0,runtime_snapshot=outcome["snapshot"],intermediate_state=inter,actor=target,target=actor,move_metadata_authority={**deepcopy(lineup[1][2]),"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(actor)})
                    if pending.get("status")!="resolved": error=pending;return
                    nxt=consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=pending)
                    if nxt.get("status")!="resolved": error=nxt;return
                    for ex in nxt["second_action_execution_branches"]: walk(plan,lineup,1,nxt["builder_inputs"]["runtime_snapshot"],weight*fraction(leaf["probability"])*fraction(ex["conditional_probability"]),[*rows,event],final,ex)
    hp={side:runtime_snapshot["state"][f"{side}_side"]["pokemon"][owner["slot_index"]]["current_hp"] for side,owner in strategy_d0["active_owners"].items()}
    for plan in orders:
        lineup=((base["own_actor"],own_action,own_meta),(base["opponent_actor"],opponent_action,opponent_meta)) if plan["order"]=="own_first" else ((base["opponent_actor"],opponent_action,opponent_meta),(base["own_actor"],own_action,own_meta));walk(plan,lineup,0,runtime_snapshot,plan["probability"],[],hp)
        if error:return {"status":error.get("status","incomplete"),"schema_version":SCHEMA,"reason":error.get("reason","status_confusion_pair_unavailable")}
    if sum((fraction(row["probability"]) for row in terminals),Fraction())!=1:return {"status":"rejected","reason":"status_confusion_pair_mass_invalid"}
    return {"status":"evaluable","schema_version":SCHEMA,"horizon":"immediate_action_pair",**deepcopy(base),"action_order":deepcopy(action_order_authority),"terminal_paths":tuple(terminals),"terminal_probability_mass":fd(Fraction(1)),"validation_request":deepcopy({"strategy_d0":strategy_d0,"runtime_snapshot":runtime_snapshot,"own_action":own_action,"opponent_action":opponent_action,"action_order_authority":action_order_authority,"quick_claw_action_order_authority":quick_claw_action_order_authority}),"provenance":"champions_status_then_confusion_pair_v1"}

def normalize_champions_status_confusion_gated_pair(pair):
    try:
        if pair.get("status")!="evaluable" or pair.get("schema_version")!=SCHEMA or sum((fraction(x["probability"]) for x in pair["terminal_paths"]),Fraction())!=1: raise ValueError()
        from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
        if materialize_immediate_move_vs_move_action_pair(**pair["validation_request"]) != pair: raise ValueError()
        from llm.advisor_exact_immediate_action_pair_outcome_ledger import _base
        base=_base(pair)
        if base is None: raise ValueError()
        leaves=[]
        for path in pair["terminal_paths"]:
            self_hits=[event for event in path["actions"] if event.get("state")=="confusion_self_hit"]
            if any("attack_leaf" in event or event["self_hit"]["critical"] or event["self_hit"]["stab"] or event["self_hit"]["contact"] for event in self_hits): raise ValueError()
            leaves.append({"pair_leaf_id":path["path_id"],"action_order":path["order"],"probability":deepcopy(path["probability"]),"first_action":deepcopy(path["actions"][0]),"second_action":deepcopy(path["actions"][-1]),"final_consequences":{"own_final_hp":path["final_hp"]["self"],"opponent_final_hp":path["final_hp"]["opponent"],"own_fainted":path["final_hp"]["self"]==0,"opponent_fainted":path["final_hp"]["opponent"]==0},"source_pair_branch":deepcopy(path)})
        return {"status":"evaluable","schema_version":"exact-immediate-action-pair-outcome-ledger-v1","horizon":"immediate_action_pair",**base,"terminal_leaves":tuple(leaves),"terminal_probability_mass":fd(Fraction(1)),"champions_status_confusion_gated_pair":deepcopy(pair),"provenance":"validated_champions_status_confusion_pair_v1"}
    except (KeyError,TypeError,ValueError): return {"status":"rejected","reason":"champions_status_confusion_pair_provenance_invalid"}
