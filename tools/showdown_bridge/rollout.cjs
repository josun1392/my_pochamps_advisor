'use strict';

const SCHEMA = 'showdown-rollout-policy-v1';
function validPolicy(policy) {
  return policy && policy.schema_version === SCHEMA && policy.policy === 'showdown-random-player' &&
    Number.isInteger(policy.max_decisions) && policy.max_decisions >= 1 && policy.max_decisions <= 128 &&
    ['self', 'opponent'].every(side => policy[side] &&
      Number.isFinite(policy[side].move_probability) && policy[side].move_probability > 0 && policy[side].move_probability <= 1 &&
      Number.isFinite(policy[side].mega_probability) && policy[side].mega_probability >= 0 && policy[side].mega_probability <= 1);
}
function rollout(battle, initialChoices, seed, policy, engine, choose) {
  const players = ['self', 'opponent'].map((side, index) => {
    const options = policy[side];
    const player = new engine.RandomPlayerAI({write() {}}, {
      seed: seed.map((word, i) => word ^ ((index + 1) * 1237 + i * 67)),
      move: options.move_probability, mega: options.mega_probability,
    });
    // Upstream receiveRequest/chooseMove/chooseSwitch remain unchanged.
    player.choose = choice => { player.detachedChoice = choice; };
    return player;
  });
  const trace = [];
  let decisions = 0, forced = 0, immediate;
  while (!battle.ended && decisions < policy.max_decisions) {
    const phase = battle.requestState;
    const requests = [battle.p1.activeRequest, battle.p2.activeRequest];
    const choices = decisions === 0 ? initialChoices : Object.fromEntries(['self', 'opponent'].map((side, i) => {
      players[i].detachedChoice = undefined;
      players[i].receiveRequest(requests[i] || {wait: true});
      return [side, players[i].detachedChoice || ''];
    }));
    if (phase === 'switch') forced++;
    choose(battle, choices);
    decisions++;
    if (decisions === 1) immediate = {...outcome(battle),
      self_fainted: battle.p1.pokemon.filter(p => p.fainted).length,
      opponent_fainted: battle.p2.pokemon.filter(p => p.fainted).length,
      request_state: battle.ended ? 'ended' : battle.requestState, pending_actions: battle.queue.list.length > 0};
    // Trace native choice boundaries, including natural pivot/faint requests.
    trace.push({decision: decisions, request_state: phase, choices, next_request_state: battle.requestState,
      turn: battle.turn, ended: battle.ended});
  }
  return {decisions, forced_replacements: forced, trace, immediate};
}
function outcome(battle) {
  const health = side => side.pokemon.reduce((sum, p) => sum + p.hp / p.maxhp, 0) / side.pokemon.length;
  const self = health(battle.p1), opponent = health(battle.p2);
  // Experimental position score; deliberately not a probability or guarantee.
  const value = battle.ended ? (battle.winner === 'self' ? 1 : battle.winner === 'opponent' ? -1 : 0) : self - opponent;
  return {self_health_fraction: self, opponent_health_fraction: opponent, outcome_value: value};
}
module.exports = {validPolicy, rollout, outcome};
