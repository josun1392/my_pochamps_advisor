"""Small shared categorical preview network inside unchanged MaskablePPO."""
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy

from advisor.learned_preview import ACTIONS, ACTION_VERSION, VERSION, PreviewEncoder, NUMERIC, ROW, DIMENSION
from advisor.learned_public_categories import BITS, EMBEDDINGS
from advisor.learned_public_categories_policy import decode_bits
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID


class PreviewExtractor(nn.Module):
    latent_dim_pi, latent_dim_vf = 120, 64

    def __init__(self):
        super().__init__()
        self.embeddings = nn.ModuleDict({"category_" + k: nn.Embedding(2 ** BITS[k], v, padding_idx=0)
                                        for k, v in EMBEDDINGS.items()})
        self.entity = nn.Sequential(nn.Linear(NUMERIC + 16 + 12 + 12 + 4 * 16, 64), nn.Tanh(),
                                    nn.Linear(64, 24), nn.Tanh())
        self.context = nn.Sequential(nn.Linear(12 * 24, 64), nn.Tanh())
        self.scorer = nn.Sequential(nn.Linear(64 + 3 * 24, 64), nn.Tanh(), nn.Linear(64, 1))
        self.critic = nn.Sequential(nn.Linear(12 * 24, 64), nn.Tanh())
        self.register_buffer("ordered_slots", torch.tensor(ACTIONS, dtype=torch.long) - 1)

    def _rows(self, features):
        raw = features.reshape(-1, 12, ROW)
        data, start = [raw[:, :, :NUMERIC]], NUMERIC
        for k in ("species", "abilities", "items"):
            width = BITS[k]
            data.append(self.embeddings["category_" + k](decode_bits(raw[:, :, start:start + width])))
            start += width
        data.append(self.embeddings["category_moves"](decode_bits(raw[:, :, start:].reshape(-1, 12, 4, BITS["moves"]))).flatten(2))
        return self.entity(torch.cat(data, dim=-1))

    def forward_actor(self, features):
        rows = self._rows(features)
        context = self.context(rows.flatten(1))[:, None, :].expand(-1, 120, -1)
        ordered = rows[:, self.ordered_slots, :].reshape(-1, 120, 72)
        return self.scorer(torch.cat((context, ordered), dim=-1)).squeeze(-1)

    def forward_critic(self, features):
        return self.critic(self._rows(features).flatten(1))

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class PreviewPolicy(MaskableActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = PreviewExtractor()

    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.action_net = nn.Identity()
        nn.init.normal_(self.mlp_extractor.scorer[-1].weight, std=.01)
        nn.init.zeros_(self.mlp_extractor.scorer[-1].bias)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class LearnedPreviewPolicy:
    """Trusted local preview-only checkpoint loader, incompatible with battle35."""
    def __init__(self, path, catalog, *, expected_sha256=None):
        path = Path(path).with_suffix(".zip")
        self.model_id = sha256(path.read_bytes()).hexdigest()
        self.metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        self.encoder = PreviewEncoder(catalog)
        expected = {"schema_version": "showdown-preview-model-v1", "encoder_version": VERSION,
            "feature_fingerprint": self.encoder.fingerprint, "action_schema_version": ACTION_VERSION,
            "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
            "model_sha256": self.model_id, "gamma": 1., "objective": "native_terminal_win_loss_draw_preview_bandit_v1"}
        if (any(self.metadata.get(k) != v for k, v in expected.items())
                or self.metadata.get("feature_contract") != self.encoder.feature_contract) or (
                expected_sha256 is not None and expected_sha256 != self.model_id):
            raise ValueError("preview_checkpoint_contract_mismatch")
        self.model = MaskablePPO.load(path, device="cpu")
        if (type(self.model.policy) is not PreviewPolicy or self.model.action_space.n != 120
                or self.model.observation_space.shape != (DIMENSION,) or self.model.gamma != 1.
                or self.model.gae_lambda != .95):
            raise ValueError("incompatible_preview_policy")

    def infer(self, observation):
        features = self.encoder.encode(observation)
        with torch.no_grad():
            x = torch.tensor(features)[None]
            distribution = self.model.policy.get_distribution(x, action_masks=np.ones((1, 120), bool))
            probabilities = distribution.distribution.probs[0].numpy()
            value = float(self.model.policy.predict_values(x)[0, 0])
        if not np.isfinite(probabilities).all() or not np.isfinite(value) or not np.isclose(probabilities.sum(), 1):
            raise ValueError("nonfinite_preview_inference")
        return {"action": int(probabilities.argmax()), "probabilities": probabilities.tolist(),
                "terminal_return_estimate": value}
