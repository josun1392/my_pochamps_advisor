"""Opt-in exact public identities bound to individual appearance records.

Categorical bit fields are embedding/gather transport, never ordinal features.
Preview entries remain separate: matching an appearance to a preview member is
not justified by matching species, nickname numbering or an unseen set.
"""
import json
from pathlib import Path
import numpy as np

from advisor.learned_encoder import fingerprint, identifier
from advisor.learned_public_interactions import (
    PublicInteractionEncoder, CONTEXT as BASE_CONTEXT, ACTION as BASE_ACTION,
)
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID

VERSION = "showdown-public-categorical-observation-v1"
REQUEST_IDENTITY_VERSION = "showdown-public-categorical-observation-v2"
RUNTIME_ABILITY_VERSION = "showdown-public-categorical-observation-v3"
VERSIONS = (VERSION, REQUEST_IDENTITY_VERSION, RUNTIME_ABILITY_VERSION, "showdown-public-categorical-observation-v4",
            "showdown-public-categorical-observation-v4-own-exact-hp-v1",
            "showdown-public-categorical-observation-v4-own-exact-hp-ablated-v1",
            "showdown-public-categorical-observation-v4-history-sequence-v1",
            "showdown-public-categorical-observation-v4-history-sequence-ablated-v1")
CATALOG_PATH = Path(__file__).resolve().parents[1] / "models/showdown_public_categories_v1/catalog.json"
PAD, UNKNOWN, ABSENT = 0, 1, 2
BITS = {"species": 11, "abilities": 9, "items": 8, "moves": 10}
EMBEDDINGS = {"species": 16, "abilities": 12, "items": 12, "moves": 16}
KNOWN_MOVES = 16
ENTITIES = 24
FLAGS = 7  # present / own / opponent / preview / active / apparent-unconfirmed / moves-listed
NUMERIC = 63
ENTITY_NUMERIC = NUMERIC + FLAGS
ENTITY_BITS = BITS["species"] + BITS["abilities"] + BITS["items"] + KNOWN_MOVES * BITS["moves"]
ENTITY = ENTITY_NUMERIC + ENTITY_BITS
ENTITY_LATENT = 24
REFERENCE_BITS = 5  # 0=no candidate, 1..24=record; lookup only
ACTION_BITS = REFERENCE_BITS + BITS["moves"] + BITS["species"]
CONTEXT = BASE_CONTEXT + ENTITIES * ENTITY
ACTION = BASE_ACTION + ACTION_BITS


def token_bits(token, width):
    return [(token >> b) & 1 for b in range(width)]


