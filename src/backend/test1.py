from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pymysql
import redis
import yaml
from cryptography.fernet import Fernet, InvalidToken
from minio import Minio


FERNET_KEY = "TI31VYJ-ldAq-FXo5QNPKV_lqGTFfp-MIdbK2Hm5F1E="
CONFIG_PATH = Path(__file__).resolve().parent / "bisheng" / "config.yaml"


def env_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> str:
    value = loader.construct_scalar(node)
    env_name = value.strip("${} ")
    env_value = os.getenv(env_name)
    if env_value is None:
        raise RuntimeError(f"环境变量 {env_name} 未设置")
    return env_value


def load_config() -> dict[str, Any]:
    yaml.SafeLoader.add_constructor("!env", env_constructor)
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def decrypt_if_needed(password: str | None) -> str:
    if not password:
        return ""

    try:
        return Fernet(FERNET_KEY).decrypt(password.encode()).decode()
    except (InvalidToken, ValueError):
        return password


def mask(value: str | None) -> str:
    if not value:
        return ""
    return "*" * min(len(value), 8)


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "https"}
    return bool(value)


def test_mysql(database_url: str) -> bool:
    parsed = urlparse(database_url)
    password = decrypt_if_needed(parsed.password)
    database = parsed.path.lstrip("/")
    port = parsed.port or 3306

    print(f"MySQL: {parsed.username}@{parsed.hostname}:{port}/{database} password={mask(password)}")
    try:
        conn = pymysql.connect(
            host=parsed.hostname,
            port=port,
            user=parsed.username,
            password=password,
            database=database,
            charset="utf8mb4",
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        conn.close()
    except Exception as exc:
        print(f"  FAIL: {type(exc).__name__}: {exc}")
        return False

    print(f"  OK: SELECT 1 -> {result[0]}")
    return True


def test_redis(name: str, redis_url: str) -> bool:
    parsed = urlparse(redis_url)
    print(f"{name}: {parsed.hostname}:{parsed.port or 6379}/{parsed.path.lstrip('/') or '0'}")
    try:
        client = redis.Redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
        pong = client.ping()
    except Exception as exc:
        print(f"  FAIL: {type(exc).__name__}: {exc}")
        return False

    print(f"  OK: ping -> {pong}")
    return True


def test_minio(minio_config: dict[str, Any]) -> bool:
    endpoint = str(minio_config["endpoint"])
    access_key = str(minio_config["access_key"])
    secret_key = str(minio_config["secret_key"])
    secure = as_bool(minio_config.get("schema", False))
    public_bucket = str(minio_config.get("public_bucket", "bisheng"))
    tmp_bucket = str(minio_config.get("tmp_bucket", "tmp-dir"))

    print(f"MinIO: {'https' if secure else 'http'}://{endpoint} access_key={access_key}")
    try:
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            cert_check=as_bool(minio_config.get("cert_check", False)),
        )
        buckets = {bucket.name for bucket in client.list_buckets()}
    except Exception as exc:
        print(f"  FAIL: {type(exc).__name__}: {exc}")
        return False

    print("  OK: authenticated and listed buckets")
    for bucket in (public_bucket, tmp_bucket):
        state = "exists" if bucket in buckets else "missing"
        print(f"  bucket {bucket}: {state}")
    return True


def main() -> int:
    print(f"Config: {CONFIG_PATH}")
    config = load_config()

    checks = [
        test_mysql(config["database_url"]),
        test_redis("Redis", config["redis_url"]),
        test_redis("Celery Redis", config["celery_redis_url"]),
        test_minio(config["object_storage"]["minio"]),
    ]

    if all(checks):
        print("Result: all connectivity checks passed")
        return 0

    print("Result: one or more connectivity checks failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
