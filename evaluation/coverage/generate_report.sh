#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
REPO_ROOT=$(realpath "$SCRIPT_DIR/../..")
IMAGE_SMT_COVERAGE="localhost/smt-exp-circom-coverage:latest"
IMAGE_CIRCUZZ_COVERAGE="localhost/circuzz-circom-coverage:latest"
PROFRAW_DIR="/coverage/profraw"

usage() {
  echo "usage: $0 <smt-solver|sat_fusion_circom|picus_fusion_circom|test-suite|circuzz-arithmetic|circuzz-fully-constraint>" >&2
  exit 1
}

EXPERIMENT="${1:-}"
if [[ -z "$EXPERIMENT" ]]; then
  usage
fi

case "$EXPERIMENT" in
  smt-solver|sat_fusion_circom|picus_fusion_circom|test-suite|circuzz-arithmetic|circuzz-fully-constraint|bool-vs-ff-*) ;;
  *) usage ;;
esac

OBJ_DIR="$SCRIPT_DIR/obj/$EXPERIMENT"
REPORT_DIR="$OBJ_DIR/coverage_report"

# Select the appropriate coverage image based on experiment type.
if [[ "$EXPERIMENT" == circuzz-* ]]; then
  IMAGE_CIRCOM_COVERAGE="$IMAGE_CIRCUZZ_COVERAGE"
else
  IMAGE_CIRCOM_COVERAGE="$IMAGE_SMT_COVERAGE"
fi

if [[ "${IN_PODMAN:-0}" != "1" ]]; then
  podman run --rm \
    -v "$REPO_ROOT":/workspace \
    --workdir /workspace/evaluation/coverage \
    -e IN_PODMAN=1 \
    "$IMAGE_CIRCOM_COVERAGE" \
    bash -lc "./generate_report.sh $EXPERIMENT"
  exit $?
fi

mkdir -p "$REPORT_DIR"

SYSROOT="$(rustc --print sysroot)"
LLVM_PROFDATA=""
LLVM_COV=""

for candidate in \
  "$(find "$SYSROOT" -name llvm-profdata 2>/dev/null | head -1)" \
  "llvm-profdata"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    LLVM_PROFDATA="$candidate"
    break
  fi
done

for candidate in \
  "$(find "$SYSROOT" -name llvm-cov 2>/dev/null | head -1)" \
  "llvm-cov"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    LLVM_COV="$candidate"
    break
  fi
done

if [[ -z "$LLVM_PROFDATA" || -z "$LLVM_COV" ]]; then
  echo "ERROR: could not find llvm-profdata or llvm-cov" >&2
  echo "Ensure 'rustup component add llvm-tools-preview' was run in the image" >&2
  exit 1
fi

echo "[coverage] llvm-profdata: $LLVM_PROFDATA" >&2
echo "[coverage] llvm-cov:      $LLVM_COV" >&2

PROFRAW_COUNT=$(find "$PROFRAW_DIR" -name '*.profraw' | wc -l)
echo "[coverage] Found $PROFRAW_COUNT .profraw files" >&2

if [[ "$EXPERIMENT" == "smt-solver" || "$EXPERIMENT" == *_fusion_circom || "$EXPERIMENT" == circuzz-* || "$EXPERIMENT" == bool-vs-ff-* ]]; then
  MERGED_PROFDATA="$REPORT_DIR/circom.profdata"
  IGNORE_FILENAME_REGEX='^/rustc/'

  if [[ "$PROFRAW_COUNT" -eq 0 ]]; then
    if [[ -f "$MERGED_PROFDATA" ]]; then
      echo "[coverage] Reusing existing merged profdata: $MERGED_PROFDATA" >&2
    else
      echo "ERROR: no .profraw files found in $PROFRAW_DIR" >&2
      echo "No existing merged profdata found at $MERGED_PROFDATA either." >&2
      echo "Run the appropriate coverage.sh first to collect coverage data." >&2
      exit 1
    fi
  else
    echo "[coverage] Merging .profraw files..." >&2
    find "$PROFRAW_DIR" -name '*.profraw' | \
      xargs "$LLVM_PROFDATA" merge -sparse -o "$MERGED_PROFDATA"
    echo "[coverage] Merged profdata: $MERGED_PROFDATA ($(du -h "$MERGED_PROFDATA" | cut -f1))" >&2
  fi

  CIRCOM_BIN="$(which circom)"

  echo "[coverage] Generating HTML report..." >&2
  "$LLVM_COV" show \
    "$CIRCOM_BIN" \
    --instr-profile="$MERGED_PROFDATA" \
    --ignore-filename-regex="$IGNORE_FILENAME_REGEX" \
    --show-line-counts-or-regions \
    --show-instantiations=false \
    --format=html \
    --output-dir="$REPORT_DIR/html"

  echo "[coverage] Generating lcov report..." >&2
  "$LLVM_COV" export \
    "$CIRCOM_BIN" \
    --instr-profile="$MERGED_PROFDATA" \
    --format=lcov \
    --ignore-filename-regex="$IGNORE_FILENAME_REGEX" \
    > "$REPORT_DIR/circom_coverage.lcov"

  echo "[coverage] Summary:" >&2
  "$LLVM_COV" report \
    "$CIRCOM_BIN" \
    --instr-profile="$MERGED_PROFDATA" \
    --ignore-filename-regex="$IGNORE_FILENAME_REGEX" \
    | tee "$REPORT_DIR/summary.txt"

  echo "" >&2
  echo "[coverage] Reports written to $REPORT_DIR/" >&2
  echo "[coverage]   HTML:    $REPORT_DIR/html/index.html" >&2
  echo "[coverage]   LCOV:    $REPORT_DIR/circom_coverage.lcov" >&2
  echo "[coverage]   Summary: $REPORT_DIR/summary.txt" >&2
  exit 0
