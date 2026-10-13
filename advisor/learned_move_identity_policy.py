"""Same allocated policy for both token arms, using upstream MaskablePPO."""

import torch
from torch import nn
from advisor.learned_action_policy import ActionExtractor, ActionConditionedPolicy
from advisor.learned_move_identity import (
    CONTEXT, ACTION, BASE_ACTION, TOKEN_BITS, TOKEN_COUNT, EMBEDDING,
)


class OwnMoveTokenExtractor(ActionExtractor):
    def __init__(self):
        super().__init__(CONTEXT, ACTION)
        self.move_embedding = nn.Embedding(TOKEN_COUNT, EMBEDDING, padding_idx=0)
        self.scorer[0] = nn.Linear(64 + BASE_ACTION + EMBEDDING, 128)
        self.critic[0] = nn.Linear(CONTEXT + BASE_ACTION + EMBEDDING, 128)

    def _public_rows(self, features):
        context, raw = self._split(features)
        bits = raw[:, :, BASE_ACTION - 1:BASE_ACTION - 1 + TOKEN_BITS]
        if not torch.all((bits == 0) | (bits == 1)):
            raise ValueError("nonbinary_own_move_token")
        powers = 2 ** torch.arange(TOKEN_BITS, device=bits.device)
        tokens = (bits * powers).sum(-1).long()
        # Raw indices/bits are excluded from every Linear/MLP input.
        base = torch.cat((raw[:, :, :BASE_ACTION - 1], raw[:, :, -1:]), dim=-1)
        return context, base, self.move_embedding(tokens)

    def forward_actor(self, features):
        context, actions, embedding = self._public_rows(features)
        shared = self.context(context)[:, None, :].expand(-1, 35, -1)
        return self.scorer(torch.cat((shared, actions, embedding), dim=-1)).squeeze(-1)

    def forward_critic(self, features):
        context, actions, embedding = self._public_rows(features)
        mask = actions[:, :, -1:]
        pooled = (torch.cat((actions, embedding), dim=-1) * mask).sum(1)
        pooled = pooled / mask.sum(1).clamp(min=1)
        return self.critic(torch.cat((context, pooled), dim=1))


class OwnMoveTokenPolicy(ActionConditionedPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = OwnMoveTokenExtractor()


def transfer_v3_to_own_move(target, source):
    """Function-preserving weights, fresh Adam required; no optimizer restoration."""
    from advisor.learned_action_policy import TacticalActionConditionedPolicy
    if not isinstance(target, OwnMoveTokenPolicy) or not isinstance(source, TacticalActionConditionedPolicy):
        raise ValueError("v3_to_own_move_transfer_required")
    old, new = source.state_dict(), target.state_dict()
    columns = {
        "mlp_extractor.scorer.0.weight": 64 + BASE_ACTION,
        "mlp_extractor.critic.0.weight": CONTEXT + BASE_ACTION,
    }
    with torch.no_grad():
        for key, value in old.items():
            if key in columns:
                new[key].zero_()
                new[key][:, :columns[key]] = value.to(new[key].device)
            else:
                new[key].copy_(value)
        target.load_state_dict(new)
    target.optimizer = target.optimizer_class(
        target.parameters(), lr=target.optimizer.param_groups[0]["lr"], **target.optimizer_kwargs,
    )
