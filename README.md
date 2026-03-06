# Adviser 📅

**Adviser** es un asistente de rutina personal automatizado desarrollado en Python. Su objetivo principal es mantenerte enfocado, organizado y productivo mediante el envío de notificaciones nativas de Windows (Toast Notifications) en horarios específicos del día.

El sistema actúa como un "compañero de responsabilidad", recordándote tus actividades, descansos, tiempos de estudio y rutinas de gimnasio según un cronograma predefinido.

El proyecto nacio, al yo ser un estudiante tendiente a la **procrastinación**, ante esta problematica se me ocurrio una solucion, crear un "asistente" el cual me este ayudando y guiando a resolver mis actividades, fue pensado en formato rutina.

## 🚀 Características

- **Interfaz Gráfica Moderna:** Construida con tecnologías web (HTML, CSS, JS) y `pywebview`, ofrece una experiencia de usuario limpia y fácil de usar.
- **Notificaciones Nativas:** Se integra con el centro de actividades de Windows 10/11 usando `winotify`.
- **Edición en Tiempo Real:** Puedes modificar las actividades de tu rutina directamente desde la aplicación.
- **Persistencia de Datos:** Tu rutina se guarda automáticamente en un archivo `rutina.json`.
- **Control Total:** Inicia o detén el asistente con un solo clic.
- **Estado Inteligente:** Visualiza si el asistente está activo, en espera o fuera de horario.

## 📋 Requisitos Previos

Para ejecutar este proyecto, necesitas tener instalado:

- [Python 3.x](https://www.python.org/downloads/)
- Sistema Operativo Windows 10 o superior.

## 🔧 Instalación

1.  **Clonar el repositorio** (o descargar los archivos en tu carpeta local):
   ```bash
   git clone https://github.com/iatorres/adviser.git
   cd adviser
   ```

2.  **Crear y activar un entorno virtual (Recomendado)**:
    Para mantener las dependencias del proyecto aisladas, es una buena práctica usar un entorno virtual.
    ```bash
    # Crear el entorno
    python -m venv venv

    # Activar en Windows
    .\venv\Scripts\activate
    ```

3.  **Instalar dependencias:**
    El proyecto necesita varias librerías para funcionar. Puedes instalarlas todas con el siguiente comando:
    ```bash
    pip install "pywebview[winforms]" winotify pywin32
    ```

4.  **Recursos:**
   Asegúrate de que el archivo `icon.png` se encuentre en el mismo directorio que `adviser_main.py`. Este icono se mostrará en todas las notificaciones.


## ▶️ Uso

Ejecuta el script principal desde tu terminal o configúralo para iniciarse con Windows.

```bash
python adviser_main.py
```

**Comportamiento:**
- El programa verificará el día y la hora actual.
- Si coincide con un horario programado, lanzará una notificación emergente.
- Si no hay actividades para la hora actual, el sistema esperará o te notificará que estás "Fuera de horario".

**Funcionalidades:** 
- 📋 Ver Rutina: Visualiza tu cronograma semanal. El día y hora actual se resaltarán automáticamente. 
- ✏️ Editar: Selecciona un día, modifica los títulos y mensajes de tus actividades y guarda los cambios. 
- ⏯️ Iniciar asistente: Activa el hilo en segundo plano que verificará la hora y te enviará notificaciones. 
- ⚙️ Personalización Ya no es necesario editar el código fuente para cambiar las actividades. Utiliza la pestaña Editar dentro de la aplicación. Los datos se guardan en rutina.json.
## 🔨Próximas actualizaciones
- Crear actividades temporales (actividad que ocurrira solo ese día y no modificará la rutina general).
- Mejorar el diseño de la interfaz.
