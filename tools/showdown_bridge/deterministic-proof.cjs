'use strict';

class NativeRandomnessRequired extends Error {}
function proveConstantRNG(battle, perform) {
  if (battle.forceRandomChance !== null) throw new NativeRandomnessRequired('forced_native_randomness_not_proven');
  const prng = battle.prng, rng = prng.rng;
  const originals = {random: prng.random, chance: prng.randomChance, next: rng.next, math: Math.random};
  const descriptors = [Object.getOwnPropertyDescriptor(prng, 'random'),
    Object.getOwnPropertyDescriptor(prng, 'randomChance'), Object.getOwnPropertyDescriptor(rng, 'next')];
  const draws = [];
  let constant = 0, rawCalls = 0;
  prng.random = function (from, to) {
    const singleton = from === 1 && to === undefined ||
      Number.isInteger(from) && Number.isInteger(to) && to > 0 && to - from === 1;
    if (!constant && !singleton) throw new NativeRandomnessRequired('native_stochastic_rng_required');
    if (!constant) draws.push({kind: 'singleton_integer', from, to: to ?? null});
    constant++;
    try { return originals.random.call(this, from, to); }
    finally { constant--; }
  };
  prng.randomChance = function (numerator, denominator) {
    if (!(Number.isFinite(numerator) && Number.isInteger(denominator) && denominator > 0 &&
      (numerator <= 0 || numerator >= denominator))) throw new NativeRandomnessRequired('native_stochastic_rng_required');
    draws.push({kind: 'constant_bernoulli', numerator, denominator});
    constant++;
    try { return originals.chance.call(this, numerator, denominator); }
    finally { constant--; }
  };
  rng.next = function () {
    if (!constant) throw new NativeRandomnessRequired('native_raw_rng_not_proven');
    rawCalls++;
    return originals.next.call(this);
  };
  Math.random = () => { throw new NativeRandomnessRequired('untracked_randomness_not_proven'); };
  try {
    const progression = perform();
    return {progression, proof: {schema_version: 'showdown-constant-rng-proof-v1',
      method: 'native_rng_guard_no_nonconstant_draws', stochastic_draws: 0, native_raw_calls: rawCalls,
      constant_draws: draws, probability_mass: {numerator: 1, denominator: 1},
      scope: 'one_completed_native_move_attempt_not_deferred_actions'}};
  } finally {
    for (const [index, object, key] of [[0, prng, 'random'], [1, prng, 'randomChance'], [2, rng, 'next']]) {
      if (descriptors[index]) Object.defineProperty(object, key, descriptors[index]);
      else delete object[key];
    }
    Math.random = originals.math;
  }
}
module.exports = {proveConstantRNG, NativeRandomnessRequired};
