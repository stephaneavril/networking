import random
import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, flash
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Cargar el modelo y vectorizador IA
with open("modelo_conexion_alfa.pkl", "rb") as f:
    modelo_ia = pickle.load(f)

with open("vectorizer_conexion_alfa.pkl", "rb") as f:
    vectorizer_ia = pickle.load(f)

app = Flask(__name__)
app.secret_key = 'clave-segura'
app.config['UPLOAD_FOLDER'] = 'evidencias'
app.config['UPLOAD_FOLDER_GRUPAL'] = 'evidencias_reto_grupal'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 🔮 IA: Generar perfil semántico
def generar_perfil_ia(nombre, respuestas):
    texto = f"{nombre} es alguien que {respuestas[0]}, le encanta {respuestas[1]}, sueña con {respuestas[2]}, y nunca diría que no a {respuestas[3]}. En su tiempo libre, {respuestas[4]}. Su estilo se define como {respuestas[5]}. Le gustaría {respuestas[6]}."
    return texto

@app.before_request
def make_session_permanent():
    session.permanent = True

# -------------------- LOGIN --------------------
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
        return redirect('/preguntas_post_login')
    return render_template('login.html')

@app.route('/preguntas_post_login', methods=['GET', 'POST'])
def preguntas_post_login():
    if 'correo' not in session:
        return redirect('/login')

    correo = session['correo']
    nombre = session['jugador']
    conn = get_db_connection()

    ya_respondio = conn.execute("SELECT * FROM conexion_alfa_respuestas WHERE correo = ?", (correo,)).fetchone()

    if request.method == 'POST' and not ya_respondio:
        respuestas = [request.form.get(f'r{i}') for i in range(1, 13)]  # r1 a r12
        perfil_ia = generar_perfil_ia(nombre, respuestas)

        conn.execute('''
            INSERT INTO conexion_alfa_respuestas 
            (nombre, correo, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, perfil_ia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nombre, correo, *respuestas, perfil_ia))

        conn.execute('''
            INSERT INTO adivina_participantes 
            (nombre_completo, superpoder, pasion, dato_curioso, pelicula_favorita, actor_favorito, no_soporto,
             mejor_libro, prenda_imprescindible, mejor_concierto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nombre,
            respuestas[0], respuestas[1], respuestas[2], respuestas[3], respuestas[4],
            respuestas[5], respuestas[6], respuestas[7], respuestas[8]
        ))

        conn.commit()
        conn.close()
        flash("✅ ¡Gracias! Tu información ha sido registrada.")
        return redirect('/')

    conn.close()
    return render_template('preguntas_post_login.html', ya_respondio=ya_respondio)

# -------------------- HOME --------------------
@app.route('/')
def index():
    if 'jugador' not in session:
        return redirect('/login')

    conn = get_db_connection()
    retos = conn.execute("SELECT * FROM retos WHERE activo = 1").fetchall()
    conn.close()

    # Conexión a la base de datos del sistema QR
    qr_conn = sqlite3.connect('scan_points.db')
    qr_conn.row_factory = sqlite3.Row
    ranking_qr = qr_conn.execute('''
        SELECT nombre, SUM(puntos) AS total
        FROM registros
        GROUP BY nombre
        ORDER BY total DESC
    ''').fetchall()
    qr_conn.close()

    return render_template('index.html', retos=retos, ranking_qr=ranking_qr)

@app.route('/reset_ranking_qr', methods=['POST'])
def reset_ranking_qr():
    conn_qr = sqlite3.connect('scan_points.db')
    conn_qr.execute("DELETE FROM registros")
    conn_qr.commit()
    conn_qr.close()
    flash("✅ Ranking de Escaneo QR reiniciado correctamente.")
    return redirect('/admin_panel')

# -------------------- RETO ADIVINA --------------------
@app.route('/adivina')
def adivina():
    if 'jugador' not in session:
        return redirect('/login')
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM adivina_participantes").fetchall()
    conn.close()
    participantes = [dict(row) for row in rows]
    random.shuffle(participantes)
    return render_template('adivina.html', participantes=participantes)

