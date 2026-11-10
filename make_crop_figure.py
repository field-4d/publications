"""Fig. S7 and Tables S7-S8 — crop-specific evaluation of the Fig. 3 predictions.

Post hoc only: no model is trained. The saved out-of-fold predictions of the
headline DOB-SCV run (predictions/full_data_preds.csv, training fraction 1.0)
are joined to plants and re-scored separately for each crop.

  Fig. S7 A/B  predictive R^2 per crop (Chinese spinach, Chinese broccoli) for
               AutoGluon and TabPFN, pooled over the five folds; grey ticks show
               the both-crops R^2 of Fig. 3. Error bars: approximate 95 %
               conditional cluster-bootstrap intervals (2,000 draws, seed 42;
               complete dosing conditions resampled within each experiment,
               predictions held fixed, nothing refitted).
  Fig. S7 C    share of the total observed sum of squares lying between the two
               crop means (SS_between / SS_total, one value per plant).
  Tables S7/S8 observed concentration summaries per crop (mean, SD, median,
               IQR, min, max) with plant / condition / experiment counts.

Join. full_data_preds.csv has no plant IDs, but training.py writes each
(Target, Fold, Model) block in the row order of df_strat.iloc[test_idx], and the
DOB-SCV partition is deterministic. The partition is rebuilt and every block's
saved `Actual` must equal the dataset values at those rows, or the script stops.

Crop coding: Plant_type 0 = Chinese spinach (Amaranthus dubius),
1 = Chinese broccoli (Brassica oleracea Alboglabra Group); the Mo experiment
(Experiment 16) is broccoli-only.

    python make_crop_figure.py --run-dir <Ionomic_Prediction_Run_dobscv_...> [--out crop_eval]
"""
from __future__ import annotations

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import TARGETS_AVAILABLE
from data import build_folds, load_dataset

MODELS = ("AutoGluon", "TabPFN")
CROPS = {0: "Chinese spinach", 1: "Chinese broccoli"}
DISP = {"NO3_output": "NO₃⁻", "TRN_output": "TRN", "P_output": "P", "K_output": "K",
        "Ca_output": "Ca", "Mg_output": "Mg", "Fe_output": "Fe", "Mn_output": "Mn",
        "Zn_output": "Zn", "Bo_output": "B", "Mo_output": "Mo", "Na_output": "Na"}
CROP_STYLE = {0: dict(color="#2F5B84", marker="o", dy=-0.13),
              1: dict(color="#D9862F", marker="^", dy=0.13)}
N_BOOT, SEED = 2000, 42


def r2(y, p, axis=0):
    sst = ((y - y.mean(axis=axis)) ** 2).sum(axis=axis)
    return 1.0 - ((y - p) ** 2).sum(axis=axis) / sst


def load(run_dir):
    df, folds = build_folds(load_dataset(), scheme="dobscv")
    targets = list(TARGETS_AVAILABLE)
    raw = pd.read_csv(os.path.join(run_dir, "predictions", "full_data_preds.csv"))
    raw = raw[raw.Model.isin(MODELS)]
    P = {m: np.full((len(df), len(targets)), np.nan) for m in MODELS}
    for (t, k, m), g in raw.groupby(["Target", "Fold", "Model"], sort=False):
        te = folds[int(k)][1]
        if len(g) != len(te) or not np.allclose(g.Actual.values,
                                                df[t].values[te], rtol=0, atol=1e-9):
            raise SystemExit(f"positional join failed for {(t, k, m)}")
        P[m][te, targets.index(t)] = g.Predicted.values
    if any(np.isnan(v).any() for v in P.values()):
        raise SystemExit("predictions missing for some plant/target/model")
    return df, targets, P


def bootstrap_r2(df, targets, P):
    """Conditions resampled with replacement within each experiment."""
    Y = df[targets].to_numpy(float)
    pt = df["Plant_type"].to_numpy()
    cond = (df["Experiment_ID"].astype(str) + "::"
            + df["Active_Gradient"].astype(str)).values
    rows_of = {c: np.flatnonzero(cond == c) for c in pd.unique(cond)}
    exp_conds = {e: pd.unique(cond[df["Experiment_ID"].values == e])
                 for e in sorted(df["Experiment_ID"].unique())}
    rng = np.random.default_rng(SEED)
    draws = {(m, c): [] for m in MODELS for c in CROPS}
    for _ in range(N_BOOT):
        idx = np.concatenate([rows_of[c] for e, cs in exp_conds.items()
                              for c in rng.choice(cs, size=len(cs), replace=True)])
        for c in CROPS:
            sel = idx[pt[idx] == c]
            for m in MODELS:
                draws[(m, c)].append(r2(Y[sel], P[m][sel]))
    ci = {}
    for key, d in draws.items():
        d = np.asarray(d)
        ci[key] = (np.nanpercentile(d, 2.5, axis=0), np.nanpercentile(d, 97.5, axis=0))
    return ci


