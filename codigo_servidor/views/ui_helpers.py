"""Componentes compartidos de las pantallas de escritorio."""
import os
import threading
from pathlib import Path
from tkinter import TclError, messagebox

import customtkinter as ctk
from PIL import Image

WINE = '#510F26'
ACCENT = '#C2185B'
BG = '#F5F6F8'
WHITE = '#FFFFFF'
TEXT = '#1F2937'
MUTED = '#6B7280'
LINE = '#E5E7EB'
SOFT = '#F9FAFB'
PINK = '#FCE7F3'
GOLD = '#F5D447'
GREEN = '#16A34A'
BLUE = '#2563EB'
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
MIN_WIDGET_SCALING = 1.15
MAX_WIDGET_SCALING = 1.25

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
    'dashboard.py',
    'areas_usuarios.py',
}


def font(size=13, bold=False):
    adjusted_size = size + 2 if size <= 14 else size
    return ctk.CTkFont(
        family='Segoe UI', size=adjusted_size,
        weight='bold' if bold else 'normal')


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
        height=44, corner_radius=9, fg_color=WHITE, border_color=LINE,
        border_width=1, font=font(13), text_color=TEXT, placeholder_text_color=MUTED)
    options.update(kwargs)
    return ctk.CTkEntry(parent, placeholder_text=placeholder, **options)


def card(parent, **kwargs):
    options = dict(fg_color=WHITE, corner_radius=14, border_width=1, border_color=LINE)
    options.update(kwargs)
    return ctk.CTkFrame(parent, **options)


def select(parent, values, command=None, width=100):
    return ctk.CTkOptionMenu(
        parent, values=values, command=command, width=width,
        height=38, corner_radius=8, fg_color=WHITE, button_color=WHITE,
        button_hover_color=SOFT, text_color=TEXT, font=font(12),
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


def window_setup(window, title):
    window.title(title)
    dpi = ctk.ScalingTracker.get_window_dpi_scaling(window)
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    fit_scale = min(
        screen_width / (1480 * dpi),
        screen_height / (900 * dpi),
    )
    scale = max(MIN_WIDGET_SCALING, min(MAX_WIDGET_SCALING, fit_scale))
    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)
    window_width = min(WINDOW_WIDTH, screen_width)
    window_height = min(WINDOW_HEIGHT, screen_height)
    window.geometry(f'{window_width}x{window_height}+0+0')
    window.minsize(min(800, window_width), min(600, window_height))
    window.maxsize(window_width, window_height)
    window.resizable(True, True)
    window.configure(fg_color=BG)
    window.after_idle(lambda: maximize_window(window))


def maximize_window(window):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    try:
        if screen_width > WINDOW_WIDTH and screen_height > WINDOW_HEIGHT:
            window.state('normal')
            window.geometry(f'{WINDOW_WIDTH}x{WINDOW_HEIGHT}+0+0')
        else:
            window.state('zoomed')
    except TclError:
        window.geometry(
            f'{min(WINDOW_WIDTH, screen_width)}x'
            f'{min(WINDOW_HEIGHT, screen_height)}+0+0'
        )


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


def image(filename, height):
    """Carga una imagen de views/assets conservando su proporción."""
    ruta = Path(__file__).resolve().parent / 'assets' / filename
    if not ruta.is_file():
        return None
    try:
        with Image.open(ruta) as source:
            original = source.convert('RGBA')
    except OSError:
        return None
    width = round(original.width * height / original.height)
    return ctk.CTkImage(light_image=original, dark_image=original,
                        size=(width, height))


