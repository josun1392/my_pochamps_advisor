'use strict';
// Canonical public Dex only: no Battle, team, request, checkpoint or RNG input.
const path = require('path');
const {Dex} = require(path.join(path.resolve(process.argv[2]), 'dist/sim'));
const dex = Dex.forFormat('gen9championsbssregmc');
const moves = {};
for (const m of dex.moves.all()) moves[m.id] = {
  type: m.type, category: m.category, power: m.basePower, priority: m.priority,
  accuracy: m.accuracy, target: m.target, flags: m.flags,
  heal: m.heal || null, drain: m.drain || null, recoil: m.recoil || null,
  boosts: m.boosts || null, selfBoosts: m.self?.boosts || null,
  status: m.status || null, volatile: m.volatileStatus || null,
  sideCondition: m.sideCondition || null, selfSwitch: !!m.selfSwitch,
  forceSwitch: !!m.forceSwitch, selfdestruct: !!m.selfdestruct,
  multihit: m.multihit || null, fixedDamage: m.damage || null,
  variablePower: !!m.basePowerCallback || !!m.onBasePower || !!m.damageCallback,
  charge: !!m.flags.charge, protect: !!m.stallingMove,
};
process.stdout.write(JSON.stringify({schema_version: 'pinned-public-response-metadata-v1',
  format_id: 'gen9championsbssregmc', moves}));
