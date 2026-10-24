"""Receipt-bound, one-candidate public BR validation. Zero PPO; no auto retry.

Reuses the maintained native evaluator, real-seat swap, frozen-model loader,
retry monitor, resource owner and durable receipt audit. This coordinator alone
holds scenario/model handles; the scripted opponent receives one public view.
"""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from advisor.learned_execution_alignment import content_hash,digest,durable_json
from advisor.learning_resources import WindowsJob,RuntimeLimit,atomic_json,process_alive,enforce_local_network_only
from scripts.evaluate_public_tactical_opponent import read,utc,append
VERSION='foundation-public-best-response-validation-v1'
RIVALS=('public_observation_best_response_v1','tactical_heuristic')


def slots(cases,players):
    return [{'scope':c['scope'],'case':c['index'],'player':name,'seat':seat,'rival':rival,
             'scenario_sha256':c['scenario_sha256']}
            for c in cases for name in players for seat in('p1','p2')for rival in RIVALS]


def verify_plan(path):
    from advisor.showdown_bridge import SHOWDOWN_COMMIT,FORMAT_ID
    from advisor.learned_encoder import fingerprint
    p=read(path)
    if (p.get('schema_version')!=VERSION or p.get('PPO_transitions')!=0 or p.get('native_total_cap')!=1536
        or p.get('automatic_restarts')!=0 or p.get('games')!=1408 or len(p.get('players',{}))!=2
        or p.get('resources')!={'workers':1,'cpu_percent':50,'memory_mib':12288,'device':'cpu','max_runtime_seconds':3600}
        or p.get('engine_commit')!=SHOWDOWN_COMMIT or p.get('format')!=FORMAT_ID):
        raise ValueError('unrecognized_bounded_best_response_contract')
    for name,sha in p['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=sha:raise ValueError('frozen_BR_source_changed:'+name)
    for path,sha in p['immutable_files'].items():
        if digest(path)!=sha:raise ValueError('BR_immutable_input_changed:'+path)
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=p['checkout'],text=True).strip()!=SHOWDOWN_COMMIT:
        raise ValueError('BR_engine_changed')
    cases=read(p['cases_path'])['cases']
    if len({c['index']for c in cases})!=176 or len(slots(cases,p['players']))!=p['games']:
        raise ValueError('BR_case_or_budget_mismatch')
    if any(fingerprint(c['scenario'])!=c['scenario_sha256']for c in cases):raise ValueError('BR_scenario_identity_mismatch')
    return p,cases


def analyze(rows,cases,players):
    import numpy as np
    if [r['slot']for r in rows]!=slots(cases,players):raise ValueError('incomplete_duplicate_BR_comparison')
    result={'games':len(rows),'case_clusters':len(cases),'summaries':[],'paired':[],'PPO_transitions':0,
            'unit':'initial_case_with_both_seats_and_all_rivals_and_players','not_independent_training_seeds':True}
    for name in players:
        for scope in('all','train','heldout'):
            chosen=[r for r in rows if r['slot']['player']==name and(scope=='all'or r['slot']['scope']==scope)]
            ids=sorted({r['slot']['case']for r in chosen});vectors={}
            for rival in RIVALS:
                for seat in('all','p1','p2'):
                    records=[r['record']for r in chosen if r['slot']['rival']==rival and(seat=='all'or r['slot']['seat']==seat)]
                    counts=Counter('truncated'if r['truncated']else'win'if r['winner']=='opponent'else'loss'if r['winner']=='self'else'draw'for r in records)
                    result['summaries'].append({'player':name,'scope':scope,'rival':rival,'seat':seat,'games':len(records),
                        **{k:counts[k]for k in('win','loss','draw','truncated')},'rival_win_fraction':counts['win']/len(records),
                        'native_rejections':sum(r['native_choice_rejections']for r in records)})
                vectors[rival]=np.array([np.mean([r['record']['winner']=='opponent'and not r['record']['truncated']for r in chosen if r['slot']['case']==i and r['slot']['rival']==rival])for i in ids])
            draws=np.random.default_rng(2026102402).integers(0,len(ids),(20000,len(ids)))
            delta=vectors[RIVALS[0]]-vectors[RIVALS[1]]
            result['paired'].append({'player':name,'scope':scope,'comparison':'new_rival_win_minus_tactical',
                'delta':float(delta.mean()),'case_cluster_95':np.quantile(delta[draws].mean(axis=1),[.025,.975]).tolist(),
                'clusters':len(ids),'discordant_clusters':int(np.count_nonzero(delta))})
            for rival in RIVALS:
                result['paired'].append({'player':name,'scope':scope,'rival':rival,'rival_win_fraction':float(vectors[rival].mean()),
                    'case_cluster_95':np.quantile(vectors[rival][draws].mean(axis=1),[.025,.975]).tolist()})
    return result


