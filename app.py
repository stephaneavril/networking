from flask import Flask, render_template, request, jsonify, session, redirect
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

# Login del usuario
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']

        session['jugador'] = nombre
        session['correo'] = correo

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jugadores WHERE correo = ?", (correo,))
        existente = cursor.fetchone()

        if not existente:
            cursor.execute("INSERT INTO jugadores (nombre, correo) VALUES (?, ?)", (nombre, correo))
            conn.commit()
        conn.close()

        return redirect('/')

    return render_template('login.html')

@app.before_request
def make_session_permanent():
    session.permanent = True

# Página principal
@app.route('/')
def index():
    if 'jugador' not in session:
        return redirect('/login')
    conn = get_db_connection()
    retos = conn.execute("SELECT * FROM retos WHERE activo = 1").fetchall()
    conn.close()
    return render_template('index.html', retos=retos)

# Reto Adivina Quién
@app.route('/adivina')
def adivina():
    if 'jugador' not in session:
        return redirect('/login')
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM adivina_participantes").fetchall()
    conn.close()
    participantes = [dict(row) for row in rows]
    return render_template('adivina.html', participantes=participantes)

# Guardar resultados Adivina Quién
@app.route('/adivina_finalizado', methods=['POST'])
def adivina_finalizado():
    if 'jugador' not in session:
        return jsonify({"error": "No autenticado"}), 401

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
        "message": f"🎉 ¡Reto completado! {jugador} ganó {total_final} puntos ({aciertos} aciertos + {bonus} bonus).",
        "redirect": "/ranking_adivina"
    })

# Ranking Adivina Quién
@app.route('/ranking_adivina')
def ranking_adivina():
    if 'jugador' not in session:
        return redirect('/login')

    conn = get_db_connection()
    resultados = conn.execute('''
        SELECT nombre_jugador, aciertos, puntos_extra, timestamp
        FROM adivina_resultados
        ORDER BY puntos_extra DESC, timestamp ASC
    ''').fetchall()

    mi_resultado = conn.execute(
        "SELECT * FROM adivina_resultados WHERE nombre_jugador = ?", (session['jugador'],)
    ).fetchone()

    conn.close()
    return render_template('ranking_adivina.html', resultados=resultados, mi_resultado=mi_resultado)

# Subir evidencia
@app.route('/subir_evidencia', methods=['POST'])
def subir_evidencia():
    if 'jugador' not in session:
        return redirect('/login')

    nombre = session['jugador']
    reto_id = request.form.get('reto_id')
    archivo = request.files.get('archivo')

    if not archivo or not reto_id:
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

if __name__ == '__main__':
    app.run(debug=True)
