# Production Recommendation Presentation Smoke

The existing sanitized multi-candidate smoke now follows the production-derived
path through completion, canonical recommendation result, presentation model,
and formatter. It checks only bounded conditions: selected action identity,
candidate-local evidence, validated summary presence, known mechanics text, and
absence of internal/raw identifiers. It prints no presentation text or provider
content.

Headless controller/formatter verification is sufficient for this slice because
MainWindow already forwards the presentation model to the existing text panel;
no widget lifecycle or visual design changed. Stale transition remains covered
by the existing `set_running(True)` and failure lifecycle regressions. Actual
execution uses the pre-approved two-fixture, two-call round with no retry.
