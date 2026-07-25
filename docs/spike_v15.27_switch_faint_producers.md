# v15.27 Switch and Faint Producers

Explicit `ui_switch_confirmation` and `ui_faint_confirmation` now produce
private canonical observations only with user confirmation, matching
session/owner provenance, and valid payloads. Switches require explicit,
different out/in identities and retain `switch_kind: unknown`; faint never
follows HP zero, damage, or Q12 automatically. Both remain detached from UI,
store, reducer, persistence, and provider paths.
