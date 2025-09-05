from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import json
import time
import random
from datetime import datetime
import logging

REDDIT_QUERY = "$AMZN"
URL_BASE = f"https://www.reddit.com/search/?q={REDDIT_QUERY}&sort=new&t=day"
SCROLLS = 6
WAIT_TIMEOUT = 15
KEYWORDS_ARG = [
    "argentina", "argentino", "merval", "banco central", "inflación", "dólar", 
    "afip", "anses", "bonos", "renta fija", "bolsa", "finanzas", "reservas"
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def es_argentino(texto):
    texto = texto.lower()
    return any(k in texto for k in KEYWORDS_ARG)

def scrapear_reddit():
    edge_options = Options()
    edge_options.add_argument("--start-maximized")
    edge_options.add_argument("--user-data-dir=C:/Users/Luciano/AppData/Local/Microsoft/Edge/User Data")
    edge_options.add_argument("--profile-directory=Default")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_argument("--disable-extensions")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")

    path_driver = "C:\\Users\\Luciano\\Desktop\\UADE\\PFI\\programa\\pfi_mervAI\\drivers\\msedgedriver.exe"
    service = Service(path_driver)
    driver = webdriver.Edge(service=service, options=edge_options)

    driver.get(URL_BASE)

    # Esperar a que aparezcan posts
    try:
        logging.info("🔍 Esperando que cargue al menos 1 post...")
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "Post")]'))
        )
    except Exception:
        logging.warning("⚠️ No se cargó ningún post inicial.")
        pass

    # Scroll progresivo
    for i in range(SCROLLS):
        logging.info(f"🔄 Scroll {i+1}/{SCROLLS}")
        driver.execute_script("window.scrollBy(0, 1500);")
        time.sleep(random.uniform(4, 7))

    # Debug visual
    with open("reddit_debug.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    posts = driver.find_elements(By.XPATH, '//div[contains(@class, "Post")]')
    logging.info(f"📄 {len(posts)} posts encontrados.")

    resultados = []
    for post in posts:
        try:
            titulo = post.find_element(By.TAG_NAME, "h3").text
            usuario = post.find_element(By.XPATH, './/a[contains(@href, "/user/")]').text
            subreddit = post.find_element(By.XPATH, './/a[contains(@href, "/r/")]').text
            url = post.find_element(By.XPATH, './/a[contains(@href, "/r/")]').get_attribute("href")

            try:
                contenido = post.find_element(By.XPATH, './/div[contains(@data-click-id, "text")]').text
            except:
                contenido = ""

            if es_argentino(f"{titulo} {contenido}"):
                resultados.append({
                    "fecha_scrapeo": datetime.now().isoformat(),
                    "titulo": titulo,
                    "usuario": usuario,
                    "subreddit": subreddit,
                    "contenido": contenido,
                    "url": url
                })
                logging.info(f"✅ {titulo[:60]}...")

        except Exception as e:
            logging.warning(f"❌ Error en post: {e}")

    driver.quit()

    archivo = f"reddit_merval_{datetime.now().date()}.json"
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    logging.info(f"💾 {len(resultados)} posts guardados en {archivo}")

if __name__ == "__main__":
    scrapear_reddit()
