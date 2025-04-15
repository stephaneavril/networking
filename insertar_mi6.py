import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

retos_mi6 = [
    ('MI6 v1', 3, 'individual', 1),  # Día 1, Activo
    ('MI6 v2', 3, 'individual', 0),  # Día 2, Inactivo
    ('MI6 v3', 3, 'individual', 0),  # Día 3, Inactivo
]

for nombre, puntos, tipo, activo in retos_mi6:
    cursor.execute("SELECT COUNT(*) FROM retos WHERE nombre = ?", (nombre,))
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO retos (nombre, puntos, tipo, activo) VALUES (?, ?, ?, ?)",
            (nombre, puntos, tipo, activo)
        )
        print(f"✅ Insertado: {nombre}")
    else:
        print(f"🔁 Ya existe: {nombre}")

conn.commit()
conn.close()
