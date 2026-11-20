"""Componentes compartidos de las pantallas de escritorio."""
import os
import threading
from tkinter import messagebox

import customtkinter as ctk

WINE = '#510F26'
ACCENT = '#801537'
BG = '#F5F6F8'
WHITE = '#FFFFFF'
TEXT = '#28262B'
MUTED = '#817B87'
LINE = '#DEDCE2'
SOFT = '#F1F2F5'
PINK = '#F5E8EE'
GOLD = '#F5D447'
GREEN = '#22865E'
BLUE = '#3274A6'

ctk.set_appearance_mode('light')
ctk.set_default_color_theme('blue')

# Pantallas permitidas en el enrutador de la ventana principal.
PANTALLAS = {
    'applogin.py',
    'home.py',
    'update.py',
    'folio_reservado.py',
    'crear_documento.py',
    'enviados.py',
}


def font(size=13, bold=False):
    return ctk.CTkFont(family='Segoe UI', size=size, weight='bold' if bold else 'normal')


def label(parent, text, size=13, color=TEXT, bold=False, **kwargs):
    return ctk.CTkLabel(parent, text=text, font=font(size, bold), text_color=color, **kwargs)


def button(parent, text, command=None, primary=False, **kwargs):
    options = dict(
        height=42, corner_radius=10, font=font(13, True),
        fg_color=ACCENT if primary else WHITE,
        hover_color=WINE if primary else SOFT,
        text_color=WHITE if primary else TEXT,
        border_width=0 if primary else 1, border_color=LINE)
    options.update(kwargs)
    return ctk.CTkButton(parent, text=text, command=command, **options)


def entry(parent, placeholder='', **kwargs):
    options = dict(
        height=40, corner_radius=8, fg_color=WHITE, border_color=LINE,
        border_width=1, font=font(12), text_color=TEXT, placeholder_text_color=MUTED)
    options.update(kwargs)
    return ctk.CTkEntry(parent, placeholder_text=placeholder, **options)


def card(parent, **kwargs):
    options = dict(fg_color=WHITE, corner_radius=14, border_width=1, border_color=LINE)
    options.update(kwargs)
    return ctk.CTkFrame(parent, **options)


def select(parent, values, command=None, width=100):
    return ctk.CTkOptionMenu(
        parent, values=values, command=command, width=width,
        height=34, corner_radius=7, fg_color=WHITE, button_color=WHITE,
        button_hover_color=SOFT, text_color=TEXT, font=font(11),
        dropdown_fg_color=WHITE, dropdown_text_color=TEXT, dropdown_hover_color=PINK)


def unavailable(window, name):
    messagebox.showinfo(
        name,
        'Esta función requiere un módulo o servicio que todavía no está conectado en este prototipo.',
        parent=window)


def usuario_actual():
    """Usuario autenticado, compartido entre pantallas por variable de entorno."""
    return os.environ.get('GI_USUARIO', 'Usuario Institucional')


def usuario_actual_id():
    """Identificador estable de la cuenta autenticada."""
    return os.environ.get('GI_USUARIO_ID', '')


def usuario_actual_email():
    """Nombre de usuario de Microsoft para seleccionar su cuenta de Graph."""
    return os.environ.get('GI_USUARIO_EMAIL', '')


def open_screen(window, filename, extra_args=None):
    """Muestra otra pantalla dentro de la ventana principal."""
    if filename not in PANTALLAS:
        messagebox.showerror(
            'Navegación', f'Pantalla no reconocida: {filename}', parent=window)
        return

    app = window.winfo_toplevel()
    if not hasattr(app, 'show_screen'):
        messagebox.showerror(
            'Navegación',
            'No se encontró el controlador de navegación de la aplicación.',
            parent=window,
        )
        return
    app.show_screen(filename, extra_args)


def window_setup(window, title, height=900):
    window.title(title)
    # Mantiene las proporciones de las referencias en pantallas con menos espacio.
    dpi = ctk.ScalingTracker.get_window_dpi_scaling(window)
    scale = min(1.0, window.winfo_screenwidth() / (1480 * dpi),
                window.winfo_screenheight() / (980 * dpi))
    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)
    window.geometry(f'1440x{height}')
    window.minsize(1440, 740)
    window.maxsize(10000, 10000)
    window.configure(fg_color=BG)