@app.route('/adivina_finalizado', methods=['POST'])
def adivina_finalizado():
    if 'jugador' not in session:
        return jsonify({"error": "No autenticado"}), 401

    data = request.get_json()
    jugador = session['jugador']
    aciertos = data.get("aciertos")
    fallos = data.get("fallos", 0)
    puntaje = data.get("puntaje", 0)

    if not isinstance(aciertos, int):
        return jsonify({"error": "Datos inválidos"}), 400

    total_final = puntaje

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adivina_resultados WHERE nombre_jugador = ?", (jugador,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Ya has completado el reto"}), 400

    cursor.execute("INSERT INTO adivina_resultados (nombre_jugador, aciertos, puntos_extra) VALUES (?, ?, ?)",
                   (jugador, aciertos, total_final))
    conn.commit()
    conn.close()

    return jsonify({
        "message": f"🎉 ¡Reto completado! {jugador} ganó {total_final} puntos ({aciertos} aciertos, {fallos} errores).",
        "redirect": "/ranking_adivina"
    })

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
    mi_resultado = conn.execute("SELECT * FROM adivina_resultados WHERE nombre_jugador = ?", (session['jugador'],)).fetchone()
    conn.close()
    return render_template('ranking_adivina.html', resultados=resultados, mi_resultado=mi_resultado)

@app.route('/reset_adivina_quien', methods=['POST'])
def reset_adivina_quien():
    conn = get_db_connection()
    conn.execute("DELETE FROM adivina_resultados")
    conn.commit()
    conn.close()
    flash("✅ Ranking de Adivina Quién reiniciado correctamente.")
    return redirect('/admin_panel')

@app.route('/reset_adivina_participantes', methods=['POST'])
def reset_adivina_participantes():
    conn = get_db_connection()
    conn.execute("DELETE FROM adivina_participantes")
    conn.commit()
    conn.close()
    flash("✅ Participantes de Adivina Quién reiniciados correctamente.")
    return redirect('/admin_panel')

@app.route('/generar_contenido_adivina', methods=['POST'])
def generar_contenido_adivina():
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        participantes = conn.execute('SELECT * FROM adivina_participantes').fetchall()
        conn.close()

        datos = []
        for p in participantes:
            datos.append({
                "nombre_completo": p["nombre_completo"],
                "superpoder": p["superpoder"],
                "pasion": p["pasion"],
                "dato_curioso": p["dato_curioso"],
                "pelicula_favorita": p["pelicula_favorita"],
                "actor_favorito": p["actor_favorito"],
                "no_soporto": p["no_soporto"],
                "mejor_libro": p["mejor_libro"],
                "prenda_imprescindible": p["prenda_imprescindible"],
                "mejor_concierto": p["mejor_concierto"]
            })

        with open('contenido_adivina.json', 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)

        flash(f"✅ Se generó el contenido de Adivina Quién con {len(datos)} participantes.")
    except Exception as e:
        flash(f"❌ Error generando contenido: {e}")
    return redirect('/admin_panel')

@app.route('/respuestas_curiosas')
def respuestas_curiosas():
    conn = get_db_connection()
    respuestas = conn.execute('SELECT * FROM adivina_participantes').fetchall()
    conn.close()

    destacados = []
    for r in respuestas:
        frases = [
            f"🎯 Superpoder: {r['superpoder']}",
            f"🎶 Pasión: {r['pasion']}",
            f"🧠 Dato curioso: {r['dato_curioso']}",
            f"🎬 Película favorita: {r['pelicula_favorita']}",
            f"🎤 Concierto: {r['mejor_concierto']}",
            f"📖 Libro favorito: {r['mejor_libro']}",
            f"👕 Prenda imprescindible: {r['prenda_imprescindible']}",
            f"🤢 No soporta: {r['no_soporto']}"
        ]
        seleccionadas = random.sample(frases, 3)
        destacados.append({
            "nombre": r["nombre_completo"],
            "frases": seleccionadas
        })

    return render_template("respuestas_curiosas.html", destacados=destacados)

# -------------------- SUBIR EVIDENCIA INDIVIDUAL --------------------
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
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    archivo.save(ruta_archivo)
    conn = get_db_connection()
    conn.execute("INSERT INTO evidencias (reto_id, nombre_participante, archivo) VALUES (?, ?, ?)",
                 (reto_id, nombre, nombre_archivo))
    conn.commit()
    conn.close()
    return "✅ Evidencia enviada con éxito"

