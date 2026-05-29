import requests

def _ollama_chat(mensajes: list, ollama_config: dict) -> str:
    """
    Llama a /api/chat de Ollama con historial limitado.
    Usa stream=False para recibir un único JSON.
    Usa num_predict para evitar respuestas enormes.
    """
    url = ollama_config.get("ollama_url", "http://localhost:11434").strip().rstrip("/")
    modelo = ollama_config.get("ollama_modelo", "llama3").strip() or "llama3"

    payload = {
        "model": modelo,
        "messages": mensajes,
        "stream": False,
        "options": {
            "num_predict": 250,
            "temperature": 0.7,
        },
    }

    print("[OLLAMA] URL:", f"{url}/api/chat")
    print("[OLLAMA] Modelo:", modelo)
    print("[OLLAMA] Cantidad de mensajes:", len(mensajes))

    r = requests.post(
        f"{url}/api/chat",
        json=payload,
        timeout=300,
    )

    print("[OLLAMA] Status:", r.status_code)

    r.raise_for_status()
    data = r.json()

    if "message" not in data or "content" not in data["message"]:
        raise Exception(f"Respuesta inesperada de Ollama: {data}")

    return data["message"]["content"].strip()

def _construir_system_prompt(rutina: dict, dia_actual: str, hora_actual: int) -> str:
    lineas = []

    for h, entrada in enumerate(rutina.get(dia_actual, [])):
        titulo = entrada[0] if entrada else "(Vacío)"
        descripcion = entrada[1] if entrada and len(entrada) > 1 else "Sin actividad asignada"

        if titulo != "(Vacío)":
            lineas.append(f"  {h:02d}:00 — {titulo}: {descripcion}")

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