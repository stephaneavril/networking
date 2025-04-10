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
    data = conn.execute("SELECT * FROM adivina_participantes").fetchall()
    conn.close()
    return render_template('adivina.html', participantes=data)

if __name__ == '__main__':
    app.run(debug=True)