# -------------------- RETO GRUPAL --------------------
@app.route('/reto_grupal')
def reto_grupal():
    if 'jugador' not in session:
        return redirect('/login')
    conn = get_db_connection()
    reto = conn.execute("SELECT nombre FROM retos_grupales ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    return render_template("reto_grupal.html", reto=reto['nombre'])

@app.route('/guardar_reto_grupal', methods=['POST'])
def guardar_reto_grupal():
    reto = request.form.get('reto')
    nombres = request.form.get('nombres')
    if not reto or not nombres:
        return "❌ Faltan datos", 400
    conn = get_db_connection()
    conn.execute("INSERT INTO participaciones_grupales (reto, nombres_participantes) VALUES (?, ?)", (reto, nombres))
    conn.commit()
    conn.close()
    flash("✅ ¡Gracias! Tu participación fue registrada.")
    return redirect('/')

# -------------------- ADMIN PANEL --------------------
@app.route('/admin_panel', methods=['GET', 'POST'])
def admin_panel():
    conn = get_db_connection()
    
    # Activar/desactivar retos
    if request.method == 'POST':
        reto_id = request.form.get('reto_id')
        nuevo_estado = request.form.get('activo')
        conn.execute("UPDATE retos SET activo = ? WHERE id = ?", (nuevo_estado, reto_id))
        conn.commit()

    # Cargar datos necesarios
    retos = conn.execute("SELECT * FROM retos").fetchall()
    resultados = conn.execute("SELECT * FROM adivina_resultados ORDER BY puntos_extra DESC").fetchall()
    participaciones = conn.execute("SELECT * FROM participaciones_grupales ORDER BY timestamp DESC").fetchall()
    matches_conexion = conn.execute("SELECT * FROM conexion_alfa_matches WHERE evidencia IS NOT NULL").fetchall()
    
    conn.close()

    return render_template(
        "admin_panel.html",
        retos=retos,
        resultados=resultados,
        participaciones=participaciones,
        matches_conexion=matches_conexion
    )

@app.route('/calificar/<int:id>', methods=['POST'])
def calificar(id):
    calificacion = request.form.get('calificacion')
    comentario = request.form.get('comentario')
    conn = get_db_connection()
    conn.execute("UPDATE participaciones_grupales SET calificacion = ?, comentario = ? WHERE id = ?",
                 (calificacion, comentario, id))
    conn.commit()
    conn.close()
    return redirect('/admin_panel')

# -------------------- RETO FOTO --------------------
@app.route('/reto_foto', methods=['GET', 'POST'])
def reto_foto():
    if 'jugador' not in session:
        return redirect('/login')
    conn = get_db_connection()
    correo = session['correo']
    ya_existe = conn.execute("SELECT * FROM reto_foto WHERE correo = ?", (correo,)).fetchone()
    if request.method == 'POST':
        if ya_existe:
            conn.close()
            return "❌ Ya has subido una foto para este reto."
        archivo = request.files.get('foto')
        if not archivo:
            return "❌ No se proporcionó ninguna imagen."
        nombre = session['jugador']
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.filename}"
        path = os.path.join('static/fotos_reto_foto', filename)
        os.makedirs('static/fotos_reto_foto', exist_ok=True)
        archivo.save(path)
        conn.execute("INSERT INTO reto_foto (correo, nombre, archivo) VALUES (?, ?, ?)", (correo, nombre, filename))
        conn.commit()
        conn.close()
        flash("✅ Foto subida con éxito. ¡Gracias por participar!")
        return redirect('/')
    conn.close()
    return render_template("reto_foto.html", ya_existe=ya_existe)

@app.route('/ver_fotos_reto_foto', methods=['GET', 'POST'])
def ver_fotos_reto_foto():
    if 'correo' not in session:
        return redirect('/login')

    correo = session['correo']
    conn = get_db_connection()

    # Verifica si ya votó
    votos_previos = conn.execute(
        "SELECT COUNT(*) FROM votos_reto_foto WHERE correo_votante = ?", (correo,)
    ).fetchone()[0]

    if request.method == 'POST' and votos_previos == 0:
        total_puntos = sum(int(v) for v in request.form.values() if v.isdigit())
        if total_puntos > 3:
            conn.close()
            return "❌ Solo puedes asignar hasta 3 puntos en total.", 400

        for key, val in request.form.items():
            if key.startswith("foto_") and val:
                id_foto = int(key.split("_")[1])
                puntos = int(val)
                try:
                    conn.execute(
                        "INSERT INTO votos_reto_foto (correo_votante, id_foto, puntos) VALUES (?, ?, ?)",
                        (correo, id_foto, puntos)
                    )
                except sqlite3.IntegrityError:
                    continue
        conn.commit()
        flash("✅ ¡Tus votos han sido registrados!")
        return redirect('/ver_fotos_reto_foto')

    fotos = conn.execute("SELECT * FROM reto_foto").fetchall()
    votos = conn.execute("SELECT * FROM votos_reto_foto WHERE correo_votante = ?", (correo,)).fetchall()
    votos_dict = {v['id_foto']: v['puntos'] for v in votos}
    conn.close()

    return render_template(
        "ver_fotos_reto_foto.html",
        fotos=fotos,
        votos=votos_dict,
        ya_voto=(votos_previos > 0)
    )
