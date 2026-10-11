'use strict';

// Stop only after the entire upstream runAction callback has returned. Native
// queue ordering, gates, Update/faint/pivot handling and RNG remain upstream.
class NativeActionPause extends Error {}
function progressNativeBattle(battle, perform, stopAfterMove) {
  const original = battle.runAction;
  const descriptor = Object.getOwnPropertyDescriptor(battle, 'runAction');
  const pause = new NativeActionPause();
  const attempts = [];
  battle.runAction = function (action) {
    const before = action.pokemon?.activeMoveActions;
    const result = original.call(this, action);
    if (action.choice === 'move' && action.pokemon.activeMoveActions > before) {
      attempts.push({side: action.pokemon.side.id === 'p1' ? 'self' : 'opponent',
        slot_index: Number(action.pokemon.name.replace('slot-', '')), queued_move: action.move.id});
      if (stopAfterMove && !this.requestState && !this.ended) throw pause;
    }
    return result;
  };
  try { perform(); }
  catch (error) { if (error !== pause) throw error; }
  finally {
    // Functions must never enter the native serialized checkpoint.
    if (descriptor) Object.defineProperty(battle, 'runAction', descriptor);
    else delete battle.runAction;
  }
  return {schema_version: 'showdown-native-action-step-v1',
    interpretation: 'conditional_seeded_native_progression_not_exact_probability',
    move_attempts: attempts, stopped_at: battle.ended ? 'battle_end' : battle.requestState ? 'native_request' : 'paused_native_queue'};
}
class NativeSwitchBoundaryRequired extends Error {}
function progressNativeSwitchEntry(battle, perform) {
  const original = battle.runAction;
  const descriptor = Object.getOwnPropertyDescriptor(battle, 'runAction');
  const pause = new NativeActionPause();
  const switches = [], entries = [];
  battle.runAction = function (action) {
    // A switch-entry proof never includes a subsequent attack.
    if (action.choice === 'move') throw new NativeSwitchBoundaryRequired('native_switch_entry_before_move_required');
    const incoming = action.choice === 'runSwitch' ? [action.pokemon] : [];
    if (incoming.length) {
      // Upstream runSwitch consumes the consecutive entry batch itself.
      for (const pending of this.queue.list) {
        if (pending.choice !== 'runSwitch') break;
        incoming.push(pending.pokemon);
      }
    }
    const result = original.call(this, action);
    if (['switch', 'instaswitch'].includes(action.choice)) {
      switches.push({side: action.pokemon.side.id === 'p1' ? 'self' : 'opponent',
        from_slot: Number(action.pokemon.name.replace('slot-', '')),
        incoming_slot: Number(action.target.name.replace('slot-', ''))});
    }
    if (incoming.length) {
      entries.push(...incoming.map(p => ({side: p.side.id === 'p1' ? 'self' : 'opponent',
        slot_index: Number(p.name.replace('slot-', '')), fainted: p.fainted})));
      if (!this.requestState && !this.ended && this.queue.list.length) throw pause;
    }
    return result;
  };
  try { perform(); }
  catch (error) { if (error !== pause) throw error; }
  finally {
    if (descriptor) Object.defineProperty(battle, 'runAction', descriptor);
    else delete battle.runAction;
  }
  if (!switches.length || !entries.length) throw new NativeSwitchBoundaryRequired('native_switch_entry_missing');
  return {schema_version: 'showdown-native-switch-entry-step-v1',
    interpretation: 'conditional_native_switch_batch_not_selected_action_probability',
    committed_switches: switches, completed_entries: entries,
    stopped_at: battle.ended ? 'battle_end' : battle.requestState ? 'native_request' : 'paused_native_queue'};
}
module.exports = {progressNativeBattle, progressNativeSwitchEntry, NativeActionPause, NativeSwitchBoundaryRequired};
