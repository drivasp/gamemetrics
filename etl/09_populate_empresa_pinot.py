"""
GameMetrics S.A. - Poblar las 10 tablas de empresa en Pinot via Kafka.
Envia registros iniciales a los topics de Kafka → emp_records en Pinot.
Este script es repetible: envia nuevos registros con nuevos IDs.
"""
import json
import os
import random
import time
import uuid
from collections import Counter

import pandas as pd
from kafka import KafkaProducer

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
random.seed(42)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_SERVERS],
    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    key_serializer=lambda k: k.encode("utf-8"),
)


def new_id() -> str:
    return uuid.uuid4().hex[:15]


def send(collection: str, data: dict):
    record_id = new_id()
    now_ms = int(time.time() * 1000)
    producer.send("emp_records", key=record_id, value={
        "record_id": record_id,
        "collection": collection,
        "data_json": json.dumps(data, default=str),
        "deleted": False,
        "created_at": now_ms,
    })


def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def load_dataset():
    df = pd.read_parquet(os.path.join(BASE_DIR, "data/stage/videogames.parquet"))
    return df.fillna("")


def extract_multivalue(df, col, min_len=2):
    counter = Counter()
    for v in df[col].dropna():
        for item in str(v).split("||"):
            item = item.strip()
            if len(item) >= min_len:
                counter[item] += 1
    return counter


# ── DATOS ──────────────────────────────────────────────────────────────────

PLATFORM_META = {
    "PC":               ("Varios / Valve",   "PC",       1970,  True),
    "macOS":            ("Apple",            "PC",       2001,  True),
    "Linux":            ("Open Source",      "PC",       1991,  True),
    "Android":          ("Google",           "mobile",   2008,  True),
    "iOS":              ("Apple",            "mobile",   2007,  True),
    "PlayStation 4":    ("Sony",             "consola",  2013,  True),
    "PlayStation 5":    ("Sony",             "consola",  2020,  True),
    "Xbox One":         ("Microsoft",        "consola",  2013,  True),
    "Nintendo Switch":  ("Nintendo",         "consola",  2017,  True),
    "PlayStation 3":    ("Sony",             "consola",  2006,  False),
    "Xbox 360":         ("Microsoft",        "consola",  2005,  False),
    "Wii":              ("Nintendo",         "consola",  2006,  False),
    "Nintendo 64":      ("Nintendo",         "consola",  1996,  False),
    "Game Boy Advance": ("Nintendo",         "handheld", 2001,  False),
    "Nintendo 3DS":     ("Nintendo",         "handheld", 2011,  True),
    "PSP":              ("Sony",             "handheld", 2004,  False),
    "PS Vita":          ("Sony",             "handheld", 2011,  False),
    "Genesis":          ("Sega",             "consola",  1988,  False),
    "Dreamcast":        ("Sega",             "consola",  1998,  False),
}

GENRE_DESC = {
    "Action":      "Juegos de accion rapida con combate y reflejos",
    "Adventure":   "Exploracion de mundos y narrativas profundas",
    "RPG":         "Juegos de rol con desarrollo de personaje y historia",
    "Shooter":     "Combate con armas de fuego en primera o tercera persona",
    "Strategy":    "Planificacion y toma de decisiones tacticamente",
    "Simulation":  "Recreacion realista de actividades o sistemas",
    "Sports":      "Competencias deportivas virtuales",
    "Puzzle":      "Retos mentales y resolucion de acertijos",
    "Platformer":  "Saltos y obstaculos en plataformas",
    "Racing":      "Competencias de velocidad en vehiculos",
    "Fighting":    "Combate cuerpo a cuerpo entre personajes",
    "Arcade":      "Juegos clasicos de maquinas recreativas",
    "Indie":       "Desarrollados por estudios independientes",
}

ESRB_DATA = [
    ("E",  "Everyone",       "Apto para todos los publicos",                0),
    ("E10","Everyone 10+",   "Apto para mayores de 10 anos",               10),
    ("T",  "Teen",           "Para adolescentes, puede incluir violencia",  13),
    ("M",  "Mature",         "Para adultos, incluye contenido intenso",     17),
    ("AO", "Adults Only",    "Solo para adultos mayores de 18",             18),
    ("RP", "Rating Pending", "Clasificacion pendiente de la ESRB",           0),
]

