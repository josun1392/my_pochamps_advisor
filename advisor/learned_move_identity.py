"""Experimental own-move categorical ablation; native actions/mechanics unchanged.

Token bits are transport for an embedding index, never ordinal MLP features.
The control token is a deterministic equivalence class of existing V3 static
features and contains no exact identity within a feature-collision group.
"""

import json
from functools import lru_cache
import numpy as np
from advisor.learned_encoder import fingerprint, identifier
from advisor.learned_tactics_encoder import (
    TacticalObservationEncoder, CONTEXT, ACTION as BASE_ACTION,
)

CONTROL = "showdown-own-move-class-observation-v1"
TREATMENT = "showdown-own-move-id-observation-v1"
VERSIONS = (CONTROL, TREATMENT)
TOKEN_BITS = 10
TOKEN_COUNT = 1 << TOKEN_BITS
EMBEDDING = 16
ACTION = BASE_ACTION + TOKEN_BITS


class OwnMoveTokenEncoder(TacticalObservationEncoder):
    dimension = CONTEXT + 35 * ACTION

    def __init__(self, catalog, version):
        if version not in VERSIONS:
            raise ValueError("unsupported_own_move_token_version")
        super().__init__(catalog)
        self.version = version
        # Showdown emits this public forced request after recharge attacks.
        # It is an action request, not a selectable Dex move or hidden inference.
        ids = sorted(set(self.catalog["moves"]) | {"recharge"})
        if len(ids) >= TOKEN_COUNT:
            raise ValueError("own_move_token_capacity_exceeded")
        descriptors = {
            m: json.dumps(self.static_descriptor(m), separators=(",", ":"))
            for m in ids
        }
        classes = {d: i + 1 for i, d in enumerate(sorted(set(descriptors.values())))}
        self.tokens = {
            m: i + 1 if version == TREATMENT else classes[descriptors[m]]
            for i, m in enumerate(ids)
        }
        self.feature_contract = {
            "schema_version": "showdown-public-own-move-token-v1",
            "version": version,
            "scope": "own_request_public_move_id_only",
            "control_information": "deterministic_existing_v3_static_descriptor_class",
            "token_map_sha256": fingerprint(self.tokens),
            "base_v3_catalog_fingerprint": self.catalog_fingerprint,
            "token_bits": TOKEN_BITS,
            "token_count": TOKEN_COUNT,
            "embedding_dimension": EMBEDDING,
            "zero_token": "no_move_candidate",
            "unknown_legal_move": "fail_closed",
            "native_request_pseudo_actions": ["recharge"],
            "transport": "binary_index_bits_decoded_only_for_categorical_embedding",
        }
        self.catalog_fingerprint = fingerprint(self.feature_contract)

    @lru_cache(maxsize=1024)
    def static_descriptor(self, move):
        return tuple(self._move(move, {}, {}, {"pp": 1, "maxpp": 1})) + self._tactic(move)

    def encode(self, observation):
        base = super().encode(observation)
        rows = base[CONTEXT:].reshape(35, BASE_ACTION)
        slots = observation["own_request"].get("active", [{}])[0].get("moves", [])
        bits = np.zeros((35, TOKEN_BITS), dtype=np.float32)
        for i in (*range(6, 14), *range(27, 35)):
            slot = (i - 6) % 4 if i < 14 else (i - 27) % 4
            if slot >= len(slots):
                continue
            move = identifier(slots[slot].get("id", ""))
            if move not in self.tokens:
                if observation["action_mask"][i]:
                    raise ValueError("unknown_public_legal_own_move")
                continue
            token = self.tokens[move]
            bits[i] = [(token >> b) & 1 for b in range(TOKEN_BITS)]
        # Preserve the existing final-column legal indicator.
        actions = np.concatenate((rows[:, :-1], bits, rows[:, -1:]), axis=1)
        return np.concatenate((base[:CONTEXT], actions.flatten())).astype(np.float32)
