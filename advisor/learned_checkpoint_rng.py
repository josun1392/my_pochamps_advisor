"""RNG-neutral checkpoint construction, not an exact native restart engine.

Reuse the Python/NumPy/Torch preservation semantics of LearnedPolicy. The
already-safe ActionableActor retains its existing CPU-only guard unchanged.
Weights and Adam in a ZIP do not include live sampler/native execution state.
"""
from contextlib import contextmanager
import random

import numpy as np
import torch


@contextmanager
def isolated_checkpoint_rng():
    """Leave the caller's generators unchanged, including when loading fails."""
    python_state, numpy_state = random.getstate(), np.random.get_state()
    devices = list(range(torch.cuda.device_count())) if torch.cuda.is_initialized() else []
    with torch.random.fork_rng(devices=devices):
        try:
            yield
        finally:
            random.setstate(python_state)
            np.random.set_state(numpy_state)


def rng_neutral_load(loader, path, *, device="cpu", **kwargs):
    """Construct an unattached model without reseeding a live learner or env.

    For a different worker count, pass n_envs explicitly and call set_env only
    after identity/optimizer validation. Passing env to SB3.load seeds its live
    vector as a side effect; a global RNG guard alone cannot undo that.
    """
    if kwargs.get("env") is not None:
        raise ValueError("checkpoint_loader_must_not_reseed_live_environment")
    if str(device) != "cpu" and not str(device).startswith("cuda"):
        raise ValueError("checkpoint_loader_requires_explicit_supported_device")
    if str(device).startswith("cuda") and not torch.cuda.is_initialized():
        raise ValueError("checkpoint_loader_requires_initialized_CUDA_rng")
    with isolated_checkpoint_rng():
        return loader(path, device=device, **kwargs)


def reject_unrestorable_resume():
    """Fail before mutating legacy runs, rather than repeat a seeded rollout.

    The current autonomous trainer persists weights/Adam and counters, but not
    Python/NumPy/Torch RNG, live native/Gym generators, case/sampler cursors or
    an unsettled rollout. No exact cold-resume implementation consumes that
    complete state yet. A metadata flag or reseeding cannot repair this gap.
    Explicit new seed-addressed continuation experiments remain separate runs.
    """
    raise ValueError(
        "checkpoint_resume_unavailable_rng_native_sampler_state: "
        "legacy --resume cannot restore execution RNG/sampler/rollout state; "
        "original checkpoint and STOP are preserved; no reseed fallback"
    )
