"""Coordinator-only public affordance/execution counters, never reward/labels."""
from collections import Counter
from functools import lru_cache
from advisor.learned_failure_opponent import established_failures, move_metadata, request_move

DEFENSE = {"protect", "detect", "endure", "substitute", "wideguard", "kingsshield", "spikyshield", "banefulbunker", "obstruct", "silktrap", "burningbulwark"}


def recovery(name):
    if not name:
        return False
    _, heal, target = move_metadata(name)
    return heal and target in {"self", "allies"} or name in {"rest", "wish"}


@lru_cache(maxsize=1024)
def public_move_families(name):
    """Descriptive overlapping public move classes, not rewards or action labels."""
    from poke_env.battle import Move
    move = Move(name, gen=9)
    return {
        "attack": move.category.name.lower() in {"physical", "special"},
        "setup": bool(move.boosts and any(v > 0 for v in move.boosts.values())
                      and getattr(move.target, "name", "").lower() == "self"),
        "status_move": move.category.name.lower() == "status",
    }


class PublicDecisionMetrics:
    def __init__(self):
        self.counts = Counter()
        self.previous_switch = False

    def decision(self, view, action):
        self.counts["joint_requests"] += 1
        if view["action_mask"][26]:
            return
        if view["request_state"] == "switch":
            self.counts["replacement"] += 1
            self.previous_switch = False
            return
        self.counts["battle_action_decisions"] += 1
        legal = [i for i, x in enumerate(view["action_mask"]) if x]
        moves = {request_move(view, i) for i in legal} - {None}
        name = request_move(view, action)
        row = view["state"]["self_side"]
        active = row["pokemon"].get(row["active_identity"], {}) if isinstance(row["active_identity"], str) else {}
        hp = active.get("hp_fraction")
        has_heal = any(recovery(m) for m in moves)
        has_defense = bool(moves & DEFENSE)
        switch = action < 6
        self.counts["switch_available"] += any(i < 6 for i in legal)
        self.counts["voluntary_switch"] += switch
        self.counts["consecutive_voluntary_switch"] += switch and self.previous_switch
        self.previous_switch = switch
        self.counts["recovery_available"] += has_heal
        self.counts["recovery_selected"] += recovery(name)
        injured = has_heal and isinstance(hp, (int, float)) and hp < .65
        self.counts["injured_recovery_available"] += injured
        self.counts["injured_recovery_selected"] += injured and recovery(name)
        self.counts["defense_available"] += has_defense
        self.counts["defense_selected"] += name in DEFENSE
        for family in ("attack", "setup", "status_move"):
            self.counts[family + "_available"] += any(public_move_families(m)[family] for m in moves)
            self.counts[family + "_selected"] += bool(name and public_move_families(name)[family])
        guards = established_failures(view)
        self.counts["established_ineffective_available"] += bool(moves & guards.keys())
        self.counts["established_ineffective_selected"] += name in guards

    def outcome(self, view, events):
        role = "p1" if view["side"] == "self" else "p2"
        for line in events:
            p = line.split("|")
            if len(p) > 2 and p[2].startswith(role):
                if p[1] == "-fail":
                    self.counts["native_public_fail"] += 1
                    self.counts["native_heal_fail"] += len(p) > 3 and p[3] == "heal"

    def drain_counts(self):
        result = dict(self.counts)
        self.counts.clear()
        return result
