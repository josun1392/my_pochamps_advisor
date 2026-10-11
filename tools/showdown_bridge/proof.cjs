'use strict';

// Verification harness only: local automatic choices never enter the advisor API.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {performance} = require('node:perf_hooks');
const {Battle} = require(path.join(process.argv[2], 'dist', 'sim'));
const {State} = require(path.join(process.argv[2], 'dist', 'sim', 'state'));
const fixture = JSON.parse(fs.readFileSync(0, 'utf8'));
const clone = value => JSON.parse(JSON.stringify(value));
function start(seed = fixture.seed) {
  const b = new Battle({formatid: 'gen9championsbssregmc', seed, strictChoices: true,
    p1: {name: 'self', team: clone(fixture.teams.self)},
    p2: {name: 'opponent', team: clone(fixture.teams.opponent)}});
  b.makeChoices('team 123', 'team 123');
  return b;
}
const normalized = battle => State.normalize(clone(battle.toJSON()));
let control = start(), restored = start();
let decisions = 0;
while (!control.ended && decisions < 300) {
  control.makeChoices();
  restored.makeChoices();
  assert.deepEqual(normalized(control), normalized(restored));
  const checkpoint = clone(restored.toJSON());
  restored.destroy();
  restored = Battle.fromJSON(clone(checkpoint));
  restored.restart(() => {});
  decisions++;
}
assert(control.ended && restored.ended, 'complete offline battle must terminate');
const complete = {decisions, turns: control.turn, winner: control.winner, restored_each_decision: true};
control.destroy();restored.destroy();

const protectedBattle = start();
protectedBattle.makeChoices('move 1', 'move 3');
assert.equal(protectedBattle.p2.active[0].hp, protectedBattle.p2.active[0].maxhp);
assert(protectedBattle.log.some(line => line.startsWith('|-activate|p2a: Scizor|move: Protect')));
const checkpoint = clone(protectedBattle.toJSON());
const independent = Battle.fromJSON(clone(checkpoint));independent.restart(() => {});
protectedBattle.makeChoices('move 2', 'move 2');independent.makeChoices('move 2', 'move 2');
assert.deepEqual(normalized(protectedBattle), normalized(independent));
protectedBattle.destroy();independent.destroy();

const frozenBattle = start();
assert(frozenBattle.p2.active[0].setStatus('frz'));
assert.equal(frozenBattle.p2.active[0].statusState.time, 3);
let frozenRestored = Battle.fromJSON(clone(frozenBattle.toJSON()));
frozenRestored.restart(() => {});
for (let i = 0; i < 3; i++) {
  frozenBattle.makeChoices('move 3', 'move 2');
  frozenRestored.makeChoices('move 3', 'move 2');
  assert.deepEqual(normalized(frozenBattle), normalized(frozenRestored));
}
assert.equal(frozenBattle.p2.active[0].status, '');
frozenBattle.destroy();frozenRestored.destroy();

const damageSamples = [], accuracy = {hit: 0, miss: 0};
for (let i = 1; i <= 64; i++) {
  const b = start([i, i * 31, i * 97, i * 127]);
  b.makeChoices('move 2', 'move 2');
  damageSamples.push(b.p2.active[0].hp);
  accuracy[b.log.some(line => line.startsWith('|-miss|')) ? 'miss' : 'hit']++;
  b.destroy();
}
assert(new Set(damageSamples).size > 1, 'different seeds must produce different native outcomes');
assert(accuracy.hit > 0 && accuracy.miss > 0, 'native seeded accuracy must include hits and misses');
const warmBattle = start();
const warmRoot = clone(warmBattle.toJSON());
warmBattle.destroy();
const timings = [];
for (let i = 0; i < 200; i++) {
  const begun = performance.now();
  const b = Battle.fromJSON(clone(warmRoot));b.restart(() => {});
  b.makeChoices('move 1', 'move 1');b.destroy();
  timings.push(performance.now() - begun);
}
timings.sort((a, b) => a - b);
process.stdout.write(JSON.stringify({complete_battle: complete, native_protect: true, native_freeze_timer_restore: true,
  seeded_accuracy_samples: accuracy, distinct_seeded_hp: [...new Set(damageSamples)].sort((a,b) => a-b),
  warm_restore_and_choice_ms: {iterations: timings.length, p50: timings[100], p95: timings[190]}}));
