# v15.74 fixed-hit provider grounding smoke

The approval-gated sanitized smoke adds exactly two fixed-hit fixture pairs:
one supported fixed two-hit versus single-hit comparison, and one supported
fixed-hit plus variable and malformed multi-hit boundary. The provider still
returns only a selected candidate ID and a bounded explanation code.

Before a call, the runner verifies canonical fixed-hit metadata, per-hit and
total ranges, total-distribution mechanics, and unsupported variable/malformed
states. After deterministic completion, it verifies candidate-local evidence
and the selected fixed-hit presentation distinction. It emits only bounded
fixture/result diagnostics; raw provider data, distributions, and internal
paths are never surfaced.

The actual round remains separately approval-gated. It does not add variable
hit support, expected or accuracy-adjusted damage, hit-by-hit state changes,
or provider-authored mechanics values.
