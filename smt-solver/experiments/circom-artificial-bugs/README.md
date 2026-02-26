# circom-artificial-bugs

This experiment uses the dedicated compiler at:

- `smt-solver/third_party/artificial-bugs/circom/target/release/circom`

## Bug config

The compiler reads bug toggles from JSON config file path:

- env: `CIRCOM_ARTIFICIAL_BUGS_CONFIG`
- experiment default: `smt-solver/experiments/circom-artificial-bugs/artificial_bugs_config.json`

Supported keys:

- `always-empty-r1cs` (`bool`): when `true`, compiler writes an empty R1CS (zero constraints).
- `remove-random-variable` (`object`): randomly picks variables and drops every constraint touching them.
  - `n` (`usize`): number of variables to pick (if larger than available variables, all are used).
- `remove-random-constraint` (`object`): randomly drops constraints directly (variables/witness map are untouched).
  - `n` (`usize`): number of constraints to drop (if larger than available constraints, all are dropped).
- `add-random-constraint` (`object`): adds random constraints of the form `x * y = num`.
  - `n` (`usize`): number of random constraints to add.
- `change-random-number` (`object`): samples coefficients/constants in existing constraints and replaces them with random numbers.
  - `n` (`usize`): number of numbers to change.
- `bias-constant-on-nonlinear` (`object`): on nonlinear constraints only, adds a tiny random delta to the constant term.
  - `n` (`usize`): number of nonlinear constraints to perturb.

Example:

```json
{
  "always-empty-r1cs": false,
  "remove-random-variable": {
    "n": 2
  },
  "remove-random-constraint": {
    "n": 1
  },
  "add-random-constraint": {
    "n": 1
  },
  "change-random-number": {
    "n": 1
  },
  "bias-constant-on-nonlinear": {
    "n": 1
  }
}
```
