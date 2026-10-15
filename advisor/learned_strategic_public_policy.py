"""Categorical V4 policy: original bindings plus two ordered public active states."""
import torch
from torch import nn
from advisor.learned_public_categories import CONTEXT as OLD_CONTEXT
from advisor.learned_public_categories_policy import (
    PublicCategoricalExtractor, PublicCategoricalPolicy, LATENT_CONTEXT, LATENT_ACTION,
)
from advisor.learned_strategic_public import CONTEXT, EXTRA, VERSION


class StrategicPublicCategoricalExtractor(PublicCategoricalExtractor):
    def __init__(self):
        super().__init__()
        self.context[0] = nn.Linear(LATENT_CONTEXT + EXTRA, 64)
        self.critic[0] = nn.Linear(LATENT_CONTEXT + EXTRA + LATENT_ACTION, 128)

    def _public_rows(self, features):
        # Preserve every original entity/candidate binding and binary decoder.
        extra = features[:, OLD_CONTEXT:CONTEXT]
        if not torch.all((extra == 0) | (extra == 1)):
            raise ValueError("nonbinary_strategic_public_transport")
        legacy = torch.cat((features[:, :OLD_CONTEXT], features[:, CONTEXT:]), dim=1)
        context, actions, mask = super()._public_rows(legacy)
        return torch.cat((context, extra), dim=1), actions, mask


class StrategicPublicCategoricalPolicy(PublicCategoricalPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = StrategicPublicCategoricalExtractor()


def transfer_strategic_public_weights(target, source, target_encoder, source_encoder):
    """Native V3->V4 function preservation, explicitly fresh Adam.

    V3's 'snow' input column 8 is never set by pinned native Snowscape. Its
    incompatible/dead weights are zeroed when that column is corrected in V4.
    All other learned weights are copied; all added input columns start at zero.
    This is NOT optimizer/mid-rollout continuation from the changed-shape model.
    """
    if (type(source) is not PublicCategoricalPolicy or type(target) is not StrategicPublicCategoricalPolicy
            or source_encoder.version != "showdown-public-categorical-observation-v3"
            or target_encoder.version != VERSION or source_encoder.tokens != target_encoder.tokens):
        raise ValueError("categorical_v3_to_v4_transfer_contract_required")
    old, new = source.state_dict(), target.state_dict()
    with torch.no_grad():
        for key, value in old.items():
            if key == "mlp_extractor.context.0.weight":
                new[key].zero_(); new[key][:, :LATENT_CONTEXT] = value
                new[key][:, 8] = 0
            elif key == "mlp_extractor.critic.0.weight":
                new[key].zero_(); new[key][:, :LATENT_CONTEXT] = value[:, :LATENT_CONTEXT]
                new[key][:, LATENT_CONTEXT + EXTRA:] = value[:, LATENT_CONTEXT:]
                new[key][:, 8] = 0
            else:
                if new[key].shape != value.shape:
                    raise ValueError("categorical_v4_transfer_unexpected_tensor_shape")
                new[key].copy_(value)
        target.load_state_dict(new)
    target.optimizer = target.optimizer_class(target.parameters(), lr=target.optimizer.param_groups[0]["lr"], **target.optimizer_kwargs)
