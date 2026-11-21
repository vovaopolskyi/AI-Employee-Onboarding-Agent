"""Append-only completed-exam storage for the single-user cloud demo."""

import hashlib
import json
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

PREFIX = "progress/exams/"


@lru_cache(maxsize=1)
def client():
    return boto3.client("s3")


def save_record(bucket: str, session_id: str, record: dict) -> dict:
    key = PREFIX + hashlib.sha256(session_id.encode("utf-8")).hexdigest() + ".json"
    try:
        client().put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(record, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
            IfNoneMatch="*",
        )
    except ClientError as exc:
        # S3's conditional-write error is not a modeled boto3 exception.
        if exc.response.get("Error", {}).get("Code") == "PreconditionFailed":
            return {"saved": False, "reason": "already_exists"}
        raise
    return {"saved": True, "session_id": session_id}


def load_records(bucket: str) -> list[dict]:
    s3 = client()
    records = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX):
        for item in page.get("Contents", []):
            response = s3.get_object(Bucket=bucket, Key=item["Key"])
            with response["Body"] as body:
                record = json.loads(body.read())
            if not isinstance(record, dict) or "session_id" not in record:
                raise ValueError("Invalid S3 exam record")
            records.append(record)
    return records
