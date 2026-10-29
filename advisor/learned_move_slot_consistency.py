"""Opt-in own move-presentation consistency, never synthetic PPO samples.

Only complete, distinct, exactly bound four-move requests are eligible. The
transformation is a presentation renaming: execution always maps back to the
original native action. Party order, public history and opponent data stay put.
"""
import numpy as np
import torch

from advisor.learned_combat_foundation import FoundationCombatPPO
from advisor.learned_combat_v5 import OLD_DIM, HP_EXTRA, HISTORY_EXTRA, TACTICAL
from advisor.learned_combat_v5_strategic import DIMENSION, PREFIX, REF_WIDTH
from advisor.learned_public_categories import (
    BASE_CONTEXT, BASE_ACTION, BITS, ENTITY, ENTITY_NUMERIC, REFERENCE_BITS, ACTION,
)
from advisor.learned_strategic_public import CONTEXT

VERSION = "showdown-foundation-own-move-slot-consistency-v1"
PERMUTATION = list(range(35))
for _start in (6, 10, 27, 31):
    PERMUTATION[_start:_start + 4] = reversed(PERMUTATION[_start:_start + 4])


def consistency_contract():
    return {"schema_version": VERSION, "coefficient": .01,
        "loss": "mean_eligible_Jensen_Shannon_both_branches_differentiable_natural_log",
        "permutation": "reverse_four_own_active_moves_and_all_aligned_candidate_blocks",
        "eligibility": "four_distinct_known_request_moves_equal_bound_own_record_no_extra_known_moves_native_move_choice",
        "PPO": "original_observations_actions_oldlogp_advantage_returns_unchanged_T1",
        "architecture": "unchanged_FoundationCombatPolicy_no_new_parameters",
        "optimizer": "all_original_named_Adam_states_restored",
        "budget": 65536, "rollout": 512,
        "inference": "original_native_view_no_permutation_no_loss"}


def validate_contract(value):
    if value != consistency_contract():
        raise ValueError("move_slot_consistency_contract_mismatch")
    return value


def _decode(bits):
    if not torch.all((bits == 0) | (bits == 1)):
        raise ValueError("move_slot_nonbinary_identity")
    return (bits * 2 ** torch.arange(bits.shape[-1], device=bits.device)).sum(-1).long()


def transform(features, action_masks=None):
    """Return transformed copy, new-slot->old-action map and eligibility.

    Never sorts moves/rosters. Ineligible rows are exact copies. Uses only the
    existing public tensor, including the authenticated own request transport.
    """
    if features.ndim != 2 or features.shape[1] != DIMENSION or not torch.isfinite(features).all():
        raise ValueError("move_slot_feature_contract")
    rows = features[:, CONTEXT:OLD_DIM].reshape(-1, 35, ACTION)
    native = rows[:, :, -1]
    if not torch.all((native == 0) | (native == 1)) or not native.bool().any(1).all():
        raise ValueError("move_slot_native_mask_required")
    if action_masks is not None:
        explicit = torch.as_tensor(action_masks, device=features.device)
        if explicit.shape != native.shape or not torch.equal(explicit, native):
            raise ValueError("move_slot_explicit_mask_mismatch")
    start = BASE_ACTION - 1
    refs = _decode(rows[:, 6:10, start:start + REFERENCE_BITS])
    offset = start + REFERENCE_BITS
    ids = _decode(rows[:, 6:10, offset:offset + BITS['moves']])
    eligible = (refs == refs[:, :1]).all(1) & (refs[:, 0] >= 1) & (refs[:, 0] <= 6)
    eligible &= (ids > 2).all(1) & (ids.sort(1).values.diff(dim=1) != 0).all(1)
    eligible &= native[:, 6:10].bool().any(1) & ~native[:, 14:26].bool().any(1)
    record = refs[:, 0].clamp(1, 6) - 1
    entities = features[:, BASE_CONTEXT:BASE_CONTEXT + 24 * ENTITY].reshape(-1, 24, ENTITY)
    batch = torch.arange(len(features), device=features.device)
    own = entities[batch, record]
    move_start = ENTITY_NUMERIC + BITS['species'] + BITS['abilities'] + BITS['items']
    moves = _decode(own[:, move_start:].reshape(-1, 16, BITS['moves']))
    # Populated native own records fill unused known-move capacity with Unknown
    # (token 1), whereas unpopulated transport may use padding (0). Preserve both.
    eligible &= (moves[:, :4] == ids).all(1) & (moves[:, 4:] <= 1).all(1)
    eligible &= (own[:, 63] == 1) & (own[:, 64] == 1) & (own[:, 67] == 1)
    for group in (10, 27, 31):
        eligible &= (rows[:, group:group + 4, start:start + REFERENCE_BITS] == rows[:, 6:10, start:start + REFERENCE_BITS]).all((1, 2))
        eligible &= (rows[:, group:group + 4, offset:offset + BITS['moves']] == rows[:, 6:10, offset:offset + BITS['moves']]).all((1, 2))
    result = features.clone()
    perm = torch.tensor(PERMUTATION, device=features.device)
    for begin, width in ((CONTEXT, ACTION),
            (OLD_DIM + HP_EXTRA + HISTORY_EXTRA, TACTICAL), (PREFIX, REF_WIDTH)):
        block = features[:, begin:begin + 35 * width].reshape(-1, 35, width)
        result[:, begin:begin + 35 * width] = torch.where(
            eligible[:, None, None], block[:, perm], block).flatten(1)
    transformed_entities = result[:, BASE_CONTEXT:BASE_CONTEXT + 24 * ENTITY].reshape(-1, 24, ENTITY)
    keep = eligible.nonzero().flatten()
    if len(keep):
        original = own[keep, move_start:move_start + 4 * BITS['moves']].reshape(-1, 4, BITS['moves'])
        transformed_entities[keep, record[keep], move_start:move_start + 4 * BITS['moves']] = original.flip(1).flatten(1)
    return result, perm, eligible


