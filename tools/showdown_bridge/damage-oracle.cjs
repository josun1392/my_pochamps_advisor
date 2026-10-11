'use strict';
// Offline regression oracle only: enumerate native damage rolls with fixed crit.
// No battle execution path or Python damage formula is modified by this harness.
const fs = require('node:fs');
const path = require('node:path');
const {Battle} = require(path.join(process.argv[2], 'dist', 'sim'));
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const clone = value => JSON.parse(JSON.stringify(value));
const slug = name => name.toLowerCase().replaceAll(' ', '-');
const results = input.map(query => {
  const rolls = [];
  let context;
  for (let roll = 0; roll < 16; roll++) {
    const battle = Battle.fromJSON(clone(query.checkpoint.native_state));
    try {
      battle.restart(() => {});
      const source = battle[query.side === 'self' ? 'p1' : 'p2'].active[0];
      const target = source.side.foe.active[0];
      let move = battle.dex.getActiveMove(query.move);
      move.willCrit = !!query.critical;
      battle.random = n => { if (n === 16) return roll; throw new Error('unexpected_oracle_randomness'); };
      battle.activeMove = move; battle.activePokemon = source; battle.activeTarget = target;
      battle.singleEvent('ModifyType', move, null, source, target, move, move);
      battle.singleEvent('ModifyMove', move, null, source, target, move, move);
      move = battle.runEvent('ModifyType', source, target, move, move);
      move = battle.runEvent('ModifyMove', source, target, move, move);
      const unblocked = battle.runEvent('TryHit', target, source, move);
      const damage = unblocked ? battle.actions.getDamage(source, target, move, true) : 0;
      rolls.push(typeof damage === 'number' ? damage : 0);
      const pokemon = p => ({species: p.species.id, stats: p.storedStats, hp: p.hp, max_hp: p.maxhp,
        types: p.getTypes().map(t => t.toLowerCase()), ability: slug(p.getAbility().name),
        item: p.item ? slug(p.getItem().name) : null, status: p.status});
      context = {attacker: pokemon(source), defender: pokemon(target), move_type: move.type.toLowerCase(),
        move_power: move.basePower, is_physical: move.category === 'Physical', level: source.level};
    } finally { battle.destroy(); }
  }
  return {case_id: query.case_id, rolls: rolls.sort((a, b) => a - b), context};
});
process.stdout.write(JSON.stringify(results));
