'use strict';
// Standalone offline entry point for the shared native conditional evaluator.
const fs = require('node:fs');
const path = require('node:path');
const {Battle} = require(path.join(process.argv[2], 'dist', 'sim'));
const {evaluateDamageRolls} = require('./damage-rolls.cjs');
const queries = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(queries.map(query => ({case_id: query.case_id,
  ...evaluateDamageRolls(Battle, query.checkpoint, query)}))));
