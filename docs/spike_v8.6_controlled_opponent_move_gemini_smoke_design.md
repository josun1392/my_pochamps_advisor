# v8.6 Controlled Opponent Move Gemini Smoke Design

## Purpose

v8.6 defines the controlled Gemini smoke criteria for the new `opponent_move_context` path.

The smoke is intended to verify, with at most one future actual Gemini call, that Gemini treats opponent move context as limited explicitly known or visible data rather than inferred battle truth.

This design does not execute a Gemini call.

## Smoke Purpose

The controlled smoke should confirm that Gemini:

- treats `opponent_move_context` as explicitly known or visible data only
- does not treat known opponent moves as selected this turn unless `selected_opponent_move` is explicit
- does not treat candidate moves as confirmed moves
- does not treat candidate moves as selected moves
- does not infer the opponent's selected move when `selected_opponent_move` is unknown
- does not infer hidden movesets or opponent sets
- does not infer EV/IV/nature, hidden item, weather, terrain, or boosts
- does not claim RNG resolution, item consumption, post-turn HP, or full turn resolution

## Pre-Check

Before any actual provider call, the smoke harness must verify:

- `opponent_move_context` is present in the payload
- opponent move prompt guard is present
- known move data is represented as known data, not selected move data
- each candidate move has `confirmed=False`
- each candidate move has `selected=False`
- `selected_opponent_move` is `{"status": "unknown"}` for this fixture
- prompt says candidate moves are not confirmed moves
- prompt says candidate moves are not selected moves
- prompt says known moves are not necessarily selected this turn
- prompt forbids hidden moveset inference
- prompt forbids opponent set inference
- prompt forbids selected move inference unless explicit
- prompt forbids EV/IV/nature, hidden item, weather, terrain, and boost inference
- prompt forbids RNG, item consumption, and post-turn HP inference
- provider call count before smoke is `0`

If any pre-check fails:

- do not execute the actual Gemini call
- classify the result as `BLOCKED`
- record the failed pre-check without including secrets, credentials, billing details, or raw token logs

## Actual Call Limit

The future v8.7 smoke is limited to:

- actual Gemini call count: maximum `1`
- retry count: `0`
- no automatic retry
- no repeated call against the same fixture
- no additional call after a failure, block, timeout, or exception
- no Vertex AI call

## Stop Conditions

Stop immediately and make no further provider calls if any of these occur:

- HTTP 429
- `RESOURCE_EXHAUSTED`
- `API_KEY_INVALID`
- auth or credential error
- billing, prepay, or credit-related error
- provider routing error
- timeout after one attempt
- unexpected exception before the call
- unexpected exception after the call

Provider, auth, billing, quota, timeout, or pre-call failures are classified as `BLOCKED`.

If Gemini returns a response but the content makes unsafe confirmed, selected, hidden-inference, or resolved-outcome claims, classify the result as `FAIL`.

## Result Classification

`PASS`:

- response satisfies all safety criteria

`PARTIAL`:

- response is mostly safe but wording is ambiguous or suggests prompt polish is needed

`FAIL`:

- response makes unsafe confirmed, selected, hidden-inference, or resolved-outcome claims

`BLOCKED`:

- provider, auth, billing, quota, timeout, pre-check, or unexpected exception prevents response evaluation

## PASS Criteria

PASS requires all of the following:

- `opponent_move_context` is treated as explicitly known or visible data
- known move is not treated as selected move
- candidate move is not treated as confirmed move
- candidate move is not treated as selected move
- selected opponent move is not inferred while `selected_opponent_move` is unknown
- no hidden moveset inference
- no opponent set inference
- no EV/IV/nature inference
- no hidden item inference
- no weather, terrain, or boost inference
- no RNG resolved claim
- no item consumption claim
- no post-turn HP claim
- no full turn resolution claim

Allowed wording includes:

- known move data indicates the move is available or known
- selected opponent move is unknown
- candidate move should be treated as unconfirmed
- candidate move may be relevant only as possible context, not confirmed

## PARTIAL Criteria

PARTIAL applies when:

- the response is overall safe but wording is ambiguous
- known move is phrased in a way that could read as selected, but the response includes a clear caveat
- candidate move is phrased somewhat strongly, but the response still says it is not confirmed or selected
- hidden inference is avoided, but guard wording appears to need polish

## FAIL Criteria

FAIL applies if the response body contains claims equivalent to:

- opponent will use a specific move
- opponent likely uses a specific move
- candidate move is confirmed
- candidate move is selected
- known move is selected this turn without explicit `selected_opponent_move`
- hidden moveset assertion
- opponent set inference
- selected opponent move inference without explicit data
- EV/IV/nature inference
- hidden item inference
- weather, terrain, or boost inference
- RNG resolved claim
- item consumption claim
- post-turn HP claim
- full turn resolution claim

The check should judge the Gemini response body. Prompt guard text such as "Do not infer opponent will use X" must not be misclassified as a response failure.

## Known / Candidate / Selected Wording Policy

Known move data means only that the move is explicitly known or visible in the supplied context. It is not selected move data unless `selected_opponent_move.status` is `explicit`.

Candidate moves are possible context only. They must remain:

- unconfirmed
- unselected
- not promoted to known move data
- not treated as the opponent's actual move choice

When `selected_opponent_move.status` is `unknown`, the response must preserve that uncertainty.

## Hidden Inference Policy

The smoke must treat these as unsupported boundaries, not missing facts to fill in:

- hidden moveset
- opponent set
- selected opponent move
- EV/IV/nature
- hidden item
- weather, terrain, boosts
- RNG result
- item consumption
- post-turn HP
- full turn resolution

## Recording Policy

Record only a safe summary:

- do not paste the full raw response
- include at most a short excerpt or paraphrase needed to justify PASS/PARTIAL/FAIL
- record token/cost information only as safe summary fields if available
- do not record API keys, credentials, billing details, or token log raw content
- do not commit or reset `logs/token_usage.jsonl`

## Not Implemented

v8.6 does not add:

- actual Gemini call
- Vertex AI call
- network/provider call
- UI/source extraction
- UI checkbox behavior change
- full Turn Engine behavior
- resolved turn order
- opponent set inference
- hidden moveset inference
- selected opponent move inference
- species/common-set/meta-based move generation
- EV/IV/nature inference
- hidden item inference
- weather/terrain/boost inference
- RNG resolution
- item consumption
- post-turn HP update

## Next Recommendation

Recommended next:

- v8.7 Controlled Gemini Smoke

Conditions:

- T1 approval is required.
- Execute at most one actual Gemini call.
- Retry count must remain `0`.
- Stop on any pre-check, provider, auth, billing, quota, routing, timeout, or unexpected exception issue.

Alternatives:

- v8.7 Prompt Wording Polish, if guard wording needs strengthening before a provider call
- v8.7 Opponent Move UI/Source Integration Design, if actual smoke is deferred
