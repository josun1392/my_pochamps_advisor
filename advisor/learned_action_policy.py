"""Shared action scorer inside upstream MaskablePPO; no custom RL algorithm."""

import torch
from torch import nn
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from advisor.learned_action_encoder import CONTEXT, ACTION


class ActionExtractor(nn.Module):
    latent_dim_pi = 35
    latent_dim_vf = 64

    def __init__(self):
        super().__init__()
        self.context = nn.Sequential(nn.Linear(CONTEXT, 64), nn.Tanh())
        self.scorer = nn.Sequential(
            nn.Linear(64 + ACTION, 128),
            nn.Tanh(),
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )
        self.critic = nn.Sequential(
            nn.Linear(CONTEXT + ACTION, 128), nn.Tanh(), nn.Linear(128, 64), nn.Tanh()
        )

    def _split(self, features):
        return features[:, :CONTEXT], features[:, CONTEXT:].reshape(-1, 35, ACTION)

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
