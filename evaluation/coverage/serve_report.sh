#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")

usage() {
  echo "usage: $0 <smt-solver|test-suite> [port]" >&2
  echo "       $0 diff [--exclude-folders folder1,folder2,...] [tool1 tool2 ...] [port]" >&2
  exit 1
}

if [[ "$#" -eq 0 ]]; then
  usage
fi

PORT="${PORT:-8000}"

if [[ "$1" == "diff" || "$1" == "differential" ]]; then
  shift

  EXCLUDED_FOLDERS=()
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --exclude-folders)
        [[ "$#" -ge 2 ]] || usage
        IFS=',' read -r -a RAW_EXCLUDED <<< "$2"
        for folder in "${RAW_EXCLUDED[@]}"; do
          folder="${folder//[[:space:]]/}"
          [[ -n "$folder" ]] || continue
          EXCLUDED_FOLDERS+=("$folder")
        done
        shift 2
        ;;
      --exclude-folders=*)
        VALUE="${1#*=}"
        IFS=',' read -r -a RAW_EXCLUDED <<< "$VALUE"
        for folder in "${RAW_EXCLUDED[@]}"; do
          folder="${folder//[[:space:]]/}"
          [[ -n "$folder" ]] || continue
          EXCLUDED_FOLDERS+=("$folder")
        done
        shift
        ;;
      *)
        break
        ;;
    esac
  done

  if [[ "$#" -ge 1 && "${!#}" =~ ^[0-9]+$ ]]; then
    PORT="${!#}"
    set -- "${@:1:$(($# - 1))}"
  fi

  TOOLS=()
  if [[ "$#" -eq 0 ]]; then
    shopt -s nullglob
    for candidate in "$SCRIPT_DIR"/obj/*; do
      [[ -d "$candidate" ]] || continue
      tool="$(basename "$candidate")"
      [[ "$tool" == "differential" ]] && continue
      REPORT_ROOT="$candidate/coverage_report"
      [[ -d "$REPORT_ROOT" ]] || continue
      LCOV_FILES=("$REPORT_ROOT"/*.lcov)
      if [[ "${#LCOV_FILES[@]}" -eq 1 ]]; then
        TOOLS+=("$tool")
      fi
    done
    shopt -u nullglob
    if [[ "${#TOOLS[@]}" -lt 2 ]]; then
      echo "ERROR: found fewer than two coverage tools under $SCRIPT_DIR/obj" >&2
      echo "Run coverage first or pass tool names explicitly." >&2
      exit 1
    fi
  else
    declare -A SEEN_TOOLS=()
    for tool in "$@"; do
      if [[ -n "${SEEN_TOOLS[$tool]:-}" ]]; then
        echo "ERROR: duplicate tool '$tool'" >&2
        exit 1
      fi
      SEEN_TOOLS[$tool]=1
      TOOLS+=("$tool")
    done
    if [[ "${#TOOLS[@]}" -lt 2 ]]; then
      usage
    fi
  fi

  mapfile -t SORTED_TOOLS < <(printf '%s\n' "${TOOLS[@]}" | sort)
  SLUG="${SORTED_TOOLS[0]}"
  for tool in "${SORTED_TOOLS[@]:1}"; do
    SLUG="${SLUG}__${tool}"
  done
  if [[ "${#EXCLUDED_FOLDERS[@]}" -gt 0 ]]; then
    mapfile -t SORTED_EXCLUDED < <(printf '%s\n' "${EXCLUDED_FOLDERS[@]}" | awk 'NF' | sort -u)
    EXCLUDED_SLUG="${SORTED_EXCLUDED[0]//\//-}"
    EXCLUDED_SLUG="${EXCLUDED_SLUG//./root}"
    for folder in "${SORTED_EXCLUDED[@]:1}"; do
      SAFE_FOLDER="${folder//\//-}"
      SAFE_FOLDER="${SAFE_FOLDER//./root}"
      EXCLUDED_SLUG="${EXCLUDED_SLUG}-${SAFE_FOLDER}"
    done
    SLUG="${SLUG}__exclude-${EXCLUDED_SLUG}"
  fi

  REPORT_DIR="$SCRIPT_DIR/obj/differential/$SLUG/html"
  if [[ ! -f "$REPORT_DIR/index.html" ]]; then
    echo "ERROR: differential coverage report not found at $REPORT_DIR/index.html" >&2
    if [[ "$#" -eq 0 ]]; then
      echo "Run ./generate_diff_report.py first." >&2
    else
      echo "Run ./generate_diff_report.py ${SORTED_TOOLS[*]} first." >&2
    fi
    exit 1
  fi

  echo "[coverage] Serving differential report for ${SORTED_TOOLS[*]} from $REPORT_DIR" >&2
  echo "[coverage] Open http://127.0.0.1:$PORT" >&2
  exec python3 -m http.server "$PORT" --directory "$REPORT_DIR"
fi

EXPERIMENT="${1:-}"
case "$EXPERIMENT" in
  smt-solver|test-suite) ;;
  *) usage ;;
esac

if [[ "$#" -ge 2 ]]; then
  PORT="$2"
fi

REPORT_DIR="$SCRIPT_DIR/obj/$EXPERIMENT/coverage_report/html"

if [[ ! -f "$REPORT_DIR/index.html" ]]; then
  echo "ERROR: coverage report not found at $REPORT_DIR/index.html" >&2
  echo "Run ./generate_report.sh $EXPERIMENT or ./$EXPERIMENT/coverage.sh first." >&2
  exit 1
fi

echo "[coverage] Serving $EXPERIMENT report from $REPORT_DIR" >&2
echo "[coverage] Open http://127.0.0.1:$PORT" >&2

exec python3 -m http.server "$PORT" --directory "$REPORT_DIR"
