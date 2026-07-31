# Validated Recommendation Panel Rendering

The existing structured advice panel continues to consume only the
UI-neutral presentation model.  Its formatter now renders a selected-candidate
section only when `selected_candidate` is present after canonical validation.

The section maps bounded explanation codes and comparison tags to short Korean
text. It displays native damage, percent, and one-hit KO values only when the
selected mechanics status is `known`; it shows action order only for known
first/second/tie statuses. Incomplete mechanics receives a missing-context
message, and unsupported mechanics receives a scope-boundary message. Internal
paths, raw provider data, and missing-input values are never displayed.

The pre-existing request-start `set_running(True)` replaces panel text with the
analyzing state. Failure and no-candidate presentation statuses do not render a
selected-candidate section, so an earlier success is not reused. No widget,
worker, thread, provider, or ranking behavior changed. Offline-only validation.
