"""Opt-in bounded public response game, NOT a simulator or optimality oracle.

One current decision against <=8 publicly supported response hypotheses. Damage
references are conditional on independent legal stat endpoints and neutral
UNOBSERVED modifiers, not bounds on the actual hidden set. Scenario weights are
declared heuristics, not calibrated action probabilities. No native handle or
learned opponent inference is accepted. Legacy policies/features are unchanged.
"""
from collections import Counter
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess
from time import perf_counter

from advisor.learned_encoder import identifier, fingerprint
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_public_tactical_opponent import FORBIDDEN, public_reference_owner, own_fraction

VERSION = 'public_observation_best_response_v1'
CONTRACT = {
    'version': VERSION, 'max_responses': 8, 'attacks': 4, 'public_bench_responses': 2,
    'mean_weight': .75, 'worst_weight': .25, 'position_weight': .22,
    'own_ko_cost': .8, 'foe_ko_gain': .65, 'tempo_cost': .025,
    'hypothesis_weights': 'revealed2_unrevealed1_status1_switch1_not_calibrated',
    'damage': 'conditional_single_hit_reference_accuracy_mean_no_hidden_modifiers',
    'search': 'one_joint_turn_plus_discounted_nominal_matchup_not_native_rollout',
}
HEALS = frozenset(('recover','roost','softboiled','slackoff','milkdrink','shoreup','synthesis','moonlight','morningsun'))


def validate_view(view):
    if FORBIDDEN & set(view): raise ValueError('privileged_best_response_input')
    mask=view.get('action_mask',[])
    if len(mask)!=35 or any(v not in (0,1,False,True) for v in mask) or not any(mask):
        raise ValueError('invalid_public_legal_mask')
    role='p1' if view.get('side')=='self' else 'p2' if view.get('side')=='opponent' else None
    request=view.get('own_request',{}).get('side',{})
    if role is None or request and request.get('id')!=role:
        raise ValueError('own_public_request_role_mismatch')
    return [i for i,m in enumerate(mask)if m]


def response_value(p, foe_hp):
    """Bounded positional utility, never a terminal return/win probability.

    Incoming HP loss on a voluntary switch is charged to the arriving bench;
    the departing active's health is preserved. A switch does not attack.
    """
    hp=p['hp'];hit=p.get('incoming',0.);damage=p.get('damage',0.)
    heal=min(1-hp,p.get('heal',0.));kind=p['kind']
    first=p.get('first',.5)
    def ordered(own_first):
        h,f=hp,min(1.,foe_hp+p.get('foe_heal',0.))
        incoming=hit*(1-p.get('protection',0.))
        if kind=='switch':h-=incoming
        elif own_first:
            h+=heal;f-=damage;h-=p.get('self_cost',0.)
            if f>0:h-=incoming
        else:
            h-=incoming
            if h>0:h+=heal;f-=damage;h-=p.get('self_cost',0.)
        gained=foe_hp-max(0,min(1,f));lost=hp-max(0,min(1,h))
        value=gained-lost
        if h<=0:value-=CONTRACT['own_ko_cost']
        if f<=0:value+=CONTRACT['foe_ko_gain']
        if h>0 and f>0:value+=p.get('potential',0.)*CONTRACT['position_weight']+p.get('effect',0.)
        return value-CONTRACT['tempo_cost']
    return first*ordered(True)+(1-first)*ordered(False)


def choose_response(rows, baseline):
    proof=[]
    for row in rows:
        values,weights=row['utilities'],row['weights']
        if (not values or len(values)!=len(weights) or
            any(not math.isfinite(v) for v in (*values,*weights)) or min(weights)<=0):
            raise ValueError('invalid_public_response_matrix')
        mean=sum(v*w for v,w in zip(values,weights))/sum(weights)
        proof.append({**row,'scenario_mean':mean,'worst_scenario':min(values),
            'conservative_score':CONTRACT['mean_weight']*mean+CONTRACT['worst_weight']*min(values)})
    if not proof:raise ValueError('empty_public_response_matrix')
    best=max(proof,key=lambda r:(r['conservative_score'],r['action']==baseline,-r['action']))
    return best['action'],proof


