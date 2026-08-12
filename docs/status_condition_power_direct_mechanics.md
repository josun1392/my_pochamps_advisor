# Status-conditioned direct power

The native direct-damage evaluator supports Hex and Venoshock from one exact,
defender-owned frozen current major condition. Hex uses 130 base power for any
major condition other than `none`; Venoshock uses 130 only for poison or toxic.
Both retain 65 base power when the exact condition does not satisfy their rule.
The resolved power feeds the established Q12 damage, KO, and danger path.

Missing, duplicated, malformed, or untrusted defender condition authority
remains incomplete or unsupported. The evaluator does not infer a condition
from a move, prior possibility, species, or damage. Other condition-dependent
dynamic moves remain unavailable unless their exact prerequisites are supported.
