# Weak Satisfying Inputs Analysis

Measures the proportion of satisfying inputs that correspond to structurally
meaningful (connected) vs. trivial (disconnected) constraints, for Circom and
Gnark backends.

For each generated circuit where an input satisfies the constraints, analyse the
dependency graph between input signals and assertions. An assertion is connected
if it depends (directly or transitively) on at least one input signal, and
disconnected otherwise. The expected result is that a large majority of satisfying
executions are structurally trivial, meaning the inputs do not actually constrain
the circuit in any meaningful way.
