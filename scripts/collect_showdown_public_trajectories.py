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
from advisor.learned_offline import TrajectoryWriter
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    enforce_local_network_only,
    atomic_json,
)
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT


def collect(config, output):
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
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    job = WindowsJob(
        memory_mib=config.get("memory_mib", 12288),
        cpu_percent=config.get("cpu_percent", 50),
        active_process_limit=max(12, workers * 4 + 8),
    )
    torch.set_num_threads(1)
    budget = RuntimeLimit(output.parent, config["max_runtime_seconds"])
    network = enforce_local_network_only()
    started = perf_counter()
    encoder = make_encoder(config["catalog"], "showdown-learned-observation-v3")
    references = {}
    for name, path in config.get("models", {}).items():
        references[name] = (
            str(Path(path).resolve()),
            LearnedPolicy(path, config["catalog"]).model_id,
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
            "gamma": 0.99,
            "split": "train",
            "config": config,
            "seed": config["seed"],
            "curriculum_version": config["curriculum_version"],
            "frozen_model_ids": {k: v[1] for k, v in references.items()},
        },
    )
    vector = None
    try:
        vector = SubprocVecEnv(factories, start_method="spawn")
        vector.seed(config["seed"])
        obs = vector.reset()
        pending = [[] for _ in range(workers)]
        rng = np.random.default_rng(config["seed"])
        behaviors = [str(rng.choice(config["behaviors"])) for _ in range(workers)]
        attempted = discarded = ended = 0
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
            attempted += workers
            for i in np.flatnonzero(dones):
                ended += 1
                outcome = infos[i]["native_outcome"]
                if outcome["terminated"] and not outcome["truncated"]:
                    writer.add_episode(pending[i], float(rewards[i]), behaviors[i])
                else:
                    discarded += len(pending[i])
                pending[i] = []
                behaviors[i] = str(rng.choice(config["behaviors"]))
        native = vector.env_method("learning_resources")
        manifest = writer.finish(
            {
                "attempted_decisions": attempted,
                "ended_episodes": ended,
                "discarded_truncated_rows": discarded,
                "discarded_incomplete_rows": sum(map(len, pending)),
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
        atomic_json(
            output / "failure.json",
            {
                "error": type(error).__name__,
                "message": str(error),
                "resources": job.usage(),
            },
        )
        raise
    finally:
        if vector is not None:
            vector.close()
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
