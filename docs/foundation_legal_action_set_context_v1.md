# Foundation legal action set context v1

`showdown-foundation-legal-action-set-context-v1` is an **opt-in policy
architecture contract**, not a new encoder, critic, PPO objective or trained
model. Original Foundation checkpoints and the V5-v3 observation fingerprint
retain their original meaning.

## Architecture

For original public context `c`, candidate rows `x_i`, and the transported own
native legal mask `m_i`:

```
g   = existing_context(c)                         # 64
h_i = existing_scorer_without_final([g, x_i])     # 64, joint identity/state/PP
u   = sum(where(m_i, h_i, 0)) / sum(m_i)
g'  = g + legal_set_residual(u)                   # Linear(64, 64), zero init
z_i = existing_scorer([g', x_i])
```

All scorer weights are reused, not duplicated. There is no independent
pairwise scorer or attention head. Pooling supplements, rather than replaces,
individual candidate representations. It pools **joint nonlinear** features;
separate averages of identity and PP would discard their association.

The extension adds 4,160 parameters: **679,099 total**, with the same 28,822
input dimensions and 35 actions. The original critic and prediction heads are
unchanged. The critic never receives this residual. Legal masks come from the
same own-player transport; opponent private requests/masks and future labels
are not inputs. Finite illegal/padding candidate rows are excluded by `where`.
Malformed nonfinite features and empty/nonbinary masks fail closed.

Every policy actor entry point checks an explicit mask against its transported
native mask. If omitted, it uses that transport, not an all-actions fallback.
Mask-only tensor experiments must update both representations consistently.

## Initialization, optimizer, and persistence

`extend_foundation_legal_set_context(source)` accepts only the original CPU
`FoundationCombatPPO` / `FoundationCombatPolicy`, standard single-group Adam
with verified parameter order, and the original observation/action dimensions.
It makes an independent in-memory copy, strictly copies every old parameter and
buffer, and zeroes the new residual **after SB3 orthogonal initialization**.
The zero path remains in the autograd graph; it is not bypassed based on values.

Old Adam tensors and group settings are copied by **parameter name**, never by
assuming that old integer optimizer IDs retain their meaning. The new optimizer
uses natural new parameter registration order so a later SB3 save/load matches
the same names. Only the two new parameters have empty Adam state. There is no
optimizer step, original checkpoint write, or fresh initialization of old Adam.
This is an architecture extension with a fresh rollout boundary, not a byte-exact
uninterrupted native/RNG resume.

`save_checkpoint` records the additional `actor_set_context` contract.
`LearnedPolicy` validates the actual policy class and contract, including
rejecting an extension whose metadata lost the marker. Historical Foundation
models keep loading as the historical policy. Unsupported combinations with
parent-KL or temperature-study metadata fail closed. Original observation and
base Foundation metadata remain a base binding; the additional policy contract
identifies the architectural change explicitly.

At the `7fb0ba7` acceptance boundary the source trainer rejected training with
this marker alone. The separately authorized [matched PPO study](foundation_legal_set_matched_PPO_v1.md)
adds a strict `legal_set_training` opt-in; the historical architecture marker
and its meaning remain unchanged. A marker alone never enables PPO training.

## Offline acceptance

Focused tests use existing public training observations and the trusted frozen
parent, configured by `POKEADVICE_LEGAL_SET_PARENT`,
`POKEADVICE_LEGAL_SET_CAPTURE`, and `POKEADVICE_LEGAL_SET_EVIDENCE`.
They never create native fixtures or call an optimizer/PPO update.

- Zero residual: compare raw logits, masked probabilities/log-probabilities,
  argmax and critic with the original; verify bytes where possible.
- Diagnostic nonzero residual: fixed `0.05 * I` weight, no fitting; changing
  another legal candidate C's owned PP must be able to change an A/B logit gap.
  This does not assert an optimal action or battle-strength improvement.
- Valid finite gradients reach new residual weights/bias at zero initialization;
  the critic has no gradient path to them. No optimizer step is taken.
- All aligned action blocks permute together; legal probabilities equivary,
  the critic is invariant up to normal FP32 reduction error.
- Illegal-row noise, candidate removal, single legal choice, explicit-mask
  mismatch, unknown/privileged input boundaries and strict save/load are checked.
- Old parameters and every named old Adam state remain identical after transfer
  and after loading an independent validation checkpoint.

The previous **50/867 full move-slot reversal sensitivity** is a separate
inherited limitation of ordered own-move context. This extension does not sort
move sets, rosters, leads, or reserves, and does not alter Illusion party order.
At zero initialization it must reproduce that same inherited behavior.

## Retained contract evidence (2026-10-25)

The frozen Foundation parent SHA-256 is
`9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf`.
On 1,024 retained public training observations, zero initialization preserves
logits, masked probabilities/log-probabilities, deterministic actions and values
byte for byte. Full move-request reversal retains the same 50/867 changed cases.
With the fixed nonzero diagnostic fixture, all 128 C-PP probes change the A/B
gap: maximum absolute changes range from 0.00358 to 0.00817 across the four
attack-versus-switch/recovery/defense/setup groups. These are logit gaps, not
battle returns or action-quality labels. Residual weight/bias gradient L2 norms
are 7.12953/1.28057 on the recorded zero-path probe; the critic path is absent.

On one CPU thread, a 32-observation actor/value batch measured median 13.08 ms
before and 19.05 ms after the extension. This short frozen neural measurement
does not establish native training throughput. Independent validation copies,
input hashes and detailed measurements are retained outside Git under
`foundation-legal-set-zero-residual-v1-20261025`.

## Limits and reuse

The supplemental 64-dimensional pool is not injective for all action sets and
does not establish correct long-horizon action quality. A second scorer pass
adds neural inference cost; measure it before any learning expansion. No
competitive-strength, promotion or Best-Response claim follows from these tests.

The set aggregation idea is compatible with [Deep Sets](https://arxiv.org/abs/1703.06114).
Existing [MaskablePPO](https://github.com/Stable-Baselines-Team/stable-baselines3-contrib/tree/v2.7.1)
and local Foundation owners supply the policy/distribution/learning contracts.
No external architecture code or new framework is imported.
