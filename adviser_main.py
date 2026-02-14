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

# ─── Configuración visual ────────────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ─── Constantes ──────────────────────────────────────────────────────────────
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
HORAS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 23, 0]
# Detectar si corre como ejecutable o script
if getattr(sys, 'frozen', False):
    _app_path = os.path.dirname(sys.executable)
else:
    _app_path = os.path.dirname(os.path.abspath(__file__))

RUTA_JSON = os.path.join(_app_path, "rutina.json")
RUTA_ICON = os.path.join(_app_path, "icon.png")

COLOR_FONDO      = "#F7F7F8"
COLOR_CARD       = "#FFFFFF"
COLOR_PRIMARIO   = "#2563EB"
COLOR_TEXTO      = "#1E293B"
COLOR_SUBTEXTO   = "#64748B"
COLOR_BORDE      = "#E2E8F0"
COLOR_ACTIVO     = "#DCFCE7"
COLOR_ACTIVO_TXT = "#166534"
COLOR_INACTIVO   = "#FEF9C3"
COLOR_INACT_TXT  = "#713F12"

# ─── Scroll estable con Canvas nativo ───────────────────────────────────────
class ScrollFrame(tk.Frame):
    """Frame scrollable sin bugs visuales, usando Canvas nativo de tkinter."""
    def __init__(self, parent, bg=COLOR_FONDO, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind("<Map>", self._bind_mouse)
        self.bind("<Unmap>", self._unbind_mouse)

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._window, width=event.width)

    def _bind_mouse(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mouse(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()

# ─── Lógica de datos ─────────────────────────────────────────────────────────
def cargar_rutina():
    try:
        with open(RUTA_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def guardar_rutina(datos):
    try:
        with open(RUTA_JSON, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar la rutina:\n{e}")

def inicializar_dia(bd, dia):
    """Asegura que el día tenga exactamente len(HORAS) entradas."""
    if dia not in bd:
        bd[dia] = []
    while len(bd[dia]) < len(HORAS):
        bd[dia].append(["(Vacío)", "Sin actividad asignada"])
    return bd[dia]

# ─── Hilo de notificaciones ──────────────────────────────────────────────────
def loop_rutina(bd_ref, estado_label, running_flag):
    """Corre en un hilo separado. bd_ref es una lista de un elemento [dict] para mutabilidad."""
    notificado_fuera = False

    while running_flag[0]:
        actual   = datetime.now()
        dia      = DIAS[actual.weekday()]
        hora     = actual.hour
        minuto   = actual.minute
        segundo  = actual.second

        bd = bd_ref[0]

        if dia in bd:
            if hora in HORAS:
                notificado_fuera = False
                _pop_out(bd[dia], hora)
                estado_label.configure(
                    text=f"▶  Activo — {hora:02d}:00 hs",
                    text_color=COLOR_ACTIVO_TXT,
                    fg_color=COLOR_ACTIVO
                )
            else:
                if not notificado_fuera:
                    _toast("FUERA DE HORARIO",
                           "No hay actividades ahora. El asistente esperará al siguiente horario.")
                    notificado_fuera = True
                estado_label.configure(
                    text="⏸  Fuera de horario",
                    text_color=COLOR_INACT_TXT,
                    fg_color=COLOR_INACTIVO
                )
        else:
            if not notificado_fuera:
                _toast("FUERA DE SERVICIO",
                       "No hay actividades seleccionadas para este día.")
                notificado_fuera = True
            estado_label.configure(
                text="—  Sin rutina hoy",
                text_color=COLOR_INACT_TXT,
                fg_color=COLOR_INACTIVO
            )

        tiempo_espera = 3600 - (minuto * 60 + segundo)
        # Dormimos en pequeños intervalos para poder detener el hilo
        for _ in range(tiempo_espera + 2):
            if not running_flag[0]:
                break
            time.sleep(1)

def _toast(titulo, mensaje):
    try:
        t = Notification(
            app_id="Adviser",
            title=titulo,
            msg=mensaje,
            duration="long",
            icon=RUTA_ICON
        )
        t.set_audio(audio.LoopingCall, loop=True)
        t.show()
    except Exception:
        pass

def _pop_out(lista_dia, hora):
    try:
        pos = HORAS.index(hora)
        if pos < len(lista_dia):
            titulo  = lista_dia[pos][0]
            mensaje = lista_dia[pos][1]
            _toast(titulo, mensaje)
    except ValueError:
        pass

# ─── Ventana principal ───────────────────────────────────────────────────────
class AdviserApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Adviser")
        self.geometry("860x620")
        self.minsize(780, 560)
        self.configure(fg_color=COLOR_FONDO)

        self.bd = cargar_rutina()
        self.bd_ref = [self.bd]          # lista de un elemento para pasar por referencia al hilo
        self.running_flag = [False]
        self.hilo = None

        self._build_ui()

    # ── Construcción de la UI ─────────────────────────────────────────────
    def _build_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color=COLOR_CARD,
                                    corner_radius=0, border_width=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo / título
        ctk.CTkLabel(self.sidebar, text="📅", font=("Segoe UI", 36),
                     text_color=COLOR_PRIMARIO).pack(pady=(32, 4))
        ctk.CTkLabel(self.sidebar, text="Adviser",
                     font=("Segoe UI", 20, "bold"), text_color=COLOR_TEXTO).pack()
        ctk.CTkLabel(self.sidebar, text="Asistente de rutina",
                     font=("Segoe UI", 11), text_color=COLOR_SUBTEXTO).pack(pady=(0, 28))

        separator = ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDE)
        separator.pack(fill="x", padx=16, pady=(0, 20))

        # Botones de navegación
        self.btn_rutina = self._nav_btn("📋  Ver Rutina",   lambda: self._mostrar_panel("rutina"))
        self.btn_editar = self._nav_btn("✏️  Editar",       lambda: self._mostrar_panel("editar"))

        # Espaciador
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)

        # Estado del asistente
        separator2 = ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDE)
        separator2.pack(fill="x", padx=16, pady=(0, 12))

        self.estado_label = ctk.CTkLabel(
            self.sidebar, text="⏹  Detenido",
            font=("Segoe UI", 11, "bold"),
            fg_color="#F1F5F9", text_color=COLOR_SUBTEXTO,
            corner_radius=8, padx=10, pady=6
        )
        self.estado_label.pack(padx=16, fill="x")

        self.btn_toggle = ctk.CTkButton(
            self.sidebar, text="▶  Iniciar asistente",
            fg_color=COLOR_PRIMARIO, hover_color="#1D4ED8",
            font=("Segoe UI", 12, "bold"), corner_radius=8,
            command=self._toggle_asistente
        )
        self.btn_toggle.pack(padx=16, pady=(10, 24), fill="x")

        # Área de contenido principal
        self.content = ctk.CTkFrame(self, fg_color=COLOR_FONDO, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        # Paneles
        self.panel_rutina = PanelRutina(self.content, self.bd, self._on_dia_select)
        self.panel_editar = PanelEditar(self.content, self.bd, self._on_guardado)

        self._mostrar_panel("rutina")

    def _nav_btn(self, texto, comando):
        btn = ctk.CTkButton(
            self.sidebar, text=texto, anchor="w",
            fg_color="transparent", hover_color="#EFF6FF",
            text_color=COLOR_TEXTO, font=("Segoe UI", 13),
            corner_radius=8, height=38, command=comando
        )
        btn.pack(padx=10, pady=2, fill="x")
        return btn

    def _mostrar_panel(self, nombre):
        self.panel_rutina.pack_forget()
        self.panel_editar.pack_forget()

        if nombre == "rutina":
            self.panel_rutina.pack(fill="both", expand=True)
            self.panel_rutina.refresh(self.bd)
        elif nombre == "editar":
            self.panel_editar.pack(fill="both", expand=True)
            self.panel_editar.refresh(self.bd)

    # ── Callbacks ─────────────────────────────────────────────────────────
    def _on_dia_select(self, dia):
        """Recibe el día seleccionado en PanelRutina para mostrarlo."""
        pass  # el panel maneja su propio refresh interno

    def _on_guardado(self, bd_actualizado):
        """Llamado desde PanelEditar al guardar."""
        self.bd = bd_actualizado
        self.bd_ref[0] = bd_actualizado
        guardar_rutina(bd_actualizado)

    def _toggle_asistente(self):
        if not self.running_flag[0]:
            self.running_flag[0] = True
            self.hilo = threading.Thread(
                target=loop_rutina,
                args=(self.bd_ref, self.estado_label, self.running_flag),
                daemon=True
            )
            self.hilo.start()
            self.btn_toggle.configure(text="⏹  Detener asistente", fg_color="#DC2626",
                                      hover_color="#B91C1C")
        else:
            self.running_flag[0] = False
            self.btn_toggle.configure(text="▶  Iniciar asistente", fg_color=COLOR_PRIMARIO,
                                      hover_color="#1D4ED8")
            self.estado_label.configure(text="⏹  Detenido",
                                        text_color=COLOR_SUBTEXTO, fg_color="#F1F5F9")

# ─── Panel: Ver rutina semanal ───────────────────────────────────────────────
class PanelRutina(ctk.CTkFrame):
    def __init__(self, parent, bd, on_dia_select):
        super().__init__(parent, fg_color=COLOR_FONDO, corner_radius=0)
        self.bd = bd
        self.on_dia_select = on_dia_select
        self.dia_actual = DIAS[0]
        self._build()

    def _build(self):
        # Encabezado
        header = ctk.CTkFrame(self, fg_color=COLOR_FONDO, corner_radius=0)
        header.pack(fill="x", padx=28, pady=(28, 0))
        ctk.CTkLabel(header, text="Rutina semanal",
                     font=("Segoe UI", 22, "bold"), text_color=COLOR_TEXTO).pack(side="left")

        # Selector de días
        dias_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12)
        dias_frame.pack(fill="x", padx=28, pady=16)

        self.dia_btns = {}
        dias_display = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for i, (dia, label) in enumerate(zip(DIAS, dias_display)):
            btn = ctk.CTkButton(
                dias_frame, text=label, width=70, height=36,
                fg_color="transparent", hover_color="#EFF6FF",
                text_color=COLOR_SUBTEXTO, font=("Segoe UI", 12),
                corner_radius=8,
                command=lambda d=dia: self._seleccionar_dia(d)
            )
            btn.pack(side="left", padx=6, pady=8)
            self.dia_btns[dia] = btn

        # Tabla de actividades
        self.tabla_frame = ScrollFrame(self, bg=COLOR_FONDO)
        self.tabla_frame.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        self._seleccionar_dia(DIAS[datetime.now().weekday()])

    def _seleccionar_dia(self, dia):
        self.dia_actual = dia
        # Resaltar botón activo
        for d, btn in self.dia_btns.items():
            if d == dia:
                btn.configure(fg_color=COLOR_PRIMARIO, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_SUBTEXTO)
        self._renderizar_tabla(dia)
        self.on_dia_select(dia)

    def _renderizar_tabla(self, dia):
        self.tabla_frame.clear()
        parent = self.tabla_frame.inner

        lista = inicializar_dia(self.bd, dia)
        hora_actual = datetime.now().hour
        dia_actual_sys = DIAS[datetime.now().weekday()]

        for i, hora in enumerate(HORAS):
            titulo  = lista[i][0] if i < len(lista) else "(Vacío)"
            mensaje = lista[i][1] if i < len(lista) else "Sin actividad asignada"
            es_ahora = (dia == dia_actual_sys and hora == hora_actual and hora in HORAS)

            bg_card   = COLOR_ACTIVO if es_ahora else COLOR_CARD
            borde_col = COLOR_PRIMARIO if es_ahora else COLOR_BORDE

            # Contenedor externo para simular borde
            outer = tk.Frame(parent, bg=borde_col, padx=1, pady=1)
            outer.pack(fill="x", pady=4)

            card = tk.Frame(outer, bg=bg_card)
            card.pack(fill="both", expand=True)

            # Hora
            tk.Label(
                card, text=f"{hora:02d}:00",
                font=("Segoe UI", 12, "bold"),
                fg=COLOR_PRIMARIO if es_ahora else COLOR_SUBTEXTO,
                bg=bg_card, width=6
            ).pack(side="left", padx=(16, 0), pady=14)

            # Separador vertical
            tk.Frame(card, width=1, bg=COLOR_BORDE).pack(
                side="left", fill="y", padx=12, pady=10)

            # Contenido
            info = tk.Frame(card, bg=bg_card)
            info.pack(side="left", fill="both", expand=True, pady=10)

            tk.Label(
                info, text=titulo,
                font=("Segoe UI", 12, "bold"),
                fg=COLOR_ACTIVO_TXT if es_ahora else COLOR_TEXTO,
                bg=bg_card, anchor="w"
            ).pack(anchor="w")
            tk.Label(
                info, text=mensaje,
                font=("Segoe UI", 11),
                fg=COLOR_SUBTEXTO,
                bg=bg_card, anchor="w", wraplength=480, justify="left"
            ).pack(anchor="w")

            if es_ahora:
                tk.Label(
                    card, text="● AHORA",
                    font=("Segoe UI", 10, "bold"),
                    fg=COLOR_ACTIVO_TXT, bg=bg_card
                ).pack(side="right", padx=16)

    def refresh(self, bd):
        self.bd = bd
        self._renderizar_tabla(self.dia_actual)


# ─── Panel: Editar rutina ────────────────────────────────────────────────────
class PanelEditar(ctk.CTkFrame):
    def __init__(self, parent, bd, on_guardado):
        super().__init__(parent, fg_color=COLOR_FONDO, corner_radius=0)
        self.bd = bd
        self.on_guardado = on_guardado
        self.dia_actual = DIAS[0]
        self._build()

    def _build(self):
        # Encabezado
        header = ctk.CTkFrame(self, fg_color=COLOR_FONDO, corner_radius=0)
        header.pack(fill="x", padx=28, pady=(28, 0))
        ctk.CTkLabel(header, text="Editar rutina",
                     font=("Segoe UI", 22, "bold"), text_color=COLOR_TEXTO).pack(side="left")

        # Selector de día
        sel_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12)
        sel_frame.pack(fill="x", padx=28, pady=16)

        ctk.CTkLabel(sel_frame, text="Día:",
                     font=("Segoe UI", 13), text_color=COLOR_SUBTEXTO).pack(side="left", padx=16, pady=12)

        self.dia_var = ctk.StringVar(value=DIAS[0])
        self.combo_dia = ctk.CTkOptionMenu(
            sel_frame,
            values=[d.capitalize() for d in DIAS],
            variable=ctk.StringVar(value=DIAS[0].capitalize()),
            fg_color=COLOR_PRIMARIO, button_color="#1D4ED8",
            font=("Segoe UI", 12), width=160,
            command=self._on_dia_change
        )
        self.combo_dia.pack(side="left", padx=(0, 16), pady=10)

        # Lista scrollable de slots
        self.slots_frame = ScrollFrame(self, bg=COLOR_FONDO)
        self.slots_frame.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        self._renderizar_slots(DIAS[0])

    def _on_dia_change(self, valor):
        self.dia_actual = valor.lower()
        self._renderizar_slots(self.dia_actual)

    def _renderizar_slots(self, dia):
        self.slots_frame.clear()
        parent = self.slots_frame.inner

        self.entradas = []
        lista = inicializar_dia(self.bd, dia)

        for i, hora in enumerate(HORAS):
            titulo_val  = lista[i][0] if i < len(lista) else "(Vacío)"
            mensaje_val = lista[i][1] if i < len(lista) else "Sin actividad asignada"

            # Borde simulado
            outer = tk.Frame(parent, bg=COLOR_BORDE, padx=1, pady=1)
            outer.pack(fill="x", pady=4)

            card = tk.Frame(outer, bg=COLOR_CARD)
            card.pack(fill="both", expand=True)

            # Hora
            tk.Label(
                card, text=f"{hora:02d}:00",
                font=("Segoe UI", 12, "bold"),
                fg=COLOR_PRIMARIO, bg=COLOR_CARD, width=6
            ).grid(row=0, column=0, rowspan=2, padx=(14, 0), pady=12)

            # Divisor vertical
            tk.Frame(card, width=1, bg=COLOR_BORDE).grid(
                row=0, column=1, rowspan=2, sticky="ns", padx=12, pady=10)

            # Labels + Entries
            tk.Label(card, text="Título", font=("Segoe UI", 9),
                     fg=COLOR_SUBTEXTO, bg=COLOR_CARD).grid(
                row=0, column=2, sticky="w", pady=(10, 0))

            titulo_entry = ctk.CTkEntry(
                card, placeholder_text="Ej: Reunión de equipo",
                width=300, font=("Segoe UI", 12),
                fg_color="#F8FAFC", border_color=COLOR_BORDE
            )
            titulo_entry.insert(0, titulo_val)
            titulo_entry.grid(row=0, column=3, padx=(0, 14), pady=(10, 4), sticky="ew")

            tk.Label(card, text="Mensaje", font=("Segoe UI", 9),
                     fg=COLOR_SUBTEXTO, bg=COLOR_CARD).grid(
                row=1, column=2, sticky="w")

            mensaje_entry = ctk.CTkEntry(
                card, placeholder_text="Descripción de la actividad...",
                width=300, font=("Segoe UI", 12),
                fg_color="#F8FAFC", border_color=COLOR_BORDE
            )
            mensaje_entry.insert(0, mensaje_val)
            mensaje_entry.grid(row=1, column=3, padx=(0, 14), pady=(0, 10), sticky="ew")

            card.columnconfigure(3, weight=1)
            self.entradas.append((titulo_entry, mensaje_entry))

        # Botón guardar
        btn_guardar = ctk.CTkButton(
            parent, text="💾  Guardar cambios",
            fg_color=COLOR_PRIMARIO, hover_color="#1D4ED8",
            font=("Segoe UI", 13, "bold"), corner_radius=10, height=42,
            command=self._guardar
        )
        btn_guardar.pack(pady=16, padx=4, fill="x")

    def _guardar(self):
        dia = self.dia_actual
        nueva_lista = []
        for titulo_e, mensaje_e in self.entradas:
            nueva_lista.append([titulo_e.get().strip(), mensaje_e.get().strip()])

        self.bd[dia] = nueva_lista
        self.on_guardado(self.bd)
        messagebox.showinfo("Guardado", f"La rutina del {dia.capitalize()} fue guardada ✅")

    def refresh(self, bd):
        self.bd = bd
        self._renderizar_slots(self.dia_actual)


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = AdviserApp()
    app.mainloop()
