"""Stateful ventilation controller; no third-party dependencies."""
import argparse
import json
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from inference import load_model, predict
from simulation import CLOCK_SECONDS, CO2_LIMIT, ROOMS, get_occupancy, next_co2

BASE = Path(__file__).resolve().parent


def decide(co2, forecast=None):
    if co2 >= CO2_LIMIT:
        return "high", 100
    if forecast is not None and forecast >= CO2_LIMIT:
        return "warning", 60
    return "normal", 20


def initial_state(co2):
    return {"co2_ppm": co2, "previous_co2_ppm": co2, "ventilation_pct": 20}


def step_room(room_id, state, occupancy, noise, model=None):
    """Observe, predict under previous ventilation, decide, then advance one minute."""
    co2 = state["co2_ppm"]
    volume = ROOMS[room_id]["volume"]
    features = {"co2_ppm": co2, "occupancy": occupancy,
                "ventilation_pct": state["ventilation_pct"], "volume_m3": volume,
                "delta_co2_ppm": round(co2 - state["previous_co2_ppm"], 2)}
    forecast = predict(model, features) if model is not None else None
    status, action = decide(co2, forecast)
    future = next_co2(co2, occupancy, volume, action, noise)
    record = {**features, "previous_ventilation_pct": features["ventilation_pct"],
              "ventilation_pct": action, "predicted_co2_5min_ppm": forecast,
              "status": status, "next_co2_ppm": future}
    new_state = {"co2_ppm": future, "previous_co2_ppm": co2, "ventilation_pct": action}
    return new_state, record


def environment(room_id, seed, minutes=90):
    """Precompute exogenous inputs so policies see identical disturbances."""
    rng = random.Random(seed)
    start = round(rng.uniform(450, 800), 2)
    inputs = []
    for minute in range(minutes):
        scenario, occupancy = get_occupancy(minute, room_id, rng)
        inputs.append((scenario, occupancy, rng.gauss(0, 3)))
    return start, inputs


def simulate_policy(room_id, episode, start, inputs, model=None):
    state = initial_state(start)
    rows = []
    for minute, (scenario, occupancy, noise) in enumerate(inputs):
        state, row = step_room(room_id, state, occupancy, noise, model)
        rows.append({"episode_id": episode, "room_id": room_id, "minute": minute,
                     "policy": "ai" if model is not None else "reactive",
                     "scenario": scenario, "noise_ppm": noise, **row})
    return rows


def run_clock(model, mode, steps, seed=300000):
    if steps < 1:
        raise ValueError("steps must be positive")
    start_time = datetime.now(timezone.utc)
    deadline = time.monotonic()
    streams = {}
    for i, room in enumerate(ROOMS):
        start, inputs = environment(room, seed + i, steps)
        streams[room] = (initial_state(start), inputs)
    for minute in range(steps):
        if minute:
            deadline += CLOCK_SECONDS[mode]
            time.sleep(max(0, deadline - time.monotonic()))
        recorded = datetime.now(timezone.utc).isoformat()
        simulated = (start_time + timedelta(minutes=minute)).isoformat()
        for room, (state, inputs) in streams.items():
            scenario, occupancy, noise = inputs[minute]
            state, row = step_room(room, state, occupancy, noise, model)
            streams[room] = (state, inputs)
            print(json.dumps(dict(row, room_id=room, minute=minute, scenario=scenario,
                                  clock_mode=mode, recorded_at=recorded, simulated_at=simulated)), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=BASE / "models" / "selected_model.json")
    parser.add_argument("--mode", choices=["live", "demo"], default="demo")
    parser.add_argument("--steps", type=int, default=6)
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("--steps must be positive")
    run_clock(load_model(args.model), args.mode, args.steps)
