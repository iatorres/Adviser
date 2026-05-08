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

## ⚙️ ¿Cómo funciona? (Arquitectura)

La aplicación utiliza una arquitectura híbrida donde Python maneja la lógica de negocio y persistencia, mientras que HTML5/CSS3/JS se encargan de la interfaz de usuario.

### 🖼️ El Motor de Renderizado
A diferencia de una web tradicional que corre en un navegador (Chrome, Firefox), **Adviser** utiliza la librería `pywebview` para crear una ventana nativa del sistema operativo:

- **En Windows:** Utiliza el motor **Microsoft Edge WebView2** (basado en Chromium). 
- **Proceso:** Python inicializa una instancia del motor web, le asigna un archivo local (`ui.html`) y lo renderiza dentro de un "wrapper" de ventana de escritorio. Esto permite tener la flexibilidad de diseño de la web con el acceso a archivos y procesos del sistema que ofrece Python.

Al compilar con PyInstaller, todos los assets (.html, .js, .css, .png) se empaquetan y Python los localiza mediante rutas dinámicas (`sys._MEIPASS`).

### 🔌 El Puente (Bridge)
La comunicación se realiza mediante la librería `pywebview`:

1.  **Frontend a Backend (JS → Python):**  
    La clase `AdviserAPI` en `adviser_main.py` se expone al motor de renderizado. En JavaScript, se invocan funciones de Python de forma asíncrona mediante el objeto global:  
    `window.pywebview.api.nombre_de_funcion(parametros)`.

2.  **Backend a Frontend (Python → JS):**  
    Cuando ocurre un evento en Python (como el tick de un cronómetro o un cambio de hora), se utiliza el método `window.evaluate_js()` para ejecutar funciones específicas en el navegador, por ejemplo:  
    `self._window.evaluate_js("window._onAsistenteHora(14)")`.

### 🧵 Concurrencia y Hilos
- **Hilo Principal:** Reservado para la renderización de la interfaz y la creación/destrucción de ventanas (como el Overlay).
- **Hilos Secundarios (Daemon):** El asistente de notificaciones y el bucle del cronómetro corren en hilos separados para no bloquear la interfaz.
- **Sincronización:** Se implementó una **cola de mensajes (`queue.Queue`)**. Los hilos secundarios envían tareas de UI a esta cola, y el bucle principal las procesa cada 200ms, garantizando que `webview` no falle por llamadas desde hilos no autorizados.

---

## ��📦 Compilar a ejecutable

```bash
pyinstaller adviser_main.spec
```

Genera un `.exe` standalone en `dist/Adviser/` sin necesidad de tener Python instalado.

---

## 🔨 Próximas mejoras
- Soporte para múltiples perfiles de rutina.
