import os
import sys

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
HORAS = list(range(24))

if getattr(sys, "frozen", False):
    _app_path = os.path.dirname(sys.executable)
    if not os.path.exists(os.path.join(_app_path, "ui.html")):
        _app_path = sys._MEIPASS
else:
    _app_path = os.path.dirname(os.path.abspath(__file__))

RUTA_JSON = os.path.join(_app_path, "rutina.json")
RUTA_ICON = os.path.join(_app_path, "icon.png")
RUTA_CONFIG = os.path.join(_app_path, "config.json")

def _ruta_web(nombre):
    ruta = os.path.join(_app_path, nombre)
    return "file:///" + ruta.replace("\\", "/")

RUTA_HTML = _ruta_web("ui.html")
RUTA_OVERLAY = _ruta_web("overlay.html")