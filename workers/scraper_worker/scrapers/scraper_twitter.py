import os
import json
import time
import logging
import random
import subprocess
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from pysentimiento import create_analyzer

# Configuración
SCROLLS = random.randint(10, 15)
PAUSA = (random.randint(0, 10), random.randint(11, 25))
TIEMPO_INICIAL = random.randint(5, 20)
"""KEYWORDS = [
    "dólar", "blue", "riesgo país", "merval", "acciones", "bonos", "inflación", "devaluación",
    "tasa", "plazo fijo", "banco central", "bcra", "emisión", "liquidez", "default",
    "ganancias", "dividendos", "pbi", "reservas", "mercado", "intervención", "brecha",
    "cepo", "paralelo", "elecciones", "economía", "finanzas", "cnv", "byma", "cedears"
]"""
KEYWORDS = [
    # Mercado de valores
    "acción", "acciones", "papel", "papeles", "equity", "adr", "cedear", "cedares",
    "dividendos", "balance", "balances", "resultados trimestrales", "suba", "baja",
    "rally", "toma de ganancias", "liquidez", "volumen", "cotización", "precio objetivo",

    # Bonos y renta fija
    "bono", "bonos", "soberano", "soberanos", "letes", "leliq", "lebas",
    "reperfilamiento", "default", "canje", "reestructuración", "vencimiento", "tasa", "tasa de interés",

    # Dólar y divisas
    "dólar", "dolar", "dólar blue", "dolar blue", "dólar mep", "dolar mep", 
    "contado con liqui", "ccl", "dólar ahorro", "dolar ahorro", "dólar tarjeta", "dolar tarjeta",
    "oficial", "devaluación", "devaluacion", "cepo", "brecha cambiaria",
    "reservas", "tipo de cambio", "corrida cambiaria",

    # Macroeconomía y riesgo
    "inflación", "inflacion", "riesgo país", "riesgo pais", "déficit", "deficit", 
    "superávit", "superavit", "deuda", "emisión monetaria", "emision monetaria",
    "ajuste", "recesión", "recesion", "crecimiento", "pbi", "bcra", "banco central",
    "fmi", "fondo", "tasas",

    # Índices y mercados
    "merval", "s&p merval", "byma", "wall street", "dow jones", "nasdaq", "s&p 500",
    "corrección", "correccion", "mercado alcista", "mercado bajista",

    # Instrumentos y derivados
    "futuros", "opciones", "puts", "calls", "warrants", 
    "commodities", "oro", "petróleo", "petroleo", "soja",
    "cripto", "bitcoin", "ethereum"
]


def analizar_sentimiento(texto):
    analyzer = create_analyzer(task="sentiment", lang="es")
    sentiment = analyzer.predict(texto)
    return sentiment

# Lógica principal
def scrapear_tweets(empresa,driver,tweets_finales):
    # Log
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    KEYWORDS_QUERY = ["bono", "bonos", "acciones", "dólar", "blue", "inflación", "riesgo", "devaluación", "merval", "cedear", "balance", "dividendos", "suba","baja"]

    query_keywords = " OR ".join(KEYWORDS)
    query = f"({empresa}) ({query_keywords}) lang:es"
    url = f"https://twitter.com/search?q={query}&src=typed_query&f=live"

    
    logging.info(f"🔎 Buscando: {query}")

    try:
        driver.get(url)
        time.sleep(TIEMPO_INICIAL)

        for i in range(SCROLLS):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(10,20))

        tweets = driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')
        logging.info(f"✍️ {len(tweets)} tweets encontrados para {empresa}")

        for tweet in tweets:
            try:
                texto = tweet.find_element(By.XPATH, './/div[@data-testid="tweetText"]').text
                autor = tweet.find_element(By.XPATH, './/div[@dir="ltr"]/span').text
                link = tweet.find_element(By.XPATH, './/a[@role="link"]').get_attribute("href")
                fecha_element = tweet.find_element(By.XPATH, './/time')
                fecha_tweet = fecha_element.get_attribute("datetime")


                if any(palabra in texto.lower() for palabra in KEYWORDS):
                    tweets_finales.append({
                        "empresa": empresa,
                        "usuario": autor,
                        "contenido": texto,
                        "sentimiento": analizar_sentimiento(texto).output,
                        "url": f"https://twitter.com{link}" if not link.startswith("http") else link,
                        "scrapingDate": datetime.now().isoformat(),
                        "fecha_tweet": fecha_tweet
                    })

            except NoSuchElementException:
                continue

    except Exception as e:
        logging.warning(f"⚠️ Fallo scrapeo para {empresa}: {e}")

    #driver.quit()

    nombre_archivo = f"tweets_merval_selenium_{datetime.today().date()}.json"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(tweets_finales, f, indent=2, ensure_ascii=False)

    logging.info(f"✅ Se guardaron {len(tweets_finales)} tweets en {nombre_archivo}")

    return tweets_finales

if __name__ == "__main__":
    scrapear_tweets()
