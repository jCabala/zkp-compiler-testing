#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import sys

SOURCE_ROOT = "/circuzz/circom/"
TARGET_ROOT = "/circuzz/circom/target/"
FOLDER_OVERVIEWS = {
    "circom": [
        "This is the compiler's command-line frontend. It parses user input, runs the main analysis and execution pipeline, and dispatches output generation.",
        "User-facing configuration, flag handling, and the top-level orchestration logic live here."
    ],
    "circom_algebra": [
        "This folder provides the core algebra layer for the compiler. It defines modular arithmetic, symbolic expressions, substitutions, constraints, and simplification helpers.",
        "Many later stages build on these data structures when transforming Circom programs into constraint systems."
    ],
    "code_producers": [
        "This folder contains backend code generators. It emits C++ and WebAssembly witness-generation code and related support fragments from the compiler's lowered representations.",
        "When coverage lands here, it usually reflects the final code emission path rather than parsing or semantic analysis."
    ],
    "compiler": [
        "This is the compiler middle-end. It owns higher-level circuit design logic, intermediate representations, and the translation steps that prepare analyzed programs for backend generation.",
        "Coverage here usually means the run exercised substantial lowering and optimization logic."
    ],
    "constant_tracking": [
        "This is a small utility crate for interning constants and assigning stable IDs. It helps other compiler stages reuse and look up constant values efficiently.",
        "It is infrastructural rather than user-facing, so coverage here tends to be narrow and incidental."
    ],
    "constraint_generation": [
        "This folder turns analyzed programs into executable constraint-system structures. It drives instantiation, execution-style traversal, and the main build path that produces constraints, DAGs, and related outputs.",
        "Large coverage here usually indicates the run exercised real compilation work rather than only unit-level helpers."
    ],
    "constraint_list": [
        "This folder manages flattened constraint collections and their simplification passes. It also contains logic for porting those constraints into export-friendly forms.",
        "Coverage here often reflects optimization and serialization-adjacent processing after constraint generation."
    ],
    "constraint_writers": [
        "This folder is the output boundary for constraint artifacts. It provides writers for R1CS, symbol files, debug logs, JSON exports, and related serialized formats.",
        "Coverage here usually means the run reached artifact emission rather than stopping earlier in the pipeline."
    ],
    "dag": [
        "This folder implements the DAG representation of instantiated circuits. It preserves structural information about components and supports traversal, export, and mapping into flatter encodings.",
        "Coverage here suggests the run exercised structure-aware compilation paths rather than only final flattened constraints."
    ],
    "parser": [
        "This folder implements Circom source parsing. It handles include resolution, grammar-driven parsing, syntax-sugar removal, and construction of the initial program archive.",
        "Coverage here is strongest when the workload explores diverse surface-language features and file-layout patterns."
    ],
    "program_structure": [
        "This folder provides the shared program model used across the compiler. It contains AST definitions, file and diagnostic infrastructure, symbol metadata, and common utility types.",
        "It is a foundational crate, so many phases touch it indirectly even when the main logic lives elsewhere."
    ],
    "type_analysis": [
        "This folder performs semantic checks and type-oriented analysis over parsed Circom programs. It contains analyzers and decorators that validate programs and enrich them before constraint generation.",
        "Coverage here reflects how much of the language's semantic surface a workload is exercising."
    ],
}


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def usage(program_name: str) -> int:
    eprint(f"usage: {program_name} [--exclude-folders folder1,folder2,...] [tool1 tool2 ...]")
    eprint(f"example: {program_name}")
    eprint(f"example: {program_name} smt-solver test-suite")
    eprint(f"example: {program_name} --exclude-folders parser,dag smt-solver test-suite")
    return 1


def discover_tools(obj_root: Path) -> list[str]:
    tools = []
    for candidate in sorted(obj_root.iterdir()):
        if not candidate.is_dir() or candidate.name == "differential":
            continue
        report_root = candidate / "coverage_report"
        if not report_root.is_dir():
            continue
        lcov_files = sorted(path for path in report_root.glob("*.lcov") if path.is_file())
        if len(lcov_files) == 1:
            tools.append(candidate.name)
    return tools


def parse_excluded_folders(raw_value: str) -> list[str]:
    folders = []
    for raw_folder in raw_value.split(","):
        folder = raw_folder.strip()
        if folder:
            folders.append(folder)
    if not folders:
        raise ValueError("ERROR: --exclude-folders requires at least one folder name")
    return folders


def parse_cli_args(argv: list[str], obj_root: Path) -> tuple[list[str], list[str]]:
    args = argv[1:]
    excluded_folders: list[str] = []
    tool_args: list[str] = []
    index = 0

    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            raise ValueError("usage")
        if arg == "--exclude-folders":
            if index + 1 >= len(args):
                raise ValueError("ERROR: --exclude-folders requires a comma-separated list")
            excluded_folders.extend(parse_excluded_folders(args[index + 1]))
            index += 2
            continue
        if arg.startswith("--exclude-folders="):
            excluded_folders.extend(parse_excluded_folders(arg.split("=", 1)[1]))
            index += 1
            continue
        tool_args.append(arg)
        index += 1

    seen_excluded: set[str] = set()
    normalized_excluded_folders: list[str] = []
    for folder in excluded_folders:
        if folder in seen_excluded:
            continue
        seen_excluded.add(folder)
        normalized_excluded_folders.append(folder)

    tools = parse_tools([argv[0], *tool_args], obj_root)
    return tools, sorted(normalized_excluded_folders)


def parse_tools(argv: list[str], obj_root: Path) -> list[str]:
    if len(argv) == 1:
        tools = discover_tools(obj_root)
        if len(tools) < 2:
            raise ValueError(
                "ERROR: found fewer than two coverage tools under obj/\n"
                "Run coverage first, or pass tool names explicitly."
            )
        return tools

    seen_tools: set[str] = set()
    tools: list[str] = []
    for tool in argv[1:]:
        if tool in seen_tools:
            raise ValueError(f"ERROR: duplicate tool '{tool}'")
        seen_tools.add(tool)
        tools.append(tool)

    if len(tools) < 2:
        raise ValueError("usage")

    return sorted(tools)


def slugify_tools(tools: list[str]) -> str:
    return "__".join(tools)


def slugify_folder_name(folder: str) -> str:
    return folder.replace("/", "-").replace(".", "root")


def slugify_report(tools: list[str], excluded_folders: list[str]) -> str:
    slug = slugify_tools(tools)
    if not excluded_folders:
        return slug
    excluded_slug = "-".join(slugify_folder_name(folder) for folder in excluded_folders)
    return f"{slug}__exclude-{excluded_slug}"


