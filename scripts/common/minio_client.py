"""Client MinIO partagé — conventions de nommage des objets bronze/silver."""
import io
import json
import os

import boto3
from botocore.client import Config


def get_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def bronze_key(execution_date: str, devise: str) -> str:
    # Convention : exchange_rates/dt=YYYY-MM-DD/devise=XXX/raw.json
    return f"exchange_rates/dt={execution_date}/devise={devise}/raw.json"


def silver_key(execution_date: str, devise: str) -> str:
    return f"exchange_rates/dt={execution_date}/devise={devise}/clean.json"


def quarantine_key(execution_date: str, devise: str) -> str:
    return f"exchange_rates/dt={execution_date}/devise={devise}/quarantine.json"


def put_json(client, bucket: str, key: str, data: dict):
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    client.put_object(Bucket=bucket, Key=key, Body=io.BytesIO(body), ContentType="application/json")


def get_json(client, bucket: str, key: str) -> dict:
    resp = client.get_object(Bucket=bucket, Key=key)
    return json.loads(resp["Body"].read().decode("utf-8"))
