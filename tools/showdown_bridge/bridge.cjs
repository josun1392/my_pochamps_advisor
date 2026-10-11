'use strict';

// Local simulator only. No server, sockets, provider, or live-state owner.
const fs = require('node:fs');
const path = require('node:path');
const {performance} = require('node:perf_hooks');
const {evaluateStatusGate} = require('./status-gate.cjs');
const {evaluateDamageRolls, NativeDamageError} = require('./damage-rolls.cjs');
const COMMIT = '942cda71d14bf0618bd57991708a2e2734b6daba';
const FORMAT = 'gen9championsbssregmc';
const SCHEMA = 'detached-showdown-v1';
const OBSERVATION_SCHEMA = 'showdown-observed-projection-v2';
const clone = value => JSON.parse(JSON.stringify(value));
class InputError extends Error {}
function requireInput(ok, code) { if (!ok) throw new InputError(code); }

function run(input, engine) {
  const {Battle, Dex, TeamValidator, toID, PRNG} = engine;
  requireInput(input.schema_version === SCHEMA, 'invalid_schema');
  requireInput(input.observation_schema_version === OBSERVATION_SCHEMA, 'unsupported_observation_projection');
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
      let choice = choices[side];
      requireInput(typeof choice === 'string' && choice.length <= 100, 'invalid_choice');
      const slotChoice = /^switch slot:(\d+)$/.exec(choice);
      if (slotChoice) {
        const pokemon = battle[id].pokemon.find(p => p.name === `slot-${Number(slotChoice[1])}`);
        requireInput(pokemon, 'unknown_switch_slot');
        choice = `switch ${pokemon.position + 1}`;
      }
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
      decision_phase: {schema_version: 'showdown-decision-phase-v1', interpretation: 'hypothetical_native_phase_not_observed',
        request_state: battle.requestState, turn: battle.turn,
        requesting_sides: [['self', battle.p1], ['opponent', battle.p2]].filter(([, side]) => side.activeRequest && !side.activeRequest.wait).map(([name]) => name),
        queued_actions: battle.queue.list.map(action => ({choice: action.choice,
          side: action.pokemon?.side.id ?? null, slot_index: action.pokemon ? Number(action.pokemon.name.replace('slot-', '')) : null,
          move: action.move?.id ?? null}))},
      field: {weather: battle.field.weather, terrain: battle.field.terrain,
        weather_duration: battle.field.weatherState.duration ?? null,
        terrain_duration: battle.field.terrainState.duration ?? null,
        pseudo_weather: Object.keys(battle.field.pseudoWeather)},
      sides: Object.fromEntries([['self', battle.p1], ['opponent', battle.p2]].map(([name, side]) => [name, {
        request: clone(side.activeRequest),
        side_conditions: Object.keys(side.sideConditions),
        pokemon: side.pokemon.map(p => ({species: p.species.id, active: p.isActive,
          slot_index: Number(p.name.replace('slot-', '')), native_position: p.position + 1,
          stats: clone(p.storedStats), types: p.getTypes(),
          hp: p.hp, max_hp: p.maxhp, fainted: p.fainted, status: p.status,
          status_counter: ['slp', 'frz'].includes(p.status) ? {schema_version: 'showdown-status-counter-v1',
            start_time: p.statusState.startTime, remaining_time: p.statusState.time,
            early_bird_active: p.hasAbility('earlybird'), interpretation: 'hypothetical_native_state_not_observed'} : null,
          item: p.item, ability: p.ability, boosts: clone(p.boosts),
          volatiles: Object.keys(p.volatiles), berry_eaten: p.ateBerry, received_hit_count: p.timesAttacked,
          moves: p.moveSlots.map(m => ({id: m.id, pp: m.pp, max_pp: m.maxpp})),
        })),
      }])),
    };
  }

  function checkpoint(battle, scenario) {
    return {schema_version: 'showdown-checkpoint-v1', engine_commit: COMMIT, format_id: FORMAT,
      observation_schema_version: OBSERVATION_SCHEMA,
      session_id: input.session_id, source_runtime_fingerprint: input.source_runtime_fingerprint,
      scenario_id: scenario.scenario_id, assumptions: clone(scenario.assumptions),
      model_definition: clone(scenario.checkpoint?.model_definition || {
        teams: scenario.teams, preview: scenario.preview,
        slot_mapping: scenario.slot_mapping || {self: [0, 1, 2, 3, 4, 5], opponent: [0, 1, 2, 3, 4, 5]},
        initial_conditioning: scenario.initial_conditioning || [],
      }),
      native_state: clone(battle.toJSON())};
  }

  function overlay(battle, scenario) {
    for (const [side, id] of [['self', 'p1'], ['opponent', 'p2']]) {
      const active = input.observed_active[side];
      requireInput(battle[id].active[0]?.name === `slot-${active.slot_index ?? 0}`, 'active_slot_mismatch');
      const rows = input.observed_roster?.[side] || [active];
      for (const observed of rows) {
        const pokemon = battle[id].pokemon.find(p => p.name === `slot-${observed.slot_index ?? 0}`);
        if (!pokemon) {
          const slots = scenario.slot_mapping?.[side] || [0, 1, 2, 3, 4, 5];
          const set = scenario.teams[side][slots.indexOf(observed.slot_index)];
          requireInput(set && toID(set.species) === toID(observed.pokemon_id), 'roster_identity_or_selection_mismatch');
          requireInput(Object.entries(observed).every(([key, value]) => ['pokemon_id', 'slot_index'].includes(key) ||
            (['boosts', 'stats', 'move_usability', 'volatiles'].includes(key) && Object.keys(value).length === 0)), 'observed_unselected_roster_mechanics');
          continue;
        }
        requireInput(pokemon && [pokemon.species.id, battle.dex.species.get(pokemon.set.species).id].includes(toID(observed.pokemon_id)), 'roster_identity_or_selection_mismatch');
        if (Object.hasOwn(observed, 'max_hp')) requireInput(observed.max_hp === pokemon.maxhp, 'observed_max_hp_or_lifecycle_mismatch');
        if (Object.hasOwn(observed, 'hp')) requireInput(Number.isInteger(observed.hp) && observed.hp >= 0 && observed.hp <= pokemon.maxhp, 'invalid_observed_hp');
        if (Object.hasOwn(observed, 'fainted')) requireInput(observed.fainted === pokemon.fainted, 'observed_faint_requires_matching_native_history');
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
        if (observed.complete_moves) requireInput(pokemon.moveSlots.length === observed.complete_moves.length &&
          observed.complete_moves.every(move => pokemon.moveSlots.some(slot => slot.id === toID(move))), 'observed_complete_moveset_conflict');
        for (const pp of observed.pp_slots || []) {
          const slot = pokemon.moveSlots[pp.slot_index];
          requireInput(slot && slot.id === toID(pp.move_id) && slot.maxpp === pp.max_pp && Number.isInteger(pp.current_pp) && pp.current_pp >= 0 && pp.current_pp <= slot.maxpp, 'observed_pp_slot_conflict');
          slot.pp = pp.current_pp;
        }
        for (const [stat, value] of Object.entries(observed.stats || {})) {
          requireInput(pokemon.storedStats[stat] === value, 'observed_final_stat_conflict');
        }
        for (const [volatile, present] of Object.entries(observed.volatiles || {})) {
          requireInput(!!pokemon.volatiles[volatile] === present, 'observed_volatile_conflict');
        }
        if (observed.leech_source) {
          const source = battle.getAtSlot(pokemon.volatiles.leechseed.sourceSlot);
          requireInput(source && source.side.id === (observed.leech_source.side === 'self' ? 'p1' : 'p2') &&
            source.name === `slot-${observed.leech_source.slot_index}`, 'observed_leech_source_phase_conflict');
        }
        for (const [id, restriction] of Object.entries(observed.restrictions || {})) {
          const native = pokemon.volatiles[id], active = restriction.state === 'active';
          requireInput(!!native === active, 'observed_restriction_conflict');
          if (active) {
            requireInput(battle.requestState === 'move', 'legacy_restriction_requires_move_boundary');
            requireInput(native.duration === restriction.remaining_target_turns, 'legacy_restriction_counter_conflict');
            const move = restriction.locked_move_id || restriction.disabled_move_id;
            if (move) requireInput(native.move === toID(move), 'observed_restricted_move_conflict');
          }
        }
        if (Object.hasOwn(observed, 'berry_eaten')) requireInput(pokemon.ateBerry === observed.berry_eaten, 'observed_berry_history_conflict');
        if (Object.hasOwn(observed, 'received_hit_count')) requireInput(pokemon.timesAttacked === observed.received_hit_count, 'observed_received_hit_count_conflict');
        if (observed.last_executed_move) requireInput(pokemon.lastMove?.id === toID(observed.last_executed_move), 'observed_last_executed_move_conflict');
        if (observed.crit_volatiles) requireInput(observed.crit_volatiles.map(toID).sort().join(',') === Object.keys(pokemon.volatiles).filter(id => ['focusenergy', 'lansat', 'dragoncheer'].includes(id)).sort().join(','), 'observed_crit_volatile_conflict');
        if (observed.substitute) {
          requireInput(!!pokemon.volatiles.substitute === observed.substitute.active, 'observed_substitute_conflict');
          if (observed.substitute.active) requireInput(pokemon.volatiles.substitute.hp === observed.substitute.hp, 'observed_substitute_hp_conflict');
        }
        if (observed.status_progression) {
          requireInput(observed.status_progression.schema_version === 'showdown-legacy-status-compatibility-v1', 'unsupported_status_compatibility');
          const progression = observed.status_progression.legacy_record;
          requireInput(pokemon.status === (progression.condition === 'sleep' ? 'slp' : 'frz'), 'observed_status_counter_conflict');
          // A native counter tick is not an action attempt under Early Bird.
          // Count native still-asleep/frozen events in this modeled episode.
          const marker = `: ${pokemon.name}|${pokemon.status}`;
          const applied = battle.log.findLastIndex(line => line.startsWith('|-status|') && line.includes(marker));
          const attempts = battle.log.slice(applied + 1).filter(line => line.startsWith('|cant|') && line.includes(marker)).length;
          const elapsed = pokemon.statusState.startTime - pokemon.statusState.time;
          const compatibleTicks = pokemon.status === 'frz' || (!pokemon.hasAbility('earlybird') && !progression.duration_adjustment?.early_bird_active);
          requireInput((progression.prior_attempts === 0 && elapsed === 0) ||
            (progression.prior_attempts > 0 && (attempts === progression.prior_attempts ||
              (attempts === 0 && compatibleTicks && elapsed === progression.prior_attempts))), 'legacy_status_requires_matching_native_attempt_history');
          if (progression.sleep_duration !== null) requireInput(pokemon.statusState.startTime === progression.sleep_duration, 'observed_sleep_duration_conflict');
        }
        if (Object.hasOwn(observed, 'toxic_next_stage')) requireInput(pokemon.status === 'tox' && pokemon.statusState.stage + 1 === observed.toxic_next_stage, 'observed_toxic_counter_conflict');
        // Overrides are applied only to a detached hypothetical simulator root.
        if (Object.hasOwn(observed, 'hp')) pokemon.hp = observed.hp;
        if (Object.hasOwn(observed, 'fainted')) {
          requireInput(observed.fainted === (pokemon.hp === 0), 'observed_fainted_conflict');
          requireInput(!pokemon.isActive || !observed.fainted || battle.requestState === 'switch', 'fainted_active_requires_native_switch_checkpoint');
        }
        for (const [stat, stage] of Object.entries(observed.boosts)) {
          requireInput(Object.hasOwn(pokemon.boosts, stat) && Number.isInteger(stage) && Math.abs(stage) <= 6, 'invalid_observed_stage');
          pokemon.boosts[stat] = stage;
        }
      }
      battle[id].pokemonLeft = battle[id].pokemon.filter(p => !p.fainted).length;
      const conditions = input.observed_sides?.[side] || {};
      if (conditions.side_conditions) requireInput(conditions.side_conditions.map(toID).sort().join(',') === Object.keys(battle[id].sideConditions).filter(k => ['reflect', 'lightscreen', 'auroraveil', 'tailwind', 'luckychant'].includes(k)).sort().join(','), 'observed_side_conditions_conflict');
      if (Object.hasOwn(conditions, 'tailwind')) requireInput(conditions.tailwind === !!battle[id].sideConditions.tailwind, 'observed_tailwind_conflict');
      for (const [key, value] of Object.entries(conditions.hazards || {})) {
        const native = battle[id].sideConditions[{stealth_rock: 'stealthrock', spikes_layers: 'spikes', toxic_spikes_layers: 'toxicspikes', sticky_web: 'stickyweb'}[key]];
        requireInput(key.endsWith('_layers') ? (native?.layers || 0) === value : !!native === (value === 'present'), 'observed_hazard_conflict');
      }
    }
    for (const [key, nativeKey] of [['weather', 'weather'], ['terrain', 'terrain']]) {
      if (Object.hasOwn(input.observed_field, key)) {
        requireInput(input.observed_field[key] === battle.field[nativeKey], `observed_${key}_conflict`);
      }
    }
    for (const [key, value] of Object.entries(input.observed_field.pseudo_weather || {})) {
      requireInput(!!battle.field.pseudoWeather[key] === value, 'observed_pseudo_weather_conflict');
    }
    // A pivot can pause with another action still queued. Preserve that phase.
    battle.makeRequest(battle.requestState);
    if (input.observed_phase) {
      const phase = input.observed_phase;
      const requesting = [['self', battle.p1], ['opponent', battle.p2]].filter(([, s]) => s.activeRequest && !s.activeRequest.wait);
      requireInput(phase.schema_version === 'battle-decision-phase-v1' && phase.session_id === input.session_id &&
        phase.turn_number === battle.turn && (phase.phase === 'move_selection' ? battle.requestState === 'move' : battle.requestState === 'switch') &&
        requesting.map(([name]) => name).sort().join(',') === phase.requesting_sides.slice().sort().join(','), 'observed_decision_phase_conflict');
      for (const [name, side] of [['self', battle.p1], ['opponent', battle.p2]]) {
        requireInput(side.active[0].name === `slot-${phase.participants[name].slot_index}` &&
          [side.active[0].species.id, battle.dex.species.get(side.active[0].set.species).id].includes(toID(phase.participants[name].pokemon_id)), 'observed_phase_owner_conflict');
      }
      if (phase.phase !== 'move_selection') {
        requireInput(requesting.every(([, side]) => side.active[0].fainted === (phase.phase === 'faint_replacement')), 'observed_replacement_reason_conflict');
      }
    }
    for (const [side, id] of [['self', 'p1'], ['opponent', 'p2']]) {
      const pokemon = battle[id].active[0];
      const permitted = input.observed_sides?.[side]?.switch_permitted;
      if (typeof permitted === 'boolean') requireInput(permitted === (!pokemon.trapped && battle[id].pokemon.some(p => !p.isActive && !p.fainted)), 'observed_switch_permission_conflict');
      for (const [move, usable] of Object.entries(input.observed_active[side].move_usability || {})) {
        const row = battle[id].activeRequest.active?.[0]?.moves.find(m => toID(m.id) === toID(move));
        requireInput(row && (row.pp > 0 && !row.disabled) === usable, 'observed_move_usability_conflict');
      }
    }
  }

  function condition(battle, rows = []) {
    requireInput(Array.isArray(rows) && rows.length <= 32, 'invalid_conditioning');
    for (const row of rows) {
      requireInput(!Object.hasOwn(row, 'source') || ['self', 'opponent'].includes(row.source), 'invalid_conditioning_source');
      const source = row.source ? (row.source === 'self' ? battle.p1 : battle.p2).active[0] : 'debug';
      if (row.effect === 'faint') {
        requireInput(['self', 'opponent'].includes(row.target) && Number.isInteger(row.slot_index), 'invalid_faint_conditioning');
        const side = row.target === 'self' ? battle.p1 : battle.p2;
        const pokemon = side.pokemon.find(p => p.name === `slot-${row.slot_index}`);
        requireInput(pokemon && !pokemon.isActive && !pokemon.fainted, 'invalid_faint_conditioning');
        pokemon.faint();
        battle.faintMessages(false, false, false);
        continue;
      }
      const id = toID(row.id);
      let state;
      if (row.target === 'field') {
        if (row.effect === 'weather') { battle.field.setWeather(id, source); state = battle.field.weatherState; }
        else if (row.effect === 'terrain') { battle.field.setTerrain(id, source); state = battle.field.terrainState; }
        else if (row.effect === 'pseudo') { battle.field.addPseudoWeather(id, source); state = battle.field.pseudoWeather[id]; }
      } else if (['self', 'opponent'].includes(row.target) && row.effect === 'side') {
        const side = row.target === 'self' ? battle.p1 : battle.p2;
        side.addSideCondition(id, source); state = side.sideConditions[id];
        if (Object.hasOwn(row, 'layers')) {
          requireInput(Number.isInteger(row.layers) && row.layers >= 1 && row.layers <= (id === 'spikes' ? 3 : id === 'toxicspikes' ? 2 : 0), 'invalid_hazard_layers');
          for (let layer = 1; layer < row.layers; layer++) side.addSideCondition(id, source);
          requireInput(state?.layers === row.layers, 'native_hazard_initialization_conflict');
        }
      } else if (['self', 'opponent'].includes(row.target) && row.effect === 'status') {
        const pokemon = (row.target === 'self' ? battle.p1 : battle.p2).active[0];
        if (pokemon.status !== id) requireInput(pokemon.setStatus(id, pokemon, null, true), 'native_status_initialization_failed');
        state = pokemon.statusState;
      } else if (['self', 'opponent'].includes(row.target) && row.effect === 'volatile') {
        const pokemon = (row.target === 'self' ? battle.p1 : battle.p2).active[0];
        requireInput(id !== 'leechseed' || row.source && row.source !== row.target, 'leech_seed_source_required');
        pokemon.addVolatile(id, source === 'debug' ? pokemon : source, battle.dex.moves.get(id)); state = pokemon.volatiles[id];
      }
      requireInput(state && state.id === id && battle.dex.conditions.get(id).exists, 'invalid_native_condition');
      if (Object.hasOwn(row, 'counter_state')) {
        const counter = row.counter_state;
        requireInput(row.effect === 'status' && ['slp', 'frz'].includes(id) &&
          counter.schema_version === 'showdown-status-counter-v1' && Number.isInteger(counter.start_time) &&
          (id === 'slp' ? [2, 3].includes(counter.start_time) : counter.start_time === 3) &&
          Number.isInteger(counter.remaining_time) && counter.remaining_time >= 1 && counter.remaining_time <= counter.start_time,
          'invalid_versioned_native_status_counter');
        state.startTime = counter.start_time; state.time = counter.remaining_time;
      }
      if (Object.hasOwn(row, 'remaining')) {
        requireInput(Number.isInteger(row.remaining) && row.remaining >= 1 && row.remaining <= 8, 'invalid_remaining_duration');
        if (row.effect === 'status' && typeof state.time === 'number') {
          requireInput(row.remaining <= state.startTime, 'invalid_remaining_duration');
          state.time = row.remaining;
        } else {
          requireInput(typeof state.duration === 'number' && row.remaining <= state.duration, 'invalid_remaining_duration');
          state.duration = row.remaining;
        }
      }
    }
    if (rows.length && battle.requestState === 'move') {
      // Initialization happens after native nextTurn prepared its request.
      // Reuse the native callbacks to derive newly added move/trap restrictions.
      // Do not advance a turn, drain a timer, or rebuild a paused switch queue.
      for (const pokemon of battle.getAllActive()) {
        battle.runEvent('DisableMove', pokemon);
        battle.runEvent('TrapPokemon', pokemon);
      }
      battle.makeRequest('move');
    }
  }

  function create(scenario) {
    requireInput(Array.isArray(scenario.seed) && scenario.seed.length === 4 &&
      scenario.seed.every(n => Number.isInteger(n) && n >= 0 && n <= 65535), 'invalid_seed');
    const teams = clone(scenario.teams);
    const validator = new TeamValidator(FORMAT);
    for (const side of ['self', 'opponent']) {
      requireInput(Array.isArray(teams[side]) && teams[side].length === 6, 'six_member_team_required');
      requireInput(!validator.validateTeam(teams[side]), 'invalid_mc_team');
      const slots = scenario.slot_mapping?.[side] || [0, 1, 2, 3, 4, 5];
      requireInput(Array.isArray(slots) && slots.length === 6 && new Set(slots).size === 6 && slots.every(n => Number.isInteger(n) && n >= 0), 'invalid_slot_mapping');
      teams[side].forEach((pokemon, index) => { pokemon.name = `slot-${slots[index]}`; });
      const pick = scenario.preview[side];
      requireInput(Array.isArray(pick) && pick.length === 3 && new Set(pick).size === 3 &&
        pick.every(n => Number.isInteger(n) && n >= 1 && n <= 6), 'invalid_team_preview');
    }
    const battle = new Battle({formatid: FORMAT, seed: scenario.seed, strictChoices: true,
      p1: {name: 'self', team: teams.self}, p2: {name: 'opponent', team: teams.opponent}});
    try {
      choose(battle, {self: `team ${scenario.preview.self.join('')}`, opponent: `team ${scenario.preview.opponent.join('')}`});
      condition(battle, scenario.initial_conditioning);
      requireInput(Array.isArray(scenario.history) && scenario.history.length <= 100, 'invalid_history');
      for (const choices of scenario.history) {
        requireInput(!battle.ended, 'history_after_battle_end');
        choose(battle, choices);
      }
      requireInput(['move', 'switch'].includes(battle.requestState) && !battle.ended, 'native_decision_boundary_required');
      condition(battle, scenario.conditioning);
      for (const [side, value] of Object.entries(scenario.hypothetical_active_hp || {})) {
        requireInput(['self', 'opponent'].includes(side), 'invalid_hypothetical_hp_side');
        const pokemon = (side === 'self' ? battle.p1 : battle.p2).active[0];
        requireInput(Number.isInteger(value) && value >= 1 && value <= pokemon.maxhp, 'invalid_hypothetical_hp');
        pokemon.hp = value;
      }
      overlay(battle, scenario);
      return battle;
    } catch (error) { battle.destroy(); throw error; }
  }

  function evaluate(scenario) {
    let root, branch;
    const started = performance.now();
    try {
      if (['resume', 'reconcile', 'status_gate', 'damage_rolls'].includes(input.operation)) {
        const saved = scenario.checkpoint;
        requireInput(saved.schema_version === 'showdown-checkpoint-v1' && saved.engine_commit === COMMIT &&
          saved.observation_schema_version === OBSERVATION_SCHEMA &&
          saved.format_id === FORMAT && saved.session_id === input.session_id &&
          (input.operation === 'reconcile' || saved.source_runtime_fingerprint === input.source_runtime_fingerprint) &&
          saved.native_state.formatid === FORMAT, 'checkpoint_binding_mismatch');
        root = Battle.fromJSON(clone(saved.native_state));
        root.restart(() => {});
        if (input.operation === 'reconcile') {
          requireInput(Array.isArray(scenario.history) && scenario.history.length <= 100, 'invalid_history');
          for (const choices of scenario.history) {
            requireInput(!root.ended, 'history_after_battle_end');
            choose(root, choices);
          }
          requireInput(['move', 'switch'].includes(root.requestState) && !root.ended, 'native_decision_boundary_required');
          // Only a fresh construction may run initialization effects.
          requireInput(!scenario.conditioning?.length, 'reconciliation_requires_native_history_for_new_effects');
          overlay(root, scenario);
        }
      } else { root = create(scenario); }
      requireInput(!root.ended, 'battle_already_ended');
      const rootCheckpoint = checkpoint(root, scenario);
      const before = summarize(root);
      if (input.operation === 'status_gate') return {status: 'simulated', scenario_id: scenario.scenario_id,
        assumptions: clone(scenario.assumptions), before, root_checkpoint: rootCheckpoint,
        status_gate: evaluateStatusGate(Battle, rootCheckpoint, scenario.status_query), elapsed_ms: performance.now() - started};
      if (input.operation === 'damage_rolls') {
        let damage;
        try { damage = evaluateDamageRolls(Battle, rootCheckpoint, scenario.damage_query); }
        catch (error) { if (error instanceof NativeDamageError) throw new InputError(error.message); throw error; }
        return {status: 'simulated', scenario_id: scenario.scenario_id, assumptions: clone(scenario.assumptions),
          before, root_checkpoint: rootCheckpoint, damage_rolls: damage, elapsed_ms: performance.now() - started};
      }
      if (scenario.evaluation) {
        return {status: 'simulated', scenario_id: scenario.scenario_id,
          interpretation: 'conditional_monte_carlo_estimate_not_exact_probability',
          assumptions: clone(scenario.assumptions), before, root_checkpoint: rootCheckpoint,
          evaluation: sample(rootCheckpoint, scenario.evaluation), elapsed_ms: performance.now() - started};
      }
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
  function sample(saved, evaluation) {
    const {seeds, candidates} = evaluation;
    requireInput(Array.isArray(seeds) && seeds.length >= 1 && seeds.length <= 256 &&
      seeds.every(seed => Array.isArray(seed) && seed.length === 4 && seed.every(n => Number.isInteger(n) && n >= 0 && n <= 65535)) &&
      new Set(seeds.map(seed => seed.join(','))).size === seeds.length, 'invalid_sample_seeds');
    requireInput(Array.isArray(candidates) && candidates.length >= 1 && candidates.length <= 16 &&
      candidates.every(c => typeof c.candidate_id === 'string' && c.candidate_id.length > 0 && Array.isArray(c.choices) && c.choices.length >= 1 && c.choices.length <= 8) &&
      new Set(candidates.map(c => c.candidate_id)).size === candidates.length, 'invalid_sample_candidates');
    requireInput(seeds.length * candidates.reduce((n, c) => n + c.choices.length, 0) <= 8192, 'sample_budget_exceeded');
    const rows = candidates.map(candidate => {
      const samples = [];
      for (const seed of seeds) {
        let battle;
        try {
          battle = Battle.fromJSON(clone(saved.native_state));
          battle.restart(() => {});
          battle.prng = new PRNG(seed);
          let decisions = 0;
          for (const choices of candidate.choices) {
            if (battle.ended) break;
            choose(battle, choices);
            decisions++;
          }
          samples.push({seed: clone(seed), decisions, turn: battle.turn, ended: battle.ended,
            winner: battle.winner || null, request_state: battle.requestState,
            self_hp: battle.p1.pokemon.reduce((n, p) => n + p.hp, 0),
            opponent_hp: battle.p2.pokemon.reduce((n, p) => n + p.hp, 0),
            self_fainted: battle.p1.pokemon.filter(p => p.fainted).length,
            opponent_fainted: battle.p2.pokemon.filter(p => p.fainted).length});
        } catch (error) {
          // No missing action is auto-selected and no invalid seed is counted.
          return {status: 'rejected', candidate_id: candidate.candidate_id,
            reason: error instanceof InputError ? error.message : 'native_sample_failed'};
        } finally { battle?.destroy(); }
      }
      const n = samples.length;
      const mean = key => samples.reduce((sum, row) => sum + row[key], 0) / n;
      const count = test => samples.filter(test).length;
      const initial = saved.native_state.sides.map(side => side.pokemon.filter(p => p.fainted).length);
      return {status: 'evaluated', candidate_id: candidate.candidate_id, sample_count: n,
        horizon_decisions: candidate.choices.length, choices: clone(candidate.choices),
        self_new_faint_samples: count(s => s.self_fainted > initial[0]),
        opponent_new_faint_samples: count(s => s.opponent_fainted > initial[1]),
        self_win_samples: count(s => s.winner === 'self'), opponent_win_samples: count(s => s.winner === 'opponent'),
        ended_samples: count(s => s.ended), switch_request_samples: count(s => s.request_state === 'switch'),
        mean_self_team_hp: mean('self_hp'), mean_opponent_team_hp: mean('opponent_hp'), samples};
    });
    return {schema_version: 'showdown-sampled-evaluation-v1', interpretation: 'conditional_monte_carlo_estimate_not_exact_probability',
      aggregation: 'per_scenario_no_implicit_opponent_prior', seeds: clone(seeds), candidates: rows};
  }
  requireInput(['simulate', 'resume', 'reconcile', 'status_gate', 'damage_rolls'].includes(input.operation), 'invalid_operation');
  requireInput(Array.isArray(input.scenarios) && input.scenarios.length > 0 && input.scenarios.length <= 16, 'invalid_scenarios');
  requireInput(new Set(input.scenarios.map(s => s.scenario_id)).size === input.scenarios.length &&
    input.scenarios.every(s => typeof s.scenario_id === 'string' && s.scenario_id.length > 0 && Array.isArray(s.assumptions)), 'invalid_scenario_identity');
  return {schema_version: SCHEMA, engine_commit: COMMIT, format_id: FORMAT,
    observation_schema_version: OBSERVATION_SCHEMA,
    session_id: input.session_id, source_runtime_fingerprint: input.source_runtime_fingerprint,
    scenarios: input.scenarios.map(evaluate)};
}

module.exports = {run};
if (require.main === module) try {
  const payload = fs.readFileSync(0, 'utf8');
  requireInput(Buffer.byteLength(payload) <= 8 * 1024 * 1024, 'request_too_large');
  const engine = require(path.join(process.argv[2], 'dist', 'sim'));
  process.stdout.write(JSON.stringify(run(JSON.parse(payload), engine)));
} catch (error) {
  process.stdout.write(JSON.stringify({status: 'error', reason: error instanceof InputError ? error.message : 'bridge_failed'}));
  process.exitCode = 1;
}
