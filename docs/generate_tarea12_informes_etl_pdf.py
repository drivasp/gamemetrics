"""PDF Tarea 12: Informes tácticos + transformación ETL (con carátula UTEQ)."""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "Tarea_12_Informes_ETL_GameMetrics.pdf"
LOGO = ROOT / "assets" / "uteq_logo.png"
FONT_DIR = Path(r"C:\Windows\Fonts")
FN = "ArialGM"


class Doc(FPDF):
    def header(self):
        if self.page_no() <= 1:
            return
        self.set_x(self.l_margin)
        self.set_font(FN, "I", 8)
        self.set_text_color(90, 90, 90)
        w = self.w - self.l_margin - self.r_margin
        self.cell(w, 6, "Tarea 12 | Informes y transformacion ETL | GameMetrics S.A.", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() <= 1:
            return
        self.set_y(-14)
        self.set_x(self.l_margin)
        self.set_font(FN, "I", 8)
        self.set_text_color(110, 110, 110)
        w = self.w - self.l_margin - self.r_margin
        self.cell(w, 8, f"Pagina {self.page_no() - 1}", align="C")


def uw(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def h1(pdf: FPDF, t: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "B", 13)
    pdf.set_text_color(15, 45, 80)
    pdf.multi_cell(uw(pdf), 7, t)
    pdf.ln(2)


def h2(pdf: FPDF, t: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "B", 11)
    pdf.set_text_color(25, 70, 110)
    pdf.multi_cell(uw(pdf), 6.5, t)
    pdf.ln(1)


def p(pdf: FPDF, t: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "", 10)
    pdf.set_text_color(25, 25, 25)
    pdf.multi_cell(uw(pdf), 5.4, t)
    pdf.ln(1.5)


def bullet(pdf: FPDF, t: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(FN, "", 10)
    pdf.set_text_color(25, 25, 25)
    pdf.multi_cell(uw(pdf), 5.3, f"  -  {t}")


def box(pdf: FPDF, title: str, lines: list[str]):
    w = uw(pdf)
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(240, 246, 252)
    pdf.set_font(FN, "B", 10)
    pdf.set_text_color(15, 45, 80)
    pdf.multi_cell(w, 6, title, fill=True)
    pdf.set_font(FN, "", 9.5)
    pdf.set_text_color(30, 30, 30)
    for ln in lines:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w, 5.2, ln, fill=True)
    pdf.ln(3)


def cover(pdf: Doc):
    pdf.add_page()
    # Logo top-right
    if LOGO.exists():
        pdf.image(str(LOGO), x=145, y=18, w=48)

    pdf.set_y(55)
    pdf.set_text_color(0, 0, 0)
    lines = [
        ("UNIVERSIDAD TECNICA ESTATAL DE QUEVEDO", "B", 13),
        ("INGENIERIA DE SOFTWARE", "B", 12),
        ("Construccion del Software", "B", 12),
        ("Tarea 12", "B", 12),
        ("RIVAS PILOSO DAYVER YAHIR", "B", 12),
        ("Informes tácticos y transformación ETL", "B", 12),
        ("Proyecto: GameMetrics S.A.", "B", 12),
        ("02/08/2026", "B", 12),
    ]
    # Use ASCII-safe titles where needed for consistency with carátula style
    lines = [
        ("UNIVERSIDAD TECNICA ESTATAL DE QUEVEDO", "B", 13),
        ("INGENIERIA DE SOFTWARE", "B", 12),
        ("Construccion del Software", "B", 12),
        ("Tarea 12", "B", 12),
        ("RIVAS PILOSO DAYVER YAHIR", "B", 12),
        ("Informes tacticos y transformacion ETL", "B", 12),
        ("Proyecto: GameMetrics S.A.", "B", 12),
        ("02/08/2026", "B", 12),
    ]
    for text, style, size in lines:
        pdf.set_font(FN, style, size)
        pdf.set_x(pdf.l_margin)
        pdf.cell(uw(pdf), 10, text, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)


def main():
    pdf = Doc(format="A4")
    pdf.add_font(FN, "", str(FONT_DIR / "arial.ttf"))
    pdf.add_font(FN, "B", str(FONT_DIR / "arialbd.ttf"))
    pdf.add_font(FN, "I", str(FONT_DIR / "ariali.ttf"))
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)

    cover(pdf)

    # 1
    pdf.add_page()
    h1(pdf, "1. Objetivo del documento")
    p(
        pdf,
        "Este documento explica como GameMetrics S.A. construye sus informes tácticos "
        "y, sobre todo, como ocurre la transformacion ETL hacia la base de datos analitica "
        "asignada al proyecto: Apache Pinot (con Apache Kafka como canal de carga en tiempo casi real).",
    )
    p(
        pdf,
        "Importante: la transformacion no 'vive' en la pantalla Angular. La UI solo consulta "
        "y presenta resultados. La calidad analitica depende del pipeline ETL y de las tablas "
        "de hechos en Pinot.",
    )
    box(
        pdf,
        "Entregables demostrados en Evaluacion 01",
        [
            "  -  3 Workpanels (ingreso/gestion de datos)",
            "  -  3 Informes simples (listados)",
            "  -  3 Informes complejos (agregaciones OLAP)",
            "  -  Explicacion ETL -> Pinot (base de datos del proyecto)",
        ],
    )

    h1(pdf, "2. Base de datos asignada: Apache Pinot")
    p(
        pdf,
        "Apache Pinot es una base columnar OLAP orientada a consultas analiticas rapidas. "
        "En GameMetrics se usa en dos modos:",
    )
    bullet(pdf, "OFFLINE: cargas por lotes (Parquet) del catalogo analitico y dimensiones.")
    bullet(pdf, "REALTIME: consumo de topics Kafka hacia tablas de hechos operativos.")
    pdf.ln(2)
    p(
        pdf,
        "Tablas clave para reportes: emp_records, fact_partner_games, fact_partner_payouts, "
        "fact_support_tickets, fact_partner_ledger, fact_partner_accounts.",
    )

    h1(pdf, "3. Transformacion ETL (Extract - Transform - Load)")
    h2(pdf, "3.1 Extract (Extraer)")
    p(
        pdf,
        "Se extraen datos desde fuentes operativas y datasets externos:",
    )
    bullet(pdf, "Catalogo de videojuegos (RAWG / Parquet / jobs ETL).")
    bullet(pdf, "Operacion de tienda: ordenes, partners, claims, tickets, payouts.")
    bullet(pdf, "Datos empresariales maestros (empleados, plataformas, generos, etc.).")
    bullet(pdf, "Disparo desde Dashboard ETL (localhost:4000) y scripts Python en etl/.")

    h2(pdf, "3.2 Transform (Transformar)")
    p(
        pdf,
        "En esta etapa los datos se normalizan para analisis. No es un 'copiar y pegar' crudo:",
    )
    bullet(pdf, "Limpieza y tipado de campos (montos, fechas en milisegundos, IDs).")
    bullet(pdf, "Estados de negocio (pending / approved / rejected; open / closed; paid).")
    bullet(pdf, "Split comercial 70/30: bruto, fee de plataforma, neto publisher.")
    bullet(pdf, "Soft-delete (deleted=true) para no perder historial analitico.")
    bullet(pdf, "Claves estables de hechos (sale_*, refund_*, payout_*, partner_game_id, etc.).")
    p(
        pdf,
        "La transformacion ocurre en scripts ETL (carpeta etl/) y en la logica FastAPI al "
        "escribir eventos de negocio hacia Kafka.",
    )

    h2(pdf, "3.3 Load (Cargar)")
    p(
        pdf,
        "El resultado se carga en Apache Pinot:",
    )
    bullet(pdf, "Realtime: productor Kafka -> topic = nombre de tabla -> Pinot consume.")
    bullet(pdf, "Offline: Parquet / ingest jobs para fact_videogames y dimensiones.")
    p(
        pdf,
        "Despues del Load, el Centro de Reportes (FastAPI /reports + Angular /reports) "
        "consulta Pinot con SQL OLAP y arma el payload del informe (filas, KPIs, CSV).",
    )

    box(
        pdf,
        "Frase sintesis (para oral / video)",
        [
            "Extraemos datos operativos y del catalogo, los transformamos en el pipeline ETL",
            "(limpieza, estados, split 70/30) y los cargamos en Apache Pinot via Kafka.",
            "Los reportes leen Pinot: simples = listados; complejos = agregaciones OLAP.",
        ],
    )

    # 4
    pdf.add_page()
    h1(pdf, "4. Informes simples (listados)")
    p(
        pdf,
        "Un informe simple responde una pregunta operativa con un listado casi directo "
        "sobre una tabla de hechos REALTIME. La 'transformacion' previa ya ocurrio en el ETL "
        "al escribir el evento; el informe no recalcula GMV ni rollups pesados.",
    )

    h2(pdf, "GM-S01 - Cola de solicitudes de propiedad")
    bullet(pdf, "Pregunta: Que claims de juegos siguen sin decidir?")
    bullet(pdf, "Fuente Pinot: fact_partner_games (filtro submission_status).")
    bullet(pdf, "ETL: el partner crea el claim -> Kafka -> Pinot (estado pending).")
    bullet(pdf, "UI: /reports/GM-S01")

    h2(pdf, "GM-S02 - Historial de liquidaciones")
    bullet(pdf, "Pregunta: Que pagos a estudios ya quedaron registrados?")
    bullet(pdf, "Fuente Pinot: fact_partner_payouts.")
    bullet(pdf, "ETL: admin registra payout -> Kafka -> Pinot (+ asiento de control en ledger).")
    bullet(pdf, "UI: /reports/GM-S02")

    h2(pdf, "GM-S03 - Tickets de soporte abiertos")
    bullet(pdf, "Pregunta: Que solicitudes de ayuda siguen abiertas?")
    bullet(pdf, "Fuente Pinot: fact_support_tickets (status=open).")
    bullet(pdf, "ETL: el jugador crea ticket -> Kafka -> Pinot.")
    bullet(pdf, "UI: /reports/GM-S03")

    h1(pdf, "5. Informes complejos (agregacion OLAP)")
    p(
        pdf,
        "Un informe complejo cruza o agrega hechos ya transformados. Aqui Pinot aporta valor: "
        "sumas, rollups por partner/juego, KPIs de GMV, fee y neto.",
    )

    h2(pdf, "GM-C01 - Resumen economico de plataforma")
    bullet(pdf, "Pregunta: Cuanto GMV, comision y adeudo acumula GameMetrics?")
    bullet(pdf, "Fuente: agregacion sobre fact_partner_ledger.")
    bullet(pdf, "Transformacion analitica: SUM(gross), SUM(fee), SUM(net), COUNT ventas/reembolsos.")
    bullet(pdf, "UI: /reports/GM-C01")

    h2(pdf, "GM-C02 - Ganancias por estudio")
    bullet(pdf, "Pregunta: Cuanto gano un estudio (bruto, fee, neto, saldo)?")
    bullet(pdf, "Fuentes: fact_partner_ledger + fact_partner_payouts (por partner_id).")
    bullet(pdf, "Transformacion: balance available/paid + desglose por juego.")
    bullet(pdf, "UI: /reports/GM-C02")

    h2(pdf, "GM-C03 - Desempeno comercial por estudio")
    bullet(pdf, "Pregunta: Que estudios venden mas y quienes concentran reembolsos?")
    bullet(pdf, "Fuentes: fact_partner_accounts + fact_partner_ledger (+ conteo de games).")
    bullet(pdf, "Transformacion: rollup por partner (unidades, bruto, fee, neto, refunds).")
    bullet(pdf, "UI: /reports/GM-C03")

    # 6
    pdf.add_page()
    h1(pdf, "6. Flujo extremo a extremo")
    box(
        pdf,
        "De la operacion al informe",
        [
            "1) Workpanel (Empresa / Partner / Admin) genera o cambia datos.",
            "2) FastAPI publica el evento a Kafka (topic = tabla).",
            "3) ETL/transformacion deja el hecho listo (estados, montos, split).",
            "4) Pinot carga el registro (REALTIME).",
            "5) /reports/view/{codigo} consulta Pinot y arma filas + KPIs.",
            "6) El usuario exporta CSV/PDF para decision tactica.",
        ],
    )

    h1(pdf, "7. Relacion Workpanel vs Informe")
    p(
        pdf,
        "Workpanel = ingreso y gestion (CRUD / aprobar / liquidar). "
        "Informe = lectura analitica o operativa para decidir. "
        "Sin ETL hacia Pinot, los informes no tendrian hechos consistentes que consultar.",
    )
    bullet(pdf, "Workpanel Empresa -> emp_records")
    bullet(pdf, "Workpanel Partner claim -> fact_partner_games")
    bullet(pdf, "Workpanel Admin approve/payout -> games + payouts + ledger")
    bullet(pdf, "Informes S01-S03 / C01-C03 -> lectura Pinot")

    h1(pdf, "8. Conclusion")
    p(
        pdf,
        "En GameMetrics, los reportes son el producto visible de un pipeline ETL hacia "
        "Apache Pinot. Extract trae la operacion y el catalogo; Transform prepara hechos "
        "con reglas de negocio (estados, 70/30); Load deja los datos en Pinot via Kafka. "
        "Los informes simples listan esos hechos; los complejos los agregan. "
        "Esa es la transformacion ETL de los reportes: ocurre en la capa de datos, "
        "no en el maquetado de la interfaz.",
    )

    pdf.output(str(OUT))
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
