# Adviser 📅

**Adviser** es un asistente de rutina personal automatizado desarrollado en Python. Su objetivo es mantenerte enfocado y productivo mediante notificaciones nativas de Windows en horarios específicos del día.

La aplicación ha evolucionado de un script monolítico a una arquitectura robusta basada en servicios, integrando inteligencia artificial local para la gestión dinámica de tareas.

---

## 🚀 Características

- **Notificaciones nativas de Windows** — Integración con el Centro de Actividades de Windows 10/11 usando `winotify`.
- **Interfaz moderna y reactiva** — Construida con HTML5, CSS3 y Vanilla JS, comunicada bidireccionalmente con Python.
- **Rutina semanal editable** — Modificá títulos y mensajes de cada hora directamente desde la app, sin tocar el código.
- **Cronómetro de tareas** — Sesiones temporizadas con lista de tareas para trabajo urgente fuera de la rutina.
- **Asistente IA (Ollama)** — Chat integrado que entiende tu rutina y puede generar listas de tareas para el cronómetro automáticamente.
- **Overlays flotantes** — Ventanas compactas que aparecen cuando la app está minimizada, mostrando la tarea actual o el estado del cronómetro.
- **Tema oscuro / claro** — Switcheable desde configuración, con preferencia persistente.
- **Persistencia automática** — La rutina se guarda en `rutina.json` y la configuración en `config.json`.
- **Entorno de Desarrollo** — Incluye un script de *hot-reload* para agilizar cambios en el código.

---

## 📋 Requisitos

- Python 3.x
- Windows 10 o superior
- Ollama (opcional, para funciones de IA)

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

## 🛠️ Desarrollo

Para trabajar en el código y ver los cambios en tiempo real (tanto en Python como en el Frontend), utilizá:

```bash
python dev_runner.py
```
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
| ⏱️ **Cronómetro** | Sesiones de enfoque con lista de tareas y **Overlay flotante** automático al minimizar. |
| 🤖 **Asistente IA** | Chat interactivo para consultar tu rutina o generar tareas basadas en el contexto. |
| ⚙️ **Configuración** | Ajustes de tema visual y parámetros de conexión (URL/Modelo) para Ollama. |

---

## ⚙️ ¿Cómo funciona? (Arquitectura)

La aplicación utiliza una arquitectura híbrida donde Python maneja la lógica de negocio y persistencia, mientras que HTML5/CSS3/JS se encargan de la interfaz de usuario.

### 📂 Estructura de Módulos
- **`adviser_main.py`**: Punto de entrada y orquestador. Define la `AdviserAPI` que sirve de puente con el frontend.
- **`assistant_service.py`**: Gestiona el ciclo de vida de las notificaciones horarias en segundo plano.
- **`chronometer_service.py`**: Controla la lógica del temporizador y el estado de las tareas activas.
- **`ai_chat_service.py`**: Maneja la comunicación con la IA (Ollama), el historial de chat y el procesamiento de tareas sugeridas.
- **`window_manager.py`**: Responsable de la gestión de ventanas, incluyendo la detección de estado (minimización) y la creación del overlay flotante.
- **`config_manager.py` & `routine_manager.py`**: Encargados de la persistencia, validación e inicialización de datos en formato JSON.
- **`utils.py`**: Provee utilidades transversales como el sistema de notificaciones (`winotify`) y la cola de ejecución sincronizada.

### 🖼️ El Motor de Renderizado
Adviser utiliza `pywebview` para renderizar la interfaz usando el motor **Microsoft Edge WebView2**. Esto permite:

- **En Windows:** Utiliza el motor **Microsoft Edge WebView2** (basado en Chromium). 
- **Proceso:** Python inicializa una instancia del motor web, le asigna un archivo local (`ui.html`) y lo renderiza dentro de un "wrapper" de ventana de escritorio. Esto permite tener la flexibilidad de diseño de la web con el acceso a archivos y procesos del sistema que ofrece Python.

Al compilar con PyInstaller, todos los assets (.html, .js, .css, .png) se empaquetan y Python los localiza mediante rutas dinámicas (`sys._MEIPASS`).

### 🔌 El Puente (Bridge)
La comunicación bidireccional se realiza de la siguiente manera:


1.  **Frontend a Backend (JS → Python):**  
    La clase `AdviserAPI` en `adviser_main.py` se expone al motor de renderizado. En JavaScript, se invocan funciones de Python de forma asíncrona mediante el objeto global:  
    `window.pywebview.api.nombre_de_funcion(parametros)`.

2.  **Backend a Frontend (Python → JS):**  
    Cuando ocurre un evento en Python (como el tick de un cronómetro o un cambio de hora), se utiliza el método `window.evaluate_js()` para ejecutar funciones específicas en el navegador, por ejemplo:  
    `self._window.evaluate_js("window._iaRespuesta(texto, tareas)")`.

### 🧵 Concurrencia y Hilos
- **Hilo Principal:** Reservado para la renderización de la interfaz y la creación/destrucción de ventanas (como el Overlay).
- **Hilos Secundarios (Daemon):** Los servicios de asistente, cronómetro e IA operan en hilos independientes para garantizar que la aplicación nunca se congele durante procesos pesados o esperas de red.
- **Sincronización (Main Queue):** Se utiliza una **cola de mensajes (`queue.Queue`)** en `utils.py`. El `_main_loop` en Python procesa esta cola constantemente. Esto permite que los hilos de fondo soliciten cambios en la UI (como abrir el Overlay o mostrar notificaciones) de forma ordenada y segura, evitando colisiones entre los hilos de los servicios y el motor web.
  
### 🤖 Inteligencia Artificial
Adviser se integra con **Ollama** para ofrecer un asistente de productividad local. El sistema construye dinámicamente un *System Prompt* que incluye el contexto de tu rutina diaria, permitiendo que la IA sugiera tareas específicas que pueden enviarse directamente al cronómetro con un solo click desde el chat.

---

## ��📦 Compilar a ejecutable

```bash
pyinstaller adviser_main.spec
```

Genera un `.exe` standalone en `dist/Adviser/` sin necesidad de tener Python instalado.

---

## 🔨 Próximas mejoras
- Soporte para múltiples perfiles de rutina.
- Historial de sesiones de cronómetro completadas.
- Estadísticas de productividad semanal basadas en tareas hechas.
