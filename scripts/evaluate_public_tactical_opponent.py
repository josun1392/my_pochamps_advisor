"""One frozen public-opponent validation, reusing native paired execution.

No training, opponent selection search, automatic retry or model promotion.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from advisor.learned_execution_alignment import content_hash, digest, durable_json
from advisor.learning_resources import WindowsJob, RuntimeLimit, atomic_json, process_alive, enforce_local_network_only

VERSION = "foundation-public-tactical-opponent-validation-v1"
RIVALS = ("public_tactical_exchange_v1", "tactical_heuristic")


def rival_policy(kind, candidate):
    # The established evaluator serializes strings or model_id-bearing policy
    # objects. Keep legacy heuristic construction/seeding inside that owner.
    if kind not in RIVALS:
        raise ValueError("unknown_tactical_validation_rival")
    return candidate if kind == RIVALS[0] else "tactical_heuristic"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def utc():
    return datetime.now(timezone.utc).isoformat()


def append(path, row):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, allow_nan=False)+"\n")
        f.flush()
        os.fsync(f.fileno())


def slots(cases):
    return [{"scope": c["scope"], "case": c["index"], "seat": seat,
             "rival": rival, "scenario_sha256": c["scenario_sha256"]}
            for c in cases for seat in ("p1", "p2") for rival in RIVALS]


def verify_plan(path):
    from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
    p=read(path)
    if (p.get("schema_version") != VERSION or p.get("PPO_transitions") != 0
            or p.get("native_total_cap") != 1024 or p.get("automatic_restarts") != 0
            or p.get("phase") not in ("development", "final")
            or p.get("resources") != {"workers":1,"cpu_percent":50,"memory_mib":12288,"device":"cpu","max_runtime_seconds":3600}
            or p.get("engine_commit") != SHOWDOWN_COMMIT or p.get("format") != FORMAT_ID):
        raise ValueError("unrecognized_public_tactical_validation_contract")
    for name,sha in p["immutable_files"].items():
        if digest(name)!=sha:raise ValueError("tactical_immutable_input_mutated:"+name)
    for name,sha in p["source_sha256"].items():
        if hashlib.sha256((ROOT/name).read_bytes().replace(b"\r\n",b"\n")).hexdigest()!=sha:
            raise ValueError("tactical_frozen_source_changed:"+name)
    if subprocess.check_output(["git","rev-parse","HEAD"],cwd=p["checkout"],text=True).strip()!=SHOWDOWN_COMMIT:
        raise ValueError("tactical_engine_pin_changed")
    cases=read(p["cases_path"])["cases"]
    if (len({c["index"] for c in cases})!=len(cases) or len(slots(cases))!=p["games"]
            or p["games"]!=(896 if p["phase"]=="final" else 16)):
        raise ValueError("tactical_frozen_panel_or_budget_changed")
    from advisor.learned_encoder import fingerprint
    if any(fingerprint(c["scenario"])!=c["scenario_sha256"] for c in cases):
        raise ValueError("tactical_case_sha_mismatch")
    return p,cases


def analyze(rows,cases):
    import numpy as np
    expected=slots(cases)
    if [r["slot"]for r in rows]!=expected:
        raise ValueError("incomplete_or_duplicate_tactical_validation")
    result={"games":len(rows),"case_clusters":len(cases),"summaries":[],"paired":[],
            "PPO_transitions":0,"no_model_promotion":True,
            "uncertainty":"case_clusters_preserve_both_native_seats_and_rivals_one_frozen_Foundation"}
    for scope in ("all","train","heldout"):
        chosen=[r for r in rows if scope=="all" or r["slot"]["scope"]==scope]
        ids=sorted({r["slot"]["case"]for r in chosen})
        if not ids:continue
        vectors={}
        for rival in RIVALS:
            for seat in ("all","p1","p2"):
                records=[r["record"]for r in chosen if r["slot"]["rival"]==rival and (seat=="all" or r["slot"]["seat"]==seat)]
                counts=Counter("truncated" if r["truncated"] else "win" if r["winner"]=="self" else "loss" if r["winner"]=="opponent" else "draw"for r in records)
                result["summaries"].append({"scope":scope,"rival":rival,"seat":seat,"games":len(records),
                    **{k:counts[k]for k in ("win","loss","draw","truncated")},
                    "Foundation_win_fraction":counts["win"]/len(records),
                    "native_rejections":sum(r["native_choice_rejections"]for r in records)})
            vectors[rival]=np.array([np.mean([r["record"]["winner"]=="self" and not r["record"]["truncated"]
                for r in chosen if r["slot"]["case"]==i and r["slot"]["rival"]==rival])for i in ids])
        draws=np.random.default_rng(2026102401).integers(0,len(ids),(20000,len(ids)))
        for rival in RIVALS:
            result["paired"].append({"scope":scope,"rival":rival,"Foundation_win_fraction":float(vectors[rival].mean()),
                "case_cluster_95":np.quantile(vectors[rival][draws].mean(axis=1),[.025,.975]).tolist()})
        delta=vectors[RIVALS[0]]-vectors[RIVALS[1]]
        result["paired"].append({"scope":scope,"comparison":"Foundation_win_candidate_minus_tactical",
            "delta":float(delta.mean()),"case_cluster_95":np.quantile(delta[draws].mean(axis=1),[.025,.975]).tolist(),"clusters":len(ids)})
    return result


def run(path, job, limit, resume=False):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
    from advisor.learned_public_tactical_opponent import PublicTacticalOpponent
    from advisor.learned_difficulty_calibration import audit_receipts, PublicRetryAudit, AttemptRateGuard
    from scripts.run_foundation_parent_anchor_study import FrozenCase, checkpoint_integrity
    from scripts.evaluate_showdown_policy import evaluate
    p,cases=verify_plan(path);out=Path(p["output"]);out.mkdir(exist_ok=True)
    for name in ("receipts","decisions"):(out/name).mkdir(exist_ok=True)
    if (out/"execution_complete.json").exists():raise ValueError("tactical_already_complete_no_duplicate")
    plan_sha=digest(path);game_slots=slots(cases);rows=audit_receipts(out,game_slots,plan_sha)
    if rows and not resume:raise ValueError("existing_tactical_results_explicit_resume_required")
    torch.set_num_threads(1)
    integrity=checkpoint_integrity(p["parent_path"],p["parent_sha256"],32768)
    player=LearnedPolicy(p["parent_path"],p["catalog"],expected_model_id=p["parent_sha256"])
    before={"parameters":tensor_digest(player.model.policy.state_dict()),"Adam":optimizer_digest(player.model.policy)}
    initial=out/"initial_identity.json"
    if not initial.exists():durable_json(initial,{**before,"integrity":integrity})
    elif read(initial)!={**before,"integrity":integrity}:raise ValueError("tactical_parent_identity_changed")
    lookup={c["index"]:c for c in cases};started=time.monotonic();done_before=len(rows)
    rate_guard=AttemptRateGuard();native_ledger=Path(p["native_start_ledger"])
    for index in range(len(rows),len(game_slots)):
        if limit.stopping():
            atomic_json(out/"status.json",{"status":"stopped","games":len(rows),"utc":utc()});return
        slot=game_slots[index];seed=slot["case"]+919
        candidate=PublicTacticalOpponent(seed,catalog=p["catalog"],checkout=p["checkout"])
        rival=rival_policy(slot["rival"],candidate)
        rival_side="opponent" if slot["seat"]=="p1" else "self"
        native_rows=native_ledger.read_text(encoding="utf-8").splitlines() if native_ledger.exists()else[]
        if len(native_rows)>=1024:raise ValueError("tactical_total_native_start_cap")
        if p["phase"]=="development" and sum(json.loads(r)["phase"]!="final" for r in native_rows)>=128:
            raise ValueError("tactical_development_start_cap")
        append(native_ledger,{"ordinal":len(native_rows),"phase":p["phase"],"index":index,"slot_sha256":content_hash(slot)})
        append(out/"game_ledger.jsonl",{"phase":"game_started","index":index,"slot_sha256":content_hash(slot)})
        decision_path=out/"decisions"/f"game_{index:04d}.jsonl.gz"
        audit=PublicRetryAudit(slot["case"]);counts=Counter();latencies=[]
        with gzip.open(decision_path,"xt",encoding="utf-8")as stream:
            def observer(event):
                audit.observe(event);rate_guard.observe(event["result"]["action_rejected"])
                v=event["before"][rival_side]
                if rival is not candidate:candidate.act(v)
                proof=deepcopy(candidate.last_decision)
                if v["request_state"]=="move" and not v["action_mask"][26]:
                    counts["decisions"]+=1;counts["comparable"]+=not bool(proof.get("fallback"))
                    counts["disagrees"]+=bool(proof.get("disagrees"));latencies.append(proof.get("seconds",0))
                stream.write(json.dumps({"ordinal":audit.steps,"rival_side":rival_side,
                    "before":event["before"],"actions":event["actions"],"result":event["result"],
                    "rival_candidate_proof":proof,"observed_public_delta":{
                        side:after["public_history"][len(event["before"][side]["public_history"]):]
                        for side,after in event["after"].items()}},allow_nan=False)+"\n")
                if event["result"]["action_rejected"]:
                    append(out/"public_rejections.jsonl",{"slot":slot,**event})
            record=evaluate(p["checkout"],p["catalog"],{"Foundation":player},cases=1,offset=slot["case"],
                rivals={slot["rival"]:rival},curriculum_version="showdown-learning-curriculum-v8",tactical_diagnostics=True,
                case_provider=FrozenCase(lookup[slot["case"]],{}),candidate_seat=slot["seat"],
                transition_observer=observer,stopping=limit.stopping)["records"][0]
        row={"slot":slot,"plan_sha256":plan_sha,"parent_sha256":p["parent_sha256"],"record":record,
             "record_sha256":content_hash(record),"decisions_path":str(decision_path),"decisions_sha256":digest(decision_path),
             "candidate_decision_counts":dict(counts),"candidate_latency_seconds":latencies}
        dest=out/"receipts"/f"game_{index:04d}.json";durable_json(dest,row)
        append(out/"game_ledger.jsonl",{"phase":"game_committed","index":index,"receipt_sha256":digest(dest)})
        rows.append(row)
        if len(rows)%8==0:
            elapsed=time.monotonic()-started
            atomic_json(out/"status.json",{"status":"running","games":len(rows),"target":len(game_slots),
                "games_per_second":(len(rows)-done_before)/elapsed,"wall_seconds":elapsed,"resources":job.usage(),"utc":utc()})
    after={"parameters":tensor_digest(player.model.policy.state_dict()),"Adam":optimizer_digest(player.model.policy)}
    if after!=before:raise ValueError("tactical_frozen_parent_mutated")
    verified=audit_receipts(out,game_slots,plan_sha)
    result=analyze(verified,cases);durable_json(out/"analysis.json",result)
    durable_json(out/"execution_complete.json",{"utc":utc(),"games":len(rows),"PPO_transitions":0,
        "seconds":time.monotonic()-started,"parent_before":before,"parent_after":after,
        "native_total_starts":len(native_ledger.read_text(encoding="utf-8").splitlines()),
        "resources":job.usage(),"analysis_sha256":digest(out/"analysis.json")})
    atomic_json(out/"status.json",{"status":"complete","games":len(rows),"utc":utc()})


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--owned',action='store_true');ap.add_argument('--resume',action='store_true');args=ap.parse_args()
    if not args.owned:raise ValueError("explicit_owned_bounded_launcher_required")
    p,cases=verify_plan(args.plan);out=Path(p["output"]);out.mkdir(exist_ok=True)
    old=out/'control.json'
    if old.exists() and process_alive(read(old)['pid']):raise ValueError('tactical_existing_owner_no_duplicate')
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=12)
    limit=RuntimeLimit(out,3600);network=enforce_local_network_only()
    atomic_json(old,{"pid":os.getpid(),"parent_pid":os.getppid(),"utc":utc(),"own_job":True,
        "inherited_job":job.inherited_job,"plan_sha256":digest(args.plan),"resources":p['resources'],"automatic_restarts":0})
    try:
        run(args.plan,job,limit,args.resume)
    except BaseException as error:
        atomic_json(out/'failure.json',{'utc':utc(),'type':type(error).__name__,'error':str(error),'resources':job.usage()})
        raise
    finally:
        limit.finished.set();atomic_json(out/'network.json',network)


if __name__=='__main__':main()
