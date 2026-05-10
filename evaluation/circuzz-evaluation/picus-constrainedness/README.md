# Picus Constrainedness Distribution

Measures the proportion of generated circuits classified as underconstrained vs.
well-constrained by Picus, for both Circom and Gnark backends.

Run Circuzz with the Picus oracle on each backend and record the Picus verdict
(underconstrained / well-constrained) for every generated circuit. The expected
result is that the vast majority of randomly generated circuits are
underconstrained, which limits the usefulness of Picus as a differential oracle
in this setting.
