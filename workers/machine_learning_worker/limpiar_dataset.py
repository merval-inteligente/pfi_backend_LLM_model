import json
import re

INPUT_PATH = "/Dataset_Completo_Con_Adaptaciones.jsonl"
OUTPUT_PATH = "/Dataset_Completo_Con_Adaptaciones_LIMPIO.jsonl"

# Frases y patrones a eliminar o reducir
REPETICIONES = [
    r"(\b[\wáéíóúñ]+\b)(?:\s+\1\b)+",  # palabras repetidas
    r"(estabilidad de corto corto plazo)",
    r"(mantener la estabilidad económica estable)",
    r"(presión del Tesoro.*presión sobre el Tesoro)",
    r"(reducción de instrumentos financieros.*reducción de instrumentos financieros)",
]

# Frases confusas o redundantes
FRASES_CONFUSAS = [
    "la estrategia estabilizó la estabilidad de corto corto plazo",
    "el objetivo es mantener el equilibrio en el corto plazo y mantener la estabilidad económica estable",
    "aumentado la presión del Tesoro y reducido la presión sobre el Tesoro",
    "presión del Tesoro",  # si aparece muchas veces
    "presión sobre el Tesoro",
]

def limpiar_texto(texto):
    # Elimina repeticiones exactas de palabras
    for patron in REPETICIONES:
        texto = re.sub(patron, r"\1", texto, flags=re.IGNORECASE)
    # Elimina frases confusas
    for frase in FRASES_CONFUSAS:
        texto = texto.replace(frase, "")
    # Elimina espacios dobles y saltos de línea redundantes
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = re.sub(r"[ ]{2,}", " ", texto)
    return texto.strip()

def es_valido(texto):
    # Considera inválido si el texto es muy corto o tiene muchas repeticiones
    if len(texto.split()) < 30:
        return False
    if texto.count("...") > 2:
        return False
    return True

def limpiar_dataset(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            data = json.loads(line)
            # Elige el campo de adaptación
            adaptado = data.get("texto_adaptado") or data.get("adaptacion")
            if not adaptado:
                continue
            limpio = limpiar_texto(adaptado)
            if es_valido(limpio):
                data["texto_adaptado"] = limpio
                fout.write(json.dumps(data, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    limpiar_dataset(INPUT_PATH, OUTPUT_PATH)
    print(f"✅ Dataset limpio guardado en: {OUTPUT_PATH}")
