"""Explicit bounded coordinator launcher. No PPO, policy loading, or native steps."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--plan")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    if not args.enable:
        print(json.dumps({"status": "disabled", "native_starts": 0}))
        return
    if not args.plan or not args.output:
        parser.error("--enable requires an external frozen --plan and new --output")
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ["OMP_NUM_THREADS"] = os.environ["MKL_NUM_THREADS"] = "1"
    from advisor.learning_resources import WindowsJob, RuntimeLimit, enforce_local_network_only
    from advisor.learned_initial_reserves import sample_initial_reserves
    from advisor.learned_decision_snapshots import outside_git
    import torch
    torch.set_num_threads(1)
    job = WindowsJob(memory_mib=4096, cpu_percent=25, active_process_limit=12)
    enforce_local_network_only()
    plan = json.loads(outside_git(args.plan).read_text(encoding="utf-8"))
    # Library creates the new output; no pre-existing directory is overwritten.
    limit = RuntimeLimit(args.output, 570)
    try:
        result = sample_initial_reserves(plan, args.output, enabled=True, stopping=limit.stopping)
        print(json.dumps({**result, "resources": job.usage()}))
    finally:
        limit.finished.set()


if __name__ == "__main__":
    main()
