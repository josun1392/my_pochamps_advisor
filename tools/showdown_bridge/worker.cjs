'use strict';
// One local engine process, sequential JSONL requests. No battle server.
const readline = require('node:readline');
const path = require('node:path');
const {run} = require('./bridge.cjs');
const engine = require(path.join(process.argv[2], 'dist', 'sim'));
const lines = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
lines.on('line', line => {
  let requestId = null;
  try {
    if (Buffer.byteLength(line) > 8 * 1024 * 1024) throw new Error();
    const envelope = JSON.parse(line);
    requestId = envelope.request_id;
    if (!Number.isSafeInteger(requestId) || requestId < 1) throw new Error();
    process.stdout.write(JSON.stringify({request_id: requestId, response: run(envelope.request, engine)}) + '\n');
  } catch {
    process.stdout.write(JSON.stringify({request_id: requestId, response: {status: 'error', reason: 'worker_request_failed'}}) + '\n');
  }
});
