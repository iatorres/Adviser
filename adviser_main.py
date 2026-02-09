
import time
import os
import json

from winotify import Notification,audio
from datetime import datetime

#Variables Globales

diasN=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]

horas_programa=[8,9,10,11,12,13,14,15,16,23,0,]

def cargar_rutina():
    """Carga la base de datos desde un archivo JSON."""
    ruta_json = os.path.join(os.path.dirname(__file__), "rutina.json")
    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("ADVERTENCIA: No se encontró 'rutina.json'. Asegúrate de que el archivo exista.")
        return {}
    except json.JSONDecodeError:
        print("ERROR: El archivo 'rutina.json' tiene un formato inválido.")
        return {}

def guardar_rutina(datos):
    """Guarda la base de datos en el archivo JSON."""
    ruta_json = os.path.join(os.path.dirname(__file__), "rutina.json")
    try:
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        print(">> Rutina guardada exitosamente.")
    except Exception as e:
        print(f"ERROR al guardar: {e}")

BD = cargar_rutina()

#Funciones


def arrancar_programa():
    # Ya no pasamos el día fijo, porque el día cambia si el programa corre 24/7
    runRutina()

def editar_rutina():
    """Permite al usuario editar la rutina desde la consola."""
    while True:
        print("\n--- EDITOR DE RUTINA ---")
        print("Días disponibles:", ", ".join(diasN))
        dia_input = input("Ingresa el día a editar (o 'volver' para ir al menú): ").lower().strip()

        if dia_input == "volver":
            break

        if dia_input not in diasN:
            print("Día no válido. Por favor ingresa un día de la semana (ej: lunes).")
            continue

        # Si el día no existe en la BD, inicializarlo
        if dia_input not in BD:
            BD[dia_input] = []

        lista_dia = BD[dia_input]

        # Asegurar que la lista tenga el tamaño correcto según horas_programa
        while len(lista_dia) < len(horas_programa):
            lista_dia.append(["(Vacío)", "Sin actividad asignada"])

        print(f"\nCronograma para {dia_input.capitalize()}:")
        for i, hora in enumerate(horas_programa):
            titulo = lista_dia[i][0]
            print(f"{i + 1}. [{hora}:00 hs] {titulo}")

        try:
            seleccion = int(input("\nElige el número de la actividad a modificar (0 para cancelar): "))
            if seleccion == 0:
                continue
            
            idx = seleccion - 1
            if 0 <= idx < len(horas_programa):
                print(f"Editando actividad de las {horas_programa[idx]}:00 hs...")
                nuevo_titulo = input("Nuevo Título: ")
                nuevo_mensaje = input("Nuevo Mensaje: ")
                lista_dia[idx] = [nuevo_titulo, nuevo_mensaje]
                BD[dia_input] = lista_dia
                guardar_rutina(BD)
            else:
                print("Número fuera de rango.")
        except ValueError:
            print("Entrada inválida. Ingresa un número.")

def runRutina():
    notificado_fuera = False # Evita spam de notificaciones "Fuera de horario"

    while True:
        print("3")
        actual = datetime.now()
        dia = diasN[actual.weekday()]
        hora = actual.hour
        minuto = actual.minute
        segundo = actual.second

        if dia in BD:
            diaLista = BD[dia]
            
            if hora in horas_programa:
                # Estamos en horario activo
                popOut(diaLista, hora)
                notificado_fuera = False # Reseteamos bandera al entrar en horario activo
            else:
                # Estamos fuera de horario (ej: 17:00 hs)
                if not notificado_fuera:
                    ruta_imagen = os.path.join(os.path.dirname(__file__), "icon.png")   
                    toast=Notification(
                        app_id="Admin de rutina",
                        title="FUERA DE HORARIO",
                        msg="No hay actividades ahora. El asistente esperará al siguiente horario.",
                        duration= 'long',
                        icon=ruta_imagen)
                    toast.add_actions(label="Click Me!",launch="https://github.com/iatorres")            
                    toast.set_audio(audio.LoopingCall, loop=True)
                    toast.show()
                    notificado_fuera = True
        else:
            # Día sin rutina (ej: fin de semana si no está en BD)
            if not notificado_fuera:
                ruta_imagen = os.path.join(os.path.dirname(__file__), "icon.png")   
                toast_fuera=Notification(
                    app_id="Admin de rutina",
                    title="FUERA DE SERVICIO",
                    msg="No hay actividades seleccionadas para este día",
                    duration= 'long',
                    icon=ruta_imagen)
                toast_fuera.set_audio(audio.LoopingCall, loop=True)
                toast_fuera.add_actions(label="Click Me!",launch="https://github.com/iatorres")
                toast_fuera.show()
                notificado_fuera = True

        # Dormir hasta la siguiente hora en punto
        # Calculamos segundos exactos para despertar cuando cambie la hora
        tiempo_espera = 3600 - (minuto * 60 + segundo)
        print("1")
        print(f"[{actual.strftime('%H:%M:%S')}] Durmiendo {tiempo_espera + 2} segundos.../ {(tiempo_espera + 2)/60} minutos.../")
        time.sleep(tiempo_espera + 2) # +2 segundos de margen para asegurar el cambio de hora
        
def popOut(lista,hora):

    try:
        pos = horas_programa.index(hora)
        # Verificamos que existan datos para esa posición en la lista del día
        if pos < len(lista):
            titulo = lista[pos][0]
            mensaje = lista[pos][1]

            toast = Notification(
                app_id="Admin de rutina",
                title=titulo,
                msg=mensaje,
                duration="long",
                icon=os.path.join(os.path.dirname(__file__), "icon.png")
            )

            toast.set_audio(audio.LoopingCall, loop=True)
            toast.add_actions(label="Click Me!", launch="https://github.com/iatorres")
            toast.show()
    except ValueError:
        pass


    


def main():
    print("Bienvenido a Adviser 📅")
    while True:
        print("\nMENÚ PRINCIPAL")
        print("1. Iniciar Asistente")
        print("2. Editar Rutina")
        print("3. Salir")
        
        opcion = input("Selecciona una opción: ")
        
        if opcion == "1":
            print("Iniciando servicio de notificaciones... (Cierra la ventana para detener)")
            arrancar_programa()
        elif opcion == "2":
            editar_rutina()
        elif opcion == "3":
            print("¡Hasta luego!")
            break
        else:
            print("Opción no válida.")


main()

#NOTIFIER
