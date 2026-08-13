# Practical-1.0 explanation integration scenarios

`tests/test_v46_practical_1_0_explanation_integration_scenarios.py` checks the
offline deterministic recommendation-to-presentation boundary. It covers exact
switch identity, danger-driven switch selection, same-tier Move preference,
blocked and incomplete switch cases, detached presentation models, and the
validated Move presentation's suppression of incomplete or unsupported
mechanics details.

The scenarios assert semantic fields and conservative visibility, not Korean
wording. They do not call a provider, invent explanation facts, or introduce
new strategic scoring. Rich prose, broad UX redesign, and provider-generated
explanations remain outside practical-1.0 deterministic validation.