fi

MERGED_PROFDATA="$REPORT_DIR/testsuite.profdata"
OBJECT_LIST="$REPORT_DIR/coverage_objects.txt"
OBJECT_DIR="$OBJ_DIR/coverage_objects"
IGNORE_FILENAME_REGEX='^/rustc/|^/root/.cargo/registry/|^/root/.cargo/git/'
CIRCOM_ROOT="/circuzz/circom"

if [[ "$PROFRAW_COUNT" -eq 0 ]]; then
  if [[ -f "$MERGED_PROFDATA" ]]; then
    echo "[coverage] Reusing existing merged profdata: $MERGED_PROFDATA" >&2
  else
    echo "ERROR: no .profraw files found in $PROFRAW_DIR" >&2
    echo "No existing merged profdata found at $MERGED_PROFDATA either." >&2
    echo "Run ./test-suite/coverage.sh first to collect coverage data." >&2
    exit 1
  fi
else
  echo "[coverage] Merging .profraw files..." >&2
  find "$PROFRAW_DIR" -name '*.profraw' | \
    xargs "$LLVM_PROFDATA" merge -sparse -o "$MERGED_PROFDATA"
  echo "[coverage] Merged profdata: $MERGED_PROFDATA ($(du -h "$MERGED_PROFDATA" | cut -f1))" >&2
fi

mkdir -p "$OBJECT_DIR"

sync_current_test_objects() {
  rm -f "$OBJECT_DIR"/*
  find "$CIRCOM_ROOT/target/debug/deps" \
    -maxdepth 1 \
    -type f \
    -executable \
    ! -name '*.so' \
    -exec cp -fp {} "$OBJECT_DIR"/ \;

  if [[ -x "$CIRCOM_ROOT/target/debug/circom" ]]; then
    cp -fp "$CIRCOM_ROOT/target/debug/circom" "$OBJECT_DIR/"
  fi
}

write_object_list() {
  find "$OBJECT_DIR" \
    -maxdepth 1 \
    -type f \
    -executable \
    ! -name '*.so' \
    | sort > "$OBJECT_LIST"
}

if [[ "$PROFRAW_COUNT" -gt 0 ]]; then
  echo "[coverage] Saving current cargo test binaries..." >&2
  sync_current_test_objects
  write_object_list
elif [[ ! -d "$OBJECT_DIR" || -z "$(find "$OBJECT_DIR" -maxdepth 1 -type f -executable ! -name '*.so' -print -quit)" ]]; then
  echo "[coverage] Building cargo test harnesses..." >&2
  (
    cd "$CIRCOM_ROOT"
    LLVM_PROFILE_FILE="/tmp/circom-test-report-%p-%m.profraw" cargo test --workspace --no-run >/dev/null
  )
  rm -f /tmp/circom-test-report-*.profraw
  echo "[coverage] Test harness build complete" >&2
  sync_current_test_objects
  write_object_list
else
  write_object_list
fi

python3 - <<'PY' "$OBJECT_LIST"
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
seen = set()
items = []
for raw in path.read_text().splitlines():
    raw = raw.strip()
    if raw and raw not in seen:
        seen.add(raw)
        items.append(raw)
path.write_text("".join(f"{item}\n" for item in items))
PY

OBJECT_COUNT=$(wc -l < "$OBJECT_LIST")
echo "[coverage] Found $OBJECT_COUNT coverage objects" >&2

if [[ "$OBJECT_COUNT" -eq 0 ]]; then
  echo "ERROR: no test executables found under $CIRCOM_ROOT/target/debug/deps" >&2
  echo "Run ./test-suite/coverage.sh first so cargo test builds the test harnesses." >&2
  exit 1
fi

mapfile -t COVERAGE_OBJECTS < "$OBJECT_LIST"
PRIMARY_OBJECT="${COVERAGE_OBJECTS[0]}"
LLVM_OBJECT_ARGS=()
for object in "${COVERAGE_OBJECTS[@]}"; do
  LLVM_OBJECT_ARGS+=( "--object=$object" )
done

echo "[coverage] Generating HTML report..." >&2
"$LLVM_COV" show \
  "$PRIMARY_OBJECT" \
  "${LLVM_OBJECT_ARGS[@]}" \
  --instr-profile="$MERGED_PROFDATA" \
  --ignore-filename-regex="$IGNORE_FILENAME_REGEX" \
  --show-line-counts-or-regions \
  --show-instantiations=false \
  --format=html \
  --output-dir="$REPORT_DIR/html"

echo "[coverage] Generating lcov report..." >&2
"$LLVM_COV" export \
  "$PRIMARY_OBJECT" \
  "${LLVM_OBJECT_ARGS[@]}" \
  --instr-profile="$MERGED_PROFDATA" \
  --format=lcov \
  --ignore-filename-regex="$IGNORE_FILENAME_REGEX" \
  > "$REPORT_DIR/circom_testsuite_coverage.lcov"

echo "[coverage] Summary:" >&2
"$LLVM_COV" report \
  "$PRIMARY_OBJECT" \
  "${LLVM_OBJECT_ARGS[@]}" \
  --instr-profile="$MERGED_PROFDATA" \
  --ignore-filename-regex="$IGNORE_FILENAME_REGEX" \
  | tee "$REPORT_DIR/summary.txt"

echo "" >&2
echo "[coverage] Reports written to $REPORT_DIR/" >&2
echo "[coverage]   Objects: $OBJECT_LIST" >&2
echo "[coverage]   HTML:    $REPORT_DIR/html/index.html" >&2
echo "[coverage]   LCOV:    $REPORT_DIR/circom_testsuite_coverage.lcov" >&2
echo "[coverage]   Summary: $REPORT_DIR/summary.txt" >&2
