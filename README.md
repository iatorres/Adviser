# Adviser 📅

**Adviser** es un asistente de rutina personal automatizado desarrollado en Python. Su objetivo principal es mantenerte enfocado, organizado y productivo mediante el envío de notificaciones nativas de Windows (Toast Notifications) en horarios específicos del día.

El sistema actúa como un "compañero de responsabilidad", recordándote tus actividades, descansos, tiempos de estudio y rutinas de gimnasio según un cronograma predefinido.

## 🚀 Características

- **Notificaciones Nativas:** Se integra perfectamente con el centro de actividades de Windows 10/11.
- **Cronograma Semanal:** Rutinas diferenciadas por día de la semana (Lunes a Viernes).
- **Alertas de Audio:** Las notificaciones incluyen sonido en bucle para asegurar que capten tu atención.
- **Interactividad:** Botones de acción integrados que pueden redirigir a enlaces útiles (por ejemplo, tu repositorio de GitHub).
- **Gestión de Estado:** Lógica inteligente para determinar si estás en horario productivo, tiempo libre o fuera de servicio.
- **Persistencia:** El script está diseñado para ejecutarse en segundo plano y "dormir" entre notificaciones para optimizar recursos.

## 📋 Requisitos Previos

Para ejecutar este proyecto, necesitas tener instalado:

- [Python 3.x](https://www.python.org/downloads/)
- Sistema Operativo Windows 10 o superior (requerido para las notificaciones `winotify`).

## 🔧 Instalación

1. **Clonar el repositorio** (o descargar los archivos en tu carpeta local):
   ```bash
   git clone https://github.com/iatorres/adviser.git
   cd adviser
   ```

2. **Instalar dependencias:**
   El proyecto utiliza la librería `winotify` para gestionar las alertas del sistema.
   ```bash
   pip install winotify
   ```

3. **Recursos:**
   Asegúrate de que el archivo `icon.png` se encuentre en el mismo directorio que `adviser_main.py`. Este icono se mostrará en todas las notificaciones.

## ⚙️ Configuración y Personalización

Toda la configuración de la rutina se encuentra dentro del archivo `adviser_main.py`. Puedes adaptar el asistente a tu vida diaria modificando las siguientes variables globales:

### 1. Horarios (`horas_programa`)
Esta lista define las horas exactas (formato 24h) en las que deseas recibir alertas.
```python
horas_programa = [8, 9, 10, 11, 12, 13, 14, 15, 22, 23, 0]
```

### 2. Base de Datos de Rutina (`BD`)
Es un diccionario donde las claves son los días de la semana (en minúsculas) y los valores son listas de tuplas. Cada tupla contiene:
1. **Título de la notificación.**
2. **Mensaje/Cuerpo de la notificación.**

El orden de las tuplas debe coincidir con el orden de `horas_programa`.

**Ejemplo:**
```python
BD = {
    "lunes": [
        ("Arrancamos el dia!!", "Tocan 2 de Gimnasio."), # Corresponde a las 8 AM
        ("Deberias estar entrenando", "Ponele ganas!!"), # Corresponde a las 9 AM
        # ... resto de actividades
    ],
    # ... otros días
}
```

## ▶️ Uso

Ejecuta el script principal desde tu terminal o configúralo para iniciarse con Windows.

```bash
python adviser_main.py
```

**Comportamiento:**
- El programa verificará el día y la hora actual.
- Si coincide con un horario programado, lanzará una notificación emergente.
- Si no hay actividades para la hora actual, el sistema esperará o te notificará que estás "Fuera de horario".

## 👤 Autor

**Ian Torres**
- GitHub: iatorres