def summarise(df, targets, P, ci):
    Y = df[targets].to_numpy(float)
    pt = df["Plant_type"].to_numpy()
    rows = []
    for j, t in enumerate(targets):
        y = Y[:, j]
        ss_tot = ((y - y.mean()) ** 2).sum()
        ss_between = sum((pt == c).sum() * (y[pt == c].mean() - y.mean()) ** 2
                         for c in CROPS)
        for m in MODELS:
            row = {"target": DISP[t], "model": m,
                   "R2_pooled": r2(y, P[m][:, j]),
                   "between_crop_pct": 100 * ss_between / ss_tot}
            for c, name in CROPS.items():
                k = pt == c
                tag = name.split()[1]
                row[f"R2_{tag}"] = r2(y[k], P[m][k, j])
                row[f"R2_{tag}_ci2.5"] = ci[(m, c)][0][j]
                row[f"R2_{tag}_ci97.5"] = ci[(m, c)][1][j]
            rows.append(row)
    return pd.DataFrame(rows)


def crop_tables(df, targets):
    out = {}
    cond = df["Experiment_ID"].astype(str) + "::" + df["Active_Gradient"].astype(str)
    for c, name in CROPS.items():
        sub = df[df.Plant_type == c]
        rows = []
        for t in targets:
            y = sub[t].to_numpy(float)
            q1, med, q3 = np.percentile(y, [25, 50, 75])
            rows.append({"Mineral": DISP[t], "Mean": y.mean(), "SD": y.std(ddof=1),
                         "Median": med, "IQR": q3 - q1, "Minimum": y.min(),
                         "Maximum": y.max()})
        tab = pd.DataFrame(rows)
        tab.attrs["counts"] = (len(sub), cond[sub.index].nunique(),
                               sub.Experiment_ID.nunique())
        out[name] = tab
    return out


def plot(res, out_base):
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42,
                         "font.size": 11})
    order = list(DISP.values())
    ypos = {t: i for i, t in enumerate(order)}
    fig, axes = plt.subplots(1, 3, figsize=(14, 8.6),
                             gridspec_kw={"width_ratios": [1, 1, 0.82], "wspace": 0.38})
    for ax, m, letter in zip(axes[:2], MODELS, "AB"):
        r = res[res.model == m].set_index("target").loc[order]
        for c, name in CROPS.items():
            tag, st = name.split()[1], CROP_STYLE[c]
            y = np.array([ypos[t] for t in order]) + st["dy"]
            lo, hi = r[f"R2_{tag}_ci2.5"], r[f"R2_{tag}_ci97.5"]
            ax.errorbar(r[f"R2_{tag}"], y, xerr=[r[f"R2_{tag}"] - lo, hi - r[f"R2_{tag}"]],
                        fmt=st["marker"], color=st["color"], ms=8, lw=1.6, capsize=0,
                        label=name, zorder=3)
        ax.scatter(r["R2_pooled"], [ypos[t] for t in order], marker="|", s=380,
                   lw=2.2, color="#777777", zorder=2, label="Both crops combined")
        ax.set_xlim(0, 1.03)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xlabel("Predictive R²", fontsize=14)
        ax.set_title(m, fontsize=15, pad=40)
        ax.grid(axis="x", color="#e5e5e5", lw=0.8)
        ax.set_axisbelow(True)
    r = res[res.model == MODELS[0]].set_index("target").loc[order]
    ax = axes[2]
    ax.barh([ypos[t] for t in order], r["between_crop_pct"], height=0.5, color="#737373")
    for t, v in r["between_crop_pct"].items():
        ax.text(v + 1, ypos[t], f"{v:.2f}%" if v < 0.1 else f"{v:.1f}%",
                va="center", fontsize=12)
    ax.set_xlim(0, 79)
    ax.set_xticks([0, 20, 40, 60])
    ax.set_xlabel("Between-crop variation (%)", fontsize=14)
    ax.set_title("Observed variation", fontsize=15, pad=40)
    ax.grid(axis="x", color="#e5e5e5", lw=0.8)
    ax.set_axisbelow(True)
    for ax, letter in zip(axes, "ABC"):
        ax.set_yticks(range(len(order)), order, fontsize=14)
        ax.set_ylim(len(order) - 0.4, -0.6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(-0.17, 1.09, letter, transform=ax.transAxes, fontsize=18,
                fontweight="bold")
    h, l = axes[0].get_legend_handles_labels()
    order_ = [l.index(n) for n in (*CROPS.values(), "Both crops combined")]
    fig.legend([h[i] for i in order_], [l[i] for i in order_], ncol=3, frameon=False,
               loc="lower center", bbox_to_anchor=(0.36, 0.02), fontsize=13)
    fig.subplots_adjust(bottom=0.15)
    for ext in ("pdf", "png"):
        fig.savefig(f"{out_base}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default="crop_eval")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    df, targets, P = load(a.run_dir)
    res = summarise(df, targets, P, bootstrap_r2(df, targets, P))
    res.to_csv(os.path.join(a.out, "fig_S7_crop_r2.csv"), index=False, float_format="%.6g")
    plot(res, os.path.join(a.out, "fig_S7_crop_r2"))
    for name, tab in crop_tables(df, targets).items():
        n_pl, n_cond, n_exp = tab.attrs["counts"]
        fname = "table_S7_spinach.csv" if "spinach" in name else "table_S8_broccoli.csv"
        tab.to_csv(os.path.join(a.out, fname), index=False, float_format="%.4g")
        print(f"{name}: {n_pl} plants, {n_cond} dosing conditions, {n_exp} experiments")
    print(res.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
