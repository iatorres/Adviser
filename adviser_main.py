import time
import sys
import os
import json
import threading

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from winotify import Notification, audio
from datetime import datetime

# ─── Constantes ──────────────────────────────────────────────────────────────
DIAS  = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
HORAS = list(range(24))  # 00:00 a 23:00

if getattr(sys, 'frozen', False):
    _app_path = os.path.dirname(sys.executable)
else:
    _app_path = os.path.dirname(os.path.abspath(__file__))

RUTA_JSON   = os.path.join(_app_path, "rutina.json")
RUTA_ICON   = os.path.join(_app_path, "icon.png")
RUTA_CONFIG = os.path.join(_app_path, "config.json")

CARD_RADIUS = 12   # radio de esquinas en toda la app


# ─── Configuración persistente ───────────────────────────────────────────────
def cargar_config():
    try:
        with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"tema": "dark"}

def guardar_config(cfg):
    try:
        with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        pass


# ─── Paletas de colores ───────────────────────────────────────────────────────
PALETAS = {
    "dark": {
        "BG_BASE":        "#0D0F14",
        "BG_SURFACE":     "#13161D",
        "GLASS":          "#1A1E28",
        "GLASS_BORDER":   "#252A38",
        "GLASS_HOVER":    "#1F2436",
        "ACCENT":         "#6366F1",
        "ACCENT_SOFT":    "#4F52C4",
        "ACCENT_GLOW":    "#1E1F3A",
        "TEXT_PRIMARY":   "#F1F3FA",
        "TEXT_SECONDARY": "#8B92A8",
        "TEXT_MUTED":     "#4A5068",
        "SUCCESS":        "#10B981",
        "SUCCESS_BG":     "#0D2B22",
        "WARNING_TXT":    "#FBBF24",
        "WARNING_BG":     "#1C1A0E",
        "SEPARATOR":      "#1E2333",
    },
    "light": {
        "BG_BASE":        "#F0F2F8",
        "BG_SURFACE":     "#FFFFFF",
        "GLASS":          "#FFFFFF",
        "GLASS_BORDER":   "#D8DDED",
        "GLASS_HOVER":    "#EEF0FB",
        "ACCENT":         "#6366F1",
        "ACCENT_SOFT":    "#4F52C4",
        "ACCENT_GLOW":    "#E0E1FF",
        "TEXT_PRIMARY":   "#1E2033",
        "TEXT_SECONDARY": "#5A6280",
        "TEXT_MUTED":     "#9AA0BB",
        "SUCCESS":        "#059669",
        "SUCCESS_BG":     "#D1FAE5",
        "WARNING_TXT":    "#92400E",
        "WARNING_BG":     "#FEF3C7",
        "SEPARATOR":      "#E2E6F5",
    }
}

# Colores activos globales
C = {}

def aplicar_paleta(tema):
    global C
    C = PALETAS[tema].copy()
    ctk.set_appearance_mode(tema)


