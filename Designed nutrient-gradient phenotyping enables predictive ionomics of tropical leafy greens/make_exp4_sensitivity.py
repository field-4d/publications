"""Fig. S5c — sensitivity of TabPFN prediction to the xLSTM-imputed Experiment 4.

Experiment 4 (potassium gradient, Chinese broccoli) is the one cultivation cycle
whose internal microclimate was reconstructed by the xLSTM (Section 2.3.2). This
script compares TabPFN v3 under the production DOB-SCV partition

  * "All data"                 - all 1,163 plants (as in Fig. 3), and
  * "Experiment 4 excluded"    - the same fold assignment with every Experiment 4
                                 plant removed from both training and validation.

Keeping the production partition fixed (rather than rebuilding DOB-SCV without
Experiment 4) means every other dosing condition stays in the same fold, so the
comparison isolates the effect of removing Experiment 4.

Both arms are trained here with the same code path as the article's full-size
TabPFN fits (training._fit_tabpfn on the full training fold, shuffled with
RANDOM_STATE), and scored by pooled out-of-fold R^2 per target. Pass --run-dir
to also report how closely the "All data" arm reproduces that run's saved
TabPFN predictions.

    python make_exp4_sensitivity.py [--out exp4_sensitivity] [--run-dir <dir>]

Outputs (in --out): predictions.csv (cached; rerun resumes), r2_by_target.csv,
fig_S5c_exp4_sensitivity.{pdf,png}.
"""
from __future__ import annotations

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from config import FEATURES, RANDOM_STATE, TARGETS_AVAILABLE
from data import build_folds, load_dataset
from training import _fit_tabpfn

EXCLUDED_EXP = 4
ARMS = ("All data", "Experiment 4 excluded")
ARM_COLOR = {"All data": "#4472C4", "Experiment 4 excluded": "#E08A2C"}
DISP = {t: ("B" if t == "Bo_output" else t.replace("_output", ""))
        for t in TARGETS_AVAILABLE}


def run_predictions(out_csv: str) -> pd.DataFrame:
    df, folds = build_folds(load_dataset(), scheme="dobscv")
    done = pd.read_csv(out_csv) if os.path.exists(out_csv) else None
    for arm in ARMS:
        keep = (np.ones(len(df), bool) if arm == "All data"
                else (df["Experiment_ID"] != EXCLUDED_EXP).values)
        for target in TARGETS_AVAILABLE:
            for k, (tr, te) in enumerate(folds):
                if done is not None and ((done.Arm == arm) & (done.Target == target)
                                         & (done.Fold == k)).any():
                    continue
                train_full = df.iloc[tr[keep[tr]]]
                test_df = df.iloc[te[keep[te]]]
                # identical to training.run_training at Training_Frac = 1.0
                train = train_full.sample(n=len(train_full), random_state=RANDOM_STATE)
                model = _fit_tabpfn(train[FEATURES], train[target])
                pred = model.predict(test_df[FEATURES].values)
                block = pd.DataFrame({
                    "Arm": arm, "Target": target, "Fold": k,
                    "row": test_df.index, "Experiment_ID": test_df["Experiment_ID"].values,
                    "Actual": test_df[target].values, "Predicted": pred,
                })
                block.to_csv(out_csv, mode="a", index=False,
                             header=not os.path.exists(out_csv))
                print(f"[{arm}] {target} fold {k}: n_train={len(train)} "
                      f"n_test={len(test_df)}", flush=True)
    return pd.read_csv(out_csv)


def pooled_r2(preds: pd.DataFrame) -> pd.DataFrame:
    r = (preds.groupby(["Target", "Arm"])
         .apply(lambda g: r2_score(g.Actual, g.Predicted), include_groups=False)
         .unstack("Arm").reindex(TARGETS_AVAILABLE)[list(ARMS)])
    r["delta_R2"] = r[ARMS[1]] - r[ARMS[0]]
    r.index = [DISP[t] for t in r.index]
    r.index.name = "Target"
    return r


def plot(r2: pd.DataFrame, out_base: str) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    x = np.arange(len(r2))
    w = 0.38
    for i, arm in enumerate(ARMS):
        ax.bar(x + (i - 0.5) * w, r2[arm], w, color=ARM_COLOR[arm], label=arm,
               edgecolor="white", linewidth=0.6)
    ax.set_xticks(x, r2.index)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("R²")
    ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.08))
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(-0.07, 1.06, "c", transform=ax.transAxes, fontsize=14, fontweight="bold")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{out_base}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="exp4_sensitivity")
    ap.add_argument("--run-dir", default=None,
                    help="optional: compare the 'All data' arm with this run's "
                         "saved TabPFN predictions/full_data_preds.csv")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    preds = run_predictions(os.path.join(a.out, "predictions.csv"))
    r2 = pooled_r2(preds)
    r2.to_csv(os.path.join(a.out, "r2_by_target.csv"), float_format="%.4f")
    plot(r2, os.path.join(a.out, "fig_S5c_exp4_sensitivity"))

    print(r2.round(3).to_string())
    print(f"\nmean R2: {r2[ARMS[0]].mean():.3f} -> {r2[ARMS[1]].mean():.3f}; "
          f"mean |dR2| = {r2.delta_R2.abs().mean():.3f}; "
          f"max |dR2| = {r2.delta_R2.abs().max():.3f} ({r2.delta_R2.abs().idxmax()})")

    if a.run_dir:
        ref = pd.read_csv(os.path.join(a.run_dir, "predictions", "full_data_preds.csv"))
        ref = ref[ref.Model == "TabPFN"]
        mine = preds[preds.Arm == ARMS[0]]
        rows = []
        for t in TARGETS_AVAILABLE:
            r_ref = r2_score(ref[ref.Target == t].Actual, ref[ref.Target == t].Predicted)
            r_me = r2_score(mine[mine.Target == t].Actual, mine[mine.Target == t].Predicted)
            rows.append((DISP[t], r_ref, r_me, r_me - r_ref))
        cmp_ = pd.DataFrame(rows, columns=["Target", "R2_run_dir", "R2_here", "diff"])
        print("\n'All data' arm vs saved run predictions (pooled R2):")
        print(cmp_.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
