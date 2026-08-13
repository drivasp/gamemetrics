"""Genera PDF guion video Evaluacion 01 — Workpanels + Informes + ETL."""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "Guion_Video_Evaluacion01_GameMetrics.pdf"
FONT_DIR = Path(r"C:\Windows\Fonts")
FN = "ArialGM"


class ScriptPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_x(self.l_margin)
        self.set_font(FN, "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "GameMetrics S.A. | Guion video Evaluacion 01 | max 15 min", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-14)
        self.set_x(self.l_margin)
        self.set_font(FN, "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}}", align="C")


def usable_w(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def h1(pdf: FPDF, text: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "B", 14)
    pdf.set_text_color(20, 40, 70)
    pdf.multi_cell(usable_w(pdf), 8, text)
    pdf.ln(2)


def h2(pdf: FPDF, text: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "B", 11)
    pdf.set_text_color(30, 80, 120)
    pdf.multi_cell(usable_w(pdf), 7, text)
    pdf.ln(1)


def body(pdf: FPDF, text: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "", 10)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(usable_w(pdf), 5.5, text)
    pdf.ln(1)


def say(pdf: FPDF, text: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "B", 9)
    pdf.set_text_color(140, 40, 40)
    pdf.multi_cell(usable_w(pdf), 5.5, "DECIR: " + text)
    pdf.ln(1)


def show(pdf: FPDF, text: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "B", 9)
    pdf.set_text_color(20, 100, 60)
    pdf.multi_cell(usable_w(pdf), 5.5, "MOSTRAR: " + text)
    pdf.ln(1)


def box(pdf: FPDF, title: str, lines: list[str]):
    w = usable_w(pdf)
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(245, 248, 252)
    pdf.set_font(FN, "B", 10)
    pdf.set_text_color(20, 40, 70)
    pdf.multi_cell(w, 6, title, fill=True)
    pdf.set_font(FN, "", 9)
    pdf.set_text_color(30, 30, 30)
    for ln in lines:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w, 5, ln, fill=True)
    pdf.ln(3)


def main():
    pdf = ScriptPDF(format="A4")
    pdf.add_font(FN, "", str(FONT_DIR / "arial.ttf"))
    pdf.add_font(FN, "B", str(FONT_DIR / "arialbd.ttf"))
    pdf.add_font(FN, "I", str(FONT_DIR / "ariali.ttf"))
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()

    pdf.set_font(FN, "B", 18)
    pdf.set_text_color(15, 35, 70)
    pdf.ln(10)
    pdf.set_x(pdf.l_margin)
    pdf.cell(usable_w(pdf), 10, "GUION PARA VIDEO", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FN, "B", 13)
    pdf.cell(usable_w(pdf), 8, "Construccion del Software - Evaluacion 01", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FN, "", 11)
    pdf.cell(usable_w(pdf), 7, "GameMetrics S.A. | Sexto semestre | Maximo 15 minutos", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    box(
        pdf,
        "Que debes demostrar (rubrica)",
        [
            "1) WORKPANEL ........................ 3",
            "2) INFORMES SIMPLES ................. 3",
            "3) INFORMES COMPLEJOS ............... 3",
            "Plus: explicar ETL / transformacion hacia la BD (Apache Pinot) que alimenta los reportes.",
        ],
    )
    body(
        pdf,
        "Usa este PDF como teleprompter: lee DECIR mientras en pantalla haces MOSTRAR. "
        "No improvises de mas: el tiempo es corto.",
    )

    pdf.add_page()
    h1(pdf, "0. Antes de grabar (checklist)")
    body(
        pdf,
        "1. Docker arriba (frontend :4000, backend :8080, Pinot, Kafka).\n"
        "2. Login Admin: admin@gamemetrics.demo (o tu admin).\n"
        "3. Pestanas listas:\n"
        "   - http://localhost:4000/empresa\n"
        "   - http://localhost:4000/admin\n"
        "   - http://localhost:4000/my-partner\n"
        "   - http://localhost:4000/reports\n"
        "   - http://localhost:4000/  (Dashboard ETL)\n"
        "4. Datos demo cargados (claims, ledger, payouts, tickets).\n"
        "5. Cronometro visible. Objetivo ~13-14 min.",
    )
    box(
        pdf,
        "Distribucion de tiempo sugerida",
        [
            "0:00-1:00    Intro + stack + BD (Pinot/Kafka)",
            "1:00-5:00    3 Workpanels",
            "5:00-7:30    Explicacion ETL (como llegan los datos a Pinot)",
            "7:30-11:00   3 Informes simples",
            "11:00-14:00  3 Informes compuestos + export CSV/PDF",
            "14:00-15:00  Cierre",
        ],
    )

    h1(pdf, "1. Introduccion (0:00 - 1:00)")
    show(pdf, "Tienda o dashboard. Logo GameMetrics.")
    say(
        pdf,
        "Buenas, somos el equipo de GameMetrics S.A. En este video demostramos la Evaluacion 01: "
        "tres workpanels de ingreso y gestion de datos, tres informes simples y tres informes complejos. "
        "Nuestra base analitica asignada es Apache Pinot, alimentada por un pipeline ETL con Kafka. "
        "La app es Angular + FastAPI en Docker.",
    )

    h1(pdf, "2. WORKPANELS - 3 (1:00 - 5:00)")
    body(
        pdf,
        "Workpanel = pantalla interactiva: listar + ingresar/editar/eliminar o acciones "
        "(CRUD / aprobar / liquidar). NO es un reporte de solo lectura.",
    )

    h2(pdf, "Workpanel 1 - CRUD Empresa / Empleados (~1:20)")
    show(pdf, "http://localhost:4000/empresa  ->  Empleados. Abrir + Nuevo.")
    say(
        pdf,
        "Primer workpanel: modulo Empresa. El administrador mantiene datos maestros. "
        "Listo empleados, creo uno con el formulario, lo edito y si alcanza el tiempo lo elimino. "
        "CRUD completo sobre emp_records en Pinot, via Kafka. Hay 10 colecciones con el mismo patron "
        "(plataformas, generos, contratos, etc.).",
    )

    h2(pdf, "Workpanel 2 - Partner: reclamar / ingresar juego (~1:20)")
    show(pdf, "http://localhost:4000/my-partner  -> formulario claim / listado de juegos.")
    say(
        pdf,
        "Segundo workpanel: portal del publisher. El estudio ingresa datos: reclama un juego del "
        "catalogo. Se crea un registro en fact_partner_games con estado pending. Es ingreso de datos, "
        "no un informe.",
    )

    h2(pdf, "Workpanel 3 - Admin: aprobar claim + payout (~1:20)")
    show(pdf, "http://localhost:4000/admin  -> Aprobar claim. Luego crear payout.")
    say(
        pdf,
        "Tercer workpanel: panel Admin. Aqui se actua: apruebo o rechazo solicitudes de propiedad "
        "y registro una liquidacion (payout). Escribe en fact_partner_games y fact_partner_payouts / ledger.",
    )

    pdf.add_page()
    h1(pdf, "3. ETL y la BD de reportes (5:00 - 7:30) - IMPORTANTE")
    body(
        pdf,
        "Esta seccion responde a lo que pidieron: explicar la transformacion ETL de los reportes. "
        "No es del frontend: es el flujo hacia la base de datos que les toco (Apache Pinot). "
        "Lee despacio.",
    )
    show(pdf, "Dashboard http://localhost:4000/ (jobs ETL). Opcional Pinot :9000 unos segundos.")
    say(
        pdf,
        "Los informes no inventan datos en Angular. Leen Apache Pinot, nuestra base columnar OLAP. "
        "El camino es ETL clasico:",
    )
    box(
        pdf,
        "E - Extract (Extraer)",
        [
            "- Fuentes: dataset de videojuegos (RAWG/Parquet), operaciones de tienda,",
            "  partners, compras, liquidaciones, tickets, datos empresa.",
            "- En el dashboard se disparan jobs: catalogo, dimensiones, empresa, seeds.",
        ],
    )
    box(
        pdf,
        "T - Transform (Transformar)",
        [
            "- Limpieza, tipado, normalizacion, IDs, estados (pending/approved),",
            "  split comercial 70/30 (bruto, fee plataforma, neto publisher),",
            "  soft-delete, timestamps en milisegundos.",
            "- Scripts Python en etl/ + logica FastAPI al escribir hechos de negocio.",
        ],
    )
    box(
        pdf,
        "L - Load (Cargar) -> Base asignada: Apache Pinot (+ Kafka)",
        [
            "- Offline: fact_videogames y dimensiones (carga por lotes/Parquet).",
            "- Realtime: Kafka topics -> tablas Pinot (emp_records, fact_partner_games,",
            "  fact_partner_ledger, fact_partner_payouts, fact_support_tickets, etc.).",
            "- Los reportes consultan esas tablas Pinot con SQL OLAP.",
        ],
    )
    say(
        pdf,
        "Resumen: Extract de la operacion y datasets, Transform en el pipeline ETL, Load en Pinot. "
        "Informe simple = listado casi directo de una tabla de hechos. "
        "Informe complejo = agregaciones y cruces OLAP sobre ledger y cuentas. "
        "Airflow podria orquestar; hoy usamos panel ETL y scripts Python.",
    )

    pdf.add_page()
    h1(pdf, "4. INFORMES SIMPLES - 3 (7:30 - 11:00)")
    show(pdf, "http://localhost:4000/reports  -> seccion Simples.")
    say(
        pdf,
        "Centro de Reportes. Un informe simple es un listado operativo: filas de una consulta "
        "directa a Pinot, sin agregacion pesada. Demuestro tres.",
    )

    h2(pdf, "Simple 1 - GM-S01 Cola de solicitudes de propiedad")
    show(pdf, "/reports/GM-S01  Filtro ESTADO = pending. Exportar CSV.")
    say(
        pdf,
        "GM-S01 lista claims pendientes desde fact_partner_games. Pregunta: que solicitudes de "
        "propiedad siguen sin decidir. Fuente Pinot, filtro por status.",
    )

    h2(pdf, "Simple 2 - GM-S02 Historial de liquidaciones")
    show(pdf, "/reports/GM-S02  Tabla con montos. Exportar.")
    say(
        pdf,
        "GM-S02 lista payouts en fact_partner_payouts: monto, metodo, referencia y fecha.",
    )

    h2(pdf, "Simple 3 - GM-S03 Tickets de soporte abiertos")
    show(pdf, "/reports/GM-S03  Filtro open.")
    say(
        pdf,
        "GM-S03 lista tickets abiertos de fact_support_tickets, ordenados por prioridad y fecha. "
        "Sigue siendo listado simple, no un KPI agregado.",
    )

    h1(pdf, "5. INFORMES COMPLEJOS - 3 (11:00 - 14:00)")
    say(
        pdf,
        "Los compuestos cruzan o agregan hechos del ledger. Aqui se ve el valor del ETL hacia Pinot.",
    )

    h2(pdf, "Complejo 1 - GM-C01 Resumen economico de plataforma")
    show(pdf, "/reports/GM-C01  KPIs GMV, ingresos, adeudado, unidades, reembolsos.")
    say(
        pdf,
        "GM-C01 agrega fact_partner_ledger: GMV, take rate, adeudado a publishers, unidades y "
        "reembolsos. Es OLAP, no un listado de una sola fila operativa.",
    )

    h2(pdf, "Complejo 2 - GM-C02 Ganancias por estudio")
    show(pdf, "/reports/GM-C02  Elegir Demo 2 o Nebula. KPIs + tabla por juego. Exportar.")
    say(
        pdf,
        "GM-C02 por partner: bruto, fee, neto, saldo disponible, ya liquidado y desglose por juego. "
        "Cruza ledger y payouts.",
    )

    h2(pdf, "Complejo 3 - GM-C03 Desempeno comercial por estudio")
    show(pdf, "/reports/GM-C03  Ranking de estudios. Exportar CSV/PDF.")
    say(
        pdf,
        "GM-C03 hace rollup por estudio: juegos, unidades, bruto, comision, neto y reembolsos. "
        "Con esto cerramos los tres compuestos.",
    )

    h1(pdf, "6. Cierre (14:00 - 15:00)")
    show(pdf, "Volver a /reports o dashboard.")
    say(
        pdf,
        "Resumen: tres workpanels (Empresa CRUD, Partner claims, Admin aprobacion/payouts); "
        "tres informes simples; tres compuestos con agregacion OLAP. Todo respaldado por ETL "
        "hacia Apache Pinot via Kafka. Gracias.",
    )

    pdf.add_page()
    h1(pdf, "7. Hoja rapida (imprimir y tener al lado)")
    box(
        pdf,
        "WORKPANELS (3)",
        [
            "1. /empresa -> Empleados (CRUD crear/editar/borrar)",
            "2. /my-partner -> reclamar juego (insert)",
            "3. /admin -> aprobar claim + crear payout",
        ],
    )
    box(
        pdf,
        "INFORMES SIMPLES (3)",
        [
            "GM-S01  Cola de solicitudes de propiedad     fact_partner_games",
            "GM-S02  Historial de liquidaciones            fact_partner_payouts",
            "GM-S03  Tickets de soporte abiertos           fact_support_tickets",
        ],
    )
    box(
        pdf,
        "INFORMES COMPLEJOS (3)",
        [
            "GM-C01  Resumen economico plataforma          agrega ledger",
            "GM-C02  Ganancias por estudio                 ledger + payouts",
            "GM-C03  Desempeno comercial por estudio       accounts + ledger",
        ],
    )
    box(
        pdf,
        "FRASE ETL (si te preguntan)",
        [
            "Extraemos datos operativos y del catalogo, los transformamos en el pipeline ETL",
            "(limpieza, estados, split 70/30) y los cargamos en Apache Pinot a traves de Kafka.",
            "Los reportes consultan Pinot: simples = listados; complejos = agregaciones OLAP.",
        ],
    )
    body(
        pdf,
        "Consejos: habla mas lento en ETL; si algo falla pasa al siguiente item; al exportar CSV "
        "abre el archivo 3 segundos para que se vean datos.",
    )

    pdf.output(str(OUT))
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
