# v14.20 Structured Same-Owner Request Token Lifecycle

## Purpose

This change closes the v14.19 same-owner stale-result gap without changing
provider, payload, schema, semantic validation, or the legacy/structured public
actions. The actual-provider budget remains zero.

## Internal identity

`MainWindow` now assigns a monotonic integer in `_begin_advice_request(owner)`
and stores the active `(owner, token)` pair. The token is captured only by the
worker signal and thread-finished closures. It is not sent to a provider,
payload, prompt, panel text, or token log.

## Callback and cleanup rules

Success and failure callbacks apply panel, status, and busy-state changes only
when `_is_current_advice_request(owner, token)` succeeds. Thread cleanup always
releases its own thread object, but clears stored worker references and active
identity only for the current owner/token pair. Thus an older request cannot
overwrite a newer same-owner or cross-mode request, display a stale error, or
clear its worker lifecycle.

## Offline coverage

Pure lifecycle tests cover monotonic tokens, same-owner stale success, stale
failure, stale cleanup, cross-mode stale legacy callbacks, and current cleanup.
They use fake panel/thread objects and make no provider or network call.

## Remaining limits

This is stale-result suppression, not provider cancellation. Older threads may
finish normally and are cleaned up independently. Worker-identity checks beyond
the captured token/thread pair, broader lifecycle unification, and full UI race
testing remain possible future refinements.
