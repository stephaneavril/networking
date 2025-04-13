import sqlite3

# Datos del reto nuevo
nuevo_nombre = "Conexión Alfa"
tipo = "individual"
puntos = 0
activo = 1

# Conectar a la base de datos
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Verificar si existe un reto duplicado con el mismo nombre
cursor.execute("SELECT * FROM retos WHERE nombre = ?", (nuevo_nombre,))
existe = cursor.fetchone()

if existe:
    print(f"⚠️ El reto '{nuevo_nombre}' ya existe en la base de datos.")
else:
    # Buscar y reemplazar el reto "Nerd Off"
    cursor.execute("SELECT id FROM retos WHERE nombre = ?", ("Nerd Off",))
    nerd_off = cursor.fetchone()
    if nerd_off:
        cursor.execute("UPDATE retos SET nombre = ?, tipo = ?, puntos = ?, activo = ? WHERE id = ?",
                       (nuevo_nombre, tipo, puntos, activo, nerd_off[0]))
        print("✅ Se reemplazó 'Nerd Off' por 'Conexión Alfa'")
    else:
        cursor.execute("INSERT INTO retos (nombre, tipo, puntos, activo) VALUES (?, ?, ?, ?)",
                       (nuevo_nombre, tipo, puntos, activo))
        print("✅ Se insertó el reto 'Conexión Alfa'")

conn.commit()
conn.close()
