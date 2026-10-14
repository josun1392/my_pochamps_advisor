'use strict';
// Registry vocabulary, not eligibility or opponent-set inference.
const path = require('node:path');
const {Dex} = require(path.join(path.resolve(process.argv[2]), 'dist/sim'));
const dex = Dex.forFormat('gen9championsbssregmc');
const abilities = dex.abilities.all().filter(a => a.exists).map(a => ({id: a.id, name: a.name, gen: a.gen})).sort((a,b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
if (new Set(abilities.map(a => a.id)).size !== abilities.length) throw new Error('duplicate_canonical_native_ability');
process.stdout.write(JSON.stringify({format_id: 'gen9championsbssregmc', mod: dex.currentMod, abilities}));