EMPLEADOS_DATA = [
    ("Carlos",    "Mendoza",   "Director de Analitica",         "Analitica",    "c.mendoza@gamemetrics.com",   "2019-03-01", 5800),
    ("Sofia",     "Herrera",   "Cientifica de Datos",           "Analitica",    "s.herrera@gamemetrics.com",   "2020-06-15", 4200),
    ("Luis",      "Paredes",   "Analista de Datos",             "Analitica",    "l.paredes@gamemetrics.com",   "2021-09-10", 3100),
    ("Ana",       "Rios",      "Analista de Datos",             "Analitica",    "a.rios@gamemetrics.com",      "2022-01-20", 3000),
    ("Diego",     "Vega",      "Gerente de Distribucion",       "Distribucion", "d.vega@gamemetrics.com",      "2018-11-05", 4800),
    ("Valentina", "Castro",    "Ejecutiva de Distribucion",     "Distribucion", "v.castro@gamemetrics.com",    "2021-04-12", 3300),
    ("Miguel",    "Torres",    "Director de Marketing",         "Marketing",    "m.torres@gamemetrics.com",    "2019-07-22", 5200),
    ("Camila",    "Ruiz",      "Especialista Marketing Digital","Marketing",    "c.ruiz@gamemetrics.com",      "2022-03-08", 3000),
    ("Andres",    "Mora",      "CTO",                           "Tecnologia",   "a.mora@gamemetrics.com",      "2017-05-30", 7500),
    ("Isabella",  "Jimenez",   "Desarrolladora Backend",        "Tecnologia",   "i.jimenez@gamemetrics.com",   "2020-10-19", 4100),
    ("Sebastian", "Gutierrez", "Desarrollador Frontend",        "Tecnologia",   "s.gutierrez@gamemetrics.com", "2021-02-14", 3900),
    ("Daniela",   "Flores",    "Administradora de Sistemas",    "Tecnologia",   "d.flores@gamemetrics.com",    "2022-07-01", 3500),
    ("Roberto",   "Vargas",    "Director Legal",                "Legal",        "r.vargas@gamemetrics.com",    "2018-09-15", 6000),
    ("Lucia",     "Medina",    "Asesora Legal",                 "Legal",        "l.medina@gamemetrics.com",    "2021-11-30", 4000),
    ("Fernando",  "Cruz",      "CFO",                           "Finanzas",     "f.cruz@gamemetrics.com",      "2017-01-10", 8000),
    ("Patricia",  "Reyes",     "Contadora Senior",              "Finanzas",     "p.reyes@gamemetrics.com",     "2019-08-20", 3800),
    ("Juan",      "Salazar",   "Analista Financiero",           "Finanzas",     "j.salazar@gamemetrics.com",   "2022-05-16", 2900),
    ("Monica",    "Perez",     "CEO",                           "Direccion",    "m.perez@gamemetrics.com",     "2015-01-01", 12000),
    ("Hector",    "Alvarado",  "Gerente de Contratos",          "Distribucion", "h.alvarado@gamemetrics.com",  "2020-03-25", 4500),
    ("Laura",     "Romero",    "Especialista en Contenido",     "Marketing",    "l.romero@gamemetrics.com",    "2023-01-09", 2800),
]

PAISES = ["USA", "Japon", "Reino Unido", "Canada", "Francia", "Alemania",
          "Polonia", "Suecia", "Espana", "Australia", "Korea del Sur", "Brasil"]
TIPOS  = ["indie", "indie", "indie", "mid-size", "mid-size", "AAA"]
TIPOS_CONTRATO = ["distribucion", "licencia", "exclusividad", "co-publicacion"]
ESTADOS = ["activo", "activo", "activo", "vencido", "cancelado"]
REGIONES = ["Global", "LATAM", "NA", "EU", "Asia"]
ESTADOS_CAT = ["activo", "activo", "activo", "descontinuado", "preventa"]
CANALES = ["redes sociales", "YouTube", "influencers", "email", "TV", "eventos gaming"]


