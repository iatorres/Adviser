import time
import threading
from datetime import datetime
from constants import DIAS
from utils import show_toast

class AssistantService:
    def __init__(self, routine_manager, window_ref):
        self.running_flag = [False]  # Usamos una lista para que sea mutable entre hilos
        self.routine_manager = routine_manager
        self._window = window_ref

    def toggle_asistente(self):
        if self.running_flag[0]:
            self.running_flag[0] = False
            return {"ok": True, "estado": False}

        self.running_flag[0] = True
        threading.Thread(target=self._loop_asistente, daemon=True).start()
        return {"ok": True, "estado": True}

    def get_status(self):
        return self.running_flag[0]

    def _loop_asistente(self):
        while self.running_flag[0]:
            ahora = datetime.now()
            dia = DIAS[ahora.weekday()]
            hora = ahora.hour
            minuto = ahora.minute
            seg = ahora.second

            rutina_dia = self.routine_manager.bd.get(dia, [])
            titulo = rutina_dia[hora][0] if rutina_dia and hora < len(rutina_dia) else "(Vacío)"
            mensaje = rutina_dia[hora][1] if rutina_dia and hora < len(rutina_dia) and len(rutina_dia[hora]) > 1 else "Sin actividad asignada"

            show_toast(titulo, mensaje)

            if self._window:
                self._window.evaluate_js(f"window._onAsistenteHora && window._onAsistenteHora({hora})")

            espera = 3600 - (minuto * 60 + seg)
            for _ in range(espera + 2): # +2 para asegurar que el tick ocurra después del cambio de hora
                if not self.running_flag[0]:
                    break
                time.sleep(1)