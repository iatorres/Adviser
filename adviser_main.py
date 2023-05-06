
import time
import os

from winotify import Notification,audio
from datetime import datetime

#Variables Globales

diasN=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]

horas_programa=[8,9,10,11,12,13,14,15,22,23,0,]


BD={  #Titulo y mensaje de cada horario

    "lunes":
    [
        ("Arrancamos el dia!!","Tocan 2 de Gimnasio."), #08AM
        ("Deberias estar entrenando","Ponele ganas!!"), #09AM
        ("Hora de OCIO","Distraete un rato."), #10AM
        ("TOCA ESTUDIAR","Activa con la facultad!!"), #11AM
        ("A seguir estudiando 1horita","CON GANAS!!"), #12AM
        ("Hora de un buen almuerzo","A recuperar el gimnasio"), #13PM
        ("Dos hora de trabajo personal","Hay que enfocarse en los proyectos"), #14 PM
        ("Una horita más y a ir a la universidad!","Focus!!"), #15PM
        ("Momento de emprender viaje!","Exitos!"), #16PM
        ("Solo una hora","Recien llegas de la facultad, distraete y a dormir"), #23 PM
        ("TOCA IR A DORMIR!!","Hay que descansar campeon excelente dia!"), #00AM
        ],
    "martes":
    [
        ("Arrancamos el dia!!","Tocan 2 de Gimnasio."), #08AM
        ("Deberias estar entrenando","Ponele ganas!!"), #09AM
        ("Hora de OCIO","Distraete un rato."), #10AM
        ("TOCA ESTUDIAR","Activa con la facultad!!"), #11AM
        ("A seguir estudiando 1horita","CON GANAS!!"), #12AM
        ("Hora de un buen almuerzo","A recuperar el gimnasio"), #13AM
        ("Dos hora de trabajo personal","Hay que enfocarse en los proyectos"), #14 PM
        ("Una horita más y a ir a la universidad!","Focus!!"), #15PM
        ("Momento de emprender viaje!","Exitos!"), #16PM
        ("Solo una hora","Recien llegas de la facultad, distraete y a dormir"), #23PM
        ("TOCA IR A DORMIR!!","Hay que descansar campeon excelente dia!"), #01AM
        ],
    "miercoles":
    [
        ("Arrancamos el dia!!","Tocan 2 de Gimnasio."), #08AM
        ("Deberias estar entrenando","Ponele ganas!!"), #09AM
        ("Hora de OCIO","Distraete un rato."), #10AM
        ("TOCA ESTUDIAR","Activa con la facultad!!"), #11AM
        ("A seguir estudiando 1horita","CON GANAS!!"), #12AM
        ("Hora de un buen almuerzo","A recuperar el gimnasio"), #13PM
        ("Dos hora de trabajo personal","Hay que enfocarse en los proyectos"), #14 PM
        ("Una horita más y a ir a la universidad!","Focus!!"), #15PM
        ("Momento de emprender viaje!","Exitos!"), #16PM
        ("Solo una hora","Recien llegas de la facultad, distraete y a dormir"), #23 pM
        ("TOCA IR A DORMIR!!","Hay que descansar campeon excelente dia!"), #00AM
        ],
    "jueves":
    [
        ("Arrancamos el dia!!","Tocan 2 de Gimnasio."), #08AM
        ("Deberias estar entrenando","Ponele ganas!!"), #09AM
        ("Hora de OCIO","Distraete un rato."), #10AM
        ("TOCA ESTUDIAR","Activa con la facultad!!"), #11AM
        ("A seguir estudiando 1horita","CON GANAS!!"), #12AM
        ("Hora de un buen almuerzo","A recuperar el gimnasio"), #13PM
        ("Dos hora de trabajo personal","Hay que enfocarse en los proyectos"), #14 PM
        ("Una horita más y a ir a la universidad!","Focus!!"), #15PM
        ("Momento de emprender viaje!","Exitos!"), #16PM
        ("Solo una hora","Recien llegas de la facultad, distraete y a dormir"), #23 AM
        ("TOCA IR A DORMIR!!","Hay que descansar campeon excelente dia!"), #00AM
        ], #jueves no curso
    "viernes":
    [
        ("Arrancamos el dia!!","Tocan 2 de Gimnasio."), #08AM
        ("Deberias estar entrenando","Ponele ganas!!"), #09AM
        ("Hora de OCIO","Distraete un rato."), #10AM
        ("TOCA ESTUDIAR","Activa con la facultad!!"), #11AM
        ("A seguir estudiando 1horita","CON GANAS!!"), #12AM
        ("Hora de un buen almuerzo","A recuperar el gimnasio"), #13PM
        ("Dos hora de trabajo personal","Hay que enfocarse en los proyectos"), #14PM
        ("Una horita más y a ir a la universidad!","Focus!!"), #15PM
        ("Momento de emprender viaje!","Exitos!"), #16PM
        ("Solo una hora","Recien llegas de la facultad, distraete y a dormir"), #23AM
        ("TOCA IR A DORMIR!!","Hay que descansar campeon excelente dia!"), #00AM
        ],
    }
