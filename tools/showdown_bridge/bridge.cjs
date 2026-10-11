'use strict';

// Local simulator only. No server, sockets, provider, or live-state owner.
const fs = require('node:fs');
const path = require('node:path');
const {performance} = require('node:perf_hooks');
const COMMIT = '942cda71d14bf0618bd57991708a2e2734b6daba';
const FORMAT = 'gen9championsbssregmc';
const SCHEMA = 'detached-showdown-v1';
const clone = value => JSON.parse(JSON.stringify(value));
class InputError extends Error {}
function requireInput(ok, code) { if (!ok) throw new InputError(code); }

function run(input, engine) {
  const {Battle, Dex, TeamValidator, toID} = engine;
  requireInput(input.schema_version === SCHEMA, 'invalid_schema');
  requireInput(input.format_id === FORMAT, 'unsupported_format');
  requireInput(typeof input.session_id === 'string' && input.session_id.length > 0 &&
    typeof input.source_runtime_fingerprint === 'string', 'invalid_source_binding');
  const format = Dex.formats.get(FORMAT);
  requireInput(format.exists && format.mod === 'champions' && format.gameType === 'singles', 'format_unavailable');

  function choose(battle, choices) {
    requireInput(choices && Object.keys(choices).sort().join(',') === 'opponent,self', 'invalid_choices');
    // Never default/autoselect a human player's hypothetical action.
    const requests = {p1: battle.p1.activeRequest, p2: battle.p2.activeRequest};
    for (const [side, id] of [['self', 'p1'], ['opponent', 'p2']]) {
      const request = requests[id];
      const choice = choices[side];
      requireInput(typeof choice === 'string' && choice.length <= 100, 'invalid_choice');
      if (!request || request.wait) {
        requireInput(choice === '', 'choice_for_waiting_side');
      } else {
        requireInput(choice.trim().length > 0, 'missing_choice');
        try { requireInput(battle.choose(id, choice), 'illegal_choice'); }
        catch (error) { throw new InputError(error instanceof InputError ? error.message : 'illegal_choice'); }
      }
    }
  }

  function summarize(battle) {
    return {
      turn: battle.turn, ended: battle.ended, winner: battle.winner || null,
      request_state: battle.requestState,
      sides: Object.fromEntries([['self', battle.p1], ['opponent', battle.p2]].map(([name, side]) => [name, {
        request: clone(side.activeRequest),
        pokemon: side.pokemon.map(p => ({species: p.species.id, active: p.isActive,
          hp: p.hp, max_hp: p.maxhp, fainted: p.fainted, status: p.status,
          item: p.item, ability: p.ability, boosts: clone(p.boosts),
          moves: p.moveSlots.map(m => ({id: m.id, pp: m.pp, max_pp: m.maxpp})),
        })),
      }])),
    };
  }

  function checkpoint(battle, scenario) {
    return {schema_version: 'showdown-checkpoint-v1', engine_commit: COMMIT, format_id: FORMAT,
      session_id: input.session_id, source_runtime_fingerprint: input.source_runtime_fingerprint,
      scenario_id: scenario.scenario_id, assumptions: clone(scenario.assumptions),
      native_state: clone(battle.toJSON())};
  }

  function overlay(battle) {
    for (const [side, id] of [['self', 'p1'], ['opponent', 'p2']]) {
      const observed = input.observed_active[side];
      const pokemon = battle[id].active[0];
      requireInput(pokemon && toID(observed.pokemon_id) === pokemon.species.id, 'active_identity_mismatch');
      requireInput(observed.max_hp === pokemon.maxhp && !pokemon.fainted, 'observed_max_hp_or_lifecycle_mismatch');
      requireInput(Number.isInteger(observed.hp) && observed.hp > 0 && observed.hp <= pokemon.maxhp, 'invalid_observed_hp');
      for (const [key, nativeKey] of [['item', 'item'], ['ability', 'ability'], ['condition', 'status']]) {
        if (Object.hasOwn(observed, key)) {
          requireInput(toID(observed[key]) === pokemon[nativeKey], `observed_${key}_conflict`);
        }
      }
      if (Object.hasOwn(observed, 'types')) {
        requireInput(observed.types.map(toID).sort().join(',') === pokemon.getTypes().map(toID).sort().join(','), 'observed_type_conflict');
      }
      if (Object.hasOwn(observed, 'level')) requireInput(observed.level === pokemon.level, 'observed_level_conflict');
      if (observed.known_moves) {
        requireInput(observed.known_moves.every(move => pokemon.baseMoves.includes(toID(move))), 'observed_move_conflict');
      }
      // Overrides are applied only to a detached hypothetical simulator root.
      pokemon.hp = observed.hp;
      for (const [stat, stage] of Object.entries(observed.boosts)) {
        requireInput(Object.hasOwn(pokemon.boosts, stat) && Number.isInteger(stage) && Math.abs(stage) <= 6, 'invalid_observed_stage');
        pokemon.boosts[stat] = stage;
      }
    }
    for (const [key, nativeKey] of [['weather', 'weather'], ['terrain', 'terrain']]) {
      if (Object.hasOwn(input.observed_field, key)) {
        requireInput(input.observed_field[key] === battle.field[nativeKey], `observed_${key}_conflict`);
      }
    }
    battle.makeRequest('move');
  }

  function create(scenario) {
    requireInput(Array.isArray(scenario.seed) && scenario.seed.length === 4 &&
      scenario.seed.every(n => Number.isInteger(n) && n >= 0 && n <= 65535), 'invalid_seed');
    const teams = clone(scenario.teams);
    const validator = new TeamValidator(FORMAT);
    for (const side of ['self', 'opponent']) {
      requireInput(Array.isArray(teams[side]) && teams[side].length === 6, 'six_member_team_required');
      requireInput(!validator.validateTeam(teams[side]), 'invalid_mc_team');
      const pick = scenario.preview[side];
      requireInput(Array.isArray(pick) && pick.length === 3 && new Set(pick).size === 3 &&
        pick.every(n => Number.isInteger(n) && n >= 1 && n <= 6), 'invalid_team_preview');
    }
    const battle = new Battle({formatid: FORMAT, seed: scenario.seed, strictChoices: true,
      p1: {name: 'self', team: teams.self}, p2: {name: 'opponent', team: teams.opponent}});
    try {
      choose(battle, {self: `team ${scenario.preview.self.join('')}`, opponent: `team ${scenario.preview.opponent.join('')}`});
      requireInput(Array.isArray(scenario.history) && scenario.history.length <= 100, 'invalid_history');
      for (const choices of scenario.history) {
        requireInput(!battle.ended, 'history_after_battle_end');
        choose(battle, choices);
      }
      requireInput(battle.requestState === 'move' && !battle.ended, 'move_boundary_required');
      overlay(battle);
      return battle;
    } catch (error) { battle.destroy(); throw error; }
  }

  function evaluate(scenario) {
    let root, branch;
    const started = performance.now();
    try {
      if (input.operation === 'resume') {
        const saved = scenario.checkpoint;
        requireInput(saved.schema_version === 'showdown-checkpoint-v1' && saved.engine_commit === COMMIT &&
          saved.format_id === FORMAT && saved.session_id === input.session_id &&
          saved.source_runtime_fingerprint === input.source_runtime_fingerprint &&
          saved.native_state.formatid === FORMAT, 'checkpoint_binding_mismatch');
        root = Battle.fromJSON(clone(saved.native_state));
        root.restart(() => {});
      } else { root = create(scenario); }
      requireInput(!root.ended, 'battle_already_ended');
      const rootCheckpoint = checkpoint(root, scenario);
      const before = summarize(root);
      // fromJSON mutates nested data; never hand it a shared checkpoint.
      branch = Battle.fromJSON(clone(rootCheckpoint.native_state));
      branch.restart(() => {});
      const logStart = branch.log.length;
      choose(branch, scenario.choices);
      return {status: 'simulated', scenario_id: scenario.scenario_id,
        interpretation: 'conditional_seeded_sample_not_exact_probability',
        assumptions: clone(scenario.assumptions), before, after: summarize(branch),
        events: branch.log.slice(logStart).filter(line => !line.startsWith('|t:|')),
        root_checkpoint: rootCheckpoint, checkpoint: checkpoint(branch, scenario),
        elapsed_ms: performance.now() - started};
    } catch (error) {
      return {status: 'rejected', scenario_id: scenario.scenario_id,
        reason: error instanceof InputError ? error.message : 'native_simulation_failed'};
    } finally { branch?.destroy(); root?.destroy(); }
  }
  requireInput(['simulate', 'resume'].includes(input.operation), 'invalid_operation');
  requireInput(Array.isArray(input.scenarios) && input.scenarios.length > 0 && input.scenarios.length <= 16, 'invalid_scenarios');
  requireInput(new Set(input.scenarios.map(s => s.scenario_id)).size === input.scenarios.length &&
    input.scenarios.every(s => typeof s.scenario_id === 'string' && s.scenario_id.length > 0 && Array.isArray(s.assumptions)), 'invalid_scenario_identity');
  return {schema_version: SCHEMA, engine_commit: COMMIT, format_id: FORMAT,
    session_id: input.session_id, source_runtime_fingerprint: input.source_runtime_fingerprint,
    scenarios: input.scenarios.map(evaluate)};
}

try {
  const payload = fs.readFileSync(0, 'utf8');
  requireInput(Buffer.byteLength(payload) <= 8 * 1024 * 1024, 'request_too_large');
  const engine = require(path.join(process.argv[2], 'dist', 'sim'));
  process.stdout.write(JSON.stringify(run(JSON.parse(payload), engine)));
} catch (error) {
  process.stdout.write(JSON.stringify({status: 'error', reason: error instanceof InputError ? error.message : 'bridge_failed'}));
  process.exitCode = 1;
}
