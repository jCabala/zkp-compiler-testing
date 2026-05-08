#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import IO, Any


ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT_DIR.parent
RESULTS_DIR = ROOT_DIR / "experiments" / "results"
ARTIFACTS_DIR = ROOT_DIR / "experiments" / "obj"
YINYANG_ROOT = ROOT_DIR / "third_party" / "yinyang"
CONTAINER_REPO_ROOT = Path("/workspace")
CONTAINER_ROOT_DIR = CONTAINER_REPO_ROOT / ROOT_DIR.name
IMAGE_CIRCOM = os.environ.get("IMAGE_CIRCOM", "localhost/smt-exp-circom:latest")
IMAGE_GNARK = os.environ.get("IMAGE_GNARK", "localhost/smt-exp-gnark:latest")
IMAGE_NOIR = os.environ.get("IMAGE_NOIR", "localhost/smt-exp-noir:latest")
IMAGE_ZOKRATES = os.environ.get("IMAGE_ZOKRATES", "localhost/smt-exp-zokrates:latest")
CONTAINER_MEMORY = os.environ.get("CONTAINER_MEMORY", "64g")
CONTAINER_MEMORY_SWAP = os.environ.get("CONTAINER_MEMORY_SWAP", "-1")
YINYANG_OK_NOBUGS = 0
YINYANG_OK_BUGS = 10
YINYANG_OK_CODES = {YINYANG_OK_NOBUGS, YINYANG_OK_BUGS}
DEFAULT_FUSION_CONFIGS = {
	"smt": ROOT_DIR / "experiments" / "legacy" / "sat_fusion" / "sat_fusion_config.txt",
	"picus": ROOT_DIR / "experiments" / "legacy" / "picus_fusion" / "picus_fusion_config.txt",
	"direct": ROOT_DIR / "experiments" / "legacy" / "sat_fusion" / "sat_fusion_config.txt",
}
DEFAULT_YINYANG_SEEDS = {
	"smt": 7586,
	"picus": 5959,
	"direct": 7586,
}
_WARM_SAT = """(set-logic QF_BV)
(declare-fun x () Bool)
(assert x)
(check-sat)
"""
_WARM_UNSAT = """(set-logic QF_BV)
(declare-fun x () Bool)
(assert x)
(assert (not x))
(check-sat)
"""


def _run_capture(
	cmd: list[str],
	*,
	timeout_sec: int | None = None,
	env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		cmd,
		cwd=str(ROOT_DIR),
		capture_output=True,
		text=True,
		timeout=timeout_sec,
		env=env,
	)


def _run_live(
	cmd: list[str],
	*,
	env: dict[str, str] | None = None,
	stdout: Any | None = None,
	stderr: Any | None = None,
) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		cmd,
		cwd=str(ROOT_DIR),
		env=env,
		stdout=stdout,
		stderr=stderr,
		text=True if stdout is None and stderr is None else None,
	)


def _spawn_live(
	cmd: list[str],
	*,
	env: dict[str, str] | None = None,
) -> subprocess.Popen[Any]:
	return subprocess.Popen(
		cmd,
		cwd=str(ROOT_DIR),
		env=env,
	)


def _resolve_path(path: Path) -> Path:
	return path if path.is_absolute() else (Path.cwd() / path).resolve()


def _path_from_root(value: str | Path | None, *, default: Path | None = None) -> Path:
	if value is None:
		if default is None:
			raise ValueError("Missing required path value")
		return default
	path = Path(value)
	return path if path.is_absolute() else (ROOT_DIR / path).resolve()


def _host_to_container_path(path: Path) -> Path:
	resolved = _resolve_path(path)
	try:
		rel = resolved.relative_to(REPO_ROOT)
	except ValueError as exc:
		raise ValueError(f"Podman mode requires paths under {REPO_ROOT}: {resolved}") from exc
	return CONTAINER_REPO_ROOT / rel


def _select_image_for_dsl(dsl: str) -> str:
	if dsl == "circom":
		return IMAGE_CIRCOM
	if dsl == "gnark":
		return IMAGE_GNARK
	if dsl == "noir":
		return IMAGE_NOIR
	if dsl == "zokrates":
		return IMAGE_ZOKRATES
	raise ValueError(f"Unsupported DSL for podman execution: {dsl}")


