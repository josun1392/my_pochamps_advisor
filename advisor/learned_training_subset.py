"""Opt-in SHA-bound subsets of native V8 train teams, coordinator only."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import random

from advisor.learned_encoder import fingerprint
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT

VERSION = "showdown-native-training-subset-v1"


class NativeTrainingSubset:
    def __init__(self, path, expected_sha256):
        from advisor.learned_full_roster import load_bank, study_identity

        raw = Path(path).read_bytes()
        if sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("training_subset_hash_mismatch")
        contract = json.loads(raw)
        if any(contract.get(k) != v for k, v in {
            "schema_version": VERSION, "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID, "parent_curriculum": "showdown-learning-curriculum-v8",
            "parent_split": "train", "parent_bank_sha256": study_identity()["bank_sha256"],
        }.items()):
            raise ValueError("training_subset_authority_mismatch")
        indices = contract.get("team_indices")
        bank = load_bank()["teams"]["train"]
        if (not isinstance(indices, list) or len(indices) not in (1, 16)
                or len(set(indices)) != len(indices)
                or any(type(i) is not int or not 0 <= i < len(bank) for i in indices)):
            raise ValueError("training_subset_membership_mismatch")
        teams = [bank[i] for i in indices]
        if contract.get("team_sha256") != [fingerprint(t) for t in teams]:
            raise ValueError("training_subset_team_identity_mismatch")
        mode = contract.get("selection_mode")
        if ((len(teams) == 1 and mode != "shared_fixed_ordered3")
                or (len(teams) == 16 and mode != "independent_random_ordered3")
                or (mode == "shared_fixed_ordered3" and contract.get("preview") != [1, 2, 3])):
            raise ValueError("training_subset_selection_mismatch")
        namespace = contract.get("seed_namespace")
        if not isinstance(namespace, str) or not 1 <= len(namespace) <= 128:
            raise ValueError("training_subset_seed_namespace_required")
        self.teams, self.contract = deepcopy(teams), contract
        self.identity = {**contract, "sha256": expected_sha256,
                         "information_scope": "coordinator_only_never_policy_features"}

    def __call__(self, split, index):
        if split != "train":
            raise ValueError("training_subset_partition_access_denied")
        return self._case("train", index)

    def probe(self, split, index):
        """Explicit consumed diagnostic inside the training-team distribution."""
        if split != "validation":
            raise ValueError("training_subset_probe_requires_validation")
        return self._case("probe", index)

    def _case(self, namespace, index):
        if type(index) is not int or index < 0:
            raise ValueError("invalid_subset_case_index")
        rng = random.Random(int.from_bytes(sha256(
            f"{self.identity['sha256']}:{self.contract['seed_namespace']}:{namespace}:{index}".encode()
        ).digest(), "big"))
        teams = {side: deepcopy(rng.choice(self.teams)) for side in ("self", "opponent")}
        preview = ({side: [1, 2, 3] for side in teams}
                   if self.contract["selection_mode"] == "shared_fixed_ordered3"
                   else {side: rng.sample(range(1, 7), 3) for side in teams})
        return {"scenario_id": f"{VERSION}:{namespace}:{index}", "teams": teams,
                "preview": preview, "seed": [rng.randrange(65536) for _ in range(4)],
                "history": [], "assumptions": [
                    "Frozen native V8 training subset; hypothetical coordinator truth, not observed truth."
                ]}


class SubsetProbeBank:
    """Alternate in-distribution probes and separate diagnostic holdout teams."""
    def __init__(self, subset, heldout):
        if heldout.scope != "validation":
            raise ValueError("subset_probe_cannot_consume_sealed_final")
        seen = {fingerprint(t) for t in subset.teams}
        if any(fingerprint(t) in seen for teams in heldout.bank["panels"].values() for t in teams):
            raise ValueError("subset_probe_heldout_team_overlap")
        self.subset, self.heldout = subset, heldout
        self.identity = {"schema_version": "showdown-training-subset-probe-v1",
                         "subset": subset.identity, "heldout": heldout.identity,
                         "selection": "even_case_training_distribution_odd_case_heldout",
                         "scope": "consumed_validation_diagnostic_not_checkpoint_selection"}

    def __call__(self, split, index):
        if split != "validation":
            raise ValueError("subset_probe_requires_validation")
        return self.subset.probe(split, index) if index % 2 == 0 else self.heldout(split, index)
