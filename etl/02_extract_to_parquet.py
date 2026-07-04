import requests
import pandas as pd
import os

# Configuración
PB_URL = "http://127.0.0.1:8090"
PB_EMAIL = "drivasp@uteq.edu.ec"
PB_PASSWORD = "Dayver.1974"
COLLECTION = "datasetVideogames"
OUTPUT_PATH = "data/stage/videogames.parquet"
PAGE_SIZE = 500

def extract():
    print("Autenticando en PocketBase...")
    auth_resp = requests.post(f"{PB_URL}/api/collections/_superusers/auth-with-password", json={
        "identity": PB_EMAIL,
        "password": PB_PASSWORD,
    })
    auth_resp.raise_for_status()
    token = auth_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Conectado")

    todos = []
    page = 1

    print("Extrayendo registros...")
    while True:
        resp = requests.get(
            f"{PB_URL}/api/collections/{COLLECTION}/records",
            params={"page": page, "perPage": PAGE_SIZE},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            todos.append({
                "id":                item.get("id", ""),
                "slug":              item.get("slug", ""),
                "name":              item.get("name", ""),
                "metacritic":        item.get("metacritic", 0),
                "released":          item.get("released", ""),
                "tba":               item.get("tba", False),
                "updated":           item.get("updated", ""),
                "website":           item.get("website", ""),
                "rating":            item.get("rating", 0),
                "achievements":      item.get("achievements", 0),
                "ratings_count":     item.get("ratings_count", 0),
                "suggestions_count": item.get("suggestions_count", 0),
                "platforms":         item.get("platforms", ""),
                "developers":        item.get("developers", ""),
                "genres":            item.get("genres", ""),
                "publishers":        item.get("publishers", ""),
                "esrb_rating":       item.get("esrb_rating", ""),
                "image":             item.get("image", ""),
                "about":             item.get("about", ""),
            })

        total_items = data.get("totalItems", 0)
        total_pages = data.get("totalPages", 0)
        print(f"  ⏳ Extraídos: {len(todos)} / {total_items}")

        if page >= total_pages:
            break
        page += 1

    print(f"\n📦 Convirtiendo {len(todos)} registros a Parquet...")
    df = pd.DataFrame(todos)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"✅ Parquet guardado en: {OUTPUT_PATH}")
    print(f"📊 Shape: {df.shape}")

if __name__ == "__main__":
    extract()
