from constants import DIAS, HORAS, RUTA_JSON
from utils import cargar_json, guardar_json

class RoutineManager:
    def __init__(self):
        self.bd = cargar_json(RUTA_JSON, {})
        self._inicializar_rutina()

    def _inicializar_rutina(self):
        for dia in DIAS:
            self._inicializar_dia(dia)

    def _inicializar_dia(self, dia):
        vacio = ["(Vacío)", "Sin actividad asignada"]

        if dia not in self.bd:
            self.bd[dia] = [list(vacio) for _ in HORAS]
        elif len(self.bd[dia]) != len(HORAS):
            while len(self.bd[dia]) < len(HORAS):
                self.bd[dia].append(list(vacio))
            self.bd[dia] = self.bd[dia][:len(HORAS)]
        return self.bd[dia]

    def get_rutina(self):
        return self.bd

    def guardar_dia(self, dia, entradas):
        self.bd[dia] = [[e[0], e[1]] for e in entradas]
        return guardar_json(RUTA_JSON, self.bd)