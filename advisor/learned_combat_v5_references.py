"""Public conditional mechanics references, never hidden-state damage facts.

The existing damage/stat owners perform calculations. Ranges vary independent
legal investment/nature endpoints; they are conditional on neutral unobserved
modifiers, fixed noncritical single hit, and do NOT bound an actual action/KO.
"""
from functools import lru_cache
import numpy as np
from advisor.learned_encoder import identifier,TYPES
from advisor.learned_own_identity import own_player_records
from advisor.learned_tactics_encoder import public_side_conditions
from advisor.learned_public_interactions import public_history_summary
from advisor.learned_combat_v5 import active_public,current_public_prediction_knowledge,inventory
from advisor.damage.stats import calc_stat_champions,apply_boosts
from advisor.damage.formula import DamageContext,calc_damage_rolls
from advisor.damage.field import Field,SideField
from advisor.damage.abilities import get_ability,load_abilities_catalog
from advisor.damage.items import get_item,load_items_catalog
from advisor.damage.item_modifiers import speed_stat_item_mod
from advisor.damage.q12 import apply_damage_modifier
from advisor.damage.type_immunity import is_immune_by_ability
from advisor.learned_public_boosts import public_boosts,STATS

FIELDS=('out_reference_min','out_reference_max','out_reference_available',
 'out_reference_possible_hp_depletion','out_reference_all_hp_depletion',
 'type_chart_effectiveness','type_chart_known','known_ability_blocks','ability_block_evidence_known',
 'own_boosted_speed_reference','foe_speed_min','foe_speed_max','speed_reference_available','conditional_speed_relation',
 'base_priority','base_priority_known','incoming_reference_min','incoming_reference_max','incoming_reference_available',
 'incoming_possible_hp_depletion','incoming_all_hp_depletion','hidden_modifier_unknown',
 'unsupported_native_effect','switch_unboosted_entry_reference')
WIDTH=len(FIELDS);TYPE_WIDTH=len(TYPES)
WEATHER={None:'none','sunnyday':'sun','raindance':'rain','sandstorm':'sand','snowscape':'snow',
 'desolateland':'harsh-sunlight','primordialsea':'heavy-rain','deltastream':'strong-winds'}

@lru_cache(maxsize=1)
def effect_ids():
    return ({identifier(k):k for k in load_abilities_catalog()}, {identifier(k):k for k in load_items_catalog()})

def ability(value):
    return get_ability(effect_ids()[0].get(identifier(value),identifier(value))) if isinstance(value,str) else None

def item(value):
    return get_item(effect_ids()[1].get(identifier(value),identifier(value))) if isinstance(value,str) else None

@lru_cache(maxsize=2048)
def stat_range(species,stat,level=50):
    base=inventory()['public_dex'].get(species,{}).get('baseStats',{}).get(stat)
    if base is None:return None
    # Native Champions fixes IV31 and permits 0..32 points/stat. These are
    # independent legal endpoints, never a reconstructed real spread.
    return (calc_stat_champions(base,0,level,1. if stat=='hp' else .9,stat=='hp'),
            calc_stat_champions(base,32,level,1. if stat=='hp' else 1.1,stat=='hp'))

@lru_cache(maxsize=32768)
def conditional_rolls(level,power,attack,defense,move_type,source_types,target_types,physical,move_id,
                      weather,terrain,reflect,screen,veil,source_ability,target_ability,source_item,target_item,burn,
                      source_hp,source_max,target_fraction,flags=(),source_species='',target_species='',source_status='none'):
    ctx=DamageContext(attacker_level=level,move_power=power,attack_stat=attack,defense_stat=defense,
        move_type=move_type.lower(),attacker_types=tuple(t.lower() for t in source_types),
        defender_types=tuple(t.lower() for t in target_types),is_physical=physical,is_critical=False,is_spread=False,
        move_id=move_id,field=Field(weather=weather,terrain=terrain,is_doubles=False,
            defender_side=SideField(reflect=reflect,light_screen=screen,aurora_veil=veil)),
        attacker_ability=ability(source_ability),defender_ability=ability(target_ability),
        attacker_item=item(source_item),defender_item=item(target_item),burn_mod_q12=2048 if burn else 4096,
        attacker_hp_current=source_hp,attacker_hp_max=source_max,defender_hp_ratio=target_fraction,
        move_flags=flags,is_contact='contact' in flags,attacker_species=source_species,defender_species=target_species,
        attacker_condition=source_status)
    values=calc_damage_rolls(ctx)
    return min(values),max(values)