def consistency_loss(policy, observations, action_masks):
    transformed, perm, eligible = transform(observations, action_masks)
    if not eligible.any():
        return observations.sum() * 0, {"eligible": 0, "rows": len(observations)}
    x, y = observations[eligible], transformed[eligible]
    mask = torch.as_tensor(action_masks, device=x.device).bool()[eligible]
    # Raw forwards do not overwrite policy.action_dist used by enclosing PPO/KL.
    a = policy.action_net(policy.mlp_extractor.forward_actor(x)).masked_fill(~mask, -torch.inf)
    b = policy.action_net(policy.mlp_extractor.forward_actor(y))[:, perm].masked_fill(~mask, -torch.inf)
    p, q = a.softmax(1), b.softmax(1)
    mixture = (p + q) / 2
    def kl(v):
        return (v * (v.clamp_min(1e-30).log() - mixture.clamp_min(1e-30).log())).sum(1)
    js = (kl(p) + kl(q)) / 2
    if not torch.isfinite(js).all() or (js < -1e-6).any():
        raise ValueError("move_slot_nonfinite_or_negative_JS")
    js = js.clamp_min(0)  # Only suppress sub-ulp negative roundoff of a divergence.
    entropy = -(p * p.clamp_min(1e-30).log()).sum(1)
    count = mask.sum(1)
    uniform = mask.to(p) / count[:, None]
    return js.mean(), {"eligible": int(eligible.sum()), "rows": len(observations),
        "JS": float(js.detach().mean()), "probability_L1": float((p-q).detach().abs().sum(1).mean()),
        "entropy": float(entropy.detach().mean()), "max_probability": float(p.detach().max(1).values.mean()),
        "uniform_L1": float((p-uniform).detach().abs().sum(1).mean()),
        "relative_entropy": float(torch.where(count>1, entropy/count.float().log().clamp_min(1e-30), 0).detach().mean()),
        "semantic_argmax_changes": int((p.argmax(1) != q.argmax(1)).sum())}


class MoveSlotFoundationPPO(FoundationCombatPPO):
    def __init__(self, *args, move_slot_consistency=None, **kwargs):
        self.move_slot_consistency = validate_contract(move_slot_consistency) if move_slot_consistency is not None else None
        self.move_slot_trained = 0
        super().__init__(*args, **kwargs)

    def train(self):
        contract = validate_contract(self.move_slot_consistency)
        if self.n_steps * self.n_envs != 512 or not self.ent_coef > 0 or self.move_slot_trained >= contract['budget']:
            raise ValueError("move_slot_training_budget_or_rollout")
        original = self.policy.evaluate_actions
        had = 'evaluate_actions' in self.policy.__dict__
        previous = self.policy.__dict__.get('evaluate_actions')
        records, raw_entropy = [], []
        def evaluate(obs, actions, action_masks=None):
            value, logp, entropy = original(obs, actions, action_masks=action_masks)
            loss, metrics = consistency_loss(self.policy, obs, action_masks)
            records.append(metrics);raw_entropy.append(float(entropy.detach().mean()))
            return value, logp, entropy - (contract['coefficient'] / self.ent_coef) * loss
        self.policy.evaluate_actions = evaluate
        try:
            super().train()
        finally:
            if had:
                self.policy.evaluate_actions = previous
            else:
                del self.policy.evaluate_actions
        self.move_slot_trained += self.n_steps * self.n_envs
        for key in ('JS', 'probability_L1', 'eligible', 'semantic_argmax_changes',
                'entropy', 'max_probability', 'uniform_L1', 'relative_entropy'):
            self.logger.record('train/slot_' + key, float(np.mean([r.get(key, 0) for r in records])))
        self.logger.record('train/slot_coefficient', contract['coefficient'])
        self.logger.record('train/slot_true_action_entropy', float(np.mean(raw_entropy)))


def validate_loaded(model, metadata):
    value = getattr(model, 'move_slot_consistency', None)
    if value != metadata.get('move_slot_consistency'):
        raise ValueError('move_slot_checkpoint_metadata_mismatch')
    if value is not None:
        validate_contract(value)
        if not isinstance(model, MoveSlotFoundationPPO) or model.move_slot_trained != metadata.get('move_slot_trained'):
            raise ValueError('move_slot_checkpoint_algorithm_or_progress_mismatch')
