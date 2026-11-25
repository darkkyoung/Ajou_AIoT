"""Paired closed-loop comparison on new synthetic episodes."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from control import environment, simulate_policy
from inference import load_model
from simulation import CO2_LIMIT, ROOMS

BASE = Path(__file__).resolve().parent
EPISODES = 20
SEED = 300000


def summarize(rows):
    # The current sample represents the beginning of each one-minute interval.
    co2 = rows.co2_ppm
    vent = rows.ventilation_pct
    return {"room_minutes": len(rows), "mean_co2_ppm": float(co2.mean()),
            "max_co2_ppm": float(co2.max()), "at_or_above_limit_minutes": int((co2 >= CO2_LIMIT).sum()),
            "excess_ppm_minutes": float((co2 - CO2_LIMIT).clip(lower=0).sum()),
            "ventilation_pct_minutes": int(vent.sum()), "mean_ventilation_pct": float(vent.mean()),
            "preventive_minutes": int((vent == 60).sum()), "strong_minutes": int((vent == 100).sum()),
            "switches": int((vent != rows.previous_ventilation_pct).sum())}


def main(model_path, output):
    model = load_model(model_path)
    records = []
    for episode in range(EPISODES):
        for index, room in enumerate(ROOMS):
            start, inputs = environment(room, SEED + episode * 10 + index)
            for policy_model in (None, model):
                records.extend(simulate_policy(room, episode, start, inputs, policy_model))
    df = pd.DataFrame(records)
    keys = ["episode_id", "room_id", "minute"]
    reactive = df[df.policy == "reactive"].set_index(keys).sort_index()
    ai = df[df.policy == "ai"].set_index(keys).sort_index()
    assert reactive.index.equals(ai.index)
    assert reactive[["occupancy", "noise_ppm", "scenario"]].equals(ai[["occupancy", "noise_ppm", "scenario"]])
    assert reactive.loc[(slice(None), slice(None), 0), "co2_ppm"].equals(ai.loc[(slice(None), slice(None), 0), "co2_ppm"])
    groups = {"overall": {p: summarize(df[df.policy == p]) for p in ("reactive", "ai")},
              "by_room": {room: {p: summarize(df[(df.room_id == room) & (df.policy == p)])
                                  for p in ("reactive", "ai")} for room in ROOMS}}
    report = {"model": model["kind"], "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
              "episodes": EPISODES, "minutes_per_episode": 90, "seed_base": SEED,
              "limit_ppm": CO2_LIMIT, "comparison": groups}
    output.mkdir(parents=True, exist_ok=True)
    df.to_csv(output / "control_timeseries.csv", index=False)
    (output / "control_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for room in ROOMS:
        fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True)
        sample = df[(df.episode_id == 0) & (df.room_id == room)]
        for policy in ("reactive", "ai"):
            part = sample[sample.policy == policy]
            axes[0].plot(part.minute, part.co2_ppm, label=policy)
            axes[1].step(part.minute, part.ventilation_pct, where="post", label=policy)
        axes[0].axhline(CO2_LIMIT, linestyle="--", label="1000 ppm threshold")
        axes[0].set_ylabel("CO2 (ppm)"); axes[0].legend()
        axes[1].set_ylabel("Ventilation (%)"); axes[1].legend()
        part = sample[sample.policy == "ai"]
        axes[2].step(part.minute, part.occupancy, where="post")
        axes[2].set(xlabel="Simulated minute", ylabel="Occupants")
        fig.suptitle(f"{room}: paired episode 0")
        fig.tight_layout(); fig.savefig(output / f"{room}.png", dpi=160); plt.close(fig)
    print(json.dumps(report, indent=2))
    print(f"Results: {output}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=BASE / "models" / "selected_model.json")
    parser.add_argument("--output", type=Path, default=BASE / "results" / "step4")
    args = parser.parse_args()
    main(args.model, args.output)
