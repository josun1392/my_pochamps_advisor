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
module.exports = {progressNativeBattle, NativeActionPause};