@app.route('/votar_fotos', methods=['POST'])
def votar_fotos():
    if 'correo' not in session:
        return redirect('/login')
    correo_votante = session['correo']
    votos = request.form
    total_puntos = sum([int(v) for v in votos.values() if v.isdigit()])
    if total_puntos != 3:
        return "❌ Debes asignar exactamente 3 puntos", 400
    conn = get_db_connection()
    for id_foto, puntos in votos.items():
        if puntos and puntos.isdigit():
            conn.execute('''
                INSERT OR REPLACE INTO votos_reto_foto (correo_votante, id_foto, puntos)
                VALUES (?, ?, ?)
            ''', (correo_votante, int(id_foto), int(puntos)))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/ranking_fotos')
def ranking_fotos():
    if 'jugador' not in session:
        return redirect('/login')
    conn = get_db_connection()
    ranking = conn.execute('''
        SELECT nombre, archivo, SUM(puntos) as total_puntos
        FROM votos_reto_foto
        JOIN reto_foto ON votos_reto_foto.id_foto = reto_foto.id
        GROUP BY id_foto
        ORDER BY total_puntos DESC
    ''').fetchall()
    conn.close()
    return render_template("ranking_fotos.html", ranking=ranking)

@app.route('/reset_reto_foto', methods=['POST'])
def reset_reto_foto():
    # 1. Borrar registros de la base de datos
    conn = get_db_connection()
    conn.execute("DELETE FROM votos_reto_foto")
    conn.execute("DELETE FROM reto_foto")
    conn.commit()
    conn.close()

    # 2. Borrar archivos de la carpeta
    carpeta = 'static/fotos_reto_foto'
    for archivo in os.listdir(carpeta):
        ruta = os.path.join(carpeta, archivo)
        if os.path.isfile(ruta):
            os.remove(ruta)

    flash("✅ Reto Foto reiniciado correctamente.")
    return redirect('/admin_panel')

# -------------------- CONEXION ALFA --------------------

@app.route('/conexion_alfa', methods=['GET', 'POST'])
def conexion_alfa():
    if 'correo' not in session:
        return redirect('/login')

    correo = session['correo']
    nombre = session['jugador']
    conn = get_db_connection()

    ya_existe = conn.execute("SELECT * FROM conexion_alfa_respuestas WHERE correo = ?", (correo,)).fetchone()

    if request.method == 'POST' and not ya_existe:
        respuestas = [request.form.get(f'r{i}') for i in range(1, 8)]

        # Aquí simularemos un perfil de IA como placeholder
        perfil_ia = generar_perfil_ia(nombre, respuestas)

        conn.execute('''
            INSERT INTO conexion_alfa_respuestas (nombre, correo, r1, r2, r3, r4, r5, r6, r7, perfil_ia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nombre, correo, *respuestas, perfil_ia))
        conn.commit()
        conn.close()
        flash("✅ ¡Gracias! Tu perfil ha sido generado.")
        return redirect('/conexion_alfa_mi_perfil')

    conn.close()
    return render_template('conexion_alfa_form.html', ya_existe=ya_existe)

@app.route('/conexion_alfa_mi_perfil')
def conexion_alfa_mi_perfil():
    if 'correo' not in session:
        return redirect('/login')

    conn = get_db_connection()
    perfil = conn.execute("SELECT * FROM conexion_alfa_respuestas WHERE correo = ?", (session['correo'],)).fetchone()
    conn.close()
    return render_template("conexion_alfa_perfil.html", perfil=perfil)

@app.route('/conexion_alfa_matches', methods=['GET'])
def conexion_alfa_matches():
    if 'correo' not in session:
        return redirect('/login')

    correo_usuario = session['correo']
    conn = get_db_connection()
    datos = conn.execute("SELECT * FROM conexion_alfa_respuestas").fetchall()

    textos = []
    correos = []
    nombres = []
    perfiles = []
    for row in datos:
        respuestas = [row[f"r{i}"] for i in range(1, 8)]
        texto = " ".join(respuestas)
        textos.append(texto)
        correos.append(row["correo"])
        nombres.append(row["nombre"])
        perfiles.append(row["perfil_ia"])

    vectores = vectorizer_ia.transform(textos)
    sim_matrix = cosine_similarity(vectores)

    # Evitar duplicados y guardar matches nuevos
    ya_guardados = conn.execute("SELECT correo_1, correo_2 FROM conexion_alfa_matches").fetchall()
    ya_guardados_set = set((min(r["correo_1"], r["correo_2"]), max(r["correo_1"], r["correo_2"])) for r in ya_guardados)

    for i in range(len(correos)):
        for j in range(i+1, len(correos)):
            correo1, correo2 = correos[i], correos[j]
            nombre1, nombre2 = nombres[i], nombres[j]
            perfil1, perfil2 = perfiles[i], perfiles[j]
            pareja = (min(correo1, correo2), max(correo1, correo2))
            if pareja not in ya_guardados_set:
                conn.execute('''
                    INSERT INTO conexion_alfa_matches (correo_1, correo_2, nombre_1, nombre_2, perfil_1, perfil_2)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (correo1, correo2, nombre1, nombre2, perfil1, perfil2))
                conn.commit()

    matches = conn.execute('''
        SELECT * FROM conexion_alfa_matches
        WHERE correo_1 = ? OR correo_2 = ?
    ''', (correo_usuario, correo_usuario)).fetchall()

    # Métricas IA
    feedbacks = conn.execute("SELECT feedback FROM conexion_alfa_matches WHERE feedback IS NOT NULL").fetchall()
    total = len(feedbacks)
    positivos = sum(f["feedback"] == 1 for f in feedbacks)
    negativos = sum(f["feedback"] == 0 for f in feedbacks)

    if total > 0:
        accuracy = round(positivos / total, 2)
        precision = round(positivos / (positivos + negativos), 2) if (positivos + negativos) > 0 else 0
        recall = round(positivos / total, 2)
        f1 = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0
    else:
        accuracy = precision = recall = f1 = None

    conn.close()
    return render_template("conexion_alfa_matches.html", matches=matches,
                           accuracy=accuracy, precision=precision, recall=recall, f1=f1)