def find_lcov_inputs(obj_root: Path, tools: list[str]) -> dict[str, Path]:
    lcov_inputs: dict[str, Path] = {}
    for tool in tools:
        report_root = obj_root / tool / "coverage_report"
        if not report_root.is_dir():
            raise FileNotFoundError(
                f"ERROR: coverage report directory not found for '{tool}': {report_root}\n"
                f"Run ./{tool}/coverage.sh or ./generate_report.sh {tool} first."
            )

        lcov_files = sorted(path for path in report_root.glob("*.lcov") if path.is_file())
        if not lcov_files:
            raise FileNotFoundError(
                f"ERROR: no LCOV report found for '{tool}' under {report_root}\n"
                f"Run ./generate_report.sh {tool} first."
            )
        if len(lcov_files) > 1:
            file_list = "\n".join(f"  {path}" for path in lcov_files)
            raise FileExistsError(
                f"ERROR: expected exactly one LCOV report for '{tool}' under {report_root}\n{file_list}"
            )

        eprint(f"[coverage] Using {tool} LCOV: {lcov_files[0]}")
        lcov_inputs[tool] = lcov_files[0]

    return lcov_inputs


def write_lcov_inputs(
    path: Path,
    lcov_inputs: dict[str, Path],
    tools: list[str],
    excluded_folders: list[str],
) -> None:
    lines = []
    if excluded_folders:
        lines.append(f"# excluded_folders\t{','.join(excluded_folders)}")
    lines.extend(f"{tool}\t{lcov_inputs[tool]}" for tool in tools)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_lcov(path: Path) -> dict[str, dict[str, set[int]]]:
    per_file: dict[str, dict[str, set[int]]] = {}
    current_file: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("SF:"):
            candidate = line[3:]
            if candidate.startswith(SOURCE_ROOT) and not candidate.startswith(TARGET_ROOT):
                current_file = candidate
                per_file.setdefault(
                    current_file,
                    {"covered": set(), "executable": set()},
                )
            else:
                current_file = None
            continue
        if line == "end_of_record":
            current_file = None
            continue
        if current_file is None or not line.startswith("DA:"):
            continue

        payload = line[3:].split(",")
        if len(payload) < 2:
            continue

        try:
            line_no = int(payload[0])
            count = int(payload[1])
        except ValueError:
            continue

        per_file[current_file]["executable"].add(line_no)
        if count > 0:
            per_file[current_file]["covered"].add(line_no)

    return dict(per_file)


def format_signature(signature: tuple[str, ...], tools: list[str]) -> str:
    if len(signature) == len(tools):
        return "shared by all tools"
    if len(signature) == 1:
        return f"{signature[0]} only"
    return " + ".join(signature)


