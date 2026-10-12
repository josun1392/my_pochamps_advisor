'use strict';
// Set/team construction only. Legality, learnability and mechanics stay upstream.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const {loadEngine} = require('./engine.cjs');
const PIN = '942cda71d14bf0618bd57991708a2e2734b6daba';
const FORMAT = 'gen9championsbssregmc';
const VERSION = 'showdown-mc-legal-domain-v1';
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));
const stats = {hp:11,atk:11,def:11,spa:11,spd:11,spe:11};
const clean = set => Object.fromEntries(['species','moves','ability','item','nature','evs','ivs','level','gender']
  .filter(k => set[k] !== undefined).map(k => [k, set[k]]));
function pinned(checkout) {
  if (execFileSync('git', ['-C',checkout,'rev-parse','HEAD'], {encoding:'utf8'}).trim() !== PIN ||
      execFileSync('git', ['-C',checkout,'status','--porcelain','--untracked-files=no'], {encoding:'utf8'}).trim()) {
    throw new Error('pinned_clean_engine_required');
  }
}
function audit(checkout) {
  pinned(checkout);
  const engine = loadEngine(checkout), dex = engine.Dex.mod('champions');
  const validator = new engine.TeamValidator(FORMAT);
  const source = engine.Teams.getGenerator(FORMAT, [1,2,3,4]).randomSets;
  const species = {}, excluded = {}, abilities = new Set(), moves = new Set(), battleAbilities = new Set();
  const legalMoves = dex.moves.all().filter(m => !validator.checkMove({name:'audit'}, m, {}));
  // Dex.all() omits virtual cosmetic aliases used by RandomTeams.getForme.
  const allSpecies = new Map(dex.species.all().map(p => [p.id,p]));
  for (const p of dex.species.all()) {
    for (const name of [...(p.cosmeticFormes || []),...(p.otherFormes || [])]) {
      const alias = dex.species.get(name);
      if (alias.exists) allSpecies.set(alias.id,alias);
    }
  }
  for (const p of [...allSpecies.values()].sort((a,b) => a.id.localeCompare(b.id))) {
    const eligibility = validator.checkSpecies({name:p.name,species:p.name},p,p,{});
    if (eligibility) { excluded[p.id] = {stage:'species_rule',reasons:[eligibility]}; continue; }
    const start = dex.species.get(p.battleOnly || p.name);
    const candidates = [...new Set(dex.species.getFullLearnset(start.id).flatMap(x => Object.keys(x.learnset)))];
    if (candidates.includes('sketch')) candidates.push(...legalMoves.map(m => m.id));
    const perAbility = {}, witnesses = {};
    for (const ability of new Set(p.requiredAbility ? [p.requiredAbility] : Object.values(start.abilities))) {
      const accepted = [];
      for (const move of [...new Set(candidates)].sort()) {
        const set = {species:p.name,ability,item:p.requiredItem || '',nature:'Serious',level:50,
          evs:clone(stats), moves:[move]};
        if (!validator.validateSet(set, {})) {
          accepted.push(dex.moves.get(move).id);
          if (!witnesses[ability]) witnesses[ability] = clean(set);
        }
      }
      if (accepted.length) perAbility[ability] = accepted;
    }
    if (!Object.keys(perAbility).length) {
      const set = {species:p.name,ability:Object.values(start.abilities)[0],item:p.requiredItem || '',
        moves:[candidates[0] || 'tackle'],nature:'Serious',level:50,evs:clone(stats)};
      excluded[p.id] = {stage:'no_legal_start_set', reasons:validator.validateSet(set,{}) || ['no witness']};
      continue;
    }
    const witness = witnesses[Object.keys(perAbility)[0]];
    const kind = p.isMega ? 'mega' : p.battleOnly ? 'ability_transformation' : 'selectable';
    species[p.id] = {name:p.name,base_species:p.baseSpecies,kind,start_species:witness.species,
      required_item:p.requiredItem || null,required_ability:p.requiredAbility || null,
      abilities:Object.keys(perAbility),moves:[...new Set(Object.values(perAbility).flat())].sort(),
      moves_by_ability:perAbility,witness,random_set_source:!!source[p.id]};
    Object.keys(perAbility).forEach(a => abilities.add(a));
    species[p.id].moves.forEach(m => moves.add(m));
    if (kind !== 'selectable') Object.values(p.abilities).forEach(a => battleAbilities.add(a));
  }
  const fillers = Object.values(species).filter(p => p.kind === 'selectable' && !p.required_item);
  function complete(set) {
    const base = dex.species.get(set.species).baseSpecies;
    const used = new Set([base]), team = [clone(set)];
    for (const p of fillers) {
      if (used.has(p.base_species)) continue;
      used.add(p.base_species); team.push(clone(p.witness));
      if (team.length === 6) break;
    }
    const errors = validator.validateTeam(team);
    if (errors) throw new Error(`legal_domain_witness_team_failed:${errors.join(';')}`);
    return team;
  }
  // Every entry is backed by an entire legal six-member team, not just a tag check.
  for (const p of Object.values(species)) p.team_witness_sha256 = hash(JSON.stringify(complete(p.witness)));
  const items = {}, rejectedItems = {};
  for (const item of dex.items.all().slice().sort((a,b) => a.id.localeCompare(b.id))) {
    const problem = validator.checkItem({name:'audit'}, item, {});
    if (problem) { rejectedItems[item.id] = problem; continue; }
    let witness;
    for (const p of fillers) {
      const set = {...clone(p.witness),item:item.name};
      if (!validator.validateSet(set,{})) { witness = clean(set); break; }
    }
    if (!witness) { rejectedItems[item.id] = 'no legal set witness'; continue; }
    items[item.id] = {name:item.name,mega_stone:item.megaStone || null,witness,
      team_witness_sha256:hash(JSON.stringify(complete(witness)))};
  }
  const bases = [...new Set(Object.values(species).map(p => p.base_species))].sort();
  const randomBases = [...new Set(Object.keys(source).map(id => dex.species.get(id).baseSpecies))].sort();
  const files = ['config/formats.ts','sim/team-validator.ts','sim/dex-species.ts',
    'data/mods/champions/formats-data.ts','data/mods/champions/learnsets.ts',
    'data/mods/champions/items.ts','data/mods/champions/abilities.ts','data/mods/champions/rulesets.ts',
    'data/mods/champions/scripts.ts','data/random-battles/champions/sets.json',
    'data/random-battles/champions/teams.ts','data/pokedex.ts','data/moves.ts','data/items.ts',
    'data/abilities.ts','data/learnsets.ts','data/formats-data.ts','data/scripts.ts','data/conditions.ts'];
  return {schema_version:VERSION,engine_commit:PIN,format_id:FORMAT,
    authority:'Pinned Showdown format, not an independent certification of live Champions eligibility.',
    probability_scope:'No probability or competitive usage claims.',
    combination_scope:'Single-move/ability legal-set witnesses; every generated combination and whole team revalidated natively. Not a Cartesian enumeration.',
    source_hashes:Object.fromEntries(files.map(f => [f,hash(fs.readFileSync(path.join(checkout,f)))])),
    rules:[...validator.ruleTable.keys()],team_constraints:{minimum:validator.ruleTable.minTeamSize,
      maximum:validator.ruleTable.maxTeamSize,picked:validator.ruleTable.pickedTeamSize,
      adjusted_level:validator.ruleTable.adjustLevel,stat_point_limit:validator.ruleTable.evLimit,
      species_clause:true,item_clause:1,ivs:'all 31'},
    base_species:bases,species,items,abilities:[...abilities].sort(),
    transformation_abilities:[...battleAbilities].sort(),moves:[...moves].sort(),
    native_move_rule_candidates:legalMoves.map(m => m.id).sort(),
    excluded_species:excluded,excluded_items:rejectedItems,
    random_source:{base_species:randomBases,forms:Object.keys(source).sort(),
      missing_bases:bases.filter(p => !randomBases.includes(p)),
      missing_forms:Object.keys(species).filter(id => !source[id])},
    public_dex:Object.fromEntries(Object.keys(species).map(id => {
      const p = dex.species.get(id);
      return [id,{name:p.name,baseSpecies:p.baseSpecies,baseStats:p.baseStats,types:p.types,
        abilities:p.abilities,heightm:p.heightm,weightkg:p.weightkg}];
    }))};
}
function generator(checkout, inventory, seed, allowedBases = inventory.base_species) {
  const engine = loadEngine(checkout), dex = engine.Dex.mod('champions');
  const validator = new engine.TeamValidator(FORMAT), gen = engine.Teams.getGenerator(FORMAT, seed);
  if (inventory.schema_version !== VERSION || inventory.engine_commit !== PIN || inventory.format_id !== FORMAT) {
    throw new Error('incompatible_legal_inventory');
  }
  const bases = [...new Set(allowedBases)].sort();
  if (bases.length < 6 || bases.some(b => !inventory.base_species.includes(b))) throw new Error('invalid_species_pool');
  const byBase = Object.fromEntries(bases.map(base => [base,Object.entries(inventory.species)
    .filter(([,p]) => p.base_species === base && p.kind !== 'ability_transformation')]));
  const failures = {}, modes = {upstream:0,domain:0}, counts = {sets:0,teams:0};
  const reject = reasons => reasons.forEach(r => failures[r] = (failures[r] || 0) + 1);
  function setFor(id, usedItems, required = {}) {
    const entry = inventory.species[id];
    if (!entry || !bases.includes(entry.base_species)) throw new Error('required_form_outside_pool');
    for (let retry = 0; retry < 64; retry++) {
      counts.sets++;
      let set;
      const upstream = gen.randomSets[id] && !Object.keys(required).length && gen.randomChance(1,2);
      if (upstream) {
        try { set = clean(gen.randomSet(id, {})); modes.upstream++; }
        catch { reject(['upstream_set_generation']); continue; }
      } else {
        modes.domain++;
        const ability = required.ability || gen.sample(entry.abilities);
        const pool = entry.moves_by_ability[ability];
        if (!pool) throw new Error('required_ability_outside_domain');
        if (required.moves && (!Array.isArray(required.moves) || required.moves.length < 1 || required.moves.length > 4 ||
            required.moves.some(m => typeof m !== 'string') || new Set(required.moves.map(m => dex.moves.get(m).id)).size !== required.moves.length)) {
          throw new Error('invalid_required_move_combination');
        }
        const needed = [...(required.moves || []),required.move, dex.species.get(id).requiredMove].filter(Boolean).map(m => dex.moves.get(m).id);
        if (needed.some(m => !pool.includes(m))) throw new Error('required_move_outside_domain');
        const sampled = [...new Set(needed)], rest = pool.filter(m => !sampled.includes(m));
        // Diverse native-legal combinations, including unsuccessful/low-power sets.
        if (!required.moves) while (sampled.length < Math.min(4,pool.length)) sampled.push(gen.sampleNoReplace(rest));
        const availableItems = Object.values(inventory.items).filter(i => !usedItems.has(i.name));
        const item = required.item !== undefined ? required.item : entry.required_item ||
          (gen.randomChance(1,10) ? '' : gen.sample(availableItems).name);
        set = {...clone(entry.witness),moves:sampled,ability,item,nature:required.nature || gen.sample(dex.natures.all()).name};
        // Native Champions stat points, not mainline EV conversion.
        const spread = {...stats};
        const statNames = Object.keys(spread);
        for (let n=0;n<36;n++) {
          const from = gen.sample(statNames), to = gen.sample(statNames);
          if (spread[from] && spread[to] < 32) { spread[from]--; spread[to]++; }
        }
        if (gen.randomChance(1,3)) {
          // Include extreme spreads, not just a neighborhood of 11/11/11/11/11/11.
          statNames.forEach(s => spread[s] = 0);
          const pool = statNames.slice();
          for (const points of [32,32,2]) spread[gen.sampleNoReplace(pool)] = points;
        }
        set.evs = required.evs || spread;
      }
      if (usedItems.has(set.item) && set.item) { reject(['item_clause_collision']); continue; }
      // Keep claimed form identity intact; an unrelated stone can activate another Mega.
      const item = dex.items.get(set.item);
      if (entry.kind !== 'mega' && required.item === undefined && item.megaEvolves === entry.start_species) {
        reject(['unrequested_mega_transformation']); continue;
      }
      if (entry.required_item && set.item !== entry.required_item) { reject(['required_form_item']); continue; }
      const errors = validator.validateSet(set,{});
      if (errors) { reject(errors); continue; }
      return clean(set);
    }
    throw new Error('bounded_legal_set_retry_exhausted');
  }
  function team(required = {}) {
    if (Object.keys(required).some(k => !['form','move','moves','ability','item','nature','evs'].includes(k))) throw new Error('unknown_generation_constraint');
    for (const key of ['form','move','ability','item','nature']) {
      if (Object.hasOwn(required,key) && typeof required[key] !== 'string') throw new Error('explicit_hypothetical_string_required');
    }
    if (Object.hasOwn(required,'moves') && (!Array.isArray(required.moves) || !required.moves.length)) throw new Error('explicit_move_combination_required');
    if (Object.hasOwn(required,'evs') && (!required.evs || Array.isArray(required.evs) ||
        Object.keys(required.evs).sort().join(',') !== Object.keys(stats).sort().join(',') ||
        Object.values(required.evs).some(n => !Number.isInteger(n)))) throw new Error('complete_explicit_stat_points_required');
    for (let retry=0;retry<64;retry++) {
      counts.teams++;
      const pool = bases.slice(), chosen = [], usedItems = new Set();
      try {
        for (let slot=0;slot<6;slot++) {
          const forced = slot === 0 && required.form;
          const base = forced ? inventory.species[forced]?.base_species : gen.sampleNoReplace(pool);
          if (forced) { const index = pool.indexOf(base); if (index < 0) throw new Error('required_form_outside_pool'); pool.splice(index,1); }
          const id = forced || gen.sample(byBase[base])[0];
          const set = setFor(id,usedItems,forced ? Object.fromEntries(Object.entries(required).filter(([k]) => k !== 'form')) : {});
          chosen.push(set); if (set.item) usedItems.add(set.item);
        }
      } catch (error) {
        if (!error.message.startsWith('bounded_')) throw error;
        reject([error.message]); continue;
      }
      const errors = validator.validateTeam(chosen);
      if (errors) { reject(errors); continue; }
      return chosen.map(clean);
    }
    throw new Error('bounded_legal_team_retry_exhausted');
  }
  return {team,counts,modes,failures};
}
module.exports = {audit,generator,pinned,PIN,FORMAT,VERSION,hash};
