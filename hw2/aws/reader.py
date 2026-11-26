"""TwinMaker DataReaderByEntity over the immutable two-room S3 journal."""
import base64
import json
import os
from datetime import datetime, timedelta, timezone

from common import COMPONENT, FIELDS, PREFIX, ROOM_IDS, get_json, iso, key_time, keys, utc


def read(s3, bucket, event, now):
    room = event.get("entityId")
    if room not in ROOM_IDS or event.get("componentName") != COMPONENT:
        return {"propertyValues": []}
    names = event.get("selectedProperties") or list(FIELDS)
    if any(name not in FIELDS for name in names):
        raise ValueError("Unknown property")
    if event.get("propertyFilters"):
        raise ValueError("Property filters not supported")
    interpolation = event.get("interpolation") or {}
    if interpolation.get("interpolationType") not in (None, "NONE"):
        raise ValueError("Interpolation not supported")
    end_raw = event.get("endTime", event.get("endDateTime"))
    start_raw = event.get("startTime", event.get("startDateTime"))
    end = utc(end_raw) if end_raw is not None else now
    start = utc(start_raw) if start_raw is not None else end - timedelta(minutes=30)
    order = event.get("orderByTime", "DESCENDING")
    if order not in ("ASCENDING", "DESCENDING"):
        raise ValueError("Unknown order")
    if event.get("nextToken"):
        token = json.loads(base64.urlsafe_b64decode(event["nextToken"]).decode())
        if token["room"] != room or token["names"] != names or token["order"] != order:
            raise ValueError("Token query mismatch")
        if (start_raw is not None and start != utc(token["start"])) or (
                end_raw is not None and end != utc(token["end"])):
            raise ValueError("Token range mismatch")
        start, end = utc(token["start"]), utc(token["end"])
        cursor = token["cursor"]
    else:
        cursor = None
    if start > end or end - start > timedelta(days=7):
        raise ValueError("Query range must be 0-7 days")
    limit = max(1, min(250, int(event.get("maxResults") or 25)))
    candidates = []
    day = start.date()
    while day <= end.date():
        for key in keys(s3, bucket, PREFIX + day.strftime("%Y%m%d")):
            if start <= key_time(key) <= end and (cursor is None or (
                    key < cursor if order == "DESCENDING" else key > cursor)):
                candidates.append(key)
        day += timedelta(days=1)
    candidates.sort(reverse=order == "DESCENDING")
    page = candidates[:limit]
    ticks = [get_json(s3, bucket, key) for key in page]
    result = {"propertyValues": []}
    for name in names:
        _, value_key, convert = FIELDS[name]
        result["propertyValues"].append({
            "entityPropertyReference": {"entityId": room, "componentName": COMPONENT, "propertyName": name},
            "values": [{"time": tick["timestamp"], "value": {value_key: convert(tick["rooms"][room]["record"][name])}}
                       for tick in ticks]})
    if len(candidates) > limit:
        token = {"room": room, "names": names, "order": order,
                 "start": iso(start), "end": iso(end), "cursor": page[-1]}
        result["nextToken"] = base64.urlsafe_b64encode(json.dumps(token).encode()).decode()
    return result


def lambda_handler(event, context):
    import boto3
    return read(boto3.client("s3"), os.environ["BUCKET_NAME"], event, datetime.now(timezone.utc))
