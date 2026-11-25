"""Train on synthetic conditional targets; select using validation MAE only."""
import argparse
import json
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, confusion_matrix

from inference import FEATURES, load_model, predict
from simulation import CO2_LIMIT, ROOMS, conditional_target

BASE = Path(__file__).resolve().parent
TARGET = "target_co2_5min_ppm"
SEED = 2026


def split_data(df):
    keys = ["episode_id", "room_id", "minute"]
    if df.duplicated(keys).any() or df[FEATURES + [TARGET]].isna().any().any():
        raise ValueError("Duplicate keys or missing feature/target")
    if not np.isfinite(df[FEATURES + [TARGET]].to_numpy()).all():
        raise ValueError("Non-finite feature/target")
    episodes = sorted(df.episode_id.unique().tolist())
    if len(episodes) != 60 or len(df) != 10800:
        raise ValueError("Expected 60 episodes and 10800 rows; regenerate STEP 2 data")
    for (_, room), g in df.groupby(["episode_id", "room_id"]):
        if room not in ROOMS or sorted(g.minute.tolist()) != list(range(90)):
            raise ValueError("Incomplete room episode")
    if set(df.room_id) != set(ROOMS):
        raise ValueError("Unexpected room set")
    random.Random(SEED).shuffle(episodes)
    ids = {"train": sorted(episodes[:42]), "validation": sorted(episodes[42:51]),
           "test": sorted(episodes[51:])}
    return ids, {k: df[df.episode_id.isin(v)].copy() for k, v in ids.items()}


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y >= CO2_LIMIT, pred >= CO2_LIMIT, labels=[False, True]).ravel()
    return {"mae": float(mean_absolute_error(y, pred)), "rmse": float(np.sqrt(mean_squared_error(y, pred))),
            "r2": float(r2_score(y, pred)), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "precision": float(tp / (tp + fp)) if tp + fp else 0.0,
            "recall": float(tp / (tp + fn)) if tp + fn else 0.0}


def export_model(name, estimator):
    model = {"version": 1, "kind": name, "features": FEATURES}
    if name == "linear_regression":
        model.update(intercept=float(estimator.intercept_), coef=estimator.coef_.tolist())
    else:
        model["trees"] = [{"left": t.tree_.children_left.tolist(), "right": t.tree_.children_right.tolist(),
                           "feature": t.tree_.feature.tolist(), "threshold": t.tree_.threshold.tolist(),
                           "value": t.tree_.value[:, 0, 0].tolist()} for t in estimator.estimators_]
    return model


def main(data, output, models):
    df = pd.read_csv(data)
    ids, parts = split_data(df)
    output.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)
    estimators = {"linear_regression": LinearRegression(),
                  "random_forest": RandomForestRegressor(n_estimators=64, max_depth=12,
                      min_samples_leaf=2, random_state=SEED, n_jobs=1)}
    for estimator in estimators.values():
        estimator.fit(parts["train"][FEATURES], parts["train"][TARGET])
    def predictions(part):
        return {"persistence": part.co2_ppm.to_numpy(), **{
            name: estimator.predict(part[FEATURES]) for name, estimator in estimators.items()}}
    val = parts["validation"]
    validation = {name: metrics(val[TARGET].to_numpy(), pred) for name, pred in predictions(val).items()}
    selected = min(estimators, key=lambda name: validation[name]["mae"])
    test = parts["test"]
    preds = predictions(test)
    test_metrics = {name: metrics(test[TARGET].to_numpy(), pred) for name, pred in preds.items()}
    # Oracle is a simulator sanity check, not a trained model or selection candidate.
    oracle = np.array([conditional_target(r.co2_ppm, r.occupancy, r.volume_m3, r.ventilation_pct)
                       for r in test.itertuples()])
    if not np.allclose(oracle, test[TARGET].to_numpy(), rtol=0, atol=1e-8):
        raise ValueError("Training targets differ from simulator; regenerate data")
    parity = {}
    for name, estimator in estimators.items():
        path = models / (name + ".json")
        path.write_text(json.dumps(export_model(name, estimator), separators=(",", ":")), encoding="utf-8")
        model = load_model(path)
        portable = np.array([predict(model, r) for r in test[FEATURES].to_dict("records")])
        parity[name] = float(np.max(np.abs(portable - preds[name])))
        if parity[name] > 1e-6:
            raise ValueError(f"Export parity failed for {name}: {parity[name]}")
    (models / "selected_model.json").write_bytes((models / (selected + ".json")).read_bytes())
    report = {"seed": SEED, "sklearn_version": sklearn.__version__, "features": FEATURES,
              "target": TARGET, "episodes": ids, "counts": {k: len(v) for k, v in parts.items()},
              "selection_rule": "minimum validation MAE among trained models", "selected_model": selected,
              "validation": validation, "test": test_metrics, "oracle_test": metrics(test[TARGET].to_numpy(), oracle),
              "export_max_abs_error_ppm": parity,
              "selected_model_bytes": (models / "selected_model.json").stat().st_size}
    (output / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    test = test.copy()
    for name, pred in preds.items():
        test[name + "_prediction"] = pred
    test.to_csv(output / "test_predictions.csv", index=False)
    names = list(preds)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(names, [test_metrics[n]["mae"] for n in names])
    ax.set_ylabel("MAE (ppm)")
    ax.set_title("Held-out synthetic episodes")
    fig.tight_layout(); fig.savefig(output / "model_mae.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 6))
    y = test[TARGET].to_numpy()
    for name in estimators:
        ax.scatter(y, preds[name], s=6, alpha=.4, label=name)
    ax.plot([y.min(), y.max()], [y.min(), y.max()], "k--")
    ax.set(xlabel="Conditional target (ppm)", ylabel="Prediction (ppm)")
    ax.legend(); fig.tight_layout(); fig.savefig(output / "predictions.png", dpi=160); plt.close(fig)
    print(json.dumps(report, indent=2))
    print(f"Results: {output}\nSelected model: {models / 'selected_model.json'}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=BASE / "data" / "training_data.csv")
    parser.add_argument("--output", type=Path, default=BASE / "results" / "step3")
    parser.add_argument("--models", type=Path, default=BASE / "models")
    args = parser.parse_args()
    main(args.data, args.output, args.models)
