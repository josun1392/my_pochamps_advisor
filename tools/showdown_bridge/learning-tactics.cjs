'use strict';
// Public move metadata from the pinned Dex. No mechanics, battle or RNG replay.
const {loadEngine} = require('./engine.cjs');
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const expected = '942cda71d14bf0618bd57991708a2e2734b6daba';
if (execFileSync('git', ['-C', process.argv[2], 'rev-parse', 'HEAD'], {encoding:'utf8'}).trim() !== expected) {
  throw new Error('learning_tactics_requires_pinned_engine');
}
const dex = loadEngine(process.argv[2]).Dex.mod('champions');
const moves = {};
for (const m of dex.moves.all()) if (m.exists) {
  moves[m.id] = {status:m.status || null, boosts:m.boosts || {},
    self_boosts:m.self?.boosts || {}, side_condition:m.sideCondition || null,
    volatile:m.volatileStatus || null, target:m.target,
    heal:m.heal ? m.heal[0] / m.heal[1] : 0, drain:m.drain ? m.drain[0] / m.drain[1] : 0,
    recoil:m.recoil ? m.recoil[0] / m.recoil[1] : 0,
    removes_hazards:['rapidspin','mortalspin','defog','tidyup'].includes(m.id),
    phaze:!!m.forceSwitch, contact:!!m.flags.contact};
}
const result = JSON.stringify({schema_version:'showdown-learning-tactics-v1',
  engine_commit:expected,format_id:'gen9championsbssregmc',moves});
if (process.argv[3]) fs.writeFileSync(process.argv[3], result);
else process.stdout.write(result);