# ── FUNCIONES ──────────────────────────────────────────────────────────────

def populate_plataformas():
    section("1. PLATAFORMAS")
    for nombre, (fab, tipo, anno, activa) in PLATFORM_META.items():
        send("plataformas", {"nombre": nombre, "fabricante": fab, "tipo": tipo,
                             "anno_lanzamiento": anno, "activa": activa})
    print(f"  Enviados: {len(PLATFORM_META)} plataformas")


def populate_generos(df):
    section("2. GENEROS")
    counter = extract_multivalue(df, "genres")
    count = 0
    for nombre, popularidad in sorted(counter.items(), key=lambda x: -x[1]):
        if len(nombre) < 3:
            continue
        send("generos", {"nombre": nombre,
                         "descripcion": GENRE_DESC.get(nombre, f"Genero de videojuegos: {nombre}"),
                         "popularidad": popularidad})
        count += 1
    print(f"  Enviados: {count} generos")


def populate_esrb():
    section("3. CLASIFICACIONES ESRB")
    for cod, nom, desc, edad in ESRB_DATA:
        send("clasificaciones_esrb", {"codigo": cod, "nombre": nom,
                                      "descripcion": desc, "edad_minima": edad})
    print(f"  Enviados: {len(ESRB_DATA)} clasificaciones")


def populate_desarrolladores(df):
    section("4. DESARROLLADORES (top 300)")
    counter = extract_multivalue(df, "developers")
    top = [(n, c) for n, c in counter.most_common(300) if len(n) > 3]
    for nombre, _ in top:
        send("desarrolladores", {"nombre": nombre, "pais": random.choice(PAISES),
                                  "tipo": random.choice(TIPOS), "sitio_web": "",
                                  "activo": random.random() > 0.1})
    print(f"  Enviados: {len(top)} desarrolladores")


def populate_publicadores(df):
    section("5. PUBLICADORES (top 200)")
    counter = extract_multivalue(df, "publishers")
    top = [(n, c) for n, c in counter.most_common(200) if len(n) > 3]
    for nombre, _ in top:
        send("publicadores", {"nombre": nombre, "pais": random.choice(PAISES),
                               "tipo": random.choice(TIPOS), "sitio_web": "",
                               "activo": random.random() > 0.05})
    print(f"  Enviados: {len(top)} publicadores")


def populate_empleados():
    section("6. EMPLEADOS")
    for n, a, c, dep, em, fi, sal in EMPLEADOS_DATA:
        send("empleados", {"nombre": n, "apellido": a, "cargo": c,
                            "departamento": dep, "email": em,
                            "fecha_ingreso": fi, "salario": sal})
    print(f"  Enviados: {len(EMPLEADOS_DATA)} empleados")


def populate_contratos(df):
    section("7. CONTRATOS")
    counter = extract_multivalue(df, "publishers")
    top_pubs = [n for n, _ in counter.most_common(20) if len(n) > 3][:15]
    anios = list(range(2018, 2025))
    for pub in top_pubs:
        inicio_y = random.choice(anios)
        fin_y = inicio_y + random.randint(1, 4)
        estado = "activo" if fin_y >= 2024 else random.choice(["vencido", "activo"])
        send("contratos", {
            "publicador_nombre": pub,
            "tipo_contrato": random.choice(TIPOS_CONTRATO),
            "fecha_inicio": f"{inicio_y}-{random.randint(1,12):02d}-01",
            "fecha_fin": f"{fin_y}-{random.randint(1,12):02d}-01",
            "valor": random.randint(50_000, 2_000_000),
            "estado": estado,
            "descripcion": f"Contrato con {pub}",
        })
    print(f"  Enviados: {len(top_pubs)} contratos")


