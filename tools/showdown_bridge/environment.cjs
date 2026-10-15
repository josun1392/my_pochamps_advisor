'use strict';
const {createHash} = require('node:crypto');
const {createLegalBattle, createPreviewBattle} = require('./legal-battle.cjs');
const SCHEMA = 'showdown-environment-v1';
const PIN = '942cda71d14bf0618bd57991708a2e2734b6daba';
const FORMAT = 'gen9championsbssregmc';
const SIDES = ['self', 'opponent'];
const clone = value => JSON.parse(JSON.stringify(value));
class EnvironmentError extends Error {}
const requireInput = (ok, reason) => { if (!ok) throw new EnvironmentError(reason); };
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
  return value;
}
function digest(value) { return createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex'); }

// Request-visible actions only. Never test hidden trapping/disable information.
function actions(request, ended) {
  const choices = Array(35).fill(null);
  if (ended) return choices;
  if (!request || request.wait) { choices[26] = ''; return choices; }
  const active = request.active?.[0], pokemon = request.side.pokemon;
  if (!active?.trapped) pokemon.forEach((p, i) => {
    const fainted = p.condition.endsWith(' fnt');
    if (!p.active && (pokemon[0].reviving ? fainted : !fainted)) choices[i] = `switch ${i + 1}`;
  });
  if (active) active.moves.forEach((move, i) => {
    if (move.disabled) return;
    choices[6 + i] = `move ${i + 1}`;
    for (const [key, offset, suffix] of [['canMegaEvo', 10, 'mega'], ['canDynamax', 18, 'dynamax'],
      ['canTerastallize', 22, 'terastallize'], ['canMegaEvoX', 27, 'megax'], ['canMegaEvoY', 31, 'megay']]) {
      if (active[key]) choices[offset + i] = `move ${i + 1} ${suffix}`;
    }
    if (active.canZMove?.[i]) choices[14 + i] = `move ${i + 1} zmove`;
  });
  return choices;
}

function createEnvironmentService(engine) {
  const episodes = new Map();
  const stats = () => ({episodes: episodes.size, rss_bytes: process.memoryUsage().rss,
    heap_used_bytes: process.memoryUsage().heapUsed});
  function view(episode, rejected = false) {
    const {battle, owner, revision, decisions, maxDecisions} = episode;
    const terminated = battle.ended, truncated = !terminated && decisions >= maxDecisions;
    const logs = engine.extractChannelMessages(battle.log.slice(episode.cursor).join('\n'), [1, 2]);
    const observations = Object.fromEntries(SIDES.map((side, i) => {
      const request = clone(battle.sides[i].activeRequest || {wait: true});
      const choices = actions(request, terminated || truncated);
      // Only native client-visible channels. Never inputLog, queue, sets or RNG.
      const events = logs[i + 1].filter(line => line && !/^\|(t:|debug|seed|error|request|html|uhtml|uhtmlchange)\|/.test(line));
      const visibleHealth = battle.sides.filter((_, index) => index !== i).flatMap(s => s.active.filter(Boolean).map(p => {
        const health = p.getHealth();
        return {identity: p.toString(), condition: health.side === `p${i + 1}` ? health.secret : health.shared};
      }));
      return [side, {schema_version: 'showdown-policy-observation-v1', episode_id: owner, revision,
        side, turn: battle.turn, request_state: terminated ? 'ended' : battle.requestState,
        terminated, truncated, events, own_request: request, visible_active_health: visibleHealth,
        action_schema_version: 'showdown-policy-actions-v1', action_mask: choices.map(c => c === null ? 0 : 1),
        choices}];
    }));
    episode.cursor = battle.log.length;
    // Keep the execution view closed at its budget. Bootstrap legality is a
    // separate, versioned public-request view, never a hidden-state query.
    const timeoutBootstrap = truncated ? {
      schema_version: 'showdown-public-timeout-bootstrap-v1', episode_id: owner, revision,
      requests: Object.fromEntries(SIDES.map(side => {
        const choices = actions(observations[side].own_request, false);
        return [side, {action_mask: choices.map(c => c === null ? 0 : 1), choices}];
      })),
    } : null;
    const selfReward = terminated ? (battle.winner === 'self' ? 1 : battle.winner === 'opponent' ? -1 : 0) : 0;
    return {status: 'ready', owner, revision, decisions, terminated, truncated,
      winner: terminated ? (battle.winner || null) : null, action_rejected: rejected,
      rewards: {self: selfReward, opponent: -selfReward}, observations,
      timeout_bootstrap: timeoutBootstrap};
  }
  function save(episode) {
    const native = clone(episode.battle.toJSON());
    // Preserve line indices used by lastMoveLine and native queued execution.
    native.log = native.log.map(line => line.startsWith('|t:|') ? '|t:|0' : line);
    const checkpoint = {schema_version: 'showdown-environment-checkpoint-v1',
      interpretation: 'privileged_hypothetical_hidden_truth_never_policy_input', engine_commit: PIN, format_id: FORMAT,
      decisions: episode.decisions, max_decisions: episode.maxDecisions, consecutive_rejections: episode.rejections,
      provenance: clone(episode.provenance), native_state: native};
    return {...checkpoint, digest: digest(checkpoint)};
  }
  function one(row) {
    let created;
    try {
      requireInput(typeof row.owner === 'string' && /^[a-f0-9]{32}$/.test(row.owner), 'invalid_episode_owner');
      if (row.operation === 'inspect_preview') {
        // Temporary native battle before ANY team choice. No episode, selected
        // three, future history, opposing request, set or engine RNG in a view.
        created = createPreviewBattle(row.scenario, engine, requireInput);
        requireInput(created.requestState === 'teampreview', 'native_preview_unavailable');
        const logs = engine.extractChannelMessages(created.log.join('\n'), [1, 2]);
        const observations = Object.fromEntries(SIDES.map((side, i) => [side, {
          schema_version: 'showdown-public-preview-v1', side,
          own_request: clone(created.sides[i].activeRequest),
          events: logs[i + 1].filter(line => /^\|(poke|clearpoke|teampreview|teamsize|gametype|gen|tier|rule)\|/.test(line)),
        }]));
        created.destroy(); created = null;
        return {status: 'preview', owner: row.owner, revision: 0, observations};
      }
      if (row.operation === 'reset' || row.operation === 'restart' || row.operation === 'import_native') {
        requireInput(!episodes.has(row.owner), 'episode_owner_exists');
        requireInput(episodes.size < 128, 'environment_capacity_exceeded');
        let decisions = 0, maxDecisions = row.max_decisions, provenance;
        if (row.operation === 'reset') {
          const scenario = row.scenario;
          requireInput(scenario && !(scenario.history?.length || scenario.conditioning?.length ||
            scenario.initial_conditioning?.length || Object.keys(scenario.hypothetical_active_hp || {}).length),
            'use_reconciled_checkpoint_for_conditioned_state');
          created = createLegalBattle(scenario, engine, requireInput);
          provenance = {kind: 'hypothetical_episode', scenario_id: scenario.scenario_id || null};
        } else {
          const cp = row.checkpoint;
          requireInput(cp?.engine_commit === PIN && cp.format_id === FORMAT && cp.native_state?.formatid === FORMAT,
            'checkpoint_engine_mismatch');
          if (row.operation === 'restart') {
            const {digest: expected, ...body} = cp;
            requireInput(cp.schema_version === 'showdown-environment-checkpoint-v1' && expected === digest(body),
              'checkpoint_integrity_mismatch');
            decisions = cp.decisions; maxDecisions = cp.max_decisions; provenance = cp.provenance;
            requireInput(Number.isSafeInteger(decisions) && decisions >= 0 && decisions <= maxDecisions, 'invalid_checkpoint_decisions');
          } else {
            requireInput(cp.schema_version === 'showdown-checkpoint-v1' &&
              cp.observation_schema_version === 'showdown-observed-projection-v2' &&
              typeof cp.session_id === 'string' && typeof cp.source_runtime_fingerprint === 'string', 'invalid_native_checkpoint');
            provenance = {kind: 'detached_reconciled_native_checkpoint', session_id: cp.session_id,
              source_runtime_fingerprint: cp.source_runtime_fingerprint, scenario_id: cp.scenario_id};
          }
          created = engine.Battle.fromJSON(clone(cp.native_state));
          created.restart(() => {});
        }
        if (row.future_seed !== undefined) {
          requireInput(row.operation === 'restart' && Array.isArray(row.future_seed) && row.future_seed.length === 4 &&
            row.future_seed.every(n => Number.isInteger(n) && n >= 0 && n <= 65535), 'invalid_counterfactual_future_seed');
          // Same maintained PRNG sampling seam as bridge.cjs sample(). No
          // hidden state edits or public "RNG reset" protocol announcement.
          created.prng = new engine.PRNG(row.future_seed);
          provenance = {...clone(provenance), counterfactual_future_seed: clone(row.future_seed)};
        }
        requireInput(Number.isInteger(maxDecisions) && maxDecisions >= 1 && maxDecisions <= 4096, 'invalid_episode_budget');
        requireInput(created.ended || ['move', 'switch'].includes(created.requestState), 'unsupported_native_phase');
        requireInput(created.sides.length === 2 && created.gameType === 'singles', 'unsupported_native_battle');
        const rejections = row.operation === 'restart' ? row.checkpoint.consecutive_rejections : 0;
        requireInput(Number.isInteger(rejections) && rejections >= 0 && rejections < 32, 'invalid_checkpoint_rejections');
        const episode = {battle: created, owner: row.owner, revision: 0, decisions, maxDecisions, provenance, cursor: 0, rejections};
        episodes.set(row.owner, episode); created = null;
        return view(episode);
      }
      const episode = episodes.get(row.owner);
      requireInput(episode, 'episode_not_found_restore_saved_checkpoint');
      requireInput(row.revision === episode.revision, 'stale_episode_revision');
      if (row.operation === 'save') return {status: 'saved', owner: row.owner, revision: episode.revision, checkpoint: save(episode)};
      if (row.operation === 'close') {
        episodes.delete(row.owner); episode.battle.destroy();
        return {status: 'closed', owner: row.owner, revision: episode.revision};
      }
      requireInput(row.operation === 'step', 'invalid_environment_operation');
      const battle = episode.battle;
      requireInput(!battle.ended && episode.decisions < episode.maxDecisions, 'episode_finished_reset_required');
      requireInput(row.actions && Object.keys(row.actions).sort().join(',') === 'opponent,self', 'invalid_joint_actions');
      const choices = SIDES.map((side, i) => {
        const index = row.actions[side], available = actions(battle.sides[i].activeRequest, false);
        requireInput(Number.isInteger(index) && index >= 0 && index < available.length && available[index] !== null, 'masked_or_invalid_action');
        return available[index];
      });
      // Native Side.choose validates both requests before Battle.commitChoices.
      // Unknown trapping can reveal a new native request; do not fabricate legality.
      let rejected = false;
      for (let i = 0; i < 2; i++) {
        if (!choices[i]) continue;
        try { if (!battle.sides[i].choose(choices[i]) || !battle.sides[i].isChoiceDone()) rejected = true; }
        catch { rejected = true; }
      }
      if (rejected) {
        for (const side of battle.sides) side.clearChoice();
        episode.rejections++;
        if (episode.rejections >= 32) {
          episodes.delete(row.owner); battle.destroy();
          throw new EnvironmentError('native_request_retry_limit_restore_saved_checkpoint');
        }
      } else {
        requireInput(battle.allChoicesDone(), 'native_joint_choice_incomplete');
        try { battle.commitChoices(); episode.decisions++; episode.rejections = 0; }
        catch {
          // No half-executed native state is reusable after an engine exception.
          episodes.delete(row.owner); battle.destroy();
          throw new EnvironmentError('native_execution_failed_restore_saved_checkpoint');
        }
      }
      episode.revision++;
      return view(episode, rejected);
    } catch (error) {
      created?.destroy();
      if (!(error instanceof EnvironmentError)) {
        const failed = episodes.get(row.owner);
        if (failed) { episodes.delete(row.owner); failed.battle.destroy(); }
      }
      return {status: 'rejected', owner: row.owner, reason: error instanceof EnvironmentError ? error.message : 'native_environment_failed'};
    }
  }
  return input => {
    requireInput(input.schema_version === SCHEMA && input.format_id === FORMAT, 'invalid_environment_schema');
    requireInput(Array.isArray(input.requests) && input.requests.length >= 1 && input.requests.length <= 64, 'invalid_environment_batch');
    return {schema_version: SCHEMA, engine_commit: PIN, format_id: FORMAT,
      results: input.requests.map(one), resources: stats()};
  };
}
module.exports = {createEnvironmentService};
