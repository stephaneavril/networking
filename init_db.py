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
print("✅ Base de datos creada con los retos.")
