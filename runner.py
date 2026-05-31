import time
import subprocess
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def run_watcher():
    """Corre el watcher cada 24 horas — solo revisa Gave to the Model."""
    logging.info("Watcher iniciado — primera revision en 10 minutos para no interferir con el scraper principal...")
    time.sleep(600)
    while True:
        subprocess.run(["python", "watcher_main.py"])
        time.sleep(86400)

def run_main():
    """Corre el scraper completo cada 24 horas."""
    logging.info("Scraper principal iniciado — corriendo cada 24 horas")
    while True:
        subprocess.run(["python", "main.py"])
        time.sleep(86400)

# Arrancar el watcher en un hilo separado
watcher_thread = threading.Thread(target=run_watcher, daemon=True)
watcher_thread.start()

# Esperar 15 segundos antes de arrancar el scraper principal
# para evitar que ambos hagan requests a Airtable al mismo tiempo (error 429)
logging.info("Esperando 15 segundos antes de arrancar el scraper principal...")
time.sleep(15)

# El scraper principal corre en el hilo principal
run_main()