def brand(parent, large=False):
    frame = ctk.CTkFrame(parent, fg_color='transparent')
    badge = ctk.CTkFrame(
        frame, width=52 if large else 42, height=52 if large else 42,
        fg_color=ACCENT, border_width=1, border_color='#913A57', corner_radius=12)
    badge.pack(side='left', padx=(0, 14 if large else 12))
    badge.pack_propagate(False)
    label(badge, 'CG', 20 if large else 17, WHITE, True).pack(expand=True)
    texts = ctk.CTkFrame(frame, fg_color='transparent')
    texts.pack(side='left')
    label(texts, 'Gestión Institucional', 15 if large else 12, WHITE, True, height=20).pack(anchor='w')
    label(texts, 'CONTROL DOCUMENTAL', 10 if large else 9, '#C9A7B5', height=16).pack(anchor='w')
    return frame


class Shell(ctk.CTkFrame):
    def __init__(self, master, active='Correspondencia'):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.title('Gestión Institucional - Control Documental')
        self.usuario = usuario_actual()
        self.usuario_id = usuario_actual_id()
        self.usuario_email = usuario_actual_email()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- Barra lateral ----
        self.sidebar = ctk.CTkFrame(self, width=248, corner_radius=0, fg_color=WINE)
        self.sidebar.grid(row=0, column=0, sticky='nsew')
        self.sidebar.grid_propagate(False)
        self.sidebar.pack_propagate(False)
        brand(self.sidebar).pack(anchor='w', padx=26, pady=(24, 18))
        self.nav_buttons = {}
        sections = [
            ('OPERACIÓN', ['Correspondencia · 18', 'Por asignar · 7', 'Seguimiento · 12', 'Enviada']),
            ('CONSULTA Y CONTROL', ['Búsqueda avanzada', 'Archivo', 'Reportes']),
            ('ADMINISTRACIÓN', ['Áreas y usuarios', 'Catálogos',
                                'Actualización' if active == 'Actualización' else 'Configuración']),
        ]
        for title, items in sections:
            label(self.sidebar, title, 9, '#CFACB9', True, height=18).pack(
                anchor='w', padx=18, pady=(0 if title == 'OPERACIÓN' else 16, 3))
            for text in items:
                selected = text.startswith(active)
                line = ctk.CTkFrame(self.sidebar, fg_color='transparent', height=26)
                line.pack(fill='x', padx=18)
                marker = ctk.CTkFrame(line, width=6, height=14, corner_radius=0,
                                      fg_color=GOLD if selected else WINE)
                marker.pack(side='left', padx=(0, 7))
                control = ctk.CTkButton(
                    line, text=text, height=26, width=195,
                    fg_color='transparent', hover_color=ACCENT,
                    text_color=GOLD if selected else WHITE,
                    anchor='w', font=font(13, selected), corner_radius=4,
                    command=lambda name=text: self.navigate(name))
                control.pack(side='left', fill='x', expand=True)
                self.nav_buttons[text] = control

        if active != 'Actualización':
            cut = ctk.CTkFrame(self.sidebar, fg_color='#671630', corner_radius=15)
            cut.pack(fill='x', padx=18, pady=24)
            label(cut, '●  Corte de recepción', 11, WHITE, True, height=22).pack(anchor='w', padx=14, pady=(10, 0))
            label(cut, 'Ventanilla abierta hasta las 17:00 h.', 10, '#D6B2C0', height=18).pack(
                anchor='w', padx=14, pady=(0, 10))

        # ---- Área principal ----
        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main.grid(row=0, column=1, sticky='nsew')
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self.top = ctk.CTkFrame(self.main, fg_color=WHITE, height=76, corner_radius=0)
        self.top.grid(row=0, column=0, sticky='ew')
        self.top.grid_columnconfigure(0, weight=1)
        self.search_entry = entry(
            self.top, '⌕   Buscar por folio, asunto, remitente o área...',
            width=510, height=42, fg_color=SOFT, border_width=0)
        self.search_entry.grid(row=0, column=0, sticky='w', padx=28, pady=17)

        # Perfil: botones de ayuda/notificaciones + avatar con iniciales
        partes = self.usuario.split()
        iniciales = ''.join(p[0].upper() for p in partes[:2]) if partes else 'UI'

        profile = ctk.CTkFrame(self.top, fg_color='transparent')
        profile.grid(row=0, column=1, padx=(8, 28))
        button(profile, '?', lambda: unavailable(self, 'Ayuda'),
               width=24, border_width=0, height=32).pack(side='left', padx=2)
        self.notification_button = button(
            profile, '♢', self.mostrar_notificaciones,
            width=56, border_width=0, height=32)
        self.notification_button.pack(side='left', padx=2)
        label(profile, iniciales, 12, ACCENT, True, width=38, height=38,
              fg_color=PINK, corner_radius=19).pack(side='left', padx=(10, 12))
        label(profile, self.usuario, 12, TEXT, True).pack(side='left')
        label(profile, '⌄', 12, MUTED).pack(side='left', padx=(10, 0))

        self.body = ctk.CTkScrollableFrame(
            self.main, fg_color=BG, corner_radius=0,
            scrollbar_button_color=LINE, scrollbar_button_hover_color=MUTED)
        self.body.grid(row=1, column=0, sticky='nsew')
        self.body.grid_columnconfigure(0, weight=1)
        self.actualizar_contador_notificaciones()

    def actualizar_contador_notificaciones(self):
        if not self.usuario_id:
            return
        self.notification_button.configure(text='♢ …')
        threading.Thread(
            target=self._cargar_contador_notificaciones,
            daemon=True,
        ).start()

    def _cargar_contador_notificaciones(self):
        from controller.database_conecction import Database_connection
        try:
            pendientes = Database_connection().contar_notificaciones_no_leidas(
                self.usuario_id)
        except (ConnectionError, RuntimeError) as error:
            self.after(0, lambda error=error: self._mostrar_error_notificaciones(error))
            return
        self.after(
            0, lambda pendientes=pendientes: self._mostrar_contador_notificaciones(
                pendientes))

    def _mostrar_contador_notificaciones(self, pendientes):
        self.notification_button.configure(
            text=f'♢ {pendientes}' if pendientes else '♢')

    def _mostrar_error_notificaciones(self, error):
        self.notification_button.configure(text='♢ !')
        root = self.winfo_toplevel()
        if not getattr(root, '_notification_error_shown', False):
            messagebox.showwarning(
                'Notificaciones',
                f'No se pudo consultar la campana de notificaciones.\n\n{error}',
                parent=self,
            )
            root._notification_error_shown = True

    def mostrar_notificaciones(self):
        if not self.usuario_id:
            messagebox.showerror(
                'Notificaciones',
                'No se encontró el identificador de tu cuenta de Microsoft.',
                parent=self,
            )
            return
        from controller.database_conecction import Database_connection
        database = Database_connection()
        try:
            notificaciones = database.listar_notificaciones(self.usuario_id)
            database.marcar_notificaciones_leidas(
                self.usuario_id, [item['id'] for item in notificaciones])
            notificaciones = database.listar_notificaciones(self.usuario_id)
        except (ConnectionError, RuntimeError) as error:
            messagebox.showerror('Notificaciones', str(error), parent=self)
            return

        ventana = ctk.CTkToplevel(self)
        ventana.title('Notificaciones')
        ventana.geometry('620x520')
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        label(ventana, 'Notificaciones', 22, TEXT, True).pack(
            anchor='w', padx=22, pady=(20, 12))
        lista = ctk.CTkScrollableFrame(ventana, fg_color='transparent')
        lista.pack(fill='both', expand=True, padx=14, pady=(0, 16))

        if not notificaciones:
            label(lista, 'No hay notificaciones por ahora.', 13, MUTED).pack(
                anchor='w', padx=10, pady=12)
        for item in notificaciones:
            fecha = item['creada_en'].strftime('%d/%m/%Y %H:%M')
            tarjeta = card(lista)
            tarjeta.pack(fill='x', padx=6, pady=5)
            etiqueta = '●  ' if not item['leida'] else ''
            label(tarjeta, f"{etiqueta}{item['titulo']}", 13, TEXT, True).pack(
                anchor='w', padx=14, pady=(12, 3))
            label(
                tarjeta, f"{item['mensaje']}\n{fecha}",
                11, MUTED, justify='left', anchor='w',
            ).pack(anchor='w', padx=14, pady=(0, 12))
        self.actualizar_contador_notificaciones()

    def on_show(self):
        self.actualizar_contador_notificaciones()

    def navigate(self, name):
        if name.startswith('Correspondencia'):
            open_screen(self, 'home.py')
        elif name == 'Enviada':
            open_screen(self, 'enviados.py')
        elif name in ('Configuración', 'Actualización'):
            open_screen(self, 'update.py')
        elif name == 'Búsqueda avanzada':
            self.search_entry.focus_set()
        else:
            unavailable(self, name)

    def title(self, value):
        self.winfo_toplevel().title(value)