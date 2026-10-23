'use strict';
// Public canonical metadata only. Never construct a Battle or accept a set.
const path = require('path');
const {Dex} = require(path.join(path.resolve(process.argv[2]), 'dist/sim'));
const dex = Dex.forFormat('gen9championsbssregmc');
const moves = {};
for (const move of dex.moves.all()) {
  moves[move.id] = {
    // Exclude deterministic state/party changes the two-round utility omits.
    simpleExchange: !move.selfSwitch && !move.forceSwitch && !move.selfdestruct &&
      !move.recoil && !move.drain && !move.self && !move.boosts &&
      !move.volatileStatus && !move.sideCondition && !move.pseudoWeather &&
      !move.weather && !move.terrain && !move.stallingMove,
  };
}
process.stdout.write(JSON.stringify({schema_version: 'pinned-public-exchange-metadata-v1',
  format_id: 'gen9championsbssregmc', moves}));
