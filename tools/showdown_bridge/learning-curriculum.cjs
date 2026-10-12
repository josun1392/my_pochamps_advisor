'use strict';
// Reuse upstream Champions team/moveset generation and the M-C legality authority.
// This coordinator-only offline corpus never becomes a policy observation.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const {loadEngine} = require('./engine.cjs');
const pin = '942cda71d14bf0618bd57991708a2e2734b6daba';
const format = 'gen9championsbssregmc';
const version = 'showdown-learning-curriculum-v6';
const checkout = process.argv[2];
if (execFileSync('git', ['-C', checkout, 'rev-parse', 'HEAD'], {encoding:'utf8'}).trim() !== pin ||
    execFileSync('git', ['-C', checkout, 'status', '--porcelain', '--untracked-files=no'], {encoding:'utf8'}).trim()) {
  throw new Error('pinned_clean_engine_required');
}
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
if (!Array.isArray(input.reserved_species) || !Number.isInteger(input.fresh_unseen_species) ||
    input.fresh_unseen_species < 6 || input.fresh_unseen_species > 32) throw new Error('bounded_reservations_required');
const {Teams, Dex, TeamValidator} = loadEngine(checkout);
const dex = Dex.mod('champions');
const source = Teams.getGenerator(format, [1,2,3,4]).randomSets;
const bases = [...new Set(Object.keys(source).map(id => dex.species.get(id).baseSpecies))].sort();
const reserved = new Set(input.reserved_species.map(id => dex.species.get(id).baseSpecies));
const hash = value => crypto.createHash('sha256').update(value).digest();
const fresh = bases.filter(id => !reserved.has(id)).sort((a,b) =>
  Buffer.compare(hash(`${version}:reserve:${a}`),hash(`${version}:reserve:${b}`))).slice(0,input.fresh_unseen_species);
fresh.forEach(id => reserved.add(id));
const pools = {
  train: Object.fromEntries(Object.entries(source).filter(([id]) => !reserved.has(dex.species.get(id).baseSpecies))),
  unseen: Object.fromEntries(Object.entries(source).filter(([id]) => reserved.has(dex.species.get(id).baseSpecies))),
};
const validator = new TeamValidator(format);
const publicDex = Object.fromEntries(Object.keys(source).map(id => {
  const p = dex.species.get(id);
  return [id, {name:p.name, baseSpecies:p.baseSpecies, baseStats:p.baseStats,
    types:p.types, abilities:p.abilities, heightm:p.heightm, weightkg:p.weightkg}];
}));
const teams = {}, attempts = {}, failures = {}, coverage = {};
for (const split of ['train','validation','test','unseen']) {
  const count = input.counts?.[split];
  if (!Number.isInteger(count) || count < 8 || count > 4096) throw new Error('bounded_bank_count_required');
  teams[split] = []; attempts[split] = 0; coverage[split] = {};
  for (let n=0; n<count; n++) {
    const bytes = hash(`${version}:${split}:${n}`);
    const seed = [0,2,4,6].map(i => bytes.readUInt16BE(i));
    const gen = Teams.getGenerator(format, seed);
    gen.randomSets = pools[split === 'unseen' ? 'unseen' : 'train'];
    let accepted = null;
    for (let retry=0; retry<512; retry++) {
      attempts[split]++;
      let team;
      try { team = gen.randomTeam(); } catch { failures.generator = (failures.generator || 0)+1; continue; }
      const problems = validator.validateTeam(team);
      if (problems) {
        for (const problem of problems) failures[problem] = (failures[problem] || 0)+1;
        continue;
      }
      accepted = team.map(p => Object.fromEntries(['species','moves','ability','item','nature','evs','ivs','level','gender']
        .map(key => [key,p[key]])));
      break;
    }
    if (!accepted) throw new Error('native_legal_team_retry_limit');
    teams[split].push(accepted);
    for (const p of accepted) coverage[split][p.species] = (coverage[split][p.species] || 0)+1;
  }
}
process.stdout.write(JSON.stringify({schema_version:'showdown-native-team-bank-v1',
  curriculum_version:version,engine_commit:pin,format_id:format,
  source:'pokemon-showdown RandomChampionsTeams.randomTeam + TeamValidator',
  source_files:['data/random-battles/champions/teams.ts','data/random-battles/champions/sets.json'],
  stats_scope:'Upstream native random-team spreads; legal coverage fixtures, not expert ladder teams.',
  legal_base_species:bases.length,train_base_species:bases.filter(id => !reserved.has(id)),
  unseen_base_species:[...reserved].filter(id => bases.includes(id)).sort(),fresh_unseen_species:fresh,
  counts:input.counts,attempts,failures,coverage,public_dex:publicDex,teams}));
