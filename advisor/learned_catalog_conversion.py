"""Explicit static-catalog extension for trusted local historical checkpoints.

No weight, optimizer, encoder or battle observation conversion is performed.
Existing public facts must remain identical; newly added facts are untrained.
"""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

from advisor.learned_action_encoder import make_encoder
from advisor.learned_policy import LearnedPolicy
from advisor.learning_resources import atomic_json


def validate_extension(old, new):
    for key in ("schema_version", "engine_commit", "format_id"):
        if old.get(key) != new.get(key):
            raise ValueError("catalog_authority_changed")

    def subset(a, b):
        return (
            isinstance(b, dict)
            and all(k in b and subset(v, b[k]) for k, v in a.items())
            if isinstance(a, dict)
            else a == b
        )

    if not subset(old, new):
        raise ValueError("catalog_existing_feature_changed")
    return sorted(set(new["species"]) - set(old["species"]))


def convert_checkpoint(source, old_catalog, new_catalog, output):
    source = Path(source).with_suffix(".zip")
    destination = Path(output)
    if destination.exists():
        raise ValueError("new_conversion_output_required")
    old = json.loads(Path(old_catalog).read_text(encoding="utf-8"))
    new = json.loads(Path(new_catalog).read_text(encoding="utf-8"))
    added = validate_extension(old, new)
    original = LearnedPolicy(source, old_catalog)
    target = make_encoder(new, original.encoder.version)
    if target.dimension != original.encoder.dimension:
        raise ValueError("catalog_encoder_shape_changed")
    metadata = deepcopy(original.metadata)
    metadata.update(
        catalog_fingerprint=target.catalog_fingerprint,
        public_state_version="showdown-policy-state-v2",
        catalog_conversion={
            "schema_version": "showdown-static-catalog-extension-v1",
            "source_model_sha256": original.model_id,
            "source_manifest_sha256": sha256(
                source.with_suffix(".json").read_bytes()
            ).hexdigest(),
            "source_catalog_fingerprint": original.encoder.catalog_fingerprint,
            "target_catalog_fingerprint": target.catalog_fingerprint,
            "added_static_species": added,
            "scope": "Exact existing catalog facts and encoder shape; original zip bytes including optimizer unchanged. Added species facts are not newly trained knowledge. Current public-state-v2 applies at inference; historical replay semantics untouched.",
        },
    )
    destination.mkdir(parents=True)
    path = destination / "model.zip"
    shutil.copyfile(source, path)
    atomic_json(path.with_suffix(".json"), metadata)
    converted = LearnedPolicy(path, new_catalog)
    if converted.model_id != original.model_id:
        raise AssertionError("conversion_changed_checkpoint_bytes")
    return str(path)
