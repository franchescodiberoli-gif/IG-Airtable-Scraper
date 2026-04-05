import time
import subprocess

while True:
    # Ejecuta el script principal
    subprocess.run(["python", "main.py"])
    
    # NOTA: Se cambió de 24 horas (86400) a 3 horas para evitar reinicios constantes
    # time.sleep(86400)  # <--- Este es el original de 24 horas
    time.sleep(10800)    # Tiempo actual: 3 horas (10800 segundos)