def run(path,job,limit,resume=False):
    import torch
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest,optimizer_digest
    from advisor.learned_public_best_response import PublicBestResponseOpponent
    from advisor.learned_difficulty_calibration import audit_receipts,PublicRetryAudit,AttemptRateGuard
    from scripts.evaluate_showdown_policy import evaluate
    from scripts.run_foundation_parent_anchor_study import FrozenCase
    p,cases=verify_plan(path);out=Path(p['output']);out.mkdir(exist_ok=True)
    for name in('receipts','decisions'):(out/name).mkdir(exist_ok=True)
    if(out/'execution_complete.json').exists():raise ValueError('BR_already_complete_no_duplicate')
    plan_sha=digest(path);game_slots=slots(cases,p['players']);rows=audit_receipts(out,game_slots,plan_sha)
    if rows and not resume:raise ValueError('explicit_BR_resume_required')
    torch.set_num_threads(1);players={};before={}
    for name,spec in p['players'].items():
        if digest(spec['path'])!=spec['sha256']:raise ValueError('BR_model_SHA_mismatch')
        player=LearnedPolicy(spec['path'],p['catalog'],expected_model_id=spec['sha256']);players[name]=player
        before[name]={'ZIP':digest(spec['path']),'parameters':tensor_digest(player.model.policy.state_dict()),'Adam':optimizer_digest(player.model.policy)}
    if not(out/'initial_identity.json').exists():durable_json(out/'initial_identity.json',before)
    elif read(out/'initial_identity.json')!=before:raise ValueError('BR_resume_model_changed')
    lookup={c['index']:c for c in cases};started=time.monotonic();initial=len(rows);rate=AttemptRateGuard()
    ledger=Path(p['native_start_ledger'])
    for index in range(len(rows),len(game_slots)):
        if limit.stopping():atomic_json(out/'status.json',{'status':'stopped','games':len(rows),'utc':utc()});return
        slot=game_slots[index];candidate=PublicBestResponseOpponent(slot['case']+919,checkout=p['checkout'],catalog=p['catalog'])
        if candidate.model_id!=p['opponent_model_id']:raise ValueError('BR_policy_identity_changed')
        rival=candidate if slot['rival']==RIVALS[0]else'tactical_heuristic'
        side='opponent'if slot['seat']=='p1'else'self';lines=ledger.read_text(encoding='utf-8').splitlines()if ledger.exists()else[]
        if len(lines)>=1536:raise ValueError('BR_total_native_cap')
        append(ledger,{'ordinal':len(lines),'phase':'final','index':index,'slot_sha256':content_hash(slot)})
        append(out/'game_ledger.jsonl',{'phase':'game_started','index':index,'slot_sha256':content_hash(slot)})
        path=out/'decisions'/f'game_{index:04d}.jsonl.gz';audit=PublicRetryAudit(slot['case']);counts=Counter();latencies=[]
        with gzip.open(path,'xt',encoding='utf-8')as stream:
            def observer(event):
                audit.observe(event);rate.observe(event['result']['action_rejected'])
                v=event['before'][side]
                if rival is not candidate:candidate.act(v) # Only this player's pre-step view, no future result input.
                proof=deepcopy(candidate.last_decision)
                if v['request_state']=='move'and not v['action_mask'][26]:
                    counts['move_decisions']+=1;counts['compared']+=not bool(proof.get('fallback'));counts['changed']+=bool(proof.get('disagrees'));latencies.append(proof.get('seconds',0.))
                stream.write(json.dumps({'ordinal':audit.steps,'rival_side':side,'before':event['before'],
                    'actions':event['actions'],'result':event['result'],'candidate_proof':proof,
                    'observed_public_delta':{s:a['public_history'][len(event['before'][s]['public_history']):]for s,a in event['after'].items()}},allow_nan=False)+'\n')
                if event['result']['action_rejected']:append(out/'public_rejections.jsonl',{'slot':slot,**event})
            t=time.monotonic()
            record=evaluate(p['checkout'],p['catalog'],{slot['player']:players[slot['player']]},cases=1,offset=slot['case'],
                rivals={slot['rival']:rival},curriculum_version='showdown-learning-curriculum-v8',tactical_diagnostics=True,
                case_provider=FrozenCase(lookup[slot['case']],{}),candidate_seat=slot['seat'],transition_observer=observer,stopping=limit.stopping)['records'][0]
        row={'slot':slot,'plan_sha256':plan_sha,'record':record,'record_sha256':content_hash(record),
            'decisions_path':str(path),'decisions_sha256':digest(path),'candidate_counts':dict(counts),
            'candidate_seconds':latencies,'game_wall_seconds':time.monotonic()-t}
        dest=out/'receipts'/f'game_{index:04d}.json';durable_json(dest,row)
        append(out/'game_ledger.jsonl',{'phase':'game_committed','index':index,'receipt_sha256':digest(dest)})
        rows.append(row)
        if len(rows)%8==0:
            elapsed=time.monotonic()-started
            atomic_json(out/'status.json',{'status':'running','games':len(rows),'target':len(game_slots),
                'games_per_second':(len(rows)-initial)/elapsed,'wall_seconds':elapsed,'resources':job.usage(),'utc':utc()})
    after={n:{'ZIP':digest(p['players'][n]['path']),'parameters':tensor_digest(m.model.policy.state_dict()),'Adam':optimizer_digest(m.model.policy)}for n,m in players.items()}
    if before!=after:raise ValueError('BR_frozen_models_mutated')
    verified=audit_receipts(out,game_slots,plan_sha);result=analyze(verified,cases,p['players']);durable_json(out/'analysis.json',result)
    durable_json(out/'execution_complete.json',{'utc':utc(),'games':len(rows),'PPO_transitions':0,'seconds':time.monotonic()-started,
        'before':before,'after':after,'resources':job.usage(),'native_total_starts':len(ledger.read_text(encoding='utf-8').splitlines()),'analysis_sha256':digest(out/'analysis.json')})
    atomic_json(out/'status.json',{'status':'complete','games':len(rows),'utc':utc()})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);parser.add_argument('--owned',action='store_true');parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if not args.owned:raise ValueError('explicit_owned_BR_launch_required')
    p,_=verify_plan(args.plan);out=Path(p['output']);out.mkdir(exist_ok=True)
    if(out/'control.json').exists()and process_alive(read(out/'control.json')['pid']):raise ValueError('BR_existing_owner_no_duplicate')
    job=WindowsJob(memory_mib=12288,cpu_percent=50,active_process_limit=12);limit=RuntimeLimit(out,3600);network=enforce_local_network_only()
    atomic_json(out/'control.json',{'pid':os.getpid(),'parent_pid':os.getppid(),'utc':utc(),'own_job':True,'inherited_job':job.inherited_job,
        'plan_sha256':digest(args.plan),'resources':p['resources'],'automatic_restarts':0})
    try:run(args.plan,job,limit,args.resume)
    except BaseException as e:
        atomic_json(out/'failure.json',{'utc':utc(),'type':type(e).__name__,'error':str(e),'resources':job.usage()});raise
    finally:limit.finished.set();atomic_json(out/'network.json',network)


if __name__=='__main__':main()