# ─── Lógica de datos ──────────────────────────────────────────────────────────
def cargar_rutina():
    try:
        with open(RUTA_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def guardar_rutina(datos):
    try:
        with open(RUTA_JSON, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar la rutina:\n{e}")

def inicializar_dia(bd, dia):
    """Garantiza que el día tenga exactamente 24 entradas (una por hora 0-23).
    Si el día ya existía con el formato viejo (lista de 11 entradas), lo migra."""
    vacio = ["(Vacío)", "Sin actividad asignada"]

    if dia not in bd:
        bd[dia] = [list(vacio) for _ in HORAS]
    elif len(bd[dia]) != len(HORAS):
        # Migrar formato viejo: extender o recortar a 24 entradas
        while len(bd[dia]) < len(HORAS):
            bd[dia].append(list(vacio))
        bd[dia] = bd[dia][:len(HORAS)]

    return bd[dia]


# ─── Scroll con Canvas nativo ─────────────────────────────────────────────────
class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self.canvas    = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner   = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self._window, width=e.width))
        self.bind("<Map>",   lambda e: self.canvas.bind_all("<MouseWheel>", self._scroll))
        self.bind("<Unmap>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _scroll(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()


# ─── Hilo de notificaciones ───────────────────────────────────────────────────
def loop_rutina(bd_ref, estado_label, running_flag):
    notificado_fuera = False
    while running_flag[0]:
        actual  = datetime.now()
        dia     = DIAS[actual.weekday()]
        hora    = actual.hour
        minuto  = actual.minute
        segundo = actual.second
        bd      = bd_ref[0]

        def update_label(text, text_color, fg_color):
            t, tc, fc = text, text_color, fg_color
            estado_label.after(0, lambda: estado_label.configure(
                text=t, text_color=tc, fg_color=fc))

        if dia in bd:
            if hora in HORAS:
                notificado_fuera = False
                _pop_out(bd[dia], hora)
                update_label(f"  ●  {hora:02d}:00 hs", C["SUCCESS"], C["SUCCESS_BG"])
            else:
                if not notificado_fuera:
                    _toast("FUERA DE HORARIO",
                           "No hay actividades ahora. El asistente esperará al siguiente horario.")
                    notificado_fuera = True
                update_label("  ◌  Fuera de horario", C["WARNING_TXT"], C["WARNING_BG"])
        else:
            if not notificado_fuera:
                _toast("FUERA DE SERVICIO", "No hay actividades para este día.")
                notificado_fuera = True
            update_label("  —  Sin rutina hoy", C["TEXT_MUTED"], C["GLASS"])

        tiempo_espera = 3600 - (minuto * 60 + segundo)
        for _ in range(tiempo_espera + 2):
            if not running_flag[0]:
                break
            time.sleep(1)

def _toast(titulo, mensaje):
    try:
        t = Notification(app_id="Adviser", title=titulo, msg=mensaje,
                         duration="long", icon=RUTA_ICON)
        t.set_audio(audio.LoopingCall, loop=True)
        t.show()
    except Exception:
        pass

def _pop_out(lista_dia, hora):
    try:
        pos = HORAS.index(hora)
        if pos < len(lista_dia):
            _toast(lista_dia[pos][0], lista_dia[pos][1])
    except ValueError:
        pass


# ─── Ventana principal ────────────────────────────────────────────────────────
class AdviserApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Adviser")
        self.geometry("920x660")
        self.minsize(820, 580)

        cfg = cargar_config()
        self.tema_actual = cfg.get("tema", "dark")
        aplicar_paleta(self.tema_actual)
        self.configure(fg_color=C["BG_BASE"])

        self.bd           = cargar_rutina()
        self.bd_ref       = [self.bd]
        self.running_flag = [False]
        self.hilo         = None

        self._build_ui()

    def _build_ui(self):
        # ── Sidebar ──
        self.sidebar = ctk.CTkFrame(self, width=220,
                                    fg_color=C["BG_SURFACE"], corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Franja de acento lateral
        tk.Frame(self.sidebar, width=3, bg=C["ACCENT"]).place(x=0, y=0, relheight=1)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(padx=24, pady=(32, 0), anchor="w")
        ctk.CTkLabel(logo_frame, text="◈", font=("Segoe UI", 28),
                     text_color=C["ACCENT"]).pack(side="left", padx=(0, 10))
        tf = ctk.CTkFrame(logo_frame, fg_color="transparent")
        tf.pack(side="left")
        ctk.CTkLabel(tf, text="Adviser", font=("Segoe UI", 18, "bold"),
                     text_color=C["TEXT_PRIMARY"]).pack(anchor="w")
        ctk.CTkLabel(tf, text="Asistente de rutina", font=("Segoe UI", 10),
                     text_color=C["TEXT_MUTED"]).pack(anchor="w")

        self._sep(self.sidebar, pady=(28, 20))

        ctk.CTkLabel(self.sidebar, text="NAVEGACIÓN", font=("Segoe UI", 9, "bold"),
                     text_color=C["TEXT_MUTED"]).pack(anchor="w", padx=24, pady=(0, 8))

        self.btn_rutina = self._nav_btn("  Ver Rutina",     "◫", lambda: self._mostrar_panel("rutina"))
        self.btn_editar = self._nav_btn("  Editar",         "✦", lambda: self._mostrar_panel("editar"))
        self.btn_config = self._nav_btn("  Configuración",  "⚙", lambda: self._mostrar_panel("config"))

        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)

        self._sep(self.sidebar, pady=(0, 16))

        ctk.CTkLabel(self.sidebar, text="ASISTENTE", font=("Segoe UI", 9, "bold"),
                     text_color=C["TEXT_MUTED"]).pack(anchor="w", padx=24, pady=(0, 8))

        self.estado_label = ctk.CTkLabel(
            self.sidebar, text="  ◻  Detenido",
            font=("Segoe UI", 11, "bold"),
            fg_color=C["GLASS"], text_color=C["TEXT_MUTED"],
            corner_radius=CARD_RADIUS, padx=12, pady=8
        )
        self.estado_label.pack(padx=16, fill="x")

        self.btn_toggle = ctk.CTkButton(
            self.sidebar, text="  Iniciar asistente",
            fg_color=C["ACCENT"], hover_color=C["ACCENT_SOFT"],
            font=("Segoe UI", 12, "bold"),
            corner_radius=CARD_RADIUS, height=40,
            command=self._toggle_asistente
        )
        self.btn_toggle.pack(padx=16, pady=(10, 28), fill="x")

        tk.Frame(self, width=1, bg=C["SEPARATOR"]).pack(side="left", fill="y")

        self.content = ctk.CTkFrame(self, fg_color=C["BG_BASE"], corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        self.panel_rutina = PanelRutina(self.content, self.bd, self._on_dia_select)
        self.panel_editar = PanelEditar(self.content, self.bd, self._on_guardado)
        self.panel_config = PanelConfig(self.content, self.tema_actual, self._on_tema_change)

        self._mostrar_panel("rutina")

    def _sep(self, parent, pady=(0, 0)):
        ctk.CTkFrame(parent, height=1, fg_color=C["GLASS_BORDER"]).pack(
            fill="x", padx=16, pady=pady)

    def _nav_btn(self, texto, icono, comando):
        btn = ctk.CTkButton(
            self.sidebar, text=f"{icono}{texto}", anchor="w",
            fg_color="transparent", hover_color=C["GLASS_HOVER"],
            text_color=C["TEXT_SECONDARY"], font=("Segoe UI", 13),
            corner_radius=CARD_RADIUS, height=40, command=comando
        )
        btn.pack(padx=10, pady=2, fill="x")
        return btn

    def _mostrar_panel(self, nombre):
        self.panel_rutina.pack_forget()
        self.panel_editar.pack_forget()
        self.panel_config.pack_forget()

        for btn in [self.btn_rutina, self.btn_editar, self.btn_config]:
            btn.configure(fg_color="transparent", text_color=C["TEXT_SECONDARY"])

        if nombre == "rutina":
            self.panel_rutina.pack(fill="both", expand=True)
            self.panel_rutina.refresh(self.bd)
            self.btn_rutina.configure(fg_color=C["ACCENT_GLOW"], text_color=C["ACCENT"])
        elif nombre == "editar":
            self.panel_editar.pack(fill="both", expand=True)
            self.panel_editar.refresh(self.bd)
            self.btn_editar.configure(fg_color=C["ACCENT_GLOW"], text_color=C["ACCENT"])
        elif nombre == "config":
            self.panel_config.pack(fill="both", expand=True)
            self.btn_config.configure(fg_color=C["ACCENT_GLOW"], text_color=C["ACCENT"])

    def _on_dia_select(self, dia):
        pass

    def _on_guardado(self, bd_actualizado):
        self.bd = bd_actualizado
        self.bd_ref[0] = bd_actualizado
        guardar_rutina(bd_actualizado)

    def _on_tema_change(self, nuevo_tema):
        # Detener hilo si estaba corriendo
        self.running_flag[0] = False
        self.tema_actual = nuevo_tema
        aplicar_paleta(nuevo_tema)
        guardar_config({"tema": nuevo_tema})
        self.configure(fg_color=C["BG_BASE"])
        # Destruir y reconstruir toda la UI con la nueva paleta al instante
        for widget in self.winfo_children():
            widget.destroy()
        self.running_flag = [False]
        self.hilo = None
        self._build_ui()

    def _toggle_asistente(self):
        if not self.running_flag[0]:
            self.running_flag[0] = True
            self.hilo = threading.Thread(
                target=loop_rutina,
                args=(self.bd_ref, self.estado_label, self.running_flag),
                daemon=True
            )
            self.hilo.start()
            self.btn_toggle.configure(text="  Detener asistente",
                                      fg_color="#7F1D1D", hover_color="#991B1B")
        else:
            self.running_flag[0] = False
            self.btn_toggle.configure(text="  Iniciar asistente",
                                      fg_color=C["ACCENT"], hover_color=C["ACCENT_SOFT"])
            self.estado_label.configure(text="  ◻  Detenido",
                                        text_color=C["TEXT_MUTED"], fg_color=C["GLASS"])


# ─── Panel: Ver rutina semanal ────────────────────────────────────────────────
class PanelRutina(ctk.CTkFrame):
    def __init__(self, parent, bd, on_dia_select):
        super().__init__(parent, fg_color=C["BG_BASE"], corner_radius=0)
        self.bd            = bd
        self.on_dia_select = on_dia_select
        self.dia_actual    = DIAS[0]
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(32, 0))
        ctk.CTkLabel(header, text="Rutina semanal",
                     font=("Segoe UI", 22, "bold"),
                     text_color=C["TEXT_PRIMARY"]).pack(side="left")
        hoy = datetime.now().strftime("%A, %d de %B").capitalize()
        ctk.CTkLabel(header, text=hoy, font=("Segoe UI", 11),
                     text_color=C["TEXT_MUTED"]).pack(side="right", pady=(8, 0))

        # Selector de días — card redondeada
        dias_card = ctk.CTkFrame(self, fg_color=C["GLASS"],
                                 corner_radius=CARD_RADIUS,
                                 border_width=1, border_color=C["GLASS_BORDER"])
        dias_card.pack(fill="x", padx=32, pady=(18, 0))

        self.dia_btns = {}
        for dia, label in zip(DIAS, ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]):
            btn = ctk.CTkButton(
                dias_card, text=label, width=74, height=36,
                fg_color="transparent", hover_color=C["GLASS_HOVER"],
                text_color=C["TEXT_SECONDARY"], font=("Segoe UI", 12),
                corner_radius=8,
                command=lambda d=dia: self._seleccionar_dia(d)
            )
            btn.pack(side="left", padx=4, pady=6)
            self.dia_btns[dia] = btn

        self.tabla_frame = ScrollFrame(self, bg=C["BG_BASE"])
        self.tabla_frame.pack(fill="both", expand=True, padx=32, pady=(16, 20))

        self._seleccionar_dia(DIAS[datetime.now().weekday()])

    def _seleccionar_dia(self, dia):
        self.dia_actual = dia
        for d, btn in self.dia_btns.items():
            btn.configure(
                fg_color=C["ACCENT"] if d == dia else "transparent",
                text_color=C["TEXT_PRIMARY"] if d == dia else C["TEXT_SECONDARY"]
            )
        self._renderizar_tabla(dia)
        self.on_dia_select(dia)

    def _renderizar_tabla(self, dia):
        self.tabla_frame.clear()
        parent = self.tabla_frame.inner

        lista          = inicializar_dia(self.bd, dia)
        hora_actual    = datetime.now().hour
        dia_actual_sys = DIAS[datetime.now().weekday()]

        for i, hora in enumerate(HORAS):
            titulo  = lista[i][0] if i < len(lista) else "(Vacío)"
            mensaje = lista[i][1] if i < len(lista) else "Sin actividad asignada"
            es_ahora = (dia == dia_actual_sys and hora == hora_actual)

            if es_ahora:
                bg_card    = C["SUCCESS_BG"]
                borde_col  = C["SUCCESS"]
                hora_color = C["SUCCESS"]
                tit_color  = C["SUCCESS"]
                msg_color  = C["TEXT_SECONDARY"]
            else:
                bg_card    = C["GLASS"]
                borde_col  = C["GLASS_BORDER"]
                hora_color = C["ACCENT"]
                tit_color  = C["TEXT_PRIMARY"]
                msg_color  = C["TEXT_SECONDARY"]

            # Una sola card con border nativo de CTk — sin frames anidados
            inner = ctk.CTkFrame(parent, fg_color=bg_card,
                                 corner_radius=CARD_RADIUS,
                                 border_width=1, border_color=borde_col)
            inner.pack(fill="x", pady=2, padx=2)

            # Layout en grid para control exacto de tamaño
            col = 0

            if es_ahora:
                ctk.CTkFrame(inner, width=4, fg_color=C["SUCCESS"],
                             corner_radius=2, height=40).grid(
                    row=0, column=col, rowspan=2, sticky="ns", padx=(4,0), pady=4)
                col += 1

            ctk.CTkLabel(inner, text=f"{hora:02d}:00",
                         font=("Segoe UI", 11, "bold"),
                         text_color=hora_color, width=52, height=16
                         ).grid(row=0, column=col, rowspan=2, padx=(10,0), pady=10, sticky="")
            col += 1

            ctk.CTkFrame(inner, width=1, fg_color=C["SEPARATOR"],
                         corner_radius=0, height=30).grid(
                row=0, column=col, rowspan=2, sticky="ns", padx=10, pady=8)
            col += 1

            ctk.CTkLabel(inner, text=titulo,
                         font=("Segoe UI", 11, "bold"),
                         text_color=tit_color, anchor="w", height=18
                         ).grid(row=0, column=col, sticky="sw", pady=(8, 0), padx=(0,8))
            ctk.CTkLabel(inner, text=mensaje,
                         font=("Segoe UI", 10),
                         text_color=msg_color, anchor="w",
                         wraplength=460, justify="left", height=16
                         ).grid(row=1, column=col, sticky="nw", pady=(0, 8), padx=(0,8))

            inner.columnconfigure(col, weight=1)

            if es_ahora:
                ctk.CTkLabel(inner, text="● AHORA",
                             font=("Segoe UI", 9, "bold"),
                             text_color=C["SUCCESS"],
                             fg_color="transparent", height=16
                             ).grid(row=0, column=col+1, rowspan=2, padx=14)

    def refresh(self, bd):
        self.bd = bd
        self._renderizar_tabla(self.dia_actual)


