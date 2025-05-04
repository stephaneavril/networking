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

def generar_perfil_ia(nombre, respuestas):
    frases = [
        f"{nombre} es una persona que destaca por su habilidad de '{respuestas[0]}'.",
        f"Le apasiona '{respuestas[1]}' y tiene un dato curioso: '{respuestas[2]}'.",
        f"Su película favorita es '{respuestas[3]}' y admira a '{respuestas[4]}'.",
        f"No puede soportar '{respuestas[5]}'.",
        f"Uno de sus libros favoritos es '{respuestas[6]}' y considera imprescindible '{respuestas[7]}'.",
        f"El mejor concierto que ha vivido fue '{respuestas[8]}'.",
    ]
    return " ".join(frases)

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
    puntaje = data.get("puntaje", 0)

    if not isinstance(puntaje, int):
        return jsonify({"error": "Datos inválidos"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM adivina_resultados WHERE nombre_jugador = ?", (jugador,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Ya has completado el reto"}), 400

    cursor.execute("INSERT INTO adivina_resultados (nombre_jugador, aciertos, puntos_extra) VALUES (?, ?, ?)",
                   (jugador, 0, puntaje))
    conn.commit()
    conn.close()

    return jsonify({
        "message": f"🎉 ¡Reto completado! {jugador} obtuvo {puntaje} puntos.",
        "redirect": "/ranking_adivina"
    })

