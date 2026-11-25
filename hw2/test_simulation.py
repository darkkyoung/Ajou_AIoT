import csv
import json
import random
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from simulation import (ROOMS, conditional_target, generate_dataset, get_occupancy,
                        next_co2, run_clock, simulate_room)


class SimulationTests(unittest.TestCase):
    def test_people_and_ventilation(self):
        self.assertGreater(next_co2(800, 30, 180, 20, 0), next_co2(800, 0, 180, 20, 0))
        self.assertLess(next_co2(1000, 20, 180, 100, 0), next_co2(1000, 20, 180, 20, 0))

    def test_sensor_bounds(self):
        self.assertEqual(next_co2(420, 0, 180, 100, -100), 420)
        self.assertEqual(next_co2(5000, 40, 180, 20, 1000), 5000)

    def test_room_profiles(self):
        self.assertEqual(get_occupancy(80, "classroom-01", random.Random(1)), ("empty", 0))
        self.assertGreater(get_occupancy(80, "computerlab-01", random.Random(1))[1], 0)
        self.assertGreater(get_occupancy(40, "computerlab-01", random.Random(1))[1],
                           get_occupancy(0, "computerlab-01", random.Random(1))[1])

    def test_room_sequence_and_reproducibility(self):
        for room, config in ROOMS.items():
            data = simulate_room(room, 0, 42)
            self.assertEqual(data, simulate_room(room, 0, 42))
            self.assertEqual([r["minute"] for r in data], list(range(90)))
            for i, r in enumerate(data):
                self.assertTrue(420 <= r["co2_ppm"] <= 5000)
                self.assertTrue(0 <= r["occupancy"] <= config["capacity"])
                self.assertIn(r["ventilation_pct"], [20, 60, 100])
                self.assertEqual(r["delta_co2_ppm"], round(r["co2_ppm"] - data[max(0, i-1)]["co2_ppm"], 2))

    def test_conditional_target(self):
        expected = 850
        for _ in range(5):
            expected = next_co2(expected, 35, 180, 20, 0)
        self.assertEqual(conditional_target(850, 35, 180, 20), expected)
        self.assertGreater(expected, conditional_target(850, 35, 180, 100))

    def test_csv_record_count_and_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = generate_dataset(directory)
            with path.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            with (Path(directory) / "training_data.csv").open(encoding="utf-8", newline="") as file:
                targets = list(csv.DictReader(file))
            self.assertEqual(len(rows), 10800)
            self.assertEqual(len(targets), 10800)
            self.assertEqual(len({(r["episode_id"], r["room_id"], r["minute"]) for r in rows}), 10800)
            for r, target in zip(rows, targets):
                self.assertEqual(r, {k: target[k] for k in r})
                self.assertEqual(float(target["target_co2_5min_ppm"]), conditional_target(
                    float(r["co2_ppm"]), int(r["occupancy"]), int(r["volume_m3"]), int(r["ventilation_pct"])))

    def test_clock_modes(self):
        for mode, seconds in [("live", 60), ("demo", 10)]:
            clock = [0]
            delays, output = [], []
            def sleep(delay):
                delays.append(delay)
                clock[0] += delay
            run_clock(mode, 3, sleep=sleep, monotonic=lambda: clock[0], emit=output.append)
            self.assertEqual(delays, [seconds, seconds])
            rows = [json.loads(s) for s in output]
            self.assertEqual(len(rows), 6)
            self.assertEqual([r["minute"] for r in rows], [0, 0, 1, 1, 2, 2])
            self.assertEqual((datetime.fromisoformat(rows[2]["simulated_at"]) -
                              datetime.fromisoformat(rows[0]["simulated_at"])).total_seconds(), 60)
            self.assertEqual(rows[0]["recorded_at"], rows[1]["recorded_at"])


if __name__ == "__main__":
    unittest.main()
