import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# ⚠️ Cambia solo un dato ligeramente
cursor.execute("UPDATE adivina_participantes SET superpoder = superpoder || ' ✨' WHERE id = 1")

conn.commit()
conn.close()

print("✔ Base de datos modificada levemente.")
