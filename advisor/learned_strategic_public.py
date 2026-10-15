"""Bounded public protocol projection for categorical V4, not battle mechanics.

Only events actually delivered to this player establish effects. No clocks,
damage rolls, hidden sets, preview joins or inferred ability activations. The
legacy nominal species/type priors remain priors; current typing is separate.
"""
from copy import deepcopy
import numpy as np

from advisor.learned_encoder import TYPES, fingerprint, identifier
from advisor.learned_public_categories import RuntimeAbilityCategoricalEncoder, CONTEXT as OLD_CONTEXT, ACTION

VERSION = "showdown-public-categorical-observation-v4"
PROJECTION = "showdown-strategic-public-protocol-v1"
EFFECTS = ("substitute", "taunt", "encore", "confusion", "trapped", "recharge",
           "healblock", "throatchop", "flashfire")
EXTRA_WEATHER = ("hail", "desolateland", "primordialsea", "deltastream")
WEATHER = (None, "sunnyday", "raindance", "sandstorm", "snowscape", *EXTRA_WEATHER)
ACTIVE_WIDTH = len(EFFECTS) * 3 + len(TYPES) + 1 + 3 + 7
EXTRA = ACTIVE_WIDTH * 2 + len(EXTRA_WEATHER)
CONTEXT = OLD_CONTEXT + EXTRA


def _effect(value):
    return identifier(value.removeprefix("move: ").removeprefix("ability: "))


def _types(text):
    values = tuple(text.split("/"))
    if not values or len(values) != len(set(values)) or any(t not in (*TYPES, "???") for t in values):
        raise ValueError("unsupported_public_current_type")
    # Native ??? is an explicitly typeless Pokemon, not Unknown.
    return tuple(t for t in values if t != "???")


