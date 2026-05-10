# o1js Backend Performance

Measures the throughput of the o1js (Mina) backend relative to Circom and Gnark
baselines.

Run Circuzz with the o1js backend using its batch execution model (single
ZkProgram.compile() call amortised across multiple prove/verify steps) and record
average time per test and tests per second. Compare against Circom and Gnark
baselines. The expected result is severely degraded throughput (~0.02x relative
to Circom) due to the high cost of ZK circuit compilation in o1js, motivating
the decision not to pursue the backend further.
