"""Observable affordances, never oracle optimal-action labels or hidden damage."""

from poke_env.battle import Move
from poke_env.player import SimpleHeuristicsPlayer
from advisor.learned_baselines import VisibleBaseline


def action_class(observation, action):
    if action == 26:
        return "wait"
    if action < 6:
        return "replacement" if observation["request_state"] == "switch" else "switch"
    slot = action - (
        31
        if action >= 31
        else 27
        if action >= 27
        else 22
        if action >= 22
        else 18
        if action >= 18
        else 14
        if action >= 14
        else 10
        if action >= 10
        else 6
    )
    moves = observation["own_request"].get("active", [{}])[0].get("moves", [])
    if slot >= len(moves):
        raise ValueError("action_request_slot_mismatch")
    m = Move(moves[slot]["id"], gen=9)
    target = getattr(m.target, "name", "").lower()
    if m.heal and target == "self":
        return "recovery"
    if m.boosts and any(n > 0 for n in m.boosts.values()) and target == "self":
        return "setup"
    if m.id in {
        "protect",
        "detect",
        "endure",
        "substitute",
        "wideguard",
        "kingsshield",
    }:
        return "defense"
    return (
        "attack"
        if m.category.name.lower() in {"physical", "special"}
        else "status_or_field"
    )


class TacticalDiagnostics:
    def __init__(self):
        self.parser = VisibleBaseline("max_power")
        self.player = object.__new__(SimpleHeuristicsPlayer)

    def describe(self, observation, action):
        category = action_class(observation, action)
        self.parser.act(observation)  # Own request + public log only.
        battle = self.parser.battle
        own, other = battle.active_pokemon, battle.opponent_active_pokemon
        available = {
            action_class(observation, i)
            for i, legal in enumerate(observation["action_mask"])
            if legal
        }
        if not own or not other or observation["request_state"] != "move":
            return {"selected": category, "available": sorted(available)}
        matchup = self.player._estimate_matchup(own, other)
        best = max(
            (
                self.player._estimate_matchup(p, other)
                for p in battle.available_switches
            ),
            default=matchup,
        )
        return {
            "selected": category,
            "available": sorted(available),
            "hp_band": "injured" if own.current_hp_fraction < 0.65 else "healthy",
            "public_type_prior": "unfavorable"
            if matchup < -1
            else "favorable"
            if matchup > 0
            else "neutral",
            "better_bench_prior": best > 0 and best - matchup > 2,
        }
