import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute(
    "INSERT INTO retos (nombre, puntos, tipo, activo) VALUES (?, ?, ?, ?)",
    ("Adivina Quién", 3, "individual", 1)
)

conn.commit()
conn.close()
print("✅ Adivina Quién agregado correctamente")
