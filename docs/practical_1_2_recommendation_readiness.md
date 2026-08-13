# Practical 1.2: recommendation readiness

The readiness panel is a read-only projection of the current structured
recommendation preparation. It reports only canonical missing-input or
unsupported-mechanic results already emitted by deterministic candidates,
action order, and move-success evaluation.

When a listed missing fact has an existing explicit confirmation control, the
panel opens that control. It never infers, fills, or mutates battle state; a
new frozen, identity-checked runtime snapshot is prepared whenever readiness is
checked. Unknown authority remains incomplete, and unsupported mechanics are
shown separately without a fictitious input route.

When a canonical material held-item gap is present, readiness prioritizes a
shortcut to the existing active-side `ItemProfileDialog`. The shortcut records
the session, slot, and Pokémon identity from the frozen readiness evaluation,
then rejects a stale route before opening the dialog. Applying or cancelling
continues to use the existing item-profile flow; no item state is inferred or
written by readiness itself.

The existing current-HP dialog can also record exact HP/max HP for both active
sides in one session. Each side remains an independent explicit record. The UI
captures the active session, slot, and Pokémon identity before opening; it
applies only entries whose owner still matches and excludes owner-mismatched
entries from later frozen requests. Unticked sides remain unchanged.
