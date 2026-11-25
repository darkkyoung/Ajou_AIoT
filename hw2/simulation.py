"""Synthetic CO2 environment; each simulation step is one virtual minute."""
import argparse
import csv
import json
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUTDOOR_CO2 = 420.0
CO2_LIMIT = 1000.0
EMISSION_RATE = 240.0
ROOMS = {
    "classroom-01": {"volume": 180, "capacity": 40},
    "computerlab-01": {"volume": 150, "capacity": 30},
}
VENTILATION_ACH = {20: 1.2, 60: 3.6, 100: 6.0}
CLOCK_SECONDS = {"live": 60, "demo": 10}
BASE_DIR = Path(__file__).resolve().parent


def next_co2(co2, occupancy, volume, ventilation, noise):
    generation = EMISSION_RATE * occupancy / volume
    removal = VENTILATION_ACH[ventilation] / 60 * (co2 - OUTDOOR_CO2)
    return round(max(420.0, min(5000.0, co2 + generation - removal + noise)), 2)


def get_occupancy(minute, room_id, rng):
    minute %= 90
    if room_id == "classroom-01":
        profile = [(15, "normal", .2), (40, "crowded", .9),
                   (55, "occupied", .7), (75, "recovery", .1), (90, "empty", 0)]
        scenario, ratio = next((name, ratio) for end, name, ratio in profile if minute < end)
    elif room_id == "computerlab-01":
        if minute < 45:
            scenario, ratio = "arrival", .35 + .55 * minute / 45
        elif minute < 65:
            scenario, ratio = "crowded", .9
        else:
            scenario, ratio = "departure", .9 - .55 * (minute - 65) / 25
    else:
        raise ValueError(f"Unknown room: {room_id}")
    capacity = ROOMS[room_id]["capacity"]
    count = 0 if ratio == 0 else round(capacity * ratio + rng.uniform(-3, 3))
    return scenario, max(0, min(capacity, count))


def conditional_target(co2, occupancy, volume, ventilation):
    """Noise-free five-minute counterfactual, keeping N and ventilation fixed."""
    for _ in range(5):
        co2 = next_co2(co2, occupancy, volume, ventilation, 0)
    return co2


def room_stream(room_id, episode_id, seed):
    """Infinite stateful stream; random ventilation is for exploration only."""
    rng = random.Random(seed)
    room = ROOMS[room_id]
    co2 = previous = round(rng.uniform(450, 800), 2)
    minute = 0
    while True:
        scenario, occupancy = get_occupancy(minute, room_id, rng)
        if minute % 15 == 0:
            ventilation = rng.choice([20, 60, 100])
        yield {"episode_id": episode_id, "room_id": room_id, "minute": minute,
               "scenario": scenario, "co2_ppm": co2, "occupancy": occupancy,
               "ventilation_pct": ventilation, "volume_m3": room["volume"],
               "delta_co2_ppm": round(co2 - previous, 2)}
        previous = co2
        co2 = next_co2(co2, occupancy, room["volume"], ventilation, rng.gauss(0, 3))
        minute += 1


def simulate_room(room_id, episode_id, seed):
    stream = room_stream(room_id, episode_id, seed)
    return [next(stream) for _ in range(90)]


def write_csv(path, records):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


def generate_dataset(output_dir=None):
    records = [record for episode in range(60) for index, room_id in enumerate(ROOMS)
               for record in simulate_room(room_id, episode, 2026 + episode * 10 + index)]
    output_dir = Path(output_dir) if output_dir is not None else BASE_DIR / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sensor_data.csv"
    write_csv(output_path, records)
    targets = [dict(r, target_co2_5min_ppm=conditional_target(
        r["co2_ppm"], r["occupancy"], r["volume_m3"], r["ventilation_pct"])) for r in records]
    write_csv(output_dir / "training_data.csv", targets)
    print(f"Total records: {len(records)}; Rooms: {len(ROOMS)}")
    print(f"Sensor data: {output_path}\nTraining data: {output_dir / 'training_data.csv'}")
    return output_path


def run_clock(mode, steps, *, sleep=time.sleep, monotonic=time.monotonic, emit=print):
    """Local clock demo. The simulated minute is independent of wall time."""
    if steps < 1:
        raise ValueError("steps must be positive")
    interval = CLOCK_SECONDS[mode]
    start = datetime.now(timezone.utc)
    deadline = monotonic()
    streams = [room_stream(room_id, 0, 2026 + i) for i, room_id in enumerate(ROOMS)]
    for minute in range(steps):
        if minute:
            deadline += interval
            sleep(max(0, deadline - monotonic()))
        recorded = datetime.now(timezone.utc).isoformat()
        simulated = (start + timedelta(minutes=minute)).isoformat()
        for stream in streams:
            emit(json.dumps(dict(next(stream), clock_mode=mode,
                                 recorded_at=recorded, simulated_at=simulated)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["batch", "live", "demo"], default="batch")
    parser.add_argument("--steps", type=int, default=6)
    args = parser.parse_args()
    if args.mode == "batch":
        generate_dataset()
    elif args.steps < 1:
        parser.error("--steps must be positive")
    else:
        run_clock(args.mode, args.steps)
