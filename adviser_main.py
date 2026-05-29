import time
import sys
import os
import json
import queue
import threading
import requests
import webview

try:
    import win32gui
    import win32con
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False

import ctypes
import ctypes.wintypes
_SW_SHOWMINIMIZED = 2

def _hwnd_por_titulo(titulo):
    FindWindowW = ctypes.windll.user32.FindWindowW
    FindWindowW.restype = ctypes.wintypes.HWND
    return FindWindowW(None, titulo)

def _esta_minimizada_ctypes(titulo):
    try:
        hwnd = _hwnd_por_titulo(titulo)
        if not hwnd:
            return False
        class WINDOWPLACEMENT(ctypes.Structure):
            _fields_ = [
                ("length",           ctypes.c_uint),
                ("flags",            ctypes.c_uint),
                ("showCmd",          ctypes.c_uint),
                ("ptMinPosition",    ctypes.wintypes.POINT),
                ("ptMaxPosition",    ctypes.wintypes.POINT),
                ("rcNormalPosition", ctypes.wintypes.RECT),
            ]
        wp = WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(wp)
        ctypes.windll.user32.GetWindowPlacement(hwnd, ctypes.byref(wp))
        return wp.showCmd == _SW_SHOWMINIMIZED
    except Exception:
        return False

from winotify import Notification, audio
from datetime import datetime

# ─── Constantes ───────────────────────────────────────────────────────────────
DIAS  = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
HORAS = list(range(24))

if getattr(sys, 'frozen', False):
    _app_path = os.path.dirname(sys.executable)
    if not os.path.exists(os.path.join(_app_path, "ui.html")):
        _app_path = sys._MEIPASS
else:
    _app_path = os.path.dirname(os.path.abspath(__file__))

def _ruta_web(nombre):
    ruta = os.path.join(_app_path, nombre)
    return "file:///" + ruta.replace("\\", "/")

RUTA_JSON    = os.path.join(_app_path, "rutina.json")
RUTA_ICON    = os.path.join(_app_path, "icon.png")
RUTA_CONFIG  = os.path.join(_app_path, "config.json")
RUTA_HTML    = _ruta_web("ui.html")
RUTA_OVERLAY = _ruta_web("overlay.html")

# ─── Helpers ──────────────────────────────────────────────────────────────────
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

# ─── Cola para el hilo principal ──────────────────────────────────────────────
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


# ═════════════════════════════════════════════════════════════════════════════
#  OLLAMA — helpers
# ═════════════════════════════════════════════════════════════════════════════

