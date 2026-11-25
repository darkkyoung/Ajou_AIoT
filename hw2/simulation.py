"""Synthetic one-minute CO2 simulation for HW2 (not measured data)."""
import csv
import random
from pathlib import Path

OUTDOOR_CO2 = 420.0
CO2_LIMIT = 1000.0
EMISSION_RATE = 240.0

ROOMS = {
    "classroom-01": {"volume": 180, "capacity": 40},
    "computerlab-01": {"volume": 150, "capacity": 30},
}

VENTILATION_ACH = {20: 1.2, 60: 3.6, 100: 6.0}
BASE_DIR = Path(__file__).resolve().parent


def next_co2(co2, occupancy, volume, ventilation, noise):
    """One-minute mass-balance approximation, clipped to sensor range."""
    ach = VENTILATION_ACH[ventilation]
    generation = EMISSION_RATE * occupancy / volume
    removal = (ach / 60) * (co2 - OUTDOOR_CO2)
    result = co2 + generation - removal + noise
    return round(max(420.0, min(5000.0, result)), 2)


def get_occupancy(minute, capacity, rng):
    if minute < 15:
        scenario, ratio = "normal", 0.2
    elif minute < 40:
        scenario, ratio = "crowded", 0.9
    elif minute < 55:
        scenario, ratio = "occupied", 0.7
    elif minute < 75:
        scenario, ratio = "recovery", 0.1
    else:
        scenario, ratio = "empty", 0.0

    occupancy = 0 if ratio == 0 else round(capacity * ratio + rng.uniform(-3, 3))
    return scenario, max(0, min(capacity, occupancy))


def simulate_room(room_id, episode_id, seed):
    rng = random.Random(seed)
    room = ROOMS[room_id]
    co2 = rng.uniform(450, 800)
    records = []

    for minute in range(90):
        scenario, occupancy = get_occupancy(minute, room["capacity"], rng)

        # Explore different actions for training data; not the final controller.
        if minute % 15 == 0:
            ventilation = rng.choice([20, 60, 100])

        records.append({
            "episode_id": episode_id,
            "room_id": room_id,
            "minute": minute,
            "scenario": scenario,
            "co2_ppm": round(co2, 2),
            "occupancy": occupancy,
            "ventilation_pct": ventilation,
        })

        co2 = next_co2(co2, occupancy, room["volume"], ventilation, rng.gauss(0, 3))

    return records


def generate_dataset(output_dir=None):
    records = []
    for episode in range(60):
        for index, room_id in enumerate(ROOMS):
            records.extend(simulate_room(room_id, episode, 2026 + episode * 10 + index))

    output_dir = Path(output_dir) if output_dir is not None else BASE_DIR / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sensor_data.csv"

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print("Sensor simulation completed")
    print(f"Total records: {len(records)}")
    print(f"Rooms: {len(ROOMS)}")
    print(f"Output: {output_path}")
    print("\nSample records:")
    for record in records[:5]:
        print(record)
    return output_path


if __name__ == "__main__":
    generate_dataset()
