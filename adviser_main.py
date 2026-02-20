import time
import sys
import os
import json
import threading
import webview

from winotify import Notification, audio
from datetime import datetime

# ─── Constantes ───────────────────────────────────────────────────────────────
DIAS  = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
HORAS = list(range(24))

if getattr(sys, 'frozen', False):
    _app_path = os.path.dirname(sys.executable)
else:
    _app_path = os.path.dirname(os.path.abspath(__file__))

RUTA_JSON   = os.path.join(_app_path, "rutina.json")
RUTA_ICON   = os.path.join(_app_path, "icon.png")
RUTA_CONFIG = os.path.join(_app_path, "config.json")
RUTA_HTML   = os.path.join(_app_path, "ui.html")


# ─── Lógica de datos ──────────────────────────────────────────────────────────
def cargar_json(ruta, default):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def guardar_json(ruta, datos):
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def inicializar_dia(bd, dia):
    vacio = ["(Vacío)", "Sin actividad asignada"]
    if dia not in bd:
        bd[dia] = [list(vacio) for _ in HORAS]
    elif len(bd[dia]) != len(HORAS):
        while len(bd[dia]) < len(HORAS):
            bd[dia].append(list(vacio))
        bd[dia] = bd[dia][:len(HORAS)]
    return bd[dia]


# ─── Notificaciones ────────────────────────────────────────────────────────────
def _toast(titulo, mensaje):
    try:
        t = Notification(app_id="Adviser", title=titulo, msg=mensaje,
                         duration="long", icon=RUTA_ICON)
        t.set_audio(audio.LoopingCall, loop=True)
        t.show()
    except Exception:
        pass


# ─── JS API — puente Python ↔ JS ─────────────────────────────────────────────
# Todos los métodos públicos de esta clase son llamables desde JS via:
#   window.pywebview.api.nombre_metodo(args)
class AdviserAPI:
    def __init__(self):
        self.bd           = cargar_json(RUTA_JSON, {})
        self.config       = cargar_json(RUTA_CONFIG, {"tema": "dark"})
        self.running_flag = [False]
        self.hilo         = None
        self._window      = None   # se asigna después de crear la ventana

    # ── Rutina ────────────────────────────────────────────────────────────────
    def get_rutina(self):
        """Devuelve toda la rutina al JS."""
        # Asegurarse de que todos los días estén inicializados a 24h
        for dia in DIAS:
            inicializar_dia(self.bd, dia)
        return self.bd

    def get_dia(self, dia):
        """Devuelve las 24 entradas de un día específico."""
        lista = inicializar_dia(self.bd, dia)
        return lista

    def guardar_dia(self, dia, entradas):
        """Recibe lista de [titulo, mensaje] x 24 y guarda."""
        try:
            self.bd[dia] = [[e[0], e[1]] for e in entradas]
            guardar_json(RUTA_JSON, self.bd)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Estado del sistema ────────────────────────────────────────────────────
    def get_estado_inicial(self):
        """Estado completo para el arranque de la UI."""
        ahora = datetime.now()
        return {
            "dia_actual":  DIAS[ahora.weekday()],
            "hora_actual": ahora.hour,
            "fecha_str":   ahora.strftime("%A %d de %B").capitalize(),
            "tema":        self.config.get("tema", "dark"),
            "asistente":   self.running_flag[0],
        }

    def get_hora_actual(self):
        ahora = datetime.now()
        return {
            "dia":  DIAS[ahora.weekday()],
            "hora": ahora.hour,
            "min":  ahora.minute,
        }

    # ── Configuración ─────────────────────────────────────────────────────────
    def guardar_tema(self, tema):
        self.config["tema"] = tema
        guardar_json(RUTA_CONFIG, self.config)
        return {"ok": True}

    # ── Control del asistente ─────────────────────────────────────────────────
    def iniciar_asistente(self):
        if self.running_flag[0]:
            return {"ok": False, "msg": "Ya está corriendo"}
        self.running_flag[0] = True
        self.hilo = threading.Thread(target=self._loop, daemon=True)
        self.hilo.start()
        return {"ok": True, "estado": True}

    def detener_asistente(self):
        self.running_flag[0] = False
        return {"ok": True, "estado": False}

    def toggle_asistente(self):
        if self.running_flag[0]:
            return self.detener_asistente()
        return self.iniciar_asistente()

    def _loop(self):
        """Hilo de fondo: dispara toast en cada hora y actualiza la UI via JS."""
        while self.running_flag[0]:
            ahora   = datetime.now()
            dia     = DIAS[ahora.weekday()]
            hora    = ahora.hour
            minuto  = ahora.minute
            segundo = ahora.second

            bd = self.bd
            if dia in bd:
                lista = bd[dia]
                pos   = hora  # índice = hora (0-23)
                if pos < len(lista):
                    _toast(lista[pos][0], lista[pos][1])

            # Notificar al JS para que actualice el badge de estado
            if self._window:
                self._window.evaluate_js(
                    f"window._onAsistenteHora && window._onAsistenteHora({hora})"
                )

            # Esperar al próximo cambio de hora
            tiempo_espera = 3600 - (minuto * 60 + segundo)
            for _ in range(tiempo_espera + 2):
                if not self.running_flag[0]:
                    break
                time.sleep(1)


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    api    = AdviserAPI()
    window = webview.create_window(
        title       = "Adviser",
        url         = RUTA_HTML,
        js_api      = api,
        width       = 960,
        height      = 680,
        min_size    = (820, 560),
        frameless   = False,
        resizable   = True,
        background_color = "#080A0F",
    )
    api._window = window
    webview.start(debug=False)
