"""One hierarchy, old TRAIN/validation development, fresh TRAIN-source test.

Fit and freeze BEFORE collecting test outcomes. The shared native collector is
receipt-bound; all1024 games are data collection, not a battle-strength study.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
import gzip,json,os,random,subprocess,sys,time
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from advisor.learned_execution_alignment import digest,content_hash,durable_json
from advisor.learned_encoder import fingerprint
from advisor.learned_response_predictor import team_signature,score_predictions,make_model,model_probabilities,LABEL_VERSION
from advisor.learned_hierarchical_response import VERSION,MetadataEncoder,HierarchicalResponseModel
from advisor.learned_difficulty_calibration import RIVALS
from advisor.learning_resources import WindowsJob,RuntimeLimit,atomic_json,enforce_local_network_only,process_alive
from advisor.showdown_bridge import SHOWDOWN_COMMIT,FORMAT_ID
from scripts.run_foundation_response_predictor import encoder as public_encoder,collect,build_dataset


def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def utc():return datetime.now(timezone.utc).isoformat()
def metadata_encoder(p):return MetadataEncoder(public_encoder(p))


def joint_signature(team):
    return fingerprint(sorted([{"species":m["species"],"moves":sorted(m["moves"])}for m in team],key=fingerprint))


def verify_partition(cases,old_teams):
    forbidden={team_signature(t)for t in old_teams};forbidden_joint={joint_signature(t)for t in old_teams}
    owners={};joint_owners={};seeds=set();pairs={};indices=set()
    for c in cases:
        pair=c["pair"]
        if c["fold"]!="test" or c["index"]in indices:raise ValueError("hierarchical_test_case_identity")
        indices.add(c["index"])
        seed=tuple(c["scenario"]["seed"])
        if seed in seeds:raise ValueError("hierarchical_repeated_test_native_seed")
        seeds.add(seed)
        pair_teams=[]
        for t in c["scenario"]["teams"].values():
            h=team_signature(t);j=joint_signature(t);pair_teams.append(h)
            if h in forbidden or j in forbidden_joint:raise ValueError("hierarchical_development_team_leak")
            if h in owners and owners[h]!=pair or j in joint_owners and joint_owners[j]!=pair:
                raise ValueError("hierarchical_test_team_cluster_overlap")
            owners[h]=joint_owners[j]=pair
        if pair in pairs and pairs[pair]!=pair_teams:raise ValueError("hierarchical_pair_changed_teams")
        pairs[pair]=pair_teams
    if len(cases)!=512 or len(pairs)!=64 or len(owners)!=128:raise ValueError("hierarchical_test_independence_budget")
    return {"cases":512,"team_pairs":64,"full_teams":128,"full_and_joint_team_overlap_with_previous256":0,"initial_native_seeds":len(seeds)}


def prepare(previous_plan,output):
    from advisor.learned_full_roster import load_bank,study_identity,BANK
    from advisor.learned_training_subset import NativeTrainingSubset
    old=read(previous_plan);out=Path(output);out.mkdir(exist_ok=False)
    old_out=Path(old["output"]);dataset_audit=read(old_out/"data_audit.json")
    if digest(old_out/"dataset.npz")!=dataset_audit["dataset_sha256"]:raise ValueError("development_dataset_SHA")
    with gzip.open(old_out/"rows.jsonl.gz","rt",encoding="utf-8")as f:old_meta=[json.loads(s)for s in f]
    if digest(old_out/"rows.jsonl.gz")!=dataset_audit["rows_sha256"]:raise ValueError("development_row_SHA")
    selected=np.asarray([i for i,m in enumerate(old_meta)if m["fold"]in("train","validation")])
    z=np.load(old_out/"dataset.npz",allow_pickle=False)
    np.savez_compressed(out/"development.npz",X=z["X"][selected],S=z["S"][selected],Y=z["Y"][selected])
    dev_meta=[{**old_meta[i],"original_row":int(i)}for i in selected]
    durable_json(out/"development_rows.json",dev_meta)
    if Counter(m["fold"]for m in dev_meta)!={"train":9983,"validation":4585}:raise ValueError("development_train_validation_contract")
    subset=NativeTrainingSubset(old["training_subset"],old["training_subset_sha256"])
    excluded={team_signature(t)for t in subset.teams};excluded_joint={joint_signature(t)for t in subset.teams}
    train_bank=load_bank()["teams"]["train"];eligible=[i for i,t in enumerate(train_bank)if team_signature(t)not in excluded and joint_signature(t)not in excluded_joint]
    rng=random.Random(2026102412);rng.shuffle(eligible);chosen=[];used=set();used_joint=set()
    for i in eligible:
        t=train_bank[i];h=team_signature(t);j=joint_signature(t)
        if h not in used and j not in used_joint:chosen.append(i);used.add(h);used_joint.add(j)
        if len(chosen)==128:break
    if len(chosen)!=128:raise ValueError("insufficient_independent_TRAIN_teams")
    old_cases=read(old["cases_path"])["cases"];previous_seeds={tuple(c["scenario"]["seed"])for c in old_cases};cases=[]
    for pair in range(64):
        for replica in range(8):
            seed=[rng.randrange(65536)for _ in range(4)]
            while tuple(seed)in previous_seeds:seed=[rng.randrange(65536)for _ in range(4)]
            previous_seeds.add(tuple(seed));index=531000000+pair*8+replica
            scenario={"scenario_id":VERSION+f":sealed_predictor_test:{pair}:{replica}",
                "teams":{s:deepcopy(train_bank[chosen[pair*2+k]])for k,s in enumerate(("self","opponent"))},
                "preview":{s:rng.sample(range(1,7),3)for s in("self","opponent")},"seed":seed,"history":[],
                "assumptions":["TRAIN partition source only; new predictor test; not combat sealed-test assets; coordinator only."]}
            cases.append({"index":index,"pair":pair,"fold":"test","scenario":scenario,"scenario_SHA256":fingerprint(scenario)})
    partition=verify_partition(cases,subset.teams)
    quota=[51,51,51,51,51,154,103];rivals=[name for name,n in zip(RIVALS,quota)for _ in range(n)];rng.shuffle(rivals);slots=[]
    for c,rival in zip(cases,rivals):
        c["rival"]=rival
        for seat in("p1","p2"):slots.append({"case":c["index"],"pair":c["pair"],"fold":"test","rival":rival,"seat":seat,"scenario_sha256":c["scenario_SHA256"]})
    durable_json(out/"cases.json",{"cases":cases,"partition":partition,"train_bank_indices":chosen,"excluded_previous256":old["training_subset_sha256"],"source_bank_sha256":study_identity()["bank_sha256"]})
    p={k:deepcopy(old[k])for k in("checkout","catalog","parent","parent_semantic_identity","rivals","training_subset","training_subset_sha256")}
    p.update(schema_version=VERSION,frozen_utc=utc(),source_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),source_root=str(ROOT),output=str(out),
        engine_commit=SHOWDOWN_COMMIT,format_id=FORMAT_ID,previous_plan=str(previous_plan),previous_output=str(old_out),
        cases_path=str(out/"cases.json"),slots=slots,games=1024,new_PPO_transitions=0,parent_action_mode="argmax",automatic_restarts=0,
        nominal_mixture={name:old["rivals"][name]["nominal_probability"]for name in RIVALS},actual_rival_case_quota=dict(zip(RIVALS,quota)),
        split={"minimum_rows":{"test":4000},"minimum_pairs_per_fold":48},
        learner={"seed":106124,"learning_rate":.0003,"batch":256,"epochs":20,"patience":4,"gradient_clip":5.,"weight_decay":0.,"class_weights":None,
                 "architecture":"context128_64_family6_shared_candidate64_1_no_move_ID_params","temperature":"one_global_scalar_validation_only_0.5_to_5"},
        statistics={"seed":2026102413,"resamples":10000,"primary":"paired_team_pair_macro_NLL_hierarchical_minus_flat_and_heuristic",
            "GO":{"primary_NLL_two_baselines_CI97_5_upper_lt":0,"cold_known_min_rows":100,"cold_known_min_pairs":16,
                  "cold_known_top1_minus_flat_CI95_lower_gt":0,"overall_Brier_point_not_worse_than_either_baseline":True,"overall_top1_point_not_worse_than_either_baseline":True,
                  "cold_known_Brier_point_not_worse_than_flat":True,"validation_inference_median_ms_max":5},
            "no_generalization_signal":"NO_GO_if_cold_known_top1_point_not_better_or_cold_NLL_not_better_than_flat",
            "no_automatic_expansion":True},
        resources={"workers":1,"cpu_percent":50,"memory_mib":12288,"device":"cpu","max_runtime_seconds":3600},
        label_contract={"version":LABEL_VERSION,"actual_argmax_selection":"original_selected_not_executed","private_target_mask":"label_authentication_only"},
        flat_model_path=str(old_out/"predictor_best_validation.pt"),flat_metadata_path=str(old_out/"predictor.json"))
    enc=metadata_encoder(p);p["encoder_identity"]=enc.identity;p["encoder_fingerprint"]=enc.fingerprint;p["public_encoder_fingerprint"]=enc.public.fingerprint
    paths=[str(previous_plan),str(old_out/"dataset.npz"),str(old_out/"rows.jsonl.gz"),p["flat_model_path"],p["flat_metadata_path"],str(out/"development.npz"),str(out/"development_rows.json"),str(out/"cases.json"),str(BANK/"teams.json.gz"),str(BANK/"manifest.json")]
    p["immutable_files"]={**old["immutable_files"],**{f:digest(f)for f in paths}}
    source=set(old["source_sha256"])|{"advisor/learned_hierarchical_response.py","scripts/run_foundation_hierarchical_response.py"}
    p["source_sha256"]={f:sha256((ROOT/f).read_bytes().replace(b"\r\n",b"\n")).hexdigest()for f in sorted(source)}
    durable_json(out/"plan.json",p)
    print(json.dumps({"plan":str(out/"plan.json"),"games":1024,"partition":partition,"eligible_train_teams":len(eligible),"context_dim":enc.dimension,"metadata_width":enc.metadata.shape[1]}))


def verify(path):
    from advisor.learned_training_subset import NativeTrainingSubset
    p=read(path)
    if p["schema_version"]!=VERSION or p["games"]!=1024 or len(p["slots"])!=1024 or p["new_PPO_transitions"]!=0 or p["parent_action_mode"]!="argmax":raise ValueError("hierarchical_contract_mismatch")
    for f,h in p["immutable_files"].items():
        if digest(f)!=h:raise ValueError("hierarchical_input_mutated:"+f)
    for f,h in p["source_sha256"].items():
        if sha256((ROOT/f).read_bytes().replace(b"\r\n",b"\n")).hexdigest()!=h:raise ValueError("hierarchical_source_mutated:"+f)
    if subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()!=p["source_commit"]:raise ValueError("hierarchical_source_commit_mismatch")
    if subprocess.check_output(["git","rev-parse","HEAD"],cwd=p["checkout"],text=True).strip()!=SHOWDOWN_COMMIT or subprocess.check_output(["git","status","--porcelain","--untracked-files=no"],cwd=p["checkout"],text=True).strip():raise ValueError("hierarchical_native_pin_or_dirty")
    cases=read(p["cases_path"])["cases"];old=NativeTrainingSubset(p["training_subset"],p["training_subset_sha256"]);verify_partition(cases,old.teams)
    enc=metadata_encoder(p)
    if enc.fingerprint!=p["encoder_fingerprint"] or enc.public.fingerprint!=p["public_encoder_fingerprint"]:raise ValueError("hierarchical_feature_contract")
    flat=read(p["flat_metadata_path"])
    if digest(p["flat_model_path"])!=flat["checkpoint_sha256"] or flat["encoder_fingerprint"]!=enc.public.fingerprint:raise ValueError("hierarchical_flat_baseline_identity")
    return p,cases


def fit(p,job,limit):
    out=Path(p["output"])
    if (out/"fit_started.json").exists():raise ValueError("hierarchical_fit_already_started_no_refit")
    cfg=p["learner"];enc=metadata_encoder(p);z=np.load(out/"development.npz",allow_pickle=False);raw=z["X"];S=z["S"];Y=z["Y"];meta=read(out/"development_rows.json")
    train=np.asarray([i for i,m in enumerate(meta)if m["fold"]=="train"]);val=np.asarray([i for i,m in enumerate(meta)if m["fold"]=="validation"])
    if len(train)!=9983 or len(val)!=4585 or len(meta)!=14568:raise ValueError("hierarchical_development_membership")
    context=enc.context(raw,S);mean=context[train].mean(0);scale=context[train].std(0);scale[scale<1]=1
    x=torch.from_numpy((context-mean)/scale);s=torch.from_numpy(S);y=torch.from_numpy(Y);torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.manual_seed(cfg["seed"])
    model=HierarchicalResponseModel(enc);opt=torch.optim.Adam(model.parameters(),lr=cfg["learning_rate"],weight_decay=cfg["weight_decay"]);g=torch.Generator().manual_seed(cfg["seed"]+1)
    start=time.monotonic();updates=0;best=float("inf");bad=0;curve=[];norms=[]
    durable_json(out/"fit_started.json",{"utc":utc(),"plan_sha256":digest(out/"plan.json"),"development_sha256":digest(out/"development.npz"),"new_test_used":False,"fresh_Adam":True})
    def save(name,epoch):torch.save({"model":model.state_dict(),"optimizer":opt.state_dict(),"epoch":epoch,"updates":updates,"mean":mean,"scale":scale,
        "RNG":torch.get_rng_state(),"shuffle_RNG":g.get_state(),"encoder_fingerprint":enc.fingerprint,"plan_sha256":digest(out/"plan.json")},out/name)
    save("hierarchical_initial.pt",0)
    for epoch in range(cfg["epochs"]):
        if limit.stopping():raise TimeoutError("hierarchical_fit_STOP_or_limit")
        order=train[torch.randperm(len(train),generator=g).numpy()];total=0.
        for b in range(0,len(order),cfg["batch"]):
            ids=order[b:b+cfg["batch"]];opt.zero_grad(set_to_none=True);lp=model(x[ids],s[ids]);loss=-lp[torch.arange(len(ids)),y[ids]].mean()
            if not torch.isfinite(loss):raise ValueError("nonfinite_hierarchical_loss")
            loss.backward();n=torch.nn.utils.clip_grad_norm_(model.parameters(),cfg["gradient_clip"],error_if_nonfinite=True);opt.step();norms.append(float(n.detach()));updates+=1;total+=float(loss.detach())*len(ids)
        with torch.no_grad():v=float(-model(x[val],s[val])[torch.arange(len(val)),y[val]].mean())
        curve.append({"epoch":epoch+1,"updates":updates,"train_NLL":total/len(train),"validation_NLL":v});save("hierarchical_resume.pt",epoch+1)
        if v<best-1e-5:best=v;bad=0;save("hierarchical_best.pt",epoch+1)
        else:bad+=1
        if bad>=cfg["patience"]:break
    chosen=torch.load(out/"hierarchical_best.pt",map_location="cpu",weights_only=False);model.load_state_dict(chosen["model"]);model.eval()
    with torch.no_grad():lp=model(x[val],s[val]).detach().masked_fill(~s[val],0.)
    scalar=torch.tensor(0.,requires_grad=True);cal=torch.optim.LBFGS([scalar],lr=.3,max_iter=40,line_search_fn="strong_wolfe")
    def closure():
        cal.zero_grad();temp=.5+4.5*torch.sigmoid(scalar);logp=torch.log_softmax((lp/temp).masked_fill(~s[val],-1e9),-1)
        loss=-logp[torch.arange(len(val)),y[val]].mean();loss.backward();return loss
    cal.step(closure);temperature=float((.5+4.5*torch.sigmoid(scalar)).detach())
    clone=HierarchicalResponseModel(enc);clone.load_state_dict(chosen["model"]);clone_opt=torch.optim.Adam(clone.parameters(),lr=cfg["learning_rate"]);clone_opt.load_state_dict(chosen["optimizer"])
    with torch.no_grad():equal=torch.equal(model(x[val[:32]],s[val[:32]]),clone(x[val[:32]],s[val[:32]]))
    if not equal:raise ValueError("hierarchical_reload_logits_mismatch")
    durable_json(out/"model.json",{"schema_version":VERSION,"encoder_fingerprint":enc.fingerprint,"encoder_identity":enc.identity,"parameter_count":sum(v.numel()for v in model.parameters()),
        "temperature":temperature,"chosen_epoch":chosen["epoch"],"chosen_optimizer_updates":chosen["updates"],"executed_updates":updates,"model_sha256":digest(out/"hierarchical_best.pt"),"plan_sha256":digest(out/"plan.json"),"BR_integration":False})
    durable_json(out/"fit_complete.json",{"utc":utc(),"curve":curve,"gradient_norm_min":min(norms),"gradient_norm_max":max(norms),"reload_bit_equal":equal,"optimizer_reloaded":True,
        "new_test_used":False,"wall_seconds":time.monotonic()-start,"resources":job.usage(),"frozen_model_json_sha256":digest(out/"model.json")})


def test(p,arrays,job):
    out=Path(p["output"])
    if (out/"test_started.json").exists():raise ValueError("hierarchical_test_already_opened_no_retest")
    X,S,Y,H,meta,ix,public=arrays;enc=metadata_encoder(p);binding=read(out/"model.json");fit_done=read(out/"fit_complete.json")
    if binding["model_sha256"]!=digest(out/"hierarchical_best.pt") or fit_done["frozen_model_json_sha256"]!=digest(out/"model.json"):raise ValueError("hierarchical_frozen_model_changed")
    saved=torch.load(out/"hierarchical_best.pt",map_location="cpu",weights_only=False);model=HierarchicalResponseModel(enc);model.load_state_dict(saved["model"]);model.eval()
    old=torch.load(p["flat_model_path"],map_location="cpu",weights_only=False);old_binding=read(p["flat_metadata_path"]);flat=make_model(public.dimension,len(public.outputs));flat.load_state_dict(old["model"]);flat.eval()
    development=np.load(out/"development.npz",allow_pickle=False);dev_x=development["X"];dev_s=development["S"];dev_y=development["Y"]
    dm=read(out/"development_rows.json");tr=np.asarray([i for i,m in enumerate(dm)if m["fold"]=="train"]);seen=set(dev_y[tr])
    ctx=torch.from_numpy((enc.context(X,S)-saved["mean"])/saved["scale"]);support=torch.from_numpy(S);oldx=torch.from_numpy((X-old["mean"])/old["scale"])
    durable_json(out/"test_started.json",{"utc":utc(),"test_use":1,"model_json_sha256":digest(out/"model.json"),"flat_model_sha256":digest(p["flat_model_path"]),"dataset_sha256":digest(out/"dataset.npz")})
    predictions={"public_heuristic":H,"flat":[],"hierarchical":[]}
    with torch.no_grad():
        for begin in range(0,len(Y),256):
            sl=slice(begin,begin+256);predictions["flat"].append(model_probabilities(flat,oldx[sl],support[sl],old_binding["temperature"]).numpy())
            predictions["hierarchical"].append(model.probabilities(ctx[sl],support[sl],binding["temperature"]).numpy())
    for name in("flat","hierarchical"):predictions[name]=np.concatenate(predictions[name])
    groups=np.asarray([m["pair"]for m in meta]);clusters=sorted(set(groups));scores={};detail={}
    for name,probs in predictions.items():
        if not np.isfinite(probs).all() or probs[~S].any():raise ValueError("hierarchical_test_invalid_public_probability")
        scores[name],detail[name]=score_predictions(probs,Y,public.family_index)
    rng=np.random.default_rng(p["statistics"]["seed"]);draws=rng.integers(0,len(clusters),(10000,len(clusters)));paired={};macro={}
    for name in predictions:
        macro[name]={metric:float(np.mean([v[groups==c].mean()for c in clusters]))for metric,v in detail[name].items()}
    for baseline in("flat","public_heuristic"):
        paired[baseline]={}
        for metric in("nll","brier","top1"):
            per=np.asarray([(detail["hierarchical"][metric][groups==c]-detail[baseline][metric][groups==c]).mean()for c in clusters]);boot=per[draws].mean(1)
            paired[baseline][metric]={"point":float(per.mean()),"CI95":np.quantile(boot,[.025,.975]).tolist(),"CI97_5":np.quantile(boot,[.0125,.9875]).tolist()}
    cold=np.asarray([m["semantic"].startswith("known:")and int(y)not in seen for m,y in zip(meta,Y)]);cold_clusters=sorted(set(groups[cold]));cold_paired={};strata={}
    if cold_clusters:
        draws_cold=rng.integers(0,len(cold_clusters),(10000,len(cold_clusters)))
        for baseline in("flat","public_heuristic"):
            cold_paired[baseline]={}
            for metric in("nll","brier","top1"):
                per=np.asarray([(detail["hierarchical"][metric][cold&(groups==c)]-detail[baseline][metric][cold&(groups==c)]).mean()for c in cold_clusters]);boot=per[draws_cold].mean(1)
                cold_paired[baseline][metric]={"point":float(per.mean()),"CI95":np.quantile(boot,[.025,.975]).tolist()}
    partitions={"cold_selected_known_move":cold,"seen_selected_label":~cold,"known_move":np.asarray([m["semantic"].startswith("known:")for m in meta]),
                "unknown_move":np.asarray([m["semantic"].startswith("unknown:")for m in meta])}
    for key,mask in partitions.items():
        if mask.any():strata[key]={name:score_predictions(pr[mask],Y[mask],public.family_index)[0]for name,pr in predictions.items()}
    for field in("rival","seat","public_known_move_count","ability_unknown","item_unknown"):
        strata[field]={}
        for value in sorted({str(m[field])for m in meta}):
            mask=np.asarray([str(m[field])==value for m in meta]);strata[field][value]={name:score_predictions(pr[mask],Y[mask],public.family_index)[0]for name,pr in predictions.items()}
    # Latency on OLD validation only, never another test inference.
    vi=np.asarray([i for i,m in enumerate(dm)if m["fold"]=="validation"]);times=[]
    with torch.no_grad():
        for i in range(160):
            raw=dev_x[vi[i%len(vi)]];s=dev_s[vi[i%len(vi)]];begin=time.perf_counter();c=enc.context(raw,s)
            model.probabilities(torch.from_numpy(((c-saved["mean"])/saved["scale"])[None]),torch.from_numpy(s[None]),binding["temperature"]);times.append((time.perf_counter()-begin)*1000)
    primary=all(paired[b]["nll"]["CI97_5"][1]<0 for b in paired);coverage=cold.sum()>=100 and len(cold_clusters)>=16
    generalization=coverage and cold_paired["flat"]["top1"]["CI95"][0]>0
    no_point_regression=all(paired[b]["brier"]["point"]<=0 and paired[b]["top1"]["point"]>=0 for b in paired) and cold_paired and cold_paired["flat"]["brier"]["point"]<=0
    cold_positive=bool(cold_paired and cold_paired["flat"]["top1"]["point"]>0 and cold_paired["flat"]["nll"]["point"]<0)
    verdict="GO"if primary and generalization and no_point_regression and np.median(times)<=5 else "CONDITIONAL GO"if cold_positive and any(paired[b]["nll"]["CI95"][1]<0 for b in paired)else"NO-GO"
    result={"verdict":verdict,"row_scores":scores,"cluster_macro":macro,"paired":paired,"test_rows":len(Y),"test_team_pairs":len(clusters),
        "cold_known":{"rows":int(cold.sum()),"clusters":len(cold_clusters),"distinct_labels":len(set(Y[cold])),"paired":cold_paired},"strata":strata,
        "gates":{"primary_NLL":primary,"cold_coverage":bool(coverage),"cold_top1_generalization":bool(generalization),"no_point_regression":bool(no_point_regression)},
        "context_plus_network_ms":{"median":float(np.median(times)),"p95":float(np.quantile(times,.95))},"new_PPO":0,"BR_integration":False,"resources":job.usage()}
    np.savez_compressed(out/"test_predictions.npz",Y=Y,groups=groups,cold=cold,**predictions);durable_json(out/"test_complete.json",result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--prepare",type=Path);parser.add_argument("--output",type=Path);parser.add_argument("--plan",type=Path);parser.add_argument("--owned",action="store_true");parser.add_argument("--resume",action="store_true");args=parser.parse_args()
    if args.prepare:prepare(args.prepare,args.output);return
    p,_=verify(args.plan);out=Path(p["output"])
    if not args.owned:raise ValueError("hierarchical_independent_owner_required")
    if (out/"control.json").exists()and process_alive(read(out/"control.json")["pid"]):raise ValueError("hierarchical_owner_already_alive")
    if any((out/f).exists()for f in("failure.json","STOP","watchdog.json","execution_complete.json","test_started.json")):raise ValueError("hierarchical_failure_or_completion_no_automatic_restart")
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=12)
    if job.inherited_job:raise ValueError("hierarchical_inherited_launcher_job")
    network=enforce_local_network_only();limit=RuntimeLimit(out,3600)
    atomic_json(out/"control.json",{"pid":os.getpid(),"parent_pid":os.getppid(),"utc":utc(),"plan_sha256":digest(args.plan),"own_job":True,"inherited_job":False,"resources":p["resources"],"automatic_restarts":0})
    started=time.monotonic()
    try:
        if (out/"fit_complete.json").exists():
            if not args.resume:raise ValueError("existing_hierarchy_requires_explicit_resume")
        else:fit(p,job,limit)
        collect(args.plan,job,limit,args.resume,plan_validator=verify)
        arrays=build_dataset(p,folds=("test",));result=test(p,arrays,job)
        verify(args.plan)
        durable_json(out/"execution_complete.json",{"status":"complete_pending_independent_audit","utc":utc(),"native_games":1024,"new_PPO":0,"independent_strength_games":0,
            "verdict":result["verdict"],"test_sha256":digest(out/"test_complete.json"),"wall_seconds":time.monotonic()-started,"resources":job.usage(),"network":network})
        atomic_json(out/"status.json",{"phase":"complete_pending_independent_audit","games":1024,"utc":utc()})
    except BaseException as err:
        import traceback
        atomic_json(out/"failure.json",{"utc":utc(),"type":type(err).__name__,"message":str(err),"traceback":traceback.format_exc(),"no_automatic_restart":True,"resources":job.usage()});raise
    finally:limit.finished.set()


if __name__=="__main__":main()
