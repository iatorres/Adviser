import time
import webview
from constants import RUTA_HTML
from utils import drain_queue, show_toast
from config_manager import ConfigManager
from routine_manager import RoutineManager
from assistant_service import AssistantService
from chronometer_service import ChronometerService
from ai_chat_service import AIChatService
from window_manager import WindowManager


# ─── API ──────────────────────────────────────────────────────────────────────
class AdviserAPI:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.routine_manager = RoutineManager()
        self._window = None
        self.chronometer_service = ChronometerService(None, None)
        self.window_manager = WindowManager(None, self.chronometer_service, self.config_manager)
        self.chronometer_service._window_manager = self.window_manager
        self.assistant_service = AssistantService(self.routine_manager, None)
        self.ai_chat_service = AIChatService(self.routine_manager, self.config_manager, None)

    # ═══════════════════════════════ RUTINA ══════════════════════════════════
    def get_rutina(self):
        return self.routine_manager.get_rutina()

    def get_dia(self, dia):
        return self.routine_manager.bd.get(dia, [])

    def guardar_dia(self, dia, entradas):
        return self.routine_manager.guardar_dia(dia, entradas)

    # ════════════════════════════ ESTADO / CONFIG ═════════════════════════════
    def get_estado_inicial(self):
        return self.config_manager.get_estado_inicial(self.assistant_service.get_status())

    def get_hora_actual(self):
        return self.config_manager.get_hora_actual()

    def guardar_tema(self, tema):
        return self.config_manager.guardar_tema(tema)

    def guardar_config_ollama(self, url, modelo):
        return self.config_manager.guardar_config_ollama(url, modelo)

    # ══════════════════════════════ ASISTENTE ═════════════════════════════════
    def toggle_asistente(self):
        return self.assistant_service.toggle_asistente()

    # ══════════════════════════════ CRONÓMETRO ════════════════════════════════
    def crono_iniciar(self, tareas_json, segs_total):
        return self.chronometer_service.crono_iniciar(tareas_json, segs_total)

    def crono_toggle_tarea(self, idx, done):
        return self.chronometer_service.crono_toggle_tarea(idx, done)

    def crono_agregar_tarea(self, texto):
        return self.chronometer_service.crono_agregar_tarea(texto)

    def crono_finalizar(self):
        return self.chronometer_service.crono_finalizar()

    def crono_cancelar(self):
        return self.chronometer_service.crono_cancelar()

    def notificar_alarma_crono(self, titulo, mensaje):
        show_toast(titulo, mensaje, loop=False)
        return {"ok": True}

    # ══════════════════════════════ IA — CHAT ═════════════════════════════════
    def ia_enviar_mensaje(self, texto: str):
        return self.ai_chat_service.ia_enviar_mensaje(texto)

    def ia_limpiar_historial(self):
        return self.ai_chat_service.ia_limpiar_historial()

    # ═══════════════════════════════ OVERLAY ═════════════════════════════════
    def overlay_get_estado(self):
        return self.window_manager.overlay_get_estado()

    def overlay_restaurar_app(self):
        return self.window_manager.overlay_restaurar_app()

    def overlay_cerrar(self):
        return self.window_manager.overlay_cerrar()

    def overlay_set_height(self, height):
        return self.window_manager.overlay_set_height(height)

    def overlay_resize(self, width, height):
        return self.window_manager.overlay_resize(width, height)

    # ════════════════════════ DETECCIÓN VENTANA ═══════════════════════════════
    def iniciar_monitor_ventana(self):
        self.window_manager.iniciar_monitor_ventana()

    def on_main_minimized(self):
        pass

    def on_main_closed(self):
        self.window_manager.on_main_closed()

    def on_main_restored(self):
        pass

# ─── Loop principal ───────────────────────────────────────────────────────────
def _main_loop(api):
    while True:
        time.sleep(0.2)
        drain_queue()


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    api = AdviserAPI()

    window = webview.create_window(
        title="Adviser",
        url=RUTA_HTML,
        js_api=api,
        width=960,
        height=680,
        min_size=(820, 560),
        frameless=False,
        resizable=True,
        background_color="#080A0F",
    )

    # Set the main window reference in the API and its managers
    api._window = window
    api.assistant_service._window = window
    api.chronometer_service._window = window
    api.ai_chat_service._window = window
    api.window_manager._main_window = window

    # Attach event handlers
    window.events.minimized += api.on_main_minimized
    window.events.restored += api.on_main_restored
    window.events.closed += api.on_main_closed
    window.events.loaded += lambda: api.iniciar_monitor_ventana()

    webview.start(_main_loop, api, debug=False)
