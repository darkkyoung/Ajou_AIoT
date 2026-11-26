"""Shared S3 journal and TwinMaker schema (standard library only)."""
import json
from datetime import datetime, timezone

PREFIX = "sensor-data/ticks/"
ROOM_IDS = ("classroom-01", "computerlab-01")
COMPONENT = "air_quality"
FIELDS = {
    "co2_ppm": ("DOUBLE", "doubleValue", float),
    "occupancy": ("INTEGER", "integerValue", int),
    "predicted_co2_5min_ppm": ("DOUBLE", "doubleValue", float),
    "ventilation_pct": ("INTEGER", "integerValue", int),
    "status": ("STRING", "stringValue", str),
    "status_code": ("INTEGER", "integerValue", int),
    "previous_ventilation_pct": ("INTEGER", "integerValue", int),
    "delta_co2_ppm": ("DOUBLE", "doubleValue", float),
}
KEY_FORMAT = "%Y%m%dT%H%M%SZ"


def utc(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


def key_for(value):
    return PREFIX + value.strftime(KEY_FORMAT) + ".json"


def key_time(key):
    try:
        return datetime.strptime(key[len(PREFIX):-5], KEY_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def keys(s3, bucket, prefix=PREFIX):
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.startswith(PREFIX) and key.endswith(".json") and key_time(key) is not None:
                yield key


def get_json(s3, bucket, key):
    return json.loads(s3.get_object(Bucket=bucket, Key=key)["Body"].read())


def error_code(exc):
    return str(getattr(exc, "response", {}).get("Error", {}).get("Code", ""))
