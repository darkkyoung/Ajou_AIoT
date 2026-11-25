import csv
import tempfile
import unittest

from simulation import ROOMS, generate_dataset, next_co2, simulate_room


class SimulationTests(unittest.TestCase):
    def test_more_people_increase_co2(self):
        self.assertGreater(next_co2(800, 30, 180, 20, 0),
                           next_co2(800, 0, 180, 20, 0))

    def test_stronger_ventilation_reduces_co2(self):
        self.assertLess(next_co2(1000, 20, 180, 100, 0),
                        next_co2(1000, 20, 180, 20, 0))

    def test_sensor_bounds(self):
        self.assertEqual(next_co2(420, 0, 180, 100, -100), 420)
        self.assertEqual(next_co2(5000, 40, 180, 20, 1000), 5000)

    def test_room_sequence_and_reproducibility(self):
        for room, config in ROOMS.items():
            data = simulate_room(room, 0, 42)
            self.assertEqual(data, simulate_room(room, 0, 42))
            self.assertEqual([r["minute"] for r in data], list(range(90)))
            for r in data:
                self.assertTrue(420 <= r["co2_ppm"] <= 5000)
                self.assertTrue(0 <= r["occupancy"] <= config["capacity"])
                self.assertIn(r["ventilation_pct"], [20, 60, 100])

    def test_csv_record_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = generate_dataset(directory)
            with path.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 10800)
            self.assertEqual(len({(r["episode_id"], r["room_id"], r["minute"])
                                  for r in rows}), 10800)


if __name__ == "__main__":
    unittest.main()
