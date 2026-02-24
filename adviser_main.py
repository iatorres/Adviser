import time
import sys
import os
import json
import queue
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

RUTA_JSON    = os.path.join(_app_path, "rutina.json")
RUTA_ICON    = os.path.join(_app_path, "icon.png")
RUTA_CONFIG  = os.path.join(_app_path, "config.json")
RUTA_HTML    = os.path.join(_app_path, "ui.html")
RUTA_OVERLAY = os.path.join(_app_path, "overlay.html")


# ─── Helpers ─────────────────────────────────────────────────────────────────
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

def _toast(titulo, mensaje, loop=True):
    try:
        t = Notification(app_id="Adviser", title=titulo, msg=mensaje,
                         duration="long", icon=RUTA_ICON)
        t.set_audio(audio.LoopingCall if loop else audio.Reminder, loop=loop)
        t.show()
    except Exception:
        pass


# ─── Cola para el hilo principal ─────────────────────────────────────────────
# PROBLEMA RAÍZ: webview.create_window() y window.destroy() SOLO pueden
# llamarse desde el hilo principal de pywebview. Usar un threading.Thread
# para crearlos falla silenciosamente.
# SOLUCIÓN: una cola que el loop principal drena cada 200ms.
_main_queue = queue.Queue()

def _drain_queue():
    while True:
        try:
            fn = _main_queue.get_nowait()
            fn()
        except queue.Empty:
            break
        except Exception as e:
            print(f"[Adviser queue] Error: {e}")