def _container_name(instance_name: str) -> str:
	safe = re.sub(r"[^a-z0-9-]+", "-", instance_name.lower()).strip("-")
	return f"exp-{safe or 'instance'}-{os.getpid()}"


def _select_benchmarks(bench_dir: Path, max_files: int | None, seed: int) -> list[Path]:
	all_files = sorted(bench_dir.glob("*.smt2"))
	if max_files is None or max_files >= len(all_files):
		return all_files
	rng = random.Random(seed)
	shuffled = all_files[:]
	rng.shuffle(shuffled)
	return sorted(shuffled[:max_files])


def _instance_benchmark_dirs(instance: dict[str, Any]) -> list[Path]:
	if "benchmarks_dirs" in instance:
		values = instance["benchmarks_dirs"]
		if not isinstance(values, list) or not values:
			raise ValueError("benchmarks_dirs must be a non-empty list of paths")
		return [_path_from_root(value) for value in values]
	if "benchmarks_dir" in instance:
		return [_path_from_root(instance["benchmarks_dir"])]
	raise ValueError("Each instance must define benchmarks_dir or benchmarks_dirs")


def _artifacts_root(defaults: dict[str, Any]) -> Path:
	return _path_from_root(defaults.get("artifacts_dir"), default=ARTIFACTS_DIR)


def _instance_tmp_dir(instance: dict[str, Any], defaults: dict[str, Any]) -> Path:
	base_tmp_dir = _path_from_root(
		instance.get("tmp_dir", defaults.get("tmp_dir")),
		default=ROOT_DIR / "experiments" / "tmp_fusion",
	)
	if instance.get("tmp_dir_exact", defaults.get("tmp_dir_exact", False)):
		return base_tmp_dir
	return base_tmp_dir / instance["name"] / "tmp"


def _instance_seed_targets(instance: dict[str, Any], defaults: dict[str, Any]) -> list[Path]:
	bench_dirs = _instance_benchmark_dirs(instance)
	max_files = instance.get("max_files", defaults.get("max_files"))
	seed = instance.get("seed", defaults.get("seed", 0))
	if max_files is None:
		return bench_dirs
	all_files: list[Path] = []
	for bench_dir in bench_dirs:
		all_files.extend(sorted(bench_dir.glob("*.smt2")))
	if max_files >= len(all_files):
		return sorted(all_files)
	rng = random.Random(seed)
	shuffled = all_files[:]
	rng.shuffle(shuffled)
	return sorted(shuffled[:max_files])


def _solver_backend(instance: dict[str, Any]) -> str:
	oracle = instance["oracle"]
	if oracle == "smt":
		return str(instance.get("solver", "z3"))
	if oracle == "picus":
		return "picus"
	if oracle == "direct":
		return str(instance.get("solver", "cvc5"))
	raise ValueError(f"Unknown oracle backend: {oracle}")


def _build_direct_solver_command(instance: dict[str, Any]) -> str:
	cmd = [str(instance.get("solver", "cvc5"))] + list(instance.get("solver_args", []))
	return shlex.join(cmd)


def _fusion_config_path(instance: dict[str, Any], defaults: dict[str, Any]) -> Path:
	value = instance.get("yinyang_config", defaults.get("yinyang_config"))
	if value is not None:
		return _path_from_root(value)
	return DEFAULT_FUSION_CONFIGS[instance["oracle"]]


def _yinyang_oracle(instance: dict[str, Any], defaults: dict[str, Any]) -> str:
	return str(instance.get("yinyang_oracle", defaults.get("yinyang_oracle", "sat")))


def _yinyang_seed(instance: dict[str, Any], defaults: dict[str, Any]) -> int:
	default = defaults.get("yinyang_seed")
	if default is None:
		default = DEFAULT_YINYANG_SEEDS[instance["oracle"]]
	return int(instance.get("yinyang_seed", default))


