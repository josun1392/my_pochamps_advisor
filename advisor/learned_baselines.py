"""Offline reuse of poke-env scripted opponents on player-visible native data.

No Player constructor/client/server is created. Request-order translation avoids
poke-env's persistent roster-order mask mismatch. Baselines are Gen9 heuristics,
not Champions exact probability consumers.
"""

import logging
import random
from threading import RLock

_RANDOM_LOCK = RLock()


class VisibleBaseline:
    def __init__(self, kind="random", seed=0):
        if kind not in {"random", "max_power", "heuristic"}:
            raise ValueError("invalid_baseline")
        self.kind, self.rng, self.battle, self.episode, self.revision = (
            kind,
            random.Random(seed),
            None,
            None,
            None,
        )
        self.cursor = 0

    def act(self, observation):
        allowed = [i for i, value in enumerate(observation["action_mask"]) if value]
        if not allowed:
            raise ValueError("no_policy_action")
        if self.kind == "random":
            return self.rng.choice(allowed)
        from poke_env.battle import Battle, Move, Pokemon
        from poke_env.player import MaxBasePowerPlayer, SimpleHeuristicsPlayer

        if self.episode != observation["episode_id"]:
            self.battle = Battle(
                "offline-policy",
                "self" if observation["side"] == "self" else "opponent",
                logging.getLogger("offline-poke-baseline"),
                9,
            )
            self.episode, self.revision, self.cursor = (
                observation["episode_id"],
                None,
                0,
            )
        if self.revision != observation["revision"]:
            events = observation["events"]
            if "public_history" in observation:
                events = observation["public_history"][self.cursor :]
                self.cursor = len(observation["public_history"])
            for line in events:
                self.battle.parse_message(line.split("|"))
            self.battle.parse_request(observation["own_request"])
            self.revision = observation["revision"]
        if allowed == [26]:
            return 26
        player = object.__new__(
            SimpleHeuristicsPlayer if self.kind == "heuristic" else MaxBasePowerPlayer
        )
        player._format = "gen9championsbssregmc"
        # Force-switch/wait never consults a future queued opponent choice.
        if observation["request_state"] == "switch" and self.battle.available_switches:
            choices = self.battle.available_switches
            if self.kind == "heuristic" and self.battle.opponent_active_pokemon:
                order = max(
                    choices,
                    key=lambda p: player._estimate_matchup(
                        p, self.battle.opponent_active_pokemon
                    ),
                )
            else:
                order = choices[self.rng.randrange(len(choices))]
        else:
            # Existing baseline fallback uses Python global random; isolate/restore
            # it so opponent decisions are reproducible and evaluation independent.
            with _RANDOM_LOCK:
                saved = random.getstate()
                random.setstate(self.rng.getstate())
                try:
                    order = player.choose_move(self.battle).order
                finally:
                    self.rng.setstate(random.getstate())
                    random.setstate(saved)
        request = observation["own_request"]
        if isinstance(order, Move):
            slots = request.get("active", [{}])[0].get("moves", [])
            matches = [6 + i for i, move in enumerate(slots) if move["id"] == order.id]
            if matches:
                base = matches[0]
                mega = [
                    offset + base - 6
                    for offset in (10, 27, 31)
                    if observation["action_mask"][offset + base - 6]
                ]
                return mega[0] if mega else base
        elif isinstance(order, Pokemon):
            for i, pokemon in enumerate(request.get("side", {}).get("pokemon", [])):
                native = self.battle.team.get(pokemon["ident"])
                if native is order and i in allowed:
                    return i
        return self.rng.choice(allowed)
