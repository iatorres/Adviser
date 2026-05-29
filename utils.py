import json
import queue
from winotify import Notification, audio
from constants import RUTA_ICON

# ─── Cola para el hilo principal ──────────────────────────────────────────────
_main_queue = queue.Queue()

def get_main_queue():
    return _main_queue

def drain_queue():
    while True:
        try:
            fn = _main_queue.get_nowait()
            fn()
        except queue.Empty:
            break
        except Exception as e:
            print(f"[Adviser queue] Error: {e}")

# ─── Helpers de JSON ──────────────────────────────────────────────────────────
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

# ─── Notificaciones ───────────────────────────────────────────────────────────
def show_toast(titulo, mensaje, loop=True):
    try:
        t = Notification(app_id="Adviser", title=titulo, msg=mensaje, duration="long", icon=RUTA_ICON)
        t.set_audio(audio.LoopingCall if loop else audio.Reminder, loop=loop)
        t.show()
    except Exception:
        pass