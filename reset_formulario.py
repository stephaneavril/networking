import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Borrar y recrear tabla conexion_alfa_respuestas
cursor.execute('DROP TABLE IF EXISTS conexion_alfa_respuestas')
cursor.execute('''
CREATE TABLE conexion_alfa_respuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correo TEXT,
    nombre TEXT,
    r1 TEXT,
    r2 TEXT,
    r3 TEXT,
    r4 TEXT,
    r5 TEXT,
    r6 TEXT,
    r7 TEXT,
    r8 TEXT,
    r9 TEXT,
    r10 TEXT,
    r11 TEXT,
    r12 TEXT,
    perfil_ia TEXT
)
''')

# Borrar y recrear tabla adivina_participantes
cursor.execute('DROP TABLE IF EXISTS adivina_participantes')
cursor.execute('''
CREATE TABLE adivina_participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT,
    superpoder TEXT,
    pasion TEXT,
    dato_curioso TEXT,
    pelicula_favorita TEXT,
    actor_favorito TEXT,
    no_soporto TEXT,
    mejor_libro TEXT,
    prenda_imprescindible TEXT,
    mejor_concierto TEXT
)
''')

conn.commit()
conn.close()
print("✅ Tablas actualizadas correctamente.")
