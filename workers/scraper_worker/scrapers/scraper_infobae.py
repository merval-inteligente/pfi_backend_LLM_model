import os
import json
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
# from webdriver_manager.microsoft import EdgeChromiumDriverManager
import time
import random
import sys
from datetime import datetime
import logging

SECCIONES_URL = [
    "https://www.infobae.com/economia-y-finanzas/"
]

TIME_SLEEP = 5 if "--test" not in sys.argv else 1

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# === Palabras clave para filtrar ===
KEYWORDS_ARG = [
    "argentina", "argentino", "merval", "banco central",
    "inflación", "dólar", "afip", "anses", "bonos",
    "renta fija", "bolsa", "finanzas", "reservas"
]

# === Cargar equivalencias de empresas ===
base_dir = os.path.dirname(os.path.abspath(__file__))
equiv_path = os.path.join(base_dir, '../companies/company_equivalencies.json')
equiv_path = os.path.normpath(equiv_path)
try:
    with open(equiv_path, "r", encoding="utf-8") as f:
        EQUIVALENCIAS_EMPRESAS = json.load(f)
except Exception as e:
    EQUIVALENCIAS_EMPRESAS = {}

def detectar_empresas(texto, equivalencias):
    texto = texto.lower()
    empresas = []
    for empresa, sinonimos in equivalencias.items():
        for s in sinonimos:
            if s.lower() in texto:
                if sinonimos:
                    empresas.append(sinonimos[0])
                else:
                    empresas.append(empresa)
                break
    return empresas

def es_argentina(titulo, contenido):
    # Considera argentina si alguna keyword aparece en el texto, pero solo si la keyword no está dentro de otra palabra
    texto = (titulo + " " + contenido).lower()
    for k in KEYWORDS_ARG:
        palabras = texto.split()
        if any(k == palabra.strip('.,;:!¡¿?"\'') for palabra in palabras):
            return True
    return False

def intentar_get(driver, url, max_reintentos=3):
    for intento in range(max_reintentos):
        try:
            driver.get(url)
            return True
        except Exception as e:
            logging.warning(f"Reintento {intento+1} para {url} fallido: {e}")
            time.sleep(random.uniform(2, 4))
    return False

def scrapear_infobae():

    edge_options = Options()
    edge_options.add_argument("--headless=new")  # Forzar headless siempre, compatible con Edge Chromium
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--log-level=3")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--disable-extensions")
    edge_options.add_argument("--disable-software-rasterizer")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    # Usar el driver local
    driver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../drivers/msedgedriver.exe'))
    service = Service(driver_path)
    driver = webdriver.Edge(service=service, options=edge_options)


    todas_noticias = []


    for URL in SECCIONES_URL:
        logging.info(f"📂 Analizando sección: {URL}")
        driver.get(URL)
        time.sleep(TIME_SLEEP)

        # Buscar links internos de noticias usando selectores más amplios
        articles = driver.find_elements(By.CSS_SELECTOR, "a[href*='/economia/'], a[href*='/finanzas/'], a[href*='/economia-y-finanzas/']")
        links = list({a.get_attribute("href") for a in articles if a.get_attribute("href") and a.get_attribute("href").startswith("http")})
        logging.info(f"Links encontrados en la sección: {links}")

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
                contenido = ""
                posibles_selectores = [
                    ".article-main-content", ".article-body",
                    "div.article-content", "div.article-text", "div[itemprop='articleBody']", "article"
                ]
                for selector in posibles_selectores:
                    elementos = driver.find_elements(By.CSS_SELECTOR, f"{selector} p")
                    if elementos:
                        contenido = "\n".join([el.text for el in elementos if el.text.strip()])
                        break

                if not contenido:
                    contenido = "[Contenido no encontrado]"
                if "Registrate gratis" in contenido or "superaste el límite" in contenido.lower():
                    contenido = "[Bloqueado por muro de pago]"
 
                # === Fecha de publicación ===
                fecha_raw = None
                try:
                    fecha_raw = driver.find_element(By.CSS_SELECTOR, ".date").text.strip()
                    fecha_part = fecha_raw.split("|")[0].strip()
                    formatos = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"]
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

                resumen = "\n".join(contenido.split("\n")[:5])
                texto_para_match = f"{titulo} {resumen} {contenido}"
                empresas_relacionadas = detectar_empresas(texto_para_match, EQUIVALENCIAS_EMPRESAS)

                noticia = {
                    "scrapingDate": datetime.now().isoformat(),
                    "title": titulo,
                    "publicationDate": fecha_raw,
                    "summary": resumen,
                    "content": contenido.strip(),
                    "adaptationLevel": None,
                    "adaptationSummary": None,
                    "adaptationContent": None,
                    "url": url,
                    "mervalSymbol": empresas_relacionadas
                }

                logging.info(f"TÍTULO: {titulo}")
                logging.info(f"CONTENIDO: {contenido[:120]}")

                if es_argentina(titulo, contenido):
                    todas_noticias.append(noticia)
                    logging.info(f"🗞️ Noticia obtenida: {titulo}")
                else:
                    logging.info(f"❌ Noticia descartada por filtro de palabras clave: {titulo}")

            except (NoSuchElementException, TimeoutException) as e:
                logging.warning(f"No se pudo encontrar un elemento en {url}. Error: {type(e).__name__}")
            except Exception as e:
                logging.error(f"Error inesperado al procesar {url}: {e}", exc_info=True)


    # Guardar en carpeta 'scrapped_data' (crear si no existe)
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraped_data'))
    os.makedirs(output_dir, exist_ok=True)
    fecha_archivo = datetime.now().date()
    noticias_path = os.path.join(output_dir, f"noticias_infobae_{fecha_archivo}.json")
    tags_path = os.path.join(output_dir, f"tags_infobae_{fecha_archivo}.json")
    with open(noticias_path, "w", encoding="utf-8") as f:
        json.dump(todas_noticias, f, indent=2, ensure_ascii=False)
        logging.info(f"\n💾 {len(todas_noticias)} noticias guardadas en {noticias_path}")

    driver.quit()

if __name__ == "__main__":
    scrapear_infobae()
