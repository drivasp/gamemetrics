"""
GameMetrics S.A. - Creacion de las 10 tablas del modelo de empresa en PocketBase.
Empresa dedicada al analisis y distribucion digital de videojuegos.
Este script es repetible: elimina y recrea las colecciones cada vez.
"""
import os
import requests

PB_URL      = os.getenv("PB_URL",      "http://127.0.0.1:8090")
PB_EMAIL    = os.getenv("PB_EMAIL",    "drivasp@uteq.edu.ec")
PB_PASSWORD = os.getenv("PB_PASSWORD", "Dayver.1974")

COLECCIONES = [
    "plataformas",
    "generos",
    "clasificaciones_esrb",
    "desarrolladores",
    "publicadores",
    "empleados",
    "contratos",
    "catalogo_distribucion",
    "campanas_marketing",
    "evaluaciones_analiticas",
]

SCHEMAS = {
    "plataformas": [
        {"name": "nombre",           "type": "text",   "required": True},
        {"name": "fabricante",       "type": "text",   "required": False},
        {"name": "tipo",             "type": "text",   "required": False},  # consola, PC, mobile, handheld, arcade
        {"name": "anno_lanzamiento", "type": "number", "required": False},
        {"name": "activa",           "type": "bool",   "required": False},
    ],
    "generos": [
        {"name": "nombre",       "type": "text",   "required": True},
        {"name": "descripcion",  "type": "text",   "required": False},
        {"name": "popularidad",  "type": "number", "required": False},  # conteo de juegos en ese genero
    ],
    "clasificaciones_esrb": [
        {"name": "codigo",       "type": "text",   "required": True},
        {"name": "nombre",       "type": "text",   "required": False},
        {"name": "descripcion",  "type": "text",   "required": False},
        {"name": "edad_minima",  "type": "number", "required": False},
    ],
    "desarrolladores": [
        {"name": "nombre",      "type": "text", "required": True},
        {"name": "pais",        "type": "text", "required": False},
        {"name": "tipo",        "type": "text", "required": False},  # indie, AAA, mid-size
        {"name": "sitio_web",   "type": "text", "required": False},
        {"name": "activo",      "type": "bool", "required": False},
    ],
    "publicadores": [
        {"name": "nombre",    "type": "text", "required": True},
        {"name": "pais",      "type": "text", "required": False},
        {"name": "tipo",      "type": "text", "required": False},  # indie, AAA, mid-size
        {"name": "sitio_web", "type": "text", "required": False},
        {"name": "activo",    "type": "bool", "required": False},
    ],
    "empleados": [
        {"name": "nombre",        "type": "text",   "required": True},
        {"name": "apellido",      "type": "text",   "required": True},
        {"name": "cargo",         "type": "text",   "required": False},
        {"name": "departamento",  "type": "text",   "required": False},
        {"name": "email",         "type": "email",  "required": False},
        {"name": "fecha_ingreso", "type": "text",   "required": False},
        {"name": "salario",       "type": "number", "required": False},
    ],
    "contratos": [
        {"name": "publicador_nombre", "type": "text",   "required": False},
        {"name": "tipo_contrato",     "type": "text",   "required": False},  # exclusividad, licencia, distribucion
        {"name": "fecha_inicio",      "type": "text",   "required": False},
        {"name": "fecha_fin",         "type": "text",   "required": False},
        {"name": "valor",             "type": "number", "required": False},
        {"name": "estado",            "type": "text",   "required": False},  # activo, vencido, cancelado
        {"name": "descripcion",       "type": "text",   "required": False},
    ],
    "catalogo_distribucion": [
        {"name": "juego_nombre",       "type": "text",   "required": True},
        {"name": "juego_id",           "type": "text",   "required": False},  # referencia a datasetVideogames
        {"name": "plataforma_nombre",  "type": "text",   "required": False},
        {"name": "precio",             "type": "number", "required": False},
        {"name": "fecha_incorporacion","type": "text",   "required": False},
        {"name": "region",             "type": "text",   "required": False},  # NA, EU, LATAM, Global
        {"name": "estado",             "type": "text",   "required": False},  # activo, descontinuado, preventa
    ],
    "campanas_marketing": [
        {"name": "nombre",        "type": "text",   "required": True},
        {"name": "juego_nombre",  "type": "text",   "required": False},
        {"name": "genero_nombre", "type": "text",   "required": False},
        {"name": "presupuesto",   "type": "number", "required": False},
        {"name": "gasto_real",    "type": "number", "required": False},
        {"name": "fecha_inicio",  "type": "text",   "required": False},
        {"name": "fecha_fin",     "type": "text",   "required": False},
        {"name": "canal",         "type": "text",   "required": False},  # redes, TV, influencers, email
        {"name": "estado",        "type": "text",   "required": False},  # planificada, activa, finalizada
    ],
    "evaluaciones_analiticas": [
        {"name": "juego_nombre",         "type": "text",   "required": True},
        {"name": "empleado_nombre",      "type": "text",   "required": False},
        {"name": "puntuacion_comercial", "type": "number", "required": False},  # 1-10
        {"name": "puntuacion_tecnica",   "type": "number", "required": False},  # 1-10
        {"name": "recomendacion",        "type": "text",   "required": False},  # adquirir, rechazar, revisar
        {"name": "fecha_evaluacion",     "type": "text",   "required": False},
        {"name": "notas",                "type": "text",   "required": False},
    ],
}


def auth():
    r = requests.post(f"{PB_URL}/api/collections/_superusers/auth-with-password", json={
        "identity": PB_EMAIL,
        "password": PB_PASSWORD,
    })
    r.raise_for_status()
    print("Autenticado correctamente")
    return r.json()["token"]


def delete_collection(token, nombre):
    r = requests.delete(
        f"{PB_URL}/api/collections/{nombre}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if r.status_code in (200, 204):
        print(f"  Eliminada: {nombre}")
    elif r.status_code == 404:
        print(f"  No existia: {nombre}")
    else:
        print(f"  Warning al eliminar {nombre}: {r.status_code}")


def create_collection(token, nombre, fields):
    payload = {
        "name": nombre,
        "type": "base",
        "fields": fields,
        "listRule": "",
        "viewRule": "",
        "createRule": "",
        "updateRule": "",
        "deleteRule": "",
    }
    r = requests.post(
        f"{PB_URL}/api/collections",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    if r.status_code in (200, 201):
        print(f"  Creada: {nombre} ({len(fields)} campos)")
    else:
        print(f"  Error al crear {nombre}: {r.status_code} - {r.text[:200]}")


if __name__ == "__main__":
    print("=" * 55)
    print("  GameMetrics S.A. - Creacion de tablas empresa")
    print("=" * 55)

    token = auth()

    print("\n--- Eliminando colecciones anteriores ---")
    for nombre in reversed(COLECCIONES):
        delete_collection(token, nombre)

    print("\n--- Creando colecciones ---")
    for nombre in COLECCIONES:
        create_collection(token, nombre, SCHEMAS[nombre])

    print("\nListo: 10 tablas creadas en PocketBase.")
    print("Ejecuta 06_populate_empresa_tables.py para poblarlas con datos.")
