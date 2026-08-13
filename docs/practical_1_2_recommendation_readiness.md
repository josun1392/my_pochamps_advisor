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

When several material gaps apply at once, the panel groups them as explicit
confirmation routes, authority that is still unavailable to capture, and
unsupported mechanics. The grouping is a stable read-only presentation of the
canonical readiness projection: it neither prioritizes battle outcomes nor
creates, infers, or mutates authority. One resolved route refreshes the full
current selection, so only its resolved gap disappears while other material
gaps remain visible.

## Deterministic integration coverage

The Practical 1.2 offline integration scenarios exercise the full bounded
readiness workflow: canonical multi-gap projection and grouped presentation,
existing confirmation routes, paired exact HP application, cancel and
partial/stale-owner handling, and post-confirmation readiness refresh. They
also verify that unavailable and unsupported reasons stay visible without a
fictional route. The scenarios use sanitized fixtures only and do not create
authority or mutate state except through the existing explicit confirmation
paths.
