"""Object storage for game builds — MinIO (S3) with local filesystem fallback."""
from __future__ import annotations

import hashlib
import io
import os
import zipfile
from pathlib import Path

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "gamemetrics")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "gamemetrics_secret")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "gamemetrics-builds")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"}
LOCAL_BUILD_DIR = Path(os.getenv("LOCAL_BUILD_DIR", "/app/static/builds"))

_client = None
_bucket_ready = False


def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        from minio import Minio
        _client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        return _client
    except Exception as exc:
        print(f"[storage] MinIO client unavailable: {exc}")
        _client = False
        return None


def _ensure_bucket(client) -> bool:
    global _bucket_ready
    if _bucket_ready:
        return True
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
        _bucket_ready = True
        return True
    except Exception as exc:
        print(f"[storage] bucket error: {exc}")
        return False


def build_game_package(product_id: str, game_name: str, version: str = "1.0.0") -> bytes:
    """Create a small playable HTML demo ZIP for the product."""
    title = (game_name or product_id).replace("<", "").replace(">", "")[:80]
    safe_id = product_id[:24]
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <title>{title} — GameMetrics</title>
  <style>
    body {{ margin:0; font-family:Segoe UI,Arial,sans-serif; background:#1b2838; color:#c7d5e0;
           display:flex; min-height:100vh; align-items:center; justify-content:center; }}
    .card {{ background:#2a475e; padding:32px 40px; border-radius:8px; text-align:center;
             box-shadow:0 8px 32px rgba(0,0,0,.4); max-width:480px; }}
    h1 {{ color:#66c0f4; margin:0 0 8px; font-size:1.4rem; }}
    .score {{ font-size:3rem; color:#beee11; margin:16px 0; }}
    button {{ background:#66c0f4; color:#1b2838; border:0; padding:12px 24px; border-radius:4px;
              font-weight:700; cursor:pointer; }}
    button:hover {{ filter:brightness(1.1); }}
    .meta {{ opacity:.7; font-size:.85rem; margin-top:16px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{title}</h1>
    <p>Demo jugable local · GameMetrics Launcher</p>
    <div class="score" id="score">0</div>
    <button id="btn" type="button">+1 puntos</button>
    <p class="meta">product={safe_id} · v{version}</p>
  </div>
  <script>
    let n = 0;
    document.getElementById('btn').onclick = () => {{
      n += 1;
      document.getElementById('score').textContent = String(n);
    }};
  </script>
</body>
</html>
"""
    readme = (
        f"GameMetrics Digital Delivery Package\n"
        f"Game: {title}\n"
        f"Product: {product_id}\n"
        f"Version: {version}\n"
        f"How to play: open index.html in your browser or via GameMetrics Desktop.\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html)
        zf.writestr("README.txt", readme)
        zf.writestr(
            "gamemetrics.json",
            f'{{"product_id":"{product_id}","version":"{version}","entry":"index.html"}}\n',
        )
    return buf.getvalue()


def put_object(key: str, data: bytes, content_type: str = "application/zip") -> str:
    """Upload bytes to MinIO or local disk. Returns storage URI."""
    client = _get_client()
    if client and _ensure_bucket(client):
        try:
            client.put_object(
                MINIO_BUCKET,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return f"s3://{MINIO_BUCKET}/{key}"
        except Exception as exc:
            print(f"[storage] MinIO put failed, falling back to local: {exc}")

    path = LOCAL_BUILD_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"file://{path.as_posix()}"


def get_object_bytes(key: str) -> bytes | None:
    client = _get_client()
    if client and _ensure_bucket(client):
        try:
            response = client.get_object(MINIO_BUCKET, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except Exception as exc:
            print(f"[storage] MinIO get failed: {exc}")

    path = LOCAL_BUILD_DIR / key
    if path.is_file():
        return path.read_bytes()
    return None


def object_exists(key: str) -> bool:
    client = _get_client()
    if client and _ensure_bucket(client):
        try:
            client.stat_object(MINIO_BUCKET, key)
            return True
        except Exception:
            pass
    return (LOCAL_BUILD_DIR / key).is_file()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Alias for generic blob upload (builds, cloud saves, etc.)."""
    return put_object(key, data, content_type=content_type)


def get_bytes(key: str) -> bytes | None:
    return get_object_bytes(key)


def delete_object(key: str) -> bool:
    client = _get_client()
    if client and _ensure_bucket(client):
        try:
            client.remove_object(MINIO_BUCKET, key)
        except Exception as exc:
            print(f"[storage] MinIO delete failed: {exc}")
    path = LOCAL_BUILD_DIR / key
    if path.is_file():
        path.unlink()
        return True
    return False


def ensure_package(product_id: str, game_name: str, version: str = "1.0.0") -> dict:
    """Ensure a real ZIP exists for this product; return path/size/checksum."""
    label = "".join(c if c.isalnum() or c in "-_" else "_" for c in (game_name or product_id))[:40]
    key = f"builds/{product_id}/{label}_{version}_win.zip"
    if not object_exists(key):
        data = build_game_package(product_id, game_name, version)
        put_object(key, data)
    else:
        data = get_object_bytes(key) or b""
    checksum = sha256_hex(data) if data else ""
    return {
        "file_path": key,
        "file_size_bytes": len(data),
        "checksum": checksum,
        "storage_key": key,
    }
