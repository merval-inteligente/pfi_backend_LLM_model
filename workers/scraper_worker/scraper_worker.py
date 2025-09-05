from pymongo import MongoClient
def probar_conexion_mongo():
    # Reemplaza la URI por la de tu clúster Atlas
    MONGO_URI = "mongodb+srv://admin:tRVIi8NhbKbzDj0q@cluster0.dad6cgj.mongodb.net/MervalDB?retryWrites=true&w=majority"
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # Fuerza la conexión
        print("✅ Conexión a MongoDB Atlas exitosa.")
    except Exception as e:
        print(f"❌ Error de conexión a MongoDB Atlas: {e}")
    finally:
        if 'client' in locals():
            client.close()
from pymongo import MongoClient
# --- IMPORTS NECESARIOS ---
from scrapers.scraper_iprofesional import scrapear_iprofesional
from scrapers.scraper_infobae import scrapear_infobae
from scrapers.scraper_ambito import scrapear_ambito
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import os
import json

# --- BLOQUE PRINCIPAL ---
if __name__ == "__main__":
    # Probar conexión a MongoDB Atlas antes de scrapear
    probar_conexion_mongo()
    print("Ejecutando scraper de Infobae...")
    scrapear_infobae()
    print("Ejecutando scraper de Infobae...")
    scrapear_infobae()
    print("Ejecutando scraper de Ámbito...")
    scrapear_ambito()
    print("Ejecutando scraper de iProfesional...")
    edge_options = Options()
    edge_options.add_argument("--headless=new")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--log-level=3")
    driver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scrapers/../drivers/msedgedriver.exe'))
    service = Service(driver_path)
    driver = None
    try:
        from selenium import webdriver
        driver = webdriver.Edge(service=service, options=edge_options)
        equiv_path = os.path.join(os.path.dirname(__file__), 'scrapers/../companies/company_equivalencies.json')
        with open(equiv_path, "r", encoding="utf-8") as f:
            equivalencias = json.load(f)
        scrapear_iprofesional(driver, equivalencias)
    finally:
        if driver:
            driver.quit()

    # Leer los archivos JSON generados por los scrapers
    scrapped_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scraped_data'))
    noticias_files = [f for f in os.listdir(scrapped_dir) if f.endswith('.json') and 'noticias_' in f]
    todas = []
    for file in noticias_files:
        path = os.path.join(scrapped_dir, file)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                noticias = json.load(f)
                if isinstance(noticias, list):
                    todas.extend(noticias)
        except Exception as e:
            print(f"Error leyendo {file}: {e}")
    # Reemplaza la URI por la de tu clúster Atlas
    MONGO_URI = "mongodb+srv://admin:tRVIi8NhbKbzDj0q@cluster0.dad6cgj.mongodb.net/MervalDB?retryWrites=true&w=majority"
    DB_NAME = "MervalDB"
    COLLECTION_NAME = "news"

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        # 'todas' ya contiene todas las noticias leídas de los archivos JSON
        if todas:
            # Insertar evitando duplicados por URL y contar realmente los upserts
            upserts = 0
            for noticia in todas:
                res = collection.update_one({"url": noticia["url"]}, {"$setOnInsert": noticia}, upsert=True)
                if res.upserted_id is not None:
                    upserts += 1
            print(f"Se insertaron {upserts} noticias nuevas (de {len(todas)} procesadas) en MongoDB Atlas.")
            # Mostrar los primeros 3 documentos para depuración
            print("Primeras noticias en la colección:")
            for doc in collection.find().limit(3):
                print(f"- {doc.get('titulo', '[sin titulo]')} | {doc.get('url', '[sin url]')}")
        else:
            print("No hay noticias para subir.")
    except Exception as e:
        print(f"Error al subir a MongoDB Atlas: {e}")
    finally:
        if 'client' in locals():
            client.close()
    print("Scraping finalizado y datos subidos a MongoDB Atlas (si la conexión fue exitosa).")
