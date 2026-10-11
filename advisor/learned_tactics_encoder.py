"""V3 public tactical features; all effects/choices still execute in Showdown.

Adds native move metadata and publicly announced side conditions to v2. No
hidden sets, ability assumptions, duration predictions or damage calculations.
"""

import json
from pathlib import Path
import numpy as np
from advisor.learned_action_encoder import (
    ActionObservationEncoder,
    CONTEXT as V2_CONTEXT,
    ACTION as V2_ACTION,
)
from advisor.learned_encoder import fingerprint, identifier
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID

VERSION = "showdown-learned-observation-v3"
SIDE_CONDITIONS = (
    "spikes",
    "toxicspikes",
    "stealthrock",
    "stickyweb",
    "reflect",
    "lightscreen",
    "auroraveil",
    "safeguard",
    "tailwind",
)
CONTEXT = V2_CONTEXT + 20
ACTION = V2_ACTION + 62
TACTICS_PATH = (
    Path(__file__).resolve().parents[1] / "models/showdown_tactics_v1/catalog.json"
)


def public_side_conditions(observation):
    """Absence is known only after the public battle-start event."""
    sides = {"p1": {}, "p2": {}}
    initialized = False
    for line in observation["public_history"]:
        parts = line.split("|")
        if len(parts) < 2:
            continue
        if parts[1] == "start":
            initialized = True
            sides = {"p1": {}, "p2": {}}
        elif parts[1] == "-swapsideconditions":
            sides["p1"], sides["p2"] = sides["p2"], sides["p1"]
        elif parts[1] in {"-sidestart", "-sideend"} and len(parts) >= 4:
            side = parts[2][:2]
            condition = identifier(parts[3].removeprefix("move: "))
            if side in sides and condition in SIDE_CONDITIONS:
                maximum = (
                    3
                    if condition == "spikes"
                    else 2
                    if condition == "toxicspikes"
                    else 1
                )
                sides[side][condition] = (
                    min(maximum, sides[side].get(condition, 0) + 1)
                    if parts[1] == "-sidestart"
                    else 0
                )
    role = "p1" if observation["side"] == "self" else "p2"
    return [
        value
        for side in (role, "p2" if role == "p1" else "p1")
        for value in (
            [
                sides[side].get(c, 0)
                / (3 if c == "spikes" else 2 if c == "toxicspikes" else 1)
                for c in SIDE_CONDITIONS
            ]
            + [float(initialized)]
        )
    ]


class TacticalObservationEncoder(ActionObservationEncoder):
    version = VERSION
    dimension = CONTEXT + 35 * ACTION

    def __init__(self, catalog):
        super().__init__(catalog)
        self.tactics = json.loads(TACTICS_PATH.read_text(encoding="utf-8"))
        if (
            self.tactics.get("schema_version") != "showdown-learning-tactics-v1"
            or self.tactics.get("engine_commit") != SHOWDOWN_COMMIT
            or self.tactics.get("format_id") != FORMAT_ID
        ):
            raise ValueError("incompatible_learning_tactics")
        self.catalog_fingerprint = fingerprint(
            {"base": self.catalog, "tactics": self.tactics}
        )

    def _tactic(self, move_id):
        move = self.tactics["moves"].get(identifier(move_id), {})
        boosts = (
            move.get("boosts", {})
            if move.get("target") == "self"
            else move.get("self_boosts", {})
        )
        return (
            [
                float(move.get("status") == s)
                for s in ("brn", "par", "slp", "frz", "psn", "tox")
            ]
            + [
                boosts.get(s, 0) / 6
                for s in ("atk", "def", "spa", "spd", "spe", "accuracy", "evasion")
            ]
            + [float(move.get("side_condition") == s) for s in SIDE_CONDITIONS]
            + [float(move.get("volatile") == "protect")]
            + [move.get(s, 0) for s in ("heal", "drain", "recoil")]
            + [
                float(bool(move.get(s)))
                for s in ("phaze", "contact", "removes_hazards")
            ]
            + [float(move.get("target") == "self"), float(bool(move))]
        )

    def encode(self, observation):
        base = super().encode(observation)
        slots = observation["own_request"].get("active", [{}])[0].get("moves", [])
        actions = base[V2_CONTEXT:].reshape(35, V2_ACTION)
        roster = observation["own_request"].get("side", {}).get("pokemon", [])
        active = next((i for i, p in enumerate(roster) if p.get("active")), 0)
        move_pools = [
            np.mean([self._tactic(m) for m in p.get("moves", [])], axis=0).tolist()
            if p.get("moves")
            else [0.0] * 31
            for p in roster
        ]
        extra = []
        for index in range(35):
            slot = (
                (index - 6) % 4
                if 6 <= index < 14
                else (index - 27) % 4
                if 27 <= index < 35
                else None
            )
            move = (
                slots[slot].get("id", "")
                if slot is not None and slot < len(slots)
                else ""
            )
            target = (
                index
                if index < 6 and index < len(roster)
                else active
                if slot is not None and roster
                else None
            )
            extra.append(
                self._tactic(move)
                + (move_pools[target] if target is not None else [0.0] * 31)
            )
        # Legal indicator stays last for the masked critic pooling contract.
        rows = np.concatenate(
            (actions[:, :-1], np.asarray(extra, dtype=np.float32), actions[:, -1:]),
            axis=1,
        )
        result = np.concatenate(
            (
                base[:V2_CONTEXT],
                np.asarray(public_side_conditions(observation), dtype=np.float32),
                rows.flatten(),
            )
        )
        assert result.shape == (self.dimension,)
        return result.astype(np.float32, copy=False)
