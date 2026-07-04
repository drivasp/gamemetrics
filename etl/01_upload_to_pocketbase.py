from pocketbase import PocketBase
import pandas as pd
import time

# Configuración
PB_URL = "http://127.0.0.1:8090"
PB_EMAIL = "drivasp@uteq.edu.ec"
PB_PASSWORD = "Dayver.1974"
CSV_PATH = "data/stage/videogames.csv"
COLLECTION = "
"
BATCH_SIZE = 50

def safe_int(val):
    try:
        if val == "" or val is None:
            return 0
        return int(float(str(val)))
    except:
        return 0

def safe_float(val):
    try:
        if val == "" or val is None:
            return 0.0
        return float(str(val))
    except:
        return 0.0

def upload():
    print("Conectando a Pocketbase...")
    client = PocketBase(PB_URL)
    client.collection("_superusers").auth_with_password(PB_EMAIL, PB_PASSWORD)
    print("✅ Conectado")

    print("Leyendo CSV...")
    df = pd.read_csv(CSV_PATH, sep=",")
    df = df.where(pd.notnull(df), "")
    total = len(df)
    print(f"📊 Total registros: {total}")

    cargados = 0
    errores = 0

    for i, row in df.iterrows():
        try:
            data = {
                "slug":             str(row.get("slug", "")),
                "name":             str(row.get("name", "")),
                "metacritic":       safe_float(row.get("metacritic")),
                "released":         str(row.get("released", "")),
                "tba":              str(row.get("tba", "")).upper() == "TRUE",
                "updated":          str(row.get("updated", "")),
                "website":          str(row.get("website", "")),
                "rating":           safe_float(row.get("rating")),
                "achievements":     safe_int(row.get("achievements")),
                "ratings_count":    safe_int(row.get("ratings_count")),
                "suggestions_count":safe_int(row.get("suggestions_count")),
                "platforms":        str(row.get("platforms", "")),
                "developers":       str(row.get("developers", "")),
                "genres":           str(row.get("genres", "")),
                "publishers":       str(row.get("publishers", "")),
                "esrb_rating":      str(row.get("esrb_rating", "")),
                "image":            str(row.get("image", "")),
                "about":            str(row.get("about", ""))[:2000],
            }
            client.collection(COLLECTION).create(data)
            cargados += 1

            if cargados % BATCH_SIZE == 0:
                print(f"  ⏳ Cargados: {cargados}/{total}")
                time.sleep(0.3)

        except Exception as e:
            errores += 1
            print(f"  ❌ Error en fila {i}: {e}")

    print(f"\n✅ Carga completa: {cargados} registros")
    print(f"❌ Errores: {errores}")

if __name__ == "__main__":
    upload()