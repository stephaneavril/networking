import sqlite3

# Conectar o crear la base de datos
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Tabla de retos
cursor.execute('''
CREATE TABLE IF NOT EXISTS retos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    puntos INTEGER NOT NULL,
    tipo TEXT CHECK(tipo IN ('individual', 'equipo')) NOT NULL,
    activo INTEGER DEFAULT 0
)
''')

# Tabla de evidencias
cursor.execute('''
CREATE TABLE IF NOT EXISTS evidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reto_id INTEGER NOT NULL,
    nombre_participante TEXT NOT NULL,
    archivo TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# Tabla de jugadores
cursor.execute('''
CREATE TABLE IF NOT EXISTS jugadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE
)
''')

# Participantes para "Adivina Quién"
cursor.execute('''
CREATE TABLE IF NOT EXISTS adivina_participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    superpoder TEXT,
    pasion TEXT,
    dato_curioso TEXT,
    pelicula TEXT,
    actor TEXT,
    no_soporto TEXT
)
''')

# Resultados para "Adivina Quién"
cursor.execute('''
CREATE TABLE IF NOT EXISTS adivina_resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_jugador TEXT NOT NULL,
    aciertos INTEGER NOT NULL,
    puntos_extra INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# Retos activos de ejemplo
retos = [
    ('Furthest Distance', 1, 'individual', 1),
    ('Nerd Off', 1, 'individual', 1),
    ('Tongue Twister', 1, 'individual', 1),
    ('Reto Grupal Random', 2, 'equipo', 1),
    ('Group Photo', 3, 'equipo', 1),
    ('Circle of Life', 2, 'equipo', 1),
    ('Vote on Media', 1, 'individual', 0),
    ('Profile Deets', 1, 'individual', 0),
    ('Sporty Spice', 1, 'equipo', 0),
    ('Adivina Quién', 3, 'individual', 1)
]
cursor.executemany("INSERT INTO retos (nombre, puntos, tipo, activo) VALUES (?, ?, ?, ?)", retos)

# Participantes para probar "Adivina Quién"
participantes = [
    ("Lucía Ramírez", "Resolver conflictos sin drama", "Escalar montañas", "Toco el ukulele en bodas", "Amélie", "Emma Stone", "El aguacate"),
    ("Carlos Méndez", "Memoria fotográfica", "Cocinar ramen", "Me sé todos los diálogos de Shrek", "El Padrino", "Al Pacino", "Friends"),
    ("Ana Torres", "Empatía sin esfuerzo", "Bailar salsa", "Colecciono plantas raras", "Intensamente", "Margot Robbie", "Café")
]
cursor.executemany('''
    INSERT INTO adivina_participantes (
        nombre_completo, superpoder, pasion, dato_curioso, pelicula, actor, no_soporto
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
''', participantes)

# Tabla de retos grupales posibles
cursor.execute("""
CREATE TABLE IF NOT EXISTS retos_grupales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
)
""")

# Tabla de registros de participación
cursor.execute("""
CREATE TABLE IF NOT EXISTS participaciones_grupales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reto TEXT,
    nombres_participantes TEXT,
    archivo TEXT,
    calificacion INTEGER DEFAULT 0,
    comentario TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# Insertar retos si no existen
retos = [('Jenga',), ('Conecta 4',), ('Corn Hole',)]
cursor.executemany("INSERT INTO retos_grupales (nombre) VALUES (?)", retos)

conn.commit()
conn.close()
print("✅ Base de datos actualizada para reto grupal.")
