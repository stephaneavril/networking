import sqlite3

correo = input("Correo a eliminar: ").strip()

conn = sqlite3.connect("database.db")

# Eliminar por correo
conn.execute("DELETE FROM jugadores WHERE correo = ?", (correo,))
conn.execute("DELETE FROM conexion_alfa_respuestas WHERE correo = ?", (correo,))
conn.execute("DELETE FROM conexion_alfa_matches WHERE correo_1 = ? OR correo_2 = ?", (correo, correo,))
conn.execute("DELETE FROM adivina_resultados WHERE nombre_jugador = (SELECT nombre FROM jugadores WHERE correo = ?)", (correo,))
conn.execute("DELETE FROM adivina_participantes WHERE nombre_completo = (SELECT nombre FROM jugadores WHERE correo = ?)", (correo,))

conn.commit()
conn.close()

print(f"✅ Usuario con correo '{correo}' eliminado completamente.")
