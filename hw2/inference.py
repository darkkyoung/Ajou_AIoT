"""Dependency-free model inference, compatible with Lambda Python 3.12."""
import json
import math
import struct
from pathlib import Path

FEATURES = ["co2_ppm", "occupancy", "ventilation_pct", "volume_m3", "delta_co2_ppm"]


def load_model(path):
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    if model["version"] != 1 or model["features"] != FEATURES:
        raise ValueError("Unsupported model schema")
    return model


def predict(model, record):
    x = [float(record[name]) for name in FEATURES]
    if not all(math.isfinite(v) for v in x):
        raise ValueError("Non-finite feature")
    if model["kind"] == "linear_regression":
        return model["intercept"] + sum(w * v for w, v in zip(model["coef"], x))
    if model["kind"] == "random_forest":
        # sklearn tree predictors compare float32 inputs with float64 thresholds.
        x = [struct.unpack("f", struct.pack("f", v))[0] for v in x]
        values = []
        for tree in model["trees"]:
            node = 0
            while tree["left"][node] != -1:
                node = (tree["left"][node] if x[tree["feature"][node]] <= tree["threshold"][node]
                        else tree["right"][node])
            values.append(tree["value"][node])
        return sum(values) / len(values)
    raise ValueError("Unsupported model type")
