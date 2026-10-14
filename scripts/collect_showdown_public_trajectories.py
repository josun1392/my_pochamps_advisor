"""Bounded parallel collection from diverse, SHA-bound public-information actors."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json
from time import perf_counter
import numpy as np
import torch
from stable_baselines3.common.vec_env import SubprocVecEnv
from sb3_contrib.common.maskable.utils import get_action_masks
from advisor.learned_action_encoder import make_encoder
from advisor.learned_parallel import LearningEnvFactory
from advisor.learned_policy import LearnedPolicy
from advisor.learned_offline import TrajectoryWriter, PUBLIC_CATEGORICAL_SCHEMA, file_hash
from advisor.learned_public_categories import RUNTIME_ABILITY_VERSION
from advisor.learned_objective import objective_contract, categorical_learning_source_identity
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    enforce_local_network_only,
    atomic_json,
)
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT


def terminal_label_eligible(outcome, rejected_episode):
    """A time limit or rejected joint choice cannot supply a V2 MC target."""
    return outcome["terminated"] and not outcome["truncated"] and not rejected_episode


def close_owned_vector(vector, *, failed):
    """Broken pipes can make upstream close block on unmatched replies."""
    if failed:
        for process in getattr(vector, "processes", []):
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
    else:
        vector.close()


def collect(config, output, *, resource_job=None):
    count, workers = config.get("decisions", 32768), config.get("envs", 8)
    if (
        not 32 <= count <= 262144
        or not 1 <= workers <= 8
        or not 30 <= config.get("max_runtime_seconds", 0) <= 1800
    ):
        raise ValueError("bounded_offline_collection_required")
    if (
        not 1024 + 768 * workers <= config.get("memory_mib", 12288) <= 16384
        or not 1 <= config.get("cpu_percent", 50) <= 75
    ):
        raise ValueError("unsafe_collection_resource_limits")
    version = config.get("encoder_version", "showdown-learned-observation-v3")
    gamma = config.get("gamma", 0.99)
    categorical = version == RUNTIME_ABILITY_VERSION
    if ((categorical and gamma != 1.0)
            or (not categorical and (version != "showdown-learned-observation-v3" or gamma != 0.99))):
        raise ValueError("unsupported_opt_in_collection_objective")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    job = resource_job or WindowsJob(
        memory_mib=config.get("memory_mib", 12288),
        cpu_percent=config.get("cpu_percent", 50),
        active_process_limit=max(12, workers * 4 + 8),
    )
    torch.set_num_threads(1)
    budget = RuntimeLimit(output.parent, config["max_runtime_seconds"])
    network = enforce_local_network_only()
    started = perf_counter()
    encoder = make_encoder(config["catalog"], version)
    references = {}
    for name, path in config.get("models", {}).items():
        references[name] = (
            str(Path(path).resolve()),
            LearnedPolicy(path, config["catalog"], expected_model_id=config.get("model_ids", {}).get(name)).model_id,
        )
    kinds = set(config["behaviors"]) | set(config["opponents"])
    if not kinds <= {
        "random",
        "max_power",
        "heuristic",
        "tactical_heuristic",
        "champions_heuristic",
    } | set(references):
        raise ValueError("unknown_public_actor")
    factories = [
        LearningEnvFactory(
            str(config["checkout"]),
            str(config["catalog"]),
            encoder.version,
            i * 100000,
            config["curriculum_version"],
            tuple(config["opponents"]),
            references,
            collect_tactical_metrics=categorical,
            collect_public_trajectories=categorical,
            diagnostic_directory=str(output.parent / "public_encoding_failures") if categorical else None,
        )
        for i in range(workers)
    ]
    writer = TrajectoryWriter(
        output,
        count + workers * 256,
        encoder.dimension,
        {
            "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID,
            "encoder_version": encoder.version,
            "catalog_fingerprint": encoder.catalog_fingerprint,
            "observation_dimension": encoder.dimension,
            "gamma": gamma,
            "split": "train",
            "config": config,
            "seed": config["seed"],
            "curriculum_version": config["curriculum_version"],
            "frozen_model_ids": {k: v[1] for k, v in references.items()},
            **({
                "schema_version": PUBLIC_CATEGORICAL_SCHEMA,
                "feature_contract": encoder.feature_contract,
                "training_objective": objective_contract(gamma, 0.95),
                "terminal_label_scope": "native_terminated_no_truncation_no_rejected_or_unsupported_episode",
                "policy_information_scope": "owner_visible_features_masks_and_executed_choices_only",
                "collection_source_sha256": {**categorical_learning_source_identity(),
                    "scripts/collect_showdown_public_trajectories.py": file_hash(Path(__file__)),
                    "advisor/learned_offline.py": file_hash(Path(__file__).resolve().parents[1] / "advisor/learned_offline.py")},
            } if categorical else {}),
        },
    )
    vector = None
    collection_failed = False
    diagnostics_file = (output / "public_diagnostics.jsonl").open("x", encoding="utf-8") if categorical else None
    try:
        vector = SubprocVecEnv(factories, start_method="spawn")
        vector.seed(config["seed"])
        obs = vector.reset()
        pending = [[] for _ in range(workers)]
        pending_diagnostics = [[] for _ in range(workers)]
        rejected_episode = [False] * workers
        unsupported_episode = [False] * workers
        rng = np.random.default_rng(config["seed"])
        behaviors = [str(rng.choice(config["behaviors"])) for _ in range(workers)]
        attempted = discarded = ended = rejected_rows = rejected_episodes = unsupported_rows = unsupported_episodes = 0
        while writer.count < count and attempted < count * 4 and not budget.stopping():
            masks = get_action_masks(vector)
            decisions = [
                vector.env_method(
                    "behavior_decision",
                    kind,
                    config.get("stochastic_learned", True),
                    indices=i,
                )[0]
                for i, kind in enumerate(behaviors)
            ]
            actions = np.array([d["action"] for d in decisions])
            # Labels are actual actor choices on its partial view, never alternatives from a hidden-state search.
            for i, action in enumerate(actions):
                pending[i].append(
                    (
                        obs[i].copy(),
                        masks[i].copy(),
                        int(action),
                        decisions[i]["category"],
                    )
                )
            obs, rewards, dones, infos = vector.step(actions)
            if categorical:
                public = vector.env_method("collection_step_diagnostics")
                for i, evidence in enumerate(public):
                    if evidence["action"] != int(actions[i]):
                        raise ValueError("public_collection_action_binding_mismatch")
                    pending_diagnostics[i].append(evidence)
                    rejected_episode[i] |= evidence["native_rejections"] > 0
                    unsupported_episode[i] |= evidence["terminal_encoding_unavailable"]
            attempted += workers
            for i in np.flatnonzero(dones):
                ended += 1
                outcome = infos[i]["native_outcome"]
                completed = vector.env_method("drain_completed", indices=int(i))[0]
                if categorical and (len(completed) != 1 or completed[0]["winner"] != outcome["winner"]):
                    raise ValueError("public_collection_terminal_binding_mismatch")
                if terminal_label_eligible(outcome, rejected_episode[i] or unsupported_episode[i]):
                    first_row = writer.count
                    writer.add_episode(pending[i], float(rewards[i]), behaviors[i])
                    if categorical:
                        if completed[0]["native_rejected_choices"]:
                            raise ValueError("rejected_episode_cannot_supply_return_labels")
                        for j, evidence in enumerate(pending_diagnostics[i]):
                            diagnostics_file.write(json.dumps({"row": first_row + j,
                                "episode": writer.episodes - 1, "behavior": behaviors[i],
                                "opponent_policy": completed[0]["opponent"], **evidence}) + "\n")
                else:
                    if unsupported_episode[i]:
                        unsupported_rows += len(pending[i]); unsupported_episodes += 1
                    elif rejected_episode[i]:
                        rejected_rows += len(pending[i]); rejected_episodes += 1
                    else:
                        discarded += len(pending[i])
                pending[i] = []
                pending_diagnostics[i] = []
                rejected_episode[i] = False
                unsupported_episode[i] = False
                behaviors[i] = str(rng.choice(config["behaviors"]))
        if diagnostics_file is not None:
            diagnostics_file.flush()
        native = vector.env_method("learning_resources")
        manifest = writer.finish(
            {
                "attempted_decisions": attempted,
                "ended_episodes": ended,
                "discarded_truncated_rows": discarded,
                "discarded_incomplete_rows": sum(map(len, pending)),
                **({"discarded_rejected_episode_rows": rejected_rows,
                    "discarded_rejected_episodes": rejected_episodes,
                    "discarded_unsupported_episode_rows": unsupported_rows,
                    "discarded_unsupported_episodes": unsupported_episodes,
                    "public_diagnostics_sha256": file_hash(output / "public_diagnostics.jsonl"),
                    "curriculum_binding": __import__("advisor.learned_full_roster", fromlist=["study_identity"]).study_identity(config["catalog"]),
                } if categorical else {}),
                "stopped": budget.stopping(),
                "wall_seconds": perf_counter() - started,
                "network": network,
                "resources": {
                    "native_rss_bytes": sum(r["rss_bytes"] for r in native),
                    **job.usage(),
                },
            }
        )
        print(
            json.dumps(
                {
                    k: manifest[k]
                    for k in (
                        "rows",
                        "completed_episodes",
                        "terminal_outcomes",
                        "behavior_rows",
                        "wall_seconds",
                        "resources",
                    )
                }
            ),
            flush=True,
        )
        return manifest
    except BaseException as error:
        collection_failed = True
        atomic_json(
            output / "failure.json",
            {
                "error": type(error).__name__,
                "message": str(error),
                "resources": job.usage(),
                "worker_exitcodes": [p.exitcode for p in getattr(vector, "processes", [])],
            },
        )
        raise
    finally:
        try:
            if vector is not None:
                try:
                    close_owned_vector(vector, failed=collection_failed)
                except (EOFError, BrokenPipeError, OSError):
                    for process in getattr(vector, "processes", []):
                        if process.is_alive():
                            process.terminate()
                        process.join(timeout=1)
        finally:
            if diagnostics_file is not None:
                diagnostics_file.close()
            budget.finished.set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkout", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.checkout:
        config["checkout"] = str(args.checkout.resolve())
    if not config.get("checkout"):
        parser.error("--checkout or config checkout is required")
    collect(config, args.output)


if __name__ == "__main__":
    main()
