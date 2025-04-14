import sqlite3
import json

DB_PATH = 'database.db'
OUTPUT_JSON = 'contenido_adivina.json'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

data = conn.execute('SELECT * FROM adivina_participantes').fetchall()
conn.close()

lista = []
for fila in data:
    lista.append({
        "nombre_completo": fila["nombre_completo"],
        "superpoder": fila["superpoder"],
        "pasion": fila["pasion"],
        "dato_curioso": fila["dato_curioso"],
        "pelicula_favorita": fila["pelicula_favorita"],
        "actor_favorito": fila["actor_favorito"],
        "no_soporto": fila["no_soporto"],
        "mejor_libro": fila["mejor_libro"],
        "prenda_imprescindible": fila["prenda_imprescindible"],
        "mejor_concierto": fila["mejor_concierto"]
    })

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(lista, f, indent=2, ensure_ascii=False)

print("✅ contenido_adivina.json actualizado con", len(lista), "participantes.")
