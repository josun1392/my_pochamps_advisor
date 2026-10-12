'use strict';
const fs = require('node:fs');
const domain = require('./legal-domain.cjs');
const checkout = process.argv[2], request = JSON.parse(fs.readFileSync(0,'utf8'));
const version = 'showdown-learning-curriculum-v7';
const seedFor = key => { const b = Buffer.from(domain.hash(key),'hex'); return [0,2,4,6].map(i => b.readUInt16BE(i)); };
function build(inventory) {
  if (!Array.isArray(request.reserved_species) || !Number.isInteger(request.new_reserved_per_split) ||
      request.new_reserved_per_split < 6 || request.new_reserved_per_split > 24) throw new Error('bounded_reservations_required');
  const historical = [...new Set(request.reserved_species)].sort();
  if (historical.some(p => !inventory.base_species.includes(p))) throw new Error('unknown_reserved_species');
  const available = inventory.base_species.filter(p => !historical.includes(p)).sort((a,b) =>
    domain.hash(`${version}:new-reserve:${a}`).localeCompare(domain.hash(`${version}:new-reserve:${b}`)));
  const n = request.new_reserved_per_split;
  const pools = {validation:available.slice(0,n),test:available.slice(n,2*n),unseen:historical};
  pools.train = available.slice(2*n).sort();
  const teams = {}, attempts = {}, failures = {}, coverage = {}, modes = {}, hashes = new Set();
  for (const split of ['train','validation','test','unseen']) {
    const count = request.counts?.[split];
    if (!Number.isInteger(count) || count < 8 || count > 4096) throw new Error('bounded_bank_count_required');
    teams[split]=[]; coverage[split]={species:{},moves:{},abilities:{},items:{}};
    const gen = domain.generator(checkout,inventory,seedFor(`${version}:${split}`),pools[split]);
    for (let i=0;i<count;i++) {
      const team = gen.team(), digest = domain.hash(JSON.stringify(team));
      if (hashes.has(digest)) throw new Error('duplicate_team_across_partitions');
      hashes.add(digest); teams[split].push(team);
      for (const p of team) {
        const record = (field,key) => coverage[split][field][key] = (coverage[split][field][key] || 0)+1;
        record('species',p.species); p.moves.forEach(m => record('moves',m));
        record('abilities',p.ability); record('items',p.item || 'known_absence');
      }
    }
    attempts[split]=gen.counts; modes[split]=gen.modes; failures[split]=gen.failures;
  }
  return {schema_version:'showdown-native-team-bank-v1',curriculum_version:version,
    engine_commit:domain.PIN,format_id:domain.FORMAT,source:'Native full-domain witnesses + RandomChampionsTeams.randomSet + TeamValidator',
    inventory_sha256:request.inventory_sha256,counts:request.counts,
    legal_base_species:inventory.base_species.length,train_base_species:pools.train,
    unseen_base_species:pools.unseen,partition_species:pools,
    partition_scope:'Disjoint base species (and all their forms), unique complete teams; historical holdouts reserved. New validation/final pools fixed before learning.',
    team_selection_scope:'Coordinator random legal pick-3; selection learning not implemented.',
    generation_profile:'Uniform eligible base species/forms, 50% upstream role sets where available; native-validated diverse move/item/nature/stat-point sets including concentrated spreads. Coverage fixtures, not competitive usage.',
    attempts,modes,failures,coverage,teams};
}
domain.pinned(checkout);
let result;
if (request.operation === 'audit') result = domain.audit(checkout);
else {
  const raw = fs.readFileSync(request.inventory);
  const inventory = JSON.parse(raw.toString('utf8'));
  if (request.inventory_sha256 !== domain.hash(raw)) throw new Error('inventory_hash_mismatch');
  if (request.operation === 'build') result = build(inventory);
  else if (request.operation === 'teams') {
    const count = request.count;
    if (!Number.isInteger(count) || count < 1 || count > 8192 ||
        !Array.isArray(request.seed) || request.seed.length !== 4 ||
        request.seed.some(n => !Number.isInteger(n) || n < 0 || n > 65535)) throw new Error('bounded_generation_required');
    if (request.constraints && request.constraints.length !== count) throw new Error('constraint_count_mismatch');
    if (request.constraints?.some(c => Object.keys(c).length && !c.form)) throw new Error('constraint_form_required');
    const gen = domain.generator(checkout,inventory,request.seed,request.allowed_bases);
    const teams = Array.from({length:count},(_,i) => gen.team(request.constraints?.[i] || {}));
    result = {schema_version:'showdown-full-domain-generated-teams-v1',engine_commit:domain.PIN,
      format_id:domain.FORMAT,inventory_sha256:request.inventory_sha256,seed:request.seed,
      teams,attempts:gen.counts,modes:gen.modes,rejections:gen.failures};
  } else throw new Error('unsupported_domain_operation');
}
process.stdout.write(JSON.stringify(result));
