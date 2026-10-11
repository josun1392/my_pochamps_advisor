'use strict';
// Shared native legality/preview construction. No battle mechanics here.
const FORMAT = 'gen9championsbssregmc';
function createLegalBattle(scenario, engine, requireInput) {
  const {Battle, TeamValidator} = engine;
  const format = engine.Dex.formats.get(FORMAT);
  requireInput(format.exists && format.mod === 'champions' && format.gameType === 'singles', 'format_unavailable');
  requireInput(Array.isArray(scenario.seed) && scenario.seed.length === 4 &&
    scenario.seed.every(n => Number.isInteger(n) && n >= 0 && n <= 65535), 'invalid_seed');
  const teams = JSON.parse(JSON.stringify(scenario.teams));
  const validator = new TeamValidator(FORMAT);
  for (const side of ['self', 'opponent']) {
    requireInput(Array.isArray(teams?.[side]) && teams[side].length === 6, 'six_member_team_required');
    requireInput(!validator.validateTeam(teams[side]), 'invalid_mc_team');
    const slots = scenario.slot_mapping?.[side] || [0, 1, 2, 3, 4, 5];
    requireInput(Array.isArray(slots) && slots.length === 6 && new Set(slots).size === 6 &&
      slots.every(n => Number.isInteger(n) && n >= 0), 'invalid_slot_mapping');
    teams[side].forEach((pokemon, index) => { pokemon.name = `slot-${slots[index]}`; });
    const pick = scenario.preview?.[side];
    requireInput(Array.isArray(pick) && pick.length === 3 && new Set(pick).size === 3 &&
      pick.every(n => Number.isInteger(n) && n >= 1 && n <= 6), 'invalid_team_preview');
  }
  const battle = new Battle({formatid: FORMAT, seed: scenario.seed, strictChoices: true,
    p1: {name: 'self', team: teams.self}, p2: {name: 'opponent', team: teams.opponent}});
  try {
    requireInput(battle.choose('p1', `team ${scenario.preview.self.join('')}`), 'illegal_preview');
    requireInput(battle.choose('p2', `team ${scenario.preview.opponent.join('')}`), 'illegal_preview');
    return battle;
  } catch (error) { battle.destroy(); throw error; }
}
module.exports = {createLegalBattle};
