"""Opt-in public-history opponent; preference guard, never a legality oracle.

Two consecutive public failures plus confirmed own prerequisites are required.
No failure caused by a miss, immunity, unknown target interaction or future
choice is inferred. Existing scripted opponents and native masks are untouched.
"""
from collections import Counter
from functools import lru_cache
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_encoder import identifier

VERSION = "public_failure_aware_v1"


@lru_cache(maxsize=1)
def native_mega_items():
    # Pinned public item catalog exported from Dex; no opponent-item inference.
    import json
    from pathlib import Path
    from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
    data = json.loads((Path(__file__).resolve().parents[1] / "models/showdown_public_categories_v1/catalog.json").read_text())
    if data["engine_commit"] != SHOWDOWN_COMMIT or data["format_id"] != FORMAT_ID:
        raise ValueError("failure_guard_public_item_catalog_mismatch")
    return frozenset(data["mega_forms_by_item"])


@lru_cache(maxsize=1024)
def move_metadata(name):
    from poke_env.battle import Move
    m = Move(name, gen=9)
    return m.base_power, bool(m.heal), getattr(m.target, "name", "").lower()


def request_move(view, action):
    offset = next((o for o in (31, 27, 22, 18, 14, 10, 6) if action >= o), None)
    if action < 6 or action == 26 or offset is None:
        return None
    moves = view["own_request"].get("active", [{}])[0].get("moves", [])
    return moves[action - offset]["id"] if action - offset < len(moves) else None


def established_failures(view):
    """Only explicit own move/fail protocol, reset when that actor switches."""
    active = view["state"]["self_side"]["active_identity"]
    if not isinstance(active, str):
        return {}
    attempts = []
    for line in view.get("public_history", []):
        p = line.split("|")
        if len(p) < 3 or p[2] != active:
            continue
        if p[1] in {"switch", "drag", "replace", "detailschange", "-formechange"}:
            attempts = []
        elif p[1] in {"-damage", "-heal"}:
            attempts = [a for a in attempts if not (move_metadata(a[0])[1] and move_metadata(a[0])[2] in {"self", "allies"})]
        elif p[1] in {"-status", "-curestatus", "-ability", "-endability"}:
            attempts = [a for a in attempts if a[0] not in {"snore", "sleeptalk"}]
        elif p[1] in {"-item", "-enditem"}:
            attempts = [a for a in attempts if a[0] != "fling"]
        elif p[1] == "move" and len(p) > 3:
            # Called/automatic moves are not evidence about the requested slot.
            attempts.append([identifier(p[3]), None, any(x.startswith("[from]") for x in p[4:])])
        elif p[1] == "-fail" and attempts:
            attempts[-1][1] = p[3] if len(p) > 3 else "generic"
    row = view["state"]["self_side"]["pokemon"].get(active, {})
    ability, status, item = row.get("current_ability", {}), row.get("condition", {}), row.get("known_item", {})
    guards = {}
    for name in {a[0] for a in attempts}:
        recent = [a for a in attempts if a[0] == name][-2:]
        if len(recent) < 2 or any(a[1] is None or a[2] for a in recent):
            continue
        if name in {"snore", "sleeptalk"} and (status is None or isinstance(status, str) and status != "slp") and isinstance(ability, str) and ability != "comatose":
            guards[name] = "repeated_awake_sleep_move_non_comatose"
        elif name == "fling" and (item is None or isinstance(item, str) and item in native_mega_items()):
            guards[name] = "repeated_fling_confirmed_no_item_or_mega_stone"
        else:
            _, heal, target = move_metadata(name)
            if (heal and target in {"self", "allies"} and row.get("hp_fraction") == 1
                    and all(a[1] == "heal" for a in recent)):
                # A preference, not illegal healing or future-damage certainty.
                guards[name] = "repeated_full_hp_public_heal_failure"
    return guards


class PublicFailureAwareOpponent:
    kind = VERSION

    def __init__(self, seed=0, *, base=None):
        from hashlib import sha256
        from pathlib import Path
        self.base = base if base is not None else VisibleBaseline("max_power", seed)
        self.model_id = VERSION + ":" + sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest() + ":" + getattr(self.base, "model_id", "max_power")
        self.counts = Counter()
        self.last_key = None
        self.last_action = None

    def act(self, view):
        key = (view["episode_id"], view["revision"])
        if key == self.last_key:
            return self.last_action
        proposal = self.base.act(view)
        guards = established_failures(view)
        allowed = [i for i, legal in enumerate(view["action_mask"]) if legal]
        blocked = {i for i in allowed if request_move(view, i) in guards}
        alternatives = [i for i in allowed if i not in blocked]
        self.counts["public_decisions"] += 1
        self.counts["guard_opportunities"] += bool(blocked)
        self.counts["guarded_base_proposals"] += proposal in blocked
        action = proposal
        if proposal in blocked and alternatives:
            attacks = [i for i in alternatives if request_move(view, i) is not None]
            if attacks:
                # Reuse the baseline's nominal-power prior, not damage estimates.
                # Stable ordering prefers the baseline's native mega choice.
                action = max(attacks, key=lambda i: (move_metadata(request_move(view, i))[0], i >= 10, -i))
            else:
                action = min(alternatives)
            self.counts["changed_proposals"] += 1
            self.counts["avoided:" + guards[request_move(view, proposal)]] += 1
        self.counts["guarded_actions_selected"] += action in blocked
        self.counts["no_safe_alternative"] += bool(blocked and not alternatives)
        assert view["action_mask"][action]
        self.last_key, self.last_action = key, action
        return action

    def drain_counts(self):
        result = dict(self.counts)
        self.counts.clear()
        return result
