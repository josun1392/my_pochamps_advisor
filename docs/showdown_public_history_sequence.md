# Bounded public history sequence V1

The original categorical V4 already includes historical information: revealed
moves/items/abilities, public move order samples, recent healing/setup and failure
summaries, Trick Room, effects and observed current typing. These are preserved.
This experiment adds ordered events rather than claiming V4 is memoryless.

Two opt-in contracts share `PublicHistorySequencePolicy` and identical shapes:

- `showdown-public-categorical-observation-v4-history-sequence-v1`
- `showdown-public-categorical-observation-v4-history-sequence-ablated-v1`

The original 15,692 values are an unchanged prefix. Added transport contains
64 chronological event rows of 88 values and four metadata flags, giving 21,328
inputs. The supplied window covers the current and previous five **public**
turns, including any delivered events in the current decision phase. If over64
relevant events occur, retain the newest64 and explicitly flag truncation.
Unrecognized event/detail payloads have explicit unsupported markers; no Dex
effect interpreter or hidden state reconstruction is attempted. Known canonical
move/species/ability/item IDs outside the supported categorical vocabulary fail
closed. Category tokens retain their historical meanings and binary transport.

Only `public_history` and the player's role supply the new path. Public health
payloads contribute a displayed fraction, never exact opponent HP or a new own
maximum-HP feature. Damage/heal events bind the recipient; a source actor is
included only when announced by `[of]`. Move events bind their actor and public
target. Side conditions may identify a side without claiming an individual.

Identity references are window-local public **entry appearances**, not private
roster slots. Each entry gets a new appearance; repeated references during that
entry remain bound. A public Illusion replacement explicitly links old/new
appearances without retroactively editing their historical species or identities.
Unknown actor/source/species is preserved; padding, unknown and non-entity turn
markers remain distinct. This does not establish true identity across entries.
References follow public event order with explicit own/opponent role flags; no
permutation-invariant roster alignment or complete effect semantics is claimed.
The last `start` is an episode boundary. Missing prefixes remain explicitly
unknown, and the encoder keeps no neural or episode hidden state.

Existing categorical embeddings are reused for event identities. Lightweight
event/appearance/detail embeddings and a16-unit GRU summarize the supplied
window. The GRU starts from zero on **every forward call**, including shuffled
PPO minibatches. No recurrent PPO, persistent hidden state or sequence rollout
buffer is introduced. Actor and critic use the same authorized window. The
policy has395,770 parameters (original383,130). Control's entire new input and
output contribution are gated to zero, including metadata; GRU biases cannot
create a learned constant bypass of the ablation.

`transfer_history_sequence_weights` copies every compatible original V4 tensor
and initializes the new actor/critic context columns to zero. The new GRU and
embeddings use fixed initialization seed91001 in a forked RNG scope, giving the
same complete initial tensors across both arms and both continuation seeds.
Sampling seeds remain independent. Changed shapes require fresh Adam in all
arms. Same-contract checkpoint loading restores Adam and the existing beta.001
regularizer through the maintained loader. Old V4/HP checkpoints remain intact.

The study uses two continuation seeds, each65,536 trained transitions per arm,
the existing256-team V8 subset, native35-action masks and fixed opponent mixture.
New native-valid cases are frozen before training and evaluated on both actual
seats. Report all fixed endpoints, paired case uncertainty conditional on the
two trained models, seed variability separately, and the limits of selected
history-sensitive fixtures. No live policy promotion is part of this feature.