def project_strategic_public(observation, catalog):
    """Active own/opponent records, bound to their current public appearance.

    None means Unknown; False means established absence. Switching ordinarily
    clears these volatiles, but silent Baton Pass/Shed Tail copying is explicitly
    unsupported (Unknown) instead of falsely declaring a clean incoming actor.
    Trap-source departures invalidate evidence; masks remain the sole legality
    authority. Supreme Overlord activation/count are separate public evidence.
    """
    role = "p1" if observation["side"] == "self" else "p2"
    active = {"p1": None, "p2": None}
    rows, preview = {}, {"p1": [], "p2": []}
    last_move = {}
    initialized = False
    # Reuse the maintained projection's weather authority; only its numerical
    # encoding changes. Terrain, screens/hazards, turn and Trick Room stay with
    # their existing owners and are not independently reduced here.
    weather = observation["state"]["field"]["weather"]
    if isinstance(weather, dict) and weather not in ({}, {"knowledge": "unknown"}):
        raise ValueError("malformed_public_weather_knowledge_v4")
    if not isinstance(weather, dict) and weather not in WEATHER:
        raise ValueError("unsupported_public_weather_v4")
    unsupported = set()

    def species_types(details):
        value = catalog["species"].get(identifier(details))
        return tuple(value["types"]) if value else None

    def blank(identity, details="", clean=False):
        return {"identity": identity, "details": details,
                "effects": {e: False if clean else None for e in EFFECTS},
                "types": None, "custom_types": False, "typing_observed": False,
                "species_change": False, "supreme_activation": None,
                "supreme_fallen": None, "roost_restore": None}

    for line in observation["public_history"]:
        p = line.split("|")
        if len(p) < 2:
            continue
        event, args = p[1], p[2:]
        if event == "start":
            rows.clear(); active = {"p1": None, "p2": None}; last_move.clear()
            initialized = True
        if event == "poke" and len(args) >= 2 and args[0] in preview:
            preview[args[0]].append(args[1])
        if event == "turn":
            for r in rows.values():
                if r["roost_restore"] is not None:
                    r["types"], r["roost_restore"] = r["roost_restore"], None
        if not args or args[0][:2] not in active or ": " not in args[0]:
            continue
        identity, side = args[0], args[0][:2]
        if event in {"switch", "drag"} and len(args) >= 2:
            # No silent pass-state reconstruction or mechanics interpreter.
            copied = last_move.get(side) in {"batonpass", "shedtail"}
            prior = active[side]
            if prior in rows:
                rows[prior] = blank(prior, rows[prior]["details"], clean=True)
            row = blank(identity, args[1], clean=initialized and not copied)
            # Absence of a trapping announcement does not rule out hidden auras.
            row["effects"]["trapped"] = None
            ambiguous = any(identifier(d).startswith("zoroark") for d in preview[side])
            row["types"] = None if ambiguous else species_types(args[1])
            if ambiguous:
                unsupported.add("unconfirmed_illusion_appearance_types")
            if copied:
                unsupported.add("silent_passed_volatiles")
                row["types"] = None  # Baton Pass can also carry typeadd.
            rows[identity], active[side] = row, identity
            last_move.pop(side, None)
            other = active["p2" if side == "p1" else "p1"]
            if other in rows and rows[other]["effects"]["trapped"]:
                rows[other]["effects"]["trapped"] = None
        row = rows.setdefault(identity, blank(identity))
        if event == "replace" and len(args) >= 2:
            # Public Illusion revelation renames an appearance, never a preview join.
            old = active[side]
            if old in rows and old != identity:
                row = deepcopy(rows[old]); row["identity"] = identity
                rows[identity] = row
            row["details"] = args[1]; active[side] = identity
            if not row["custom_types"]:
                row["types"] = species_types(args[1])
        if event in {"detailschange", "-formechange"} and len(args) >= 2:
            row["details"], row["types"] = args[1], species_types(args[1])
            row["custom_types"] = False
            row["species_change"] = True
        if event == "-transform" and len(args) >= 2:
            target = rows.get(args[1], {})
            row["types"] = target.get("types")
            row["custom_types"] = True
            row["typing_observed"] = True
        if event == "move" and len(args) >= 2:
            last_move[side] = identifier(args[1])
        if event in {"-start", "-end", "-activate", "cant", "-singleturn"} and len(args) >= 2:
            effect = _effect(args[1])
            if event in {"-start", "-end"} and effect in EFFECTS:
                row["effects"][effect] = event == "-start"
            if event == "-activate" and effect in {"trapped", "confusion"}:
                row["effects"][effect] = True
            if event == "cant" and effect == "recharge":
                row["effects"]["recharge"] = False
            if effect == "typechange":
                row["typing_observed"] = True
                if event == "-start" and len(args) >= 3:
                    # Reflect Type deliberately omits the type payload in native
                    # protocol. Do not manufacture it from the hidden target.
                    if args[2].startswith("["):
                        row["types"] = None
                        unsupported.add("typechange_without_public_type_payload")
                    else:
                        row["types"] = _types(args[2])
                    row["custom_types"] = True
                elif event == "-end":
                    row["types"], row["custom_types"] = species_types(row["details"]), False
            if effect == "typeadd" and event == "-start" and len(args) >= 3:
                added = _types(args[2])
                if row["types"] is None:
                    unsupported.add("typeadd_on_unknown_public_base")
                row["types"] = tuple(dict.fromkeys((*row["types"], *added))) if row["types"] is not None else None
                row["custom_types"] = True
                row["typing_observed"] = True
            if event == "-singleturn" and effect == "roost":
                row["roost_restore"] = row["types"]
                row["types"] = None
                row["typing_observed"] = True
                unsupported.add("in_turn_roost_typing")
            if event == "-activate" and effect == "supremeoverlord":
                row["supreme_activation"] = True
            if effect.startswith("fallen") and effect[6:] in {str(n) for n in range(1, 6)}:
                row["supreme_fallen"] = int(effect[6:]) if event == "-start" else None
        if event == "-mustrecharge":
            row["effects"]["recharge"] = True
        if event == "faint":
            rows[identity] = blank(identity, row["details"], clean=True)
            other = active["p2" if side == "p1" else "p1"]
            if other in rows and rows[other]["effects"]["trapped"]:
                rows[other]["effects"]["trapped"] = None

    own = active[role]
    # Own Illusion identity is known from this player's request, not opponent data.
    if own in rows and not rows[own]["custom_types"] and not rows[own]["typing_observed"]:
        own_request = next((r for r in observation["own_request"].get("side", {}).get("pokemon", []) if r.get("active")), None)
        if own_request and not rows[own]["species_change"]:
            rows[own]["types"] = species_types(own_request["details"])
    # Own authoritative request may establish trapping; maybeTrapped never does.
    request_active = observation["own_request"].get("active", [])
    if own in rows and request_active and request_active[0].get("trapped") is True:
        rows[own]["effects"]["trapped"] = True
    return {"schema_version": PROJECTION,
            "active": [rows.get(active[s], blank("")) for s in (role, "p2" if role == "p1" else "p1")],
            "weather": weather,
            "unsupported": sorted(unsupported)}


