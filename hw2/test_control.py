import unittest
from unittest.mock import patch

from control import decide, environment, initial_state, simulate_policy, step_room
from simulation import next_co2


class ControlTests(unittest.TestCase):
    def test_decision_boundaries(self):
        self.assertEqual(decide(999, 999), ("normal", 20))
        self.assertEqual(decide(999, 1000), ("warning", 60))
        self.assertEqual(decide(1000, 800), ("high", 100))
        self.assertEqual(decide(999), ("normal", 20))
        self.assertEqual(decide(1000), ("high", 100))

    def test_forecast_uses_previous_output(self):
        state = initial_state(850)
        with patch("control.predict", return_value=1100) as mock:
            new, row = step_room("classroom-01", state, 35, 0, {})
            self.assertEqual(mock.call_args.args[1]["ventilation_pct"], 20)
        self.assertEqual(row["previous_ventilation_pct"], 20)
        self.assertEqual(row["ventilation_pct"], 60)
        self.assertEqual(new["co2_ppm"], next_co2(850, 35, 180, 60, 0))
        self.assertEqual(new["previous_co2_ppm"], 850)
        self.assertEqual(new["ventilation_pct"], 60)
        with patch("control.predict", return_value=900) as mock:
            step_room("classroom-01", new, 35, 0, {})
            self.assertEqual(mock.call_args.args[1]["ventilation_pct"], 60)

    def test_feedback_and_fair_inputs(self):
        start, inputs = environment("classroom-01", 300000)
        self.assertEqual((start, inputs), environment("classroom-01", 300000))
        baseline = simulate_policy("classroom-01", 0, start, inputs)
        with patch("control.predict", return_value=1100):
            ai = simulate_policy("classroom-01", 0, start, inputs, {})
        self.assertEqual(baseline[0]["co2_ppm"], ai[0]["co2_ppm"])
        self.assertEqual(len(ai), 90)
        for i, (b, a) in enumerate(zip(baseline, ai)):
            for key in ("occupancy", "scenario", "noise_ppm"):
                self.assertEqual(a[key], b[key])
            self.assertTrue(420 <= a["co2_ppm"] <= 5000)
            if i:
                self.assertEqual(a["co2_ppm"], ai[i-1]["next_co2_ppm"])
                self.assertEqual(a["previous_ventilation_pct"], ai[i-1]["ventilation_pct"])
        self.assertTrue(any(a["co2_ppm"] != b["co2_ppm"] for a, b in zip(ai, baseline)))


if __name__ == "__main__":
    unittest.main()
