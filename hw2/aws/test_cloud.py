"""Offline fake-S3 integration tests, no credentials or boto3 required."""
import io
import json
import unittest
from datetime import datetime, timedelta, timezone

from generate import tick
from reader import read

MODEL = {"kind": "linear_regression", "coef": [0, 0, 0, 0, 0], "intercept": 1100}
START = datetime(2026, 11, 26, 23, 59, 50, tzinfo=timezone.utc)


class FakeS3:
    def __init__(self):
        self.data = {}
    def get_paginator(self, name):
        return self
    def paginate(self, Bucket, Prefix):
        found = [{"Key": k} for k in sorted(self.data) if k.startswith(Prefix)]
        return [{"Contents": found[i:i+2]} for i in range(0, len(found), 2)] or [{}]
    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.data[Key])}
    def put_object(self, Bucket, Key, Body, ContentType, IfNoneMatch):
        if IfNoneMatch != "*" or Key in self.data:
            raise AssertionError("Unexpected overwrite")
        self.data[Key] = Body


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.s3 = FakeS3()
    def emit(self, seconds=0, mode="demo", event=None):
        now = START + timedelta(seconds=seconds)
        return tick(self.s3, "test", MODEL, event or {"mode": mode}, now)
    def request(self, **kwargs):
        return read(self.s3, "test", {"entityId": "classroom-01", "componentName": "air_quality",
                    "startTime": START.isoformat(), "endTime": (START+timedelta(minutes=3)).isoformat(),
                    **kwargs}, START+timedelta(minutes=3))
    def test_two_rooms_and_feedback(self):
        a, b = self.emit(), self.emit(10)
        self.assertEqual(set(a["rooms"]), {"classroom-01", "computerlab-01"})
        for room in a["rooms"]:
            self.assertEqual(a["rooms"][room]["record"]["ventilation_pct"], 60)
            self.assertEqual(b["rooms"][room]["record"]["co2_ppm"], a["rooms"][room]["next_state"]["co2_ppm"])
            self.assertEqual(b["rooms"][room]["record"]["previous_ventilation_pct"], 60)
        self.assertEqual(b["minute"], 1)
        self.assertEqual(b["simulated_at"], "2026-11-27T00:00:50Z")
    def test_duplicate_and_stale(self):
        self.emit()
        self.assertEqual(self.emit(1)["result"], "duplicate_or_stale")
        self.emit(20)
        self.assertEqual(self.emit(10)["result"], "duplicate_or_stale")
        self.assertEqual(len(self.s3.data), 2)
    def test_scheduled_time_retry(self):
        event = {"mode": "live", "scheduled_time": "2026-11-26T23:59:00Z"}
        self.emit(event=event)
        self.assertEqual(self.emit(70, event=event)["result"], "duplicate_or_stale")
    def test_reader_types_and_room_isolation(self):
        a = self.emit()
        r = self.request(entityId="computerlab-01", selectedProperties=["occupancy", "co2_ppm", "status", "status_code"])
        expected = a["rooms"]["computerlab-01"]["record"]
        for field, key in zip(r["propertyValues"], ["integerValue","doubleValue","stringValue","integerValue"]):
            ref = field["entityPropertyReference"]
            self.assertEqual(ref["entityId"], "computerlab-01")
            self.assertEqual(field["values"][0]["value"][key], expected[ref["propertyName"]])
    def test_pagination_across_midnight(self):
        for seconds in (0, 10, 20, 30, 40):
            self.emit(seconds)
        for order in ("ASCENDING", "DESCENDING"):
            result, times = self.request(maxResults=2, orderByTime=order), []
            while True:
                times += [v["time"] for v in result["propertyValues"][0]["values"]]
                if "nextToken" not in result:
                    break
                result = self.request(maxResults=2, orderByTime=order, nextToken=result["nextToken"])
            self.assertEqual(len(set(times)), 5)
            self.assertEqual(times, sorted(times, reverse=order=="DESCENDING"))
    def test_unknown_and_empty(self):
        self.assertEqual(self.request(entityId="unknown"), {"propertyValues":[]})
        self.assertEqual(self.request()["propertyValues"][0]["values"], [])
        with self.assertRaises(ValueError):
            self.request(selectedProperties=["unknown"])


if __name__ == "__main__":
    unittest.main()
