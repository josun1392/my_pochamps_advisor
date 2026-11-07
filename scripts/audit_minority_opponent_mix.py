"""Terminal-only audit and report for the frozen minority-opponent study."""
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np
import torch

from advisor import experimental_minority_opponent as impl
from advisor.learned_execution_alignment import content_hash, digest, durable_json, masked_sample
from advisor.learned_parent_anchor import tensor_digest
from advisor.learned_selfplay_pilot import read
from advisor.learned_train_opponents import addressed_policy_seed
from scripts.pilot_critic_trainability_controlled import analyze
from scripts.pilot_minority_opponent_mix import MODELS, RIVALS, verify


def analyze_results(rows,cases):
    if len(rows)!=6400:raise ValueError('mixed_expected6400results')
    results={rival:analyze([r for r in rows if r['rival']==rival],cases,20000,116095,treatment_prefix='Am') for rival in RIVALS}
    primary=results['foundation_argmax']['comparisons']['two_seed_mean']
    verdict='MIXED_OPPONENT_CONTROLLED_EXPERIMENT_COMPLETE' if primary['cluster95CI'][0]>0 else 'DEVELOPMENT_SIGNAL_NOT_CONFIRMED'
    return results,verdict


def audit_training(root,p):
    training={}
    with zipfile.ZipFile(p['parent']['path']) as z:parent=torch.load(io.BytesIO(z.read('policy.pth')),map_location='cpu',weights_only=True)
    for name,seed in [('Am_s1',116051),('Am_s2',116053)]:
        folder=root/name;end=read(folder/'endpoint.json');assert end['new_transitions']==16384 and end['new_Adam']==512 and end['seed']==seed
        assert digest(end['path'])==end['sha256'] and end['frozen_SHA256']==p['parent']['parameters']
        with zipfile.ZipFile(end['path']) as z:
            assert z.testzip() is None
            weights=torch.load(io.BytesIO(z.read('policy.pth')),map_location='cpu',weights_only=True)
            opt=torch.load(io.BytesIO(z.read('policy.optimizer.pth')),map_location='cpu',weights_only=True)
            adam_archive=hashlib.sha256(z.read('policy.optimizer.pth')).hexdigest()
        assert all(torch.equal(t,weights[k]) for k,t in parent.items())
        assert {int(v['step']) for v in opt['state'].values()}=={512} and len(opt['state'])==2
        assert set(weights)-set(parent)==impl.EXTRA
        assert any(weights[k].any() for k in impl.EXTRA)
        updates=[json.loads(x) for x in (folder/'optimizer_updates.jsonl').read_text().splitlines()]
        assert len(updates)==512 and [x['step'] for x in updates]==list(range(1,513))
        assert all(x['groups']['critic_only']['raw_gradient_L2']==x['groups']['critic_only']['parameter_delta_L2']==0 for x in updates)
        starts=list((folder/'TRAIN_starts').glob('*.json'));assert len(starts)==end['TRAIN_starts'] and len(starts)<=4096
        policies={};traces={};episode_counts=Counter();statuses=Counter();native_counts=Counter();reject=truncated=0
        for f in (folder/'segments').glob('*/native_training/worker_*/identity_*.json'):
            identity=read(f);policy=impl.verify_training_identity(identity,seed,p['parent']['sha256']);eid=identity['episode_id']
            assert eid not in policies;policies[eid]=policy;episode_counts[policy]+=1
            ep=read(f.with_name(f.name.replace('identity_','episode_')))
            assert ep['identity_SHA256']==digest(f) and ep['trace_SHA256']==digest(ep['trace'])
            statuses[(policy,ep['status'])]+=1;rng=np.random.default_rng(identity['TRAIN_foundation_opponent']['rng_seed'])
            with gzip.open(ep['trace'],'rt',encoding='utf-8') as stream:
                events=[json.loads(s) for s in stream]
            assert len(events)==ep['native_steps'];traces[ep['trace']]=events
            for i,e in enumerate(events):
                proof=e['opponent_proof'];mask=e['before']['opponent']['action_mask'];spec=proof['TRAIN_opponent']
                assert proof['selection_index']==i and spec==identity['TRAIN_foundation_opponent']
                assert proof['episode_id']==eid and proof['revision']==e['before']['opponent']['revision']
                assert content_hash(rng.bit_generator.state)==proof['rng_before_SHA256']
                u=float(rng.random()) if policy=='foundation_masked_sample' else None
                assert u==proof['uniform'] and content_hash(rng.bit_generator.state)==proof['rng_after_SHA256']
                action=masked_sample(proof['probabilities'],mask,u) if u is not None else int(np.argmax(proof['probabilities']))
                assert action==proof['action']==e['actions']['opponent'] and mask[action]
                assert e['ordinal']==i;native_counts[policy]+=1
                reject+=int(e['result']['action_rejected']);truncated+=int(e['result']['truncated'])
        assert len(policies)==len(starts)
        assert sum(n for (policy,status),n in statuses.items() if status=='terminal')==end['completed_native_battles']
        exposure=Counter();audits=sorted((folder/'rollouts').glob('*.audit.json'));assert len(audits)==32
        entropy=[];kl=[];ratios=[];clip=[];pre_mse=[];post_mse=[]
        for a_file in audits:
            a=read(a_file);capture=Path(a['capture']);assert digest(capture)==a['capture_SHA256'] and a['transitions']==512
            assert a['Adam_after']-a['Adam_before']==16 and len(a['minibatches'])==16
            assert a['preupdate_logp_error']<=2e-5 and a['preupdate_value_error']<=2e-5
            assert a['T1_formula_error']<=2e-6 and a['GAE_error']<=2e-6 and a['return_error']<=2e-6
            join=read(str(capture).replace('.audit.npz','.native_join.json'));assert len(join['rows'])==512
            with np.load(capture,allow_pickle=False) as z, np.load(str(capture).replace('.audit.npz','.post.npz'),allow_pickle=False) as post:
                for link in join['rows']:
                    e=traces[link['native_trace']][link['native_ordinal']];t,w=link['t'],link['env']
                    assert e['decision_id']==link['decision_id'] and e['actions']['self']==link['action']==int(z['actions'].reshape(128,4)[t,w])
                    assert e['self_feature_SHA256']==link['feature_SHA256'];exposure[policies[link['episode_id']]]+=1
                assert np.isfinite(post['probabilities']).all() and not post['probabilities'][~z['native_masks']].any()
                pre_mse.append(float(np.mean((z['values'].reshape(-1)-post['returns'])**2)))
                post_mse.append(float(np.mean((post['values']-post['returns'])**2)))
            for batch in a['minibatches']:
                actual=np.exp(np.array(batch['new_logp'])-np.array(batch['old_logp']))
                assert np.isfinite(actual).all() and np.isclose(actual.min(),batch['ratio_min'],rtol=1e-5)
                entropy.append(batch['entropy']);kl.append(batch['approx_KL']);clip.append(batch['clip_fraction']);ratios.extend([batch['ratio_min'],batch['ratio_max']])
        assert sum(exposure.values())==16384
        progress=read(folder/'training_progress.json');assert progress['new_trained']==progress['new_collected']==16384 and progress['new_Adam']==512
        assert len(progress['segments'])==16
        slot=Counter()
        for segment in progress['segments']:
            for s in segment['slots']:slot[s]+=segment['transitions_per_slot']
        assert len(slot)==16 and set(slot.values())=={1024}
        training[name]={'transitions':16384,'Adam':512,'seed':seed,'ZIP_SHA256':end['sha256'],
            'Adam_archive_SHA256':adam_archive,'Adam_logical_SHA256':end['optimizer_SHA256'],
            'trainable_parameter_count':4160,'frozen_parent_tensors':len(parent),
            'native_starts':len(starts),'terminal_completed':end['completed_native_battles'],
            'episode_policy_counts':dict(episode_counts),'episode_sample_fraction':episode_counts['foundation_masked_sample']/len(starts),
            'episode_statuses':[{'policy':a,'status':b,'count':n} for (a,b),n in sorted(statuses.items())],
            'PPO_transition_policy_counts':dict(exposure),'transition_sample_fraction':exposure['foundation_masked_sample']/16384,
            'native_decision_policy_counts':dict(native_counts),'native_rejections':reject,'native_truncations':truncated,
            'template_transition_exposure':dict(slot),'entropy_mean':float(np.mean(entropy)),'KL_mean':float(np.mean(kl)),
            'clip_fraction_mean':float(np.mean(clip)),'ratio_range':[min(ratios),max(ratios)],
            'value_target_MSE_pre':float(np.mean(pre_mse)),'value_target_MSE_post_same_inputs':float(np.mean(post_mse)),
            'residual_delta_L2':float(sum(weights[k].double().square().sum() for k in impl.EXTRA)**.5),
            'seconds':end['seconds'],'transitions_per_second':16384/end['seconds']}
    return training


