import json
import threading
import requests
from datetime import datetime
from constants import DIAS
from utils import get_main_queue
from ollama_service import _ollama_chat, _construir_system_prompt

class AIChatService:
    def __init__(self, routine_manager, config_manager, window_ref):
        self.esperando_respuesta = False
        self.chat_historial = []
        self.routine_manager = routine_manager
        self.config_manager = config_manager
        self._window = window_ref
        self._main_queue = get_main_queue()

    def ia_enviar_mensaje(self, texto: str):
        texto = texto.strip()
        if not texto or self.esperando_respuesta:
            return {"ok": False, "error": "Mensaje vacío o esperando respuesta"}

        self.chat_historial.append({"role": "user", "content": texto})
        self.esperando_respuesta = True
        threading.Thread(target=self._ollama_worker, daemon=True).start()
        return {"ok": True}

    def ia_limpiar_historial(self):
        self.chat_historial = []
        return {"ok": True}

    def _ollama_worker(self):
        try:
            ahora = datetime.now()
            dia = DIAS[ahora.weekday()]
            hora = ahora.hour

            system_prompt = _construir_system_prompt(self.routine_manager.bd, dia, hora)
            historial_reciente = self.chat_historial[-10:]
            mensajes = [{"role": "system", "content": system_prompt}] + historial_reciente

            ollama_config = self.config_manager.get_ollama_config()
            respuesta = _ollama_chat(mensajes, ollama_config)
            self.chat_historial.append({"role": "assistant", "content": respuesta})

            if "---TAREAS---" in respuesta:
                partes = respuesta.split("---TAREAS---", 1)
                respuesta_limpia = partes[0].strip()
                tareas = [l.strip() for l in partes[1].splitlines() if l.strip()]
            else:
                respuesta_limpia = respuesta
                tareas = []

            resp_js = json.dumps(respuesta_limpia, ensure_ascii=False)
            tareas_js = json.dumps(tareas, ensure_ascii=False)

            if self._window:
                # Usamos la cola principal para actualizar la UI de forma segura
                self._main_queue.put(lambda: self._window.evaluate_js(f"window._iaRespuesta && window._iaRespuesta({resp_js}, {tareas_js})"))

        except requests.exceptions.Timeout:
            err = json.dumps("Ollama tardó demasiado en responder. Probá bajar num_predict, usar un modelo más liviano como llama3.2:1b, o revisar recursos del equipo.", ensure_ascii=False)
            if self.chat_historial and self.chat_historial[-1]["role"] == "user": self.chat_historial.pop()
            if self._window: self._window.evaluate_js(f"window._iaError && window._iaError({err})")

        except requests.exceptions.ConnectionError:
            url = self.config_manager.get_ollama_config().get("ollama_url", "http://localhost:11434")
            err = json.dumps(f"No pude conectarme a Ollama en {url}. ¿Está corriendo?", ensure_ascii=False)
            if self.chat_historial and self.chat_historial[-1]["role"] == "user": self.chat_historial.pop()
            if self._window: self._window.evaluate_js(f"window._iaError && window._iaError({err})")

        except Exception as e:
            err = json.dumps(f"Error inesperado: {str(e)}", ensure_ascii=False)
            if self.chat_historial and self.chat_historial[-1]["role"] == "user": self.chat_historial.pop()
            if self._window: self._window.evaluate_js(f"window._iaError && window._iaError({err})")
        finally:
            self.esperando_respuesta = False