@app.route('/confirmar_match', methods=['POST'])
def confirmar_match():
    match_id = request.form.get('match_id')
    respuesta = int(request.form.get('respuesta'))
    conn = get_db_connection()
    conn.execute("UPDATE conexion_alfa_matches SET feedback = ? WHERE id = ?", (respuesta, match_id))
    conn.commit()
    conn.close()
    flash("✅ ¡Gracias por tu respuesta!")
    return redirect('/conexion_alfa_matches')

@app.route('/subir_video_match', methods=['GET', 'POST'])
def subir_video_match():
    if 'correo' not in session:
        return redirect('/login')
    
    correo = session['correo']
    conn = get_db_connection()
    match = conn.execute('''
        SELECT * FROM conexion_alfa_matches 
        WHERE correo_1 = ? OR correo_2 = ?
    ''', (correo, correo)).fetchone()

    if not match:
        conn.close()
        flash("❌ No tienes un match asignado.")
        return redirect('/')

    if request.method == 'POST':
        archivo = request.files.get('video')
        if archivo:
            nombre_archivo = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.filename}"
            ruta = os.path.join('static/evidencias_alfa', nombre_archivo)
            archivo.save(ruta)

            conn.execute('''
                UPDATE conexion_alfa_matches
                SET evidencia = ?
                WHERE id = ?
            ''', (nombre_archivo, match['id']))
            conn.commit()
            flash("✅ Video subido exitosamente.")
            return redirect('/conexion_alfa_mi_perfil')
    
    conn.close()
    return render_template('conexion_alfa_subir_video.html', match=match)

@app.route('/conexion_alfa_match')
def conexion_alfa_match():
    if 'correo' not in session:
        return redirect('/login')

    correo = session['correo']
    conn = get_db_connection()

    match = conn.execute('''
        SELECT * FROM conexion_alfa_matches
        WHERE correo_1 = ? OR correo_2 = ?
        LIMIT 1
    ''', (correo, correo)).fetchone()

    conn.close()

    if not match:
        return "❌ Aún no tienes match asignado. Espera a que el sistema los genere."

    return render_template('conexion_alfa_match.html', match=match)

