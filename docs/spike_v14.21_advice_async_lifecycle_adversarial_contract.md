# v14.21 Advice Async Lifecycle Adversarial Contract

v14.20 owner/token identity now has a request-local terminal claim. A current
success or failure claims the terminal transition once; duplicates are ignored.
Cleanup is idempotent per thread and never clears a newer owner/token.

Offline adversarial tests cover finished-before-success, duplicate success and
failure, duplicate finished, stale cleanup after a newer request, and a
structured → legacy → structured callback race. Preparation still occurs before
token issuance, so a local preparation failure does not invalidate an existing
active request. This is deliberate current behavior and not cancellation.

Owner/token provenance is sufficient for current closure wiring; no separate
worker identity was added. Real close/teardown races, cancellation, and long
running repeated UI sessions remain gaps. Provider budget is zero and no
provider/network evaluation was executed.
