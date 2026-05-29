import time
import json
import threading
from utils import show_toast, get_main_queue

class ChronometerService:
    def __init__(self, window_ref, window_manager_ref):
        self._crono = {
            "activo": False,
            "tareas": [],
            "segs_restantes": 0,
            "segs_total": 0,
        }
        self._window = window_ref
        self._window_manager = window_manager_ref # Para interactuar con el overlay
        self._main_queue = get_main_queue()

    def crono_iniciar(self, tareas_json, segs_total):
        tareas = json.loads(tareas_json) if isinstance(tareas_json, str) else list(tareas_json)

        self._crono.update(
            {
                "activo": True,
                "tareas": tareas,
                "segs_restantes": int(segs_total),
                "segs_total": int(segs_total),
            }
        )

        threading.Thread(target=self._loop_crono, daemon=True).start()
        return {"ok": True}

    def crono_toggle_tarea(self, idx, done):
        try:
            self._crono["tareas"][int(idx)]["done"] = bool(done)
            self._window_manager.update_overlay_state(self._crono)
            return {"ok": True}
        except Exception:
            return {"ok": False}

    def crono_agregar_tarea(self, texto):
        try:
            self._crono["tareas"].append({"texto": texto, "done": False})
            self._window_manager.update_overlay_state(self._crono)
            return {"ok": True, "total": len(self._crono["tareas"])}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def crono_finalizar(self):
        self._crono["activo"] = False
        self._main_queue.put(self._window_manager.destroy_overlay)
        return {"ok": True}

    def crono_cancelar(self):
        self._crono["activo"] = False
        self._main_queue.put(self._window_manager.destroy_overlay)
        return {"ok": True}

    def get_crono_state(self):
        return self._crono

    def _loop_crono(self):
        while self._crono["activo"] and self._crono["segs_restantes"] > 0:
            time.sleep(1)
            if not self._crono["activo"]: return
            self._crono["segs_restantes"] -= 1
            if self._window: self._window.evaluate_js(f"window._cronoPythonTick && window._cronoPythonTick({self._crono['segs_restantes']})")
            self._window_manager.update_overlay_state(self._crono)

        if self._crono["activo"] and self._crono["segs_restantes"] <= 0:
            self._crono["activo"] = False
            todas = all(t.get("done", False) for t in self._crono["tareas"])
            if not todas: show_toast("⏰ ¡Tiempo agotado!", "No completaste todas las tareas.", loop=False)
            if self._window: self._window.evaluate_js("window._cronoTiempoAgotado && window._cronoTiempoAgotado()")
            self._main_queue.put(self._window_manager.destroy_overlay)