def populate_catalogo(df):
    section("8. CATALOGO DE DISTRIBUCION (top 500)")
    top = (df[df["rating"].apply(pd.to_numeric, errors="coerce") > 0]
           .nlargest(500, "rating")[["id", "name", "platforms", "rating"]]
           .dropna(subset=["name"]))
    count = 0
    for _, row in top.iterrows():
        plats = [p.strip() for p in str(row["platforms"]).split("||") if len(p.strip()) > 2]
        send("catalogo_distribucion", {
            "juego_nombre": str(row["name"])[:200],
            "juego_id": str(row["id"]),
            "plataforma_nombre": plats[0] if plats else "PC",
            "precio": round(random.uniform(4.99, 59.99), 2),
            "fecha_incorporacion": f"{random.randint(2019,2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "region": random.choice(REGIONES),
            "estado": random.choice(ESTADOS_CAT),
        })
        count += 1
    print(f"  Enviados: {count} juegos en catalogo")


def populate_campanas(df):
    section("9. CAMPANAS DE MARKETING")
    top_games = (df[df["rating"].apply(pd.to_numeric, errors="coerce") > 0]
                 .nlargest(20, "rating")["name"].tolist())
    generos = list(extract_multivalue(df, "genres").keys())[:10]
    campanas = [
        "Lanzamiento Temporada Verano", "Campana Black Friday", "Rebrand GameMetrics",
        "Promo Indie Showcase", "Semana RPG", "Campana Nostalgia Retro",
        "GameMetrics Awards", "Promo Familia", "Campana Multiplayer",
        "Semana de Terror", "Promo Educativa", "Lanzamiento Navidad",
        "Campana PS5 Exclusives", "Semana de Estrategia", "Promo Switch Hits",
        "Campana Deportes Virtuales", "Festival Indie 2024", "Campana AAA Invierno",
        "Promo Simulacion", "Campana Ranking Global",
    ]
    for i, nombre in enumerate(campanas):
        presupuesto = random.randint(10_000, 500_000)
        send("campanas_marketing", {
            "nombre": nombre,
            "juego_nombre": top_games[i] if i < len(top_games) else top_games[0],
            "genero_nombre": generos[i % len(generos)],
            "presupuesto": presupuesto,
            "gasto_real": round(presupuesto * random.uniform(0.5, 1.1)),
            "fecha_inicio": f"{random.randint(2022,2024)}-{random.randint(1,12):02d}-01",
            "fecha_fin": f"{random.randint(2024,2025)}-{random.randint(1,12):02d}-01",
            "canal": random.choice(CANALES),
            "estado": random.choice(["planificada", "activa", "finalizada"]),
        })
    print(f"  Enviados: {len(campanas)} campanas")


def populate_evaluaciones(df):
    section("10. EVALUACIONES ANALITICAS")
    top = (df[df["rating"].apply(pd.to_numeric, errors="coerce") > 0]
           .nlargest(30, "rating")["name"].tolist())
    analistas = ["Carlos Mendoza", "Sofia Herrera", "Luis Paredes", "Ana Rios", "Diego Vega"]
    for juego in top:
        rc = round(random.uniform(6.0, 10.0), 1)
        rt = round(random.uniform(5.5, 10.0), 1)
        send("evaluaciones_analiticas", {
            "juego_nombre": str(juego)[:200],
            "empleado_nombre": random.choice(analistas),
            "puntuacion_comercial": rc,
            "puntuacion_tecnica": rt,
            "recomendacion": "adquirir" if (rc + rt) / 2 >= 7.5 else "revisar",
            "fecha_evaluacion": f"{random.randint(2022,2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "notas": f"Puntaje promedio: {round((rc+rt)/2,1)}",
        })
    print(f"  Enviados: {len(top)} evaluaciones")


# ── MAIN ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  GameMetrics S.A. - Poblar empresa en Pinot via Kafka")
    print("=" * 55)

    print(f"\nConectando a Kafka ({KAFKA_SERVERS})...")
    df = load_dataset()
    print(f"Dataset cargado: {len(df)} registros")

    populate_plataformas()
    populate_generos(df)
    populate_esrb()
    populate_desarrolladores(df)
    populate_publicadores(df)
    populate_empleados()
    populate_contratos(df)
    populate_catalogo(df)
    populate_campanas(df)
    populate_evaluaciones(df)

    producer.flush()
    producer.close()

    print("\n" + "=" * 55)
    print("  Listo: 10 tablas enviadas a Kafka -> Pinot.")
    print("  Los datos apareceran en Pinot en ~5-10 segundos.")
    print("=" * 55)
