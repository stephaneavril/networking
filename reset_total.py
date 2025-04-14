import sqlite3

# Ruta a tu base de datos principal
db_path = 'database.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Borrar respuestas
cursor.execute("DELETE FROM conexion_alfa_respuestas")
cursor.execute("DELETE FROM conexion_alfa_matches")
cursor.execute("DELETE FROM adivina_participantes")
cursor.execute("DELETE FROM adivina_resultados")
cursor.execute("DELETE FROM jugadores")

conn.commit()
conn.close()

print("✅ Todo ha sido reseteado. Ya puedes empezar desde cero.")
