import json
import time
import random
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
# from webdriver_manager.microsoft import EdgeChromiumDriverManager

# === Configuración ===
URL_BASE = "https://www.iprofesional.com/finanzas"
TIME_SLEEP = 5
SCROLLS = 2

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

def scrapear_iprofesional(driver,equivalencias):
    #driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)

    driver.get(URL_BASE)
    logging.info("🔍 Cargando iProfesional Finanzas…")
    time.sleep(TIME_SLEEP)

    for i in range(SCROLLS):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(random.uniform(3, 5))

    articulos = driver.find_elements(By.CSS_SELECTOR, "a[href*='/finanzas/']")
    urls = []
    for a in articulos:
        href = a.get_attribute("href")
        if href and href not in urls:
            urls.append(href)
    logging.info(f"🔗 {len(urls)} links encontrados.")

    noticias = []
    for url in urls:
        try:
            driver.get(url)
            time.sleep(random.uniform(4, 6))

            titulo = driver.find_element(By.TAG_NAME, "h1").text


            # Mejorar extracción y parseo de fecha
            fecha_raw = None
            try:
                fecha_raw = driver.find_element(By.CSS_SELECTOR, ".date").text.strip()
                # Tomar solo la parte de la fecha (puede venir con hora o con '|')
                fecha_part = fecha_raw.split("|")[0].strip()
                # Intentar varios formatos
                formatos = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"]
                for fmt in formatos:
                    try:
                        fecha_publicacion = datetime.strptime(fecha_part, fmt)
                        break
                    except Exception:
                        continue
                if not fecha_publicacion:
                    # Si no se pudo parsear, usar fecha actual pero guardar el valor crudo
                    fecha_publicacion = datetime.now()
            except Exception as e:
                fecha_publicacion = datetime.now()
                fecha_raw = None

            # Filtrar solo noticias del día actual
            if fecha_publicacion.date() != datetime.now().date():
                continue

            posibles_contenedores = [
                "article", ".note-body", ".article-body", ".container-body", ".article-container", ".story-content"
            ]

            parrafos = []
            for selector in posibles_contenedores:
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
            empresas_relacionadas = detectar_empresas(texto_para_match, equivalencias)


            noticias.append({
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
            })

            logging.info(f"📝 {titulo[:60]}...")

        except Exception as e:
            logging.warning(f"❌ Error en {url}: {e}")
            with open("debug_iprofesional.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

    #driver.quit()

    # Guardar en carpeta 'scrapped_data' (crear si no existe)
    import os
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scraped_data'))
    os.makedirs(output_dir, exist_ok=True)
    archivo = os.path.join(output_dir, f"noticias_iprofesional_{datetime.today().date()}.json")
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(noticias, f, indent=2, ensure_ascii=False)
    logging.info(f"💾 {len(noticias)} noticias guardadas en {archivo}")


# === Ejecución principal ===
if __name__ == "__main__":
    # Configurar Selenium Edge driver

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    # Usar el driver local
    import os
    driver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../drivers/msedgedriver.exe'))
    driver = webdriver.Edge(service=Service(driver_path), options=options)

    # Cargar equivalencias de empresas

    try:
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        equiv_path = os.path.join(base_dir, '../companies/company_equivalencies.json')
        equiv_path = os.path.normpath(equiv_path)
        with open(equiv_path, "r", encoding="utf-8") as f:
            equivalencias = json.load(f)
    except Exception as e:
        logging.error(f"No se pudo cargar el archivo de equivalencias: {e}")
        equivalencias = {}

    try:
        scrapear_iprofesional(driver, equivalencias)
    finally:
        driver.quit()
