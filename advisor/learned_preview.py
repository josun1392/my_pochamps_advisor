"""PREVIEW_V1: exact ordered roster actions and pre-choice public features.

No scenario, native checkpoint, rival selection or future history is accepted
by this encoder. Native requests, not hypothetical opponent sets, supply data.
"""
from itertools import permutations
import numpy as np

from advisor.learned_encoder import TYPES, STATS, fingerprint, identifier
from advisor.learned_public_categories import RuntimeAbilityCategoricalEncoder, BITS, token_bits
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID

VERSION = "showdown-public-preview-observation-v1"
ACTION_VERSION = "showdown-ordered-bring-three-actions-v1"
ACTIONS = tuple(permutations(range(1, 7), 3))
NUMERIC = 51
ROW = NUMERIC + BITS["species"] + BITS["abilities"] + BITS["items"] + 4 * BITS["moves"]
DIMENSION = 12 * ROW


def selection(action):
    if type(action) is not int or not 0 <= action < 120:
        raise ValueError("invalid_ordered_preview_action")
    return list(ACTIONS[action])


def public_preview(native):
    """Reduce one actual pre-selection native request to a closed public DTO."""
    if (set(native) != {"schema_version", "side", "own_request", "events"}
            or native["schema_version"] != "showdown-public-preview-v1"
            or native["side"] not in ("self", "opponent")):
        raise ValueError("invalid_native_public_preview")
    role = "p1" if native["side"] == "self" else "p2"
    request = native["own_request"]
    if (request.get("teamPreview") is not True or request.get("maxChosenTeamSize") != 3
            or request.get("side", {}).get("id") != role):
        raise ValueError("wrong_preview_phase_or_owner")
    own = request["side"]["pokemon"]
    preview = {"p1": [], "p2": []}
    for line in native["events"]:
        parts = line.split("|")
        if len(parts) > 3 and parts[1] == "poke" and parts[2] in preview:
            preview[parts[2]].append(parts[3])
        elif len(parts) < 2 or parts[1] not in {"gametype", "gen", "tier", "rule", "teampreview", "teamsize", "clearpoke"}:
            raise ValueError("future_or_non_preview_event")
    if len(own) != 6 or any(len(p) != 6 for p in preview.values()):
        raise ValueError("full_six_member_preview_required")
    rows = []
    for i, pokemon in enumerate(own):
        if (not pokemon["ident"].startswith(role + ": ") or
                identifier(pokemon["details"]) != identifier(preview[role][i])):
            raise ValueError("preview_roster_binding_mismatch")
        condition = pokemon["condition"].split("/")
        hp = int(condition[1].split()[0]) if len(condition) == 2 else None
        if hp is None or not 1 <= hp <= 2048:
            raise ValueError("own_preview_stats_unavailable")
        rows.append({"slot": i + 1, "details": pokemon["details"],
            "moves": list(pokemon["moves"]), "ability": pokemon["ability"] or None,
            "item": pokemon["item"] or None,
            "stats": {"hp": hp, **{s: pokemon["stats"][s] for s in STATS[1:]}}})
    other = "p2" if role == "p1" else "p1"
    return {"schema_version": VERSION, "format_id": FORMAT_ID,
        "own": rows, "opponent": [{"slot": i + 1, "details": details,
            "moves": {"knowledge": "unknown"}, "ability": {"knowledge": "unknown"},
            "item": {"knowledge": "unknown"}, "stats": {"knowledge": "unknown"}}
            for i, details in enumerate(preview[other])]}


