import pandas as pd
import requests
import json
import os

PARQUET_PATH = "data/stage/videogames.parquet"
PINOT_CONTROLLER = "http://localhost:9000"
SEGMENT_DIR = "data/stage/segments"

def load():
    print("Leyendo Parquet...")
    df = pd.read_parquet(PARQUET_PATH)
    df = df.fillna("")
    print(f"📊 Registros: {df.shape}")

    # Convertir released a timestamp en milisegundos
    print("Transformando fechas...")
    # El formato es DD-MM-YYYY
    df["released_ts"] = pd.to_datetime(df["released"], format="%d-%m-%Y", errors="coerce")
    # Fallback para registros sin fecha válida: usar 2000-01-01
    default_ts = int(pd.Timestamp("2000-01-01").timestamp()) * 1000
    df["released_ts"] = df["released_ts"].apply(
        lambda x: int(x.timestamp() * 1000) if pd.notna(x) else default_ts
    )

    # Limpiar tipos
    for col in ["metacritic", "rating"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)

    for col in ["achievements", "ratings_count", "suggestions_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in ["id", "slug", "name", "released", "updated",
                "website", "image", "about", "esrb_rating",
                "platforms", "developers", "genres", "publishers"]:
        df[col] = df[col].astype(str).str[:2000]

    df["tba"] = df["tba"].astype(str).str.upper().map({"TRUE": True, "FALSE": False}).fillna(False)

    # Guardar en JSON por lotes para enviar a Pinot
    os.makedirs(SEGMENT_DIR, exist_ok=True)
    BATCH = 10000
    total = len(df)
    batches = (total // BATCH) + 1

    print(f"📦 Enviando {total} registros en {batches} lotes...")

    for i in range(batches):
        start = i * BATCH
        end = min(start + BATCH, total)
        if start >= total:
            break

        chunk = df.iloc[start:end]
        batch_file = os.path.join(SEGMENT_DIR, f"batch_{i}.json")

        records = chunk.to_dict(orient="records")
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, default=str)

        print(f"  ✅ Lote {i+1}/{batches} guardado ({start}-{end})")

    print(f"\n✅ Archivos JSON listos en: {SEGMENT_DIR}")
    print("Ahora ejecuta el script 04_ingest_pinot.py para ingesta final")

if __name__ == "__main__":
    load()