class PublicCategoricalEncoder:
    version = VERSION
    dimension = CONTEXT + 35 * ACTION

    def __init__(self, catalog):
        self.base = PublicInteractionEncoder(catalog)
        self.catalog = self.base.catalog
        public = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        if (public.get("schema_version") != "showdown-public-categories-v1"
                or public.get("engine_commit") != SHOWDOWN_COMMIT
                or public.get("format_id") != FORMAT_ID):
            raise ValueError("public_category_catalog_identity_mismatch")
        self.tokens = {}
        for kind, width in BITS.items():
            ids = public[kind]
            if (ids != sorted(set(ids)) or any(identifier(i) != i or not i for i in ids)
                    or len(ids) + 3 > 2 ** width):
                raise ValueError("public_category_vocabulary_invalid")
            self.tokens[kind] = {name: i + 3 for i, name in enumerate(ids)}
        if (set(self.tokens["species"]) != set(self.catalog["species"])
                or set(self.tokens["moves"]) != set(self.catalog["moves"]) | {"recharge"}):
            raise ValueError("public_category_base_catalog_mismatch")
        self.mega_forms = public["mega_forms_by_item"]
        if any(item not in self.tokens["items"] or not isinstance(forms, dict)
               or any(species not in self.tokens["species"] or form not in self.tokens["species"]
                      for species, form in forms.items()) for item, forms in self.mega_forms.items()):
            raise ValueError("invalid_public_mega_form_metadata")
        self.feature_contract = {
            "schema_version": "showdown-public-categorical-contract-v1",
            "version": VERSION,
            "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID,
            "public_state_version": "showdown-policy-state-v2",
            "base_v4_catalog_fingerprint": self.base.catalog_fingerprint,
            "category_catalog_sha256": fingerprint(public),
            "token_map_sha256": fingerprint(self.tokens),
            "category_counts": {kind: len(tokens) for kind, tokens in self.tokens.items()},
            "token_sentinels": {"padding_or_no_candidate": PAD, "unknown": UNKNOWN, "confirmed_absence": ABSENT},
            "token_bits": dict(BITS), "embedding_dimensions": dict(EMBEDDINGS),
            "entity_layout": ["own_public_records_6", "opponent_apparent_records_6", "own_preview_6", "opponent_preview_6"],
            "entity_order": "public_protocol_key_sorted_no_inferred_preview_join",
            "entity_flag_order": ["present", "own", "opponent", "preview", "active",
                                  "apparent_identity_unconfirmed", "public_moves_listed"],
            "known_moves_capacity": KNOWN_MOVES,
            "move_list_scope": "own_projected_request_moves_or_opponent_public_reveals_not_inferred_complete_set",
            "entity_dimensions": {"numeric": ENTITY_NUMERIC, "transport": ENTITY_BITS, "latent": ENTITY_LATENT},
            "action_dimensions": {"base_v4": BASE_ACTION, "transport": ACTION_BITS},
            "action_transport_order": ["own_record_reference", "own_request_move", "public_candidate_form"],
            "mega_candidate_scope": "native_request_flag_plus_public_own_item_and_pinned_native_item_metadata_or_unknown",
            "observation_dimension": self.dimension,
            "policy_projection": "shared_entity_mlp_366_64_24_flattened_record_latents_then_existing_shared_action_scorer",
            "transport": "binary_indices_decoded_only_by_embedding_or_entity_gather",
            "overflow_or_unknown_known_identity": "fail_closed",
            "preview_binding": "separate_public_records_not_inferred_individual_identity",
        }
        self.catalog_fingerprint = fingerprint(self.feature_contract)

    def token(self, kind, value):
        if isinstance(value, dict):
            if value not in ({}, {"knowledge": "unknown"}):
                raise ValueError("invalid_public_unknown_value")
            return UNKNOWN
        if value is None:
            return ABSENT  # only the versioned public projection can establish absence
        if not isinstance(value, str):
            raise ValueError("invalid_public_categorical_value")
        if not value:
            return UNKNOWN  # empty/unconfirmed value is not known absence
        key = identifier(value)
        if key not in self.tokens[kind]:
            raise ValueError(f"unsupported_known_public_{kind}")
        return self.tokens[kind][key]

    def _entity(self, row, *, own, preview, active):
        moves = row.get("known_moves", [])
        if not isinstance(moves, list) or any(not isinstance(m, str) or not m for m in moves):
            raise ValueError("invalid_public_known_move_list")
        if len(moves) > KNOWN_MOVES:
            raise ValueError("public_known_move_capacity_exceeded")
        flags = [1, float(own), float(not own), float(preview), float(active),
                 float(row.get("identity_scope") == "public_apparent_identity_unconfirmed"),
                 float(bool(moves))]
        values = self.base._row(row) + flags
        for kind, value in (("species", row.get("details", {})),
                            ("abilities", row.get("current_ability", {})),
                            ("items", row.get("known_item", {}))):
            values += token_bits(self.token(kind, value), BITS[kind])
        for i in range(KNOWN_MOVES):
            # Unrevealed/missing moves remain Unknown, never "no move".
            values += token_bits(self.token("moves", moves[i]) if i < len(moves) else UNKNOWN, BITS["moves"])
        return values

    def coverage(self, observation):
        return {**self.base.coverage(observation), "catalog_fingerprint": self.catalog_fingerprint,
                "categorical_contract": self.version, "known_moves_capacity": KNOWN_MOVES,
                "structured_projection_scope": "existing_public_state_v2_not_complete_native_mechanics_state",
                "unsupported_cases": "encode_rejects_known_identity_or_record_capacity_gaps"}

    def encode(self, observation):
        if observation.get("state", {}).get("state_version") != "showdown-policy-state-v2":
            raise ValueError("versioned_public_state_required")
        # Existing channel/privileged-root checks and numerical features are reused.
        base = self.base.encode(observation)
        state = observation["state"]
        own, opp = state["self_side"], state["opponent_side"]
        roster = observation["own_request"].get("side", {}).get("pokemon", [])
        if len(roster) > 6:
            raise ValueError("public_roster_capacity_exceeded")
        records, own_refs = [], {}
        own_rows = self._own_records(observation)
        for side_index, side in enumerate((own, opp)):
            rows = own_rows if side_index == 0 else sorted(side["pokemon"].items())
            if len(rows) > 6:
                raise ValueError("public_appearance_capacity_exceeded")
            for i, (key, row) in enumerate(rows):
                if side_index == 0:
                    name = key.split(": ", 1)[-1]
                    if name in own_refs:
                        raise ValueError("ambiguous_own_public_identity")
                    own_refs[name] = i + 1
                # Do not merge opponent apparent aliases or infer hidden Illusion identity.
                records.append(self._entity(row, own=side_index == 0, preview=False,
                                            active=self._record_active(side, key, row)))
            records.extend([[0.0] * ENTITY for _ in range(6 - len(rows))])
        for side_index, side in enumerate((own, opp)):
            if len(side["preview"]) > 6:
                raise ValueError("public_preview_capacity_exceeded")
            records.extend(self._entity(p, own=side_index == 0, preview=True, active=False) for p in side["preview"])
            records.extend([[0.0] * ENTITY for _ in range(6 - len(side["preview"]))])
        references = []
        for p in roster:
            name = p["ident"].split(": ", 1)[-1]
            if name not in own_refs:
                raise ValueError("unbound_own_request_identity")
            references.append(own_refs[name])
        active = next((i for i, p in enumerate(roster) if p.get("active")), None)
        slots = observation["own_request"].get("active", [{}])[0].get("moves", [])
        native_rows = base[BASE_CONTEXT:].reshape(35, BASE_ACTION)
        extra = []
        for index in range(35):
            slot = ((index - 6) % 4 if 6 <= index < 14 else
                    (index - 27) % 4 if 27 <= index < 35 else None)
            target = index if index < min(6, len(roster)) else active if slot is not None else None
            reference = references[target] if target is not None else 0
            move = self.token("moves", slots[slot].get("id", {})) if slot is not None and slot < len(slots) else PAD
            form = UNKNOWN if reference else PAD
            if reference:
                own_row = own_rows[reference - 1][1]
                form = self.token("species", own_row.get("details", {}))
                if slot is not None and (10 <= index < 14 or 27 <= index < 35):
                    key = "canMegaEvo" if index < 14 else "canMegaEvoX" if index < 31 else "canMegaEvoY"
                    mega = observation["own_request"].get("active", [{}])[0].get(key)
                    form = UNKNOWN  # availability is not evidence of the current/base form being the candidate
                    if isinstance(mega, str):
                        form = self.token("species", mega)
                    elif mega is True and key == "canMegaEvo":
                        # Native M-C requests expose a boolean; reuse public native
                        # stone metadata, not hidden Pokemon.canMegaEvo or mechanics.
                        item = own_row.get("known_item", {})
                        if isinstance(item, str):
                            species = identifier(own_row.get("request_details", own_row.get("details", "")))
                            candidate = self.mega_forms.get(identifier(item), {}).get(species)
                            if candidate:
                                form = self.token("species", candidate)
            if observation["action_mask"][index] and slot is not None and (not reference or move in (PAD, UNKNOWN, ABSENT)):
                raise ValueError("unbound_public_legal_move")
            if observation["action_mask"][index] and index < 6 and not reference:
                raise ValueError("unbound_public_legal_switch")
            extra.append(token_bits(reference, REFERENCE_BITS) + token_bits(move, BITS["moves"]) + token_bits(form, BITS["species"]))
        actions = np.concatenate((native_rows[:, :-1], np.asarray(extra), native_rows[:, -1:]), axis=1)
        result = np.concatenate((base[:BASE_CONTEXT], np.asarray(records).flatten(), actions.flatten())).astype(np.float32)
        if result.shape != (self.dimension,) or not np.isfinite(result).all():
            raise ValueError("invalid_public_categorical_features")
        return result

    def _own_records(self, observation):
        return sorted(observation["state"]["self_side"]["pokemon"].items())

    def _record_active(self, side, key, row):
        return key == side["active_identity"]