@app.route('/ranking_adivina')
def ranking_adivina():
    if 'jugador' not in session:
        return redirect('/login')
    conn = get_db_connection()
    resultados = conn.execute('''
        SELECT nombre_jugador, puntos_extra, timestamp
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
        if 'activar_solo' in request.form:
            id_a_activar = int(request.form['activar_solo'])
            conn.execute("UPDATE retos SET activo = 0 WHERE nombre LIKE 'MI6%' OR nombre = 'Reto Foto'")
            conn.execute("UPDATE retos SET activo = 1 WHERE id = ?", (id_a_activar,))
            conn.commit()
            flash("✅ Se activó solo ese reto MI6.")
        elif 'reto_id' in request.form and 'activo' in request.form:
            reto_id = request.form.get('reto_id')
            nuevo_estado = request.form.get('activo')
            conn.execute("UPDATE retos SET activo = ? WHERE id = ?", (nuevo_estado, reto_id))
            conn.commit()
            flash("✅ Estado del reto actualizado correctamente.")

    # Datos para el panel
    retos = conn.execute("SELECT * FROM retos").fetchall()
    resultados = conn.execute("SELECT * FROM adivina_resultados ORDER BY puntos_extra DESC").fetchall()
    matches_conexion = conn.execute("SELECT * FROM conexion_alfa_matches").fetchall()

    conn.close()

    return render_template(
        "admin_panel.html",
        retos=retos,
        resultados=resultados,
        matches_conexion=matches_conexion
    )

# -------------------- RETOS FOTO Y MI6 --------------------

def get_reto_id(nombre_reto):
    conn = get_db_connection()
    resultado = conn.execute("SELECT id FROM retos WHERE nombre = ?", (nombre_reto,)).fetchone()
    conn.close()
    return resultado["id"] if resultado else None

@app.route('/reto_foto', methods=['GET', 'POST'])
@app.route('/reto_mi6_v1', methods=['GET', 'POST'])
@app.route('/reto_mi6_v2', methods=['GET', 'POST'])
@app.route('/reto_mi6_v3', methods=['GET', 'POST'])
def reto_foto():
    if 'jugador' not in session:
        return redirect('/login')

    ruta = request.path.strip("/")

    # Definir información para cada reto
    config = {
        "reto_foto": {
            "nombre_reto": "Reto Foto",
            "mensaje": "Sube una foto original que represente tu creatividad. Esta será votada por los demás participantes."
        },
        "reto_mi6_v1": {
            "nombre_reto": "MI6 v1",
            "titulo_visible": "Integridad FARMAPIEL",
            "mensaje": "📸 Toma una foto que represente cómo haces lo correcto incluso cuando nadie está mirando. Una imagen de integridad, valentía o esfuerzo extra."
        },
        "reto_mi6_v2": {
            "nombre_reto": "MI6 v2",
            "titulo_visible": "Transparencia FARMAPIEL",
            "mensaje": "Sube una foto que muestre apertura, honestidad o confianza. La transparencia se refleja cuando actuamos con claridad y coherencia ante los demás."
        },
        "reto_mi6_v3": {
            "nombre_reto": "MI6 v3",
            "titulo_visible": "Calidad FARMAPIEL",
            "mensaje": " Comparte una foto que represente excelencia, atención al detalle o mejora continua. La calidad se demuestra en cada acción bien hecha."
        }
    }

    datos_reto = config.get(ruta)
    if not datos_reto:
        return "❌ Ruta no válida", 404

    reto_id = get_reto_id(datos_reto["nombre_reto"])
    if reto_id is None:
        return "❌ El reto no existe en la base de datos", 500

    conn = get_db_connection()
    correo = session['correo']
    ya_existe = conn.execute(
        "SELECT * FROM reto_foto WHERE correo = ? AND reto_id = ?",
        (correo, reto_id)
    ).fetchone()

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

        conn.execute(
            "INSERT INTO reto_foto (correo, nombre, archivo, reto_id) VALUES (?, ?, ?, ?)",
            (correo, nombre, filename, reto_id)
        )
        conn.commit()
        conn.close()
        flash("✅ Foto subida con éxito. ¡Gracias por participar!")
        return redirect('/')

    conn.close()
    return render_template(
    "reto_foto.html",
    ya_existe=ya_existe,
    mensaje=datos_reto["mensaje"],
    reto_nombre=datos_reto["titulo_visible"] or datos_reto["nombre_reto"]
)

@app.route('/ver_fotos_reto_foto', methods=['GET', 'POST'])
def ver_fotos_reto_foto():
    if 'correo' not in session:
        return redirect('/login')

    correo = session['correo']
    conn = get_db_connection()

    # Obtener el reto activo del tipo 'individual' que se llame MI6 o Reto Foto
    reto = conn.execute('''
        SELECT * FROM retos
        WHERE tipo = 'individual' AND activo = 1
        AND (nombre = 'Reto Foto' OR nombre LIKE 'MI6%')
        ORDER BY id ASC
        LIMIT 1
    ''').fetchone()

    if not reto:
        conn.close()
        return "❌ No hay ningún reto de foto activo en este momento."

    reto_id = reto["id"]
    reto_nombre = reto["nombre"]

    # Verificar si el usuario ya votó en este reto
    fotos_ids = [row["id"] for row in conn.execute("SELECT * FROM reto_foto WHERE reto_id = ?", (reto_id,)).fetchall()]
    votos_previos = conn.execute(
        "SELECT COUNT(*) FROM votos_reto_foto WHERE correo_votante = ? AND id_foto IN (%s)" % ",".join("?"*len(fotos_ids)),
        [correo] + fotos_ids
    ).fetchone()[0] if fotos_ids else 0

    # Procesar votos
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

    fotos = conn.execute("SELECT * FROM reto_foto WHERE reto_id = ?", (reto_id,)).fetchall()
    votos = conn.execute(
        "SELECT * FROM votos_reto_foto WHERE correo_votante = ?",
        (correo,)
    ).fetchall()
    votos_dict = {v['id_foto']: v['puntos'] for v in votos}
    conn.close()

    return render_template(
        "ver_fotos_reto_foto.html",
        fotos=fotos,
        votos=votos_dict,
        ya_voto=(votos_previos > 0),
        reto_nombre=reto_nombre
    )
@app.route('/ver_fotos_mi6_v1', methods=['GET', 'POST'])
@app.route('/ver_fotos_mi6_v2', methods=['GET', 'POST'])
@app.route('/ver_fotos_mi6_v3', methods=['GET', 'POST'])
def ver_fotos_mi6():
    if 'correo' not in session:
        return redirect('/login')

    ruta = request.path.strip("/")
    nombre_reto = {
        "ver_fotos_mi6_v1": "MI6 v1",
        "ver_fotos_mi6_v2": "MI6 v2",
        "ver_fotos_mi6_v3": "MI6 v3"
    }.get(ruta)

    if not nombre_reto:
        return "❌ Ruta inválida", 404

    conn = get_db_connection()
    reto = conn.execute("SELECT * FROM retos WHERE nombre = ?", (nombre_reto,)).fetchone()

    if not reto:
        conn.c@lose()
        return "❌ El reto no existe en la base de datos", 500

    reto_id = reto["id"]
    correo = session["correo"]
    fotos = conn.execute("SELECT * FROM reto_foto WHERE reto_id = ?", (reto_id,)).fetchall()

    # Revisión de votos
    fotos_ids = [f["id"] for f in fotos]
    votos = conn.execute(
        "SELECT * FROM votos_reto_foto WHERE correo_votante = ? AND id_foto IN (%s)" % ",".join("?" * len(fotos_ids)),
        [correo] + fotos_ids if fotos_ids else [correo]
    ).fetchall() if fotos_ids else []

    votos_previos = len(votos)
    votos_dict = {v['id_foto']: v['puntos'] for v in votos}
  # ✅ ✅ ✅ PEGA AQUÍ ESTE BLOQUE
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
        return redirect(request.path)

    conn.close()

    return render_template(
        "ver_fotos_reto_foto.html",
        fotos=fotos,
        votos=votos_dict,
        ya_voto=(votos_previos > 0),
        reto_nombre=nombre_reto
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

    nombre_reto = request.args.get("reto")

    if nombre_reto:
        reto = conn.execute("SELECT * FROM retos WHERE nombre = ?", (nombre_reto,)).fetchone()
    else:
        reto = conn.execute('''
            SELECT * FROM retos
            WHERE tipo = 'individual' AND activo = 1
            AND (nombre = 'Reto Foto' OR nombre LIKE 'MI6%')
            ORDER BY id ASC
            LIMIT 1
        ''').fetchone()

    if not reto:
        conn.close()
        return "❌ No hay reto de foto activo en este momento."

    reto_id = reto['id']
    reto_nombre = reto['nombre']

    ranking = conn.execute('''
        SELECT nombre, archivo, SUM(puntos) as total_puntos
        FROM votos_reto_foto
        JOIN reto_foto ON votos_reto_foto.id_foto = reto_foto.id
        WHERE reto_foto.reto_id = ?
        GROUP BY id_foto
        ORDER BY total_puntos DESC
    ''', (reto_id,)).fetchall()

    conn.close()
    return render_template("ranking_fotos.html", ranking=ranking, reto_nombre=reto_nombre)

@app.route('/reset_reto_foto', methods=['POST'])
def reset_reto_foto():
    conn = get_db_connection()

    # Obtener IDs de todos los retos de foto (Reto Foto + MI6)
    reto_ids = conn.execute(
        "SELECT id FROM retos WHERE nombre = 'Reto Foto' OR nombre LIKE 'MI6%'"
    ).fetchall()
    ids = [str(r["id"]) for r in reto_ids]

    if ids:
        # Borrar votos solo de esas fotos
        foto_ids = conn.execute(
            f"SELECT id FROM reto_foto WHERE reto_id IN ({','.join(['?'] * len(ids))})",
            ids
        ).fetchall()
        foto_ids_int = [str(f["id"]) for f in foto_ids]

        if foto_ids_int:
            conn.execute(
                f"DELETE FROM votos_reto_foto WHERE id_foto IN ({','.join(['?'] * len(foto_ids_int))})",
                foto_ids_int
            )

        # Borrar fotos
        conn.execute(
            f"DELETE FROM reto_foto WHERE reto_id IN ({','.join(['?'] * len(ids))})",
            ids
        )
        conn.commit()

    conn.close()

    # Eliminar archivos del folder
    carpeta = 'static/fotos_reto_foto'
    if os.path.exists(carpeta):
        for archivo in os.listdir(carpeta):
            ruta = os.path.join(carpeta, archivo)
            if os.path.isfile(ruta):
                os.remove(ruta)

    flash("✅ Reto Foto y fotos MI6 reiniciadas correctamente.")
    return redirect('/admin_panel')

# -------------------- CONEXION ALFA --------------------

@app.route('/conexion_alfa')
def conexion_alfa():
    if 'correo' not in session:
        return redirect('/login')
    
    return redirect('/conexion_alfa_match')

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
        WHERE (correo_1 = ? OR correo_2 = ?) AND evidencia IS NULL
        LIMIT 1
    ''', (correo, correo)).fetchone()

    if not match:
        conn.close()
        flash("❌ Ya subieron el video o no tienes un match asignado.")
        return redirect('/conexion_alfa_match')

    if request.method == 'POST':
        archivo = request.files.get('video')
        if archivo and archivo.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            nombre_archivo = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.filename}"
            carpeta = os.path.join('static', 'evidencias_alfa')
            os.makedirs(carpeta, exist_ok=True)
            ruta = os.path.join(carpeta, nombre_archivo)
            
            try:
                archivo.save(ruta)
                conn.execute('''
                    UPDATE conexion_alfa_matches
                    SET evidencia = ?
                    WHERE id = ?
                ''', (nombre_archivo, match['id']))
                conn.commit()
                flash("✅ Video subido exitosamente.")
                return redirect('/conexion_alfa_match')
            except Exception as e:
                flash(f"❌ Error al guardar el video: {e}")
        else:
            flash("❌ Formato de video no válido. Usa mp4, mov, avi o mkv.")
    
    conn.close()
    return render_template('conexion_alfa_subir_video.html', match=match)

