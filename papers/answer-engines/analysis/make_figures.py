"""Generate the paper's figures from the raw run data.

Reads data/runs/exp1_main and data/runs/exp2_main and writes PDF (for LaTeX)
plus PNG previews to paper/figures/. Design follows the repo's dataviz rules:
one hue where identity is on the axis, a single-hue sequential ramp for
magnitude, thin marks, hairline solid grid, selective direct labels.

Usage:
    uv run python analysis/make_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "paper" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

# Palette (validated against white surface; see dataviz notes)
BLUE = "#2a78d6"       # series slot 1: the single data hue
INK = "#0b0b0b"
SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
# Sequential blue ramp, light -> dark (steps 100..700)
RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "axes.edgecolor": BASELINE,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": SECONDARY,
    "ytick.color": SECONDARY,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "grid.linestyle": "-",
    "figure.dpi": 150,
    "savefig.bbox": "tight",
})


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIGDIR / f"{name}.pdf")
    fig.savefig(FIGDIR / f"{name}.png", dpi=200)
    plt.close(fig)
    print(f"wrote paper/figures/{name}.pdf (+png)")


def bootstrap_ci(values: np.ndarray, n: int = 5000, alpha: float = 0.05) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(0)
    means = values[rng.integers(0, len(values), size=(n, len(values)))].mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


# ---------------------------------------------------------------- Experiment 1

exp1 = pd.read_csv(ROOT / "data" / "runs" / "exp1_main" / "trials.csv")
exp1 = exp1[exp1["rep"] == 0]

CELLS = [  # (tier, condition, treatment, display label)
    ("high", "no_search", "baseline", "HIGH · no search (prior)"),
    ("high", "search", "consistent", "HIGH · consistent"),
    ("high", "search", "contradicting", "HIGH · contradicting"),
    ("high", "search", "novel", "HIGH · novel"),
    ("tail", "no_search", "baseline", "TAIL · no search (prior)"),
    ("tail", "search", "novel", "TAIL · novel"),
    ("zero", "no_search", "baseline", "ZERO · no search (prior)"),
    ("zero", "search", "novel", "ZERO · novel"),
]


def fig_adoption() -> None:
    """Forest-style dot plot: adoption of planted facts by tier x treatment."""
    fig, ax = plt.subplots(figsize=(6.0, 3.1))
    ys = np.arange(len(CELLS))[::-1]
    rng = np.random.default_rng(1)
    for y, (tier, cond, treat, label) in zip(ys, CELLS):
        g = exp1[(exp1.tier == tier) & (exp1.condition == cond) & (exp1.treatment == treat)]
        vals = g["adopt_rate"].dropna().values
        if len(vals) == 0:
            continue
        jitter = rng.uniform(-0.16, 0.16, len(vals))
        ax.scatter(vals, y + jitter, s=14, color=MUTED, alpha=0.55, zorder=2,
                   edgecolors="none")
        lo, hi = bootstrap_ci(vals)
        m = vals.mean()
        ax.plot([lo, hi], [y, y], color=BLUE, lw=1.8, zorder=3, solid_capstyle="round")
        ax.scatter([m], [y], s=46, color=BLUE, zorder=4, edgecolors="white", linewidths=1.2)
        ax.annotate(f"{m:.2f}", (m, y), xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=8, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels([c[3] for c in CELLS])
    ax.set_xlim(-0.04, 1.09)
    ax.set_xlabel("Adoption rate of planted facts (mean, 95% bootstrap CI over entities)")
    ax.grid(axis="x", zorder=0)
    ax.set_axisbelow(True)
    save(fig, "fig_adoption")


def fig_search() -> None:
    """Strip plot: tool queries per trial by tier x treatment (search condition)."""
    cells = [
        ("high", "novel", "HIGH · novel"),
        ("high", "consistent", "HIGH · consistent"),
        ("high", "contradicting", "HIGH · contradicting"),
        ("tail", "novel", "TAIL · novel"),
        ("zero", "novel", "ZERO · novel"),
    ]
    srch = exp1[exp1.condition == "search"]
    fig, ax = plt.subplots(figsize=(6.0, 2.7))
    ys = np.arange(len(cells))[::-1]
    rng = np.random.default_rng(2)
    for y, (tier, treat, label) in zip(ys, cells):
        vals = srch[(srch.tier == tier) & (srch.treatment == treat)]["n_tool_queries"].values
        jitter = rng.uniform(-0.18, 0.18, len(vals))
        ax.scatter(vals, y + jitter, s=16, color=BLUE, alpha=0.65, zorder=3,
                   edgecolors="none")
        m = vals.mean()
        ax.plot([m, m], [y - 0.28, y + 0.28], color=INK, lw=1.6, zorder=4)
        ax.annotate(f"mean {m:.1f}", (m, y + 0.34), ha="center", fontsize=7.5,
                    color=SECONDARY)
    ax.set_yticks(ys)
    ax.set_yticklabels([c[2] for c in cells])
    ax.set_xlabel("web_search queries issued per trial")
    ax.set_xlim(0, srch["n_tool_queries"].max() + 1.5)
    ax.grid(axis="x", zorder=0)
    ax.set_axisbelow(True)
    save(fig, "fig_search")


# ---------------------------------------------------------------- Experiment 2

exp2 = pd.read_csv(ROOT / "data" / "runs" / "exp2_main" / "trials.csv")


def fig_rank_heatmap() -> None:
    """Heatmap: target rank by feature treatment x presented position (temp 0)."""
    prim = exp2[exp2.rep == 0]
    order = (prim.groupby("treatment")["target_rank"].mean().sort_values().index.tolist())
    pivot = prim.pivot_table(index="treatment", columns="target_pos",
                             values="target_rank").reindex(order)
    # darker = better rank (rank 1). Map rank 1..5 onto reversed light->dark ramp.
    cmap = LinearSegmentedColormap.from_list("blues", RAMP)
    fig, ax = plt.subplots(figsize=(5.4, 2.6))
    data = 6 - pivot.values  # rank 1 -> 5 (dark), rank 5 -> 1 (light)
    ax.imshow(data, cmap=cmap, vmin=0.5, vmax=5.5, aspect="auto")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            rank = int(pivot.values[i, j])
            ax.text(j, i, str(rank), ha="center", va="center", fontsize=9,
                    color="white" if rank <= 2 else INK,
                    fontweight="bold" if rank == 1 else "normal")
    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels([f"{p + 1}" for p in pivot.columns])
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Target's presented position in search results (1 = shown first)")
    ax.tick_params(length=0)
    # 2px surface gaps between cells
    ax.set_xticks(np.arange(-0.5, pivot.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, pivot.shape[0], 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    save(fig, "fig_rank_heatmap")


def fig_tau() -> None:
    """Histogram: curation rate (Kendall tau, presented order vs model ranking)."""
    tau = exp2["curation_tau"].dropna().values
    fig, ax = plt.subplots(figsize=(5.4, 2.4))
    bins = np.arange(-1.0, 1.15, 0.1)
    ax.hist(tau, bins=bins, color=BLUE, edgecolor="white", linewidth=0.8, zorder=3)
    m = tau.mean()
    ax.axvline(m, color=INK, lw=1.4, zorder=4)
    ax.annotate(f"mean τ = {m:.2f}", (m, ax.get_ylim()[1] * 0.92), xytext=(6, 0),
                textcoords="offset points", fontsize=8.5, color=INK)
    ax.axvline(1.0, color=BASELINE, lw=1.0, zorder=2)
    ax.annotate("τ = 1: echoes\nsearch order", (1.0, ax.get_ylim()[1] * 0.62),
                xytext=(-8, 0), textcoords="offset points", ha="right",
                fontsize=7.5, color=SECONDARY)
    ax.set_xlabel("Kendall's τ between presented order and the model's ranking")
    ax.set_ylabel("Trials")
    ax.set_xlim(-1.05, 1.1)
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    save(fig, "fig_tau")


# ------------------------------------------------ Experiment 2b (FAQ confound)

def fig_faq() -> None:
    """Bar chart: target mean rank by treatment in the FAQ content-matched re-run.

    The clean contrast is prose_matched vs faq_matched: identical feature content,
    only the Q&A structure differs. Lower rank (leftward) is better."""
    path = ROOT / "data" / "runs" / "exp2b_faq" / "trials.csv"
    if not path.exists():
        print("  (skip fig_faq: exp2b_faq run not present)")
        return
    df = pd.read_csv(path)
    prim = df[df.rep == 0]
    means = prim.groupby("treatment")["target_rank"].mean()
    labels = {
        "prose_matched": "Prose, full features",
        "baseline": "Prose, partial features",
        "faq_matched": "FAQ, full features",
        "faq_original": "FAQ, partial features",
    }
    order = ["prose_matched", "baseline", "faq_matched", "faq_original"]
    order = [t for t in order if t in means.index]
    vals = [means[t] for t in order]
    ys = np.arange(len(order))[::-1]
    fig, ax = plt.subplots(figsize=(6.0, 2.5))
    ax.barh(ys, vals, height=0.6, color=BLUE, zorder=3)
    for y, v in zip(ys, vals):
        ax.annotate(f"{v:.1f}", (v, y), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels([labels.get(t, t) for t in order])
    ax.set_xlim(0, 5.4)
    ax.set_xlabel("Target's mean rank of 5 (1 = recommended first; lower is better)")
    ax.grid(axis="x", zorder=0)
    ax.set_axisbelow(True)
    save(fig, "fig_faq")


if __name__ == "__main__":
    fig_adoption()
    fig_search()
    fig_rank_heatmap()
    fig_tau()
    fig_faq()
