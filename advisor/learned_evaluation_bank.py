"""Hash-bound, coordinator-only evaluation cases; never policy features.

Native legality is established by the bank builder. Loading trusted JSON checks
identity/partition integrity and never substitutes a final bank for validation.
"""

from copy import deepcopy
from hashlib import sha256
import json
import random
from pathlib import Path
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID


class EvaluationCaseBank:
    def __init__(self, path, expected_sha256, *, scope, panel=None):
        raw = Path(path).read_bytes()
        if sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("evaluation_bank_hash_mismatch")
        bank = json.loads(raw)
        if (
            bank.get("schema_version") != "showdown-experimental-evaluation-bank-v1"
            or bank.get("scope") != scope
            or scope not in {"validation", "test"}
            or bank.get("engine_commit") != SHOWDOWN_COMMIT
            or bank.get("format_id") != FORMAT_ID
            or bank.get("native_validated") is not True
        ):
            raise ValueError("evaluation_bank_contract_mismatch")
        panels = bank.get("panels", {})
        if not panels or len(panels) > 3 or any(
            not isinstance(teams, list) or not 1 <= len(teams) <= 4096
            or any(not isinstance(t, list) or len(t) != 6 for t in teams)
            for teams in panels.values()
        ):
            raise ValueError("bounded_evaluation_bank_required")
        if panel is not None and panel not in panels:
            raise ValueError("unknown_evaluation_panel")
        self.bank, self.scope, self.panel = bank, scope, panel
        self.identity = {
            "schema_version": bank["schema_version"], "sha256": expected_sha256,
            "scope": scope, "panels": [panel] if panel else sorted(panels),
            "engine_commit": SHOWDOWN_COMMIT,
            "native_validation_scope": "trusted_builder_attestation_and_content_binding",
        }

    def __call__(self, split, index):
        if split != self.scope or type(index) is not int or index < 0:
            raise ValueError("evaluation_partition_access_denied")
        names = [self.panel] if self.panel else sorted(self.bank["panels"])
        panel = names[index % len(names)]
        rng = random.Random(int.from_bytes(sha256(
            f"{self.identity['sha256']}:{split}:{panel}:{index}".encode()
        ).digest(), "big"))
        pool = self.bank["panels"][panel]
        teams = {side: deepcopy(rng.choice(pool)) for side in ("self", "opponent")}
        preview = {side: rng.sample(range(1, 7), 3) for side in teams}
        if self.bank.get("forced_first_slot"):
            preview["self"] = [1, *rng.sample(range(2, 7), 2)]
        return {
            "scenario_id": f"{split}:{panel}:{index}", "teams": teams,
            "preview": preview, "seed": [rng.randrange(65536) for _ in range(4)],
            "history": [], "assumptions": [
                "Native-validated complete hypothetical evaluation sets, not live truth."
            ],
        }
