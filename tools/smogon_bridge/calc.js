const { calculate, Generations, Pokemon, Move, Field, TYPE_CHART } = require('@smogon/calc');

const STAT_KEYS = ['hp', 'atk', 'def', 'spa', 'spd', 'spe'];

function readStdin(callback) {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {
    input += chunk;
  });
  process.stdin.on('end', () => callback(input));
}

function toCalcWeather(weather) {
  if (weather === null || weather === undefined) return undefined;
  const values = {
    sun: 'Sun',
    'harsh-sunlight': 'Harsh Sunshine',
    rain: 'Rain',
    'heavy-rain': 'Heavy Rain',
    sand: 'Sand',
    hail: 'Hail',
    snow: 'Snow',
    harsh_sunshine: 'Harsh Sunshine',
    heavy_rain: 'Heavy Rain',
    'strong-winds': 'Strong Winds',
    strong_winds: 'Strong Winds'
  };
  return values[weather] || weather;
}

function toCalcTerrain(terrain) {
  if (terrain === null || terrain === undefined) return undefined;
  const values = {
    electric: 'Electric',
    grassy: 'Grassy',
    misty: 'Misty',
    psychic: 'Psychic'
  };
  return values[terrain] || terrain;
}

function titleWord(word) {
  return word.length === 0 ? word : word[0].toUpperCase() + word.slice(1);
}

function toCalcName(value, separator = ' ') {
  if (value === null || value === undefined || value === '') return undefined;
  const specialNames = {
    'well-baked-body': 'Well-Baked Body',
    'mind-s-eye': "Mind's Eye"
  };
  const raw = String(value);
  if (Object.prototype.hasOwnProperty.call(specialNames, raw.toLowerCase())) {
    return specialNames[raw.toLowerCase()];
  }
  return raw
    .split('-')
    .map(titleWord)
    .join(separator);
}

function normalizeBoosts(boosts) {
  const normalized = {};
  for (const key of STAT_KEYS) {
    if (key !== 'hp') normalized[key] = boosts?.[key] ?? 0;
  }
  return normalized;
}

function makePokemon(gen, input, fieldInput) {
  const ability = String(input.ability || '').toLowerCase();
  const pokemon = new Pokemon(gen, toCalcName(input.species, '-'), {
    level: input.level,
    ability: toCalcName(input.ability),
    abilityOn: !!fieldInput?.ally_has_plus_minus && (ability === 'plus' || ability === 'minus'),
    item: toCalcName(input.item),
    nature: toCalcName(input.nature),
    evs: input.evs,
    ivs: input.ivs,
    boosts: normalizeBoosts(input.boosts),
    status: input.status || undefined,
    teraType: toCalcName(input.tera_type),
    isTerastallized: input.is_terastallized,
    boostedStat: input.boosted_stat || undefined
  });
  if (input.current_hp_pct !== undefined && input.current_hp_pct !== null) {
    pokemon.originalCurHP = Math.floor((pokemon.maxHP() * input.current_hp_pct) / 100);
  }
  return pokemon;
}

function makeMove(gen, input) {
  return new Move(gen, toCalcName(input.name), {
    isCrit: input.is_critical,
    isZ: input.is_z,
    useMax: input.is_max
  });
}

function makeField(input) {
  return new Field({
    weather: toCalcWeather(input.weather),
    terrain: toCalcTerrain(input.terrain),
    gameType: input.format && input.format.includes('doubles') ? 'Doubles' : 'Singles',
    isGravity: input.is_gravity,
    isTrickRoom: input.is_trick_room,
    defenderSide: toCalcSide(input.defender_side),
    attackerSide: toCalcSide(input.attacker_side)
  });
}

function toCalcSide(side) {
  if (!side) return undefined;
  return {
    isReflect: !!side.reflect,
    isLightScreen: !!side.light_screen,
    isAuroraVeil: !!side.aurora_veil
  };
}

function flattenDamage(damage) {
  if (Array.isArray(damage)) {
    return damage.flatMap(flattenDamage);
  }
  return [damage];
}

function typeEffectiveness(genNum, moveType, defenderTypes) {
  const chart = TYPE_CHART[genNum]?.[moveType];
  if (!chart) return 1.0;
  return defenderTypes.reduce((multiplier, type) => multiplier * (chart[type] ?? 1), 1.0);
}

function weatherModifier(moveType, weather) {
  if (weather === 'Sun' && moveType === 'Fire') return 1.5;
  if (weather === 'Sun' && moveType === 'Water') return 0.5;
  if (weather === 'Rain' && moveType === 'Water') return 1.5;
  if (weather === 'Rain' && moveType === 'Fire') return 0.5;
  return 1.0;
}

function itemModifier(item) {
  if (!item) return 1.0;
  return item.toLowerCase() === 'life-orb' || item.toLowerCase() === 'life orb' ? 1.3 : 1.0;
}

function stabModifier(attacker, move) {
  return attacker.types.includes(move.type) ? 1.5 : 1.0;
}

function roundPct(value) {
  return Math.round(value * 10) / 10;
}

function buildResponse(req) {
  const gen = Generations.get(9);
  const attacker = makePokemon(gen, req.attacker, req.field);
  const defender = makePokemon(gen, req.defender, req.field);
  const move = makeMove(gen, req.move);
  const field = makeField(req.field);
  const result = calculate(gen, attacker, defender, move, field);
  const damageRolls = result.damage === 0 ? Array(16).fill(0) : flattenDamage(result.damage);
  const damageMin = Math.min(...damageRolls);
  const damageMax = Math.max(...damageRolls);
  const defenderHp = defender.maxHP();
  const koChance = damageMax === 0
    ? { n: 0, chance: 0, text: '0% chance to KO' }
    : result.kochance();
  const weather = toCalcWeather(req.field.weather);

  return {
    schema_version: 'v1',
    damage_rolls: damageRolls,
    damage_min: damageMin,
    damage_max: damageMax,
    damage_min_pct: roundPct((damageMin / defenderHp) * 100),
    damage_max_pct: roundPct((damageMax / defenderHp) * 100),
    ko_chance: {
      n_hits: koChance.n,
      chance: koChance.chance ?? 0,
      description: koChance.text
    },
    modifiers: {
      stab: stabModifier(attacker, move),
      weather: weatherModifier(move.type, weather),
      type_effectiveness: typeEffectiveness(gen.num, move.type, defender.types),
      burn: req.attacker.status === 'brn' && move.category === 'Physical' ? 0.5 : 1.0,
      screens: 1.0,
      item: itemModifier(req.attacker.item),
      ability_attacker: 1.0,
      ability_defender: 1.0
    },
    raw_calc_desc: damageMax === 0 ? 'No effect' : result.desc()
  };
}

readStdin(input => {
  try {
    const req = JSON.parse(input);
    if (req.schema_version !== 'v1') {
      throw new Error(`Unsupported schema_version: ${req.schema_version}`);
    }
    const response = buildResponse(req);
    process.stdout.write(JSON.stringify(response));
  } catch (err) {
    process.stderr.write(JSON.stringify({ error: err.message, stack: err.stack }));
    process.exit(1);
  }
});
