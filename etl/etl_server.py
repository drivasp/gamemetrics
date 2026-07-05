"""
GameMetrics S.A. - ETL API Server
Expone endpoints HTTP para re-ejecutar el ETL desde la web.
"""
import json
import os
import subprocess
import threading
import urllib.error
import urllib.request

from flask import Flask, jsonify, request

app = Flask(__name__)

# Estado de cada job: idle | running | ok | error
jobs = {
    "dataset":     {"status": "idle", "mensaje": ""},
    "empresa":     {"status": "idle", "mensaje": ""},
    "dimensiones": {"status": "idle", "mensaje": ""},
    "realtime":    {"status": "idle", "mensaje": ""},
    "catalogo":    {"status": "idle", "mensaje": ""},
    "promociones": {"status": "idle", "mensaje": ""},
    "phase2":      {"status": "idle", "mensaje": ""},
    "coupons":     {"status": "idle", "mensaje": ""},
    "phase3":      {"status": "idle", "mensaje": ""},
    "phase4":      {"status": "idle", "mensaje": ""},
    "phase5":      {"status": "idle", "mensaje": ""},
}

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "data", "stage", "semanas_cargadas.json")

# Garantiza resolución DNS Docker aunque el subprocess no herede bien el entorno
PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://pinot-controller:9000")
PINOT_BROKER_URL = os.getenv("PINOT_BROKER_URL", "http://pinot-broker:8099")
KAFKA_BOOTSTRAP  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
BASE_ETL_ENV = {
    "PINOT_CONTROLLER": PINOT_CONTROLLER,
    "PINOT_CONTROLLER_URL": PINOT_CONTROLLER,
    "PINOT_BROKER_URL": PINOT_BROKER_URL,
    "KAFKA_BOOTSTRAP_SERVERS": KAFKA_BOOTSTRAP,
}


def get_semanas_cargadas() -> list:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _format_job_error(stdout: str, stderr: str) -> str:
    text = (stderr or stdout or "").strip()
    if not text:
        return "Error desconocido"
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in reversed(lines):
        if any(k in ln for k in ("ERROR", "Error", "Failed", "Traceback", "❌", "RuntimeError")):
            return ln[:600]
    return text[-600:]


