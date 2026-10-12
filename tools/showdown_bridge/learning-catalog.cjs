'use strict';
// Public Dex priors only: no battle, selected roster, set, request or RNG.
const {loadEngine} = require('./engine.cjs');
const {execFileSync} = require('node:child_process');
const expected = '942cda71d14bf0618bd57991708a2e2734b6daba';
if (execFileSync('git', ['-C', process.argv[2], 'rev-parse', 'HEAD'], {encoding:'utf8'}).trim() !== expected) {
  throw new Error('learning_catalog_requires_pinned_engine');
}
const dex = loadEngine(process.argv[2]).Dex.mod('champions');
const allSpecies = new Map(dex.species.all().map(p => [p.id,p]));
for (const p of dex.species.all()) for (const name of [...(p.cosmeticFormes || []),...(p.otherFormes || [])]) {
  const alias = dex.species.get(name);
  if (alias.exists) allSpecies.set(alias.id,alias);
}
const species = {}, moves = {}, effectiveness = {};
for (const p of allSpecies.values()) if (p.exists) {
  species[p.id] = {types:p.types, base_stats:p.baseStats};
}
for (const m of dex.moves.all()) if (m.exists) {
  moves[m.id] = {type:m.type, category:m.category, power:m.basePower, accuracy:m.accuracy === true ? 1 : m.accuracy / 100,
    priority:m.priority, heal:!!m.heal, pivot:!!m.selfSwitch, boost:!!(m.boosts || m.self?.boosts)};
}
for (const t of dex.types.all()) if (t.exists) {
  effectiveness[t.name] = {};
  for (const p of allSpecies.values()) if (p.exists) {
    effectiveness[t.name][p.id] = dex.getImmunity(t.name,p.types) ? 2 ** dex.getEffectiveness(t.name,p.types) : 0;
  }
}
process.stdout.write(JSON.stringify({schema_version:'showdown-learning-catalog-v1',
  engine_commit:'942cda71d14bf0618bd57991708a2e2734b6daba',format_id:'gen9championsbssregmc',species,moves,effectiveness}));
