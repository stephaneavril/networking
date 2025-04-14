import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.executescript("""
-- Reiniciar tabla de Conexión Alfa (IA)
DROP TABLE IF EXISTS conexion_alfa_respuestas;

CREATE TABLE conexion_alfa_respuestas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT,
  correo TEXT UNIQUE,
  r1 TEXT,
  r2 TEXT,
  r3 TEXT,
  r4 TEXT,
  r5 TEXT,
  r6 TEXT,
  r7 TEXT,
  r8 TEXT,
  perfil_ia TEXT
);

-- Reiniciar tabla de Adivina Quién
DROP TABLE IF EXISTS adivina_participantes;

CREATE TABLE adivina_participantes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre_completo TEXT,
  superpoder TEXT,
  pasion TEXT,
  dato_curioso TEXT,
  pelicula_favorita TEXT,
  actor_favorito TEXT,
  no_soporto TEXT
);
""")

conn.commit()
conn.close()
print("✅ Tablas reiniciadas correctamente.")