def _check_pinot_ready() -> str | None:
    """None si Pinot responde; mensaje de error legible si no."""
    try:
        req = urllib.request.Request(
            f"{PINOT_CONTROLLER.rstrip('/')}/health",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return None
            return f"Pinot Controller respondió HTTP {resp.status}"
    except Exception as exc:
        return (
            f"Pinot Controller no disponible en {PINOT_CONTROLLER}. "
            "Levanta Pinot: docker compose up -d pinot-controller pinot-broker pinot-server. "
            f"Detalle: {exc}"
        )


def _run(key, scripts, extra_env=None):
    jobs[key] = {"status": "running", "mensaje": "Ejecutando..."}
    env = {**os.environ, **BASE_ETL_ENV, "PYTHONUTF8": "1"}
    if extra_env:
        env.update(extra_env)
    for script in scripts:
        lines: list[str] = []
        try:
            proc = subprocess.Popen(
                ["python", "-u", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                cwd=BASE_DIR,
                bufsize=1,
            )
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.rstrip()
                if not line:
                    continue
                lines.append(line)
                jobs[key]["mensaje"] = line[:240]
            proc.wait()
            if proc.returncode != 0:
                jobs[key] = {
                    "status": "error",
                    "mensaje": _format_job_error("\n".join(lines), ""),
                }
                return
        except Exception as e:
            jobs[key] = {"status": "error", "mensaje": str(e)}
            return
    jobs[key] = {"status": "ok", "mensaje": "Completado exitosamente"}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route("/etl/status")
def get_status():
    return jsonify(jobs)


@app.route("/etl/semanas-status")
def semanas_status():
    return jsonify({"semanas": get_semanas_cargadas()})


@app.route("/etl/reload-dataset", methods=["POST"])
def reload_dataset():
    if jobs["dataset"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409

    data   = request.get_json(silent=True) or {}
    semana = max(1, min(17, int(data.get("semana", 1))))
    force  = bool(data.get("force", False))

    semanas_cargadas = get_semanas_cargadas()

    if semana in semanas_cargadas and not force:
        return jsonify({
            "mensaje":   f"La semana {semana} ya esta cargada",
            "ya_existe": True,
            "semana":    semana,
        })

    pinot_err = _check_pinot_ready()
    if pinot_err:
        jobs["dataset"] = {"status": "error", "mensaje": pinot_err}
        return jsonify({"mensaje": pinot_err, "pinot_down": True}), 503

    jobs["dataset"]["mensaje"] = f"Cargando semana {semana}..."
    env = {"SEMANA_TARGET": str(semana)}
    if force:
        env["FORCE_RESET"] = "1"

    threading.Thread(
        target=_run,
        args=("dataset", ["04_ingest_pinot.py"]),
        kwargs={"extra_env": env},
        daemon=True,
    ).start()
    return jsonify({"mensaje": "Iniciado", "semana": semana, "ya_existe": False})


@app.route("/etl/reload-empresa", methods=["POST"])
def reload_empresa():
    if jobs["empresa"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run,
        args=("empresa", ["09_populate_empresa_pinot.py"]),
        daemon=True,
    ).start()
    return jsonify({"mensaje": "Iniciado"})


@app.route("/etl/reload-dimensions", methods=["POST"])
def reload_dimensions():
    if jobs["dimensiones"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run, args=("dimensiones", ["07_create_dimensions.py"]), daemon=True
    ).start()
    return jsonify({"mensaje": "Iniciado"})


@app.route("/etl/create-realtime-tables", methods=["POST"])
def create_realtime_tables():
    if jobs["realtime"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run, args=("realtime", ["08_create_realtime_tables.py"]), daemon=True
    ).start()
    return jsonify({"mensaje": "Iniciado"})


@app.route("/etl/reload-catalogo", methods=["POST"])
def reload_catalogo():
    if jobs["catalogo"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    data = request.get_json(silent=True) or {}
    semana = max(1, min(17, int(data.get("semana", 1))))
    env = {"SEMANA_TARGET": str(semana)}
    threading.Thread(
        target=_run,
        args=("catalogo", ["10_create_catalog_tables.py"]),
        kwargs={"extra_env": env},
        daemon=True,
    ).start()
    return jsonify({"mensaje": "Iniciado", "semana": semana})


@app.route("/etl/seed-promociones", methods=["POST"])
def seed_promociones():
    if jobs["promociones"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run, args=("promociones", ["11_seed_promotions.py"]), daemon=True
    ).start()
    return jsonify({"mensaje": "Iniciado"})


@app.route("/etl/create-phase2-tables", methods=["POST"])
def create_phase2_tables():
    if jobs["phase2"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run, args=("phase2", ["13_create_phase2_tables.py"]), daemon=True
    ).start()
    return jsonify({"mensaje": "Iniciado"})


@app.route("/etl/seed-coupons", methods=["POST"])
def seed_coupons():
    if jobs["coupons"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run, args=("coupons", ["12_seed_coupons.py"]), daemon=True
    ).start()
    return jsonify({"mensaje": "Iniciado"})


@app.route("/etl/create-phase3-tables", methods=["POST"])
def create_phase3_tables():
    if jobs["phase3"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run, args=("phase3", ["14_create_phase3_tables.py"]), daemon=True
    ).start()
    return jsonify({"mensaje": "Iniciado"})


@app.route("/etl/create-phase4-tables", methods=["POST"])
def create_phase4_tables():
    if jobs["phase4"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run, args=("phase4", ["15_create_phase4_tables.py"]), daemon=True
    ).start()
    return jsonify({"mensaje": "Iniciado"})


@app.route("/etl/create-phase5-tables", methods=["POST"])
def create_phase5_tables():
    if jobs["phase5"]["status"] == "running":
        return jsonify({"mensaje": "Ya esta en ejecucion"}), 409
    threading.Thread(
        target=_run, args=("phase5", ["16_create_phase5_tables.py"]), daemon=True
    ).start()
    return jsonify({"mensaje": "Iniciado"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
