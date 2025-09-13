# -*- coding: utf-8 -*-
"""
extraer_temas.py

Lee un JSONL con noticias y agrega un campo "temas_detectados" (lista) y "scores_temas" (conteo de hits por tema).
Opcionalmente genera un CSV de distribución por tema.

Uso:
  python extraer_temas.py --input Dataset_Completo_Con_Adaptaciones_LIMPIO.jsonl --output Dataset_con_temas.jsonl --resumen temas_resumen.csv
"""

import json, re, argparse, unicodedata
from collections import defaultdict, Counter

# ------------------------------
# Utilidades
# ------------------------------
def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # normaliza sin tildes pero conservando 'ñ'
    s = unicodedata.normalize("NFKD", s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    return s

def compile_pattern(p):
    return re.compile(p, flags=re.IGNORECASE)

# ------------------------------
# Taxonomía de temas (Argentina)
# ------------------------------
TOPICS = {
    "dolar_fx": [
        r"\bdolar(es)?\b", r"\bblue\b", r"\bmep\b", r"\bccl\b", r"\bcontado con liqui\b",
        r"\bbrecha cambiaria\b", r"\bcepo\b", r"\breservas\b", r"\bmercado cambiario\b",
        r"\bdevaluaci[oó]n\b", r"\btipo de cambio\b"
    ],
    "politica_monetaria_tasas": [
        r"\btasa(s)?\b", r"\bleliq(s)?\b", r"\bpases?\b", r"\bencajes?\b", r"\bemisi[oó]n\b",
        r"\bbase monetaria\b", r"\bpol[íi]tica monetaria\b", r"\bBCRA\b", r"\nueva tasa\b"
    ],
    "inflacion_precios": [
        r"\binflaci[oó]n\b", r"\bIPC\b", r"\bindec\b", r"\bcanasta\b", r"\bprecios?\b",
        r"\binflaci[oó]n n[uú]cleo\b", r"\bprecios regulados\b"
    ],
    "bonos_deuda": [
        r"\bbono(s)?\b", r"\bAL\d{2}\b", r"\bGD\d{2}\b", r"\bCER\b", r"\bcupon(es)?\b",
        r"\briesgo pa[ií]s\b", r"\bspread\b", r"\bdefault\b", r"\bcanje\b", r"\bletra(s)?\b",
        r"\bvencimiento(s)?\b", r"\bFMI\b"
    ],
    "acciones_mercado": [
        r"\bMERVAL\b", r"\bS\&?P Merval\b", r"\bacciones?\b", r"\bBYMA\b",
        r"\bpanel (l[ií]der|general)\b", r"\bsuba(s)?\b", r"\bbaja(s)?\b",
        r"\bvolatilidad\b", r"\brally\b", r"\bpapeles?\b", r"\bADR(s)?\b"
    ],
    "macro": [
        r"\bPBI\b", r"\bactividad econ[oó]mica\b", r"\bindustri(a|al)\b", r"\bconstrucci[oó]n\b",
        r"\bconsumo\b", r"\bempleo\b", r"\bdesempleo\b", r"\bcomercio exterior\b",
        r"\bbalanza comercial\b", r"\bexportaci[oó]n(es)?\b", r"\bimportaci[oó]n(es)?\b"
    ],
    "bancos_fintech": [
        r"\bbanco(s)?\b", r"\bfintech\b", r"\bdep[oó]sitos?\b", r"\bpr[eé]stamos?\b",
        r"\bcartera\b", r"\bmora\b", r"\bROE\b", r"\bROA\b"
    ],
    "empresas_resultados": [
        r"\bresultados?\b", r"\bbalance(s)?\b", r"\bEBITDA\b", r"\butilidad(es)?\b",
        r"\bingresos?\b", r"\bventas?\b", r"\bguidance\b", r"\bcapex\b"
    ],
    "energia_commodities": [
        r"\benerg[ií]a\b", r"\bVaca Muerta\b", r"\bYPF\b", r"\bcrudo\b", r"\bpetrol[ií]fer(o|a)\b",
        r"\bgas\b", r"\bshale\b", r"\bsoja\b", r"\bma[ií]z\b", r"\btrigo\b", r"\bcommodit(?:y|ies)\b"
    ],
    "sector_publico_fiscal": [
        r"\bAFIP\b", r"\bretenci[oó]n(es)?\b", r"\bimpuesto(s)?\b", r"\bsuper[aá]vit\b",
        r"\bd[ée]ficit\b", r"\bsubsidios?\b", r"\bpresupuesto\b"
    ],
    "regulaciones_politica": [
        r"\bdecreto\b", r"\bresoluci[oó]n\b", r"\bbolet[ií]n oficial\b", r"\breglamentaci[oó]n\b",
        r"\bmedida(s)? oficial(es)?\b", r"\bsecretar[ií]a\b", r"\bministerio\b"
    ],
}

COMPILED = {k: [re.compile(p, flags=re.IGNORECASE) for p in v] for k, v in TOPICS.items()}

def detect_topics(text: str):
    if not isinstance(text, str):
        return [], {}
    t_norm = normalize_text(text)
    scores = {}
    for topic, pats in COMPILED.items():
        s = 0
        for pat in pats:
            s += len(pat.findall(t_norm))
        if s > 0:
            scores[topic] = s
    temas = list(scores.keys()) if scores else []
    return temas, scores

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Ruta del JSONL de entrada")
    ap.add_argument("--output", required=True, help="Ruta del JSONL de salida con temas")
    ap.add_argument("--resumen", default=None, help="(Opcional) CSV con distribución por tema")
    ap.add_argument("--campo_texto", default=None, help="Nombre del campo de texto si no es 'texto_original'")
    args = ap.parse_args()

    campo_texto = args.campo_texto or "texto_original"

    total = 0
    con_temas = 0
    dist = Counter()

    with open(args.input, "r", encoding="utf-8") as fin, open(args.output, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue

            texto = data.get(campo_texto, "")
            temas, scores = detect_topics(texto)

            data["temas_detectados"] = temas if temas else ["otros"]
            data["scores_temas"] = scores

            for t in data["temas_detectados"]:
                dist[t] += 1

            total += 1
            if temas:
                con_temas += 1

            fout.write(json.dumps(data, ensure_ascii=False) + "\n")

    if args.resumen:
        import csv
        with open(args.resumen, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["tema", "cantidad"])
            for tema, cant in dist.most_common():
                writer.writerow([tema, cant])

    print(f"Procesadas: {total} | Con al menos un tema: {con_temas}")
    print("Ejemplo de temas:", dist.most_common(10))

if __name__ == "__main__":
    main()