def _yinyang_env(instance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, str]:
	env = os.environ.copy()
	existing = env.get("PYTHONPATH")
	env["PYTHONPATH"] = str(YINYANG_ROOT) if not existing else f"{YINYANG_ROOT}:{existing}"

	rewrite_policy = instance.get("fusion_rewrite_policy", defaults.get("fusion_rewrite_policy"))
	side_policy = instance.get("fusion_side_policy", defaults.get("fusion_side_policy"))
	if instance["oracle"] == "picus":
		rewrite_policy = rewrite_policy or "all"
		side_policy = side_policy or "one"
	if rewrite_policy:
		env["YY_FUSION_REWRITE_POLICY"] = str(rewrite_policy)
	if side_policy:
		env["YY_FUSION_SIDE_POLICY"] = str(side_policy)
	return env


def _instance_layout(instance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Path]:
	obj_root = _artifacts_root(defaults)
	instance_root = obj_root / instance["name"]
	return {
		"obj_root": obj_root,
		"instance_root": instance_root,
		"out_file": obj_root / f"{instance['name']}.out",
		"warmup_log": instance_root / "warmup.log",
		"log_dir": instance_root / "logs",
		"scratch_dir": instance_root / "scratch",
		"bug_dir": instance_root / "bugs",
		"solve_config": instance_root / "solve_config.json",
	}


def _solve_config_data(instance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
	hints_enabled = instance.get("hints", defaults.get("hints", False))
	data: dict[str, Any] = {
		"zk_dsl": instance["dsl"],
		"solver": _solver_backend(instance),
		"tmp_dir": str(_instance_tmp_dir(instance, defaults)),
		"with_logs": bool(instance.get("with_logs", defaults.get("with_logs", False))),
		"without_hints": not bool(hints_enabled),
		"no_simplify": bool(instance.get("no_simplify", defaults.get("no_simplify", False))),
		"with_circ": bool(instance.get("with_circ", defaults.get("with_circ", False))),
	}

	solving_timeout = instance.get("solving_timeout_sec", defaults.get("solver_timeout_sec"))
	if solving_timeout is not None:
		data["solving_timeout"] = solving_timeout

	not_chain_length = instance.get("not_chain_length", defaults.get("not_chain_length"))
	if not_chain_length is not None:
		data["not_chain_length"] = not_chain_length

	max_not_chain_count = instance.get("max_not_chain_count", defaults.get("max_not_chain_count"))
	if max_not_chain_count is not None:
		data["max_not_chain_count"] = max_not_chain_count

	if instance.get("compiler"):
		data["compiler"] = instance["compiler"]

	if instance.get("opt_level") and instance["dsl"] == "circom" and instance["opt_level"] == "O0":
		data["no_simplify"] = True

	return data


def _write_solve_config(instance: dict[str, Any], defaults: dict[str, Any], path: Path) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(_solve_config_data(instance, defaults), indent=2))


def _build_solver_command(solve_config_path: Path) -> str:
	return shlex.join([
		sys.executable,
		str(ROOT_DIR / "cli.py"),
		"solve",
		"--config",
		str(solve_config_path),
	])


def _write_run_snapshot(
	instance: dict[str, Any],
	defaults: dict[str, Any],
	layout: dict[str, Path],
	seed_targets: list[Path],
	yinyang_cmd: list[str],
) -> Path:
	ts = time.strftime("%Y%m%d-%H%M%S")
	snapshot = layout["obj_root"] / f"run_config_{ts}_{instance['name']}.env"
	lines = [
		"# Auto-generated experiment config snapshot",
		f"timestamp={ts}",
		f"name={instance['name']}",
		f"dsl={instance['dsl']}",
		f"oracle_backend={instance['oracle']}",
		f"solver_backend={_solver_backend(instance)}",
		f"yinyang_oracle={_yinyang_oracle(instance, defaults)}",
		f"yinyang_seed={_yinyang_seed(instance, defaults)}",
		f"yinyang_config={_fusion_config_path(instance, defaults)}",
		f"tmp_dir={_instance_tmp_dir(instance, defaults)}",
		f"out_file={layout['out_file']}",
		f"warmup_log={layout['warmup_log']}",
		f"log_dir={layout['log_dir']}",
		f"scratch_dir={layout['scratch_dir']}",
		f"bug_dir={layout['bug_dir']}",
		f"solve_config={layout['solve_config']}",
		f"seed_targets={' '.join(str(path) for path in seed_targets)}",
		f"YINYANG_CMD={shlex.join(yinyang_cmd)}",
	]
	snapshot.write_text("\n".join(lines) + "\n")
	return snapshot


