"""Receipt-bound TRAIN-only collection then one offline predictor experiment.

No PPO construction/update, battle-strength evaluation or BR integration.
Run --prepare once, validate offline, then launch --owned independently.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from advisor.learned_execution_alignment import content_hash, digest, durable_json
from advisor.learned_response_predictor import (VERSION, ResponseEncoder, public_input,
    selected_label, audit_split, team_signature, frequency_predictions,
    score_predictions, make_model, model_probabilities)
from advisor.learned_difficulty_calibration import RIVALS, PublicRetryAudit, AttemptRateGuard
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, process_alive, enforce_local_network_only
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID


def utc(): return datetime.now(timezone.utc).isoformat()
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def append(p,value):
    with Path(p).open("a",encoding="utf-8") as f:
        f.write(json.dumps(value,allow_nan=False)+"\n");f.flush();os.fsync(f.fileno())


def encoder(plan):
    return ResponseEncoder(plan["catalog"],read(ROOT/"models/showdown_tactics_v1/catalog.json")["moves"],
        read(ROOT/"models/showdown_combat_priors_v3/catalog.json")["native_moves"])


def prepare(old_plan_path,output):
    from advisor.learned_training_subset import NativeTrainingSubset
    old=read(old_plan_path); out=Path(output);out.mkdir(exist_ok=False)
    subset=NativeTrainingSubset(old["training_subset"],old["training_subset_sha256"])
    teams=deepcopy(subset.teams)
    if len(teams)!=256 or len({team_signature(t) for t in teams})!=256:
        raise ValueError("requires_256_semantically_distinct_verified_train_teams")
    rng=random.Random(2026102401);rng.shuffle(teams)
    # Disjoint full-team pairs are the independent clusters, not their seven RNG replicas.
    pairs=[];cases=[]
    for pair in range(128):
        fold="train" if pair<64 else "validation" if pair<96 else "test"
        own,foe=teams[2*pair:2*pair+2]
        pairs.append({"pair":pair,"fold":fold,"teams_sha256":[content_hash(own),content_hash(foe)],
            "semantic_team_sha256":[team_signature(own),team_signature(foe)]})
        for repeat in range(7):
            index=pair*7+repeat
            scenario={"scenario_id":VERSION+":"+str(index),"teams":{"self":deepcopy(own),"opponent":deepcopy(foe)},
                "preview":{s:rng.sample(range(1,7),3) for s in ("self","opponent")},
                "seed":[rng.randrange(65536) for _ in range(4)],"history":[],
                "assumptions":["TRAIN-only paired full teams; coordinator identifiers never predictor inputs."]}
            cases.append({"index":index,"pair":pair,"fold":fold,"scenario":scenario,
                          "scenario_SHA256":__import__("advisor.learned_encoder",fromlist=["fingerprint"]).fingerprint(scenario)})
    audit_split(cases)
    # Original 10-slot mixture, integer quotas in each preassigned fold. No strength tuning.
    weights=[.1,.1,.1,.1,.1,.3,.2]; slots=[];quotas={}
    for fold in ("train","validation","test"):
        selected=[c for c in cases if c["fold"]==fold];n=len(selected)
        exact=[n*w for w in weights];counts=[int(x) for x in exact]
        for i in sorted(range(7),key=lambda i:(-(exact[i]-counts[i]),i))[:n-sum(counts)]:counts[i]+=1
        rivals=[name for name,count in zip(RIVALS,counts) for _ in range(count)]
        rng.shuffle(rivals);quotas[fold]=dict(zip(RIVALS,counts))
        for case,rival in zip(selected,rivals):
            case["rival"]=rival
            for seat in ("p1","p2"):
                slots.append({"case":case["index"],"pair":case["pair"],"fold":fold,"rival":rival,
                    "seat":seat,"scenario_sha256":case["scenario_SHA256"]})
    if len(slots)!=1792:raise ValueError("predictor_native_budget")
    durable_json(out/"cases.json",{"cases":cases,"pairs":pairs})
    p={"schema_version":VERSION,"frozen_utc":utc(),"output":str(out),"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "source_root":str(ROOT),"checkout":old["checkout"],"engine_commit":SHOWDOWN_COMMIT,"format_id":FORMAT_ID,
        "catalog":old["catalog"],"parent":old["parent"],"parent_semantic_identity":old["parent_semantic_identity"],
        "rivals":old["rivals"],"training_subset":old["training_subset"],"training_subset_sha256":old["training_subset_sha256"],
        "cases_path":str(out/"cases.json"),"slots":slots,"games":1792,"new_PPO_transitions":0,"independent_strength_games":0,
        "parent_action_mode":"argmax","rival_actions":"unchanged_argmax_neural_or_seeded_scripted",
        "team_protocol":"existing_TRAIN256_membership_random_ordered_three_disjoint_full_team_pairs_7_rng_replicas",
        "nominal_mixture":dict(zip(RIVALS,weights)),"fold_rival_case_quotas":quotas,
        "split":{"train_pairs":64,"validation_pairs":32,"test_pairs":32,"minimum_pairs_per_fold":24,
                 "minimum_rows":{"train":4000,"validation":1500,"test":1500}},
        "learner":{"seed":106024,"hidden":[128,64],"learning_rate":.0003,"batch":256,"epochs":20,
                   "early_stopping_patience":4,"weight_decay":0.,"gradient_clip":5.,"class_weights":None,
                   "temperature":"single_validation_scalar_bounded_0.5_to_5","test_uses":1},
        "statistics":{"resamples":10000,"seed":2026102402,"unit":"full_team_pair_all_replicas_rivals_seats",
            "primary":"test_case_macro_NLL_and_Brier_vs_frequency_and_public_heuristic",
            "intervals":"paired_cluster95_and_Bonferroni97.5_for_two_baselines",
            "GO":"both_metrics_improve_against_both_baselines_with_familywise_interval_and_known_move_NLL_improvement",
            "known_move_gate":{"minimum_rows":300,"minimum_team_pair_clusters":16,"paired_NLL_CI95_upper_less_than":0}},
        "resources":{"workers":1,"cpu_percent":50,"memory_mib":12288,"device":"cpu","max_runtime_seconds":3600},
        "automatic_restarts":0,"prior_calibration_plan":str(old_plan_path),"prior_calibration_plan_sha256":digest(old_plan_path)}
    e=encoder(p);p["encoder_identity"]=e.identity;p["encoder_fingerprint"]=e.fingerprint
    inputs=[p["cases_path"],p["training_subset"],p["catalog"],p["parent"]["path"],str(old_plan_path)]
    for binding in p["rivals"].values():
        if "model_path" in binding:inputs += [binding["model_path"],str(Path(binding["model_path"]).with_name("model.json"))]
    inputs += [str(Path(p["parent"]["path"]).with_name("model.json"))]
    p["immutable_files"]={path:digest(path) for path in inputs if Path(path).exists()}
    source=set(old["source_sha256"])|{"advisor/learned_response_predictor.py","scripts/run_foundation_response_predictor.py"}
    p["source_sha256"]={name:sha256((ROOT/name).read_bytes().replace(b"\r\n",b"\n")).hexdigest() for name in sorted(source)}
    durable_json(out/"plan.json",p)
    print(json.dumps({"plan":str(out/"plan.json"),"games":1792,"team_pairs":128,"quotas":quotas,"encoder_dimension":e.dimension,"outputs":len(e.outputs)},indent=2))


def verify(plan_path):
    p=read(plan_path)
    if p["schema_version"]!=VERSION or p["games"]!=1792 or p["new_PPO_transitions"]!=0 or p["parent_action_mode"]!="argmax" or p["automatic_restarts"]!=0:
        raise ValueError("predictor_frozen_contract_mismatch")
    for path,s in p["immutable_files"].items():
        if digest(path)!=s:raise ValueError("predictor_input_mutated:"+path)
    for path,s in p["source_sha256"].items():
        if sha256((ROOT/path).read_bytes().replace(b"\r\n",b"\n")).hexdigest()!=s:raise ValueError("predictor_source_mutated:"+path)
    if subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()!=p["source_commit"]:
        raise ValueError("predictor_source_commit_changed")
    if subprocess.check_output(["git","rev-parse","HEAD"],cwd=p["checkout"],text=True).strip()!=SHOWDOWN_COMMIT:
        raise ValueError("predictor_native_pin_changed")
    if subprocess.check_output(["git","status","--porcelain","--untracked-files=no"],cwd=p["checkout"],text=True).strip():
        raise ValueError("predictor_native_checkout_dirty")
    cases=read(p["cases_path"])["cases"];audit_split(cases)
    if encoder(p).fingerprint!=p["encoder_fingerprint"] or len(p["slots"])!=1792:raise ValueError("predictor_encoder_or_budget_changed")
    return p,cases


class ArgmaxRecorder:
    def __init__(self,infer):self.infer=infer;self.pending=[]
    def __call__(self,view):
        proof=self.infer(view);action=proof["action_index"]
        if action!=int(np_argmax(proof["action_probabilities"])) or not view["action_mask"][action]:
            raise ValueError("Foundation_argmax_contract")
        self.pending.append({"mode":"argmax","action":action,"revision":view["revision"],
            "mask":view["action_mask"],"public_view_sha256":content_hash(public_input(view))})
        return proof


def np_argmax(p):
    import numpy as np
    return np.argmax(p)


def audit_games(out,slots,plan_sha):
    ledger=out/"game_ledger.jsonl";events=[json.loads(s) for s in ledger.read_text().splitlines()] if ledger.exists() else []
    if len(events)%2:raise ValueError("uncertain_started_game_no_automatic_reexecution")
    if len(events)>2*len(slots):raise ValueError("predictor_native_budget_exceeded")
    rows=[]
    for i in range(len(events)//2):
        path=out/"receipts"/f"game_{i:04d}.json";a,b=events[2*i:2*i+2]
        if a!={"phase":"game_started","index":i,"slot_sha256":content_hash(slots[i])} or b!={"phase":"game_committed","index":i,"receipt_sha256":digest(path)}:
            raise ValueError("predictor_ledger_corrupt")
        row=read(path)
        if row["slot"]!=slots[i] or row["plan_sha256"]!=plan_sha or digest(row["trace"])!=row["trace_sha256"] or content_hash(row["record"])!=row["record_sha256"]:
            raise ValueError("predictor_receipt_corrupt")
        rows.append(row)
    if len(list((out/"receipts").glob("game_*.json")))!=len(rows):raise ValueError("unledgered_predictor_receipt")
    return rows


def collect(plan_path,job,limit,resume):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest
    from scripts.run_foundation_parent_anchor_study import checkpoint_integrity,FrozenCase
    from scripts.run_foundation_difficulty_calibration import compact_view
    from scripts.evaluate_showdown_policy import evaluate
    p,cases=verify(plan_path);out=Path(p["output"]);plan_sha=digest(plan_path)
    for d in ("receipts","traces"): (out/d).mkdir(exist_ok=True)
    rows=audit_games(out,p["slots"],plan_sha)
    if rows and not resume:raise ValueError("predictor_existing_games_require_explicit_resume")
    if (out/"collection_complete.json").exists():return
    torch.set_num_threads(1)
    proof=checkpoint_integrity(p["parent"]["path"],p["parent"]["sha256"],32768)
    player=LearnedPolicy(p["parent"]["path"],p["catalog"],expected_model_id=p["parent"]["sha256"])
    identity=lambda:{"parameters":tensor_digest(player.model.policy.state_dict()),"Adam":optimizer_digest(player.model.policy)}
    before=identity()
    if before!=p["parent_semantic_identity"]:raise ValueError("predictor_parent_identity")
    if not (out/"initial_identity.json").exists():durable_json(out/"initial_identity.json",{"parent":proof,**before})
    rivals={name:name if "model_path" not in b else LearnedPolicy(b["model_path"],p["catalog"],expected_model_id=b["model_SHA256"]) for name,b in p["rivals"].items()}
    frozen={name:tensor_digest(v.model.policy.state_dict()) for name,v in rivals.items() if not isinstance(v,str)}
    lookup={c["index"]:c for c in cases};guard=AttemptRateGuard();start=time.monotonic();initial=len(rows)
    for i in range(initial,len(p["slots"])):
        if limit.stopping():raise TimeoutError("predictor_STOP_or_deadline_before_next_game")
        slot=p["slots"][i]; recorder=ArgmaxRecorder(player.infer);audit=PublicRetryAudit(slot["case"])
        trace=out/"traces"/f"game_{i:04d}.jsonl.gz"
        append(out/"game_ledger.jsonl",{"phase":"game_started","index":i,"slot_sha256":content_hash(slot)})
        original=player.infer;began=time.monotonic()
        with trace.open("xb") as raw:
            with gzip.GzipFile(fileobj=raw,mode="wb",mtime=0) as f:
                def observe(event):
                    if len(recorder.pending)!=1:raise ValueError("predictor_argmax_transition_join")
                    row={"ordinal":audit.steps,"target_choice":recorder.pending.pop(),"actions":event["actions"],"result":event["result"],
                        "before":{s:compact_view(v) for s,v in event["before"].items()},"after":{s:compact_view(v) for s,v in event["after"].items()}}
                    if audit.steps==0:row["initial_public_views"]=event["before"]
                    try:audit.observe(event);guard.observe(event["result"]["action_rejected"])
                    except BaseException as err:
                        row["audit_error"]=str(err);f.write((json.dumps(row,allow_nan=False)+"\n").encode());f.flush();raise
                    f.write((json.dumps(row,allow_nan=False)+"\n").encode())
                    if limit.stopping():raise TimeoutError("predictor_STOP_or_deadline_active_game_no_replay")
                player.infer=recorder
                try:
                    result=evaluate(p["checkout"],p["catalog"],{"Foundation_argmax":player},split="validation",cases=1,offset=slot["case"],
                        curriculum_version="showdown-learning-curriculum-v8",rivals={slot["rival"]:rivals[slot["rival"]]},
                        case_provider=FrozenCase(lookup[slot["case"]],plan_sha),candidate_seat=slot["seat"],
                        transition_observer=observe,stopping=limit.stopping)
                finally:player.infer=original
            raw.flush();os.fsync(raw.fileno())
        record=result["records"][0]
        if record["canonical_scenario_sha256"]!=slot["scenario_sha256"] or record["native_choice_rejections"]!=audit.rejections or record["decisions"]!=audit.steps or recorder.pending:
            raise ValueError("predictor_native_receipt_binding")
        receipt={"slot":slot,"plan_sha256":plan_sha,"trace":str(trace),"trace_sha256":digest(trace),"record":record,
            "record_sha256":content_hash(record),"wall_seconds":time.monotonic()-began,"retry_statistics":audit.monitor.statistics()}
        path=out/"receipts"/f"game_{i:04d}.json";durable_json(path,receipt)
        append(out/"game_ledger.jsonl",{"phase":"game_committed","index":i,"receipt_sha256":digest(path)})
        rows.append(receipt)
        if len(rows)%8==0:
            atomic_json(out/"status.json",{"phase":"collection","pid":os.getpid(),"utc":utc(),"games":len(rows),"target":1792,
                "games_per_second":(len(rows)-initial)/max(1,time.monotonic()-start),"wall_seconds":time.monotonic()-start,"resources":job.usage()})
    audited=audit_games(out,p["slots"],plan_sha)
    if len(audited)!=1792 or before!=identity() or frozen!={name:tensor_digest(v.model.policy.state_dict()) for name,v in rivals.items() if not isinstance(v,str)}:
        raise ValueError("predictor_collection_or_frozen_identity")
    verify(plan_path)
    durable_json(out/"collection_complete.json",{"games":1792,"new_PPO":0,"new_strength_evaluations":0,"parent_before":before,"parent_after":identity(),
        "native_rejections":sum(r["record"]["native_choice_rejections"] for r in rows),"truncations":sum(r["record"]["truncated"] for r in rows),
        "utc":utc(),"wall_seconds":time.monotonic()-start,"resources":job.usage()})


def build_dataset(p):
    import numpy as np
    from advisor.showdown_observation import project_policy_observation
    out=Path(p["output"]);e=encoder(p);lookup={c["index"]:c for c in read(p["cases_path"])["cases"]}
    rows=audit_games(out,p["slots"],digest(out/"plan.json"));xs=[];supports=[];labels=[];heuristics=[];meta=[];excluded=Counter();hashes=0;encoding_times=[]
    for game,r in enumerate(rows):
        slot=r["slot"];target_side="self" if slot["seat"]=="p1" else "opponent";observer_side="opponent" if target_side=="self" else "self";hist={}
        with gzip.open(r["trace"],"rt",encoding="utf-8") as stream:
            for ordinal,line in enumerate(stream):
                row=json.loads(line)
                if row["ordinal"]!=ordinal:raise ValueError("predictor_trace_ordinal")
                if ordinal==0:hist={s:list(v["public_history"]) for s,v in row["initial_public_views"].items()}
                full={}
                for side,v in row["before"].items():
                    full[side]=project_policy_observation(v,hist[side])
                    if content_hash(hist[side])!=v["public_history_sha256"] or content_hash(full[side]["state"])!=v["state_sha256"]:raise ValueError("predictor_before_digest")
                    hashes+=2
                target,observer=full[target_side],full[observer_side];choice=row["target_choice"];action=row["actions"][target_side]
                if choice!={"mode":"argmax","action":action,"revision":target["revision"],"mask":target["action_mask"],"public_view_sha256":content_hash(public_input(target))}:
                    raise ValueError("predictor_target_argmax_join")
                label,reason=selected_label(observer,target,action,row["result"],e.tactics,e.native)
                if reason:excluded[reason]+=1
                else:
                    encoding_started=time.perf_counter();x,support=e.encode(observer)
                    if len(encoding_times)<1000:encoding_times.append(time.perf_counter()-encoding_started)
                    y=e.output_index[label["semantic"]]
                    if not support[y]:raise ValueError("predictor_label_outside_PUBLIC_support")
                    xs.append(x);supports.append(support);labels.append(y);heuristics.append(e.heuristic(observer))
                    foe=active_public_local(observer)
                    meta.append({"game":game,"ordinal":ordinal,"pair":slot["pair"],"case":slot["case"],"fold":slot["fold"],"rival":slot["rival"],"seat":slot["seat"],
                        "input_sha256":content_hash(public_input(observer)),"family":label["family"],"semantic":label["semantic"],
                        "ability_unknown":isinstance(foe.get("current_ability",{}),dict),"item_unknown":isinstance(foe.get("known_item",{}),dict),
                        "public_known_move_count":len(foe.get("known_moves",[]))})
                for side,v in row["after"].items():
                    hist[side].extend(v["events"])
                    if content_hash(hist[side])!=v["public_history_sha256"] or content_hash(project_policy_observation(v,hist[side])["state"])!=v["state_sha256"]:raise ValueError("predictor_after_digest")
                    hashes+=2
    X=np.asarray(xs,np.float32);S=np.asarray(supports,bool);Y=np.asarray(labels,np.int64);H=np.asarray(heuristics,np.float32)
    fold_indices={f:np.asarray([i for i,m in enumerate(meta) if m["fold"]==f]) for f in ("train","validation","test")}
    # Identical feature states across folds are audited, not silently deleted.
    owners={};overlap=Counter()
    for m in meta:
        key=m["input_sha256"]
        if key in owners and owners[key]!=m["fold"]:overlap["public_input_cross_fold"]+=1
        owners[key]=m["fold"]
    for f,ix in fold_indices.items():
        if len(ix)<p["split"]["minimum_rows"][f] or len({meta[i]["pair"] for i in ix})<24:raise ValueError("predictor_insufficient_independent_data:"+f)
    if overlap:raise ValueError("predictor_cross_fold_public_input_leak")
    summary={"rows":len(meta),"excluded":dict(excluded),"verified_original_digests":hashes,"folds":{},"cross_fold_identical_public_inputs":dict(overlap),
        "encoder_ms":{"samples":len(encoding_times),"median":float(np.median(encoding_times)*1000),"p95":float(np.quantile(encoding_times,.95)*1000)}}
    for f,ix in fold_indices.items():
        summary["folds"][f]={"rows":len(ix),"team_pair_clusters":len({meta[i]["pair"] for i in ix}),"battles":len({meta[i]["game"] for i in ix}),
            "families":dict(Counter(meta[i]["family"] for i in ix)),"rivals":dict(Counter(meta[i]["rival"] for i in ix)),"seats":dict(Counter(meta[i]["seat"] for i in ix)),
            "known_selected_moves":sum(meta[i]["semantic"].startswith("known:") for i in ix)}
    # Single-purpose offline artifacts; no model/Adam or native input overwritten.
    np.savez_compressed(out/"dataset.npz",X=X,S=S,Y=Y,H=H)
    with gzip.open(out/"rows.jsonl.gz","wt",encoding="utf-8") as f:
        for row in meta:f.write(json.dumps(row)+"\n")
    durable_json(out/"data_audit.json",{**summary,"dataset_sha256":digest(out/"dataset.npz"),"rows_sha256":digest(out/"rows.jsonl.gz"),"encoder":e.identity})
    return X,S,Y,H,meta,fold_indices,e


def active_public_local(view):
    side=view["state"]["opponent_side"]
    return side["pokemon"].get(side["active_identity"],{})


def fit_and_test(plan_path,job,limit):
    import numpy as np
    import torch
    p,_=verify(plan_path);out=Path(p["output"])
    if (out/"test_started.json").exists():raise ValueError("final_test_already_opened_no_automatic_refit_or_retest")
    if (out/"fit_started.json").exists():raise ValueError("interrupted_fit_requires_explicit_checkpoint_audit_no_automatic_refit")
    X,S,Y,H,meta,ix,e=build_dataset(p)
    # Test labels remain unused until the immutable final test receipt below.
    cfg=p["learner"];torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.manual_seed(cfg["seed"])
    tr,va,te=(ix[f] for f in ("train","validation","test"));mean=X[tr].mean(0);scale=X[tr].std(0);scale[scale<1.]=1.
    X=(X-mean)/scale;tx=torch.from_numpy(X);ts=torch.from_numpy(S);ty=torch.from_numpy(Y)
    model=make_model(e.dimension,len(e.outputs));opt=torch.optim.Adam(model.parameters(),lr=cfg["learning_rate"],weight_decay=cfg["weight_decay"])
    start=time.monotonic();g=torch.Generator().manual_seed(cfg["seed"]+1);updates=0;best=float("inf");bad=0;curve=[]
    durable_json(out/"fit_started.json",{"utc":utc(),"plan_sha256":digest(plan_path),"dataset_sha256":digest(out/"dataset.npz"),"parameter_count":sum(v.numel() for v in model.parameters()),"fresh_Adam":True})
    def checkpoint(name,epoch):
        torch.save({"model":model.state_dict(),"optimizer":opt.state_dict(),"epoch":epoch,"updates":updates,
            "torch_rng":torch.get_rng_state(),"shuffle_rng":g.get_state(),"mean":mean,"scale":scale,
            "encoder_fingerprint":e.fingerprint,"outputs":e.outputs,"plan_sha256":digest(plan_path)},out/name)
    checkpoint("predictor_initial.pt",0)
    gradient_norms=[]
    for epoch in range(cfg["epochs"]):
        if limit.stopping():raise TimeoutError("predictor_fit_STOP_or_deadline")
        model.train();order=tr[torch.randperm(len(tr),generator=g).numpy()];total=0.
        for batch in range(0,len(order),cfg["batch"]):
            ids=order[batch:batch+cfg["batch"]];opt.zero_grad(set_to_none=True)
            logits=model(tx[ids]).masked_fill(~ts[ids],-1e9);loss=torch.nn.functional.cross_entropy(logits,ty[ids])
            if not torch.isfinite(loss):raise ValueError("nonfinite_predictor_loss")
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),cfg["gradient_clip"],error_if_nonfinite=True)
            opt.step();updates+=1;gradient_norms.append(float(norm.detach()));total+=float(loss.detach())*len(ids)
        model.eval()
        with torch.no_grad():v=float(torch.nn.functional.cross_entropy(model(tx[va]).masked_fill(~ts[va],-1e9),ty[va]))
        curve.append({"epoch":epoch+1,"updates":updates,"train_nll":total/len(tr),"validation_nll":v})
        checkpoint("predictor_resume.pt",epoch+1)
        if v<best-1e-5:best=v;bad=0;checkpoint("predictor_best_validation.pt",epoch+1)
        else:bad+=1
        atomic_json(out/"status.json",{"phase":"offline_fit","epoch":epoch+1,"updates":updates,"utc":utc(),"resources":job.usage()})
        if bad>=cfg["early_stopping_patience"]:break
    chosen=torch.load(out/"predictor_best_validation.pt",map_location="cpu",weights_only=False);model.load_state_dict(chosen["model"]);model.eval()
    # Exactly one validation-only scalar calibration, no coefficient/model search.
    with torch.no_grad():val_logits=model(tx[va]).detach()
    scalar=torch.tensor(0.,requires_grad=True);temperature_opt=torch.optim.LBFGS([scalar],lr=.3,max_iter=40,line_search_fn="strong_wolfe")
    def calibrate():
        temperature_opt.zero_grad();temperature=.5+4.5*torch.sigmoid(scalar)
        loss=torch.nn.functional.cross_entropy((val_logits/temperature).masked_fill(~ts[va],-1e9),ty[va]);loss.backward();return loss
    temperature_opt.step(calibrate);temperature=float((.5+4.5*torch.sigmoid(scalar)).detach())
    model_binding={"schema_version":VERSION,"encoder_fingerprint":e.fingerprint,"outputs":e.outputs,"temperature":temperature,
        "parameter_count":sum(v.numel() for v in model.parameters()),"chosen_epoch":chosen["epoch"],"optimizer_updates":updates,
        "checkpoint_sha256":digest(out/"predictor_best_validation.pt"),"plan_sha256":digest(plan_path),
        "runtime_scope":"offline_observer_public_only_not_BR_connected","training_mode":"Foundation_argmax_labels"}
    durable_json(out/"predictor.json",model_binding)
    # Restart numerical equality, including the actual optimizer state.
    clone=make_model(e.dimension,len(e.outputs));clone.load_state_dict(chosen["model"])
    clone_opt=torch.optim.Adam(clone.parameters(),lr=cfg["learning_rate"]);clone_opt.load_state_dict(chosen["optimizer"])
    with torch.no_grad():
        equal=torch.equal(model(tx[va[:64]]),clone(tx[va[:64]]))
    if not equal:raise ValueError("predictor_reload_output_mismatch")
    durable_json(out/"fit_complete.json",{"curve":curve,"gradient_norms":{"min":min(gradient_norms),"max":max(gradient_norms)},
        "updates":updates,"chosen_updates":chosen["updates"],"reload_logits_bit_equal":equal,"optimizer_state_reloaded":True,
        "temperature":temperature,"wall_seconds":time.monotonic()-start,"resources":job.usage()})
    durable_json(out/"test_started.json",{"utc":utc(),"frozen_predictor_sha256":digest(out/"predictor.json"),"dataset_sha256":digest(out/"dataset.npz"),"test_use":1})
    with torch.no_grad():learned=model_probabilities(model,tx[te],ts[te],temperature).numpy()
    frequency=frequency_predictions(Y[tr],S[te],len(e.outputs));predictions={"frequency":frequency,"public_heuristic":H[te],"predictor":learned}
    scores={};details={};groups=np.asarray([meta[i]["pair"] for i in te]);clusters=sorted(set(groups))
    for name,probs in predictions.items():scores[name],details[name]=score_predictions(probs,Y[te],e.family_index)
    rng=np.random.default_rng(p["statistics"]["seed"]);draws=rng.integers(0,len(clusters),(p["statistics"]["resamples"],len(clusters)))
    paired={}
    for base in ("frequency","public_heuristic"):
        paired[base]={}
        for metric in ("nll","brier","top1"):
            per=np.asarray([(details["predictor"][metric][groups==c]-details[base][metric][groups==c]).mean() for c in clusters])
            boot=per[draws].mean(1)
            paired[base][metric]={"predictor_minus_baseline_cluster_macro":float(per.mean()),"CI95":np.quantile(boot,[.025,.975]).tolist(),"CI97_5":np.quantile(boot,[.0125,.9875]).tolist()}
    strata={}
    for field in ("rival","seat","ability_unknown","item_unknown"):
        strata[field]={}
        for value in sorted({str(meta[i][field]) for i in te}):
            ids=np.asarray([j for j,i in enumerate(te) if str(meta[i][field])==value])
            strata[field][value]={name:score_predictions(probs[ids],Y[te][ids],e.family_index)[0] for name,probs in predictions.items()}
    for scope,selected in (("known_move",[j for j,i in enumerate(te) if meta[i]["semantic"].startswith("known:")]),("unknown_move",[j for j,i in enumerate(te) if meta[i]["semantic"].startswith("unknown:")])):
        if selected:strata[scope]={name:score_predictions(probs[selected],Y[te][selected],e.family_index)[0] for name,probs in predictions.items()}
    # Inference benchmark uses only already consumed validation rows.
    times=[]
    with torch.no_grad():
        for _ in range(200):
            t=time.perf_counter();model_probabilities(model,tx[va[:1]],ts[va[:1]],temperature);times.append(time.perf_counter()-t)
    known=np.asarray([meta[i]["semantic"].startswith("known:") for i in te]);known_clusters=sorted(set(groups[known]));known_paired={}
    if known_clusters:
        kd=rng.integers(0,len(known_clusters),(p["statistics"]["resamples"],len(known_clusters)))
        for base in ("frequency","public_heuristic"):
            diff=details["predictor"]["nll"]-details[base]["nll"]
            per=np.asarray([diff[known&(groups==c)].mean() for c in known_clusters])
            known_paired[base]={"cluster_macro_difference":float(per.mean()),"CI95":np.quantile(per[kd].mean(1),[.025,.975]).tolist()}
    known_gate=bool(int(known.sum())>=300 and len(known_clusters)>=16 and all(v["CI95"][1]<0 for v in known_paired.values()))
    probabilistic_go=known_gate and all(paired[b][m]["CI97_5"][1]<0 for b in paired for m in ("nll","brier"))
    verdict="GO" if probabilistic_go else "CONDITIONAL GO" if any(paired[b]["nll"]["CI95"][1]<0 for b in paired) else "NO-GO"
    result={"verdict":verdict,"test_rows":len(te),"test_full_team_pair_clusters":len(clusters),"scores":scores,"paired":paired,"strata":strata,
        "known_move_gate":{"passed":bool(known_gate),"rows":int(known.sum()),"team_pair_clusters":len(known_clusters),"paired":known_paired},
        "training_action_family_counts":dict(Counter(meta[i]["family"] for i in tr)),
        "inference_network_ms":{"median":float(np.median(times)*1000),"p95":float(np.quantile(times,.95)*1000)},
        "not_battle_strength_evidence":True,"new_PPO":0,"new_independent_strength_games":0,"BR_integration":False}
    np.savez_compressed(out/"test_predictions.npz",Y=Y[te],groups=groups,**predictions)
    durable_json(out/"test_complete.json",result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--prepare",type=Path);parser.add_argument("--output",type=Path)
    parser.add_argument("--plan",type=Path);parser.add_argument("--owned",action="store_true");parser.add_argument("--resume",action="store_true");args=parser.parse_args()
    if args.prepare:prepare(args.prepare,args.output);return
    p,_=verify(args.plan);out=Path(p["output"])
    if not args.owned:raise ValueError("predictor_detached_owned_process_required")
    if (out/"control.json").exists() and process_alive(read(out/"control.json")["pid"]):raise ValueError("predictor_owner_already_alive")
    if any((out/f).exists() for f in ("failure.json","STOP","watchdog.json","execution_complete.json")):raise ValueError("predictor_existing_failure_STOP_or_completion")
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=12)
    if job.inherited_job:raise ValueError("predictor_owner_inherited_terminal_job")
    network=enforce_local_network_only();limit=RuntimeLimit(out,3600)
    atomic_json(out/"control.json",{"pid":os.getpid(),"parent_pid":os.getppid(),"utc":utc(),"plan_sha256":digest(args.plan),"own_job":True,"inherited_job":False,"automatic_restarts":0,"resources":p["resources"]})
    started=time.monotonic()
    try:
        collect(args.plan,job,limit,args.resume)
        result=fit_and_test(args.plan,job,limit)
        verify(args.plan)
        durable_json(out/"execution_complete.json",{"status":"complete_pending_independent_audit","utc":utc(),"native_games":1792,"new_PPO":0,
            "verdict":result["verdict"],"test_sha256":digest(out/"test_complete.json"),"wall_seconds":time.monotonic()-started,"resources":job.usage(),"network":network})
        atomic_json(out/"status.json",{"phase":"complete_pending_independent_audit","utc":utc(),"games":1792,"test_complete":True})
    except BaseException as err:
        import traceback
        atomic_json(out/"failure.json",{"utc":utc(),"type":type(err).__name__,"message":str(err),"traceback":traceback.format_exc(),"no_automatic_restart":True,"resources":job.usage()})
        raise
    finally:limit.finished.set()


if __name__=="__main__":main()