# ─── API ──────────────────────────────────────────────────────────────────────
class AdviserAPI:
    def __init__(self):
        self.bd           = cargar_json(RUTA_JSON, {})
        self.config       = cargar_json(RUTA_CONFIG, {"tema": "dark"})
        self.running_flag = [False]
        self._window      = None

        self._crono = {
            "activo":         False,
            "tareas":         [],
            "segs_restantes": 0,
            "segs_total":     0,
        }
        self._overlay_win  = None
        self._overlay_open = False

    # ═════════════════════════════════════════════════════════════════════════
    #  RUTINA
    # ═════════════════════════════════════════════════════════════════════════
    def get_rutina(self):
        for dia in DIAS:
            inicializar_dia(self.bd, dia)
        return self.bd

    def get_dia(self, dia):
        return inicializar_dia(self.bd, dia)

    def guardar_dia(self, dia, entradas):
        try:
            self.bd[dia] = [[e[0], e[1]] for e in entradas]
            guardar_json(RUTA_JSON, self.bd)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ═════════════════════════════════════════════════════════════════════════
    #  ESTADO / CONFIG
    # ═════════════════════════════════════════════════════════════════════════
    def get_estado_inicial(self):
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
        return {"dia": DIAS[ahora.weekday()], "hora": ahora.hour, "min": ahora.minute}

    def guardar_tema(self, tema):
        self.config["tema"] = tema
        guardar_json(RUTA_CONFIG, self.config)
        return {"ok": True}

    # ═════════════════════════════════════════════════════════════════════════
    #  ASISTENTE
    # ═════════════════════════════════════════════════════════════════════════
    def toggle_asistente(self):
        if self.running_flag[0]:
            self.running_flag[0] = False
            return {"ok": True, "estado": False}
        self.running_flag[0] = True
        threading.Thread(target=self._loop_asistente, daemon=True).start()
        return {"ok": True, "estado": True}

    def _loop_asistente(self):
        while self.running_flag[0]:
            ahora   = datetime.now()
            dia     = DIAS[ahora.weekday()]
            hora    = ahora.hour
            minuto  = ahora.minute
            segundo = ahora.second
            if dia in self.bd and hora < len(self.bd[dia]):
                _toast(self.bd[dia][hora][0], self.bd[dia][hora][1])
            if self._window:
                try:
                    self._window.evaluate_js(
                        f"window._onAsistenteHora && window._onAsistenteHora({hora})"
                    )
                except Exception:
                    pass
            espera = 3600 - (minuto * 60 + segundo)
            for _ in range(espera + 2):
                if not self.running_flag[0]:
                    break
                time.sleep(1)

    # ═════════════════════════════════════════════════════════════════════════
    #  CRONÓMETRO
    # ═════════════════════════════════════════════════════════════════════════
    def crono_iniciar(self, tareas_json, segs_total):
        tareas = json.loads(tareas_json) if isinstance(tareas_json, str) else list(tareas_json)
        self._crono["activo"]         = True
        self._crono["tareas"]         = tareas
        self._crono["segs_restantes"] = int(segs_total)
        self._crono["segs_total"]     = int(segs_total)
        threading.Thread(target=self._loop_crono, daemon=True).start()
        return {"ok": True}

    def crono_toggle_tarea(self, idx, done):
        try:
            self._crono["tareas"][int(idx)]["done"] = bool(done)
            self._push_overlay()
            return {"ok": True}
        except Exception:
            return {"ok": False}

    def crono_finalizar(self):
        self._crono["activo"] = False
        _main_queue.put(self._destruir_overlay)
        return {"ok": True}

    def crono_cancelar(self):
        self._crono["activo"] = False
        _main_queue.put(self._destruir_overlay)
        return {"ok": True}

    def notificar_alarma_crono(self, titulo, mensaje):
        _toast(titulo, mensaje, loop=False)
        return {"ok": True}

    def _loop_crono(self):
        while self._crono["activo"] and self._crono["segs_restantes"] > 0:
            time.sleep(1)
            if not self._crono["activo"]:
                return
            self._crono["segs_restantes"] -= 1

            if self._window:
                try:
                    segs = self._crono["segs_restantes"]
                    self._window.evaluate_js(
                        f"window._cronoPythonTick && window._cronoPythonTick({segs})"
                    )
                except Exception:
                    pass

            self._push_overlay()

        if self._crono["activo"] and self._crono["segs_restantes"] <= 0:
            self._crono["activo"] = False
            todas = all(t.get("done", False) for t in self._crono["tareas"])
            if not todas:
                _toast("⏰ ¡Tiempo agotado!", "No completaste todas las tareas.", loop=False)
                if self._window:
                    try:
                        self._window.evaluate_js(
                            "window._cronoTiempoAgotado && window._cronoTiempoAgotado()"
                        )
                    except Exception:
                        pass
            _main_queue.put(self._destruir_overlay)

    # ═════════════════════════════════════════════════════════════════════════
    #  OVERLAY API (llamada desde overlay.html)
    # ═════════════════════════════════════════════════════════════════════════
    def overlay_get_estado(self):
        tareas = self._crono["tareas"]
        hechas = sum(1 for t in tareas if t.get("done", False))
        return {
            "segs_restantes": self._crono["segs_restantes"],
            "segs_total":     self._crono["segs_total"],
            "hechas":         hechas,
            "total":          len(tareas),
            "tema":           self.config.get("tema", "dark"),
        }

    def overlay_restaurar_app(self):
        if self._window:
            try:
                self._window.restore()
            except Exception:
                pass
        return {"ok": True}

    def overlay_cerrar(self):
        """El usuario cerró el overlay manualmente desde el botón ✕."""
        _main_queue.put(self._destruir_overlay)
        return {"ok": True}

    def overlay_set_height(self, height):
        """Redimensiona la ventana overlay al colapsar/expandir."""
        ov = self._overlay_win
        if ov is None:
            return {"ok": False}
        def _resize():
            try:
                ov.resize(300, int(height))
            except Exception as e:
                print(f"[Adviser] Error resize overlay: {e}")
        _main_queue.put(_resize)
        return {"ok": True}

    # ═════════════════════════════════════════════════════════════════════════
    #  EVENTOS DE VENTANA PRINCIPAL
    # ═════════════════════════════════════════════════════════════════════════
    def on_main_minimized(self):
        """Evento pywebview: ventana principal minimizada."""
        if self._crono["activo"]:
            _main_queue.put(self._crear_overlay)

    def on_main_restored(self):
        """Evento pywebview: ventana principal restaurada."""
        _main_queue.put(self._destruir_overlay)

    # ═════════════════════════════════════════════════════════════════════════
    #  HELPERS QUE DEBEN CORRER EN EL HILO PRINCIPAL
    # ═════════════════════════════════════════════════════════════════════════
    def _crear_overlay(self):
        """Crea la ventana overlay. SOLO llamar desde el hilo principal."""
        if self._overlay_open:
            return
        try:
            ov = webview.create_window(
                title            = "Adviser Overlay",
                url              = RUTA_OVERLAY,
                js_api           = self,
                width            = 300,
                height           = 380,
                resizable        = False,
                frameless        = True,
                on_top           = True,
                background_color = "#080A0F",
                shadow           = True,
            )
            self._overlay_win  = ov
            self._overlay_open = True
            print("[Adviser] Overlay abierto.")
        except Exception as e:
            print(f"[Adviser] Error al crear overlay: {e}")

    def _destruir_overlay(self):
        """Destruye la ventana overlay. SOLO llamar desde el hilo principal."""
        if self._overlay_win is not None:
            try:
                self._overlay_win.destroy()
                print("[Adviser] Overlay cerrado.")
            except Exception as e:
                print(f"[Adviser] Error al cerrar overlay: {e}")
        self._overlay_win  = None
        self._overlay_open = False

    def _push_overlay(self):
        """Envía tick al overlay. Puede llamarse desde cualquier hilo."""
        ov = self._overlay_win
        if ov is None:
            return
        try:
            segs   = self._crono["segs_restantes"]
            hechas = sum(1 for t in self._crono["tareas"] if t.get("done", False))
            total  = len(self._crono["tareas"])
            ov.evaluate_js(
                f"window._ovTick && window._ovTick({segs}, {hechas}, {total})"
            )
        except Exception:
            pass


# ─── Loop del hilo principal (drena la cola) ──────────────────────────────────
def _main_loop(api):
    """
    Se pasa como `func` a webview.start(). Corre en el hilo principal de pywebview,
    lo que hace seguro llamar create_window() y destroy() desde aquí.
    """
    while True:
        time.sleep(0.2)
        _drain_queue()


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    api    = AdviserAPI()
    window = webview.create_window(
        title            = "Adviser",
        url              = RUTA_HTML,
        js_api           = api,
        width            = 960,
        height           = 680,
        min_size         = (820, 560),
        frameless        = False,
        resizable        = True,
        background_color = "#080A0F",
    )
    api._window = window

    window.events.minimized += api.on_main_minimized
    window.events.restored  += api.on_main_restored

    # func= corre en el hilo principal → puede crear/destruir ventanas de forma segura
    webview.start(_main_loop, api, debug=False)
