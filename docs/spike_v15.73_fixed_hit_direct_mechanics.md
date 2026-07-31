# v15.73 fixed-hit direct mechanics

Direct mechanics now supports only canonical fixed 1–4-hit moves where
`min_hits == max_hits`. It convolves the native per-hit Q12 roll counts to
derive total range and conditional KO probability. Variable-hit metadata,
malformed counts, and fixed-hit drain/recoil combinations remain unsupported.

Per-hit range and total range are distinct. Total evidence keeps the existing
damage comparison surface; presentation adds an explicit fixed-hit/per-hit
summary only for known fixed-hit results. No accuracy-adjusted probability,
expected damage, hit-state transition, or consequence accumulation is added.
