# ==============================
# backends/zokrates/command.py
# ==============================
from __future__ import annotations

import time
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .utils import ZokratesCurve


@dataclass
class CmdResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    delta_time: float
    outputs: list[int] | None = None


def _write_log(log_path: Path, cmd: list[str], stdout: str, stderr: str, returncode: int, dt: float) -> None:
    """
    Persist stdout/stderr next to other artifacts.
    """
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8", errors="replace") as f:
            f.write("CMD:\n")
            f.write(" ".join(cmd) + "\n\n")
            f.write(f"RETURNCODE: {returncode}\n")
            f.write(f"TIME_SEC: {dt}\n\n")
            if stdout:
                f.write("STDOUT:\n")
                f.write(stdout)
                if not stdout.endswith("\n"):
                    f.write("\n")
                f.write("\n")
            if stderr:
                f.write("STDERR:\n")
                f.write(stderr)
                if not stderr.endswith("\n"):
                    f.write("\n")
    except Exception:
        # Never let logging break the harness
        pass


def _run(cmd: list[str], cwd: Path, *, log_path: Optional[Path] = None) -> CmdResult:
    t0 = time.time()
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    dt = time.time() - t0
    res = CmdResult(
        ok=(p.returncode == 0),
        stdout=p.stdout,
        stderr=p.stderr,
        returncode=p.returncode,
        delta_time=dt,
    )
    if log_path is not None:
        _write_log(log_path, cmd, p.stdout, p.stderr, p.returncode, dt)
    return res


def _curve_args(curve: ZokratesCurve) -> list[str]:
    match curve:
        case ZokratesCurve.BN254:
            # ZoKrates uses "bn128" naming for BN254
            return ["--curve", "bn128"]
        case ZokratesCurve.BLS12_381:
            return ["--curve", "bls12_381"]
        case _:
            return []


def zokrates_compile(
    *,
    workdir: Path,
    source: Path,
    curve: ZokratesCurve,
    out_name: str,
) -> CmdResult:
    """
    Creates workdir/out/<out_name> (ZoKrates binary program).
    Logs saved to workdir/out/compile.log
    """
    out_dir = workdir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name

    cmd = [
        "zokrates",
        "compile",
        "-i",
        str(source),
        "-o",
        str(out_path),
    ] + _curve_args(curve)

    return _run(cmd, workdir, log_path=out_dir / "compile.log")


def zokrates_compute_witness(
    *,
    workdir: Path,
    out_name: str,
    args: list[str],
) -> CmdResult:
    """
    Uses workdir/out/<out_name> and writes witness to workdir/out/witness.
    Logs saved to workdir/out/witness.log
    """
    out_dir = workdir / "out"
    out_path = out_dir / out_name
    witness_path = out_dir / "witness"

    cmd = [
        "zokrates",
        "compute-witness",
        "-i",
        str(out_path),
        "-o",
        str(witness_path),
        "-a",
    ] + [str(a) for a in args]

    res = _run(cmd, workdir, log_path=out_dir / "witness.log")
    res.outputs = _parse_outputs_from_stdout(res.stdout)
    return res


def zokrates_setup(
    *,
    workdir: Path,
    out_name: str,
    curve: ZokratesCurve,
) -> CmdResult:
    """
    Writes proving/verification keys into workdir/out by running from that cwd.
    Logs saved to workdir/out/setup.log
    """
    out_dir = workdir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name

    cmd = [
        "zokrates",
        "setup",
        "-i",
        str(out_path),
    ] + _curve_args(curve)

    # Run setup with cwd=out_dir so verification.key, proving.key land in out/
    return _run(cmd, out_dir, log_path=out_dir / "setup.log")


def zokrates_generate_proof(
    *,
    workdir: Path,
    out_name: str,
    curve: ZokratesCurve,
) -> CmdResult:
    """
    Uses workdir/out/<out_name> + workdir/out/witness, emits proof.json into workdir/out.
    Logs saved to workdir/out/prove.log
    """
    out_dir = workdir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name
    witness_path = out_dir / "witness"

    cmd = [
        "zokrates",
        "prove",
        "-i",
        str(out_path),
        "-w",
        str(witness_path),
    ] + _curve_args(curve)

    # Run prove with cwd=out_dir so proof.json lands in out/
    return _run(cmd, out_dir, log_path=out_dir / "prove.log")


def zokrates_verify(
    *,
    workdir: Path,
    curve: ZokratesCurve,
) -> CmdResult:
    """
    Verifies workdir/out/proof.json against workdir/out/verification.key
    Logs saved to workdir/out/verify.log
    """
    out_dir = workdir / "out"
    proof_path = out_dir / "proof.json"
    vk_path = out_dir / "verification.key"

    cmd = [
        "zokrates",
        "verify",
        "-j",
        str(proof_path),
        "-v",
        str(vk_path),
    ] + _curve_args(curve)

    return _run(cmd, out_dir, log_path=out_dir / "verify.log")


def _parse_outputs_from_stdout(stdout: str) -> list[int]:
    import re

    # ZoKrates prints something like: Outputs: [1, 2, 3]
    m = re.search(r"Outputs:\s*\[([^\]]*)\]", stdout)
    if not m:
        return []
    outs: list[int] = []
    for p in m.group(1).split(","):
        p = p.strip()
        if not p:
            continue
        try:
            outs.append(int(p))
        except Exception:
            pass
    return outs
