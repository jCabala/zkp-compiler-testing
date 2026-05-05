from pathlib import Path
import sys

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from cli import cli


def test_prod_to_noir_acir_command(monkeypatch, tmp_path: Path):
	in_folder = tmp_path / "prod"
	(in_folder / "sat").mkdir(parents=True)
	(in_folder / "unsat").mkdir(parents=True)
	(in_folder / "sat" / "b.smt2").write_text("(set-logic QF_BV)\n(assert true)\n(check-sat)\n")
	(in_folder / "unsat" / "a.smt2").write_text("(set-logic QF_BV)\n(assert false)\n(check-sat)\n")

	from src.cli.helper_tools_cli import noir_acir

	monkeypatch.setattr(noir_acir.shutil, "which", lambda name: f"/fake/{name}")

	compiled_projects: list[Path] = []
	built_decoder = tmp_path / "decoder" / "acir-decoder"

	def fake_run(cmd, cwd=None, env=None, check=None, capture_output=None, text=None):
		project_dir = Path(cwd) if cwd is not None else tmp_path
		if cmd == ["/fake/nargo", "compile"]:
			assert env["HOME"] == str(tmp_path / "nargo-home")
			compiled_projects.append(project_dir)
			target_dir = project_dir / "target"
			target_dir.mkdir(parents=True, exist_ok=True)
			package_name = project_dir.name
			(target_dir / f"{package_name}.json").write_text('{"bytecode":"stub"}')
		elif cmd[:3] == ["/fake/cargo", "build", "--manifest-path"]:
			built_decoder.parent.mkdir(parents=True, exist_ok=True)
			built_decoder.write_text("")
		elif cmd[0] == str(built_decoder):
			output_idx = cmd.index("--output") + 1
			Path(cmd[output_idx]).write_text('{"summary":{"function_count":1}}')
			class Result:
				returncode = 0
				stdout = ""
				stderr = ""
			return Result()
		else:
			raise AssertionError(cmd)
		class Result:
			returncode = 0
			stdout = ""
			stderr = ""
		return Result()

	monkeypatch.setattr(noir_acir.subprocess, "run", fake_run)
	monkeypatch.setattr(noir_acir, "_acir_decoder_paths", lambda: (tmp_path / "decoder" / "Cargo.toml", built_decoder))
	def fake_emit_sr1cs(decoded_path, log=print):
		sr1cs_path = decoded_path.with_name(decoded_path.name.replace(".json.decoded.json", ".sr1cs"))
		sr1cs_path.write_text("(prime-number 47)\n")
		return sr1cs_path
	monkeypatch.setattr(noir_acir, "emit_sr1cs_from_decoded_noir_artifact", fake_emit_sr1cs)

	out_folder = tmp_path / "out"
	result = CliRunner().invoke(
		cli,
		[
			"prod-to-noir-acir",
			str(in_folder),
			str(out_folder),
			"--count",
			"2",
			"--cache-home",
			str(tmp_path / "nargo-home"),
		],
	)

	assert result.exit_code == 0, result.output
	assert compiled_projects == [
		out_folder / "sat" / "b",
		out_folder / "unsat" / "a",
	]
	assert (out_folder / "sat" / "b" / "src" / "main.nr").exists()
	assert (out_folder / "sat" / "b" / "target" / "b.json").exists()
	assert (out_folder / "sat" / "b" / "target" / "b.json.decoded.json").exists()
	assert (out_folder / "sat" / "b" / "target" / "b.sr1cs").exists()
	assert (out_folder / "unsat" / "a" / "target" / "a.json").exists()
	assert (out_folder / "acir_manifest.json").exists()