def _eff(base,kind,types):
    witnesses=getattr(base,'_reference_type_witnesses',None)
    if witnesses is None:
        witnesses={}
        for k,s in base.catalog['species'].items():
            if len(s['types'])==1:witnesses.setdefault(s['types'][0],k)
        base._reference_type_witnesses=witnesses
    v=1.
    for t in types:v*=base.catalog['effectiveness'][kind][witnesses[t]]
    return v

def public_stat_template_unsupported(view,identity):
    """Visible copied/replaced stats cannot use the displayed species template."""
    for line in reversed(view['public_history']):
        p=line.split('|')
        if len(p)<3 or p[2]!=identity:continue
        if p[1] in ('switch','drag','faint'):return False
        if p[1]=='-transform' or p[1]=='-start' and len(p)>3 and p[3].lower().removeprefix('move: ') in ('powertrick','power trick','powersplit','power split','guardsplit','guard split','speedswap','speed swap'):
            return True
    return False

def reference_features(view,base,native_moves):
    projection=base.project(view);foe=active_public(view);foe_id=identifier(foe.get('details',''))
    ft=projection['active'][1]['types'];roster=view['own_request'].get('side',{}).get('pokemon',[])
    active=next((p for p in roster if p.get('active')),None)
    slots=view['own_request'].get('active',[{}])[0].get('moves',[])
    stages_by_identity=public_boosts(view['public_history']);known=current_public_prediction_knowledge(view)
    fa=known['abilities'] if isinstance(known['abilities'],str) else ''
    fi=known['items'] if isinstance(known['items'],str) else ''
    conditions=public_side_conditions(view);weather=WEATHER.get(projection['weather'],'none') if not isinstance(projection['weather'],dict) else 'none'
    terr=view['state']['field']['terrain'];terrain=terr.removesuffix('terrain') if isinstance(terr,str) else 'none'
    history,_=public_history_summary(view,base.catalog,base.legacy.base.tactics);trick=bool(history[10])
    stat_override=public_stat_template_unsupported(view,foe.get('identity'))
    fboost=stages_by_identity.get(foe.get('identity'),dict.fromkeys(STATS));fs=None if stat_override else stat_range(foe_id,'spe');fh=None if stat_override else stat_range(foe_id,'hp')
    result=np.zeros((35,WIDTH),np.float32);threat=np.zeros((35,TYPE_WIDTH),np.float32)
    hp_fraction=foe.get('hp_fraction');hp_fraction=hp_fraction if isinstance(hp_fraction,(int,float)) else None
    for action,legal in enumerate(view['action_mask']):
        if not legal or action==26:continue
        switch=action<6;p=roster[action] if switch and action<len(roster) else active
        if p is None:continue
        stats=p.get('stats',{});stages=dict.fromkeys(STATS,0) if switch else stages_by_identity.get(view['state']['self_side']['active_identity'],dict.fromkeys(STATS))
        own_types=tuple(base.catalog['species'].get(identifier(p['details']),{}).get('types',[])) if switch else projection['active'][0]['types']
        sa=p.get('ability','');si=p.get('item','');cond=p.get('condition','');status=cond.split()[-1] if len(cond.split())>1 else None
        health=cond.split()[0].split('/')
        ohp=int(health[0]) if health and health[0].isdigit() else None;omax=int(health[1]) if len(health)==2 and health[1].isdigit() else None
        outgoing=[];incoming=[];unsupported=False
        # Highest-stat Paradox activation, variable speed abilities, conditional
        # move callbacks and public volatiles are not interpreted by this owner.
        # Their absence from a reference is explicit, never an actual KO claim.
        unmodeled_ability=any(identifier(a) in ('protosynthesis','quarkdrive','supremeoverlord') for a in (sa,fa))
        unmodeled_modifier=any(a and (ability(a) is None or not ability(a).implemented) for a in (sa,fa)) or any(i and item(i) is None for i in (si,fi))
        mids=p.get('moves',[]) if switch else [slots[action-6]['id']] if 6<=action<10 and action-6<len(slots) else []
        if not mids:unsupported=True
        row=result[action];row[21]=float(isinstance(known['abilities'],dict) or isinstance(known['items'],dict));row[23]=float(switch)
        if own_types is not None:
            threat[action]=[_eff(base,t,own_types)/4 for t in TYPES]
        if 'spe' in stats and fs is not None and ft is not None and stages['spe'] is not None and fboost['spe'] is not None:
            speed=apply_boosts(stats['spe'],int(stages.get('spe',0)))
            speed=apply_damage_modifier(speed,speed_stat_item_mod(item(si),identifier(p['details'])))
            if status=='par' and identifier(sa)!='quickfeet':speed=max(1,speed//2)
            if conditions[8]:speed*=2
            low,high=(apply_boosts(v,int(fboost.get('spe',0))) for v in fs)
            if foe.get('condition')=='par':low=max(1,low//2);high=max(1,high//2)
            if conditions[18]:low*=2;high*=2
            row[9:14]=[min(4,speed/512),min(4,low/512),min(4,high/512),1,
                (1 if speed>high else -1 if speed<low else 0)*(-1 if trick else 1)]
        for mid in mids:
            mid=identifier(mid);m=native_moves.get(mid,{})
            if not switch and m:row[14:16]=[m['priority']/7,1]
            if not m.get('referenceSupported') or not ft or own_types is None or fh is None or not omax or hp_fraction is None or unmodeled_ability:
                unsupported |= bool(m.get('category') in ('Physical','Special'));continue
            physical=m['category']=='Physical';stat='atk' if physical else 'spa';defstat='def' if physical else 'spd';fd=stat_range(foe_id,defstat)
            if fd is None or stat not in stats or stages[stat] is None or fboost[defstat] is None:continue
            attack=apply_boosts(stats[stat],int(stages.get(stat,0)))
            defence=[apply_boosts(v,int(fboost.get(defstat,0))) for v in fd]
            values=[]
            for d,h in ((defence[1],fh[1]),(defence[0],fh[0])):
                vals=conditional_rolls(50,m['power'],attack,d,m['type'],tuple(own_types),tuple(ft),physical,mid,weather,terrain,
                    bool(conditions[14]),bool(conditions[15]),bool(conditions[16]),sa,fa,si,fi,status=='brn' and identifier(sa)!='guts',ohp,omax,hp_fraction,
                    tuple(k for k,v in m['flags'].items() if v),identifier(p['details']),foe_id,'burn' if status=='brn' else status or 'none')
                values.append((vals[0]/h,vals[1]/h))
            outgoing.append((min(v[0] for v in values),max(v[1] for v in values)))
            row[5:7]=[_eff(base,m['type'],ft)/4,1]
            ab=ability(fa);mold=identifier(sa) in ('moldbreaker','teravolt','turboblaze')
            if fa:
                row[7:9]=[float(is_immune_by_ability(m['type'].lower(),mid,tuple(k for k,v in m['flags'].items() if v),ab,'Flying' not in ft,mold)),1]
        # Only moves actually revealed to the player can supply incoming references.
        for mid in foe.get('known_moves',[]):
            m=native_moves.get(identifier(mid),{})
            if not m.get('referenceSupported') or not ft or own_types is None or not omax or hp_fraction is None or fh is None or unmodeled_ability:continue
            physical=m['category']=='Physical';stat='atk' if physical else 'spa';defstat='def' if physical else 'spd';attack_range=stat_range(foe_id,stat)
            if attack_range is None or defstat not in stats or stages[defstat] is None or fboost[stat] is None:continue
            d=apply_boosts(stats[defstat],int(stages.get(defstat,0)));values=[]
            for atk,h in zip(attack_range,fh):
                vals=conditional_rolls(50,m['power'],apply_boosts(atk,int(fboost.get(stat,0))),d,m['type'],tuple(ft),tuple(own_types),physical,identifier(mid),weather,terrain,
                    bool(conditions[4]),bool(conditions[5]),bool(conditions[6]),fa,sa,fi,si,foe.get('condition')=='brn' and identifier(fa)!='guts',max(1,round(h*hp_fraction)),h,ohp/omax,
                    tuple(k for k,v in m['flags'].items() if v),foe_id,identifier(p['details']),'burn' if foe.get('condition')=='brn' else foe.get('condition') or 'none')
                values.append((vals[0]/omax,vals[1]/omax))
            incoming.append((min(v[0] for v in values),max(v[1] for v in values)))
        if outgoing:
            lo=max(v[0] for v in outgoing);hi=max(v[1] for v in outgoing)
            row[:5]=[min(4,lo),min(4,hi),1,float(hp_fraction is not None and hi>=hp_fraction),float(hp_fraction is not None and lo>=hp_fraction)]
        if incoming:
            lo=max(v[0] for v in incoming);hi=max(v[1] for v in incoming)
            row[16:21]=[min(4,lo),min(4,hi),1,float(ohp is not None and hi*omax>=ohp),float(ohp is not None and lo*omax>=ohp)]
        row[22]=float(unsupported or stat_override or unmodeled_ability or unmodeled_modifier or any(v is None for v in (*stages.values(),*fboost.values())) or any(v==1 for a in projection['active'] for v in a['effects'].values()))
    return result,threat
