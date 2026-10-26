"""Opt-in existing-snapshot inference only; no rollout, training or model save."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch

from advisor.learned_decision_snapshots import read_root, replay_original, outside_git, write_new
from advisor.learned_action_signals import public_identity
from advisor.learned_policy_matched_signals import HistoricalSampler, policy_matched_branch, paired_summary
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
from advisor.learned_policy import LearnedPolicy
from advisor.learning_resources import WindowsJob, RuntimeLimit, enforce_local_network_only, atomic_json
from advisor.showdown_environment import ShowdownEnvironment
from scripts.pilot_foundation_decision_snapshots import NativeBudget


def file_hash(p): return sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))


def training_forbidden(*_, **__):
    raise RuntimeError("no_PPO_rollout_optimizer_or_model_save_authorized")


def forbid_training():
    from sb3_contrib import MaskablePPO
    from advisor.learned_combat_foundation import FoundationCombatPPO
    for cls in (MaskablePPO, FoundationCombatPPO):
        cls.learn = cls.train = cls.collect_rollouts = cls.save = training_forbidden
    torch.optim.Adam.step = training_forbidden


def references(cfg):
    exp = cfg["experiments"][0]
    result = {"previous": (cfg["previous_model"], cfg["previous_model_id"]),
              "historical": (exp["historical_model"], exp["historical_model_id"])}
    result.update({k: (p, exp["frozen_opponent_ids"][k]) for k,p in exp["frozen_opponents"].items()})
    return result


def load_source(source):
    original_plan = read(source / "plan_revision02.json")
    for path, identity in original_plan["input_hashes"].items():
        if file_hash(path) != identity: raise ValueError("immutable_original_input:"+path)
    for path, identity in read(source / "artifact_hashes.json")["files"].items():
        if file_hash(source / path) != identity: raise ValueError("original_artifact_SHA:"+path)
    cfg = read(original_plan["source_config"])
    parent = LearnedPolicy(original_plan["model"], cfg["catalog"], expected_model_id=original_plan["model_sha256"])
    if parent.model.gamma != 1. or parent.model.gae_lambda != .95 or parent.model.n_steps != 128:
        raise ValueError("original_gamma_lambda_horizon_required")
    roots = read(source / "run/snapshots/capture_manifest.json")["roots"]
    if len(roots) != 32 or len({r["id"] for r in roots}) != 32:
        raise ValueError("exactly_existing32_roots_required")
    return original_plan, cfg, parent, roots


def source_provenance(source, output):
    op, cfg, parent, roots = load_source(source)
    refs = references(cfg); policy = deepcopy(parent.model.policy); records = []
    audits = {}
    for p in (source / "run/PPO_audits").glob("*.audit.json"):
        a = read(p)
        idx = (a["model_timesteps_end"]-1048576)//512-1
        if idx in audits: raise ValueError("duplicate_rollout_provenance")
        audits[idx] = a
    for r in roots:
        state_file = Path(r["policy_state_file"])
        if file_hash(state_file) != r["policy_state_file_SHA256"]:
            raise ValueError("behavior_state_file_SHA")
        state = torch.load(state_file, map_location="cpu", weights_only=True)
        if tensor_digest(state) != r["policy_id"]: raise ValueError("behavior_parameter_SHA")
        policy.load_state_dict(state, strict=True)
        public = read(source / "run/snapshots/public" / (r["id"]+".json"))["observation"]
        if sha256(parent.encoder.encode(public).tobytes()).hexdigest() != r["observation_sha256"]:
            raise ValueError("behavior_encoded_public_SHA")
        scores = HistoricalSampler(parent.encoder, policy, 0).scores(public)
        errors = [abs(scores["log_probabilities"][r["action"]]-r["old_logp"]),
                  abs(scores["value"]-r["value"])]
        if max(errors)>2e-5: raise ValueError("behavior_logp_value_mismatch")
        cp = read_root(source/"run/snapshots", r)
        trace = [json.loads(l) for l in (source/"run/snapshots/private"/(r["id"]+".trace.jsonl")).read_text().splitlines()]
        if not trace or not trace[-1]["result"]["terminated"] or trace[0]["actions"]["self"] != r["action"]:
            raise ValueError("source_factual_native_suffix_missing")
        joined = read(source/"run/snapshots/joins"/(r["id"]+".json"))
        if any(joined[k] != r[k] for k in ("id","action","old_logp","value","advantage","return_target","t","rollout")):
            raise ValueError("snapshot_GAE_join_provenance")
        audit = audits[r["rollout"]]
        if file_hash(audit["capture"]) != audit["capture_SHA256"]: raise ValueError("original_GAE_capture_SHA")
        with np.load(audit["capture"]) as d:
            t=r["t"]; pos=(t,0)
            for key, root_key in (("actions","action"),("old_logp","old_logp"),("values","value"),
                                  ("advantages","advantage"),("returns","return_target")):
                if float(d[key].reshape(128,4)[pos]) != r[root_key]: raise ValueError("GAE_row_"+key)
            if d["native_masks"].reshape(128,4,35)[pos].astype(int).tolist() != r["action_mask"]:
                raise ValueError("source_GAE_mask")
        kind = r["training_episode_identity"]["opponent"]
        eligible = kind in refs
        if eligible and refs[kind][1] != r["training_episode_identity"]["opponent_model_id"]:
            raise ValueError("historical_opponent_identity_missing")
        records.append({"root":r["id"],"update":r["rollout"],"opponent":kind,"eligible":eligible,
            "exclusion":None if eligible else "stateful_heuristic_RNG_state_at_root_not_captured",
            "behavior_parameter_SHA256":r["policy_id"],"critic_same_state":True,
            "native_checkpoint_digest":cp["digest"],"encoded_public_SHA256":r["observation_sha256"],
            "old_logp_error":errors[0],"value_error":errors[1],"original_GAE":r["advantage"],
            "original_return_target":r["return_target"],"remaining_rollout_steps":128-r["t"],
            "original_native_RNG":"exact_checkpoint_state_and_source_scenario_seed_preserved",
            "original_actor_sampling_RNG":"not_saved; new_predeclared_local_streams_sample_exact_T1_distribution",
            "opponent_mode":"original_LearnedPolicy_argmax" if eligible else None})
    result={"source":str(source),"roots":records,"eligible_count":sum(r["eligible"] for r in records),
        "excluded_count":sum(not r["eligible"] for r in records),
        "native_executions":0,"PPO":0,"optimizer_steps":0,
        "parent_parameters":tensor_digest(parent.model.policy.state_dict()),
        "parent_Adam":optimizer_digest(parent.model.policy)}
    write_new(output, result)
    return result


def validate_plan(plan):
    if (plan.get("schema") != "foundation-policy-matched-signals-plan-v1" or plan.get("repeats") != 8
            or plan.get("native_cap") != 496 or plan.get("global_cap") != 512
            or plan.get("regression_reserve") != 16 or len(plan.get("future_seeds",[])) != 8
            or plan.get("PPO") != 0 or plan.get("workers") != 1 or plan.get("device") != "cpu"
            or plan.get("cpu_percent") != 50 or plan.get("memory_mib") != 12288
            or not 60 <= plan.get("max_seconds",0) <= 1800
            or len(plan.get("eligible_roots",[]))*19 > 496):
        raise ValueError("bounded_policy_matched_plan_required")
    if len(set(plan["eligible_roots"])) != len(plan["eligible_roots"]): raise ValueError("duplicate_root")
    for seed in plan["future_seeds"]:
        if len(seed)!=4 or any(type(n) is not int or not 0<=n<=65535 for n in seed):
            raise ValueError("invalid_policy_matched_seed")
    if len({tuple(s) for s in plan["future_seeds"]}) != 8: raise ValueError("duplicate_seed")
    for path, identity in plan["input_hashes"].items():
        if file_hash(path)!=identity: raise ValueError("frozen_input_changed:"+path)
    repo=Path(__file__).resolve().parents[1]
    for path, identity in plan["source_hashes"].items():
        if file_hash(repo/path)!=identity: raise ValueError("frozen_source_changed:"+path)


def run(plan, output, job):
    validate_plan(plan)
    output=outside_git(output);output.mkdir(exist_ok=True)
    write_new(output/"started.json",{"PID":os.getpid(),"plan_SHA256":file_hash(plan["plan_file"]),
        "no_automatic_restart":True,"new_PPO":0})
    started=perf_counter();limit=RuntimeLimit(output,plan["max_seconds"])
    native=None;budget=None
    try:
        source=Path(plan["source"]);op,cfg,parent,roots=load_source(source)
        eligible=[r for r in roots if r["id"] in plan["eligible_roots"]]
        if [r["id"] for r in eligible]!=plan["eligible_roots"]:raise ValueError("changed_root_allocation")
        parent_before={"parameters":tensor_digest(parent.model.policy.state_dict()),"Adam":optimizer_digest(parent.model.policy)}
        policy=deepcopy(parent.model.policy);refs=references(cfg);rivals={}
        for kind in {r["training_episode_identity"]["opponent"] for r in eligible}:
            path,identity=refs[kind];rivals[kind]=LearnedPolicy(path,cfg["catalog"],expected_model_id=identity)
        rival_before={k:{"parameters":tensor_digest(v.model.policy.state_dict()),
                        "Adam":optimizer_digest(v.model.policy)} for k,v in rivals.items()}
        native=ShowdownEnvironment(cfg["checkout"],max_decisions=cfg["max_decisions"])
        units=output/"native_units";units.mkdir();budget=NativeBudget(units,maximum=plan["native_cap"])
        pairs=[];roots_report=[]
        # All eligible roots must pass exact binding and original replay first.
        for r in eligible:
            state=torch.load(r["policy_state_file"],map_location="cpu",weights_only=True)
            if tensor_digest(state)!=r["policy_id"]:raise ValueError("behavior_identity")
            policy.load_state_dict(state,strict=True)
            cp=read_root(source/"run/snapshots",r)
            public=read(source/"run/snapshots/public"/(r["id"]+".json"))["observation"]
            rival=rivals[r["training_episode_identity"]["opponent"]]
            trace=[json.loads(l) for l in (source/"run/snapshots/private"/(r["id"]+".trace.jsonl")).read_text().splitlines()]
            r["trace"]=trace
            def bind():
                native.restart(cp)
                actual=native.observation("self",include_history=True)
                if native.save()!=cp or public_identity(actual)!=r["public_identity"]:
                    raise ValueError("policy_matched_native_root")
                scores=HistoricalSampler(parent.encoder,policy,0).scores(actual)
                if (max(abs(scores["value"]-r["value"]),abs(scores["log_probabilities"][r["action"]]-r["old_logp"]))>2e-5
                        or sha256(parent.encoder.encode(actual).tobytes()).hexdigest()!=r["observation_sha256"]):
                    raise ValueError("policy_matched_root_behavior")
                other=int(rival.act(native.observation("opponent",include_history=True)))
                if other!=trace[0]["actions"]["opponent"]:raise ValueError("original_opponent_action_not_reconstructed")
                return {"root":r["id"],"opponent_action":other,"checkpoint":cp["digest"],"scores":scores}
            budget.run("bind_"+r["id"],bind)
            budget.run("replay_"+r["id"],lambda:replay_original(native,cp,r,public,stopping=limit.stopping))
        write_new(output/"replay_gate_passed.json",{"roots":len(eligible),"units":budget.count})
        for r in eligible:
            policy.load_state_dict(torch.load(r["policy_state_file"],map_location="cpu",weights_only=True),strict=True)
            cp=read_root(source/"run/snapshots",r)
            public=read(source/"run/snapshots/public"/(r["id"]+".json"))["observation"]
            opponent=rivals[r["training_episode_identity"]["opponent"]]
            horizon=128-r["t"]
            def branch(rep, forced):
                actor=HistoricalSampler(parent.encoder,policy,118000000+r["rollout"]*100+rep)
                return policy_matched_branch(native,cp,public,actor=actor,opponent=opponent,
                    forced_action=r["action"] if forced else None,future_seed=plan["future_seeds"][rep],
                    horizon=horizon,stopping=limit.stopping)
            for rep in range(8):
                # Alternation fixed before outcomes; same local actor/native seeds.
                order=("forced","baseline") if rep%2==0 else ("baseline","forced")
                results={}
                for condition in order:
                    results[condition]=budget.run(f"{condition}_{r['id']}_{rep}",
                        lambda condition=condition:branch(rep,condition=="forced"))
                if results["forced"]["first_policy_action"]!=results["baseline"]["first_policy_action"]:
                    raise ValueError("paired_actor_first_draw_mismatch")
                if results["forced"]["first_executed_action"]==results["baseline"]["first_executed_action"]:
                    if results["forced"]!=results["baseline"]:raise ValueError("same_first_action_same_RNG_not_exact")
                pairs.append({"root":r["id"],"rep":rep,"GAE":r["advantage"],"critic_value":r["value"],**results})
            repeated=budget.run("repeat_"+r["id"],lambda:branch(0,True))
            if repeated!=pairs[-8]["forced"]:raise ValueError("policy_matched_repetition_not_exact")
            roots_report.append({"root":r["id"],"family":r["family"],"turn":r["turn"],
                "original_native_horizon":len(r["trace"]),"opponent":r["training_episode_identity"]["opponent"],
                "behavior_parameter_SHA256":r["policy_id"],"horizon":horizon})
            atomic_json(output/"progress.json",{"phase":"policy_matched_continuations","roots_done":len(roots_report),
                "total_roots":len(eligible),"native_units":budget.count,"elapsed_seconds":perf_counter()-started,
                "resources":job.usage()})
        after={"parameters":tensor_digest(parent.model.policy.state_dict()),"Adam":optimizer_digest(parent.model.policy)}
        rival_after={k:{"parameters":tensor_digest(v.model.policy.state_dict()),
                       "Adam":optimizer_digest(v.model.policy)} for k,v in rivals.items()}
        if parent_before!=after or rival_before!=rival_after:raise ValueError("frozen_model_or_Adam_changed")
        write_new(output/"pairs.json",pairs)
        summary=paired_summary(pairs,root_order=plan["eligible_roots"])
        ci=summary["correlation_95CI"]
        evidence=(summary["nonzero_roots"]>=8 and ci is not None and (ci[0]>0 or ci[1]<0))
        result={"status":"POLICY_MATCHED_SIGNAL_EVIDENCE" if evidence else "INCONCLUSIVE",
            "interpretation":"linkage_and_policy_matching_not_strength_or_GAE_correctness_verdict",
            **summary,"root_provenance":roots_report,"native_units":budget.count,
            "repeat_checks":len(eligible),"parent_before":parent_before,"parent_after":after,
            "rivals_before":rival_before,"rivals_after":rival_after,"resources":job.usage(),
            "seconds":perf_counter()-started,"PPO":0,"rollout_collection":0,"optimizer_updates":0,"evaluation_games":0}
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
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path);ap.add_argument("--preflight",type=Path)
    ap.add_argument("--plan",type=Path);ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=12)
    enforce_local_network_only();torch.set_num_threads(1);forbid_training()
    if args.preflight:
        result=source_provenance(args.source,args.preflight)
        print(json.dumps({"eligible":result["eligible_count"],"excluded":result["excluded_count"],"native":0}))
    else:
        plan=read(args.plan);plan["plan_file"]=str(args.plan)
        result=run(plan,args.output,job)
        print(json.dumps({k:result[k] for k in ("status","root_clusters","paired_samples","native_units","seconds")}))


if __name__=="__main__":main()
