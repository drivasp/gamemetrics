"""
GameMetrics S.A. - Poblar las 10 tablas de empresa con datos del dataset.
Este script es repetible: borra registros existentes y los recarga.
"""
import os
import requests
import pandas as pd
import random
from collections import Counter

PB_URL      = os.getenv("PB_URL",      "http://127.0.0.1:8090")
PB_EMAIL    = os.getenv("PB_EMAIL",    "drivasp@uteq.edu.ec")
PB_PASSWORD = os.getenv("PB_PASSWORD", "Dayver.1974")

random.seed(42)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def auth():
    r = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
    )
    r.raise_for_status()
    return r.json()["token"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def delete_all(token, collection):
    """Elimina todos los registros de una coleccion."""
    page = 1
    deleted = 0
    while True:
        r = requests.get(
            f"{PB_URL}/api/collections/{collection}/records",
            params={"perPage": 200, "page": page},
            headers={"Authorization": f"Bearer {token}"},
        )
        items = r.json().get("items", [])
        if not items:
            break
        for item in items:
            requests.delete(
                f"{PB_URL}/api/collections/{collection}/records/{item['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            deleted += 1
        page += 1
    return deleted


def insert_batch(token, collection, records):
    """Inserta una lista de registros en una coleccion."""
    ok = err = 0
    for rec in records:
        r = requests.post(
            f"{PB_URL}/api/collections/{collection}/records",
            json=rec,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if r.status_code in (200, 201):
            ok += 1
        else:
            err += 1
    return ok, err


def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ---------------------------------------------------------------------------
# Datos del dataset
# ---------------------------------------------------------------------------
def load_dataset():
    df = pd.read_parquet("data/stage/videogames.parquet")
    df = df.fillna("")
    return df


def extract_multivalue(df, col, min_len=2):
    counter = Counter()
    for v in df[col].dropna():
        for item in str(v).split("||"):
            item = item.strip()
            if len(item) >= min_len:
                counter[item] += 1
    return counter


# ---------------------------------------------------------------------------
# 1. PLATAFORMAS
# ---------------------------------------------------------------------------
PLATFORM_META = {
    "PC":               ("Varios / Valve",   "PC",       1970,  True),
    "macOS":            ("Apple",            "PC",       2001,  True),
    "Linux":            ("Open Source",      "PC",       1991,  True),
    "Android":          ("Google",           "mobile",   2008,  True),
    "iOS":              ("Apple",            "mobile",   2007,  True),
    "Web":              ("Varios",           "web",      1995,  True),
    "PlayStation":      ("Sony",             "consola",  1994,  False),
    "PlayStation 2":    ("Sony",             "consola",  2000,  False),
    "PlayStation 3":    ("Sony",             "consola",  2006,  False),
    "PlayStation 4":    ("Sony",             "consola",  2013,  True),
    "PlayStation 5":    ("Sony",             "consola",  2020,  True),
    "PS Vita":          ("Sony",             "handheld", 2011,  False),
    "PSP":              ("Sony",             "handheld", 2004,  False),
    "Xbox":             ("Microsoft",        "consola",  2001,  False),
    "Xbox 360":         ("Microsoft",        "consola",  2005,  False),
    "Xbox One":         ("Microsoft",        "consola",  2013,  True),
    "Nintendo Switch":  ("Nintendo",         "consola",  2017,  True),
    "Wii":              ("Nintendo",         "consola",  2006,  False),
    "Wii U":            ("Nintendo",         "consola",  2012,  False),
    "Nintendo 64":      ("Nintendo",         "consola",  1996,  False),
    "GameCube":         ("Nintendo",         "consola",  2001,  False),
    "NES":              ("Nintendo",         "consola",  1983,  False),
    "SNES":             ("Nintendo",         "consola",  1990,  False),
    "Nintendo DS":      ("Nintendo",         "handheld", 2004,  False),
    "Nintendo DSi":     ("Nintendo",         "handheld", 2008,  False),
    "Nintendo 3DS":     ("Nintendo",         "handheld", 2011,  True),
    "Game Boy":         ("Nintendo",         "handheld", 1989,  False),
    "Game Boy Color":   ("Nintendo",         "handheld", 1998,  False),
    "Game Boy Advance": ("Nintendo",         "handheld", 2001,  False),
    "Genesis":          ("Sega",             "consola",  1988,  False),
    "Dreamcast":        ("Sega",             "consola",  1998,  False),
    "SEGA CD":          ("Sega",             "consola",  1991,  False),
    "SEGA Master System":("Sega",            "consola",  1985,  False),
    "Game Gear":        ("Sega",             "handheld", 1990,  False),
    "Neo Geo":          ("SNK",              "consola",  1990,  False),
    "3DO":              ("Panasonic",        "consola",  1993,  False),
    "Atari ST":         ("Atari",            "PC",       1985,  False),
    "Classic Macintosh":("Apple",            "PC",       1984,  False),
    "Commodore / Amiga":("Commodore",        "PC",       1985,  False),
}

def populate_plataformas(token):
    section("1. PLATAFORMAS")
    d = delete_all(token, "plataformas")
    print(f"  Eliminados: {d} registros anteriores")
    records = []
    for nombre, (fab, tipo, anno, activa) in PLATFORM_META.items():
        records.append({
            "nombre": nombre,
            "fabricante": fab,
            "tipo": tipo,
            "anno_lanzamiento": anno,
            "activa": activa,
        })
    ok, err = insert_batch(token, "plataformas", records)
    print(f"  Insertados: {ok} plataformas | Errores: {err}")


# ---------------------------------------------------------------------------
# 2. GENEROS
# ---------------------------------------------------------------------------
GENRE_DESC = {
    "Action":               "Juegos de accion rapida con combate y reflejos",
    "Adventure":            "Exploracion de mundos y narrativas profundas",
    "RPG":                  "Juegos de rol con desarrollo de personaje y historia",
    "Shooter":              "Combate con armas de fuego en primera o tercera persona",
    "Strategy":             "Planificacion y toma de decisiones tacticamente",
    "Simulation":           "Recreacion realista de actividades o sistemas",
    "Sports":               "Competencias deportivas virtuales",
    "Puzzle":               "Retos mentales y resolucion de acertijos",
    "Platformer":           "Saltos y obstaculos en plataformas",
    "Racing":               "Competencias de velocidad en vehiculos",
    "Fighting":             "Combate cuerpo a cuerpo entre personajes",
    "Arcade":               "Juegos clasicos de maquinas recreativas",
    "Casual":               "Entretenimiento ligero y accesible",
    "Indie":                "Desarrollados por estudios independientes",
    "Massively Multiplayer":"Mundos en linea con miles de jugadores",
    "Family":               "Apto para todas las edades y grupos familiares",
    "Educational":          "Aprendizaje interactivo con contenido didactico",
    "Card":                 "Juegos de cartas digitales y coleccionables",
    "Board Games":          "Version digital de juegos de mesa clasicos",
    "Fighting":             "Combate directo entre jugadores o contra la IA",
    "Beat 'em up":          "Combate en masa contra enemigos en desplazamiento lateral",
}

def populate_generos(token, df):
    section("2. GENEROS")
    d = delete_all(token, "generos")
    print(f"  Eliminados: {d} registros anteriores")
    counter = extract_multivalue(df, "genres")
    records = []
    for nombre, count in sorted(counter.items(), key=lambda x: -x[1]):
        if len(nombre) < 3:
            continue
        records.append({
            "nombre": nombre,
            "descripcion": GENRE_DESC.get(nombre, f"Genero de videojuegos: {nombre}"),
            "popularidad": count,
        })
    ok, err = insert_batch(token, "generos", records)
    print(f"  Insertados: {ok} generos | Errores: {err}")


# ---------------------------------------------------------------------------
# 3. CLASIFICACIONES ESRB
# ---------------------------------------------------------------------------
ESRB_DATA = [
    ("E",  "Everyone",       "Apto para todos los publicos, sin contenido inapropiado",      0),
    ("E10","Everyone 10+",   "Apto para mayores de 10 anos, puede incluir violencia leve",  10),
    ("T",  "Teen",           "Para adolescentes, puede incluir violencia moderada",          13),
    ("M",  "Mature",         "Para adultos, incluye violencia intensa o contenido sexual",   17),
    ("AO", "Adults Only",    "Solo para adultos, contenido sexual o violencia extrema",      18),
    ("RP", "Rating Pending", "Clasificacion pendiente de revision por la ESRB",               0),
]

def populate_esrb(token):
    section("3. CLASIFICACIONES ESRB")
    d = delete_all(token, "clasificaciones_esrb")
    print(f"  Eliminados: {d} registros anteriores")
    records = [
        {"codigo": cod, "nombre": nom, "descripcion": desc, "edad_minima": edad}
        for cod, nom, desc, edad in ESRB_DATA
    ]
    ok, err = insert_batch(token, "clasificaciones_esrb", records)
    print(f"  Insertados: {ok} clasificaciones | Errores: {err}")


# ---------------------------------------------------------------------------
# 4. DESARROLLADORES (top 300 por numero de juegos)
# ---------------------------------------------------------------------------
PAISES = ["USA", "Japon", "Reino Unido", "Canada", "Francia", "Alemania",
          "Polonia", "Suecia", "Espana", "Australia", "Korea del Sur", "Brasil"]
TIPOS  = ["indie", "indie", "indie", "mid-size", "mid-size", "AAA"]

def populate_desarrolladores(token, df):
    section("4. DESARROLLADORES (top 300)")
    d = delete_all(token, "desarrolladores")
    print(f"  Eliminados: {d} registros anteriores")
    counter = extract_multivalue(df, "developers")
    top = [(n, c) for n, c in counter.most_common(300) if len(n) > 3]
    records = []
    for nombre, _ in top:
        records.append({
            "nombre": nombre,
            "pais": random.choice(PAISES),
            "tipo": random.choice(TIPOS),
            "sitio_web": "",
            "activo": random.random() > 0.1,
        })
    ok, err = insert_batch(token, "desarrolladores", records)
    print(f"  Insertados: {ok} desarrolladores | Errores: {err}")


# ---------------------------------------------------------------------------
# 5. PUBLICADORES (top 200 por numero de juegos)
# ---------------------------------------------------------------------------
def populate_publicadores(token, df):
    section("5. PUBLICADORES (top 200)")
    d = delete_all(token, "publicadores")
    print(f"  Eliminados: {d} registros anteriores")
    counter = extract_multivalue(df, "publishers")
    top = [(n, c) for n, c in counter.most_common(200) if len(n) > 3]
    records = []
    for nombre, _ in top:
        records.append({
            "nombre": nombre,
            "pais": random.choice(PAISES),
            "tipo": random.choice(TIPOS),
            "sitio_web": "",
            "activo": random.random() > 0.05,
        })
    ok, err = insert_batch(token, "publicadores", records)
    print(f"  Insertados: {ok} publicadores | Errores: {err}")


# ---------------------------------------------------------------------------
# 6. EMPLEADOS (20 empleados de GameMetrics S.A.)
# ---------------------------------------------------------------------------
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

def populate_empleados(token):
    section("6. EMPLEADOS")
    d = delete_all(token, "empleados")
    print(f"  Eliminados: {d} registros anteriores")
    records = [
        {"nombre": n, "apellido": a, "cargo": c, "departamento": dep,
         "email": em, "fecha_ingreso": fi, "salario": sal}
        for n, a, c, dep, em, fi, sal in EMPLEADOS_DATA
    ]
    ok, err = insert_batch(token, "empleados", records)
    print(f"  Insertados: {ok} empleados | Errores: {err}")


# ---------------------------------------------------------------------------
# 7. CONTRATOS (con los top publicadores)
# ---------------------------------------------------------------------------
TIPOS_CONTRATO = ["distribucion", "licencia", "exclusividad", "co-publicacion"]
ESTADOS        = ["activo", "activo", "activo", "vencido", "cancelado"]

def populate_contratos(token, df):
    section("7. CONTRATOS")
    d = delete_all(token, "contratos")
    print(f"  Eliminados: {d} registros anteriores")
    counter = extract_multivalue(df, "publishers")
    top_pubs = [n for n, _ in counter.most_common(20) if len(n) > 3]

    anios_inicio = list(range(2018, 2025))
    records = []
    for pub in top_pubs[:15]:
        inicio_y = random.choice(anios_inicio)
        fin_y    = inicio_y + random.randint(1, 4)
        estado   = "activo" if fin_y >= 2024 else random.choice(["vencido", "activo"])
        records.append({
            "publicador_nombre": pub,
            "tipo_contrato":     random.choice(TIPOS_CONTRATO),
            "fecha_inicio":      f"{inicio_y}-{random.randint(1,12):02d}-01",
            "fecha_fin":         f"{fin_y}-{random.randint(1,12):02d}-01",
            "valor":             random.randint(50_000, 2_000_000),
            "estado":            estado,
            "descripcion":       f"Contrato de {random.choice(TIPOS_CONTRATO)} con {pub}",
        })
    ok, err = insert_batch(token, "contratos", records)
    print(f"  Insertados: {ok} contratos | Errores: {err}")


# ---------------------------------------------------------------------------
# 8. CATALOGO DE DISTRIBUCION (top 500 juegos por rating)
# ---------------------------------------------------------------------------
REGIONES = ["Global", "LATAM", "NA", "EU", "Asia"]
ESTADOS_CAT = ["activo", "activo", "activo", "descontinuado", "preventa"]

def populate_catalogo(token, df):
    section("8. CATALOGO DE DISTRIBUCION (top 500 por rating)")
    d = delete_all(token, "catalogo_distribucion")
    print(f"  Eliminados: {d} registros anteriores")

    top = (
        df[df["rating"].apply(pd.to_numeric, errors="coerce") > 0]
        .nlargest(500, "rating")
        [["id", "name", "platforms", "rating"]]
        .dropna(subset=["name"])
    )

    records = []
    for _, row in top.iterrows():
        plats = [p.strip() for p in str(row["platforms"]).split("||") if len(p.strip()) > 2]
        plat  = plats[0] if plats else "PC"
        records.append({
            "juego_nombre":        str(row["name"])[:200],
            "juego_id":            str(row["id"]),
            "plataforma_nombre":   plat,
            "precio":              round(random.uniform(4.99, 59.99), 2),
            "fecha_incorporacion": f"{random.randint(2019,2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "region":              random.choice(REGIONES),
            "estado":              random.choice(ESTADOS_CAT),
        })
    ok, err = insert_batch(token, "catalogo_distribucion", records)
    print(f"  Insertados: {ok} juegos en catalogo | Errores: {err}")


# ---------------------------------------------------------------------------
# 9. CAMPANAS DE MARKETING (20 campanas)
# ---------------------------------------------------------------------------
CANALES = ["redes sociales", "YouTube", "influencers", "email", "TV", "eventos gaming"]

def populate_campanas(token, df):
    section("9. CAMPANAS DE MARKETING")
    d = delete_all(token, "campanas_marketing")
    print(f"  Eliminados: {d} registros anteriores")

    top_games = (
        df[df["rating"].apply(pd.to_numeric, errors="coerce") > 0]
        .nlargest(20, "rating")["name"]
        .tolist()
    )
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

    records = []
    for i, nombre in enumerate(campanas):
        presupuesto = random.randint(10_000, 500_000)
        records.append({
            "nombre":        nombre,
            "juego_nombre":  top_games[i] if i < len(top_games) else top_games[0],
            "genero_nombre": generos[i % len(generos)],
            "presupuesto":   presupuesto,
            "gasto_real":    round(presupuesto * random.uniform(0.5, 1.1)),
            "fecha_inicio":  f"{random.randint(2022,2024)}-{random.randint(1,12):02d}-01",
            "fecha_fin":     f"{random.randint(2024,2025)}-{random.randint(1,12):02d}-01",
            "canal":         random.choice(CANALES),
            "estado":        random.choice(["planificada", "activa", "finalizada"]),
        })
    ok, err = insert_batch(token, "campanas_marketing", records)
    print(f"  Insertados: {ok} campanas | Errores: {err}")


# ---------------------------------------------------------------------------
# 10. EVALUACIONES ANALITICAS (top 30 juegos por rating)
# ---------------------------------------------------------------------------
RECOMENDACIONES = ["adquirir", "adquirir", "revisar", "rechazar"]

def populate_evaluaciones(token, df):
    section("10. EVALUACIONES ANALITICAS")
    d = delete_all(token, "evaluaciones_analiticas")
    print(f"  Eliminados: {d} registros anteriores")

    top = (
        df[df["rating"].apply(pd.to_numeric, errors="coerce") > 0]
        .nlargest(30, "rating")["name"]
        .tolist()
    )
    analistas = [
        "Carlos Mendoza", "Sofia Herrera", "Luis Paredes",
        "Ana Rios", "Diego Vega",
    ]

    records = []
    for juego in top:
        analista = random.choice(analistas)
        rating_c = round(random.uniform(6.0, 10.0), 1)
        rating_t = round(random.uniform(5.5, 10.0), 1)
        records.append({
            "juego_nombre":         str(juego)[:200],
            "empleado_nombre":      analista,
            "puntuacion_comercial": rating_c,
            "puntuacion_tecnica":   rating_t,
            "recomendacion":        "adquirir" if (rating_c + rating_t) / 2 >= 7.5 else "revisar",
            "fecha_evaluacion":     f"{random.randint(2022,2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "notas":                f"Evaluacion interna. Puntaje promedio: {round((rating_c+rating_t)/2,1)}",
        })
    ok, err = insert_batch(token, "evaluaciones_analiticas", records)
    print(f"  Insertados: {ok} evaluaciones | Errores: {err}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 55)
    print("  GameMetrics S.A. - Poblando tablas de empresa")
    print("=" * 55)

    token = auth()
    print("Autenticado correctamente")

    df = load_dataset()
    print(f"Dataset cargado: {len(df)} registros")

    populate_plataformas(token)
    populate_generos(token, df)
    populate_esrb(token)
    populate_desarrolladores(token, df)
    populate_publicadores(token, df)
    populate_empleados(token)
    populate_contratos(token, df)
    populate_catalogo(token, df)
    populate_campanas(token, df)
    populate_evaluaciones(token, df)

    print("\n" + "=" * 55)
    print("  Listo: 10 tablas pobladas correctamente.")
    print("  Este script puede ejecutarse las veces que quieras.")
    print("=" * 55)
