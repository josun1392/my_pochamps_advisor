"""Shared public categorical embeddings inside the existing MaskablePPO policy.

Each record binds its species, moves, item, ability and combat state before
projection. Individual record latents stay separate in actor AND critic context;
candidate rows gather their own actor record without guessing preview links.
"""
import torch
from torch import nn

from advisor.learned_action_policy import ActionExtractor, ActionConditionedPolicy
from advisor.learned_public_categories import (
    BASE_CONTEXT, BASE_ACTION, CONTEXT, ACTION, BITS, EMBEDDINGS, ENTITY,
    ENTITY_NUMERIC, ENTITY_LATENT, ENTITIES, KNOWN_MOVES, REFERENCE_BITS,
)

LATENT_CONTEXT = BASE_CONTEXT + ENTITIES * ENTITY_LATENT
LATENT_ACTION = BASE_ACTION + ENTITY_LATENT + EMBEDDINGS["moves"] + EMBEDDINGS["species"]


def decode_bits(bits):
    if not torch.all((bits == 0) | (bits == 1)):
        raise ValueError("nonbinary_public_categorical_transport")
    powers = 2 ** torch.arange(bits.shape[-1], device=bits.device)
    return (bits * powers).sum(-1).long()


class PublicCategoricalExtractor(ActionExtractor):
    def __init__(self):
        super().__init__(CONTEXT, ACTION)
        self.embeddings = nn.ModuleDict({
            "category_" + kind: nn.Embedding(2 ** BITS[kind], dimension, padding_idx=0)
            for kind, dimension in EMBEDDINGS.items()
        })
        self.entity_encoder = nn.Sequential(
            nn.Linear(ENTITY_NUMERIC + sum(EMBEDDINGS[k] for k in ("species", "abilities", "items"))
                      + KNOWN_MOVES * EMBEDDINGS["moves"], 64), nn.Tanh(),
            nn.Linear(64, ENTITY_LATENT), nn.Tanh(),
        )
        self.context[0] = nn.Linear(LATENT_CONTEXT, 64)
        self.scorer[0] = nn.Linear(64 + LATENT_ACTION, 128)
        self.critic[0] = nn.Linear(LATENT_CONTEXT + LATENT_ACTION, 128)

    def _public_rows(self, features):
        context, raw = self._split(features)
        entities = context[:, BASE_CONTEXT:].reshape(-1, ENTITIES, ENTITY)
        values = [entities[:, :, :ENTITY_NUMERIC]]
        start = ENTITY_NUMERIC
        for kind in ("species", "abilities", "items"):
            width = BITS[kind]
            values.append(self.embeddings["category_" + kind](decode_bits(entities[:, :, start:start + width])))
            start += width
        moves = entities[:, :, start:].reshape(-1, ENTITIES, KNOWN_MOVES, BITS["moves"])
        values.append(self.embeddings["category_moves"](decode_bits(moves)).flatten(2))
        bound = self.entity_encoder(torch.cat(values, dim=-1)) * entities[:, :, 63:64]
        # Individual bindings remain separate; there is no entity mean pooling.
        public_context = torch.cat((context[:, :BASE_CONTEXT], bound.flatten(1)), dim=-1)
        start = BASE_ACTION - 1
        reference = decode_bits(raw[:, :, start:start + REFERENCE_BITS])
        if (reference > ENTITIES).any():
            raise ValueError("invalid_public_entity_reference")
        start += REFERENCE_BITS
        move = decode_bits(raw[:, :, start:start + BITS["moves"]])
        start += BITS["moves"]
        form = decode_bits(raw[:, :, start:start + BITS["species"]])
        bank = torch.cat((bound.new_zeros((len(bound), 1, ENTITY_LATENT)), bound), dim=1)
        candidate = bank.gather(1, reference[:, :, None].expand(-1, -1, ENTITY_LATENT))
        # Bit patterns and reference ordinals are excluded from every linear layer.
        numeric = torch.cat((raw[:, :, :BASE_ACTION - 1], raw[:, :, -1:]), dim=-1)
        actions = torch.cat((numeric, candidate, self.embeddings["category_moves"](move),
                             self.embeddings["category_species"](form)), dim=-1)
        return public_context, actions, numeric[:, :, -1:]

    def forward_actor(self, features):
        context, actions, _ = self._public_rows(features)
        shared = self.context(context)[:, None, :].expand(-1, 35, -1)
        return self.scorer(torch.cat((shared, actions), dim=-1)).squeeze(-1)

    def forward_critic(self, features):
        context, actions, mask = self._public_rows(features)
        pooled = (actions * mask).sum(1) / mask.sum(1).clamp(min=1)
        return self.critic(torch.cat((context, pooled), dim=1))


class PublicCategoricalPolicy(ActionConditionedPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = PublicCategoricalExtractor()


def transfer_public_categorical_weights(target, source):
    """V3/V4 function-preserving weights only; changed shapes require fresh Adam."""
    from advisor.learned_action_policy import TacticalActionConditionedPolicy, PublicInteractionPolicy
    from advisor.learned_tactics_encoder import CONTEXT as V3_CONTEXT, ACTION as V3_ACTION
    if not isinstance(target, PublicCategoricalPolicy):
        raise ValueError("public_categorical_target_required")
    if isinstance(source, PublicInteractionPolicy):
        old_context, old_action = BASE_CONTEXT, BASE_ACTION
    elif isinstance(source, TacticalActionConditionedPolicy):
        old_context, old_action = V3_CONTEXT, V3_ACTION
    else:
        raise ValueError("v3_or_v4_public_transfer_source_required")
    columns = {
        "mlp_extractor.context.0.weight": list(range(old_context)),
        "mlp_extractor.scorer.0.weight": list(range(64 + old_action - 1)) + [64 + BASE_ACTION - 1],
        "mlp_extractor.critic.0.weight": list(range(old_context))
            + [LATENT_CONTEXT + i for i in range(old_action - 1)] + [LATENT_CONTEXT + BASE_ACTION - 1],
    }
    old, new = source.state_dict(), target.state_dict()
    with torch.no_grad():
        for key, value in old.items():
            if key in columns:
                new[key].zero_()
                new[key][:, columns[key]] = value.to(new[key].device)
            else:
                new[key].copy_(value)
        target.load_state_dict(new)
    target.optimizer = target.optimizer_class(
        target.parameters(), lr=target.optimizer.param_groups[0]["lr"], **target.optimizer_kwargs,
    )