def _warmup_instance(instance: dict[str, Any], defaults: dict[str, Any], warmup_log: Path) -> None:
	if instance.get("warmup_cli", defaults.get("warmup_cli", True)) is False:
		return

	tmp_dir = _instance_tmp_dir(instance, defaults)
	warm_dir = tmp_dir / "warmup"
	warm_dir.mkdir(parents=True, exist_ok=True)
	warmup_log.parent.mkdir(parents=True, exist_ok=True)

	warm_sat = warm_dir / "warm_sat.smt2"
	warm_unsat = warm_dir / "warm_unsat.smt2"
	warm_sat.write_text(_WARM_SAT)
	warm_unsat.write_text(_WARM_UNSAT)

	warm_solver = str(instance.get("warmup_solver", defaults.get("warmup_solver", "z3")))
	with warmup_log.open("w") as log_f:
		log_f.write(f"warmup_tmp_dir={tmp_dir}\n")
		log_f.write(f"warmup_solver={warm_solver}\n")
		for warm_path in (warm_sat, warm_unsat):
			args = [
				sys.executable,
				"cli.py",
				"solve",
				str(warm_path),
				"--zk-dsl",
				instance["dsl"],
				"--solver",
				warm_solver,
				"--tmp-dir",
				str(tmp_dir),
			]
			if instance.get("compiler"):
				args += ["--compiler", instance["compiler"]]
			proc = _run_capture(args)
			log_f.write(f"\n== Warmup: {warm_path.name} ==\n")
			log_f.write(f"command={shlex.join(args)}\n")
			log_f.write(f"returncode={proc.returncode}\n")
			if proc.stdout:
				log_f.write("[stdout]\n")
				log_f.write(proc.stdout)
				if not proc.stdout.endswith("\n"):
					log_f.write("\n")
			if proc.stderr:
				log_f.write("[stderr]\n")
				log_f.write(proc.stderr)
				if not proc.stderr.endswith("\n"):
					log_f.write("\n")


def _prepare_yinyang_instance(
	instance: dict[str, Any], defaults: dict[str, Any]
) -> tuple[dict[str, Any], list[str], dict[str, str] | None, Any, list[Any]]:
	"""Set up dirs/config/warmup and return (layout, cmd, env, snapshot, seed_targets)."""
	layout = _instance_layout(instance, defaults)
	layout["obj_root"].mkdir(parents=True, exist_ok=True)
	layout["instance_root"].mkdir(parents=True, exist_ok=True)
	layout["log_dir"].mkdir(parents=True, exist_ok=True)
	layout["scratch_dir"].mkdir(parents=True, exist_ok=True)
	layout["bug_dir"].mkdir(parents=True, exist_ok=True)

	seed_targets = _instance_seed_targets(instance, defaults)
	if instance["oracle"] == "direct":
		solver_cmd_str = _build_direct_solver_command(instance)
	else:
		_write_solve_config(instance, defaults, layout["solve_config"])
		_warmup_instance(instance, defaults, layout["warmup_log"])
		solver_cmd_str = _build_solver_command(layout["solve_config"])

	yinyang_cmd = [
		sys.executable,
		str(YINYANG_ROOT / "yinyang_cli.py"),
		solver_cmd_str,
		"--oracle",
		_yinyang_oracle(instance, defaults),
		"--timeout",
		str(instance.get("timeout_sec", defaults.get("timeout_sec", 60))),
		"--config",
		str(_fusion_config_path(instance, defaults)),
		"--logfolder",
		str(layout["log_dir"]),
		"--scratchfolder",
		str(layout["scratch_dir"]),
		"--bugsfolder",
		str(layout["bug_dir"]),
		"--seed",
		str(_yinyang_seed(instance, defaults)),
	]
	iterations = instance.get("yinyang_iterations", defaults.get("yinyang_iterations"))
	if iterations is not None:
		yinyang_cmd += ["--iterations", str(iterations)]
	file_size_limit = instance.get("file_size_limit", defaults.get("file_size_limit"))
	if file_size_limit is not None:
		yinyang_cmd += ["--file-size-limit", str(file_size_limit)]
	yinyang_cmd += [str(path) for path in seed_targets]

	snapshot = _write_run_snapshot(instance, defaults, layout, seed_targets, yinyang_cmd)
	env = _yinyang_env(instance, defaults)
	return layout, yinyang_cmd, env, snapshot, seed_targets


