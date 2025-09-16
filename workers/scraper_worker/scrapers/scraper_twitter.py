import psutil
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import json
import time
import logging
import random
import subprocess
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from pysentimiento import create_analyzer

# Configuración
SCROLLS = random.randint(2, 5)
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
    {"acción", "acciones", "papel", "papeles", "equity", "adr", "cedear", "cedares",
    "dividendos", "balance", "balances", "resultados trimestrales", "suba", "baja",
    "rally", "toma de ganancias", "liquidez", "volumen", "cotización", "precio objetivo",
    },
    # Bonos y renta fija
    {"bono", "bonos", "soberano", "soberanos", "letes", "leliq", "lebas",
    "reperfilamiento", "default", "canje", "reestructuración", "vencimiento", "tasa", "tasa de interés"
    },

    # Dólar y divisas
    {"dólar", "dolar", "dólar blue", "dolar blue", "dólar mep", "dolar mep", 
    "contado con liqui", "ccl", "dólar ahorro", "dolar ahorro", "dólar tarjeta", "dolar tarjeta",
    "oficial", "devaluación", "devaluacion", "cepo", "brecha cambiaria",
    "reservas", "tipo de cambio", "corrida cambiaria",
    },
    # Macroeconomía y riesgo
    {"inflación", "inflacion", "riesgo país", "riesgo pais", "déficit", "deficit", 
    "superávit", "superavit", "deuda", "emisión monetaria", "emision monetaria",
    "ajuste", "recesión", "recesion", "crecimiento", "pbi", "bcra", "banco central",
    "fmi", "fondo", "tasas",
    },
    # Índices y mercados
    {"merval", "s&p merval", "byma", "wall street", "dow jones", "nasdaq", "s&p 500",
    "corrección", "correccion", "mercado alcista", "mercado bajista",
    },

    # Instrumentos y derivados
    {"futuros", "opciones", "puts", "calls", "warrants", 
    "commodities", "oro", "petróleo", "petroleo", "soja",
    "cripto", "bitcoin", "ethereum"
    }
]

def kill_edge_processes():
    """Mata todos los procesos de Microsoft Edge."""
    killed = 0
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'msedge' in proc.info['name'].lower():
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    print(f"Procesos de Edge terminados: {killed}")

def analizar_sentimiento(texto):
    analyzer = create_analyzer(task="sentiment", lang="es")
    sentiment = analyzer.predict(texto)
    return sentiment

# Lógica principal
def scrapear_tweets(empresa,driver,tweets_finales):
    # Log
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Permite filtrar por fecha (opcional)
    fecha_desde = (datetime.now() - timedelta(days=60)).date()  # Últimos 60 días
    fecha_hasta = datetime.now().date()  # Hoy


    for palabra in KEYWORDS:
        query_word = " OR ".join(palabra)
        query = f"({empresa}) ({query_word}) lang:es"
        if fecha_desde:
            query += f" since:{fecha_desde}"
        if fecha_hasta:
            query += f" until:{fecha_hasta}"
        url = f"https://twitter.com/search?q={query}&src=typed_query&f=live"

        logging.info(f"🔎 Buscando: {query}")

        try:
            driver.get(url)
            time.sleep(TIEMPO_INICIAL)

            for i in range(SCROLLS):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(10,20))

            tweets = driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')
            logging.info(f"✍️ {len(tweets)} tweets encontrados para {empresa} y palabra '{palabra}'")

            for tweet in tweets:
                try:
                    texto = tweet.find_element(By.XPATH, './/div[@data-testid="tweetText"]').text
                    autor = tweet.find_element(By.XPATH, './/div[@dir="ltr"]/span').text
                    link = tweet.find_element(By.XPATH, './/a[@role="link"]').get_attribute("href")
                    fecha_element = tweet.find_element(By.XPATH, './/time')
                    fecha_tweet = fecha_element.get_attribute("datetime")

                    # Evitar duplicados por URL
                    if not any(t["url"] == (f"https://twitter.com{link}" if not link.startswith("http") else link) for t in tweets_finales):
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
            logging.warning(f"⚠️ Fallo scrapeo para {empresa} y palabra '{palabra}': {e}")

    nombre_archivo = f"tweets_merval_selenium_{datetime.today().date()}.json"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(tweets_finales, f, indent=2, ensure_ascii=False)

    logging.info(f"✅ Se guardaron {len(tweets_finales)} tweets en {nombre_archivo}")

    return tweets_finales

def twitter_login_with_google(driver, google_email, google_password):
    driver.get("https://twitter.com/login")
    wait = WebDriverWait(driver, 20)
    try:
        # Esperar y hacer clic en el botón de Google
        google_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@role="button"][.//span[contains(text(), "Google")]]')))
        google_btn.click()
        time.sleep(2)

        # Cambiar a la nueva ventana de Google
        main_window = driver.current_window_handle
        for handle in driver.window_handles:
            if handle != main_window:
                driver.switch_to.window(handle)
                break

        # Completar email de Google
        email_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="email"]')))
        email_input.clear()
        email_input.send_keys(google_email)
        email_input.send_keys(Keys.RETURN)
        time.sleep(2)

        # Completar contraseña de Google
        password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
        password_input.clear()
        password_input.send_keys(google_password)
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)

        # Volver a la ventana principal de Twitter
        driver.switch_to.window(main_window)
        time.sleep(5)
    except Exception as e:
        logging.error(f"Error en login con Google: {e}")
        raise

def twitter_login(driver, email, password):
    driver.get("https://twitter.com/login")
    try:
        wait = WebDriverWait(driver, 20)
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "text")))
        email_input.clear()
        email_input.send_keys(email)
        email_input.send_keys(Keys.RETURN)
        time.sleep(2)

        # Twitter puede pedir usuario o directamente la contraseña
        try:
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        except TimeoutException:
            # Si pide usuario, completar y avanzar
            username_input = wait.until(EC.presence_of_element_located((By.NAME, "text")))
            username_input.clear()
            username_input.send_keys(email)
            username_input.send_keys(Keys.RETURN)
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))

        password_input.clear()
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)
    except Exception as e:
        logging.error(f"Error al iniciar sesión en Twitter: {e}")
        raise

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
    # Matar procesos de Edge antes de iniciar Selenium
    kill_edge_processes()
    # Configuración del driver de Edge
    edge_options = Options()
    #edge_options.add_argument("--headless=new")
    edge_options.add_argument('user-data-dir=C:/Users/Luciano Bergaglio/AppData/Local/Microsoft/Edge/User Data')
    edge_options.add_argument('profile-directory=Default')  # O el nombre de tu perfil
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--log-level=3")
    driver_path = r"D:\UADE\PFI\pfi_backend_LLM_model\workers\scraper_worker\drivers\msedgedriver.exe"
    driver = webdriver.Edge(service=Service(driver_path), options=edge_options)
    try:
        # Si la sesión está activa en el perfil de Edge, no es necesario login
        empresa = "$YPF"  # Puedes cambiar por cualquier empresa de prueba
        tweets_finales = []
        scrapear_tweets(empresa, driver, tweets_finales)
        print(f"Se recolectaron {len(tweets_finales)} tweets para {empresa}.")
        input("Presiona Enter para cerrar el navegador...")
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        input("Presiona Enter para cerrar el navegador...")
    finally:
        driver.quit()