@app.route('/conexion_alfa_match')
def conexion_alfa_match():
    if 'correo' not in session:
        return redirect('/login')

    correo = session['correo']
    conn = get_db_connection()

    # Buscar match si existe
    match = conn.execute('''
        SELECT * FROM conexion_alfa_matches 
        WHERE correo_1 = ? OR correo_2 = ?
        LIMIT 1
    ''', (correo, correo)).fetchone()

    feedback_dado = match['feedback'] if match and match['feedback'] is not None else None

    conn.close()
    return render_template(
        "conexion_alfa_match.html",
        match=match,
        sin_match=(match is None),
        feedback_dado=feedback_dado
    )

@app.route('/api/conexion_alfa_match', methods=['POST'])
def api_conexion_alfa_match():
    from sklearn.metrics.pairwise import cosine_similarity

    data = request.get_json()
    participantes = data.get("participantes", [])

    if not participantes or len(participantes) < 2:
        return jsonify({"error": "No hay suficientes participantes"}), 400

    textos, correos, nombres, perfiles = [], [], [], []

    for p in participantes:
        # 🔍 Solo las primeras 7 preguntas
        respuestas = [p.get(f"r{i}", "") or "" for i in range(1, 8)]
        textos.append(" ".join(respuestas))
        correos.append(p["correo"])
        nombres.append(p["nombre"])
        perfiles.append(p.get("perfil_ia", ""))

    vectores = vectorizer_ia.transform(textos).toarray()

    usados = set()
    matches = []

    for i in range(len(correos)):
        if i in usados:
            continue

        mejor_j = None
        mejor_sim = -1

        for j in range(i + 1, len(correos)):
            if j in usados:
                continue
            sim = cosine_similarity([vectores[i]], [vectores[j]])[0][0]
            if sim > mejor_sim:
                mejor_sim = sim
                mejor_j = j

        if mejor_j is not None:
            matches.append({
                "correo_1": correos[i],
                "correo_2": correos[mejor_j],
                "nombre_1": nombres[i],
                "nombre_2": nombres[mejor_j],
                "perfil_1": perfiles[i],
                "perfil_2": perfiles[mejor_j],
                "razon": f"Coincidencia rápida: {round(mejor_sim * 100)}% de similitud basada en respuestas clave."
            })
            usados.add(i)
            usados.add(mejor_j)

    return jsonify({"matches": matches})

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
    import traceback

    conn = get_db_connection()
    try:
        print("📥 Obteniendo datos de participantes...")
        datos = conn.execute("SELECT * FROM conexion_alfa_respuestas").fetchall()

        if len(datos) < 2:
            flash("❌ No hay suficientes participantes para generar matches.")
            return redirect('/admin_panel')

        if len(datos) % 2 != 0:
            flash("⚠️ Número impar de participantes, alguien se quedará sin match.")

        participantes = [dict(row) for row in datos]

        print("⚙️ Ejecutando IA localmente (sin requests)...")
        with app.test_client() as client:
            response = client.post('/api/conexion_alfa_match', json={"participantes": participantes})

        if response.status_code != 200:
            flash("❌ Error al generar matches usando IA interna.")
            return redirect('/admin_panel')

        matches = response.get_json().get("matches", [])
        print(f"🔄 Matches recibidos: {len(matches)}")

        ya_guardados = set(
            tuple(sorted((r["correo_1"], r["correo_2"])))
            for r in conn.execute("SELECT correo_1, correo_2 FROM conexion_alfa_matches").fetchall()
        )

        nuevos = 0
        for match in matches:
            c1, c2 = match["correo_1"], match["correo_2"]
            pareja = tuple(sorted((c1, c2)))
            if pareja not in ya_guardados:
                conn.execute('''
                    INSERT INTO conexion_alfa_matches (
                        correo_1, correo_2, nombre_1, nombre_2, perfil_1, perfil_2, razon_match
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    c1, c2,
                    match["nombre_1"], match["nombre_2"],
                    match["perfil_1"], match["perfil_2"],
                    match.get("razon", "🤖 Este match fue generado por IA con base en afinidades comunes.")
                ))
                nuevos += 1
                ya_guardados.add(pareja)

        conn.commit()
        flash(f"✅ {nuevos} matches generados con éxito.")

    except Exception as e:
        print("❌ ERROR en generar_matches_conexion_alfa:", str(e))
        traceback.print_exc()
        flash("❌ Error interno al generar los matches.")
    finally:
        conn.close()

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

@app.route('/feedback_match', methods=['POST'])
def feedback_match():
    if 'correo' not in session:
        return redirect('/login')

    feedback = int(request.form.get('feedback'))
    match_id = int(request.form.get('match_id'))

    conn = get_db_connection()
    conn.execute("UPDATE conexion_alfa_matches SET feedback = ? WHERE id = ?", (feedback, match_id))
    conn.commit()
    conn.close()
    
    flash("✅ Gracias por tu feedback sobre la conexión.")
    return redirect("/conexion_alfa_match")

# -------------------- RUN --------------------
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_GRUPAL'], exist_ok=True)
    os.makedirs('static/fotos_reto_foto', exist_ok=True)
    app.run(debug=True)