#Funciones


def arrancar_programa():

    dia=datetime.today().weekday()
    diaF=diasN[dia]
    runRutina(diaF)


def runRutina(dia):

    actual=datetime.now()
    hora=actual.hour


    if dia in BD:
        diaLista=BD[dia]
    


        if (hora>=8 and hora<15) or (hora>=22) or (hora == 0):
            popOut(diaLista,hora)
                

        while (hora>=8 and hora<16) or (hora>=22):

            time.sleep( (3600 - (minuto*60) ))  #el programa descansa hasta la siguiente hora
            
            horaN=actual.hour
                                            
            if (horaN != hora):
                hora=horaN
                minuto=actual.minute
                popOut(diaLista,hora)

        if hora > 8 or hora < 23:
            ruta_imagen = os.path.join(os.path.dirname(__file__), "icon.png")   
            toast=Notification(
                    
                app_id="Admin de rutina",
                title="FUERA DE HORARIO",
                msg="No hay actividades seleccionadas para este horario",
                duration= 'long',
                icon=ruta_imagen)
            
            toast.add_actions(label="Click Me!",launch="https://github.com/iatorres")            
            toast.set_audio(audio.LoopingCall, loop=True)
            toast.show()
    else:
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
        
def popOut(lista,hora):

    pos=horas_programa.index(hora) 
    titulo=lista[pos][0]
    mensaje=lista[pos][1]

    toast=Notification(
        

            app_id="Admin de rutina",
            title=titulo,
            msg=mensaje,
            duration="long",
            icon=r"icon.png")
            

    toast.set_audio(audio.LoopingCall, loop=True)
    toast.add_actions(label="Click Me!",launch="https://github.com/iatorres")

    toast.show()


    


def main():

    now=datetime.now()
    dia=datetime.today().weekday()
    hora=now.hour
    minuto=now.minute
    
    arrancar_programa()
    


main()













#NOTIFIER




     



'''
Programa corriendo aprox desde 8 am hasta 15 pm y reanuda 23 pm hasta 3am.

1) primero necesito obtener las variablles de Hora,Minuto y Dia. --
2) bucle que vaya viendo las horas, en el momento que lo haga arrancar deberia ser mayor a las 8.
3) ¿Como romper el bucle, como inicializarlo?

4)Una vez en el bucle, ¿Como hago q mi pc no se rompa?
    Hago funcion que reconozco dia hora minuto

    17:20

    while se pause unas 35 

    18:00


    now=datetime.now()
        dia=datetime.today().weekday()
        hora=now.hour
        minuto=now.minute




'''
        
'''
if hora >= 22:
    
    title="Nery se la come"

    message="A ver como anda esta mierda"

    notification.notify(title=title,
                    message=message,
                    timeout=10,
                    toast=False
                    )'''     





'''
tengo que llenar la base de datos, tengo que empezar a ver cuando falta 1 o 2 horas y tambien podriap ner como un modo pilotoi

'''
