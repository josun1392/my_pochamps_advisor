"""Shared action scorer inside upstream MaskablePPO; no custom RL algorithm."""

import torch
from torch import nn
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from advisor.learned_action_encoder import CONTEXT, ACTION


class ActionExtractor(nn.Module):
    latent_dim_pi = 35
    latent_dim_vf = 64

    def __init__(self, context_dim=CONTEXT, action_dim=ACTION):
        super().__init__()
        self.context_dim, self.action_dim = context_dim, action_dim
        self.context = nn.Sequential(nn.Linear(context_dim, 64), nn.Tanh())
        self.scorer = nn.Sequential(
            nn.Linear(64 + action_dim, 128),
            nn.Tanh(),
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )
        self.critic = nn.Sequential(
            nn.Linear(context_dim + action_dim, 128),
            nn.Tanh(),
            nn.Linear(128, 64),
            nn.Tanh(),
        )

    def _split(self, features):
        return features[:, : self.context_dim], features[:, self.context_dim :].reshape(
            -1, 35, self.action_dim
        )

    def forward_actor(self, features):
        context, actions = self._split(features)
        shared = self.context(context)[:, None, :].expand(-1, 35, -1)
        return self.scorer(torch.cat((shared, actions), dim=-1)).squeeze(-1)

    def forward_critic(self, features):
        context, actions = self._split(features)
        mask = actions[:, :, -1:]
        pooled = (actions * mask).sum(1) / mask.sum(1).clamp(min=1)
        return self.critic(torch.cat((context, pooled), dim=1))

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class ActionConditionedPolicy(MaskableActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = ActionExtractor()

    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        # Native action rows share a scorer, preserving row permutation symmetry.
        self.action_net = nn.Identity()
        self.value_net = nn.Sequential(self.value_net, nn.Tanh())
        nn.init.normal_(self.mlp_extractor.scorer[-1].weight, std=0.01)
        nn.init.zeros_(self.mlp_extractor.scorer[-1].bias)
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs
        )


class TacticalActionConditionedPolicy(ActionConditionedPolicy):
    def _build_mlp_extractor(self):
        from advisor.learned_tactics_encoder import (
            CONTEXT as TACTICAL_CONTEXT,
            ACTION as TACTICAL_ACTION,
        )

        self.mlp_extractor = ActionExtractor(TACTICAL_CONTEXT, TACTICAL_ACTION)


def transfer_v2_weights(target, source):
    """Embed the frozen v2 function in v3; new public features initially have zero weight.

    This transfers weights only. A fresh optimizer is required for changed tensor
    shapes; it does not claim to restore the old optimizer's moments.
    """
    from advisor.learned_tactics_encoder import (
        CONTEXT as NEW_CONTEXT,
        ACTION as NEW_ACTION,
    )

    if (
        not isinstance(source, ActionConditionedPolicy)
        or isinstance(source, TacticalActionConditionedPolicy)
        or not isinstance(target, TacticalActionConditionedPolicy)
    ):
        raise ValueError("v2_to_v3_policy_transfer_required")
    old, new = source.state_dict(), target.state_dict()
    columns = {
        "mlp_extractor.context.0.weight": list(range(CONTEXT)),
        "mlp_extractor.scorer.0.weight": list(range(64 + ACTION - 1))
        + [64 + NEW_ACTION - 1],
        "mlp_extractor.critic.0.weight": list(range(CONTEXT))
        + [NEW_CONTEXT + i for i in range(ACTION - 1)]
        + [NEW_CONTEXT + NEW_ACTION - 1],
    }
    with torch.no_grad():
        for key, weights in old.items():
            if key in columns:
                new[key].zero_()
                new[key][:, columns[key]] = weights
            else:
                new[key].copy_(weights)
        target.load_state_dict(new)
