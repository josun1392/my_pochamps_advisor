'use strict';
// Enumerate native status-callback RNG only, never the full action's probability.
const clone = value => JSON.parse(JSON.stringify(value));
class Split extends Error { constructor(n, d) { super('native_rng_split'); this.n = n; this.d = d; } }
const gcd = (a, b) => b ? gcd(b, a % b) : a;
function weight(a, n, d) {
  const numerator = a.numerator * n, denominator = a.denominator * d;
  const divisor = gcd(numerator, denominator);
  return {numerator: numerator / divisor, denominator: denominator / divisor};
}
function evaluateStatusGate(Battle, saved, query) {
  if (!query || !['self', 'opponent'].includes(query.side) || typeof query.move !== 'string') throw new Error('invalid_native_status_query');
  const pending = [{trace: [], probability: {numerator: 1, denominator: 1}}], branches = [];
  while (pending.length) {
    if (pending.length + branches.length > 32) throw new Error('native_status_gate_budget_exceeded');
    const row = pending.pop(), battle = Battle.fromJSON(clone(saved.native_state));
    try {
      battle.restart(() => {});
      if (battle.requestState !== 'move') throw new Error('native_status_gate_requires_move_boundary');
      const pokemon = battle[query.side === 'self' ? 'p1' : 'p2'].active[0];
      const move = battle.dex.getActiveMove(query.move);
      if (!['slp', 'frz'].includes(pokemon.status) || !move.exists || !pokemon.baseMoves.includes(move.id)) throw new Error('native_status_query_not_supported');
      let calls = 0;
      battle.randomChance = (n, d) => {
        if (!Number.isInteger(n) || !Number.isInteger(d) || n <= 0 || n >= d) throw new Error('unsupported_native_status_rng');
        if (calls === row.trace.length) throw new Split(n, d);
        return row.trace[calls++];
      };
      const before = pokemon.status;
      const allowed = battle.singleEvent('BeforeMove', battle.dex.conditions.get(before), pokemon.statusState,
        pokemon, pokemon.side.foe.active[0], move) !== false;
      branches.push({probability: row.probability, executes_status_gate: allowed,
        condition_before: before, condition_after: pokemon.status,
        remaining_time: pokemon.statusState.time ?? null, early_bird_active: pokemon.hasAbility('earlybird'),
        // defrost callbacks can allow execution before the later ModifyMove cure.
        interpretation: 'conditional_native_status_callback_not_full_action_or_ranking'});
    } catch (error) {
      if (!(error instanceof Split)) throw error;
      pending.push({trace: [...row.trace, false], probability: weight(row.probability, error.d - error.n, error.d)},
        {trace: [...row.trace, true], probability: weight(row.probability, error.n, error.d)});
    } finally { battle.destroy(); }
  }
  return {schema_version: 'showdown-native-status-gate-v1', scope: 'native_status_before_move_callback_only',
    interpretation: 'conditional_exact_callback_probability_not_full_action_or_ranking',
    side: query.side, move: query.move, branches};
}
module.exports = {evaluateStatusGate};