def _ollama_chat(mensajes: list, config: dict) -> str:
    """Llama a /api/chat de Ollama con historial completo."""
    url    = config.get("ollama_url",    "http://localhost:11434")
    modelo = config.get("ollama_modelo", "llama3")
    r = requests.post(
        f"{url}/api/chat",
        json={"model": modelo, "messages": mensajes, "stream": False},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def _construir_system_prompt(rutina: dict, dia_actual: str, hora_actual: int) -> str:
    lineas = []
    for h, entrada in enumerate(rutina.get(dia_actual, [])):
        titulo = entrada[0] if entrada else "(Vacío)"
        if titulo != "(Vacío)":
            lineas.append(f"  {h:02d}:00 — {titulo}: {entrada[1]}")

    rutina_str = "\n".join(lineas) if lineas else "  (sin actividades cargadas)"

    return (
        "Sos Adviser, un asistente de productividad personal integrado en una app de rutinas. "
        "Hablás en español rioplatense, de forma directa, amigable y motivadora. "
        "Sos conciso: respondés en 2-4 oraciones salvo que el usuario pida más detalle.\n\n"
        f"Contexto actual:\n"
        f"- Día: {dia_actual.capitalize()}\n"
        f"- Hora: {hora_actual:02d}:00\n"
        f"- Rutina de hoy:\n{rutina_str}\n\n"
        "Podés hacer dos cosas:\n"
        "1. GENERAR TAREAS: cuando el usuario describa algo que necesita hacer, "
        "devolvé primero una respuesta breve y luego la lista marcada con '---TAREAS---' "
        "seguida de cada tarea en una línea separada, sin numeración ni guiones.\n"
        "2. CONVERSAR LIBREMENTE: respondé cualquier pregunta o charla.\n\n"
        "Usá el contexto de la rutina cuando sea relevante para responder con precisión."
    )


# ─── API ──────────────────────────────────────────────────────────────────────
class AdviserAPI:
    def __init__(self):
        self.bd           = cargar_json(RUTA_JSON, {})
        self.config       = cargar_json(RUTA_CONFIG, {
            "tema":          "dark",
            "ollama_url":    "http://localhost:11434",
            "ollama_modelo": "llama3",
        })
        self.running_flag = [False]
        self._window      = None

        self._crono = {
            "activo": False, "tareas": [],
            "segs_restantes": 0, "segs_total": 0,
        }
        self._overlay_win  = None
        self._overlay_open = False
        self._window_minimized = False
        self._window_closing   = False

        # Historial del chat IA
        self._chat_historial = []

    # ═══════════════════════════════ RUTINA ══════════════════════════════════
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

    # ════════════════════════════ ESTADO / CONFIG ═════════════════════════════
    def get_estado_inicial(self):
        ahora = datetime.now()
        return {
            "dia_actual":    DIAS[ahora.weekday()],
            "hora_actual":   ahora.hour,
            "fecha_str":     ahora.strftime("%A %d de %B").capitalize(),
            "tema":          self.config.get("tema", "dark"),
            "asistente":     self.running_flag[0],
            "ollama_url":    self.config.get("ollama_url",    "http://localhost:11434"),
            "ollama_modelo": self.config.get("ollama_modelo", "llama3"),
        }

    def get_hora_actual(self):
        ahora = datetime.now()
        return {"dia": DIAS[ahora.weekday()], "hora": ahora.hour, "min": ahora.minute}

    def guardar_tema(self, tema):
        self.config["tema"] = tema
        guardar_json(RUTA_CONFIG, self.config)
        return {"ok": True}

    def guardar_config_ollama(self, url, modelo):
        self.config["ollama_url"]    = url.strip()
        self.config["ollama_modelo"] = modelo.strip()
        guardar_json(RUTA_CONFIG, self.config)
        return {"ok": True}

    # ══════════════════════════════ ASISTENTE ═════════════════════════════════
    def toggle_asistente(self):
        if self.running_flag[0]:
            self.running_flag[0] = False
            return {"ok": True, "estado": False}
        self.running_flag[0] = True
        threading.Thread(target=self._loop_asistente, daemon=True).start()
        return {"ok": True, "estado": True}

    def _loop_asistente(self):
        while self.running_flag[0]:
            ahora  = datetime.now()
            dia    = DIAS[ahora.weekday()]
            hora   = ahora.hour
            minuto = ahora.minute
            seg    = ahora.second
            titulo  = "(Vacío)"
            mensaje = "Sin actividad asignada"
            if dia in self.bd and hora < len(self.bd[dia]):
                titulo  = self.bd[dia][hora][0]
                mensaje = self.bd[dia][hora][1]
            _toast(titulo, mensaje)
            if self._window:
                try:
                    self._window.evaluate_js(
                        f"window._onAsistenteHora && window._onAsistenteHora({hora})"
                    )
                except Exception:
                    pass
            espera = 3600 - (minuto * 60 + seg)
            for _ in range(espera + 2):
                if not self.running_flag[0]:
                    break
                time.sleep(1)

    # ══════════════════════════════ CRONÓMETRO ════════════════════════════════
    def crono_iniciar(self, tareas_json, segs_total):
        tareas = json.loads(tareas_json) if isinstance(tareas_json, str) else list(tareas_json)
        self._crono.update({"activo": True, "tareas": tareas,
                            "segs_restantes": int(segs_total), "segs_total": int(segs_total)})
        threading.Thread(target=self._loop_crono, daemon=True).start()
        return {"ok": True}

    def crono_toggle_tarea(self, idx, done):
        try:
            self._crono["tareas"][int(idx)]["done"] = bool(done)
            self._push_overlay()
            return {"ok": True}
        except Exception:
            return {"ok": False}

    def crono_agregar_tarea(self, texto):
        try:
            self._crono["tareas"].append({"texto": texto, "done": False})
            self._push_overlay()
            return {"ok": True, "total": len(self._crono["tareas"])}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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

    # ══════════════════════════════ IA — CHAT ═════════════════════════════════
    def ia_enviar_mensaje(self, texto: str):
        texto = texto.strip()
        if not texto:
            return {"ok": False, "error": "Mensaje vacío"}
        self._chat_historial.append({"role": "user", "content": texto})
        threading.Thread(target=self._ollama_worker, daemon=True).start()
        return {"ok": True}

    def _ollama_worker(self):
        try:
            ahora = datetime.now()
            dia   = DIAS[ahora.weekday()]
            hora  = ahora.hour
            system_prompt = _construir_system_prompt(self.bd, dia, hora)
            mensajes = [{"role": "system", "content": system_prompt}] + self._chat_historial
            respuesta = _ollama_chat(mensajes, self.config)
            self._chat_historial.append({"role": "assistant", "content": respuesta})

            # Detectar lista de tareas en la respuesta
            if "---TAREAS---" in respuesta:
                partes = respuesta.split("---TAREAS---", 1)
                respuesta_limpia = partes[0].strip()
                tareas = [l.strip() for l in partes[1].splitlines() if l.strip()]
            else:
                respuesta_limpia = respuesta
                tareas = []

            resp_js   = json.dumps(respuesta_limpia)
            tareas_js = json.dumps(tareas, ensure_ascii=False)

            if self._window:
                self._window.evaluate_js(
                    f"window._iaRespuesta && window._iaRespuesta({resp_js}, {tareas_js})"
                )

        except requests.exceptions.ConnectionError:
            url = self.config.get("ollama_url", "http://localhost:11434")
            err = json.dumps(f"No pude conectarme a Ollama en {url}. ¿Está corriendo?")
            if self._chat_historial and self._chat_historial[-1]["role"] == "user":
                self._chat_historial.pop()
            if self._window:
                self._window.evaluate_js(f"window._iaError && window._iaError({err})")

        except Exception as e:
            err = json.dumps(f"Error inesperado: {str(e)}")
            if self._chat_historial and self._chat_historial[-1]["role"] == "user":
                self._chat_historial.pop()
            if self._window:
                self._window.evaluate_js(f"window._iaError && window._iaError({err})")

    def ia_limpiar_historial(self):
        self._chat_historial = []
        return {"ok": True}

    # ═══════════════════════════════ OVERLAY ═════════════════════════════════
    def overlay_get_estado(self):
        tareas = self._crono["tareas"]
        hechas = sum(1 for t in tareas if t.get("done", False))
        return {
            "segs_restantes": self._crono["segs_restantes"],
            "segs_total":     self._crono["segs_total"],
            "hechas": hechas, "total": len(tareas),
            "tareas": tareas, "tema": self.config.get("tema", "dark"),
        }

    def overlay_restaurar_app(self):
        if self._window:
            try:
                self._window.restore()
            except Exception:
                pass
        return {"ok": True}

    def overlay_cerrar(self):
        _main_queue.put(self._destruir_overlay)
        return {"ok": True}

    def overlay_set_height(self, height):
        ov = self._overlay_win
        if ov is None:
            return {"ok": False}
        def _resize():
            try:
                ov.resize(ov.width, int(height))
            except Exception:
                pass
        _main_queue.put(_resize)
        return {"ok": True}

    def overlay_resize(self, width, height):
        ov = self._overlay_win
        if ov is None:
            return {"ok": False}
        w, h = max(200, int(width)), max(120, int(height))
        def _resize():
            try:
                ov.resize(w, h)
            except Exception:
                pass
        _main_queue.put(_resize)
        return {"ok": True}

    # ════════════════════════ DETECCIÓN VENTANA ═══════════════════════════════
    def iniciar_monitor_ventana(self):
        threading.Thread(target=self._poll_ventana, daemon=True).start()

    def _poll_ventana(self):
        prev_minimized = False
        while not self._window_closing:
            time.sleep(0.5)
            try:
                is_min = self._es_ventana_minimizada()
            except Exception:
                continue
            if is_min == prev_minimized:
                continue
            prev_minimized = is_min
            if is_min:
                self._window_minimized = True
                if self._crono["activo"]:
                    _main_queue.put(self._crear_overlay)
            else:
                self._window_minimized = False
                _main_queue.put(self._destruir_overlay)

    def _es_ventana_minimizada(self):
        if self._window is None:
            return False
        if _WIN32_AVAILABLE:
            try:
                hwnd = win32gui.FindWindow(None, "Adviser")
                if not hwnd:
                    return False
                return win32gui.GetWindowPlacement(hwnd)[1] == win32con.SW_SHOWMINIMIZED
            except Exception:
                pass
        return _esta_minimizada_ctypes("Adviser")

    def on_main_minimized(self): pass
    def on_main_closed(self):
        self._window_closing   = True
        self._window_minimized = False
    def on_main_restored(self): pass

    # ════════════════════════ HELPERS HILO PRINCIPAL ══════════════════════════
    def _crear_overlay(self):
        if self._overlay_open:
            return
        try:
            ov = webview.create_window(
                title="Adviser · Cronómetro", url=RUTA_OVERLAY, js_api=self,
                width=250, height=150, resizable=True, frameless=True,
                on_top=True, background_color="#0D1018",
            )
            self._overlay_win  = ov
            self._overlay_open = True
            def _on_closed():
                self._overlay_win  = None
                self._overlay_open = False
            ov.events.closed += _on_closed
        except Exception as e:
            print(f"[Adviser] Error al crear overlay: {e}")

    def _destruir_overlay(self):
        if self._overlay_win is not None:
            try:
                self._overlay_win.destroy()
            except Exception:
                pass
        self._overlay_win  = None
        self._overlay_open = False

    def _push_overlay(self):
        ov = self._overlay_win
        if ov is None:
            return
        try:
            segs   = self._crono["segs_restantes"]
            tareas = self._crono["tareas"]
            hechas = sum(1 for t in tareas if t.get("done", False))
            ov.evaluate_js(
                f"window._ovTick && window._ovTick({segs}, {hechas}, "
                f"{len(tareas)}, {json.dumps(tareas)})"
            )
        except Exception:
            pass


# ─── Loop principal ───────────────────────────────────────────────────────────
def _main_loop(api):
    while True:
        time.sleep(0.2)
        _drain_queue()


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    api    = AdviserAPI()
    window = webview.create_window(
        title="Adviser", url=RUTA_HTML, js_api=api,
        width=960, height=680, min_size=(820, 560),
        frameless=False, resizable=True, background_color="#080A0F",
    )
    api._window = window
    window.events.minimized += api.on_main_minimized
    window.events.restored  += api.on_main_restored
    window.events.closed    += api.on_main_closed
    window.events.loaded    += lambda: api.iniciar_monitor_ventana()
    webview.start(_main_loop, api, debug=False)
