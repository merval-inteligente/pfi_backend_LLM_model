import pandas as pd
import time
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# === CONFIGURACIÓN ===
JSONL_PATH = "Dataset_Completo.jsonl"
OUTPUT_PATH = "Dataset_Completo_Con_Adaptaciones.jsonl"
LIMITE_POR_TANDA = 570

# === CARGA DE VARIABLES DE ENTORNO ===
load_dotenv()
API_KEY = os.getenv("OPEN_AI_API_KEY")
if not API_KEY:
    raise ValueError("❌ No se encontró la variable OPEN_AI_API_KEY en el entorno")

client = OpenAI(api_key=API_KEY)

# === CARGA DEL DATASET (ROBUSTA) ===
with open(JSONL_PATH, "r", encoding="utf-8") as f:
    lines = [json.loads(line) for line in f if line.strip()]

if not lines:
    raise ValueError("⚠️ El archivo está vacío o no contiene líneas JSON válidas.")

df = pd.DataFrame(lines)

# Crear columna 'adaptacion' si no existe
if 'adaptacion' not in df.columns:
    df['adaptacion'] = None

# === FUNCIÓN DE ADAPTACIÓN ===
def adaptar(texto, nivel):
    prompt = f"""Sos un redactor especializado en adaptar noticias financieras.
Te voy a dar una noticia original y un nivel (1=principiante, 5=avanzado). 
Reescribila completamente para que sea comprensible para ese nivel. No resumas. No omitas nada. Solo cambiá el estilo, hacelo más explicativo y acorde al lector.
En el caso de que el texto original tenga un nivel de complejidad alto, intentá explicarlo de manera que un lector de nivel 1 pueda entenderlo, explicando asi tambinen palabras clave.
Necesito que la noticia tenga el mismo estilo y formato que el original.
Nivel {nivel}:
NOTICIA ORIGINAL:
{texto}

Ahora escribí la versión adaptada al nivel {nivel}:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2048,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error al adaptar noticia (nivel {nivel}):", e)
        return None

# === PROCESAMIENTO ===
pendientes = df[df['adaptacion'].isna()].copy()

if pendientes.empty:
    print("✅ No hay noticias pendientes de adaptación.")
else:
    for idx in pendientes.head(LIMITE_POR_TANDA).index:
        texto = df.at[idx, "texto_original"]
        nivel = df.at[idx, "nivel"]
        print(f"🔄 Adaptando fila {idx} (nivel {nivel})...")
        resultado = adaptar(texto, nivel)
        if resultado:
            df.at[idx, "adaptacion"] = resultado
            df.at[idx, "texto_adaptado"] = resultado  # opcional
        time.sleep(2)

    # Guardar el dataset actualizado
    df.to_json(OUTPUT_PATH, orient="records", lines=True, force_ascii=False)
    print(f"✅ Adaptaciones guardadas en: {OUTPUT_PATH}")