def compress_lines(lines: list[int]) -> str:
    if not lines:
        return "-"
    ranges: list[str] = []
    start = prev = lines[0]
    for value in lines[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = value
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ",".join(ranges)


def format_percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "-"
    return f"{(100.0 * numerator / denominator):.2f}%"


def format_coverage_stat(covered: int, executable: int) -> str:
    return f"{covered}/{executable} ({format_percent(covered, executable)})"


def normalize_path(path: str) -> str:
    return path[len(SOURCE_ROOT):] if path.startswith(SOURCE_ROOT) else path


def top_level_folder(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "."


def path_within_folder(path: str) -> str:
    parts = path.split("/", 1)
    return parts[1] if len(parts) == 2 else path


def folder_overview(folder: str) -> list[str]:
    return FOLDER_OVERVIEWS.get(
        folder,
        [
            "This folder is part of the Circom compiler workspace.",
            "The differential report generator does not have a custom description for it yet."
        ],
    )


def signature_sort_key(
    signature: tuple[str, ...], count: int, tools: list[str]
) -> tuple[int, int, int, str]:
    if len(signature) == len(tools):
        bucket = 0
    elif len(signature) == 1:
        bucket = 1
    else:
        bucket = 2
    return (bucket, -count, -len(signature), format_signature(signature, tools))


def build_report(
    lcov_inputs: dict[str, Path],
    tools: list[str],
    excluded_folders: list[str],
) -> dict[str, object]:
    tool_data = {tool: parse_lcov(path) for tool, path in lcov_inputs.items()}
    all_files = sorted({path for data in tool_data.values() for path in data})
    full_signature = tuple(tools)
    per_file_reports = []

    for file_path in all_files:
        per_tool_coverage = {
            tool: tool_data[tool].get(file_path, {"covered": set(), "executable": set()})
            for tool in tools
        }
        per_tool_lines = {
            tool: per_tool_coverage[tool]["covered"]
            for tool in tools
        }
        per_tool_executable_lines = {
            tool: per_tool_coverage[tool]["executable"]
            for tool in tools
        }
        union_executable_lines = sorted(set().union(*per_tool_executable_lines.values()))
        if not union_executable_lines:
            continue

        union_lines = sorted(set().union(*per_tool_lines.values()))
        intersection = set(union_lines)
        executable_intersection = set(union_executable_lines)
        for tool in tools:
            intersection &= per_tool_lines[tool]
            executable_intersection &= per_tool_executable_lines[tool]

        signature_counts: Counter[tuple[str, ...]] = Counter()
        signature_lines: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for line_no in union_lines:
            signature = tuple(tool for tool in tools if line_no in per_tool_lines[tool])
            signature_counts[signature] += 1
            signature_lines[signature].append(line_no)

        has_differences = any(signature != full_signature for signature in signature_counts)
        diff_line_count = sum(
            count for signature, count in signature_counts.items() if signature != full_signature
        )

        signature_entries = []
        for signature, count in sorted(
            signature_counts.items(),
            key=lambda item: signature_sort_key(item[0], item[1], tools),
        ):
            signature_entries.append(
                {
                    "signature": list(signature),
                    "label": format_signature(signature, tools),
                    "count": count,
                    "ranges": compress_lines(signature_lines[signature]),
                }
            )

        display_path = normalize_path(file_path)
        per_file_reports.append(
            {
                "path": file_path,
                "display_path": display_path,
                "top_level_folder": top_level_folder(display_path),
                "path_within_folder": path_within_folder(display_path),
                "excluded_from_totals": top_level_folder(display_path) in set(excluded_folders),
                "covered_lines_any": len(union_lines),
                "covered_lines_all": len(intersection),
                "executable_lines_any": len(union_executable_lines),
                "executable_lines_all": len(executable_intersection),
                "diff_line_count": diff_line_count,
                "has_differences": has_differences,
                "covered_lines_by_tool": {tool: len(per_tool_lines[tool]) for tool in tools},
                "executable_lines_by_tool": {
                    tool: len(per_tool_executable_lines[tool]) for tool in tools
                },
                "tool_lines": {tool: sorted(per_tool_lines[tool]) for tool in tools},
                "tool_executable_lines": {
                    tool: sorted(per_tool_executable_lines[tool]) for tool in tools
                },
                "signatures": signature_entries,
            }
        )

    per_file_reports.sort(
        key=lambda item: (
            not item["has_differences"],
            -item["diff_line_count"],
            -item["covered_lines_any"],
            item["display_path"],
        )
    )

    folders_by_name: dict[str, dict[str, object]] = {}
    for item in per_file_reports:
        folder_name = item["top_level_folder"]
        folder = folders_by_name.setdefault(
            folder_name,
            {
                "folder": folder_name,
                "overview": folder_overview(folder_name),
                "excluded_from_totals": folder_name in set(excluded_folders),
                "files_seen": 0,
                "files_with_differences": 0,
                "covered_lines_any": 0,
                "covered_lines_all": 0,
                "executable_lines_any": 0,
                "executable_lines_all": 0,
                "diff_line_count": 0,
                "covered_lines_by_tool": {tool: 0 for tool in tools},
                "executable_lines_by_tool": {tool: 0 for tool in tools},
                "covered_lines_unique_to_tool": {tool: 0 for tool in tools},
                "files": [],
            },
        )
        folder["files_seen"] += 1
        folder["files_with_differences"] += int(item["has_differences"])
        folder["covered_lines_any"] += item["covered_lines_any"]
        folder["covered_lines_all"] += item["covered_lines_all"]
        folder["executable_lines_any"] += item["executable_lines_any"]
        folder["executable_lines_all"] += item["executable_lines_all"]
        folder["diff_line_count"] += item["diff_line_count"]
        for tool in tools:
            folder["covered_lines_by_tool"][tool] += item["covered_lines_by_tool"][tool]
            folder["executable_lines_by_tool"][tool] += item["executable_lines_by_tool"][tool]
        for signature in item["signatures"]:
            if len(signature["signature"]) == 1:
                folder["covered_lines_unique_to_tool"][signature["signature"][0]] += signature["count"]
        folder["files"].append(item)

    folder_reports = sorted(
        folders_by_name.values(),
        key=lambda item: (
            item["folder"] == ".",
            item["folder"],
        ),
    )

    excluded_folder_set = set(excluded_folders)
    included_files = [
        item for item in per_file_reports if item["top_level_folder"] not in excluded_folder_set
    ]
    included_folders = [
        folder for folder in folder_reports if folder["folder"] not in excluded_folder_set
    ]

    summary_signature_counts: Counter[tuple[str, ...]] = Counter()
    per_tool_total_lines = {tool: 0 for tool in tools}
    per_tool_total_executable_lines = {tool: 0 for tool in tools}
    per_tool_unique_lines = {tool: 0 for tool in tools}
    for item in included_files:
        for tool in tools:
            per_tool_total_lines[tool] += item["covered_lines_by_tool"][tool]
            per_tool_total_executable_lines[tool] += item["executable_lines_by_tool"][tool]
        for signature in item["signatures"]:
            signature_tuple = tuple(signature["signature"])
            summary_signature_counts[signature_tuple] += signature["count"]
            if len(signature_tuple) == 1:
                per_tool_unique_lines[signature_tuple[0]] += signature["count"]

    global_signature_entries = [
        {
            "signature": list(signature),
            "label": format_signature(signature, tools),
            "count": count,
        }
        for signature, count in sorted(
            summary_signature_counts.items(),
            key=lambda item: signature_sort_key(item[0], item[1], tools),
        )
    ]

    return {
        "tools": tools,
        "excluded_folders": excluded_folders,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lcov_inputs": {tool: str(path) for tool, path in lcov_inputs.items()},
        "folder_overviews": {folder: folder_overview(folder) for folder in folders_by_name},
        "summary": {
            "folder_count": len(included_folders),
            "files_seen": len(included_files),
            "files_with_differences": sum(
                int(item["has_differences"]) for item in included_files
            ),
            "covered_lines_any": sum(item["covered_lines_any"] for item in included_files),
            "covered_lines_all": sum(item["covered_lines_all"] for item in included_files),
            "executable_lines_any": sum(
                item["executable_lines_any"] for item in included_files
            ),
            "executable_lines_all": sum(
                item["executable_lines_all"] for item in included_files
            ),
            "covered_lines_unique_to_tool": per_tool_unique_lines,
            "covered_lines_by_tool": per_tool_total_lines,
            "executable_lines_by_tool": per_tool_total_executable_lines,
            "coverage_signatures": global_signature_entries,
        },
        "folders": folder_reports,
        "files": per_file_reports,
    }


def build_summary_text(report: dict[str, object]) -> str:
    tools = report["tools"]
    summary = report["summary"]
    folders = report["folders"]
    files = report["files"]
    excluded_folders = report["excluded_folders"]
    included_folders = [folder for folder in folders if not folder["excluded_from_totals"]]
    included_files = [item for item in files if not item["excluded_from_totals"]]

    summary_lines = [
        "Differential coverage report",
        f"Tools: {', '.join(tools)}",
        f"Generated: {report['generated_at']}",
        "Excluded folders from totals: "
        + (", ".join(excluded_folders) if excluded_folders else "none"),
        "",
        "Summary",
        f"  Folders seen: {summary['folder_count']}",
        f"  Files seen: {summary['files_seen']}",
        f"  Files with differences: {summary['files_with_differences']}",
        "  Covered lines by any tool: "
        f"{format_coverage_stat(summary['covered_lines_any'], summary['executable_lines_any'])}",
        "  Covered lines by all tools: "
        f"{format_coverage_stat(summary['covered_lines_all'], summary['executable_lines_all'])}",
        "",
        "Per tool",
    ]

    for tool in tools:
        summary_lines.append(
            "  "
            f"{tool}: covered={format_coverage_stat(summary['covered_lines_by_tool'][tool], summary['executable_lines_by_tool'][tool])}, "
            f"unique_vs_others={summary['covered_lines_unique_to_tool'][tool]}"
        )

    summary_lines.extend(["", "Coverage signatures"])
    for entry in summary["coverage_signatures"]:
        summary_lines.append(f"  {entry['label']}: {entry['count']}")

    summary_lines.extend(["", "Per folder"])
    for folder in sorted(
        included_folders,
        key=lambda item: (-item["diff_line_count"], -item["covered_lines_any"], item["folder"]),
    )[:20]:
        summary_lines.append(
            "  "
            f"{folder['folder']}: files={folder['files_seen']}, diff_files={folder['files_with_differences']}, "
            f"diff={folder['diff_line_count']}, "
            f"any={format_coverage_stat(folder['covered_lines_any'], folder['executable_lines_any'])}, "
            f"all={format_coverage_stat(folder['covered_lines_all'], folder['executable_lines_all'])}"
        )

    if excluded_folders:
        summary_lines.extend(["", "Excluded folders"])
        for folder in sorted(
            [folder for folder in folders if folder["excluded_from_totals"]],
            key=lambda item: item["folder"],
        ):
            summary_lines.append(
                "  "
                f"{folder['folder']}: files={folder['files_seen']}, diff_files={folder['files_with_differences']}, "
                f"diff={folder['diff_line_count']}, "
                f"any={format_coverage_stat(folder['covered_lines_any'], folder['executable_lines_any'])}, "
                f"all={format_coverage_stat(folder['covered_lines_all'], folder['executable_lines_all'])}"
            )

    summary_lines.extend(["", "Top differing files"])
    top_diffs = [item for item in included_files if item["has_differences"]][:50]
    if not top_diffs:
        summary_lines.append("  None")
    else:
        for item in top_diffs:
            summary_lines.append(
                "  "
                f"{item['display_path']}: diff={item['diff_line_count']}, "
                f"any={format_coverage_stat(item['covered_lines_any'], item['executable_lines_any'])}, "
                f"all={format_coverage_stat(item['covered_lines_all'], item['executable_lines_all'])}"
            )

    return "\n".join(summary_lines) + "\n"


def build_html(report: dict[str, object]) -> str:
    tools = report["tools"]
    summary = report["summary"]
    folders = report["folders"]
    excluded_folders = report["excluded_folders"]
    report_json = json.dumps(report, separators=(",", ":")).replace("</", "<\\/")
    exclusion_note = (
        "Totals exclude: " + ", ".join(excluded_folders)
        if excluded_folders
        else "No folders excluded from totals."
    )

    tool_rows = "\n".join(
        f"<tr><td>{escape(tool)}</td>"
        f"<td>{escape(format_coverage_stat(summary['covered_lines_by_tool'][tool], summary['executable_lines_by_tool'][tool]))}</td>"
        f"<td>{summary['covered_lines_unique_to_tool'][tool]}</td></tr>"
        for tool in tools
    )

    signature_rows = "\n".join(
        f"<tr><td>{escape(entry['label'])}</td><td>{entry['count']}</td></tr>"
        for entry in summary["coverage_signatures"]
    )

    folder_header_cells = "".join(f"<th>{escape(tool)}</th>" for tool in tools)
    folder_rows = "\n".join(
        "<tr>"
        f"<td><code>{escape(folder['folder'])}</code>{' <span class=\"status-badge excluded\">excluded</span>' if folder['excluded_from_totals'] else ''}</td>"
        f"<td>{''.join(f'<p class=\"overview-cell-paragraph\">{escape(paragraph)}</p>' for paragraph in folder['overview'])}</td>"
        f"<td>{folder['files_seen']}</td>"
        f"<td>{folder['files_with_differences']}</td>"
        f"<td>{folder['diff_line_count']}</td>"
        f"<td>{escape(format_coverage_stat(folder['covered_lines_any'], folder['executable_lines_any']))}</td>"
        f"<td>{escape(format_coverage_stat(folder['covered_lines_all'], folder['executable_lines_all']))}</td>"
        + "".join(
            f"<td>{escape(format_coverage_stat(folder['covered_lines_by_tool'][tool], folder['executable_lines_by_tool'][tool]))}</td>"
            for tool in tools
        )
        + "</tr>"
        for folder in sorted(
            folders,
            key=lambda item: (-item["diff_line_count"], -item["covered_lines_any"], item["folder"]),
        )
    )

    folder_sections = []
    for folder in folders:
        file_sections = []
        for item in folder["files"]:
            if item["covered_lines_any"] == 0:
                continue
            signature_rows_html = "\n".join(
                "<tr>"
                f"<td>{escape(signature['label'])}</td>"
                f"<td>{signature['count']}</td>"
                f"<td><code>{escape(signature['ranges'])}</code></td>"
                "</tr>"
                for signature in item["signatures"]
            )
            totals = " | ".join(
                f"{tool}: {format_coverage_stat(item['covered_lines_by_tool'][tool], item['executable_lines_by_tool'][tool])}"
                for tool in tools
            )
            file_sections.append(
                f"""
        <details class="file-card">
          <summary>
            <span class="file-path">{escape(item['path_within_folder'])}</span>
            <span class="file-meta">diff lines: {item['diff_line_count']} | covered by any: {escape(format_coverage_stat(item['covered_lines_any'], item['executable_lines_any']))} | covered by all: {escape(format_coverage_stat(item['covered_lines_all'], item['executable_lines_all']))}</span>
          </summary>
          <p class="tool-breakdown">{escape(totals)}</p>
          <table>
            <thead>
              <tr><th>Coverage signature</th><th>Lines</th><th>Line numbers</th></tr>
            </thead>
            <tbody>
              {signature_rows_html}
            </tbody>
          </table>
        </details>
        """
            )

        folder_totals = " | ".join(
            f"{tool}: covered={format_coverage_stat(folder['covered_lines_by_tool'][tool], folder['executable_lines_by_tool'][tool])}, unique={folder['covered_lines_unique_to_tool'][tool]}"
            for tool in tools
        )
        folder_overview_html = "".join(
            f'<p class="folder-overview">{escape(paragraph)}</p>'
            for paragraph in folder["overview"]
        )
        folder_badge_html = (
            ' <span class="status-badge excluded">excluded from totals</span>'
            if folder["excluded_from_totals"]
            else ""
        )
        folder_sections.append(
            f"""
        <details class="folder-card">
          <summary>
            <span class="folder-path">{escape(folder['folder'])}{folder_badge_html}</span>
            <span class="folder-meta">files: {folder['files_seen']} | diff files: {folder['files_with_differences']} | diff lines: {folder['diff_line_count']} | covered by any: {escape(format_coverage_stat(folder['covered_lines_any'], folder['executable_lines_any']))} | covered by all: {escape(format_coverage_stat(folder['covered_lines_all'], folder['executable_lines_all']))}</span>
          </summary>
          {folder_overview_html}
          <p class="tool-breakdown">{escape(folder_totals)}</p>
          {''.join(file_sections)}
        </details>
        """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Differential Coverage Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f1e8;
      --panel: #fffaf0;
      --ink: #1f1a14;
      --muted: #6a6258;
      --line: #d8cdbd;
      --accent: #8a3b12;
      --accent-soft: #f1dfcf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(138, 59, 18, 0.12), transparent 28%),
        linear-gradient(180deg, #fbf7f0 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }}
    h1, h2 {{
      margin: 0 0 12px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    p {{
      margin: 0 0 12px;
      line-height: 1.5;
    }}
    .lede {{
      color: var(--muted);
      max-width: 72ch;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin: 24px 0;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 10px 30px rgba(31, 26, 20, 0.04);
    }}
    .tool-picker-card {{
      background: rgba(255, 250, 240, 0.82);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 10px 30px rgba(31, 26, 20, 0.04);
    }}
    .tool-picker-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }}
    .tool-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      cursor: pointer;
      font-size: 0.95rem;
    }}
    .tool-chip input {{
      margin: 0;
      accent-color: var(--accent);
    }}
    .button-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }}
    button {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 999px;
      padding: 8px 12px;
      cursor: pointer;
      font: inherit;
    }}
    .metric {{
      font-size: 1.9rem;
      font-weight: 700;
      color: var(--accent);
    }}
    .label {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .detail {{
      color: var(--muted);
      font-size: 0.88rem;
      margin-top: 6px;
      line-height: 1.4;
    }}
    .status-badge {{
      display: inline-block;
      margin-left: 8px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.74rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      vertical-align: middle;
      text-transform: uppercase;
    }}
    .status-badge.excluded {{
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid rgba(138, 59, 18, 0.2);
    }}
    section {{
      margin-top: 28px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid var(--line);
    }}
    th {{
      background: var(--accent-soft);
      font-size: 0.95rem;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    code {{
      font-family: "SFMono-Regular", "Consolas", monospace;
      font-size: 0.92rem;
      word-break: break-word;
    }}
    .folder-card,
    .file-card {{
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel);
      overflow: hidden;
    }}
    .folder-card {{
      margin-top: 16px;
      box-shadow: 0 10px 30px rgba(31, 26, 20, 0.04);
    }}
    .folder-card > summary,
    .file-card summary {{
      list-style: none;
      cursor: pointer;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .folder-card > summary {{
      padding: 16px 18px;
      background: rgba(138, 59, 18, 0.08);
    }}
    .folder-card > summary::-webkit-details-marker,
    .file-card summary::-webkit-details-marker {{
      display: none;
    }}
    .folder-card[open] > summary {{
      background: rgba(138, 59, 18, 0.12);
    }}
    .file-card[open] summary {{
      background: rgba(138, 59, 18, 0.06);
    }}
    .folder-path,
    .file-path {{
      font-weight: 700;
    }}
    .folder-meta,
    .file-meta, .tool-breakdown {{
      color: var(--muted);
    }}
    .folder-overview {{
      padding: 0 16px;
      margin: 12px 0 0;
      color: var(--ink);
    }}
    .overview-cell-paragraph {{
      margin: 0 0 8px;
      max-width: 42ch;
    }}
    .overview-cell-paragraph:last-child {{
      margin-bottom: 0;
    }}
    .selection-note, .empty-state {{
      color: var(--muted);
    }}
    .tool-breakdown {{
      padding: 0 16px 14px;
      margin: 10px 0 0;
    }}
    .footer {{
      margin-top: 24px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    @media (max-width: 720px) {{
      main {{
        padding: 24px 14px 48px;
      }}
      th, td {{
        padding: 8px 10px;
      }}
      .metric {{
        font-size: 1.55rem;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Differential Coverage Report</h1>
    <p class="lede" id="lede">This report compares covered Circom repository source lines across {escape(', '.join(tools))}. It ignores dependency code and generated files under <code>target/</code>. The "coverage signature" for a line is the exact set of tools that covered it, which makes the report scale cleanly when more experiments are added later.</p>

    <section class="tool-picker-card">
      <h2>Compare Tools</h2>
      <p class="selection-note" id="selection-note">Currently showing: {escape(', '.join(tools))}</p>
      <div id="tool-picker">
        <div class="tool-picker-grid">
          {''.join(f'<label class="tool-chip"><input type="checkbox" checked data-tool="{escape(tool)}"> {escape(tool)}</label>' for tool in tools)}
        </div>
      </div>
      <div class="button-row">
        <button type="button" id="select-all-tools">Select all</button>
      </div>
    </section>

    <section class="tool-picker-card">
      <h2>Folder Totals Scope</h2>
      <p class="selection-note" id="exclusion-note">{escape(exclusion_note)}</p>
      <p class="selection-note">Checked folders count toward totals. Unchecked folders still stay visible below.</p>
      <div id="folder-picker">
        <div class="tool-picker-grid">
          {''.join(
              f'<label class="tool-chip"><input type="checkbox" {"checked" if not folder["excluded_from_totals"] else ""} data-folder="{escape(folder["folder"])}"> {escape(folder["folder"])}</label>'
              for folder in folders
          )}
        </div>
      </div>
      <div class="button-row">
        <button type="button" id="include-all-folders">Include all</button>
        <button type="button" id="exclude-all-folders">Exclude all</button>
      </div>
    </section>

    <div class="card-grid">
      <div class="card">
        <div class="metric" id="metric-folder-count">{summary['folder_count']}</div>
        <div class="label">folders in totals</div>
      </div>
      <div class="card">
        <div class="metric" id="metric-files-seen">{summary['files_seen']}</div>
        <div class="label">files in scope</div>
      </div>
      <div class="card">
        <div class="metric" id="metric-files-diff">{summary['files_with_differences']}</div>
        <div class="label">files with differential coverage</div>
      </div>
      <div class="card">
        <div class="metric" id="metric-lines-any">{summary['covered_lines_any']}</div>
        <div class="label">lines covered by any tool</div>
        <div class="detail" id="metric-lines-any-detail">{escape(format_percent(summary['covered_lines_any'], summary['executable_lines_any']))} of {summary['executable_lines_any']} executable lines</div>
      </div>
      <div class="card">
        <div class="metric" id="metric-lines-all">{summary['covered_lines_all']}</div>
        <div class="label">lines covered by all tools</div>
        <div class="detail" id="metric-lines-all-detail">{escape(format_percent(summary['covered_lines_all'], summary['executable_lines_all']))} of {summary['executable_lines_all']} shared executable lines</div>
      </div>
    </div>

    <section>
      <h2>Per Tool</h2>
      <table>
        <thead>
          <tr><th>Tool</th><th>Coverage</th><th>Unique vs others</th></tr>
        </thead>
        <tbody id="tool-rows">
          {tool_rows}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Coverage Signatures</h2>
      <table>
        <thead>
          <tr><th>Signature</th><th>Covered lines</th></tr>
        </thead>
        <tbody id="signature-rows">
          {signature_rows}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Folder Overview</h2>
      <table>
        <thead id="folder-table-head">
          <tr><th>Folder</th><th>Overview</th><th>Files</th><th>Diff files</th><th>Diff lines</th><th>Any coverage</th><th>All-tools coverage</th>{folder_header_cells}</tr>
        </thead>
        <tbody id="folder-rows">
          {folder_rows}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Per-Folder File Differences</h2>
      <div id="folder-sections">
        {''.join(folder_sections)}
      </div>
    </section>

    <p class="footer">Generated at {escape(report['generated_at'])}. Raw data: <code>report.json</code>. Compact summary: <code>summary.txt</code>.</p>
  </main>
  <script id="report-data" type="application/json">{report_json}</script>
  <script>
    (() => {{
      const baseReport = JSON.parse(document.getElementById("report-data").textContent);
      const selected = new Set(baseReport.tools);
      const excluded = new Set(baseReport.excluded_folders || []);
      const toolOrder = (tools) => baseReport.tools.filter((tool) => tools.includes(tool));
      const escapeHtml = (value) => String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
      const formatPercent = (covered, executable) =>
        executable > 0 ? `${{((100 * covered) / executable).toFixed(2)}}%` : "-";
      const formatCoverageStat = (covered, executable) =>
        `${{covered}}/${{executable}} (${{formatPercent(covered, executable)}})`;

      const formatSignature = (signature, tools) => {{
        if (signature.length === tools.length) {{
          return "shared by all tools";
        }}
        if (signature.length === 1) {{
          return `${{signature[0]}} only`;
        }}
        return signature.join(" + ");
      }};

      const compressLines = (lines) => {{
        if (!lines.length) {{
          return "-";
        }}
        const ranges = [];
        let start = lines[0];
        let prev = lines[0];
        for (const value of lines.slice(1)) {{
          if (value === prev + 1) {{
            prev = value;
            continue;
          }}
          ranges.push(start === prev ? `${{start}}` : `${{start}}-${{prev}}`);
          start = value;
          prev = value;
        }}
        ranges.push(start === prev ? `${{start}}` : `${{start}}-${{prev}}`);
        return ranges.join(",");
      }};

      const signatureBucket = (signature, tools) => {{
        if (signature.length === tools.length) {{
          return 0;
        }}
        if (signature.length === 1) {{
          return 1;
        }}
        return 2;
      }};

      const compareSignatureEntries = (left, right, tools) => {{
        const bucketDiff = signatureBucket(left.signature, tools) - signatureBucket(right.signature, tools);
        if (bucketDiff !== 0) {{
          return bucketDiff;
        }}
        if (right.count !== left.count) {{
          return right.count - left.count;
        }}
        if (right.signature.length !== left.signature.length) {{
          return right.signature.length - left.signature.length;
        }}
        return left.label.localeCompare(right.label);
      }};

      const computeDerived = (selectedToolsInput, excludedFoldersInput) => {{
        const tools = toolOrder(selectedToolsInput);
        const excludedFolders = new Set(excludedFoldersInput);
        const perToolTotalLines = Object.fromEntries(tools.map((tool) => [tool, 0]));
        const perToolTotalExecutableLines = Object.fromEntries(tools.map((tool) => [tool, 0]));
        const perToolUniqueLines = Object.fromEntries(tools.map((tool) => [tool, 0]));
        const globalSignatureCounts = new Map();
        const files = [];
        let filesWithDifferences = 0;
        let totalLinesAny = 0;
        let totalLinesAll = 0;
        let totalExecutableLinesAny = 0;
        let totalExecutableLinesAll = 0;
        const signatureKeyOf = (signature) => signature.join("\\u001f");

        for (const baseItem of baseReport.files) {{
          const toolLines = Object.fromEntries(tools.map((tool) => [tool, baseItem.tool_lines[tool] || []]));
          const toolExecutableLines = Object.fromEntries(
            tools.map((tool) => [tool, baseItem.tool_executable_lines[tool] || []]),
          );
          const toolSets = Object.fromEntries(tools.map((tool) => [tool, new Set(toolLines[tool])]));
          const toolExecutableSets = Object.fromEntries(
            tools.map((tool) => [tool, new Set(toolExecutableLines[tool])]),
          );
          const unionSet = new Set();
          const unionExecutableSet = new Set();
          for (const tool of tools) {{
            for (const line of toolLines[tool]) {{
              unionSet.add(line);
            }}
            for (const line of toolExecutableLines[tool]) {{
              unionExecutableSet.add(line);
            }}
          }}
          const unionLines = Array.from(unionSet).sort((left, right) => left - right);
          const unionExecutableLines = Array.from(unionExecutableSet).sort((left, right) => left - right);
          if (!unionExecutableLines.length) {{
            continue;
          }}
          const excludedFromTotals = excludedFolders.has(baseItem.top_level_folder);

          const executableLinesAll = unionExecutableLines.filter((line) =>
            tools.every((tool) => toolExecutableSets[tool].has(line)),
          ).length;
          const coveredLinesAll = unionLines.filter((line) => tools.every((tool) => toolSets[tool].has(line))).length;
          if (!excludedFromTotals) {{
            totalLinesAny += unionLines.length;
            totalLinesAll += coveredLinesAll;
            totalExecutableLinesAny += unionExecutableLines.length;
            totalExecutableLinesAll += executableLinesAll;
          }}

          const signatureCounts = new Map();
          const signatureLines = new Map();
          for (const tool of tools) {{
            if (!excludedFromTotals) {{
              perToolTotalLines[tool] += toolLines[tool].length;
              perToolTotalExecutableLines[tool] += toolExecutableLines[tool].length;
            }}
          }}

          for (const line of unionLines) {{
            const signature = tools.filter((tool) => toolSets[tool].has(line));
            const key = signatureKeyOf(signature);
            signatureCounts.set(key, (signatureCounts.get(key) || 0) + 1);
            if (!signatureLines.has(key)) {{
              signatureLines.set(key, []);
            }}
            signatureLines.get(key).push(line);
            if (!excludedFromTotals) {{
              globalSignatureCounts.set(key, (globalSignatureCounts.get(key) || 0) + 1);
            }}
          }}

          for (const tool of tools) {{
            if (!excludedFromTotals) {{
              perToolUniqueLines[tool] += signatureCounts.get(signatureKeyOf([tool])) || 0;
            }}
          }}

          const signatureEntries = Array.from(signatureCounts.entries()).map(([key, count]) => {{
            const signature = key ? key.split("\\u001f") : [];
            return {{
              signature,
              label: formatSignature(signature, tools),
              count,
              ranges: compressLines(signatureLines.get(key) || []),
            }};
          }}).sort((left, right) => compareSignatureEntries(left, right, tools));

          const hasDifferences = signatureEntries.some((entry) => entry.signature.length !== tools.length);
          const diffLineCount = signatureEntries.reduce(
            (sum, entry) => sum + (entry.signature.length === tools.length ? 0 : entry.count),
            0,
          );
          if (hasDifferences) {{
            if (!excludedFromTotals) {{
              filesWithDifferences += 1;
            }}
          }}

          files.push({{
            path: baseItem.path,
            display_path: baseItem.display_path,
            top_level_folder: baseItem.top_level_folder,
            path_within_folder: baseItem.path_within_folder,
            excluded_from_totals: excludedFromTotals,
            covered_lines_any: unionLines.length,
            covered_lines_all: coveredLinesAll,
            executable_lines_any: unionExecutableLines.length,
            executable_lines_all: executableLinesAll,
            diff_line_count: diffLineCount,
            has_differences: hasDifferences,
            covered_lines_by_tool: Object.fromEntries(tools.map((tool) => [tool, toolLines[tool].length])),
            executable_lines_by_tool: Object.fromEntries(
              tools.map((tool) => [tool, toolExecutableLines[tool].length]),
            ),
            tool_lines: toolLines,
            tool_executable_lines: toolExecutableLines,
            signatures: signatureEntries,
          }});
        }}

        files.sort((left, right) => {{
          if (left.has_differences !== right.has_differences) {{
            return Number(right.has_differences) - Number(left.has_differences);
          }}
          if (right.diff_line_count !== left.diff_line_count) {{
            return right.diff_line_count - left.diff_line_count;
          }}
          if (right.covered_lines_any !== left.covered_lines_any) {{
            return right.covered_lines_any - left.covered_lines_any;
          }}
          return left.display_path.localeCompare(right.display_path);
        }});

        const coverageSignatures = Array.from(globalSignatureCounts.entries()).map(([key, count]) => {{
          const signature = key ? key.split("\\u001f") : [];
          return {{
            signature,
            label: formatSignature(signature, tools),
            count,
          }};
        }}).sort((left, right) => compareSignatureEntries(left, right, tools));

        const foldersByName = new Map();
        for (const item of files) {{
          if (!foldersByName.has(item.top_level_folder)) {{
            foldersByName.set(item.top_level_folder, {{
              folder: item.top_level_folder,
              overview: baseReport.folder_overviews[item.top_level_folder] || [
                "This folder is part of the Circom compiler workspace.",
                "The differential report generator does not have a custom description for it yet.",
              ],
              excluded_from_totals: excludedFolders.has(item.top_level_folder),
              files_seen: 0,
              files_with_differences: 0,
              covered_lines_any: 0,
              covered_lines_all: 0,
              executable_lines_any: 0,
              executable_lines_all: 0,
              diff_line_count: 0,
              covered_lines_by_tool: Object.fromEntries(tools.map((tool) => [tool, 0])),
              executable_lines_by_tool: Object.fromEntries(tools.map((tool) => [tool, 0])),
              covered_lines_unique_to_tool: Object.fromEntries(tools.map((tool) => [tool, 0])),
              files: [],
            }});
          }}
          const folder = foldersByName.get(item.top_level_folder);
          folder.files_seen += 1;
          folder.files_with_differences += Number(item.has_differences);
          folder.covered_lines_any += item.covered_lines_any;
          folder.covered_lines_all += item.covered_lines_all;
          folder.executable_lines_any += item.executable_lines_any;
          folder.executable_lines_all += item.executable_lines_all;
          folder.diff_line_count += item.diff_line_count;
          for (const tool of tools) {{
            folder.covered_lines_by_tool[tool] += item.covered_lines_by_tool[tool];
            folder.executable_lines_by_tool[tool] += item.executable_lines_by_tool[tool];
          }}
          for (const signature of item.signatures) {{
            if (signature.signature.length === 1) {{
              folder.covered_lines_unique_to_tool[signature.signature[0]] += signature.count;
            }}
          }}
          folder.files.push(item);
        }}

        const folders = Array.from(foldersByName.values()).sort((left, right) => {{
          if (left.folder === "." || right.folder === ".") {{
            return Number(left.folder === ".") - Number(right.folder === ".");
          }}
          return left.folder.localeCompare(right.folder);
        }});

        return {{
          tools,
          excluded_folders: Array.from(excludedFolders),
          summary: {{
            folder_count: folders.filter((folder) => !folder.excluded_from_totals).length,
            files_seen: files.filter((item) => !item.excluded_from_totals).length,
            files_with_differences: filesWithDifferences,
            covered_lines_any: totalLinesAny,
            covered_lines_all: totalLinesAll,
            executable_lines_any: totalExecutableLinesAny,
            executable_lines_all: totalExecutableLinesAll,
            covered_lines_unique_to_tool: perToolUniqueLines,
            covered_lines_by_tool: perToolTotalLines,
            executable_lines_by_tool: perToolTotalExecutableLines,
            coverage_signatures: coverageSignatures,
          }},
          folders,
          files,
        }};
      }};

      const render = (report) => {{
        document.getElementById("lede").innerHTML =
          `This report compares covered Circom repository source lines across <code>${{escapeHtml(report.tools.join(", "))}}</code>. It ignores dependency code and generated files under <code>target/</code>. The coverage signature for a line is the exact set of selected tools that covered it.`;
        document.getElementById("selection-note").textContent =
          `Currently showing: ${{report.tools.join(", ")}}`;
        document.getElementById("exclusion-note").textContent =
          report.excluded_folders.length
            ? `Totals exclude: ${{report.excluded_folders.join(", ")}}`
            : "No folders excluded from totals.";
        document.getElementById("metric-folder-count").textContent = report.summary.folder_count;
        document.getElementById("metric-files-seen").textContent = report.summary.files_seen;
        document.getElementById("metric-files-diff").textContent = report.summary.files_with_differences;
        document.getElementById("metric-lines-any").textContent = report.summary.covered_lines_any;
        document.getElementById("metric-lines-all").textContent = report.summary.covered_lines_all;
        document.getElementById("metric-lines-any-detail").textContent =
          `${{formatPercent(report.summary.covered_lines_any, report.summary.executable_lines_any)}} of ${{report.summary.executable_lines_any}} executable lines`;
        document.getElementById("metric-lines-all-detail").textContent =
          `${{formatPercent(report.summary.covered_lines_all, report.summary.executable_lines_all)}} of ${{report.summary.executable_lines_all}} shared executable lines`;

        document.getElementById("tool-rows").innerHTML = report.tools.map((tool) =>
          `<tr><td>${{escapeHtml(tool)}}</td><td>${{escapeHtml(formatCoverageStat(report.summary.covered_lines_by_tool[tool], report.summary.executable_lines_by_tool[tool]))}}</td><td>${{report.summary.covered_lines_unique_to_tool[tool]}}</td></tr>`
        ).join("");

        document.getElementById("signature-rows").innerHTML = report.summary.coverage_signatures.map((entry) =>
          `<tr><td>${{escapeHtml(entry.label)}}</td><td>${{entry.count}}</td></tr>`
        ).join("");

        document.getElementById("folder-table-head").innerHTML =
          `<tr><th>Folder</th><th>Overview</th><th>Files</th><th>Diff files</th><th>Diff lines</th><th>Any coverage</th><th>All-tools coverage</th>${{report.tools.map((tool) => `<th>${{escapeHtml(tool)}}</th>`).join("")}}</tr>`;
        document.getElementById("folder-rows").innerHTML = report.folders
          .slice()
          .sort((left, right) => {{
            if (right.diff_line_count !== left.diff_line_count) {{
              return right.diff_line_count - left.diff_line_count;
            }}
            if (right.covered_lines_any !== left.covered_lines_any) {{
              return right.covered_lines_any - left.covered_lines_any;
            }}
            return left.folder.localeCompare(right.folder);
          }})
          .map((folder) => {{
            const overview = folder.overview.map((paragraph) =>
              `<p class="overview-cell-paragraph">${{escapeHtml(paragraph)}}</p>`
            ).join("");
            const folderBadge = folder.excluded_from_totals
              ? ' <span class="status-badge excluded">excluded</span>'
              : "";
            return `<tr><td><code>${{escapeHtml(folder.folder)}}</code>${{folderBadge}}</td><td>${{overview}}</td><td>${{folder.files_seen}}</td><td>${{folder.files_with_differences}}</td><td>${{folder.diff_line_count}}</td><td>${{escapeHtml(formatCoverageStat(folder.covered_lines_any, folder.executable_lines_any))}}</td><td>${{escapeHtml(formatCoverageStat(folder.covered_lines_all, folder.executable_lines_all))}}</td>${{report.tools.map((tool) => `<td>${{escapeHtml(formatCoverageStat(folder.covered_lines_by_tool[tool], folder.executable_lines_by_tool[tool]))}}</td>`).join("")}}</tr>`;
          }}).join("");

        if (!report.folders.length) {{
          document.getElementById("folder-sections").innerHTML =
            '<p class="empty-state">No covered lines were found for the selected tools.</p>';
          return;
        }}

        document.getElementById("folder-sections").innerHTML = report.folders.map((folder) => {{
          const folderTotals = report.tools.map((tool) =>
            `${{escapeHtml(tool)}}: covered=${{escapeHtml(formatCoverageStat(folder.covered_lines_by_tool[tool], folder.executable_lines_by_tool[tool]))}}, unique=${{folder.covered_lines_unique_to_tool[tool]}}`
          ).join(" | ");
          const folderOverview = folder.overview.map((paragraph) =>
            `<p class="folder-overview">${{escapeHtml(paragraph)}}</p>`
          ).join("");
          const folderBadge = folder.excluded_from_totals
            ? ' <span class="status-badge excluded">excluded from totals</span>'
            : "";
          const fileSections = folder.files.filter((item) => item.covered_lines_any > 0).map((item) => {{
            const totals = report.tools.map((tool) =>
              `${{escapeHtml(tool)}}: ${{escapeHtml(formatCoverageStat(item.covered_lines_by_tool[tool], item.executable_lines_by_tool[tool]))}}`
            ).join(" | ");
            const signatureRows = item.signatures.map((signature) =>
              `<tr><td>${{escapeHtml(signature.label)}}</td><td>${{signature.count}}</td><td><code>${{escapeHtml(signature.ranges)}}</code></td></tr>`
            ).join("");
            return `
        <details class="file-card">
          <summary>
            <span class="file-path">${{escapeHtml(item.path_within_folder)}}</span>
            <span class="file-meta">diff lines: ${{item.diff_line_count}} | covered by any: ${{escapeHtml(formatCoverageStat(item.covered_lines_any, item.executable_lines_any))}} | covered by all: ${{escapeHtml(formatCoverageStat(item.covered_lines_all, item.executable_lines_all))}}</span>
          </summary>
          <p class="tool-breakdown">${{totals}}</p>
          <table>
            <thead>
              <tr><th>Coverage signature</th><th>Lines</th><th>Line numbers</th></tr>
            </thead>
            <tbody>
              ${{signatureRows}}
            </tbody>
          </table>
        </details>`;
          }}).join("");
          return `
        <details class="folder-card">
          <summary>
            <span class="folder-path">${{escapeHtml(folder.folder)}}${{folderBadge}}</span>
            <span class="folder-meta">files: ${{folder.files_seen}} | diff files: ${{folder.files_with_differences}} | diff lines: ${{folder.diff_line_count}} | covered by any: ${{escapeHtml(formatCoverageStat(folder.covered_lines_any, folder.executable_lines_any))}} | covered by all: ${{escapeHtml(formatCoverageStat(folder.covered_lines_all, folder.executable_lines_all))}}</span>
          </summary>
          ${{folderOverview}}
          <p class="tool-breakdown">${{folderTotals}}</p>
          ${{fileSections}}
        </details>`;
        }}).join("");
      }};

      const rerender = () => {{
        render(computeDerived(Array.from(selected), Array.from(excluded)));
      }};

      const bindPicker = () => {{
        document.querySelectorAll("#tool-picker input[data-tool]").forEach((input) => {{
          input.addEventListener("change", () => {{
            if (input.checked) {{
              selected.add(input.dataset.tool);
            }} else if (selected.size > 1) {{
              selected.delete(input.dataset.tool);
            }} else {{
              input.checked = true;
              return;
            }}
            rerender();
          }});
        }});
        document.getElementById("select-all-tools").addEventListener("click", () => {{
          selected.clear();
          for (const tool of baseReport.tools) {{
            selected.add(tool);
          }}
          document.querySelectorAll("#tool-picker input[data-tool]").forEach((input) => {{
            input.checked = true;
          }});
          rerender();
        }});
      }};

      const bindFolderPicker = () => {{
        document.querySelectorAll("#folder-picker input[data-folder]").forEach((input) => {{
          input.addEventListener("change", () => {{
            if (input.checked) {{
              excluded.delete(input.dataset.folder);
            }} else {{
              excluded.add(input.dataset.folder);
            }}
            rerender();
          }});
        }});
        document.getElementById("include-all-folders").addEventListener("click", () => {{
          excluded.clear();
          document.querySelectorAll("#folder-picker input[data-folder]").forEach((input) => {{
            input.checked = true;
          }});
          rerender();
        }});
        document.getElementById("exclude-all-folders").addEventListener("click", () => {{
          document.querySelectorAll("#folder-picker input[data-folder]").forEach((input) => {{
            input.checked = false;
            excluded.add(input.dataset.folder);
          }});
          rerender();
        }});
      }};

      bindPicker();
      bindFolderPicker();
      rerender();
    }})();
  </script>
</body>
</html>
"""


def write_report(output_dir: Path, report: dict[str, object]) -> None:
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output_dir / "summary.txt").write_text(build_summary_text(report), encoding="utf-8")
    (output_dir / "html" / "index.html").write_text(build_html(report), encoding="utf-8")


def main(argv: list[str]) -> int:
    program_name = Path(argv[0]).name
    script_dir = Path(__file__).resolve().parent
    obj_root = script_dir / "obj"
    try:
        tools, excluded_folders = parse_cli_args(argv, obj_root)
    except ValueError as exc:
        if str(exc) == "usage":
            return usage(program_name)
        eprint(str(exc))
        return 1

    diff_root = obj_root / "differential"
    slug = slugify_report(tools, excluded_folders)
    output_dir = diff_root / slug
    report_dir = output_dir / "html"
    lcov_inputs_path = output_dir / "lcov_inputs.txt"

    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        lcov_inputs = find_lcov_inputs(obj_root, tools)
    except (FileNotFoundError, FileExistsError) as exc:
        eprint(str(exc))
        return 1

    write_lcov_inputs(lcov_inputs_path, lcov_inputs, tools, excluded_folders)
    report = build_report(lcov_inputs, tools, excluded_folders)
    write_report(output_dir, report)

    eprint(f"[coverage] Differential report written to {output_dir}")
    eprint(f"[coverage]   HTML:    {report_dir / 'index.html'}")
    eprint(f"[coverage]   JSON:    {output_dir / 'report.json'}")
    eprint(f"[coverage]   Summary: {output_dir / 'summary.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
