'use strict';
// Validation only. No Battle/BattleStream construction or policy execution.
const fs = require('node:fs');
const crypto = require('node:crypto');
const domain = require('./legal-domain.cjs');
const {loadEngine} = require('./engine.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
if (request.schema_version !== 'showdown-team-validation-only-v1' ||
    !Array.isArray(request.teams) || !request.teams.length || request.teams.length > 256) {
  throw new Error('bounded_team_validation_required');
}
domain.pinned(process.argv[2]);
const {TeamValidator} = loadEngine(process.argv[2]);
const validator = new TeamValidator(domain.FORMAT);
const canonical = x => Array.isArray(x) ? x.map(canonical) : x && typeof x === 'object' ?
  Object.fromEntries(Object.keys(x).sort().map(k => [k, canonical(x[k])])) : x;
const hash = x => crypto.createHash('sha256').update(JSON.stringify(canonical(x))).digest('hex');
const results = request.teams.map((team, index) => {
  if (!Array.isArray(team) || team.length !== 6) {
    return {index, valid: false, errors: ['full_six_source_roster_required']};
  }
  const copy = JSON.parse(JSON.stringify(team));
  let errors;
  try { errors = validator.validateTeam(copy) || []; }
  catch { errors = ['native_validator_rejected_malformed_set']; }
  return {index, valid: errors.length === 0, errors,
    input_team_SHA256: hash(team), validated_team_SHA256: hash(copy)};
});
process.stdout.write(JSON.stringify({schema_version: request.schema_version,
  engine_commit: domain.PIN, format_id: domain.FORMAT,
  input_SHA256: hash(request.teams), results}));