class RequestIdentityCategoricalEncoder(PublicCategoricalEncoder):
    """Same tensors/embeddings, separately bound own-request identity semantics."""
    version = REQUEST_IDENTITY_VERSION

    def __init__(self, catalog):
        super().__init__(catalog)
        self.feature_contract = {**self.feature_contract, "version": self.version,
            "schema_version": "showdown-public-categorical-contract-v2",
            "own_record_binding": "unique_native_own_request_ident_and_latest_public_appearance_v1",
            "wait_request_binding": "drop_only_empty_unpositioned_own_protocol_reference_v1",
            "legacy_numeric_scope": "unchanged_v4_features_original_public_projection",
            "opponent_binding": "unchanged_apparent_records_no_inferred_merge"}
        self.catalog_fingerprint = fingerprint(self.feature_contract)

    def _own_records(self, observation):
        from advisor.learned_own_identity import own_player_records
        return own_player_records(observation)

    def _record_active(self, side, key, row):
        return row.get("own_request_active", super()._record_active(side, key, row))


class RuntimeAbilityCategoricalEncoder(RequestIdentityCategoricalEncoder):
    """Append-only ability vocabulary, identical transport and tensor layout."""
    version = RUNTIME_ABILITY_VERSION

    def __init__(self, catalog):
        super().__init__(catalog)
        from hashlib import sha256
        path = Path(__file__).resolve().parents[1] / "models/showdown_public_categories_v3/catalog.json"
        runtime = json.loads(path.read_text(encoding="utf-8"))
        old = self.tokens["abilities"]
        names = runtime["abilities"]
        registry = runtime["native_registry"]
        if (runtime.get("schema_version") != "showdown-public-runtime-categories-v3"
                or runtime.get("engine_commit") != SHOWDOWN_COMMIT or runtime.get("format_id") != FORMAT_ID
                or runtime.get("legacy_catalog_sha256") != sha256(CATALOG_PATH.read_bytes()).hexdigest()
                or names[:len(old)] != list(old) or runtime["legacy_ability_count"] != len(old)
                or names[len(old):] != sorted(set(names) - set(old))
                or len(names) != len(set(names)) or len(names) + 3 > 2 ** BITS["abilities"]
                or any(identifier(n) != n or not n for n in names)
                or set(names) != {a["id"] for a in registry["abilities"]}
                or registry["format_id"] != FORMAT_ID or fingerprint(registry) != runtime["native_registry_sha256"]):
            raise ValueError("public_runtime_ability_catalog_mismatch")
        tokens = {n: i + 3 for i,n in enumerate(names)}
        if fingerprint(tokens) != runtime["token_map_sha256"]:
            raise ValueError("public_runtime_ability_token_map_mismatch")
        self.tokens["abilities"] = tokens
        self._ability_spellings = {a["id"].casefold() for a in registry["abilities"]}
        self._ability_spellings.update(a["name"].casefold() for a in registry["abilities"]
                                       if identifier(a["name"]) == a["id"])
        self.feature_contract = {**self.feature_contract,"schema_version":"showdown-public-categorical-contract-v3",
            "version":self.version,"runtime_ability_catalog_sha256":sha256(path.read_bytes()).hexdigest(),
            "runtime_ability_catalog_fingerprint":fingerprint(runtime),"token_map_sha256":fingerprint(self.tokens),
            "category_counts":{k:len(t) for k,t in self.tokens.items()},
            "runtime_ability_scope":"pinned_format_Dex_all_canonical_abilities_public_only_not_set_legality",
            "ability_assignment":"V1_V2_tokens_preserved_canonical_additions_appended_existing_512_embeddings",
            "compatibility":"V2_features_and_all_policy_tensors_unchanged_for_legacy_identities"}
        self.catalog_fingerprint = fingerprint(self.feature_contract)

    def token(self, kind, value):
        if kind == "abilities" and isinstance(value, str) and value and value.casefold() not in self._ability_spellings:
            raise ValueError("invalid_or_unsupported_public_runtime_ability_identity")
        return super().token(kind, value)