@app.route('/reset_conexion_alfa', methods=['POST'])
def reset_conexion_alfa():
    conn = get_db_connection()

    # Borrar registros de la base de datos
    conn.execute("DELETE FROM conexion_alfa_matches")
    conn.execute("DELETE FROM conexion_alfa_respuestas")
    conn.commit()
    conn.close()

    # Borrar archivos de evidencia de video
    carpeta = 'static/evidencias_alfa'
    if os.path.exists(carpeta):
        for archivo in os.listdir(carpeta):
            ruta = os.path.join(carpeta, archivo)
            if os.path.isfile(ruta):
                os.remove(ruta)

    flash("✅ Conexión Alfa reiniciado correctamente.")
    return redirect('/admin_panel')

@app.route('/generar_matches_conexion_alfa', methods=['POST'])
def generar_matches_conexion_alfa():
    conn = get_db_connection()
    datos = conn.execute("SELECT * FROM conexion_alfa_respuestas").fetchall()

    textos = []
    correos = []
    nombres = []
    perfiles = []

    for row in datos:
        respuestas = [row[f"r{i}"] for i in range(1, 8)]
        texto = " ".join(respuestas)
        textos.append(texto)
        correos.append(row["correo"])
        nombres.append(row["nombre"])
        perfiles.append(row["perfil_ia"])

    vectores = vectorizer_ia.transform(textos)
    sim_matrix = cosine_similarity(vectores)

    # Evitar duplicados
    ya_guardados = conn.execute("SELECT correo_1, correo_2 FROM conexion_alfa_matches").fetchall()
    ya_guardados_set = set((min(r["correo_1"], r["correo_2"]), max(r["correo_1"], r["correo_2"])) for r in ya_guardados)

    nuevos_matches = 0

    for i in range(len(correos)):
        for j in range(i + 1, len(correos)):
            correo1, correo2 = correos[i], correos[j]
            nombre1, nombre2 = nombres[i], nombres[j]
            perfil1, perfil2 = perfiles[i], perfiles[j]
            pareja = (min(correo1, correo2), max(correo1, correo2))

            if pareja not in ya_guardados_set:
                conn.execute('''
                    INSERT INTO conexion_alfa_matches (correo_1, correo_2, nombre_1, nombre_2, perfil_1, perfil_2)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (correo1, correo2, nombre1, nombre2, perfil1, perfil2))
                nuevos_matches += 1

    conn.commit()

    # Métricas
    feedbacks = conn.execute("SELECT feedback FROM conexion_alfa_matches WHERE feedback IS NOT NULL").fetchall()
    total = len(feedbacks)
    positivos = sum(f["feedback"] == 1 for f in feedbacks)
    negativos = sum(f["feedback"] == 0 for f in feedbacks)

    if total > 0:
        accuracy = round(positivos / total, 2)
        precision = round(positivos / (positivos + negativos), 2) if (positivos + negativos) > 0 else 0
        recall = round(positivos / total, 2)
        f1 = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0
    else:
        accuracy = precision = recall = f1 = None

    conn.close()

    flash(f"✅ {nuevos_matches} matches generados con IA. Métricas: Accuracy={accuracy}, Precision={precision}, Recall={recall}, F1={f1}")
    return redirect('/admin_panel')

@app.route('/forzar_matches_conexion_alfa', methods=['POST'])
def forzar_matches_conexion_alfa():
    import subprocess
    subprocess.call(["python", "generar_matches_conexion_alfa.py"])
    flash("✅ Matches de Conexión Alfa generados correctamente.")
    return redirect('/admin_panel')

@app.route('/reset_datos_participantes', methods=['POST'])
def reset_datos_participantes():
    conn = get_db_connection()
    conn.execute("DELETE FROM conexion_alfa_respuestas")
    conn.execute("DELETE FROM adivina_participantes")
    conn.commit()
    conn.close()
    flash("✅ Datos de participantes reiniciados. Todos podrán volver a llenar el formulario.")
    return redirect('/admin_panel')

@app.route('/eliminar_todos_los_jugadores', methods=['POST'])
def eliminar_todos_los_jugadores():
    conn = get_db_connection()
    conn.execute("DELETE FROM jugadores")
    conn.execute("DELETE FROM conexion_alfa_respuestas")
    conn.execute("DELETE FROM conexion_alfa_matches")
    conn.execute("DELETE FROM adivina_resultados")
    conn.execute("DELETE FROM adivina_participantes")
    conn.commit()
    conn.close()
    session.clear()  # Limpiar sesión activa
    flash("✅ Se eliminaron todos los jugadores, respuestas y sesiones.")
    return redirect('/admin_panel')

# -------------------- RUN --------------------
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_GRUPAL'], exist_ok=True)
    os.makedirs('static/fotos_reto_foto', exist_ok=True)
    app.run(debug=True)
