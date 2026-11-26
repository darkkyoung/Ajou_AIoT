"""One serialized, idempotent tick for both rooms; package at ZIP root."""
import json
import os
import random
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from common import PREFIX, ROOM_IDS, error_code, get_json, iso, key_for, keys, utc
from control import initial_state, step_room
from inference import load_model
from simulation import get_occupancy

STATUS_CODES = {"normal": 0, "warning": 1, "high": 2}


def tick(s3, bucket, model, event, now):
    mode = event.get("mode", "live")
    if mode not in ("live", "demo"):
        raise ValueError("mode must be live or demo")
    interval = 60 if mode == "live" else 10
    requested = utc(event["scheduled_time"]) if event.get("scheduled_time") else now
    if requested > now + timedelta(seconds=5):
        raise ValueError("Future scheduled time")
    slot = datetime.fromtimestamp(int(requested.timestamp()) // interval * interval, timezone.utc)
    key = key_for(slot)
    # Single writer required: Lambda reserved concurrency=1; no other writers.
    latest_key = max(keys(s3, bucket), default=None)
    if latest_key is not None and key <= latest_key:
        return {"result": "duplicate_or_stale", "key": key, "latest_key": latest_key}
    previous = get_json(s3, bucket, latest_key) if latest_key else None
    if previous and previous["schema_version"] != 1:
        raise ValueError("Unknown journal schema")
    minute = previous["minute"] + 1 if previous else 0
    simulated = utc(previous["simulated_at"]) + timedelta(minutes=1) if previous else slot
    rooms = {}
    for i, room in enumerate(ROOM_IDS):
        state = previous["rooms"][room]["next_state"] if previous else initial_state(
            round(random.Random(300000 + i).uniform(450, 800), 2))
        # Independent deterministic inputs for a retry; no global RNG state.
        rng = random.Random(400000 + minute * 10 + i)
        scenario, occupancy = get_occupancy(minute, room, rng)
        next_state, record = step_room(room, state, occupancy, rng.gauss(0, 3), model)
        record.update(status_code=STATUS_CODES[record["status"]], scenario=scenario)
        rooms[room] = {"record": record, "next_state": next_state}
    data = {"schema_version": 1, "timestamp": iso(slot), "recorded_at": iso(now),
            "simulated_at": iso(simulated), "minute": minute, "clock_mode": mode,
            "model": model["kind"], "rooms": rooms}
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(data, allow_nan=False).encode(),
                      ContentType="application/json", IfNoneMatch="*")
    except Exception as exc:
        if error_code(exc) in ("412", "PreconditionFailed"):
            return {"result": "duplicate_or_stale", "key": key}
        raise
    return {"result": "created", "key": key, **data}


@lru_cache(maxsize=1)
def model():
    return load_model(Path(__file__).with_name("selected_model.json"))


def lambda_handler(event, context):
    import boto3
    result = tick(boto3.client("s3"), os.environ["BUCKET_NAME"], model(),
                  event or {}, datetime.now(timezone.utc))
    print(json.dumps(result, allow_nan=False))
    return result