class Shell(ctk.CTkFrame):
    def __init__(self, master, active='Correspondencia'):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.title('Gestión Institucional - Control Documental')
        self.usuario = usuario_actual()
        self.usuario_id = usuario_actual_id()
        self.usuario_email = usuario_actual_email()
        try:
            from model.areas_usuarios import usuario_puede_administrar
            self.puede_administrar = usuario_puede_administrar(self.usuario_email)
        except (ConnectionError, RuntimeError) as error:
            self.puede_administrar = False
            root = self.winfo_toplevel()
            if not getattr(root, '_areas_permission_error_shown', False):
                root._areas_permission_error_shown = True
                self.after(
                    0,
                    lambda error=error: messagebox.showwarning(
                        'Áreas y usuarios',
                        f'No se pudo validar el acceso de administración.\n\n{error}',
                        parent=self,
                    ),
                )
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
            ('OPERACIÓN', ['Correspondencia', 'Dashboard', 'No leídos', 'Seguimiento', 'Enviados']),
            ('CONSULTA Y CONTROL', ['Búsqueda avanzada', 'Archivo', 'Reportes']),
        ]
        if self.puede_administrar:
            sections.append((
                'ADMINISTRACIÓN',
                ['Áreas y usuarios', 'Catálogos',
                 'Actualización' if active == 'Actualización' else 'Configuración'],
            ))
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

        self.top = ctk.CTkFrame(self.main, fg_color=WHITE, height=84, corner_radius=0)
        self.top.grid(row=0, column=0, sticky='ew')
        self.top.grid_columnconfigure(0, weight=1)
        self.search_entry = entry(
            self.top, '⌕   Buscar por folio, asunto, remitente o área...',
            width=550, height=46, fg_color=SOFT, border_width=0)
        self.search_entry.grid(row=0, column=0, sticky='w', padx=32, pady=18)
        self.search_entry.bind('<Return>', self.buscar_global)

        # Perfil: botones de ayuda/notificaciones + avatar con iniciales
        partes = self.usuario.split()
        iniciales = ''.join(p[0].upper() for p in partes[:2]) if partes else 'UI'

        profile = ctk.CTkFrame(self.top, fg_color='transparent')
        profile.grid(row=0, column=1, padx=(8, 32))
        button(profile, '?', lambda: unavailable(self, 'Ayuda'),
               width=24, border_width=0, height=32).pack(side='left', padx=2)
        notification_area = ctk.CTkFrame(profile, fg_color='transparent', width=58, height=40)
        notification_area.pack(side='left', padx=2)
        notification_area.pack_propagate(False)
        self.notification_button = button(
            notification_area, '♢', self.mostrar_notificaciones,
            width=54, border_width=0, height=36)
        self.notification_button.pack(side='left')
        self.notification_badge = label(
            notification_area, '', 10, WHITE, True, width=22, height=19,
            fg_color='#C21D3B', corner_radius=10)
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
            database = Database_connection()
            pendientes = database.contar_notificaciones_no_leidas(self.usuario_id)
            borradores = database.listar_borradores(self.usuario_id)
        except (ConnectionError, RuntimeError) as error:
            self.after(0, lambda error=error: self._mostrar_error_notificaciones(error))
            return
        try:
            self.after(0, lambda: self._mostrar_contador_notificaciones(
                pendientes, len(borradores)))
        except RuntimeError:
            pass

    def _mostrar_contador_notificaciones(self, pendientes, borradores=0):
        self.notification_button.configure(text='♢')
        total = pendientes + borradores
        if total:
            self.notification_badge.configure(text=str(total) if total <= 99 else '99+')
            self.notification_badge.place(relx=1, x=0, y=0, anchor='ne')
        else:
            self.notification_badge.place_forget()

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
        panel_actual = getattr(self, '_panel_notificaciones', None)
        if panel_actual is not None and panel_actual.winfo_exists():
            panel_actual.destroy()
            self._panel_notificaciones = None
            return
        if not self.usuario_id:
            messagebox.showerror(
                'Notificaciones',
                'No se encontró el identificador de tu cuenta de Microsoft.',
                parent=self,
            )
            return

        ventana = ctk.CTkFrame(
            self.main, width=545, height=530, fg_color=WHITE,
            border_width=1, border_color=LINE, corner_radius=13)
        ventana.place(relx=1, x=-20, y=70, anchor='ne')
        ventana.pack_propagate(False)
        ventana.lift()
        self._panel_notificaciones = ventana
        cabecera = ctk.CTkFrame(ventana, fg_color='transparent')
        cabecera.pack(fill='x', padx=17, pady=(14, 8))
        label(cabecera, 'Notificaciones', 19, TEXT, True).pack(side='left')
        button(cabecera, '✕', lambda: ventana.destroy(), width=30,
               height=30, border_width=0).pack(side='right')
        ventana.notification_list = ctk.CTkScrollableFrame(
            ventana, fg_color=BG, corner_radius=10,
            scrollbar_button_color=LINE, scrollbar_button_hover_color=MUTED)
        ventana.notification_list.pack(
            fill='both', expand=True, padx=11, pady=(0, 12))
        label(ventana.notification_list, 'Cargando notificaciones...', 13, MUTED).pack(
            anchor='w', padx=10, pady=12)
        self._cargar_notificaciones_panel(ventana)

    def _cargar_notificaciones_panel(self, ventana):
        if not ventana.winfo_exists():
            return
        for elemento in ventana.notification_list.winfo_children():
            elemento.destroy()
        label(ventana.notification_list, 'Cargando notificaciones...', 13, MUTED).pack(
            anchor='w', padx=10, pady=12)

        def consultar():
            from controller.database_conecction import Database_connection
            try:
                database = Database_connection()
                notificaciones = database.listar_notificaciones(self.usuario_id)
                borradores = database.listar_borradores(self.usuario_id)
            except (ConnectionError, RuntimeError) as error:
                try:
                    self.after(0, lambda error=error:
                               self._mostrar_error_panel_notificaciones(ventana, error))
                except RuntimeError:
                    pass
                return
            try:
                self.after(
                    0, lambda: self._renderizar_notificaciones(
                        ventana, notificaciones, borradores))
            except RuntimeError:
                pass

        threading.Thread(target=consultar, daemon=True).start()

    def _mostrar_error_panel_notificaciones(self, ventana, error):
        if not ventana.winfo_exists():
            return
        for elemento in ventana.notification_list.winfo_children():
            elemento.destroy()
        label(
            ventana.notification_list,
            f'No se pudieron cargar las notificaciones: {error}',
            12, ACCENT, justify='left', wraplength=480,
        ).pack(anchor='w', padx=10, pady=12)
        messagebox.showerror('Notificaciones', str(error), parent=self)

    def _renderizar_notificaciones(self, ventana, notificaciones, borradores):
        if not ventana.winfo_exists():
            return
        lista = ventana.notification_list
        for elemento in lista.winfo_children():
            elemento.destroy()
        if borradores:
            label(lista, f'Documentos pendientes ({len(borradores)})', 16, TEXT, True).pack(
                anchor='w', padx=10, pady=(8, 10))
        for borrador in borradores:
            tarjeta = card(lista)
            tarjeta.pack(fill='x', padx=6, pady=6)
            estado = borrador['estado']
            asunto = borrador['asunto'] or 'Sin asunto'
            fecha = borrador['actualizado_en'].strftime('%d/%m/%Y %H:%M')
            label(tarjeta, borrador['folio'], 13, ACCENT, True).pack(
                anchor='w', padx=14, pady=(12, 3))
            label(tarjeta, f'{asunto} · {estado} · {fecha}', 11, MUTED,
                  justify='left', anchor='w', wraplength=550).pack(
                      anchor='w', padx=14, pady=(0, 8))
            acciones = ctk.CTkFrame(tarjeta, fg_color='transparent')
            acciones.pack(fill='x', padx=14, pady=(0, 12))
            button(acciones, 'Seguir editando' if estado == 'Borrador' else 'Generar PDF',
                   lambda folio=borrador['folio'], tipo=estado:
                       self._abrir_borrador_desde_notificacion(ventana, folio, tipo),
                   width=155, height=34).pack(side='left', padx=(0, 8))
            if estado == 'Borrador':
                button(acciones, 'Guardar',
                       lambda folio=borrador['folio']:
                           self._abrir_borrador_desde_notificacion(
                               ventana, folio, 'Borrador', guardar=True),
                       primary=True, width=120, height=34).pack(side='left')

        if notificaciones:
            label(lista, 'Otras notificaciones', 16, TEXT, True).pack(
                anchor='w', padx=10, pady=(15, 10))
        elif not borradores:
            label(lista, 'No hay notificaciones ni documentos pendientes.', 13, MUTED).pack(
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
            ).pack(anchor='w', padx=14, pady=(0, 8))
            if not item['leida']:
                button(
                    tarjeta, 'Marcar como leída',
                    lambda notification_id=item['id']:
                        self._marcar_notificacion_leida(ventana, notification_id),
                    width=150, height=30,
                ).pack(anchor='e', padx=14, pady=(0, 10))
        self.actualizar_contador_notificaciones()

    def _marcar_notificacion_leida(self, ventana, notificacion_id):
        def marcar():
            from controller.database_conecction import Database_connection
            try:
                Database_connection().marcar_notificaciones_leidas(
                    self.usuario_id, [notificacion_id])
            except (ConnectionError, RuntimeError) as error:
                try:
                    self.after(0, lambda error=error:
                               self._mostrar_error_panel_notificaciones(ventana, error))
                except RuntimeError:
                    pass
                return
            try:
                self.after(
                    0, lambda: self._cargar_notificaciones_panel(ventana)
                    if ventana.winfo_exists() else None)
            except RuntimeError:
                pass

        threading.Thread(target=marcar, daemon=True).start()

    def _abrir_borrador_desde_notificacion(self, ventana, folio, estado, guardar=False):
        from controller.database_conecction import Database_connection
        try:
            borrador = Database_connection().obtener_borrador(folio, self.usuario_id)
            if borrador is None or borrador['estado'] not in ('Borrador', 'Creado'):
                raise ValueError('El documento ya no está disponible para editarlo.')
            if borrador['estado'] == 'Creado':
                pantalla = 'folio_reservado.py'
            else:
                pantalla = 'crear_documento.py'
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror('Documento pendiente', str(error), parent=self)
            return
        ventana.destroy()
        open_screen(self, pantalla, folio)
        if guardar and pantalla == 'crear_documento.py':
            pagina = self.winfo_toplevel().active_page
            if getattr(pagina, 'folio', None) == folio:
                pagina.guardar()
        self.actualizar_contador_notificaciones()

    def on_show(self):
        self.actualizar_contador_notificaciones()

    def navigate(self, name):
        if name.startswith('Correspondencia'):
            open_screen(self, 'home.py')
        elif name == 'Enviados':
            open_screen(self, 'enviados.py')
        elif name == 'Dashboard':
            open_screen(self, 'dashboard.py')
        elif name == 'Áreas y usuarios':
            open_screen(self, 'areas_usuarios.py')
        elif name in ('Configuración', 'Actualización'):
            open_screen(self, 'update.py')
        elif name == 'Búsqueda avanzada':
            self.buscar_global()
        else:
            unavailable(self, name)

    def buscar_global(self, _event=None):
        consulta = self.search_entry.get().strip()
        app = self.winfo_toplevel()
        open_screen(self, 'home.py')

        def enfocar_busqueda():
            pagina = getattr(app, 'active_page', None)
            campo = getattr(pagina, 'search_entry', None)
            if campo is None:
                return
            pagina.category = 'all'
            if consulta:
                campo.delete(0, 'end')
                campo.insert(0, consulta)
                pagina.filter_rows()
            campo.focus_set()

        app.after(0, enfocar_busqueda)

    def title(self, value):
        self.winfo_toplevel().title(value)