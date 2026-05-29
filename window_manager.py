import time
import json
import threading
import webview

try:
    import win32gui
    import win32con
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False

import ctypes
import ctypes.wintypes

from constants import RUTA_OVERLAY
from utils import get_main_queue

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
                ("length", ctypes.c_uint),
                ("flags", ctypes.c_uint),
                ("showCmd", ctypes.c_uint),
                ("ptMinPosition", ctypes.wintypes.POINT),
                ("ptMaxPosition", ctypes.wintypes.POINT),
                ("rcNormalPosition", ctypes.wintypes.RECT),
            ]

        wp = WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(wp)
        ctypes.windll.user32.GetWindowPlacement(hwnd, ctypes.byref(wp))
        return wp.showCmd == _SW_SHOWMINIMIZED
    except Exception:
        return False

class WindowManager:
    def __init__(self, main_window_ref, crono_service_ref, config_manager_ref):
        self._main_window = main_window_ref
        self._crono_service = crono_service_ref
        self._config_manager = config_manager_ref
        self._overlay_win = None
        self._overlay_open = False
        self._window_minimized = False
        self._window_closing = False
        self._main_queue = get_main_queue()

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

            if is_min == prev_minimized: continue
            prev_minimized = is_min

            if is_min:
                self._window_minimized = True
                if self._crono_service.get_crono_state()["activo"]:
                    self._main_queue.put(self.create_overlay)
            else:
                self._window_minimized = False
                self._main_queue.put(self.destroy_overlay)

    def _es_ventana_minimizada(self):
        if self._main_window is None: return False
        if _WIN32_AVAILABLE:
            try:
                hwnd = win32gui.FindWindow(None, "Adviser")
                if not hwnd: return False
                return win32gui.GetWindowPlacement(hwnd)[1] == win32con.SW_SHOWMINIMIZED
            except Exception: pass
        return _esta_minimizada_ctypes("Adviser")

    def create_overlay(self):
        if self._overlay_open: return
        try:
            ov = webview.create_window(title="Adviser · Cronómetro", url=RUTA_OVERLAY, js_api=self._main_window.api,
                                       width=250, height=150, resizable=True, frameless=True, on_top=True,
                                       background_color="#0D1018")
            self._overlay_win = ov
            self._overlay_open = True
            ov.events.closed += lambda: setattr(self, '_overlay_open', False)
        except Exception as e: print(f"[Adviser] Error al crear overlay: {e}")

    def destroy_overlay(self):
        if self._overlay_win is not None:
            try: self._overlay_win.destroy()
            except Exception: pass
        self._overlay_win = None
        self._overlay_open = False

    def update_overlay_state(self, crono_state):
        ov = self._overlay_win
        if ov is None: return
        try:
            segs = crono_state["segs_restantes"]
            tareas = crono_state["tareas"]
            hechas = sum(1 for t in tareas if t.get("done", False))
            ov.evaluate_js(f"window._ovTick && window._ovTick({segs}, {hechas}, {len(tareas)}, {json.dumps(tareas, ensure_ascii=False)})")
        except Exception: pass

    def overlay_get_estado(self):
        crono_state = self._crono_service.get_crono_state()
        tareas = crono_state["tareas"]
        hechas = sum(1 for t in tareas if t.get("done", False))
        return {
            "segs_restantes": crono_state["segs_restantes"],
            "segs_total": crono_state["segs_total"],
            "hechas": hechas,
            "total": len(tareas),
            "tareas": tareas,
            "tema": self._config_manager.get_config().get("tema", "dark"),
        }

    def overlay_restaurar_app(self):
        if self._main_window:
            try: self._main_window.restore()
            except Exception: pass
        return {"ok": True}

    def overlay_cerrar(self):
        self._main_queue.put(self.destroy_overlay)
        return {"ok": True}

    def overlay_set_height(self, height):
        ov = self._overlay_win
        if ov is None: return {"ok": False}
        def _resize():
            try: ov.resize(ov.width, int(height))
            except Exception: pass
        self._main_queue.put(_resize)
        return {"ok": True}

    def overlay_resize(self, width, height):
        ov = self._overlay_win
        if ov is None: return {"ok": False}
        w, h = max(200, int(width)), max(120, int(height))
        def _resize():
            try: ov.resize(w, h)
            except Exception: pass
        self._main_queue.put(_resize)
        return {"ok": True}

    def on_main_closed(self):
        self._window_closing = True
        self._window_minimized = False