def _collect_yinyang_result(
	instance: dict[str, Any],
	layout: dict[str, Any],
	snapshot: Any,
	seed_targets: list[Any],
	returncode: int,
	elapsed: float,
) -> dict[str, Any]:
	status = "ok"
	if returncode == YINYANG_OK_BUGS:
		status = "bugs_found"
	elif returncode not in YINYANG_OK_CODES:
		status = f"error ({returncode})"

	return {
		"name": instance["name"],
		"dsl": instance["dsl"],
		"oracle": instance["oracle"],
		"benchmarks_dir": instance.get("benchmarks_dir"),
		"benchmarks_dirs": instance.get("benchmarks_dirs"),
		"status": status,
		"returncode": returncode,
		"elapsed_sec": round(elapsed, 3),
		"out_file": str(layout["out_file"]),
		"warmup_log": str(layout["warmup_log"]),
		"log_dir": str(layout["log_dir"]),
		"scratch_dir": str(layout["scratch_dir"]),
		"bug_dir": str(layout["bug_dir"]),
		"solve_config": str(layout["solve_config"]),
		"run_snapshot": str(snapshot),
		"seed_targets": [str(path) for path in seed_targets],
	}


def _run_yinyang_instance(instance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
	layout, yinyang_cmd, env, snapshot, seed_targets = _prepare_yinyang_instance(instance, defaults)
	start = time.time()
	with layout["out_file"].open("w") as out_f:
		proc = _run_live(yinyang_cmd, env=env, stdout=out_f, stderr=subprocess.STDOUT)
	elapsed = time.time() - start
	return _collect_yinyang_result(instance, layout, snapshot, seed_targets, proc.returncode, elapsed)


def _summarize(instance_result: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": instance_result["name"],
		"status": instance_result["status"],
		"returncode": instance_result["returncode"],
		"elapsed_sec": instance_result["elapsed_sec"],
		"out_file": instance_result["out_file"],
		"warmup_log": instance_result["warmup_log"],
		"log_dir": instance_result["log_dir"],
		"scratch_dir": instance_result["scratch_dir"],
		"bug_dir": instance_result["bug_dir"],
	}


def _merge_exit_status(current: int, new_code: int) -> int:
	if new_code not in YINYANG_OK_CODES:
		return 1
	if new_code == YINYANG_OK_BUGS and current == 0:
		return YINYANG_OK_BUGS
	return current


def _podman_instance_cmd(instance: dict[str, Any], config_path: Path, output_dir: Path) -> list[str]:
	container_config = _host_to_container_path(config_path)
	container_output = _host_to_container_path(output_dir)
	return [
		"podman",
		"run",
		"--rm",
		"--name",
		_container_name(instance["name"]),
		"-v",
		f"{REPO_ROOT}:/workspace",
		"--workdir",
		str(CONTAINER_ROOT_DIR),
		"--memory",
		CONTAINER_MEMORY,
		"--memory-swap",
		CONTAINER_MEMORY_SWAP,
		"-e",
		"IN_PODMAN=1",
		"-e",
		f"GOCACHE={CONTAINER_ROOT_DIR / 'experiments' / 'obj' / 'go-cache'}",
		"-e",
		"IMAGE_CIRCOM",
		"-e",
		"IMAGE_GNARK",
		"-e",
		"IMAGE_NOIR",
		"-e",
		"IMAGE_ZOKRATES",
		_select_image_for_dsl(instance["dsl"]),
		"python3",
		"experiments/run_experiments.py",
		"--config",
		str(container_config),
		"--output-dir",
		str(container_output),
		"--instance-name",
		instance["name"],
		"--local",
	]


def main() -> int:
	parser = argparse.ArgumentParser(description="Run experiments from a single config file.")
	parser.add_argument(
		"--config",
		type=Path,
		default=ROOT_DIR / "experiments" / "configs" / "bool_exp_config.json",
	)
	parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
	parser.add_argument("--instance-name", type=str, default=None, help="Run only the named instance from the config.")
	parser.add_argument("--local", action="store_true", help="Run directly in the current environment instead of launching podman containers.")
	args = parser.parse_args()

	config_path = _resolve_path(args.config)
	output_dir = _resolve_path(args.output_dir)
	cfg = json.loads(config_path.read_text())
	defaults = cfg.get("defaults", {})
	instances = cfg.get("instances", [])
	if args.instance_name is not None:
		instances = [inst for inst in instances if inst["name"] == args.instance_name]
	if not instances:
		print("No instances configured.")
		return 1

	output_dir.mkdir(parents=True, exist_ok=True)
	summaries = []

	if not args.local and os.environ.get("IN_PODMAN") != "1":
		overall_status = 0
		running: list[tuple[dict[str, Any], subprocess.Popen[Any]]] = []
		for inst in instances:
			print(f"== Running in podman: {inst['name']} ==")
			running.append((inst, _spawn_live(_podman_instance_cmd(inst, config_path, output_dir))))
		for inst, proc in running:
			returncode = proc.wait()
			overall_status = _merge_exit_status(overall_status, returncode)
			out_file = output_dir / f"{inst['name']}.json"
			if returncode in YINYANG_OK_CODES and out_file.exists():
				res = json.loads(out_file.read_text())
				summaries.append(_summarize(res))
				print(f"  -> {out_file}")
		summary_file = output_dir / "summary.json"
		summary_file.write_text(json.dumps(summaries, indent=2))
		print(f"\nSummary written to {summary_file}")
		return overall_status

	overall_status = 0
	# Prepare all instances (dirs, config, warmup) before spawning
	prepared = []
	for inst in instances:
		print(f"== Preparing: {inst['name']} ==")
		prepared.append((inst, *_prepare_yinyang_instance(inst, defaults)))

	# Spawn all concurrently
	running: list[tuple[dict[str, Any], dict[str, Any], Any, list[Any], subprocess.Popen[Any], IO[Any], float]] = []
	for inst, layout, cmd, env, snapshot, seed_targets in prepared:
		print(f"== Spawning: {inst['name']} ==")
		out_f = layout["out_file"].open("w")
		proc = subprocess.Popen(cmd, cwd=str(ROOT_DIR), env=env, stdout=out_f, stderr=subprocess.STDOUT)
		running.append((inst, layout, snapshot, seed_targets, proc, out_f, time.time()))

	# Wait for all, killing on interrupt
	try:
		for inst, layout, snapshot, seed_targets, proc, out_f, start in running:
			proc.wait()
			out_f.close()
			elapsed = time.time() - start
			res = _collect_yinyang_result(inst, layout, snapshot, seed_targets, proc.returncode, elapsed)
			overall_status = _merge_exit_status(overall_status, res["returncode"])
			out_file = output_dir / f"{inst['name']}.json"
			out_file.write_text(json.dumps(res, indent=2))
			summaries.append(_summarize(res))
			print(f"  -> {out_file}")
	except KeyboardInterrupt:
		print("\nInterrupted — killing all running instances...")
		for _, _, _, _, proc, out_f, _ in running:
			proc.kill()
			out_f.close()
		raise

	summary_file = output_dir / "summary.json"
	summary_file.write_text(json.dumps(summaries, indent=2))
	print(f"\nSummary written to {summary_file}")
	return overall_status


if __name__ == "__main__":
	raise SystemExit(main())
