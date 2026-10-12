import os
import time

import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)


def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def init_db(retries=10):
    """Crea la tabla si no existe, reintentando mientras la BD arranca."""
    for intento in range(1, retries + 1):
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS registros (
                        id SERIAL PRIMARY KEY,
                        mensaje TEXT NOT NULL,
                        creado_en TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            print("Base de datos lista.", flush=True)
            return
        except psycopg2.OperationalError as e:
            print(f"BD no disponible (intento {intento}): {e}", flush=True)
            time.sleep(3)
    raise RuntimeError("No se pudo conectar a la base de datos")


@app.get("/api/health")
def health():
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
        return jsonify(status="ok", backend="Flask", database=version)
    except Exception as e:
        return jsonify(status="error", detalle=str(e)), 500


@app.get("/api/registros")
def listar_registros():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, mensaje, creado_en FROM registros ORDER BY id DESC")
        filas = cur.fetchall()
    return jsonify(
        [{"id": f[0], "mensaje": f[1], "creado_en": f[2].isoformat()} for f in filas]
    )


@app.post("/api/registros")
def crear_registro():
    datos = request.get_json(silent=True) or {}
    mensaje = (datos.get("mensaje") or "").strip()
    if not mensaje:
        return jsonify(error="El campo 'mensaje' es obligatorio"), 400
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO registros (mensaje) VALUES (%s) RETURNING id, creado_en",
            (mensaje,),
        )
        id_, creado_en = cur.fetchone()
    return jsonify(id=id_, mensaje=mensaje, creado_en=creado_en.isoformat()), 201


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
