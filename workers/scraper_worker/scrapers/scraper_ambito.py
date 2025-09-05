import json
import time
import random
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
## from webdriver_manager.microsoft import EdgeChromiumDriverManager
import pickle
import logging


URL = "https://www.ambito.com/finanzas/"
COOKIES_PATH = "cookies.pkl"
TIME_SLEEP = 5 if "--test" not in sys.argv else 1

# === Cargar equivalencias de empresas ===
import os
base_dir = os.path.dirname(os.path.abspath(__file__))
equiv_path = os.path.join(base_dir, '../companies/company_equivalencies.json')
equiv_path = os.path.normpath(equiv_path)
try:
    with open(equiv_path, "r", encoding="utf-8") as f:
        EQUIVALENCIAS_EMPRESAS = json.load(f)
except Exception as e:
    EQUIVALENCIAS_EMPRESAS = {}

def detectar_empresas(texto, equivalencias):
    import unicodedata
    def normalizar(s):
        return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8').lower()

    texto_norm = normalizar(texto)
    empresas = set()
    for empresa, sinonimos in equivalencias.items():
        for s in sinonimos:
            if normalizar(s) in texto_norm:
                if sinonimos:
                    empresas.add(sinonimos[0])
                else:
                    empresas.add(empresa)
                break
    return list(empresas)

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Clasificación automática por palabras clave ===
CATEGORIAS = {
    "dólar": ["dólar", "dólares", "blue", "oficial", "mayorista", "MEP", "CCL"],
    "acciones": ["acción", "acciones", "ADR", "renta variable"],
    "bonos": ["bonos", "bono", "título", "deuda", "AL30", "GD30", "cupones"],
    "Merval": ["Merval", "índice", "bolsa porteña"],
    "macro": ["inflación", "actividad", "PIB", "economía", "recesión", "macroeconomía", "macroeconómico", "superávit"],
    "internacional": ["Wall Street", "EEUU", "China", "Brasil", "global", "internacional", "Reserva Federal", "Fed"]
}

def clasificar_texto(texto):
    texto = texto.lower()
    categorias_detectadas = []
    for categoria, palabras in CATEGORIAS.items():
        if any(palabra.lower() in texto for palabra in palabras):
            categorias_detectadas.append(categoria)
    return categorias_detectadas if categorias_detectadas else ["otras"]

def cargar_cookies(driver, path=COOKIES_PATH):
    try:
        with open(path, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        logging.info(f"🍪 {len(cookies)} cookies cargadas correctamente desde {path}.")
    except FileNotFoundError:
        logging.warning(f"⚠️ El archivo de cookies no se encontró en '{path}'. Se continuará sin cookies.")
    except Exception as e:
        logging.error(f"⚠️ No se pudieron cargar las cookies desde '{path}': {e}")

def intentar_get(driver, url, max_reintentos=3):
    for intento in range(max_reintentos):
        try:
            driver.get(url)
            return True
        except Exception as e:
            logging.warning(f"Reintento {intento+1} para {url} fallido: {e}")
            time.sleep(random.uniform(2, 4))
    return False

def scrapear_ambito():
    edge_options = Options()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--log-level=3")
    # Usar el driver local
    driver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../drivers/msedgedriver.exe'))
    service = Service(driver_path)
    driver = webdriver.Edge(service=service, options=edge_options)

    driver.get(URL)
    time.sleep(TIME_SLEEP)

    cargar_cookies(driver)
    driver.refresh()
    time.sleep(TIME_SLEEP)

    articles = driver.find_elements(By.CSS_SELECTOR, "article a[href*='/finanzas/']")
    links = list({a.get_attribute("href") for a in articles if a.get_attribute("href")})[:8]

    noticias = []

    for url in links:
        logging.info(f"🔗 Entrando a: {url}")
        if not intentar_get(driver, url):
            logging.error(f"❌ No se pudo acceder a {url} tras múltiples intentos.")
            continue

        time.sleep(random.uniform(2.5, 5.5))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1.5, 3.5))

        try:
            titulo = driver.find_element(By.TAG_NAME, "h1").text

            # Fecha de publicación
            fecha_publicacion = None
            fecha_raw = None
            try:
                fecha_raw = driver.find_element(By.CSS_SELECTOR, ".date, time, .article-date").text.strip()
                fecha_part = fecha_raw.split("|")[0].strip()
                formatos = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
                for fmt in formatos:
                    try:
                        fecha_publicacion = datetime.strptime(fecha_part, fmt)
                        break
                    except Exception:
                        continue
                if not fecha_publicacion:
                    fecha_publicacion = datetime.now()
            except Exception:
                fecha_publicacion = datetime.now()
                fecha_raw = None

            posibles_selectores = [
                ".article-main-content", ".article-body",
                "div.article-content", "div.article-text", "article"
            ]
            parrafos = []
            for selector in posibles_selectores:
                try:
                    contenedor = driver.find_element(By.CSS_SELECTOR, selector)
                    parrafos = contenedor.find_elements(By.TAG_NAME, "p")
                    if len(parrafos) > 3:
                        break
                except:
                    continue

            texto_completo = " ".join(p.text for p in parrafos if p.text.strip())
            resumen = " ".join(p.text for p in parrafos[:5])

            texto_para_match = f"{titulo} {resumen} {texto_completo}"
            empresas_relacionadas = detectar_empresas(texto_para_match, EQUIVALENCIAS_EMPRESAS)

            noticia = {
                "scrapingDate": datetime.now().isoformat(),
                "title": titulo,
                "publicationDate": fecha_raw,
                "summary": resumen,
                "content": texto_completo,
                "adaptationLevel": None,
                "adaptationSummary": None,
                "adaptationContent": None,
                "url": url,
                "mervalSymbol": empresas_relacionadas
            }

            noticias.append(noticia)
            logging.info(f"📝 {titulo[:60]}...")

        except (NoSuchElementException, TimeoutException) as e:
            logging.warning(f"No se pudo encontrar un elemento en {url}. Error: {type(e).__name__}")
        except Exception as e:
            logging.error(f"Error inesperado al procesar {url}: {e}", exc_info=True)

    # Guardar en carpeta 'scrapped_data' (crear si no existe)
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraped_data'))
    os.makedirs(output_dir, exist_ok=True)
    nombre_archivo = os.path.join(output_dir, f"noticias_ambito_{datetime.now().date()}.json")
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(noticias, f, indent=2, ensure_ascii=False)
        logging.info(f"\n💾 {len(noticias)} noticias guardadas en {nombre_archivo}")

    driver.quit()

if __name__ == "__main__":
    scrapear_ambito()
