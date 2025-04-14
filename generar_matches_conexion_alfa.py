import sqlite3
import pickle
from sklearn.metrics.pairwise import cosine_similarity

# Cargar modelo y vectorizer
with open("modelo_conexion_alfa.pkl", "rb") as f:
    modelo = pickle.load(f)
with open("vectorizer_conexion_alfa.pkl", "rb") as f:
    vectorizer = pickle.load(f)

# Conectar a la base de datos
conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Obtener respuestas
respuestas = cursor.execute("SELECT * FROM conexion_alfa_respuestas").fetchall()
if len(respuestas) < 2:
    print("⚠️ Se requieren al menos 2 participantes para generar matches.")
    conn.close()
    exit()

# Convertir textos
correos = [r["correo"] for r in respuestas]
nombres = [r["nombre"] for r in respuestas]
perfiles = [r["perfil_ia"] for r in respuestas]
textos = [
    f"{r['r1']} {r['r2']} {r['r3']} {r['r4']} {r['r5']} {r['r6']} {r['r7']}"
    for r in respuestas
]
vectores = vectorizer.transform(textos)
sim_matrix = cosine_similarity(vectores)

# Borrar matches anteriores
cursor.execute("DELETE FROM conexion_alfa_matches")
conn.commit()

# Lógica de emparejamiento 1 a 1 más justo posible
asignados = set()
for i in range(len(correos)):
    if correos[i] in asignados:
        continue
    mejores = [
        (j, sim_matrix[i][j])
        for j in range(len(correos))
        if j != i and correos[j] not in asignados
    ]
    if mejores:
        mejor_j, score = max(mejores, key=lambda x: x[1])
        cursor.execute('''
            INSERT INTO conexion_alfa_matches 
            (correo_1, correo_2, nombre_1, nombre_2, perfil_1, perfil_2)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            correos[i], correos[mejor_j],
            nombres[i], nombres[mejor_j],
            perfiles[i], perfiles[mejor_j]
        ))
        asignados.add(correos[i])
        asignados.add(correos[mejor_j])
        print(f"✅ Match: {nombres[i]} 🤝 {nombres[mejor_j]}")

conn.commit()
conn.close()
print("✅ Todos los matches fueron generados correctamente.")
