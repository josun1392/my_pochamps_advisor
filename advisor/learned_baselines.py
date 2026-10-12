"""Offline reuse of poke-env scripted opponents on player-visible native data.

No Player constructor/client/server is created. Request-order translation avoids
poke-env's persistent roster-order mask mismatch. Baselines are Gen9 heuristics,
not Champions exact probability consumers.
"""

import logging
import random
from copy import copy
from threading import RLock

_RANDOM_LOCK = RLock()


class VisibleBaseline:
    def __init__(self, kind="random", seed=0):
        if kind not in {
            "random",
            "max_power",
            "heuristic",
            "champions_heuristic",
            "tactical_heuristic",
        }:
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
        from poke_env.battle import Move, Pokemon
        from poke_env.player import MaxBasePowerPlayer, SimpleHeuristicsPlayer

        if self.episode != observation["episode_id"]:
            from advisor.learned_champions_metadata import make_champions_battle

            self.battle = make_champions_battle(
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
            SimpleHeuristicsPlayer
            if self.kind in {"heuristic", "champions_heuristic", "tactical_heuristic"}
            else MaxBasePowerPlayer
        )
        player._format = "gen9championsbssregmc"
        # Force-switch/wait never consults a future queued opponent choice.
        if observation["request_state"] == "switch" and self.battle.available_switches:
            choices = self.battle.available_switches
            if (
                self.kind in {"heuristic", "champions_heuristic", "tactical_heuristic"}
                and self.battle.opponent_active_pokemon
            ):
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
                    order = (
                        self._tactical_choice(player)
                        if self.kind == "tactical_heuristic"
                        else self._champions_choice(player)
                        if self.kind == "champions_heuristic"
                        else player.choose_move(self.battle).order
                    )
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

    def _tactical_choice(self, player):
        """New experimental teacher; old benchmark policies retain their semantics.

        Reuses public poke-env matchup priors. These thresholds are heuristic,
        not damage/KO guarantees. Corrects the upstream Target enum setup gate.
        """
        battle = self.battle
        own, other = battle.active_pokemon, battle.opponent_active_pokemon
        if own and other:
            matchup = player._estimate_matchup(own, other)
            if battle.available_switches:
                best = max(
                    battle.available_switches,
                    key=lambda p: player._estimate_matchup(p, other),
                )
                score = player._estimate_matchup(best, other)
                if matchup < -1 and score > 0 and score - matchup > 2:
                    return best
            if 0 < own.current_hp_fraction < 0.65 and matchup >= -0.3:
                heal = next(
                    (
                        m
                        for m in battle.available_moves
                        if m.heal and getattr(m.target, "name", "").lower() == "self"
                    ),
                    None,
                )
                if heal:
                    return heal
            # Do not set up when finishing a weakened target or after a revealed
            # reset/phaze/Unaware; hidden moves and abilities are never queried.
            revealed_reset = any(
                m in other.moves for m in ("haze", "whirlwind", "roar", "clearsmog")
            )
            if (
                own.current_hp_fraction > 0.75
                and other.current_hp_fraction > 0.4
                and matchup > 0
                and not revealed_reset
                and other.ability != "unaware"
            ):
                for move in battle.available_moves:
                    positive = [s for s, n in (move.boosts or {}).items() if n > 0]
                    if (
                        positive
                        and sum(move.boosts.values()) >= 2
                        and getattr(move.target, "name", "").lower() == "self"
                        and all(own.boosts[s] < 2 for s in positive)
                    ):
                        if (
                            "def" in positive
                            and other.base_stats["spa"] > other.base_stats["atk"]
                        ):
                            continue
                        return move
        return self._champions_choice(player)

    def _champions_choice(self, player):
        """Experimental public tactics around poke-env's maintained baseline.

        HP thresholds are heuristic choices, never exact outcome guarantees.
        Opponent species base stats are public; its actual build is unavailable.
        """
        battle = self.battle
        own, other = battle.active_pokemon, battle.opponent_active_pokemon
        if own and other and battle.available_moves:
            matchup = player._estimate_matchup(own, other)
            if 0 < own.current_hp_fraction < 0.45 and matchup > -0.5:
                heal = next(
                    (
                        m
                        for m in battle.available_moves
                        if m.heal and getattr(m.target, "name", "").lower() == "self"
                    ),
                    None,
                )
                if heal:
                    return heal
            if not other.status and own.current_hp_fraction > 0.55 and matchup >= 0:
                for move in battle.available_moves:
                    status = getattr(move.status, "name", "").lower()
                    types = {getattr(t, "name", "").lower() for t in other.types}
                    if (
                        status == "brn"
                        and "fire" not in types
                        and other.base_stats["atk"] > other.base_stats["spa"]
                    ):
                        return move
                    if (
                        status == "par"
                        and not types & {"electric", "ground"}
                        and other.base_stats["spe"] > own.base_stats["spe"]
                    ):
                        return move
                    if (
                        status == "tox"
                        and not types & {"poison", "steel"}
                        and own.base_stats["def"] + own.base_stats["spd"] >= 200
                    ):
                        return move
            # The upstream six-member heuristic overcounts hidden reserves in
            # Champions bring-six/pick-three. Suppress repeated late hazards.
            if any(p.fainted for p in battle.opponent_team.values()):
                proxy = copy(battle)
                choices = [
                    m
                    for m in battle.available_moves
                    if m.id not in {"spikes", "toxicspikes", "stealthrock", "stickyweb"}
                ]
                if choices:
                    proxy._available_moves = choices
                    return player.choose_move(proxy).order
        return player.choose_move(battle).order
