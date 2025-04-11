from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave-segura'
app.config['UPLOAD_FOLDER'] = 'evidencias'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['jugador'] = request.form['nombre']
        session['correo'] = request.form['correo']
        return redirect('/')
    return render_template('login.html')

@app.route('/')
def index():
    if 'jugador' not in session:
        return redirect('/login')
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

    nombre_archivo = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.filename}"
    ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
    archivo.save(ruta_archivo)

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
    if 'jugador' not in session:
        return redirect('/login')
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM adivina_participantes").fetchall()
    conn.close()
    participantes = [dict(row) for row in rows]
    return render_template('adivina.html', participantes=participantes)

@app.route('/adivina_finalizado', methods=['POST'])
def adivina_finalizado():
    if 'jugador' not in session:
        return jsonify({"error": "Sesión no válida"}), 401

    data = request.get_json()
    jugador = session['jugador']
    aciertos = data.get("aciertos")

    if not isinstance(aciertos, int):
        return jsonify({"error": "Datos inválidos"}), 400

    puntos_por_acierto = 3
    puntos_totales = aciertos * puntos_por_acierto

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM adivina_resultados WHERE nombre_jugador = ?", (jugador,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Ya has completado el reto"}), 400

    cursor.execute("SELECT COUNT(*) FROM adivina_resultados")
    finalizados = cursor.fetchone()[0]

    bonus = max(500 - (finalizados * 50), 0)
    total_final = puntos_totales + bonus

    cursor.execute(
        "INSERT INTO adivina_resultados (nombre_jugador, aciertos, puntos_extra) VALUES (?, ?, ?)",
        (jugador, aciertos, total_final)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message": f"🎉 ¡Reto completado! {jugador} ganó {total_final} puntos ({aciertos} aciertos + {bonus} bonus)."
    })

@app.route('/adivina_ranking')
def adivina_ranking():
    conn = get_db_connection()
    resultados = conn.execute(
        "SELECT nombre_jugador, aciertos, puntos_extra, timestamp FROM adivina_resultados ORDER BY puntos_extra DESC"
    ).fetchall()
    conn.close()
    return render_template('adivina_ranking.html', resultados=resultados)

@app.route('/ranking_adivina')
def ranking_adivina():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM adivina_resultados ORDER BY puntos DESC")
    rows = cursor.fetchall()
    conn.close()

    return render_template('ranking_adivina.html', resultados=rows, jugador=session.get('jugador'))

if __name__ == '__main__':
    app.run(debug=True)
