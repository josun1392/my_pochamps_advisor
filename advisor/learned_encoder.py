"""Versioned fixed features from one policy-visible observation and public Dex.

No simulator/checkpoint/scenario access. Type priors are public type-only facts,
not damage estimates, hidden ability assumptions or exact outcome evidence.
"""

from hashlib import sha256
import json
from pathlib import Path
import re
import numpy as np
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID

ENCODER_VERSION = "showdown-learned-observation-v1"
TYPES = (
    "Normal",
    "Fire",
    "Water",
    "Electric",
    "Grass",
    "Ice",
    "Fighting",
    "Poison",
    "Ground",
    "Flying",
    "Psychic",
    "Bug",
    "Rock",
    "Ghost",
    "Dragon",
    "Dark",
    "Steel",
    "Fairy",
)
STATUS = (None, "brn", "par", "slp", "frz", "psn", "tox")
STATS = ("hp", "atk", "def", "spa", "spd", "spe")


def identifier(value):
    return re.sub(r"[^a-z0-9]", "", str(value).split(",")[0].lower())


def known(value):
    return not isinstance(value, dict)


def fingerprint(value):
    return sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


class PartialObservationEncoder:
    version = ENCODER_VERSION
    dimension = 787

    def __init__(self, catalog):
        self.catalog = (
            json.loads(Path(catalog).read_text(encoding="utf-8"))
            if isinstance(catalog, (str, Path))
            else catalog
        )
        if (
            self.catalog.get("schema_version") != "showdown-learning-catalog-v1"
            or self.catalog.get("engine_commit") != SHOWDOWN_COMMIT
            or self.catalog.get("format_id") != FORMAT_ID
        ):
            raise ValueError("incompatible_learning_catalog")
        self.catalog_fingerprint = fingerprint(self.catalog)

    def _species(self, details):
        key = identifier(details)
        result = self.catalog["species"].get(key, {})
        if key and not result and self.catalog.get("legal_domain_version"):
            raise ValueError("species_outside_full_domain_public_catalog")
        return result

    def coverage(self, observation):
        """Public identifiers only; classify old catalog gaps without fabricating facts."""
        details = []
        for side in ("self_side", "opponent_side"):
            public = observation["state"][side]
            details.extend(p.get("details", "") for p in public["preview"])
            details.extend(p.get("details", "") for p in public["pokemon"].values())
        missing = sorted(
            {
                identifier(p)
                for p in details
                if p and identifier(p) not in self.catalog["species"]
            }
        )
        return {
            "schema_version": "showdown-public-catalog-coverage-v1",
            "missing_species": missing,
            "catalog_fingerprint": self.catalog_fingerprint,
        }

    def _row(self, row):
        species = self._species(row.get("details", ""))
        result = [species.get("base_stats", {}).get(s, 0) / 255 for s in STATS]
        result += [float(t in species.get("types", [])) for t in TYPES]
        hp, fainted, status = (
            row.get("hp_fraction", {}),
            row.get("fainted", {}),
            row.get("condition", {}),
        )
        result += [
            float(hp) if known(hp) else 0,
            float(known(hp)),
            float(fainted) if known(fainted) else 0,
            float(known(fainted)),
        ]
        result += [float(known(status) and status == s) for s in STATUS] + [
            float(not known(status))
        ]
        result += [
            float(row.get("stat_stages", {}).get(s, 0)) / 6
            for s in ("atk", "def", "spa", "spd", "spe", "accuracy", "evasion")
        ]
        for key in ("known_item", "current_ability"):
            value = row.get(key, {})
            # Explicit absence and Unknown remain different; hashes are public revelations only.
            result += [float(known(value)), float(value is None)]
            bucket = (
                int(sha256(str(value).encode()).hexdigest()[:8], 16) % 8
                if known(value) and value
                else -1
            )
            result += [float(bucket == i) for i in range(8)]
        return result

    def encode(self, observation):
        if (
            observation.get("schema_version") != "showdown-policy-observation-v1"
            or observation.get("action_schema_version") != "showdown-policy-actions-v1"
            or observation.get("interpretation")
            != "hypothetical_player_visible_observation_not_live_truth"
        ):
            raise ValueError("policy_visible_observation_required")
        if any(
            k in observation
            for k in (
                "native_state",
                "seed",
                "checkpoint",
                "scenario",
                "teams",
                "queue",
            )
        ):
            raise ValueError("privileged_truth_is_not_policy_input")
        state, request = observation["state"], observation["own_request"]
        own, opp = state["self_side"], state["opponent_side"]
        active = (
            own["pokemon"].get(own["active_identity"], {})
            if isinstance(own["active_identity"], str)
            else {}
        )
        other = (
            opp["pokemon"].get(opp["active_identity"], {})
            if isinstance(opp["active_identity"], str)
            else {}
        )
        result = [min(observation["turn"] / 100, 1)]
        result += [
            float(observation["request_state"] == phase)
            for phase in ("move", "switch", "ended")
        ]
        for field, values in (
            ("weather", (None, "sunnyday", "raindance", "sandstorm", "snow")),
            (
                "terrain",
                (
                    None,
                    "electricterrain",
                    "grassyterrain",
                    "mistyterrain",
                    "psychicterrain",
                ),
            ),
        ):
            value = state["field"][field]
            result += [float(known(value) and value == v) for v in values] + [
                float(not known(value))
            ]
        result += self._row(active) + self._row(other)
        for i in range(3):
            mons = request.get("side", {}).get("pokemon", [])
            if i < len(mons):
                name = mons[i]["ident"].split(": ", 1)[1]
                row = next(
                    (
                        r
                        for key, r in own["pokemon"].items()
                        if key.split(": ", 1)[1] == name
                    ),
                    {},
                )
            else:
                row = {}
            result += self._row(row)
        observed = list(opp["pokemon"].values())[:3]
        for i in range(3):
            result += self._row(observed[i] if i < len(observed) else {})
        for i in range(6):
            details = opp["preview"][i]["details"] if i < len(opp["preview"]) else ""
            result += [
                float(t in self._species(details).get("types", [])) for t in TYPES
            ]
        slots = request.get("active", [{}])[0].get("moves", [])
        own_types = self._species(active.get("details", "")).get("types", [])
        for i in range(4):
            native = slots[i] if i < len(slots) else {}
            move = self.catalog["moves"].get(identifier(native.get("id", "")), {})
            result += [float(move.get("type") == t) for t in TYPES]
            result += [
                float(move.get("category") == c)
                for c in ("Physical", "Special", "Status")
            ]
            prior = (
                self.catalog["effectiveness"]
                .get(move.get("type"), {})
                .get(identifier(other.get("details", "")), 1)
            )
            result += [
                min(move.get("power", 0) / 150, 2),
                move.get("accuracy", 0),
                move.get("priority", 0) / 5,
                float(move.get("type") in own_types),
                prior / 4,
                float(bool(move.get("heal"))),
                float(bool(move.get("pivot"))),
                float(bool(move.get("boost"))),
                native.get("pp", 0) / max(native.get("maxpp", 1), 1),
                float(bool(move)),
            ]
        result += observation["action_mask"]
        array = np.asarray(result, dtype=np.float32)
        if not np.all(np.isfinite(array)):
            raise ValueError("nonfinite_policy_features")
        return array
