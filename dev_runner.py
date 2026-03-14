import subprocess, sys, time, os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Reloader(FileSystemEventHandler):
    def __init__(self):
        self.proceso = None
        self.iniciar()

    def iniciar(self):
        if self.proceso:
            self.proceso.kill()
        self.proceso = subprocess.Popen([sys.executable, "adviser_main.py"])

    def on_modified(self, event):
        # Reinicia al detectar cambios en el backend o en el frontend
        if event.src_path.endswith(("adviser_main.py", "ui.html", "script.js")):
            print(f"Cambio detectado en {os.path.basename(event.src_path)}, reiniciando...")
            self.iniciar()

reloader = Reloader()
observer = Observer()
observer.schedule(reloader, path=".", recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
    if reloader.proceso:
        reloader.proceso.kill()
observer.join()