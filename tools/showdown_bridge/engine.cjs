'use strict';
const path = require('node:path');

// Reuse the pinned upstream request consumer, including forced replacements.
// Never connect its BattlePlayer interface to a public stream or server.
function loadEngine(checkout) {
  return {...require(path.join(checkout, 'dist', 'sim')),
    RandomPlayerAI: require(path.join(checkout, 'dist', 'sim', 'tools', 'random-player-ai')).RandomPlayerAI};
}
module.exports = {loadEngine};