def _tristate(value):
    return [float(value is True), float(value is False), float(value is None)]


def strategic_features(projection):
    result = []
    for row in projection["active"]:
        for effect in EFFECTS:
            result += _tristate(row["effects"][effect])
        types = row["types"]
        result += [float(types is not None and t in types) for t in TYPES] + [float(types is not None)]
        result += _tristate(row["supreme_activation"])
        result += [float(row["supreme_fallen"] == n) for n in range(6)] + [float(row["supreme_fallen"] is None)]
    result += [float(projection["weather"] == w) for w in EXTRA_WEATHER]
    assert len(result) == EXTRA
    return np.asarray(result, dtype=np.float32)


class StrategicPublicCategoricalEncoder(RuntimeAbilityCategoricalEncoder):
    version = VERSION
    dimension = CONTEXT + 35 * ACTION

    def __init__(self, catalog):
        super().__init__(catalog)
        self.legacy = RuntimeAbilityCategoricalEncoder(self.catalog)
        self.feature_contract = {**self.feature_contract,
            "schema_version": "showdown-public-categorical-contract-v4", "version": VERSION,
            "context_dim": CONTEXT, "dimension": self.dimension,
            "observation_dimension": self.dimension,
            "strategic_projection": PROJECTION, "strategic_effects": list(EFFECTS),
            "strategic_layout": "self_active_then_opponent_active_tristates_current_types_supreme_evidence_then_extra_weather",
            "strategic_width": EXTRA, "active_width": ACTIVE_WIDTH,
            "strategic_tristate_order": ["known_active", "known_absent", "unknown"],
            "strategic_transport": "binary_presence_not_continuous_normalization",
            "strategic_active_binding": "ordered_self_and_opponent_current_public_appearance_not_preview_identity",
            "strategic_type_order": [*TYPES, "known_current_types"],
            "supreme_scope": "separate_public_activation_evidence_and_explicit_fallen_0_to_5_or_unknown_not_inferred",
            "switch_scope": "fresh_entry_reset_except_unknown_pass_state_and_unannounced_trapping",
            "weather": {"legacy_context_column_8": "snowscape_not_snow", "extra": list(EXTRA_WEATHER)},
            "type_scope": "current_public_types_separate_from_legacy_nominal_species_priors",
            "legacy_numeric_scope": "nominal_catalog_priors_preserved_weather_column8_corrected",
            "duration_scope": "not_encoded_no_hidden_extension_or_rng_inference",
            "transfer": "categorical_v3_weights_fresh_adam_new_columns_zero_native_dead_snow_column_zero",
            "compatibility": "separate_V4_shapes_V1_V2_V3_unchanged"}
        self.catalog_fingerprint = fingerprint(self.feature_contract)

    def project(self, observation):
        return project_strategic_public(observation, self.catalog)

    def encode(self, observation):
        old = self.legacy.encode(observation)  # original public boundary/transport
        projection = self.project(observation)
        # Correct pinned native 'Snowscape'. Historical V3 'snow' remains unchanged.
        old[8] = float(projection["weather"] == "snowscape")
        return np.concatenate((old[:OLD_CONTEXT], strategic_features(projection), old[OLD_CONTEXT:]))