def audit(root,p):
    verify(root);training=audit_training(root,p);d=root/'evaluation';cases=read(root/'cases.json');lookup={c['index']:c for c in cases}
    rows=[read(f) for f in (d/'receipts').glob('*.json')];starts=[read(f) for f in (d/'starts').glob('*.json')]
    assert len(rows)==len(starts)==6400 and len({r['key'] for r in rows})==6400
    assert {s['key'] for s in starts}=={r['key'] for r in rows} and sorted(s['ordinal'] for s in starts)==list(range(6400))
    for sub,n in [('decisions',6400),('initial_public',12800),('trace_receipts',6400),('initial_native',6400)]:assert len(list((d/sub).iterdir()))==n
    models={'Foundation':p['parent'],**p['controls'],**{n:read(root/n/'endpoint.json') for n in ('Am_s1','Am_s2')}}
    before=read(d/'model_before.json');assert before==read(d/'model_after.json')
    role_counts=Counter();first={};behavior={n:Counter() for n in MODELS};rival_diversity=Counter()
    for r in rows:
        rec=r['record'];key=r['key'].replace(':','_');tr=read(d/'trace_receipts'/(key+'.json'))
        assert rec['initial_native_seed']==lookup[r['case']]['scenario']['seed'] and rec['canonical_scenario_sha256']==lookup[r['case']]['scenario_sha256']
        assert r['record_SHA256']==content_hash(rec)==tr['record_SHA256'] and r['model_SHA256']==models[r['policy']]['sha256']
        assert r['plan_SHA256']==digest(root/'plan.json') and tr['trace_SHA256']==digest(tr['trace_path'])
        assert not rec['native_choice_rejections'] and not rec['truncated']
        side='self' if r['seat']=='p1' else 'opponent';pending={};counts=Counter();rngs={}
        from scripts.evaluate_showdown_policy import seat_scenario
        assert rec['native_scenario_sha256']==content_hash(seat_scenario(lookup[r['case']]['scenario'],r['seat']))
        for line in Path(tr['trace_path']).read_text(encoding='utf-8').splitlines():
            e=json.loads(line)
            if e['phase']=='selected_before_native_step':
                role=e['role'];counts[role]+=1;role_counts[role]+=1;pending[role]=e
                assert e['policy']==(r['policy'] if role=='candidate' else r['rival'])
                assert e['rng_seed']==addressed_policy_seed(e['sampling_policy'],r['case']+91,e['rng_address'])
                if role not in rngs:rngs[role]=np.random.default_rng(e['rng_seed'])
                rng=rngs[role];assert content_hash(rng.bit_generator.state)==e['rng_before_SHA256']
                u=float(rng.random()) if e['mode']=='T1_sample' else None
                assert u==e['uniform'] and content_hash(rng.bit_generator.state)==e['rng_after_SHA256']
                expected=masked_sample(e['probabilities'],e['mask'],u) if u is not None else int(np.argmax(e['probabilities']))
                assert e['action']==expected and e['argmax']==int(np.argmax(e['probabilities'])) and e['mask'][expected] and e['global_RNG_unchanged']
                assert e['model_SHA256']==models[r['policy'] if role=='candidate' else 'Foundation']['sha256']
                assert e['rng_address']['seed_namespace']==116091
                mask=np.array(e['mask'],bool);prob=np.array(e['probabilities']);masked_sample(prob,mask,0.)
                logits=np.array([v for v,m in zip(e['legal_logits'],mask) if m]);ex=np.exp(logits-logits.max());ex/=ex.sum()
                assert np.isfinite(logits).all() and np.allclose(ex,prob[mask],rtol=2e-5,atol=2e-6) and int(mask.sum())==e['legal_count']
                if role=='candidate':
                    assert e['mode']=='argmax';behavior[r['policy']][e['selected_family']]+=1
                else:
                    assert e['sampling_policy']==r['rival'];rival_diversity[(r['rival'],'decisions')]+=1
                    if e['legal_count']>1:
                        rival_diversity[(r['rival'],'multilegal')]+=1;rival_diversity[(r['rival'],'nonargmax')]+=e['action']!=e['argmax']
            else:
                assert e['phase']=='native_result' and set(pending)=={'candidate','rival'} and not e['result']['action_rejected'] and not e['result']['truncated']
                assert e['actions'][side]==pending['candidate']['action'] and e['actions']['opponent' if side=='self' else 'self']==pending['rival']['action']
                pending={};counts['executed']+=1
        assert not pending and counts['candidate']==counts['rival']==counts['executed']==rec['decisions']
        assert e['result']['terminated'] and e['result']['winner']==rec['raw_native_winner']
        winner='self' if rec['raw_native_winner']==side else 'opponent' if rec['raw_native_winner'] else None
        assert rec['winner']==winner and rec['return']==e['result']['rewards'][side]
        for role in ('candidate','rival'):
            f=read(d/'initial_public'/(key+'_'+role+'.json'));assert f['proof']==tr['first'][role]
            baseline=read(d/'initial_public'/f'Foundation_foundation_argmax_{r["seat"]}_{r["case"]}_{role}.json')
            assert f['view']==baseline['view'] and f['proof']['input_SHA256']==baseline['proof']['input_SHA256']
        first[r['policy'],r['rival'],r['seat'],r['case']]=tr['first']['candidate']
        native=read(d/'initial_native'/(key+'.json'));base=read(d/'initial_native'/f'Foundation_foundation_argmax_{r["seat"]}_{r["case"]}.json')
        assert all(native[k]==base[k] for k in ('native_checkpoint_digest','native_state_SHA256','canonical_scenario_sha256','native_scenario_sha256'))
    results,verdict=analyze_results(rows,cases)
    first_actions={}
    for rival in RIVALS:
        for i in (1,2):
            changed=0
            for c in cases:
                for seat in ('p1','p2'):
                    a,b=[first[n,rival,seat,c['index']] for n in (f'A_s{i}',f'Am_s{i}')]
                    assert a['input_SHA256']==b['input_SHA256'] and a['mask']==b['mask'];changed+=a['action']!=b['action']
            first_actions[f'{rival}:s{i}']={'matched':640,'different_first_actions':changed,'not_terminal_causal_effect':True}
    result={'verdict':verdict,'vs_rivals':results,'training':training,'first_actions':first_actions,
        'candidate_behavior_counts':{n:dict(v) for n,v in behavior.items()},
        'rival_behavior':[{'rival':r,'metric':m,'count':n} for (r,m),n in sorted(rival_diversity.items())],
        'uncertainty':'80pair clusters preserve both training repetitions; not seed-population uncertainty'}
    durable_json(root/'analysis.json',result)
    for n,m in models.items():assert digest(m['path'])==m['sha256']
    verify(root)
    durable_json(root/'audit_complete.json',{'status':'PASS','training_transitions':32768,'Adam_steps':1024,
        'evaluation_starts':6400,'valid_results':6400,'model_games':dict(Counter(r['policy'] for r in rows)),
        'initial_native_state_groups':640,'candidate_selections':role_counts['candidate'],'rival_selections':role_counts['rival'],
        'missing_duplicate_eval_rejection_truncation_retry':0,'model_Adam_before_after_equal':True,'public_boundary':'same maintained native owner-visible view only',
        'analysis_SHA256':digest(root/'analysis.json'),'plan_SHA256':digest(root/'plan.json')})
    lines=[f'# {impl.VERSION}',f'판정: **{verdict}**','신규32,768전이·1,024 Adam, 평가6,400경기. A 대조군 재학습0.',
        '주 비교는 argmax 상대의 Am−A terminal return이며 sampled 상대는 부 비교다.']
    for rival,x in results.items():
        lines.append(f'## 상대 {rival}')
        lines.append('|모델|승|패|무|승률|\n|---|---:|---:|---:|---:|\n'+'\n'.join(f"|{n}|{o['wins']}|{o['losses']}|{o['draws']}|{o['wins']/o['games']:.4%}|" for n,o in x['outcomes'].items()))
        for n,c in x['comparisons'].items():lines.append(f"{n}: Am−A return {c['Am_minus_A_terminal_return']:+.6f}, 95% CI {c['cluster95CI']}")
    lines += ['80팀쌍 bootstrap20,000회(seed116095), 양방향 소유권/실제 좌석/native RNG/두 학습 반복을 함께 유지했다. 첫 행동 차이는 terminal 결과의 단독 인과효과가 아니다.',
        '새 완전팀/roster/joint-moveset이 과거 소스와 중복0인 개발 패널이다. 개별 species/set 완전 미학습이나 sealed 일반화 우월성을 뜻하지 않는다.',
        '훈련 episode/전이 노출, PPO logp/GAE/ratio/entropy/KL/clip/value/gradient 및 원본 SHA는 analysis.json과 audit_complete.json, source_manifest.json에 보존했다.',
        '후속 학습·평가·sealed 평가·모델 승격은 실행하지 않는다. 최종 자원/Git closure는 복귀 감사에서 별도 기록한다.']
    with (root/'REPORT_KO.md').open('x',encoding='utf-8') as f:f.write('\n\n'.join(lines)+'\n')
    return result