class PreviewEncoder:
    version, dimension = VERSION, DIMENSION

    def __init__(self, catalog):
        self.categories = RuntimeAbilityCategoricalEncoder(catalog)
        self.catalog = self.categories.catalog
        self.feature_contract = {"version": VERSION, "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID, "action_schema": ACTION_VERSION,
            "actions_sha256": fingerprint(ACTIONS), "category_contract": self.categories.catalog_fingerprint,
            "rows": "own_original_roster_slots_1_to_6_then_opponent_public_preview_slots_1_to_6",
            "own_set_source": "native_prechoice_owner_request",
            "opponent_scope": "native_public_poke_details_only_no_selected_three",
            "numeric": "own_flag_native_owner_stats6_public_base_stats6_types18_move_power4_accuracy4_category12",
            "numeric_scaling": "stats/500_base/255_power/250_accuracy_native_fraction",
            "binary_transport": ["species11", "ability9", "item8", "moves4x10"],
            "category_sentinels": {"padding": 0, "unknown": 1, "known_absent": 2},
            "dimensions": {"row": ROW, "rows": 12, "total": DIMENSION},
            "network": {"shared_embeddings": {"species": 16, "abilities": 12, "items": 12, "moves": 16},
                "entity_mlp": [155, 64, 24], "context": [288, 64], "ordered_actor": [136, 64, 1],
                "critic": [288, 64, 1], "activations": "tanh"},
            "unrepresented": ["gender", "shiny", "pokeball", "explicit_nature_EV_IV_already_reflected_in_own_native_stats"],
            "policy": "shared_category_embeddings_bound_to_slot_then_ordered_action_scorer_v1"}
        self.fingerprint = fingerprint(self.feature_contract)

    def encode(self, observation):
        if (set(observation) != {"schema_version", "format_id", "own", "opponent"}
                or observation["schema_version"] != VERSION or observation["format_id"] != FORMAT_ID
                or len(observation["own"]) != 6 or len(observation["opponent"]) != 6):
            raise ValueError("invalid_preview_observation_contract")
        result = []
        unknown = {"knowledge": "unknown"}
        for is_own, roster in ((True, observation["own"]), (False, observation["opponent"])):
            for slot, row in enumerate(roster, 1):
                if set(row) != {"slot", "details", "moves", "ability", "item", "stats"} or row["slot"] != slot:
                    raise ValueError("invalid_preview_slot_binding")
                if not is_own and any(row[k] != unknown for k in ("moves", "ability", "item", "stats")):
                    raise ValueError("opponent_hidden_preview_information")
                species = identifier(row["details"])
                if species not in self.catalog["species"]:
                    raise ValueError("unsupported_public_preview_species")
                public = self.catalog["species"][species]
                moves = row["moves"] if is_own else []
                if is_own and (not isinstance(moves, list) or not 1 <= len(moves) <= 4
                        or set(row["stats"]) != set(STATS)):
                    raise ValueError("invalid_own_preview_set")
                move_data = [self.catalog["moves"][identifier(m)] for m in moves]
                numeric = [float(is_own)] + ([row["stats"][s] / 500 for s in STATS] if is_own else [0.] * 6)
                numeric += [public["base_stats"][s] / 255 for s in STATS]
                numeric += [float(t in public["types"]) for t in TYPES]
                numeric += [m["power"] / 250 for m in move_data] + [0.] * (4 - len(moves))
                numeric += [m["accuracy"] for m in move_data] + [0.] * (4 - len(moves))
                numeric += [float(m["category"] == c) for m in move_data for c in ("Physical", "Special", "Status")]
                numeric += [0.] * (3 * (4 - len(moves)))
                tokens = token_bits(self.categories.token("species", row["details"]), BITS["species"])
                tokens += token_bits(self.categories.token("abilities", row["ability"]), BITS["abilities"])
                tokens += token_bits(self.categories.token("items", row["item"]), BITS["items"])
                for index in range(4):
                    token = self.categories.token("moves", moves[index]) if index < len(moves) else (0 if is_own else 1)
                    tokens += token_bits(token, BITS["moves"])
                result.extend(numeric + tokens)
        features = np.asarray(result, dtype=np.float32)
        if features.shape != (DIMENSION,) or not np.isfinite(features).all() or (abs(features) > 8).any():
            raise ValueError("invalid_preview_features")
        return features
