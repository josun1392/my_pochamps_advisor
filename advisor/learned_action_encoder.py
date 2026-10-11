"""Permutation-aware context/action features from one public policy view only."""

import numpy as np
from advisor.learned_encoder import PartialObservationEncoder, identifier, TYPES

VERSION = "showdown-learned-observation-v2"
CONTEXT = 321
ACTION = 140


class ActionObservationEncoder(PartialObservationEncoder):
    version = VERSION
    dimension = CONTEXT + 35 * ACTION

    def _own_row(self, own, pokemon):
        name = pokemon.get("ident", "").split(": ", 1)[-1]
        return next(
            (r for k, r in own["pokemon"].items() if k.split(": ", 1)[-1] == name), {}
        )

    def _move(self, move_id, row, other, native=None):
        native = native or {}
        move = self.catalog["moves"].get(identifier(move_id), {})
        types = self._species(row.get("details", "")).get("types", [])
        prior = (
            self.catalog["effectiveness"]
            .get(move.get("type"), {})
            .get(identifier(other.get("details", "")), 1)
        )
        return (
            [float(move.get("type") == t) for t in TYPES]
            + [
                float(move.get("category") == c)
                for c in ("Physical", "Special", "Status")
            ]
            + [
                min(move.get("power", 0) / 150, 2),
                move.get("accuracy", 0),
                move.get("priority", 0) / 5,
                float(move.get("type") in types),
                prior / 4,
                float(bool(move.get("heal"))),
                float(bool(move.get("pivot"))),
                float(bool(move.get("boost"))),
                native.get("pp", 0) / max(native.get("maxpp", 1), 1),
                float(bool(move)),
            ]
        )

    def encode(self, observation):
        legacy = super().encode(
            observation
        )  # validates channel and rejects privileged roots
        state = observation["state"]
        own = state["self_side"]
        opp = state["opponent_side"]
        request = observation["own_request"]
        other = (
            opp["pokemon"].get(opp["active_identity"], {})
            if isinstance(opp["active_identity"], str)
            else {}
        )
        roster = request.get("side", {}).get("pokemon", [])
        rows = [self._own_row(own, p) for p in roster]
        public = list(opp["pokemon"].values())[:3]
        pool = (
            lambda values, size: np.mean(values, axis=0).tolist()
            if values
            else [0.0] * size
        )
        context = (
            legacy[:142].tolist()
            + pool([self._row(p) for p in rows], 63)
            + pool([self._row(p) for p in public], 63)
        )
        context += pool(
            [
                [
                    float(t in self._species(p["details"]).get("types", []))
                    for t in TYPES
                ]
                for p in opp["preview"]
            ],
            18,
        )
        revealed = [
            self.catalog["moves"].get(identifier(m), {})
            for p in public
            for m in p.get("known_moves", [])
        ]
        context += pool(
            [[float(m.get("type") == t) for t in TYPES] for m in revealed], 18
        )
        recent = observation.get("public_history", observation["events"])[-16:]
        role = "p1" if observation["side"] == "self" else "p2"
        for side in (role, "p2" if role == "p1" else "p1"):
            for kind in ("move", "switch", "faint", "-damage", "-status", "-boost"):
                context.append(sum(f"|{kind}|{side}" in line for line in recent) / 16)
        active = next((i for i, p in enumerate(roster) if p.get("active")), 0)
        stats = lambda p: [
            p.get("stats", {}).get(s, 0) / 300
            for s in ("atk", "def", "spa", "spd", "spe")
        ]
        context += stats(roster[active] if roster else {})
        slots = request.get("active", [{}])[0].get("moves", [])
        features = []
        if any(observation["action_mask"][14:26]):
            raise ValueError("unsupported_champions_action_family")
        for index in range(35):
            move_slot = None
            mega = 0
            if 6 <= index < 14:
                move_slot = (index - 6) % 4
                mega = int(index >= 10)
            elif 27 <= index < 35:
                move_slot = (index - 27) % 4
                mega = 2 if index < 31 else 3
            switch = index < 6
            move = move_slot is not None
            p = (
                roster[index]
                if switch and index < len(roster)
                else roster[active]
                if move and roster
                else {}
            )
            row = self._own_row(own, p)
            if move and mega:
                form = request.get("active", [{}])[0].get("canMegaEvo")
                if isinstance(form, str):
                    row = {**row, "details": form}
            slot = slots[move_slot] if move and move_slot < len(slots) else {}
            moves = p.get("moves", [])
            typ = self._species(other.get("details", "")).get("types", [])
            defensive = [
                self.catalog["effectiveness"]
                .get(t, {})
                .get(identifier(row.get("details", "")), 1)
                / 4
                for t in typ
            ]
            action = [float(switch), float(move), float(index == 26)] + self._row(row)
            action += (
                self._move(slot.get("id", ""), row, other, slot) if move else [0.0] * 31
            )
            action += pool([self._move(m, row, other) for m in moves], 31)
            action += [float(mega == m) for m in range(4)] + stats(p)
            action += [
                max(defensive, default=0.25),
                sum(defensive) / len(defensive) if defensive else 0.25,
                float(observation["action_mask"][index]),
            ]
            assert len(action) == ACTION
            features += action
        assert len(context) == CONTEXT
        array = np.asarray(context + features, dtype=np.float32)
        if not np.all(np.isfinite(array)):
            raise ValueError("nonfinite_action_features")
        return array


def make_encoder(catalog, version):
    if version == PartialObservationEncoder.version:
        return PartialObservationEncoder(catalog)
    if version == VERSION:
        return ActionObservationEncoder(catalog)
    raise ValueError("unsupported_learning_encoder")
