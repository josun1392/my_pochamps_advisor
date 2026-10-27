'use strict';
// Narrow hypothetical initialization, NOT a replacement simulator. Never reads
// a real checkpoint, hidden request, actor logits, RNG or selected opponent team.
const fs = require('node:fs');
const {createHash} = require('node:crypto');
const {createLegalBattle} = require('./legal-battle.cjs');
const {publicRequestActions} = require('./environment.cjs');
const {proveConstantRNG} = require('./deterministic-proof.cjs');
const {loadEngine} = require('./engine.cjs');
const PIN = '942cda71d14bf0618bd57991708a2e2734b6daba';
const FORMAT = 'gen9championsbssregmc';
const STATS = ['hp','atk','def','spa','spd','spe'];
const clone = x => JSON.parse(JSON.stringify(x));
const id = x => String(x).toLowerCase().replace(/[^a-z0-9]/g,'');
const stable = x => Array.isArray(x) ? x.map(stable) : x && typeof x === 'object' ?
  Object.fromEntries(Object.keys(x).sort().map(k=>[k,stable(x[k])])) : x;
const hash = x => createHash('sha256').update(JSON.stringify(stable(x))).digest('hex');
class Unsupported extends Error {}
const requireProof = (ok, code) => { if (!ok) throw new Unsupported(code); };

