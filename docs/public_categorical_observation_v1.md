# Opt-in integrated public categorical observation

`showdown-public-categorical-observation-v1` adds categorical identities to the
unchanged V4 numerical/tactical features, including the V3 features and V4 public
history summaries. It does not change the simulator, legality, reward, PPO,
curriculum, action mask or guaranteed-first recommendation policy. This is a
representation implementation, not evidence of improved playing strength.

## Authority and identity contract

The engine is pinned to `942cda71d14bf0618bd57991708a2e2734b6daba`, format
`gen9championsbssregmc`. The input is the existing policy-visible observation
channel and explicitly requires `showdown-policy-state-v2`; old state semantics
are not silently converted. Native own requests are authorized player
information. Opponent identity values come only from the public projection.
No hidden teams, private opponent requests, checkpoints or future RNG are read.

The generated public vocabulary has 1,586 species/form display IDs, 939 move IDs
(938 native metadata entries plus the native `recharge` request), 215 initial or
transformation ability IDs and 166 item IDs. This display vocabulary is not the
M-C eligibility inventory: the legal domain remains 231 base species, 396 forms
and the native TeamValidator. Public vocabulary size does not authorize a set,
team, unavailable form, ability, item or move combination.

For each category, `0` means padding/no candidate, `1` means Unknown, `2` means
confirmed absence and `3+` means a unique sorted canonical native ID. Missing,
empty or unrevealed values do not become absence. Explicit `None` is accepted
only under the existing versioned public-state contract. The encoder does not
deduce an opponent ability or item from species, or complete its unrevealed set.
Indices use binary transport (species 11, ability 9, item 8, move 10 bits) and are
decoded exclusively into embeddings/gathers, never ordinal numerical features.

## Individual bindings and model

Twenty-four records are allocated: six own public records, six opponent apparent
records, six own preview entries and six opponent preview entries. Padding is
explicit. Public protocol keys deterministically order appearance records.
Each record binds the exact species/form, ability, item, up to sixteen known
move IDs, existing 63 numerical Pokémon features and seven presence/role flags.
Unrevealed move slots remain Unknown. Opponent move lists are public reveals,
not a claim that all entries are the current four-move set. Apparent identities
under possible Illusion carry an explicit unconfirmed flag. Preview entries
are not guessed to match appearance records by species or nickname numbering.

Shared embeddings have dimensions species 16, move 16, ability 12 and item 12.
A shared `366 -> 64 -> 24` entity MLP binds information within each record.
The actor and critic retain all 24 record latents individually in their context;
there is no entity mean pooling. Each action additionally gathers its own actor
record, exact own-request move and public candidate form (including native Mega
choices). The existing shared action scorer preserves row permutation behavior;
the critic pools legal candidate rows with the original mask.

The flat observation has 15,576 float32 values: context 6,546 and 35 action rows
of 258 values. There are 360,858 parameters, compared with V4's 152,514. The
serialized feature contract binds the category/source hashes, token mapping,
sentinels, record/flag order, dimensions, source state, base V4 fingerprint and
projection layout. Loading requires the exact contract, model hash, spaces and
categorical policy class. Changed catalog/encoder identities fail closed.

## Usage and compatibility

Use `make_encoder(full_domain_catalog, "showdown-public-categorical-observation-v1")`
and `PublicCategoricalPolicy` through the existing source autonomous trainer.
Set an experiment's `encoder_version` to this version. Fresh initialization is
supported. For a compatible V3/V4 source, set `transfer_model` and explicitly
`fresh_optimizer: true`: weights are transferred function-preservingly, with
zero initial projections for new features and **fresh Adam**. Old optimizer
moments are not restored across changed tensor shapes. Subsequent same-contract
checkpoints reload their model and optimizer normally. An incompatible source
catalog requires the existing separately verified conversion or fresh training;
this encoder does not silently convert old artifacts.

Original V1–V4 and move-ID ablation encoders/models remain separate and load
through their original contracts. The existing opt-in strategy evidence accepts
this new version after strict model loading; exact evidence, runtime truth and
default rankings stay unchanged. The previously packaged AI Trainer executable
has not been rebuilt and does not acquire this source version automatically.
No new production model is supplied or promoted.

Regenerate the public names with
`python -m scripts.build_showdown_public_categories`; verify with `--check`.
The builder only extracts already committed pinned public metadata, hashes its
sources and performs no engine download or current-battle access. No Metamon
architecture, code or pretrained OU model is imported.

## Explicit limitations and verification

Known IDs outside the vocabulary, more than six appearance records per side,
more than six preview entries, more than sixteen known moves per record,
ambiguous own aliases and unbound legal actions fail closed. There is no silent
truncation or hash substitution. Opponent aliases are preserved as appearance
records, not merged into asserted true identities.

The upstream structured public projection remains lossy: some transform,
volatile and suppression interactions are retained only as public protocol
events. Exact tokens describe projected public values, not a complete native
mechanics state or a guarantee that every last-revealed move/ability is current.
Existing history summaries, numerical move priors and learned latent vectors
are lossy; the discrete transport IDs themselves have no vocabulary collisions.
This model is feed-forward and does not learn bring-6/pick-3 selection.

Focused tests cover native vocabulary reproduction, exact IDs, per-record
relationships, Unknown/absence, Illusion appearance flags, hidden set/RNG
isolation, V3/V4 transfer, masks/permutations, shared embedding gradients,
strict save/load, opt-in strategy rollback and two-worker Windows spawn parity.
A 32-transition native PPO integration smoke verifies actual parameter updates
and optimizer reload, not strategic superiority. No large learning experiment
or broad win-rate evaluation is part of this change.
