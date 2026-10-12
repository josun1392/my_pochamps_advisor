"""Experimental V4 encoder: public interactions, never mechanics predictions.

Observed order is a historical sample, not a true-speed guarantee. Healing
gap uses current HP and nominal native metadata, not future damage/weather
calculations. Native legality remains unchanged, including full-HP healing.
"""

import numpy as np
from advisor.learned_encoder import identifier, known, fingerprint
from advisor.learned_tactics_encoder import (
    TacticalObservationEncoder,
    CONTEXT as OLD_CONTEXT,
    ACTION as OLD_ACTION,
)

VERSION = "showdown-learned-observation-v4"
CONTEXT = OLD_CONTEXT + 13
ACTION = OLD_ACTION + 30


def public_history_summary(observation, catalog, tactics):
    own = "p1" if observation["side"] == "self" else "p2"
    other = "p2" if own == "p1" else "p1"
    own_id = observation["state"]["self_side"]["active_identity"]
    other_id = observation["state"]["opponent_side"]["active_identity"]
    own_id = own_id if isinstance(own_id, str) else None
    other_id = other_id if isinstance(other_id, str) else None
    hp = {}
    damage, damage_known = 0, False
    last_moves = {}
    last_turn = {}
    turn = 0
    recent = []
    frame, pair = [], []
    trick, initialized = False, False
    failed = False
    for line in observation["public_history"]:
        p = line.split("|")
        if len(p) < 2:
            continue
        event = p[1]
        if event == "start":
            initialized = True
        if event == "turn":
            if len(frame) == 2 and {r[0][:2] for r in frame} == {own, other}:
                pair = frame
            frame = []
            turn = int(p[2])
        if (
            event in {"-fieldstart", "-fieldend"}
            and len(p) > 2
            and identifier(p[2].removeprefix("move: ")) == "trickroom"
        ):
            trick = event == "-fieldstart"
        if event == "move" and len(p) > 3:
            actor, move = p[2], identifier(p[3])
            last_moves[actor] = move
            last_turn[actor] = turn
            frame.append((actor, move))
            if actor == own_id:
                recent.append(move)
                failed = False
        if event == "-fail" and len(p) > 2 and p[2] == own_id:
            failed = True
        if event in {"switch", "drag", "-damage", "-heal"} and len(p) > (
            4 if event in {"switch", "drag"} else 3
        ):
            actor = p[2]
            condition = p[4] if event in {"switch", "drag"} else p[3]
            health = condition.split()[0]
            if "/" in health:
                try:
                    a, b = health.split("/")
                    fraction = float(a) / float(b)
                except (ValueError, ZeroDivisionError):
                    continue
                if actor == own_id and event == "-damage":
                    damage_known = actor in hp
                    damage = max(0, hp.get(actor, fraction) - fraction)
                hp[actor] = fraction
    valid_pair = len(pair) == 2 and {r[0] for r in pair} == {own_id, other_id}
    first = valid_pair and pair[0][0] == own_id
    priorities_known = valid_pair and all(
        "priority" in catalog["moves"].get(move, {}) for _, move in pair
    )
    equal_priority = priorities_known and catalog["moves"].get(pair[0][1], {}).get(
        "priority", 0
    ) == catalog["moves"].get(pair[1][1], {}).get("priority", 0)
    last = last_moves.get(own_id, "")
    foe_move = catalog["moves"].get(last_moves.get(other_id, ""), {})
    healing = (
        sum(bool(tactics["moves"].get(m, {}).get("heal")) for m in recent[-4:]) / 4
    )
    setup = (
        sum(
            bool(tactics["moves"].get(m, {}).get("boosts"))
            and tactics["moves"].get(m, {}).get("target") == "self"
            for m in recent[-4:]
        )
        / 4
    )
    values = [
        float(valid_pair),
        float(first),
        float(equal_priority),
        float(failed),
        float(last in {"protect", "detect"}),
        float(foe_move.get("category") in {"Physical", "Special"}),
        float(damage_known),
        damage,
        healing,
        setup,
        float(trick),
        float(initialized),
        float(
            last == "wish"
            and observation["turn"] - last_turn.get(own_id, -100) == 1
            and not failed
        ),
    ]
    return values, last


class PublicInteractionEncoder(TacticalObservationEncoder):
    version = VERSION
    dimension = CONTEXT + 35 * ACTION

    def __init__(self, catalog):
        super().__init__(catalog)
        self.catalog_fingerprint = fingerprint(
            {
                "parent": self.catalog_fingerprint,
                "contract": VERSION,
                "context_extra": 13,
                "action_extra": 30,
            }
        )

    def encode(self, observation):
        base = super().encode(observation)
        rows = base[OLD_CONTEXT:].reshape(35, OLD_ACTION)
        history, last = public_history_summary(observation, self.catalog, self.tactics)
        state = observation["state"]
        own = (
            state["self_side"]["pokemon"].get(state["self_side"]["active_identity"], {})
            if isinstance(state["self_side"]["active_identity"], str)
            else {}
        )
        other = (
            state["opponent_side"]["pokemon"].get(
                state["opponent_side"]["active_identity"], {}
            )
            if isinstance(state["opponent_side"]["active_identity"], str)
            else {}
        )
        hp = own.get("hp_fraction", {})
        gap = 1 - float(hp) if known(hp) else 0
        status = other.get("condition", {})
        slots = observation["own_request"].get("active", [{}])[0].get("moves", [])
        extra = []
        for i in range(35):
            slot = (
                (i - 6) % 4 if 6 <= i < 14 else (i - 27) % 4 if 27 <= i < 35 else None
            )
            move = (
                slots[slot].get("id", "")
                if slot is not None and slot < len(slots)
                else ""
            )
            t = self._tactic(move)
            heal, protect, status_move = t[23], t[22], float(any(t[:6]))
            switch = float(i < 6)
            target_hp = rows[i, 27]  # kind3 + species/types24; HP is index27.
            interactions = [
                heal * gap,
                heal * float(known(hp) and hp == 1),
                heal * float(history[3] and move == last),
                heal * float(history[0] and not history[1] and history[2]),
            ]
            interactions += [
                rows[i, 39 + j] * t[6 + j] for j in range(7)
            ]  # kind3 + row stage offset36.
            interactions += [
                protect * history[4],
                protect * history[5],
                status_move * float(known(status) and status is not None),
                status_move * float(not known(status)),
                float(bool(self.catalog["moves"].get(move, {}).get("pivot"))) * gap,
                switch * (target_hp - float(hp) if known(hp) else 0),
                switch * (rows[i, 137] - rows[6, 137]),
                switch * (rows[i, 138] - rows[6, 138]),
            ]
            interactions += [switch * x for x in base[321:330]]
            interactions += [float(bool(move) and move == last)]
            interactions += [protect * history[12]]
            assert len(interactions) == 30
            extra.append(interactions)
        augmented = np.concatenate(
            (rows[:, :-1], np.asarray(extra, dtype=np.float32), rows[:, -1:]), axis=1
        )
        result = np.concatenate(
            (
                base[:OLD_CONTEXT],
                np.asarray(history, dtype=np.float32),
                augmented.flatten(),
            )
        )
        assert result.shape == (self.dimension,)
        return result.astype(np.float32, copy=False)