function run(input, engine) {
  const view = input.view, role = view.side === 'self' ? 'p1' : 'p2', other = role === 'p1' ? 'p2' : 'p1';
  const roleName = role === 'p1' ? 'self' : 'opponent';
  const counts = {native_starts:0, native_transitions:0};
  // Same append-only schema as MicroLedger. This process is the sole writer.
  function reserve(budget) {
    const lines = fs.existsSync(input.ledger) ? fs.readFileSync(input.ledger,'utf8').trim().split('\n').filter(Boolean) : [];
    const used = lines.map(JSON.parse).filter(r=>r.budget===budget).reduce((s,r)=>s+r.count,0);
    requireProof(used < (budget === 'TRAIN_start' ? 1024 : 16384), 'native_teacher_budget_exhausted');
    const fd = fs.openSync(input.ledger,'a');
    try { fs.writeSync(fd,JSON.stringify({ordinal:lines.length,kind:budget,budget,count:1})+'\n');fs.fsyncSync(fd); }
    finally { fs.closeSync(fd); }
    if (budget === 'TRAIN_start') counts.native_starts++; else counts.native_transitions++;
  }
  const calc = new engine.Battle({formatid:FORMAT,seed:[31,37,41,43]});
  const dex = calc.dex;
  const stat = (species,set,s) => calc.statModify(dex.species.get(species).baseStats,set,s);
  const names = p => {
    const match = /slot-(\d+)$/.exec(p.ident || p.identity || '');
    requireProof(match, 'noncanonical_public_slot_identity');return Number(match[1]);
  };
  const gender = details => /, (M|F)(,|$)/.exec(details)?.[1] || undefined;
  const sid = details => dex.species.get(details.split(',')[0]).id;
  function canonical(details, moves, ability) {
    const species = dex.species.get(sid(details));
    requireProof(species.exists,'unknown_public_species');
    return {species:species.name,level:50,gender:gender(details),ability:ability || species.abilities[0],
      item:'',moves:moves?.length ? moves : ['protect'],nature:'Hardy',evs:Object.fromEntries(STATS.map(s=>[s,0]))};
  }
  function ownMaximum(p) {
    const hp = /^(\d+)\/(\d+)/.exec(p.condition);
    if (hp) return Number(hp[2]);
    // Own exact health was already delivered in the owner channel, not a
    // private opposing health query. Unknown dead-bench max HP stays nuisance.
    const label = p.ident.split(': ')[1];
    for (const line of [...view.public_history].reverse()) {
      const q=line.split('|');
      if (['switch','-damage','-heal'].includes(q[1]) && q[2]?.startsWith(role) && q[2].endsWith(': '+label)) {
        const m = /\d+\/(\d+)/.exec(q[q[1]==='switch'?4:3] || ''); if(m)return Number(m[1]);
      }
    }
    return null;
  }
  function ownSet(p) {
    const row=canonical(p.details,p.moves,p.baseAbility || p.ability), max=ownMaximum(p);
    row.item=p.item;
    requireProof(p.stats && Object.keys(p.stats).length===5,'missing_authenticated_own_stats');
    for (const nature of dex.natures.all()) {
      const set={...row,nature:nature.name,evs:{...row.evs}};let ok=true;
      for (const s of STATS) {
        const target=s==='hp'?max:p.stats[s];if(target===null)continue;
        let point=-1;
        for(let n=0;n<=32;n++){set.evs[s]=n;if(stat(row.species,set,s)===target){point=n;break;}}
        if(point<0){ok=false;break;}set.evs[s]=point;
      }
      const total=Object.values(set.evs).reduce((a,b)=>a+b,0);
      if(ok && total<=66)return set;
    }
    throw new Unsupported('no_native_legal_own_stat_witness');
  }
  const own = view.own_request.side.pokemon;
  const foeState = view.state.opponent_side;
  const foe = foeState.pokemon[foeState.active_identity];
  requireProof(sid(foe.details)==='charizard' && own.filter(p=>p.active).length===1,'narrow_species_or_active_mismatch');
  const ownActive=own.find(p=>p.active);
  requireProof(sid(ownActive.details)==='heracross','narrow_own_species_mismatch');
  ownSet(ownActive);
  const baseFoe=canonical(foe.details,['hyperbeam']);
  // Native legal endpoints, not neutral-spread facts about the real opponent.
  let minFoeSpeed=Infinity;
  for(const nature of dex.natures.all()) {
    minFoeSpeed=Math.min(minFoeSpeed,stat('charizard',{...baseFoe,nature:nature.name},'spe'));
  }
  requireProof(ownActive.stats.spe < minFoeSpeed,'unknown_speed_could_change_order');
  const ownTeam=view.state.self_side.preview.map(p=>canonical(p.details));
  const foeTeam=foeState.preview.map(p=>canonical(p.details));
  requireProof(ownTeam.length===6 && foeTeam.length===6,'full_public_preview_required');
  // Preview order supplies original slots; selected-three identities come only
  // from actual owner request / publicly observed opponent appearances.
  for(const p of own)ownTeam[names(p)]=ownSet(p);
  for(const p of Object.values(foeState.pokemon)) {
    foeTeam[names(p)]=canonical(p.details,p.known_moves?.length?p.known_moves:undefined);
  }
  const ownPick=own.map(p=>names(p)+1);
  const foeRows=[foe,...Object.values(foeState.pokemon).filter(p=>p!==foe)];
  const foePick=foeRows.map(p=>names(p)+1);
  const health=view.visible_active_health.find(p=>p.identity===foe.identity)?.condition;
  requireProof(typeof health==='string','missing_public_opponent_health_interval');
  const hpDomains = new Map();
  for(let point=0;point<=32;point++) {
    const set=clone(baseFoe);set.evs.hp=point;
    const maximum=stat('charizard',set,'hp');if(!hpDomains.has(maximum))hpDomains.set(maximum,set);
  }
  const hypotheses=[];let complete=true;const ownSlot=names(ownActive), foeSlot=names(foe);
  try {
    const nativeAbilities=Object.values(dex.species.get('charizard').abilities).map(id).sort();
    requireProof(JSON.stringify(nativeAbilities)===JSON.stringify(['blaze','solarpower']),'public_ability_domain_changed');
    const abilities=typeof foe.current_ability==='string'?[foe.current_ability]:nativeAbilities;
    requireProof(abilities.every(a=>nativeAbilities.includes(a)),'ability_domain_contradiction');
    for(const ability of abilities)for(const [maxhp,foeSet] of hpDomains) {
      const teams={self:clone(role==='p1'?ownTeam:foeTeam),opponent:clone(role==='p1'?foeTeam:ownTeam)};
      teams[other==='p1'?'self':'opponent'][foeSlot]={...clone(foeTeam[foeSlot]),evs:foeSet.evs};
      teams[other==='p1'?'self':'opponent'][foeSlot].ability=ability;
      const preview={self:role==='p1'?ownPick:foePick,opponent:role==='p1'?foePick:ownPick};
      // Each representative is natively TeamValidator-checked. No privileged
      // historical checkpoint or hidden real team is imported.
      for(const team of Object.values(teams)) {
        const errors=new engine.TeamValidator(FORMAT).validateTeam(clone(team));
        requireProof(!errors,'public_hypothesis_legality: '+(errors||[]).join('; '));
      }
      reserve('TRAIN_start');
      const b=createLegalBattle({teams,preview,seed:[31,37,41,43]},engine,requireProof);
      try {
        for(const side of b.sides) {
          for(const p of side.pokemon)if(!p.isActive)p.faint();
        }
        b.faintMessages();
        const a=b[role].active[0],f=b[other].active[0];
        requireProof(a.name===`slot-${ownSlot}` && f.name===`slot-${foeSlot}`,'native_slot_contradiction');
        requireProof(f.maxhp===maxhp,'native_hp_domain_contradiction');
        a.hp=Number(ownActive.condition.split('/')[0]);
        a.setAbility(ownActive.ability);f.setAbility(ability);
        a.moveSlots.forEach((m,i)=>{
          const source=view.own_request.active[0].moves[i];
          requireProof(source && source.id===m.id && source.maxpp===m.maxpp,'native_own_PP_or_slot_contradiction');
          m.pp=source.pp;
        });
        f.addVolatile('mustrecharge');b.turn=view.turn;
        b.log=[...view.public_history];
        let candidateHP=[];
        for(let hp=1;hp<=maxhp;hp++){f.hp=hp;if(f.getHealth().shared===health)candidateHP.push(hp);}
        if(!candidateHP.length)throw new Unsupported('public_HP_display_has_no_native_witness');
        requireProof(candidateHP.every(hp=>hp<=50),'fixed_damage_not_guaranteed_HP_depletion');
        for(const hp of candidateHP) {
          f.hp=hp;b.makeRequest('move');
          const checkpoint=clone(b.toJSON());
          reserve('TRAIN_start');const branch=engine.Battle.fromJSON(checkpoint);branch.restart(()=>{});
          try {
            const target=branch[other].active[0];
            const choices=publicRequestActions(branch[role].activeRequest,false);
            requireProof(JSON.stringify(choices)===JSON.stringify(view.choices),'native_own_legal_mask_contradiction');
            const responses=publicRequestActions(branch[other].activeRequest,false).filter(x=>x!==null);
            requireProof(responses.length===1 && responses[0]==='move 1','opponent_availability_not_forced');
            requireProof(branch[other].activeRequest.active[0].moves[0].id==='recharge','native_recharge_not_confirmed');
            const channel=role==='p1'?1:2;
            const history=engine.extractChannelMessages(branch.log.join('\n'),[channel])[channel];
            const before={turn:branch.turn,request_state:branch.requestState,own_request:clone(branch[role].activeRequest),
              visible_active_health:branch.sides.filter(s=>s.id!==role).flatMap(s=>s.active.filter(Boolean).map(p=>({identity:p.toString(),condition:p.getHealth().shared}))),
              action_mask:choices.map(c=>c===null?0:1),choices,public_history:history};
            if(input.inspect)return {status:'inspection_only_no_target',before,...counts};
            // Fixed-damage dependency certificate: no unknown offensive or
            // defensive stat may be read in this entire native resolution.
            const accesses=[];const original=target.getStat;
            target.getStat=function(s,...args){accesses.push(s);requireProof(s==='spe','unmodeled_hidden_stat_dependency');return original.call(this,s,...args);};
            target.storedStats=new Proxy(target.storedStats,{get(object,key){
              if(typeof key==='string' && STATS.includes(key))requireProof(key==='spe','unmodeled_stored_stat_dependency');
              return object[key];
            }});
            reserve('transition');
            const proof=proveConstantRNG(branch,()=>{
              requireProof(branch[role].choose(choices[input.action]),'illegal_own_native_candidate');
              requireProof(branch[other].choose('move 1'),'illegal_forced_response');
              requireProof(branch.allChoicesDone(),'native_joint_choice_incomplete');
              branch.commitChoices();return {ended:branch.ended,winner:branch.winner};
            },'complete_native_joint_turn_fixed_damage_terminal_endgame');
            const ended=branch.ended && branch.winner===roleName;
            requireProof(ended,'native_terminal_win_not_proven');
            hypotheses.push({max_hp:maxhp,current_hp:hp,ability,before,terminated:true,truncated:false,terminal_return:1,
              own_choice:choices[input.action],opponent_choice:'move 1',hidden_stat_reads:accesses,
              proof:proof.proof,constructed_checkpoint_SHA256:hash(checkpoint)});
          } finally {branch.destroy();}
        }
      } finally {b.destroy();}
    }
  } catch(e) {
    if(!(e instanceof Unsupported) && e.name!=='NativeRandomnessRequired')throw e;
    complete=false;
    return {status:'abstain',reason:e.message,engine_commit:PIN,...counts,completed_witnesses:hypotheses.length};
  } finally {calc.destroy();}
  return {status:'proven',engine_commit:PIN,complete_HP_domain:complete,hypotheses,...counts,stochastic_draws:0,
    omitted_variable_contract:'all_unrevealed_moves_and_nonHP_spreads_are_nuisance_only_under_public_locked_recharge_inert_known_abilities_no_items_strict_speed_order_fixed_damage_and_native_dependency_guard',
    distribution:'none_no_hidden_set_or_response_probability_assigned'};
}

module.exports={run};
if(require.main===module)try {
  const payload=fs.readFileSync(0,'utf8');if(Buffer.byteLength(payload)>1024*1024)throw new Error('bounded_input_required');
  process.stdout.write(JSON.stringify(run(JSON.parse(payload),loadEngine(process.argv[2]))));
} catch(e) {process.stdout.write(JSON.stringify({status:'error',reason:e instanceof Unsupported?e.message:'public_native_teacher_failed'}));process.exitCode=1;}
