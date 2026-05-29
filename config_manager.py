from datetime import datetime
from constants import DIAS, RUTA_CONFIG
from utils import cargar_json, guardar_json

class ConfigManager:
    def __init__(self):
        self.config = cargar_json(
            RUTA_CONFIG,
            {
                "tema": "dark",
                "ollama_url": "http://localhost:11434",
                "ollama_modelo": "llama3",
            },
        )

    def get_estado_inicial(self, running_flag_state):
        ahora = datetime.now()
        return {
            "dia_actual": DIAS[ahora.weekday()],
            "hora_actual": ahora.hour,
            "fecha_str": ahora.strftime("%A %d de %B").capitalize(),
            "tema": self.config.get("tema", "dark"),
            "asistente": running_flag_state,
            "ollama_url": self.config.get("ollama_url", "http://localhost:11434"),
            "ollama_modelo": self.config.get("ollama_modelo", "llama3"),
        }

    def guardar_tema(self, tema):
        self.config["tema"] = tema
        return guardar_json(RUTA_CONFIG, self.config)

    def guardar_config_ollama(self, url, modelo):
        self.config["ollama_url"] = url.strip()
        self.config["ollama_modelo"] = modelo.strip()
        return guardar_json(RUTA_CONFIG, self.config)

    def get_config(self):
        return self.config

    def get_ollama_config(self):
        return {
            "ollama_url": self.config.get("ollama_url", "http://localhost:11434"),
            "ollama_modelo": self.config.get("ollama_modelo", "llama3"),
        }

    def get_hora_actual(self):
        ahora = datetime.now()
        return {
            "dia": DIAS[ahora.weekday()],
            "hora": ahora.hour,
            "min": ahora.minute,
        }