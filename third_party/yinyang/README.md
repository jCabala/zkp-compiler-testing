# Vendored YinYang

This directory vendors `yinyang` version 0.3.0 source code from the installed
package for local patching and reproducible experiments.

License: MIT (`third_party/yinyang/LICENSE.md`).

Local patches in this repo:
- `YY_FUSION_REWRITE_POLICY` environment variable support in semantic fusion:
  - `random` (upstream behavior)
  - `all` (rewrite all occurrences for selected fusion pairs)
- `YY_FUSION_SIDE_POLICY` environment variable support in semantic fusion:
  - `both` (upstream behavior: rewrite both x and y sides)
  - `one` (rewrite only x side)

Entry point used by experiments:
- `third_party/yinyang/yinyang_cli.py`
