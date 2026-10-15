"""Opt-in V4 extension: exact HP from the authenticated owner's request only.

The original V4 transport is an unchanged prefix. Six sorted own identity rows
carry current/1024, maximum/1024 and separate knowledge flags. A fainted request
`0 fnt` establishes zero current HP, but does not establish a maximum. No public
percentage, species prior, previous episode or opponent request fills a gap.
"""
import re
import numpy as np

from advisor.learned_encoder import fingerprint
from advisor.learned_own_identity import own_player_records
from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder

VERSION = "showdown-public-categorical-observation-v4-own-exact-hp-v1"
ABLATED_VERSION = "showdown-public-categorical-observation-v4-own-exact-hp-ablated-v1"
VERSIONS = (VERSION, ABLATED_VERSION)
SLOTS, WIDTH, SCALE, LIMIT = 6, 4, 1024, 4096
EXTRA = SLOTS * WIDTH
OLD_DIMENSION = StrategicPublicCategoricalEncoder.dimension


def own_hp_features(observation):
    """Bind request identities to the same sorted own rows used by V4.

    Authentication here validates the native policy-channel side/roster binding;
    the upstream ShowdownEnvironment remains the trusted channel owner. This
    accepts no checkpoint, scenario set or separately supplied native state.
    """
    if observation.get("side") not in ("self", "opponent"):
        raise ValueError("invalid_own_hp_player_side")
    role = "p1" if observation["side"] == "self" else "p2"
    side = observation["own_request"].get("side", {})
    roster = side.get("pokemon", [])
    result = np.zeros((SLOTS, WIDTH), dtype=np.float32)
    if not roster:
        return result  # Unknown, not an inferred zero or maximum.
    if side.get("id") != role or not 1 <= len(roster) <= SLOTS:
        raise ValueError("unauthenticated_own_hp_roster")
    requests = {}
    for pokemon in roster:
        ident = pokemon.get("ident")
        if (not isinstance(ident, str) or not ident.startswith(role + ": ")
                or not ident[len(role) + 2:] or ident in requests):
            raise ValueError("invalid_own_hp_request_identity")
        requests[ident] = pokemon
    parsed = {}
    # Validate before invoking the historical projector (which expects native
    # well-formed condition strings). No malformed denominator reaches it.
    for ident, pokemon in requests.items():
        values = np.zeros(WIDTH, dtype=np.float32)
        parsed[ident] = values
        condition = pokemon.get("condition")
        # The maintained V4 request contract uses strings, including an empty
        # string for unavailable HP. Do not broaden historical condition parsing.
        if condition == "":
            continue
        if not isinstance(condition, str):
            raise ValueError("malformed_own_hp_condition")
        match = re.fullmatch(r"(0|[1-9]\d*)/([1-9]\d*)(?: (?:brn|par|slp|frz|psn|tox|fnt))?", condition)
        if condition == "0 fnt" or condition == "0":
            values[2] = 1
        elif match:
            current, maximum = map(int, match.group(1, 2))
            if not 0 <= current <= maximum <= LIMIT:
                raise ValueError("out_of_bounds_own_hp_condition")
            values[:] = (current / SCALE, maximum / SCALE, 1, 1)
        else:
            raise ValueError("nonexact_or_malformed_own_hp_condition")
    rows = own_player_records(observation)
    if len(rows) != len(requests) or {key for key, _ in rows} != set(requests):
        raise ValueError("unbound_own_hp_request_identity")
    for i, (ident, _) in enumerate(rows):
        result[i] = parsed[ident]
    return result


class OwnExactHPCategoricalEncoder(StrategicPublicCategoricalEncoder):
    dimension = OLD_DIMENSION + EXTRA

    def __init__(self, catalog, version=VERSION):
        if version not in VERSIONS:
            raise ValueError("unsupported_own_hp_contract")
        self.version = version
        super().__init__(catalog)
        self.base = StrategicPublicCategoricalEncoder(self.catalog)
        self.feature_contract = {
            **self.feature_contract,
            "schema_version": "showdown-public-categorical-own-exact-hp-contract-v1",
            "version": version, "dimension": self.dimension,
            "observation_dimension": self.dimension,
            "parent_feature_fingerprint": self.base.catalog_fingerprint,
            "own_hp": {
                "transport": "unchanged_v4_prefix_then_six_sorted_own_identity_rows",
                "fields": ["current_div_1024", "maximum_div_1024", "current_known", "maximum_known"],
                "scale": SCALE, "maximum_supported_hp": LIMIT, "width": EXTRA,
                "authority": "native_policy_channel_own_request_side_id_and_exact_ident_only",
                "binding": "V4_own_player_records_sorted_identities_and_candidate_reference",
                "missing": "zero_values_unknown_flags_no_previous_state_or_species_inference",
                "padding": "zero_row_existing_v4_entity_presence_unchanged",
                "ablation": version == ABLATED_VERSION,
                "ablation_scope": "all_added_hp_values_and_flags_zero_in_actor_and_critic",
                "transfer": "V4_weights_new_columns_zero_fresh_Adam",
            },
        }
        self.catalog_fingerprint = fingerprint(self.feature_contract)

    def encode(self, observation):
        hp = own_hp_features(observation)
        if self.version == ABLATED_VERSION:
            hp = np.zeros_like(hp)
        return np.concatenate((self.base.encode(observation), hp.flatten()))
