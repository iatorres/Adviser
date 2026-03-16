# Adviser 📅

**Adviser** es un asistente de rutina personal automatizado desarrollado en Python. Su objetivo es mantenerte enfocado y productivo mediante notificaciones nativas de Windows en horarios específicos del día.

El proyecto nació de una necesidad personal: siendo estudiante con tendencia a la procrastinación, la idea fue crear un "compañero de responsabilidad" que guíe el día con una rutina predefinida y editable.

---

## 🚀 Características

- **Notificaciones nativas de Windows** — Integración con el Centro de Actividades de Windows 10/11 usando `winotify`.
- **Interfaz moderna** — Construida con HTML, CSS y JS embebidos en Python mediante `pywebview`.
- **Rutina semanal editable** — Modificá títulos y mensajes de cada hora directamente desde la app, sin tocar el código.
- **Cronómetro de tareas** — Sesiones temporizadas con lista de tareas para trabajo urgente fuera de la rutina.
- **Overlays flotantes** — Ventanas compactas que aparecen cuando la app está minimizada, mostrando la tarea actual o el estado del cronómetro.
- **Tema oscuro / claro** — Switcheable desde configuración, con preferencia persistente.
- **Persistencia automática** — La rutina se guarda en `rutina.json` y la configuración en `config.json`.

---

## 📋 Requisitos

- Python 3.x
- Windows 10 o superior

---

## 🔧 Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/iatorres/adviser.git
cd adviser

# 2. Crear y activar entorno virtual (recomendado)
python -m venv venv
.\venv\Scripts\activate

# 3. Instalar dependencias
pip install "pywebview[winforms]" winotify pywin32
```

Asegurate de que `icon.png` esté en el mismo directorio que `adviser_main.py`.

---

## ▶️ Uso

```bash
python adviser_main.py
```

La app tiene cuatro secciones principales:

| Sección | Descripción |
|---|---|
| 📋 **Ver Rutina** | Visualiza el cronograma semanal. La hora y día actual se resaltan automáticamente. |
| ✏️ **Editar** | Modificá los títulos y mensajes de cada franja horaria por día. |
| ⏱️ **Cronómetro** | Creá una sesión con tiempo límite y lista de tareas urgentes. |
| ⚙️ **Configuración** | Cambiá el tema visual entre oscuro y claro. |

---

## 📦 Compilar a ejecutable

```bash
pyinstaller adviser_main.spec
```

Genera un `.exe` standalone en `dist/Adviser/` sin necesidad de tener Python instalado.

---

## 🔨 Próximas mejoras
- Soporte para múltiples perfiles de rutina.
