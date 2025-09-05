from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
import pickle
import time
import os

# Ruta absoluta o relativa al driver si lo tenés en una carpeta específica
# service = Service("drivers/msedgedriver.exe")
# driver = webdriver.Edge(service=service, options=options)

options = Options()
options.headless = False

# Solo eliminamos si el archivo existe
if os.path.exists("cookies.pkl"):
    os.remove("cookies.pkl")
    print("🧹 Cookie anterior eliminada")

driver = webdriver.Edge(options=options)

driver.get("https://www.ambito.com/finanzas/")
print("🔐 Iniciá sesión manual si es necesario y aceptá cookies")
input("Presioná ENTER cuando termines...")

# Guardamos las cookies
with open("cookies.pkl", "wb") as file:
    pickle.dump(driver.get_cookies(), file)
    print("✅ Cookies guardadas en cookies.pkl")

driver.quit()