@lru_cache(maxsize=2)
def response_metadata(checkout):
    from advisor.showdown_bridge import SHOWDOWN_COMMIT,FORMAT_ID
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()!=SHOWDOWN_COMMIT:
        raise ValueError('best_response_native_pin_mismatch')
    path=Path(__file__).resolve().parents[1]/'tools/showdown_bridge/public-response-metadata.cjs'
    data=json.loads(subprocess.check_output(['node',str(path),checkout],text=True))
    if data.get('schema_version')!='pinned-public-response-metadata-v1' or data['format_id']!=FORMAT_ID:
        raise ValueError('best_response_metadata_mismatch')
    return data['moves']


class PublicBestResponseOpponent:
    kind=VERSION

    def __init__(self,seed=0,*,catalog=None,checkout):
        catalog=catalog or Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'
        self.reference,self.native_moves=public_reference_owner(str(catalog))
        self.moves=response_metadata(str(checkout));self.base=VisibleBaseline('tactical_heuristic',seed)
        self.model_id=VERSION+':'+fingerprint({'contract':CONTRACT,'metadata':self.moves,
            'catalog':self.reference.catalog_fingerprint,
            'source':sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest()})
        self.last_decision=None;self.counts=Counter();self._key=None

    def _context(self,view):
        from advisor.learned_combat_v5 import active_public,current_public_prediction_knowledge,inventory
        from advisor.learned_combat_v5_strategic import public_species_candidates
        from advisor.learned_own_identity import own_player_records
        from advisor.learned_public_boosts import public_boosts,STATS
        from advisor.learned_tactics_encoder import public_side_conditions
        from advisor.learned_public_interactions import public_history_summary
        from advisor.learned_combat_v5_references import stat_range,public_stat_template_unsupported
        own_player_records(view)
        projection=self.reference.project(view);foe=active_public(view)
        names=public_species_candidates(view)
        if len(names)!=1 or projection['active'][1]['types'] is None:
            raise LookupError('ambiguous_public_species_or_current_types')
        if public_stat_template_unsupported(view,foe.get('identity')):
            raise LookupError('public_copied_stats_unavailable')
        if not isinstance(foe.get('hp_fraction'),(int,float)) or not 0<foe['hp_fraction']<=1:
            raise LookupError('unknown_public_opponent_health')
        if projection['unsupported']:raise LookupError('unsupported_public_projection')
        stages=public_boosts(view['public_history']);known=current_public_prediction_knowledge(view)
        roster=view['own_request']['side']['pokemon'];own=[]
        for index,p in enumerate(roster):
            fraction=own_fraction(p)
            if fraction is None:own.append(None);continue
            sid=identifier(p['details']);active=p.get('active',False)
            own.append({'identity':p['ident'],'species':sid,'types':tuple(projection['active'][0]['types']) if active and projection['active'][0]['types'] is not None else tuple(self.reference.catalog['species'].get(sid,{}).get('types',[])),
                'stats':{k:(v,v)for k,v in p.get('stats',{}).items()},
                'stages':stages.get(view['state']['self_side']['active_identity'],dict.fromkeys(STATS,0)) if active else dict.fromkeys(STATS,0),
                'max_hp':tuple([int(p['condition'].split()[0].split('/')[1])]*2),
                'hp':fraction,'ability':p.get('ability',''),'item':p.get('item',''),
                'status':p['condition'].split()[1] if len(p['condition'].split())>1 else None,
                'moves':[identifier(m)for m in p.get('moves',[])], 'own':True,'index':index,'active':active})
        active=next((p for p in own if p and p['active']),None)
        if not active:raise LookupError('missing_authenticated_own_active')
        if any(v is None for v in active['stages'].values()):raise LookupError('unknown_own_boost')
        def public_actor(row,types):
            sid=identifier(row.get('details',''))
            stats={s:stat_range(sid,s)for s in STATS}
            h=stat_range(sid,'hp')
            if h is None or any(stats[s] is None for s in ('atk','def','spa','spd','spe')):return None
            return {'identity':row.get('identity'), 'species':sid,'types':tuple(types),
                'stats':stats,'stages':stages.get(row.get('identity'),dict.fromkeys(STATS,0)),
                'max_hp':h,'hp':row.get('hp_fraction'),
                'ability':row.get('current_ability') if isinstance(row.get('current_ability'),str) else '',
                'item':row.get('known_item') if isinstance(row.get('known_item'),str) else '',
                'status':row.get('condition') if isinstance(row.get('condition'),str) else None,
                'moves':[identifier(m)for m in row.get('known_moves',[])],'own':False}
        other=public_actor(foe,projection['active'][1]['types'])
        if other is None or any(v is None for v in other['stages'].values()):raise LookupError('unknown_opponent_stat_template')
        # Runtime form changes invalidate old ability evidence unless re-revealed.
        other['ability']=known['abilities'] if isinstance(known['abilities'],str) else ''
        other['item']=known['items'] if isinstance(known['items'],str) else ''
        bench=[]
        for row in view['state']['opponent_side']['pokemon'].values():
            # Only actually seen living bench identities. Preview is NOT selected-three evidence.
            if row.get('identity')==foe.get('identity') or row.get('fainted') is not False or not isinstance(row.get('hp_fraction'),(float,int)):continue
            sid=identifier(row.get('details',''));types=self.reference.catalog['species'].get(sid,{}).get('types')
            if types:
                p=public_actor(row,types)
                if p and all(v is not None for v in p['stages'].values()):bench.append(p)
        history,_=public_history_summary(view,self.reference.catalog,self.reference.legacy.base.tactics)
        return {'own':own,'active':active,'foe':other,'bench':bench[:2],
            'projection':projection,'conditions':public_side_conditions(view),'trick':bool(history[10]),
            'unknown_foe_ability':isinstance(known['abilities'],dict),
            'unknown_foe_item':isinstance(known['items'],dict),'memo':{},'view':view,
            'entry':inventory()['species'].get(names[0],{})}

    def _damage(self,source,target,mid,ctx):
        from advisor.learned_combat_v5_references import conditional_rolls,WEATHER,_eff,ability
        from advisor.damage.type_immunity import is_immune_by_ability
        from advisor.damage.stats import apply_boosts
        key=(source['identity'],target['identity'],mid)
        if key in ctx['memo']:return ctx['memo'][key]
        m=self.moves.get(mid,{})
        if m.get('category') not in ('Physical','Special'):return (0.,0.,'not_damaging')
        physical=m['category']=='Physical';a='atk'if physical else'spa';d='def'if physical else'spd'
        assumptions=[];power=m.get('power',0)
        if m.get('charge'):assumptions.append('charge_average_two_turn_opportunity')
        if m.get('variablePower'):assumptions.append('nominal_variable_power_not_actual')
        if m.get('fixedDamage'):
            amount=50 if m['fixedDamage']=='level' else m['fixedDamage']
            if not isinstance(amount,(int,float)):amount=0
            values=(amount/target['max_hp'][1],amount/target['max_hp'][0])
            if (_eff(self.reference,m['type'],target['types'])==0 or is_immune_by_ability(
                m['type'].lower(),mid,tuple(k for k,v in m.get('flags',{}).items()if v),ability(target['ability']),
                'Flying'not in target['types'],identifier(source['ability'])in('moldbreaker','teravolt','turboblaze'))):values=(0.,0.)
            assumptions.append('fixed_damage_nominal_type_and_ability_uncertainty')
        elif power>0 and source['types'] and target['types']:
            values=[]
            for end in (0,1):
                attack=apply_boosts(source['stats'][a][end],source['stages'].get(a,0))
                defense=apply_boosts(target['stats'][d][1-end],target['stages'].get(d,0))
                side=ctx['conditions'][10:20]if source['own']else ctx['conditions'][:10]
                weather=ctx['projection']['weather'];weather=WEATHER.get(weather,'none') if isinstance(weather,(str,type(None)))else'none'
                terrain=ctx['view']['state']['field'].get('terrain');terrain=terrain.removesuffix('terrain')if isinstance(terrain,str)else'none'
                rolls=conditional_rolls(50,power,attack,max(1,defense),m['type'],source['types'],target['types'],physical,mid,
                    weather,terrain,bool(side[4]),bool(side[5]),bool(side[6]),source['ability'],target['ability'],source['item'],target['item'],
                    source['status']=='brn' and identifier(source['ability'])!='guts',
                    max(1,round(source['hp']*source['max_hp'][end])),source['max_hp'][end],target['hp'],
                    tuple(k for k,v in m.get('flags',{}).items()if v),source['species'],target['species'],source['status']or'none')
                values.append(rolls[end]/target['max_hp'][1-end])
        else:return (0.,0.,'unavailable_power_callback_not_assumed_effective')
        scale=1.
        mh=m.get('multihit')
        if mh:
            scale=float(mh)if isinstance(mh,int)else 3.
            assumptions.append('nominal_multihit_count')
        if m.get('charge'):scale*=.5
        # Hit chance is nominal (no invented accuracy/evasion/hidden-item facts).
        accuracy=1. if m.get('accuracy')is True else max(0.,min(1.,float(m.get('accuracy',100))/100))
        values=tuple(max(0.,min(4.,v*scale*accuracy))for v in values)
        answer=(*values,'conditional_neutral_unobserved_modifiers;'+','.join(assumptions))
        ctx['memo'][key]=answer;return answer

    def _hypotheses(self,ctx):
        from advisor.learned_combat_v5_strategic import priors
        data,_=priors();entry=ctx['entry'];foe=ctx['foe']
        counts=data['species'].get(identifier(entry.get('start_species','')),{}).get('moves',{})
        revealed=set(foe['moves']);allowed=set(entry.get('moves',[]))|revealed
        attacks=[m for m in allowed if self.moves.get(m,{}).get('category')in('Physical','Special') and (self.moves[m]['power']or self.moves[m]['fixedDamage'])]
        attacks.sort(key=lambda m:(m in revealed,counts.get(m,0),self.moves[m]['type']in foe['types'],self.moves[m]['power']),reverse=True)
        selected=[];types=set()
        # Revealed attacks first, then distinct attack types; at most four.
        for m in attacks:
            if m in revealed or self.moves[m]['type']not in types:
                selected.append(m);types.add(self.moves[m]['type'])
            if len(selected)==4:break
        result=[{'kind':'attack','move':m,'actor':foe,'weight':2 if m in revealed else 1,
            'basis':'public_revealed'if m in revealed else'canonical_legal_learnset_hypothesis',
            'current_availability':'unknown_no_private_request'}for m in selected]
        if ctx['projection']['active'][1]['effects'].get('recharge')is True:
            return [{'kind':'wait','move':None,'actor':foe,'weight':1,'basis':'public_recharge_evidence','current_availability':'public_forced_recharge'}]
        taunted=ctx['projection']['active'][1]['effects'].get('taunt')is True
        for kind,predicate in (('recovery',lambda m:m in HEALS and foe['hp']<.8),
                               ('status',lambda m:self.moves.get(m,{}).get('status')and not ctx['active']['status'])):
            possibilities=[m for m in allowed if predicate(m)]
            if possibilities and not taunted:
                m=max(possibilities,key=lambda x:(x in revealed,counts.get(x,0),x))
                result.append({'kind':kind,'move':m,'actor':foe,'weight':1,
                    'basis':'public_revealed'if m in revealed else'canonical_legal_learnset_hypothesis','current_availability':'unknown_no_private_request'})
        if ctx['projection']['active'][1]['effects'].get('trapped')is not True:
            result += [{'kind':'switch','move':None,'actor':p,'weight':1,'basis':'previously_public_living_identity',
                        'current_availability':'unknown_trap_or_selection_not_observed'}for p in ctx['bench']]
        return result[:CONTRACT['max_responses']]

    def _first(self,own,foe,mid,response,ctx):
        from advisor.damage.stats import apply_boosts
        if response['kind']=='switch':return 0. # native switching precedes ordinary moves
        a=self.moves.get(mid,{}).get('priority',0);b=self.moves.get(response['move'],{}).get('priority',0)
        # Nominal priorities and legal stat endpoints, NOT exact hidden action order.
        if a!=b:return float(a>b)
        so=[apply_boosts(v,own['stages'].get('spe',0))for v in own['stats']['spe']]
        sf=[apply_boosts(v,foe['stages'].get('spe',0))for v in foe['stats']['spe']]
        if own['status']=='par':so=[v/2 for v in so]
        if foe['status']=='par':sf=[v/2 for v in sf]
        relation=1. if so[0]>sf[1] else 0. if so[1]<sf[0] else .5
        # Unknown speed modifiers retain ambiguity rather than a forced order.
        if ctx['unknown_foe_ability']or ctx['unknown_foe_item']or own['item']or own['ability']:relation=.5
        return 1-relation if ctx['trick']else relation

    def _matrix(self,ctx,allowed,baseline):
        from advisor.learned_combat_v5_references import _eff
        view=ctx['view'];responses=self._hypotheses(ctx)
        if not responses:raise LookupError('no_public_supported_response')
        rows=[];unavailable=[]
        for action in allowed:
            choice=str(view['choices'][action]);match=re.search(r'\bmove (\d+)',choice)
            switch=action<6
            own=ctx['own'][action]if switch and action<len(ctx['own'])else ctx['active']
            if own is None:continue
            mid=None;move={};kind='switch'if switch else'other'
            if not switch:
                if not match:continue
                slot=int(match.group(1))-1;slots=view['own_request'].get('active',[{}])[0].get('moves',[])
                if not 0<=slot<len(slots):raise ValueError('public_native_choice_slot_mismatch')
                mid=identifier(slots[slot]['id']);move=self.moves.get(mid,{})
                kind='attack'if move.get('category')in('Physical','Special')else'recovery'if mid in HEALS else'defense'if move.get('protect')else'status'
                if kind=='attack'and not(move.get('power')or move.get('fixedDamage')):
                    unavailable.append({'action':action,'reason':'unavailable_damage_callback'});continue
                if kind=='status'and not any(move.get(k)for k in('status','boosts','sideCondition')):
                    unavailable.append({'action':action,'reason':'unmodeled_status_effect'});continue
            utilities=[];weights=[];pairs=[]
            # Future potential uses own known move set, not hypothetical future legality.
            for response in responses:
                foe=response['actor'];incoming=0.;out=0.;effect=0.;heal=0.;protection=0.;self_cost=0.
                in_reference=None;out_reference=None
                if response['kind']=='attack':
                    in_reference=self._damage(foe,own,response['move'],ctx);lo,hi,_=in_reference;incoming=(lo+hi)/2
                if kind=='attack':
                    out_reference=self._damage(own,foe,mid,ctx);lo,hi,basis=out_reference;out=(lo+hi)/2
                    # Substitute is public evidence that damage is not direct HP loss.
                    if ctx['projection']['active'][1]['effects'].get('substitute')is True and response['kind']!='switch':
                        effect+=min(.18,out);out=0.
                    if move.get('recoil'):self_cost+=min(foe['hp'],out)*sum(foe['max_hp'])/sum(own['max_hp'])*move['recoil'][0]/move['recoil'][1]
                    if move.get('drain'):heal=min(foe['hp'],out)*sum(foe['max_hp'])/sum(own['max_hp'])*move['drain'][0]/move['drain'][1]
                    if move.get('selfdestruct'):self_cost+=own['hp']+1
                    if move.get('selfBoosts'):effect+=.035*sum(move['selfBoosts'].values())
                elif kind=='recovery':
                    heal=0. if ctx['projection']['active'][0]['effects'].get('healblock')is True else .5
                elif kind=='defense':
                    protection=1. if response['kind']=='attack'else 0.
                    # Repeated protection is not modeled as certain success.
                    last=[x.split('|')[3]for x in view['public_history']if x.startswith('|move|'+str(ctx['projection']['active'][0]['identity'])+'|')]
                    if last and self.moves.get(identifier(last[-1]),{}).get('protect'):protection/=3
                    effect-=.07
                elif kind=='status':
                    if move.get('status')and not foe['status']:
                        status=move['status'];immune=(status in('tox','psn')and any(t in foe['types']for t in('Poison','Steel'))or status=='brn'and'Fire'in foe['types']or status=='par'and'Electric'in foe['types'])
                        if not immune:effect+=.13
                    if move.get('boosts'):
                        boosts=move['boosts'];self_target=move.get('target')=='self'
                        effect+=.06*sum(max(0,v)if self_target else max(0,-v)for k,v in boosts.items())
                    if move.get('sideCondition'):effect+=.06
                if response['kind']=='status'and not own['status']:effect-=.10
                hazard=0.
                if switch:
                    side=ctx['conditions'];hazard=(.125*_eff(self.reference,'Rock',own['types'])if side[2]else 0.)
                    if 'Flying'not in own['types']and identifier(own['ability'])!='levitate':
                        hazard+=({1:.125,2:1/6,3:.25}.get(round(side[0]*3),0.))
                    if identifier(own['item'])=='heavydutyboots'or identifier(own['ability'])=='magicguard':hazard=0.
                    incoming+=hazard
                future=max((sum(self._damage(own,foe,m,ctx)[:2])/2 for m in own['moves']),default=0.)
                potential=max(-1.,min(1.,future-incoming))
                p={'kind':kind,'hp':own['hp'],'damage':max(0.,out),'incoming':incoming,'heal':heal,
                    'protection':protection,'self_cost':self_cost,'first':0. if switch else self._first(own,foe,mid,response,ctx),
                    'foe_heal':min(.5,1-foe['hp']) if response['kind']=='recovery'else 0.,
                    'effect':effect,'potential':potential}
                utility=response_value(p,foe['hp']);utilities.append(utility);weights.append(response['weight'])
                pairs.append({'response':{k:v for k,v in response.items()if k!='actor'},
                    'public_target':foe['identity'],'conditional_pair':p,'utility':utility,
                    'incoming_reference':in_reference,'outgoing_reference':out_reference})
            rows.append({'action':action,'kind':kind,'move':mid,'utilities':utilities,'weights':weights,'pairs':pairs,
                'native_transformation_alias':bool(match and action>=10),
                'transformation_scope':'pre_transformation_reference_not_exact_new_form'if match and action>=10 else None})
        return rows,responses,unavailable

    def act(self,view):
        allowed=validate_view(view)
        if allowed==[26]:self.last_decision={'action':26,'fallback':'administrative_wait'};return 26
        key=fingerprint(view)
        if key==self._key:return self.last_decision['action']
        start=perf_counter();baseline=self.base.act(view)
        if baseline not in allowed:raise ValueError('best_response_baseline_mask_violation')
        action=baseline;rows=[];responses=[];unavailable=[];fallback=None
        try:
            if view['request_state']!='move':raise LookupError('forced_or_administrative_request')
            ctx=self._context(view);rows,responses,unavailable=self._matrix(ctx,allowed,baseline)
            if len(rows)<2:raise LookupError('insufficient_supported_legal_candidates')
            action,rows=choose_response(rows,baseline)
        except LookupError as e:fallback=str(e)
        if action not in allowed:raise ValueError('best_response_mask_violation')
        probabilities=[float(a==action)for a in range(35)]
        self.last_decision={'version':VERSION,'action':action,'baseline_action':baseline,'disagrees':action!=baseline,
            'action_probabilities':probabilities,'fallback':fallback,'comparisons':rows,'unavailable_candidates':unavailable,
            'responses':[{**{k:v for k,v in r.items()if k!='actor'},'public_actor':r['actor']['identity']}for r in responses],
            'legal_actions':allowed,'seconds':perf_counter()-start,
            'limitations':['hypothesis_weights_not_calibrated','unrevealed_availability_unknown','unknown_modifiers_neutral_condition_only',
                'no_critical_secondary_or_complete_residual_interpreter','switch_entry_abilities_and_unseen_bench_not_predicted',
                'nominal_accuracy_and_conditional_order','pre_transform_alias_reference','heuristic_position_not_native_outcome']}
        self._key=key;self.counts['decisions']+=1;self.counts['compared']+=not bool(fallback);self.counts['changed']+=action!=baseline
        return action

    def drain_counts(self):
        result=dict(self.counts);self.counts.clear();return result
