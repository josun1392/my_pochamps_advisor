"""TRAIN snapshot first-action teacher upper-bound pilot; no learning or model save."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch

from advisor.learned_action_search_teacher import public_candidates, select_from_search, summarize_confirmation
from advisor.learned_action_signals import branch_candidate, public_identity
from advisor.learned_decision_snapshots import read_root,replay_original,outside_git,write_new
from advisor.learned_parent_anchor import tensor_digest,optimizer_digest
from advisor.learned_policy import LearnedPolicy
from advisor.learned_update_credit import score_public
from advisor.learning_resources import WindowsJob,RuntimeLimit,enforce_local_network_only,atomic_json
from advisor.showdown_environment import ShowdownEnvironment
from scripts.pilot_foundation_decision_snapshots import NativeBudget
from scripts.diagnose_foundation_policy_matched_signals import load_source,references,forbid_training


def read(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def file_hash(path):return sha256(Path(path).read_bytes()).hexdigest()


def preflight(source, prior, output):
    """Original TRAIN sources only; do not open any protected/master user file."""
    op,cfg,parent,all_roots=load_source(source)
    provenance=read(prior/"source_provenance.json")
    ids=[r["root"] for r in provenance["roots"] if r["eligible"]]
    roots=[r for r in all_roots if r["id"] in ids]
    if len(roots)!=24 or [r["id"] for r in roots]!=ids:raise ValueError("existing24_order_required")
    refs=references(cfg);contracts=[]
    for root in roots:
        identity=root["training_episode_identity"]
        if identity["split"]!="train" or refs[identity["opponent"]][1]!=identity["opponent_model_id"]:
            raise ValueError("TRAIN_frozen_opponent_provenance")
        read_root(source/"run/snapshots",root)
        public=read(source/"run/snapshots/public"/(root["id"]+".json"))["observation"]
        features=parent.encoder.encode(public)
        if sha256(features.tobytes()).hexdigest()!=root["observation_sha256"]:raise ValueError("public_binding")
        scores=score_public(parent.model.policy,features,root["action_mask"])
        contract=public_candidates(public,scores["probabilities"])
        if contract["baseline"]!=parent.act(public):raise ValueError("Foundation_argmax_binding")
        contracts.append({"root":root["id"],"opponent":identity["opponent"],"case_index":identity["case_index"],
            "public_SHA256":root["public_identity"],"encoded_SHA256":root["observation_sha256"],
            "checkpoint_digest":root["checkpoint_digest"],"source_policy_id":root["policy_id"],
            "Foundation_scores":scores,**contract})
    result={"roots":contracts,"source":str(source),"prior":str(prior),
        "Foundation_ZIP_SHA256":op["model_sha256"],
        "Foundation_parameters":tensor_digest(parent.model.policy.state_dict()),
        "Foundation_Adam":optimizer_digest(parent.model.policy),
        "source_distribution":"PPO_collected_TRAIN_decisions_not_independent_generalization",
        "native_suffixes":0,"training":0,"protected_content_reads":0}
    write_new(output,result);return result


def validate_plan(plan):
    if (plan.get("schema")!="foundation-action-search-teacher-plan-v1" or plan.get("native_cap")!=1008
            or plan.get("global_cap")!=1024 or plan.get("regression_reserve")!=16
            or plan.get("PPO")!=0 or plan.get("device")!="cpu" or plan.get("workers")!=1
            or plan.get("cpu_percent")!=50 or plan.get("memory_mib")!=12288
            or not 60<=plan.get("max_seconds",0)<=1800):
        raise ValueError("bounded_teacher_plan")
    search=plan["search_seeds"];confirm=plan["confirmation_seeds"]
    if len(search)!=6 or len(confirm)!=10 or len({tuple(s) for s in search+confirm})!=16:
        raise ValueError("disjoint_predeclared_search_confirmation_seeds")
    if any(len(s)!=4 or any(type(n) is not int or not 0<=n<=65535 for n in s) for s in search+confirm):
        raise ValueError("native_seed_contract")
    for path,expected in plan["input_hashes"].items():
        if file_hash(path)!=expected:raise ValueError("frozen_teacher_input:"+path)
    repo=Path(__file__).resolve().parents[1]
    for path,expected in plan["source_hashes"].items():
        if file_hash(repo/path)!=expected:raise ValueError("frozen_teacher_source:"+path)
    contracts=read(plan["preflight"])["roots"]
    if len(contracts)>24 or not contracts or sum(6*len(r["actions"])+20+3 for r in contracts)>1008:
        raise ValueError("teacher_allocation_cap")


def run(plan,output,job):
    validate_plan(plan);output=outside_git(output);output.mkdir(exist_ok=True)
    write_new(output/"started.json",{"PID":os.getpid(),"plan_SHA256":file_hash(plan["plan_file"]),
        "no_automatic_restart":True,"training":0})
    start=perf_counter();limit=RuntimeLimit(output,plan["max_seconds"]);native=None;budget=None
    try:
        source=Path(plan["source"]);op,cfg,parent,all_roots=load_source(source)
        contracts=read(plan["preflight"])["roots"];roots={r["id"]:r for r in all_roots}
        refs=references(cfg);rivals={}
        for kind in {r["opponent"] for r in contracts}:
            path,identity=refs[kind];rivals[kind]=LearnedPolicy(path,cfg["catalog"],expected_model_id=identity)
        before={"Foundation":{"parameters":tensor_digest(parent.model.policy.state_dict()),
            "Adam":optimizer_digest(parent.model.policy)},
            "rivals":{k:{"parameters":tensor_digest(v.model.policy.state_dict()),"Adam":optimizer_digest(v.model.policy)} for k,v in rivals.items()}}
        units=output/"native_units";units.mkdir();budget=NativeBudget(units,maximum=1008)
        native=ShowdownEnvironment(cfg["checkout"],max_decisions=cfg["max_decisions"])
        search_results={};selections=[]
        def data(contract):
            r=roots[contract["root"]];cp=read_root(source/"run/snapshots",r)
            public=read(source/"run/snapshots/public"/(r["id"]+".json"))["observation"]
            return r,cp,public,rivals[contract["opponent"]]
        # Verify all roots before any selection-driven continuation.
        for contract in contracts:
            r,cp,public,rival=data(contract)
            r["trace"]=[json.loads(l) for l in (source/"run/snapshots/private"/(r["id"]+".trace.jsonl")).read_text().splitlines()]
            def bind():
                native.restart(cp);actual=native.observation("self",include_history=True)
                if native.save()!=cp or public_identity(actual)!=r["public_identity"]:raise ValueError("teacher_native_root")
                scores=score_public(parent.model.policy,parent.encoder.encode(actual),r["action_mask"])
                check=public_candidates(actual,scores["probabilities"])
                if check["actions"]!=contract["actions"] or scores!=contract["Foundation_scores"]:
                    raise ValueError("teacher_candidates_changed_after_native_restore")
                other=int(rival.act(native.observation("opponent",include_history=True)))
                if other!=r["trace"][0]["actions"]["opponent"]:raise ValueError("original_opponent_not_reconstructed")
                return {"root":r["id"],"choices":check,"opponent_action":other,"native_digest":cp["digest"]}
            budget.run("bind_"+r["id"],bind)
            budget.run("replay_"+r["id"],lambda:replay_original(native,cp,r,public,stopping=limit.stopping))
        write_new(output/"replay_gate_passed.json",{"roots":len(contracts),"native_units":budget.count})
        for i,contract in enumerate(contracts):
            r,cp,public,rival=data(contract);samples={a:[] for a in contract["actions"]}
            for rep,seed in enumerate(plan["search_seeds"]):
                # Rotate candidate execution order without changing samples.
                actions=contract["actions"];ordered=actions[rep%len(actions):]+actions[:rep%len(actions)]
                for action in ordered:
                    result=budget.run(f"search_{r['id']}_{rep}_{action}",lambda action=action,seed=seed:
                        branch_candidate(native,cp,public,side="self",action=action,future_seed=seed,
                            own_policy=parent,opponent_policy=rival,stopping=limit.stopping))
                    samples[action].append(result)
            chosen=select_from_search(contract,samples)
            selections.append({"root":r["id"],**chosen})
            search_results[r["id"]]=samples
            atomic_json(output/"progress.json",{"phase":"search_only","roots_done":i+1,"roots":len(contracts),
                "native_units":budget.count,"seconds":perf_counter()-start,"resources":job.usage()})
        write_new(output/"search_results.json",search_results)
        write_new(output/"teacher_selections.json",selections)
        selection_sha=file_hash(output/"teacher_selections.json")
        write_new(output/"selections_sealed_before_confirmation.json",{
            "selection_SHA256":selection_sha,"confirmation_native_started":0,"native_units":budget.count})
        confirmation=[]
        for i,(contract,selection) in enumerate(zip(contracts,selections)):
            r,cp,public,rival=data(contract)
            if selection["root"]!=r["id"]:raise ValueError("teacher_root_join")
            if selection["status"]!="selected":
                confirmation.append({"root":r["id"],"baseline_action":contract["baseline"],
                    "selected_action":contract["baseline"],"pairs":[],"incomplete":True});continue
            baseline=contract["baseline"];selected=selection["selected"];pairs=[]
            families={x["action"]:x["family"] for x in contract["candidates"]}
            for rep,seed in enumerate(plan["confirmation_seeds"]):
                results={}
                actions=[baseline] if selected==baseline else [baseline,selected]
                if rep%2:actions=actions[::-1]
                for action in actions:
                    results[action]=budget.run(f"confirm_{r['id']}_{rep}_{action}",lambda action=action,seed=seed:
                        branch_candidate(native,cp,public,side="self",action=action,future_seed=seed,
                            own_policy=parent,opponent_policy=rival,stopping=limit.stopping))
                pairs.append({"rep":rep,"baseline":results[baseline],"selected":results[selected],
                    "same_action_result_reused":selected==baseline})
            repeat=budget.run("repeat_"+r["id"],lambda:
                branch_candidate(native,cp,public,side="self",action=selected,future_seed=plan["confirmation_seeds"][0],
                    own_policy=parent,opponent_policy=rival,stopping=limit.stopping))
            if repeat!=pairs[0]["selected"]:raise ValueError("teacher_repeated_continuation_failed")
            confirmation.append({"root":r["id"],"baseline_action":baseline,"selected_action":selected,
                "baseline_family":families[baseline],"selected_family":families[selected],
                "search_gain":selection["search_return_gain"],"pairs":pairs})
            atomic_json(output/"progress.json",{"phase":"independent_confirmation","roots_done":i+1,
                "roots":len(contracts),"native_units":budget.count,"seconds":perf_counter()-start,"resources":job.usage()})
        if file_hash(output/"teacher_selections.json")!=selection_sha:raise ValueError("selection_changed_after_confirmation")
        after={"Foundation":{"parameters":tensor_digest(parent.model.policy.state_dict()),"Adam":optimizer_digest(parent.model.policy)},
            "rivals":{k:{"parameters":tensor_digest(v.model.policy.state_dict()),"Adam":optimizer_digest(v.model.policy)} for k,v in rivals.items()}}
        if before!=after:raise ValueError("frozen_teacher_models_changed")
        write_new(output/"confirmation_results.json",confirmation)
        summary=summarize_confirmation(confirmation)
        result={**summary,"native_units":budget.count,"source_roots":len(contracts),
            "selection_SHA256":selection_sha,"before":before,"after":after,"seconds":perf_counter()-start,
            "resources":job.usage(),"PPO":0,"supervised_learning":0,"optimizer_updates":0,
            "evaluation_games":0,"promotion":False,"hidden_state_scope":"privileged_TRAIN_teacher_upper_bound"}
        write_new(output/"execution_complete.json",result)
        atomic_json(output/"progress.json",{"phase":"execution_complete","native_units":budget.count})
        return result
    except BaseException as error:
        write_new(output/"failure.json",{"error":repr(error),"consumed_units":budget.count if budget else 0,
            "no_automatic_restart":True,"resources":job.usage()})
        raise
    finally:
        if native is not None:native.close()
        limit.finished.set()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--source",type=Path)
    ap.add_argument("--prior",type=Path);ap.add_argument("--preflight",type=Path)
    ap.add_argument("--plan",type=Path);ap.add_argument("--output",type=Path);args=ap.parse_args()
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=12)
    enforce_local_network_only();torch.set_num_threads(1);forbid_training()
    if args.preflight:
        result=preflight(args.source,args.prior,args.preflight)
        print(json.dumps({"roots":len(result["roots"]),"candidates":sum(len(r["actions"]) for r in result["roots"]),"native":0}))
    else:
        plan=read(args.plan);plan["plan_file"]=str(args.plan)
        result=run(plan,args.output,job)
        print(json.dumps({k:result[k] for k in ("status","native_units","seconds")}))


if __name__=="__main__":main()