# ─── Panel: Editar rutina ─────────────────────────────────────────────────────
class PanelEditar(ctk.CTkFrame):
    def __init__(self, parent, bd, on_guardado):
        super().__init__(parent, fg_color=C["BG_BASE"], corner_radius=0)
        self.bd          = bd
        self.on_guardado = on_guardado
        self.dia_actual  = DIAS[0]
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(32, 0))
        ctk.CTkLabel(header, text="Editar rutina",
                     font=("Segoe UI", 22, "bold"),
                     text_color=C["TEXT_PRIMARY"]).pack(side="left")

        # Selector de día — card redondeada
        sel_card = ctk.CTkFrame(self, fg_color=C["GLASS"],
                                corner_radius=CARD_RADIUS,
                                border_width=1, border_color=C["GLASS_BORDER"])
        sel_card.pack(fill="x", padx=32, pady=(18, 0))

        ctk.CTkLabel(sel_card, text="Día  →", font=("Segoe UI", 12),
                     text_color=C["TEXT_MUTED"]).pack(side="left", padx=16, pady=12)

        self.combo_dia = ctk.CTkOptionMenu(
            sel_card,
            values=[d.capitalize() for d in DIAS],
            variable=ctk.StringVar(value=DIAS[0].capitalize()),
            fg_color=C["GLASS_HOVER"],
            button_color=C["ACCENT"], button_hover_color=C["ACCENT_SOFT"],
            dropdown_fg_color=C["GLASS"], dropdown_hover_color=C["GLASS_HOVER"],
            text_color=C["TEXT_PRIMARY"],
            font=("Segoe UI", 12), width=170,
            command=self._on_dia_change
        )
        self.combo_dia.pack(side="left", padx=(0, 16), pady=10)

        scroll_outer = ctk.CTkFrame(self, fg_color="transparent")
        scroll_outer.pack(fill="both", expand=True, padx=32, pady=(16, 0))

        self.slots_frame = ScrollFrame(scroll_outer, bg=C["BG_BASE"])
        self.slots_frame.pack(fill="both", expand=True)

        self._renderizar_slots(DIAS[0])

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=32, pady=(12, 24))
        ctk.CTkButton(
            btn_frame, text="  Guardar cambios",
            fg_color=C["ACCENT"], hover_color=C["ACCENT_SOFT"],
            font=("Segoe UI", 13, "bold"),
            corner_radius=CARD_RADIUS, height=44,
            command=self._guardar
        ).pack(fill="x")

    def _on_dia_change(self, valor):
        self.dia_actual = next((d for d in DIAS if d.capitalize() == valor), valor.lower())
        self._renderizar_slots(self.dia_actual)

    def _renderizar_slots(self, dia):
        self.slots_frame.clear()
        parent = self.slots_frame.inner
        self.entradas = []
        lista = inicializar_dia(self.bd, dia)

        for i, hora in enumerate(HORAS):
            titulo_val  = lista[i][0] if i < len(lista) else "(Vacío)"
            mensaje_val = lista[i][1] if i < len(lista) else "Sin actividad asignada"

            # Un solo CTkFrame con border nativo — sin frames anidados
            card = ctk.CTkFrame(parent, fg_color=C["GLASS"],
                                corner_radius=CARD_RADIUS,
                                border_width=1, border_color=C["GLASS_BORDER"])
            card.pack(fill="x", pady=2, padx=2)

            # Hora
            ctk.CTkLabel(card, text=f"{hora:02d}:00",
                         font=("Segoe UI", 11, "bold"),
                         text_color=C["ACCENT"], width=52, height=16
                         ).grid(row=0, column=0, rowspan=2, padx=(14, 0), pady=10)

            # Divisor
            ctk.CTkFrame(card, width=1, fg_color=C["SEPARATOR"],
                         corner_radius=0, height=34).grid(
                row=0, column=1, rowspan=2, sticky="ns", padx=12, pady=8)

            # Label TÍTULO
            ctk.CTkLabel(card, text="TÍTULO", font=("Segoe UI", 8, "bold"),
                         text_color=C["TEXT_MUTED"],
                         fg_color="transparent", height=14
                         ).grid(row=0, column=2, sticky="sw", pady=(8, 1))

            # Entry título
            titulo_entry = ctk.CTkEntry(
                card, placeholder_text="Ej: Reunión de equipo",
                font=("Segoe UI", 11),
                fg_color=C["BG_BASE"], border_color=C["GLASS_BORDER"],
                text_color=C["TEXT_PRIMARY"],
                placeholder_text_color=C["TEXT_MUTED"],
                corner_radius=6, height=28
            )
            titulo_entry.insert(0, titulo_val)
            titulo_entry.grid(row=0, column=3, padx=(0, 16), pady=(8, 2), sticky="ew")

            # Label MENSAJE
            ctk.CTkLabel(card, text="MENSAJE", font=("Segoe UI", 8, "bold"),
                         text_color=C["TEXT_MUTED"],
                         fg_color="transparent", height=14
                         ).grid(row=1, column=2, sticky="nw", pady=(1, 8))

            # Entry mensaje
            mensaje_entry = ctk.CTkEntry(
                card, placeholder_text="Descripción de la actividad...",
                font=("Segoe UI", 11),
                fg_color=C["BG_BASE"], border_color=C["GLASS_BORDER"],
                text_color=C["TEXT_PRIMARY"],
                placeholder_text_color=C["TEXT_MUTED"],
                corner_radius=6, height=28
            )
            mensaje_entry.insert(0, mensaje_val)
            mensaje_entry.grid(row=1, column=3, padx=(0, 16), pady=(2, 8), sticky="ew")

            card.columnconfigure(3, weight=1)
            self.entradas.append((titulo_entry, mensaje_entry))

    def _guardar(self):
        dia = self.dia_actual
        self.bd[dia] = [[t.get().strip(), m.get().strip()] for t, m in self.entradas]
        self.on_guardado(self.bd)
        messagebox.showinfo("Guardado", f"Rutina del {dia.capitalize()} guardada ✓")

    def refresh(self, bd):
        self.bd = bd
        self._renderizar_slots(self.dia_actual)


