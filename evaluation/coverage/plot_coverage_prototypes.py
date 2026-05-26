#!/usr/bin/env python3
"""Generate the module-delta coverage figure.

The module-level numbers are taken from evaluation/coverage/main_report.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch


OUT_DIR = Path(__file__).resolve().parent / "figures"

CORE = "#2F7D62"
SUPPORT = "#8B949E"
WITNESS = "#C75622"
GRID = "#D6D8DC"
TEXT = "#20242A"


@dataclass(frozen=True)
class ModuleCoverage:
    module: str
    circuzz: int
    picus: int
    category: str

    @property
    def delta(self) -> int:
        return self.circuzz - self.picus


MODULES = [
    ModuleCoverage("constraint_generation", 2636, 2236, "R1CS core"),
    ModuleCoverage("constraint_list", 819, 670, "R1CS core"),
    ModuleCoverage("circom_algebra", 1183, 791, "R1CS core"),
    ModuleCoverage("dag", 555, 402, "R1CS core"),
    ModuleCoverage("constant_tracking", 21, 18, "R1CS core"),
    ModuleCoverage("constraint_writers", 294, 251, "support"),
    ModuleCoverage("parser", 546, 529, "support"),
    ModuleCoverage("type_analysis", 1750, 1623, "support"),
    ModuleCoverage("program_structure", 1565, 1428, "support"),
    ModuleCoverage("circom frontend", 661, 533, "support"),
    ModuleCoverage("compiler", 4058, 711, "witness branch"),
    ModuleCoverage("code_producers", 2355, 0, "witness branch"),
]


def category_color(category: str) -> str:
    return {
        "R1CS core": CORE,
        "support": SUPPORT,
        "witness branch": WITNESS,
    }[category]


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 220,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 10,
            "axes.edgecolor": "#AEB4BC",
            "axes.labelcolor": TEXT,
            "xtick.color": TEXT,
            "ytick.color": TEXT,
            "text.color": TEXT,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{name}.png", bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_module_delta() -> None:
    data = sorted(MODULES, key=lambda item: item.delta)
    labels = [item.module for item in data]
    values = [item.delta for item in data]
    colors = [category_color(item.category) for item in data]

    fig, ax = plt.subplots(figsize=(9, 6.2))
    bars = ax.barh(labels, values, color=colors, edgecolor="none")
    ax.set_title("Where circuzz covers more code")
    ax.set_xlabel("Extra covered lines in circuzz")
    ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, max(values) * 1.18)

    for bar, value in zip(bars, values):
        ax.text(
            value + max(values) * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"+{value:,}",
            va="center",
            ha="left",
            fontsize=9,
        )

    ax.legend(
        handles=[
            Patch(facecolor=CORE, label="R1CS core"),
            Patch(facecolor=SUPPORT, label="support/frontend"),
            Patch(facecolor=WITNESS, label="witness/codegen branch"),
        ],
        frameon=False,
        loc="lower right",
    )
    save(fig, "01_module_delta_bar")


def main() -> None:
    setup_style()
    plot_module_delta()


if __name__ == "__main__":
    main()
