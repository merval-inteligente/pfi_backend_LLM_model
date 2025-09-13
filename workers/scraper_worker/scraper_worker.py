from datetime import datetime
from datetime import timedelta
from pymongo import MongoClient
from scrapers.scraper_iprofesional import scrapear_iprofesional
from scrapers.scraper_infobae import scrapear_infobae
from scrapers.scraper_ambito import scrapear_ambito
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium import webdriver
import os
import json

MONGO_URI = "mongodb+srv://admin:tRVIi8NhbKbzDj0q@cluster0.dad6cgj.mongodb.net/MervalDB?retryWrites=true&w=majority"
DB_NAME = "MervalDB"
COLLECTION_NAME_NEWS = "news"
DAYS_TO_KEEP = 7  # Número de días para mantener las noticias (prueba de borrado)

def clean_files():
    scrapped_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scraped_data'))
    now = datetime.now()
    for filename in os.listdir(scrapped_dir):
        if filename.endswith('.json') and 'noticias_' in filename:
            date_str = filename.replace('noticias_', '').replace('.json', '')
            try:
                #file_date = datetime.strptime(date_str, '%Y-%m-%d')
                #if (now - file_date).days > DAYS_TO_KEEP:
                os.remove(os.path.join(scrapped_dir, filename))
                print(f"Archivo {filename} eliminado.")
            except ValueError:
                print(f"Nombre de archivo {filename} no coincide con el formato esperado.")

def clean_database():
    datetime_limit = (datetime.now() - timedelta(days=DAYS_TO_KEEP)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME_NEWS]
        # Si las fechas en la base tienen decimales en los segundos, compara solo hasta segundos
        deleted_count = collection.delete_many({"scrapingDate": {"$lt": datetime_limit}}).deleted_count
        print(f"Base de datos limpiada. Se eliminaron {deleted_count} documentos.")
    except Exception as e:
        print(f"Error al limpiar la base de datos: {e}")
    finally:
        if 'client' in locals():
            client.close()
    

def probar_conexion_mongo():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # Fuerza la conexión
        print("✅ Conexión a MongoDB Atlas exitosa.")
    except Exception as e:
        print(f"❌ Error de conexión a MongoDB Atlas: {e}")
    finally:
        if 'client' in locals():
            client.close()

# --- BLOQUE PRINCIPAL ---
if __name__ == "__main__":
    # Probar conexión a MongoDB Atlas antes de scrapear
    probar_conexion_mongo()

    # Limpiar archivos antiguos
    clean_files()
    
    print("Ejecutando scraper de Infobae...")
    scrapear_infobae()
    print("Ejecutando scraper de Ámbito...")
    scrapear_ambito()
    print("Ejecutando scraper de iProfesional...")

    # Configuración del driver de Edge
    edge_options = Options()
    edge_options.add_argument("--headless=new")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--log-level=3")
    driver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scrapers/../drivers/msedgedriver.exe'))
    service = Service(driver_path)
    driver = None

    # Ejecutar el scraper de iProfesional
    try:
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

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME_NEWS]
        # Limpiar la base de datos antes de insertar nuevas noticias
        clean_database()

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