# ─── Panel: Configuración ─────────────────────────────────────────────────────
class PanelConfig(ctk.CTkFrame):
    def __init__(self, parent, tema_actual, on_tema_change):
        super().__init__(parent, fg_color=C["BG_BASE"], corner_radius=0)
        self.tema_actual    = tema_actual
        self.on_tema_change = on_tema_change
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(32, 0))
        ctk.CTkLabel(header, text="Configuración",
                     font=("Segoe UI", 22, "bold"),
                     text_color=C["TEXT_PRIMARY"]).pack(side="left")

        # ── Sección Apariencia ──
        ctk.CTkLabel(self, text="APARIENCIA", font=("Segoe UI", 9, "bold"),
                     text_color=C["TEXT_MUTED"]).pack(anchor="w", padx=32, pady=(28, 8))

        apariencia_card = ctk.CTkFrame(
            self, fg_color=C["GLASS"],
            corner_radius=CARD_RADIUS,
            border_width=1, border_color=C["GLASS_BORDER"]
        )
        apariencia_card.pack(fill="x", padx=32)

        # Fila toggle tema
        fila = ctk.CTkFrame(apariencia_card, fg_color="transparent")
        fila.pack(fill="x", padx=20, pady=18)

        left = ctk.CTkFrame(fila, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        icono = "🌙" if self.tema_actual == "dark" else "☀️"
        texto = "Modo oscuro" if self.tema_actual == "dark" else "Modo claro"
        self.lbl_titulo_tema = ctk.CTkLabel(
            left, text=f"{icono}  {texto}",
            font=("Segoe UI", 13, "bold"),
            text_color=C["TEXT_PRIMARY"]
        )
        self.lbl_titulo_tema.pack(anchor="w")
        ctk.CTkLabel(
            left, text="Cambia entre el tema oscuro y el tema claro.",
            font=("Segoe UI", 11), text_color=C["TEXT_MUTED"]
        ).pack(anchor="w", pady=(2, 0))

        self.switch_var = ctk.StringVar(value="on" if self.tema_actual == "dark" else "off")
        self.switch = ctk.CTkSwitch(
            fila, text="",
            variable=self.switch_var, onvalue="on", offvalue="off",
            progress_color=C["ACCENT"],
            button_color=C["TEXT_PRIMARY"],
            button_hover_color=C["TEXT_SECONDARY"],
            command=self._toggle_tema
        )
        self.switch.pack(side="right")

        # Divisor interno
        ctk.CTkFrame(apariencia_card, height=1,
                     fg_color=C["GLASS_BORDER"]).pack(fill="x", padx=16)

        # Fila info tema actual
        fila2 = ctk.CTkFrame(apariencia_card, fg_color="transparent")
        fila2.pack(fill="x", padx=20, pady=14)
        ctk.CTkLabel(fila2, text="🎨  Tema activo",
                     font=("Segoe UI", 12), text_color=C["TEXT_SECONDARY"]).pack(side="left")
        self.lbl_tema_badge = ctk.CTkLabel(
            fila2,
            text="Oscuro" if self.tema_actual == "dark" else "Claro",
            font=("Segoe UI", 12, "bold"),
            text_color=C["ACCENT"]
        )
        self.lbl_tema_badge.pack(side="right")

        # ── Sección Acerca de ──
        ctk.CTkLabel(self, text="ACERCA DE", font=("Segoe UI", 9, "bold"),
                     text_color=C["TEXT_MUTED"]).pack(anchor="w", padx=32, pady=(28, 8))

        about_card = ctk.CTkFrame(
            self, fg_color=C["GLASS"],
            corner_radius=CARD_RADIUS,
            border_width=1, border_color=C["GLASS_BORDER"]
        )
        about_card.pack(fill="x", padx=32)

        about_inner = ctk.CTkFrame(about_card, fg_color="transparent")
        about_inner.pack(fill="x", padx=20, pady=18)
        ctk.CTkLabel(about_inner, text="◈  Adviser",
                     font=("Segoe UI", 14, "bold"),
                     text_color=C["ACCENT"]).pack(anchor="w")
        ctk.CTkLabel(about_inner, text="Asistente de rutina personal  ·  v1.0",
                     font=("Segoe UI", 11),
                     text_color=C["TEXT_MUTED"]).pack(anchor="w", pady=(2, 0))

    def _toggle_tema(self):
        nuevo = "dark" if self.switch_var.get() == "on" else "light"
        self.tema_actual = nuevo
        self.lbl_tema_badge.configure(text="Oscuro" if nuevo == "dark" else "Claro")
        self.lbl_titulo_tema.configure(
            text=f"{'🌙' if nuevo == 'dark' else '☀️'}  {'Modo oscuro' if nuevo == 'dark' else 'Modo claro'}"
        )
        self.on_tema_change(nuevo)


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = AdviserApp()
    app.mainloop()
