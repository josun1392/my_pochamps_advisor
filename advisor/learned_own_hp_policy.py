"""Identity-bound own HP pathways, with a function-preserving V4 transfer."""
import torch
from torch import nn

from advisor.learned_own_hp import OLD_DIMENSION, EXTRA, WIDTH, SLOTS, VERSIONS
from advisor.learned_public_categories import BASE_ACTION, ACTION, REFERENCE_BITS
from advisor.learned_public_categories_policy import decode_bits, LATENT_CONTEXT, LATENT_ACTION
from advisor.learned_strategic_public import CONTEXT, EXTRA as STRATEGIC_EXTRA, VERSION as V4
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalExtractor, StrategicPublicCategoricalPolicy

OLD_LATENT_CONTEXT = LATENT_CONTEXT + STRATEGIC_EXTRA


class OwnExactHPExtractor(StrategicPublicCategoricalExtractor):
    def __init__(self):
        super().__init__()
        self.context[0] = nn.Linear(OLD_LATENT_CONTEXT + EXTRA, 64)
        self.scorer[0] = nn.Linear(64 + LATENT_ACTION + WIDTH, 128)
        self.critic[0] = nn.Linear(OLD_LATENT_CONTEXT + EXTRA + LATENT_ACTION + WIDTH, 128)

    def _public_rows(self, features):
        old, hp = features[:, :OLD_DIMENSION], features[:, OLD_DIMENSION:]
        if hp.shape[1] != EXTRA or not torch.isfinite(hp).all():
            raise ValueError("invalid_own_hp_transport")
        rows = hp.reshape(-1, SLOTS, WIDTH)
        if (not torch.all((rows[:, :, 2:] == 0) | (rows[:, :, 2:] == 1))
                or (rows[:, :, :2] < 0).any() or (rows[:, :, :2] > 4).any()
                or (rows[:, :, :2] * (1 - rows[:, :, 2:]) != 0).any()):
            raise ValueError("invalid_own_hp_knowledge_transport")
        context, actions, mask = super()._public_rows(old)
        raw = old[:, CONTEXT:].reshape(-1, 35, ACTION)
        reference = decode_bits(raw[:, :, BASE_ACTION - 1:BASE_ACTION - 1 + REFERENCE_BITS])
        if (reference > SLOTS).any():
            raise ValueError("nonown_hp_candidate_reference")
        bank = torch.cat((rows.new_zeros((len(rows), 1, WIDTH)), rows), dim=1)
        candidate = bank.gather(1, reference[:, :, None].expand(-1, -1, WIDTH))
        return torch.cat((context, hp), dim=1), torch.cat((actions, candidate), dim=-1), mask


class OwnExactHPCategoricalPolicy(StrategicPublicCategoricalPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = OwnExactHPExtractor()


def transfer_own_hp_weights(target, source, target_encoder, source_encoder):
    """Weights only, never a changed-shape optimizer or uninterrupted resume."""
    if (type(source) is not StrategicPublicCategoricalPolicy
            or type(target) is not OwnExactHPCategoricalPolicy
            or source_encoder.version != V4 or target_encoder.version not in VERSIONS
            or source_encoder.catalog_fingerprint != target_encoder.base.catalog_fingerprint
            or source_encoder.tokens != target_encoder.tokens):
        raise ValueError("v4_to_own_exact_hp_transfer_contract_required")
    old, new = source.state_dict(), target.state_dict()
    with torch.no_grad():
        for key, value in old.items():
            value = value.to(new[key].device)
            if key == "mlp_extractor.context.0.weight":
                new[key].zero_(); new[key][:, :OLD_LATENT_CONTEXT] = value
            elif key == "mlp_extractor.scorer.0.weight":
                new[key].zero_(); new[key][:, :64 + LATENT_ACTION] = value
            elif key == "mlp_extractor.critic.0.weight":
                new[key].zero_()
                new[key][:, :OLD_LATENT_CONTEXT] = value[:, :OLD_LATENT_CONTEXT]
                new[key][:, OLD_LATENT_CONTEXT + EXTRA:OLD_LATENT_CONTEXT + EXTRA + LATENT_ACTION] = value[:, OLD_LATENT_CONTEXT:]
            else:
                if new[key].shape != value.shape:
                    raise ValueError("own_hp_transfer_unexpected_tensor_shape")
                new[key].copy_(value)
        target.load_state_dict(new)
    target.optimizer = target.optimizer_class(target.parameters(), lr=target.optimizer.param_groups[0]["lr"], **target.optimizer_kwargs)
