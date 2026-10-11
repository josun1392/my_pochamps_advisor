'use strict';
// Conditional single-hit calculation, reused by transport and parity oracle.
// Native callbacks own mechanics. This is not an action/KO probability ledger.
const clone = value => JSON.parse(JSON.stringify(value));
class NativeDamageError extends Error {}
const requireQuery = (ok, code) => { if (!ok) throw new NativeDamageError(code); };
const slug = name => name.toLowerCase().replaceAll(' ', '-');
function evaluateDamageRolls(Battle, saved, query) {
  requireQuery(query && ['self', 'opponent'].includes(query.side) && typeof query.move === 'string' &&
    typeof query.critical === 'boolean', 'invalid_native_damage_query');
  const rolls = [];
  let context;
  for (let roll = 0; roll < 16; roll++) {
    const battle = Battle.fromJSON(clone(saved.native_state));
    try {
      battle.restart(() => {});
      requireQuery(battle.requestState === 'move', 'native_damage_requires_move_boundary');
      const source = battle[query.side === 'self' ? 'p1' : 'p2'].active[0], target = source.side.foe.active[0];
      let move = battle.dex.getActiveMove(query.move);
      requireQuery(move.exists && source.baseMoves.includes(move.id) && ['Physical', 'Special'].includes(move.category) &&
        move.basePower > 0 && !move.basePowerCallback && !move.damageCallback && !move.multihit && !move.ohko &&
        ['normal', 'allAdjacentFoes', 'allAdjacent', 'any'].includes(move.target), 'unsupported_native_damage_query');
      requireQuery(move.willCrit !== true || query.critical, 'incompatible_native_critical_assumption');
      move.willCrit = query.critical;
      // No RNG other than the one uniform native damage roll may be ignored.
      let rollCalls = 0;
      battle.random = (n, upper) => {
        requireQuery(n === 16 && upper === undefined && rollCalls++ === 0, 'unsupported_native_damage_randomness');
        return roll;
      };
      battle.randomChance = () => { throw new NativeDamageError('unsupported_native_damage_randomness'); };
      battle.sample = () => { throw new NativeDamageError('unsupported_native_damage_randomness'); };
      battle.prng.random = () => { throw new NativeDamageError('unsupported_native_damage_randomness'); };
      battle.activeMove = move; battle.activePokemon = source; battle.activeTarget = target;
      battle.singleEvent('ModifyType', move, null, source, target, move, move);
      battle.singleEvent('ModifyMove', move, null, source, target, move, move);
      move = battle.runEvent('ModifyType', source, target, move, move);
      move = battle.runEvent('ModifyMove', source, target, move, move);
      requireQuery(move && !move.multihit, 'unsupported_native_modified_damage_query');
      const unblocked = battle.runEvent('TryHit', target, source, move);
      const damage = unblocked ? battle.actions.getDamage(source, target, move, true) : 0;
      requireQuery(damage === false || damage === null || typeof damage === 'number', 'unsupported_native_damage_result');
      rolls.push(typeof damage === 'number' ? damage : 0);
      const pokemon = p => ({species: p.species.id, stats: clone(p.storedStats), hp: p.hp, max_hp: p.maxhp,
        types: p.getTypes().map(t => t.toLowerCase()), ability: slug(p.getAbility().name),
        item: p.item ? slug(p.getItem().name) : null, status: p.status});
      context = {attacker: pokemon(source), defender: pokemon(target), move_type: move.type.toLowerCase(),
        move_power: move.basePower, is_physical: move.category === 'Physical', level: source.level};
    } finally { battle.destroy(); }
  }
  return {schema_version: 'showdown-native-damage-rolls-v1',
    scope: 'conditional_single_hit_damage_calculation_fixed_crit',
    interpretation: 'conditional_exact_damage_rolls_not_action_or_ko_probability',
    excludes: ['before_move_gates', 'accuracy', 'secondary_effects', 'multi_hit', 'damage_application_and_survival', 'ranking'],
    side: query.side, move: query.move, critical_assumption: query.critical,
    rolls: rolls.sort((a, b) => a - b), context};
}
module.exports = {evaluateDamageRolls, NativeDamageError};
