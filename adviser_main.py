import time
import sys
import os
import json
import queue
import threading
import webview

# win32gui es parte de pywin32. Si no está, usamos ctypes como fallback
# (ctypes siempre está disponible en Windows sin instalar nada extra).
try:
    import win32gui
    import win32con
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False

# Fallback via ctypes — funciona sin pywin32
import ctypes
import ctypes.wintypes
_SW_SHOWMINIMIZED = 2

def _hwnd_por_titulo(titulo):
    """Busca un HWND por título de ventana usando ctypes puro."""
    result = ctypes.c_ulong(0)
    FindWindowW = ctypes.windll.user32.FindWindowW
    FindWindowW.restype = ctypes.wintypes.HWND
    hwnd = FindWindowW(None, titulo)
    return hwnd

def _esta_minimizada_ctypes(titulo):
    """Detecta si una ventana está minimizada usando ctypes (sin pywin32)."""
    try:
        hwnd = _hwnd_por_titulo(titulo)
        if not hwnd:
            return False
        # GetWindowPlacement via ctypes
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
else:
    _app_path = os.path.dirname(os.path.abspath(__file__))

RUTA_JSON    = os.path.join(_app_path, "rutina.json")
RUTA_ICON    = os.path.join(_app_path, "icon.png")
RUTA_CONFIG  = os.path.join(_app_path, "config.json")
RUTA_HTML    = os.path.join(_app_path, "ui.html")
RUTA_OVERLAY = os.path.join(_app_path, "overlay.html")
RUTA_RUTINA_OVERLAY = os.path.join(_app_path, "rutina_overlay.html")


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

        # Overlay de rutina (recordatorio de tarea actual)
        self._window_minimized    = False   # True cuando está minimizada
        self._window_closing      = False   # True cuando se está cerrando (no abrir overlay)
        self._rutina_overlay_win   = None
        self._rutina_overlay_datos = {"hora_str": "--:00", "titulo": "", "mensaje": ""}

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

            titulo  = "(Vacío)"
            mensaje = "Sin actividad asignada"
            if dia in self.bd and hora < len(self.bd[dia]):
                titulo  = self.bd[dia][hora][0]
                mensaje = self.bd[dia][hora][1]

            # 1. Mostrar notificación de Windows
            _toast(titulo, mensaje)

            # 2. Notificar a la ventana principal (resalta hora actual)
            if self._window:
                try:
                    self._window.evaluate_js(
                        f"window._onAsistenteHora && window._onAsistenteHora({hora})"
                    )
                except Exception:
                    pass

            # 3. Guardar datos de la tarea actual para el overlay
            hora_str = f"{str(hora).zfill(2)}:00"
            self._rutina_overlay_datos = {
                "hora_str": hora_str,
                "titulo":   titulo,
                "mensaje":  mensaje,
            }

            # 4. Esperar 4s y abrir el overlay SOLO si la app está minimizada
            def _abrir_si_minimizada():
                if self._window_minimized:
                    _main_queue.put(self._crear_rutina_overlay)

            t = threading.Timer(4.0, _abrir_si_minimizada)
            t.daemon = True
            t.start()

            espera = 3600 - (minuto * 60 + segundo)
            for _ in range(espera + 2):
                if not self.running_flag[0]:
                    break
                time.sleep(1)

            # 5. Al cumplirse la hora → cerrar el overlay (ya llega uno nuevo)
            _main_queue.put(self._destruir_rutina_overlay)

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
    #  OVERLAY DE RUTINA — llamado desde rutina_overlay.html
    # ═════════════════════════════════════════════════════════════════════════
    def rutina_overlay_get_datos(self):
        """El overlay de rutina solicita sus datos al abrirse."""
        return {
            **self._rutina_overlay_datos,
            "tema": self.config.get("tema", "dark"),
        }

    def rutina_overlay_cerrar(self):
        """El usuario cerró el overlay de rutina."""
        _main_queue.put(self._destruir_rutina_overlay)
        return {"ok": True}

    def rutina_overlay_abrir_app(self):
        """El usuario pulsó 'Abrir Adviser' en el overlay de rutina."""
        if self._window:
            try:
                self._window.restore()
            except Exception:
                pass
        _main_queue.put(self._destruir_rutina_overlay)
        return {"ok": True}

    def _crear_rutina_overlay(self):
        """Crea la ventana del overlay de rutina. SOLO desde el hilo principal."""
        # Si ya hay uno abierto, destruirlo primero (nueva hora, nuevo overlay)
        if self._rutina_overlay_win is not None:
            try:
                self._rutina_overlay_win.destroy()
            except Exception:
                pass
            self._rutina_overlay_win = None

        try:
            ov = webview.create_window(
                title            = "Adviser Rutina",
                url              = RUTA_RUTINA_OVERLAY,
                js_api           = self,
                width            = 320,
                height           = 110,
                resizable        = False,
                frameless        = True,
                on_top           = True,
                background_color = "#080A0F",
                shadow           = True,
            )
            self._rutina_overlay_win = ov
            print(f"[Adviser] Overlay rutina abierto: {self._rutina_overlay_datos['hora_str']}")
        except Exception as e:
            print(f"[Adviser] Error al crear overlay rutina: {e}")

    def _destruir_rutina_overlay(self):
        """Destruye el overlay de rutina. SOLO desde el hilo principal."""
        if self._rutina_overlay_win is not None:
            try:
                self._rutina_overlay_win.destroy()
            except Exception:
                pass
            self._rutina_overlay_win = None
            print("[Adviser] Overlay rutina cerrado.")

    # ═════════════════════════════════════════════════════════════════════════
    #  DETECCIÓN DE ESTADO DE VENTANA (polling via win32gui)
    # ═════════════════════════════════════════════════════════════════════════
    def iniciar_monitor_ventana(self):
        """Lanza un hilo que detecta minimizar/restaurar via win32gui."""
        t = threading.Thread(target=self._poll_ventana, daemon=True)
        t.start()

    def _poll_ventana(self):
        """Polling cada 500ms del estado real de la ventana via win32gui."""
        prev_minimized = False
        print("[Adviser] Monitor de ventana iniciado.")

        while not self._window_closing:
            time.sleep(0.5)
            try:
                is_min = self._es_ventana_minimizada()
            except Exception as e:
                print(f"[Adviser] Error en poll: {e}")
                continue

            if is_min == prev_minimized:
                continue

            prev_minimized = is_min
            print(f"[Adviser] Estado ventana → {'MINIMIZADA' if is_min else 'RESTAURADA'}")

            if is_min:
                self._window_minimized = True
                # Overlay cronómetro
                if self._crono["activo"]:
                    _main_queue.put(self._crear_overlay)
                # Overlay rutina — cargar tarea actual al momento de minimizar
                if self.running_flag[0]:
                    self._actualizar_datos_rutina_ahora()
                    _main_queue.put(self._crear_rutina_overlay)
            else:
                self._window_minimized = False
                _main_queue.put(self._destruir_overlay)
                _main_queue.put(self._destruir_rutina_overlay)

    def _actualizar_datos_rutina_ahora(self):
        """Carga la tarea de la hora actual en _rutina_overlay_datos."""
        ahora   = datetime.now()
        dia     = DIAS[ahora.weekday()]
        hora    = ahora.hour
        hora_str = f"{str(hora).zfill(2)}:00"
        titulo  = "(Vacío)"
        mensaje = "Sin actividad asignada"
        if dia in self.bd and hora < len(self.bd[dia]):
            entrada = self.bd[dia][hora]
            if entrada and len(entrada) >= 2:
                titulo  = entrada[0] or "(Vacío)"
                mensaje = entrada[1] or "Sin actividad asignada"
        self._rutina_overlay_datos = {
            "hora_str": hora_str,
            "titulo":   titulo,
            "mensaje":  mensaje,
        }
        print(f"[Adviser] Datos rutina: {hora_str} — {titulo}")

    def _es_ventana_minimizada(self):
        """Devuelve True si la ventana principal está minimizada.
        Usa win32gui si está disponible, si no cae a ctypes puro.
        """
        if self._window is None:
            return False
        if _WIN32_AVAILABLE:
            try:
                hwnd = win32gui.FindWindow(None, "Adviser")
                if not hwnd:
                    return False
                placement = win32gui.GetWindowPlacement(hwnd)
                return placement[1] == win32con.SW_SHOWMINIMIZED
            except Exception:
                pass
        # Fallback ctypes (siempre disponible en Windows)
        return _esta_minimizada_ctypes("Adviser")

    # Mantener estos handlers para compatibilidad (pywebview los llama igual)
    def on_main_minimized(self):
        pass  # reemplazado por polling

    def on_main_closed(self):
        self._window_closing   = True
        self._window_minimized = False

    def on_main_restored(self):
        pass  # reemplazado por polling

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
    window.events.closed    += api.on_main_closed

    # Arrancar monitor de ventana (polling win32gui) una vez que webview esté listo
    def _on_loaded():
        api.iniciar_monitor_ventana()

    window.events.loaded += _on_loaded

    # func= corre en el hilo principal → puede crear/destruir ventanas de forma segura
    webview.start(_main_loop, api, debug=False)
