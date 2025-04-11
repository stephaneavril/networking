from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'evidencias'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    retos = conn.execute("SELECT * FROM retos WHERE activo = 1").fetchall()
    conn.close()
    return render_template('index.html', retos=retos)

@app.route('/subir_evidencia', methods=['POST'])
def subir_evidencia():
    nombre = request.form.get('nombre')
    reto_id = request.form.get('reto_id')
    archivo = request.files.get('archivo')

    if not nombre or not archivo or not reto_id:
        return "❌ Faltan datos", 400

    # Guardar archivo
    nombre_archivo = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.filename}"
    ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
    archivo.save(ruta_archivo)

    # Guardar en base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO evidencias (reto_id, nombre_participante, archivo) VALUES (?, ?, ?)",
        (reto_id, nombre, nombre_archivo)
    )
    conn.commit()
    conn.close()

    return "✅ Evidencia enviada con éxito"

@app.route('/adivina')
def adivina():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM adivina_participantes").fetchall()
    conn.close()
    participantes = [dict(row) for row in rows]  # 👈 convierte a diccionarios
    return render_template('adivina.html', participantes=participantes)

@app.route('/adivina_finalizado', methods=['POST'])
def adivina_finalizado():
    data = request.get_json()
    jugador = data.get("jugador")
    aciertos = data.get("aciertos")

    if not jugador or not isinstance(aciertos, int):
        return jsonify({"error": "Datos inválidos"}), 400

    puntos_por_acierto = 3
    puntos_totales = aciertos * puntos_por_acierto

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar si ya jugó
    cursor.execute("SELECT * FROM adivina_resultados WHERE nombre = ?", (jugador,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Ya has completado el reto"}), 400

    # Contar jugadores ya finalizados
    cursor.execute("SELECT COUNT(*) FROM adivina_resultados")
    finalizados = cursor.fetchone()[0]

    # Cálculo de puntos extra
    bonus = max(500 - (finalizados * 50), 0)
    total_final = puntos_totales + bonus

    # Insertar resultado
    cursor.execute(
        "INSERT INTO adivina_resultados (nombre, aciertos, puntos, bonus) VALUES (?, ?, ?, ?)",
        (jugador, aciertos, total_final, bonus)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": f"🎉 ¡Reto completado! {jugador} ganó {total_final} puntos ({aciertos} aciertos + {bonus} bonus)."})

if __name__ == '__main__':
    app.run(debug=True)
