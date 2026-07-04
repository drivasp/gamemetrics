"""
Crea la colección 'datasetVideogames' en PocketBase si no existe.
Compatible con PocketBase v0.23+
Ejecutar ANTES de 01_upload_to_pocketbase.py
"""
import requests
import json

PB_URL = "http://127.0.0.1:8090"
PB_EMAIL = "drivasp@uteq.edu.ec"
PB_PASSWORD = "Dayver.1974"
COLLECTION = "datasetVideogames"

def auth():
    r = requests.post(f"{PB_URL}/api/collections/_superusers/auth-with-password", json={
        "identity": PB_EMAIL,
        "password": PB_PASSWORD,
    })
    r.raise_for_status()
    return r.json()["token"]

def delete_collection(token):
    """Borrar la colección si existe (para recrearla con campos correctos)."""
    r = requests.delete(f"{PB_URL}/api/collections/{COLLECTION}", headers={
        "Authorization": f"Bearer {token}"
    })
    if r.status_code in (200, 204):
        print(f"🗑️  Colección '{COLLECTION}' eliminada")
    elif r.status_code == 404:
        print(f"ℹ️  Colección '{COLLECTION}' no existía")
    else:
        print(f"⚠️  Status {r.status_code}: {r.text[:200]}")

def create_collection(token):
    """Crear la colección con campos usando formato fields (PB v0.23+)."""
    fields = [
        {"name": "slug",              "type": "text", "required": False},
        {"name": "name",              "type": "text", "required": False},
        {"name": "metacritic",        "type": "number", "required": False},
        {"name": "released",          "type": "text", "required": False},
        {"name": "tba",               "type": "bool", "required": False},
        {"name": "updated",           "type": "text", "required": False},
        {"name": "website",           "type": "text", "required": False},
        {"name": "rating",            "type": "number", "required": False},
        {"name": "achievements",      "type": "number", "required": False},
        {"name": "ratings_count",     "type": "number", "required": False},
        {"name": "suggestions_count", "type": "number", "required": False},
        {"name": "platforms",         "type": "text", "required": False},
        {"name": "developers",        "type": "text", "required": False},
        {"name": "genres",            "type": "text", "required": False},
        {"name": "publishers",        "type": "text", "required": False},
        {"name": "esrb_rating",       "type": "text", "required": False},
        {"name": "image",             "type": "text", "required": False},
        {"name": "about",             "type": "text", "required": False},
    ]

    payload = {
        "name": COLLECTION,
        "type": "base",
        "fields": fields,
        "listRule": "",
        "viewRule": "",
        "createRule": "",
        "updateRule": "",
        "deleteRule": "",
    }

    r = requests.post(f"{PB_URL}/api/collections", json=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })

    if r.status_code in (200, 201):
        print(f"✅ Colección '{COLLECTION}' creada con {len(fields)} campos")
    else:
        print(f"❌ Error {r.status_code}: {r.text[:500]}")

if __name__ == "__main__":
    print("Autenticando...")
    token = auth()
    print("✅ Autenticado")

    print("Eliminando colección anterior (si existe)...")
    delete_collection(token)

    print(f"Creando colección '{COLLECTION}' con campos...")
    create_collection(token)
