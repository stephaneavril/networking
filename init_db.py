import sqlite3

# Conectar o crear la base de datos
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Crear tabla de retos
cursor.execute('''
CREATE TABLE IF NOT EXISTS retos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    puntos INTEGER NOT NULL,
    tipo TEXT CHECK(tipo IN ('individual', 'equipo')) NOT NULL,
    activo INTEGER DEFAULT 0
)
''')

# Crear tabla de evidencias
cursor.execute('''
CREATE TABLE IF NOT EXISTS evidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reto_id INTEGER NOT NULL,
    nombre_participante TEXT NOT NULL,
    archivo TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

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


# Insertar retos de ejemplo
retos = [
    ('Furthest Distance', 1, 'individual', 1),
    ('Nerd Off', 1, 'individual', 1),
    ('Tongue Twister', 1, 'individual', 1),
    ('Social', 2, 'equipo', 1),
    ('Group Photo', 3, 'equipo', 1),
    ('Circle of Life', 2, 'equipo', 1),
    ('Vote on Media', 1, 'individual', 0),
    ('Profile Deets', 1, 'individual', 0),
    ('Sporty Spice', 1, 'equipo', 0)
]

cursor.executemany("INSERT INTO retos (nombre, puntos, tipo, activo) VALUES (?, ?, ?, ?)", retos)

conn.commit()
conn.close()
print("✅ Base de datos creada con los retos y tabla de evidencias.")
