# v14.23 Advice Worker Bounded Shutdown Contract

## Scope and safety boundary

This investigation used deterministic fake workers, monkeypatched local runner
functions, and lifecycle harnesses only. Actual-provider and network calls: 0.
The provider budget remains 0. No force termination, unbounded wait, retry,
fallback, or provider-adapter change is included.

## Ownership inventory

Both advice modes construct a parented `QThread(self)` in `MainWindow`, create
an unparented `QObject` worker, move it with `moveToThread`, and start its
`run` slot from `thread.started`.

| Path | Result signals | Natural exit | References |
| --- | --- | --- | --- |
| legacy `LLMAdviceWorker` | `finished(recommendation, payload)`, `failed(message)` | each result signal calls `thread.quit`; `thread.finished` calls worker `deleteLater`, main cleanup, then one-shot thread `deleteLater` | `_llm_thread`, `_llm_worker` |
| structured `StructuredRecommendationWorker` | `finished(result)`, `failed(message)` | same signal/quit/delete path | `_structured_thread`, `_structured_worker` |

The MainWindow holds at most one reference per mode. A stale callback cannot
mutate the shared panel because owner/token terminal claims reject it. Cleanup
may run after a request is stale and its one-shot `deleteLater` remains safe.

## Current shutdown contract

`closeEvent` first permanently marks the window closing and clears the active
owner/token. It then requests interruption from each distinct active advice
thread without waiting. Each live thread is reparented to `QApplication` before
the close is accepted, so the window is no longer its QObject owner while the
worker naturally completes. Finished cleanup still deletes the thread later.

Workers now have an internal `cancelled` signal connected to `thread.quit`.
They check `QThread.currentThread().isInterruptionRequested()` before entering
the local runner and again after it returns but before presentation signals.
Thus an interruption before execution exits immediately, and an interruption
during a non-cancellable provider call exits immediately once that call returns
without a success/failure UI callback. This is cooperative cancellation, not a
claim that the provider call itself can be stopped.

## Candidate decision

| Candidate | Decision | Reason |
| --- | --- | --- |
| Callback suppression only | retained, insufficient alone | protects UI but leaves no cooperative exit request or window-independent thread parent. |
| `requestInterruption` + worker checks | adopted | meaningful at run entry and immediately after the runner returns; deterministic offline proof exists. |
| Bounded `thread.wait(ms)` | not adopted | cannot interrupt an in-flight provider call and would block the UI for no guaranteed benefit. |
| Retained thread registry | not adopted | there is only one field per mode; QApplication reparenting retains the actual active QThread through its natural completion without a global singleton. |
| Provider cancellation | deferred | current runner is synchronous and exposes no safe cancellation contract. |

## Tests and remaining gaps

The bounded-shutdown contract covers no-worker close, cooperative pre-run exit,
post-run cancellation suppression, non-cooperative late cleanup, duplicate
cleanup, two active mode threads, and existing stale callback suppression. It
does not emulate a real provider timeout.

Remaining gaps: an in-flight synchronous provider call cannot be interrupted;
a permanently hung non-cooperative worker remains owned by QApplication until
process shutdown; OS/application shutdown needs a separate application-level
contract; repeated long-running requests need soak testing. No `terminate()` or
unbounded `wait()` is used.
