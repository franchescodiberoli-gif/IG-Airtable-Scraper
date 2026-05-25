import time
import subprocess
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def run_watcher():
    """Corre el watcher cada 3 minutos — solo revisa Gave to the Model."""
    logging.info("Watcher iniciado — revisando cada 3 minutos")
    while True:
        subprocess.run(["python", "watcher_main.py"])
        time.sleep(180)

def run_main():
    """Corre el scraper completo cada 24 horas."""
    logging.info("Scraper principal iniciado — corriendo cada 24 horas")
    while True:
        subprocess.run(["python", "main.py"])
        time.sleep(86400)

# Arrancar el watcher en un hilo separado
watcher_thread = threading.Thread(target=run_watcher, daemon=True)
watcher_thread.start()

# El scraper principal corre en el hilo principal
run_main()
