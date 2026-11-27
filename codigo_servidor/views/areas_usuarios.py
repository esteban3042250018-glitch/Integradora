"""Interfaz de administración de áreas y usuarios institucionales."""

from tkinter import messagebox
import customtkinter as ctk

from model.areas_usuarios import (
    agregar_area, agregar_empleado, eliminar_area,
    eliminar_empleado, listar_areas, listar_empleados,
    usuario_puede_administrar,
)
from views.ui_helpers import (
    ACCENT, BG, LINE, MUTED, PINK, TEXT, WHITE, Shell,
    button, card, entry, label, usuario_actual_email,
)


class AreasUsuariosApp(Shell):
    def __init__(self, master):
        if not usuario_puede_administrar(usuario_actual_email()):
            raise PermissionError(
                'Acceso restringido. Tu cuenta no tiene permiso de '
                'administración de áreas en PostgreSQL.'
            )
        super().__init__(master, 'Áreas y usuarios')
        self.active_tab = 'areas'
        content = ctk.CTkFrame(self.body, fg_color='transparent')
        content.pack(fill='both', expand=True, padx=30, pady=24)
        label(content, 'Administración de áreas y usuarios', 28, TEXT, True).pack(anchor='w')
        label(content, 'Administra el catálogo de áreas y las cuentas asignadas, conservando el historial.', 14, MUTED).pack(anchor='w', pady=(4, 18))
        self.tabs = ctk.CTkFrame(content, fg_color=WHITE, corner_radius=12, border_width=1, border_color=LINE, height=62)
        self.tabs.pack(fill='x', pady=(0, 16))
        self.btn_areas = button(self.tabs, 'Áreas', command=lambda: self.mostrar('areas'), width=150, border_width=0)
        self.btn_areas.pack(side='left', padx=10, pady=9)
        self.btn_usuarios = button(self.tabs, 'Usuarios', command=lambda: self.mostrar('usuarios'), width=150, border_width=0)
        self.btn_usuarios.pack(side='left', padx=4, pady=9)
        self.panel = ctk.CTkFrame(content, fg_color='transparent')
        self.panel.pack(fill='both', expand=True)
        self.mostrar('areas')

    def mostrar(self, tab):
        self.active_tab = tab
        self.btn_areas.configure(fg_color=PINK if tab == 'areas' else WHITE, text_color=ACCENT if tab == 'areas' else TEXT)
        self.btn_usuarios.configure(fg_color=PINK if tab == 'usuarios' else WHITE, text_color=ACCENT if tab == 'usuarios' else TEXT)
        for child in self.panel.winfo_children():
            child.destroy()
        if tab == 'areas':
            self._panel_areas()
        else:
            self._panel_usuarios()

    def _panel_areas(self):
        form = card(self.panel)
        form.pack(fill='x', pady=(0, 14))
        label(form, 'Agregar área al catálogo', 18, TEXT, True).pack(anchor='w', padx=20, pady=(16, 8))
        fields = ctk.CTkFrame(form, fg_color='transparent')
        fields.pack(fill='x', padx=20, pady=(0, 14))
        self.area_nombre = entry(fields, 'Nombre del área')
        self.area_nombre.pack(side='left', fill='x', expand=True, padx=(0, 8))
        button(fields, 'Guardar área', self._agregar_area, primary=True, width=150).pack(side='left', padx=(8, 0))
        listing = card(self.panel)
        listing.pack(fill='both', expand=True)
        header = ctk.CTkFrame(listing, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(14, 6))
        label(header, 'Áreas activas del catálogo', 18, TEXT, True).pack(side='left')
        button(header, 'Actualizar', self._refrescar_areas, width=110).pack(side='right')
        self.area_list = ctk.CTkScrollableFrame(listing, fg_color='transparent')
        self.area_list.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        self._refrescar_areas()

    def _refrescar_areas(self):
        for child in self.area_list.winfo_children():
            child.destroy()
        try:
            rows = listar_areas()
            for id_area, nombre in rows:
                row = ctk.CTkFrame(self.area_list, fg_color=BG, corner_radius=9)
                row.pack(fill='x', padx=5, pady=4)
                info = ctk.CTkFrame(row, fg_color='transparent')
                info.pack(side='left', fill='x', expand=True, padx=12, pady=9)
                label(info, nombre, 14, TEXT, True).pack(anchor='w')
                button(row, 'Desactivar', lambda value=id_area, title=nombre: self._eliminar_area(value, title), width=100, height=34).pack(side='right', padx=10)
            if not rows:
                label(self.area_list, 'No hay áreas activas en el catálogo.', 13, MUTED).pack(pady=20)
        except (ConnectionError, RuntimeError, ValueError) as error:
            messagebox.showerror('Áreas', str(error), parent=self)

    def _agregar_area(self):
        try:
            agregar_area(self.area_nombre.get())
            self.area_nombre.delete(0, 'end')
            self._refrescar_areas()
            messagebox.showinfo('Áreas', 'El área se guardó correctamente.', parent=self)
        except (ConnectionError, RuntimeError, ValueError) as error:
            messagebox.showerror('No se pudo agregar', str(error), parent=self)

    def _eliminar_area(self, id_area, nombre):
        if not messagebox.askyesno('Desactivar área', f'¿Deseas desactivar «{nombre}»? Se conservarán el área y sus relaciones históricas.', parent=self):
            return
        try:
            eliminar_area(id_area)
            self._refrescar_areas()
        except (ConnectionError, RuntimeError, ValueError) as error:
            messagebox.showerror('No se pudo desactivar', str(error), parent=self)

    def _panel_usuarios(self):
        form = card(self.panel)
        form.pack(fill='x', pady=(0, 14))
        label(form, 'Agregar usuario', 18, TEXT, True).pack(anchor='w', padx=20, pady=(16, 8))
        fields = ctk.CTkFrame(form, fg_color='transparent')
        fields.pack(fill='x', padx=20, pady=(0, 14))
        self.usuario_correo = entry(fields, 'Correo Microsoft')
        self.usuario_correo.pack(side='left', fill='x', expand=True, padx=8)
        try:
            self.areas_disponibles = listar_areas()
            opciones = [f'{id_area} · {nombre}' for id_area, nombre in self.areas_disponibles]
        except (ConnectionError, RuntimeError, ValueError) as error:
            opciones = []
            messagebox.showerror('Áreas', str(error), parent=self)
        self.area_seleccionada = ctk.StringVar(value=opciones[0] if opciones else '')
        self.usuario_area = ctk.CTkOptionMenu(fields, values=opciones or ['Primero registra un área'], variable=self.area_seleccionada, width=210)
        self.usuario_area.pack(side='left', padx=8)
        button(fields, 'Agregar usuario', self._agregar_usuario, primary=True, width=155).pack(side='left', padx=(8, 0))
        listing = card(self.panel)
        listing.pack(fill='both', expand=True)
        header = ctk.CTkFrame(listing, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(14, 6))
        label(header, 'Usuarios registrados', 18, TEXT, True).pack(side='left')
        button(header, 'Actualizar', self._refrescar_usuarios, width=110).pack(side='right')
        self.usuario_list = ctk.CTkScrollableFrame(listing, fg_color='transparent')
        self.usuario_list.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        self._refrescar_usuarios()

    def _refrescar_usuarios(self):
        for child in self.usuario_list.winfo_children():
            child.destroy()
        try:
            rows = listar_empleados()
            for id_empleado, correo, areas in rows:
                row = ctk.CTkFrame(self.usuario_list, fg_color=BG, corner_radius=9)
                row.pack(fill='x', padx=5, pady=4)
                info = ctk.CTkFrame(row, fg_color='transparent')
                info.pack(side='left', fill='x', expand=True, padx=12, pady=9)
                label(info, correo, 14, TEXT, True).pack(anchor='w')
                label(info, areas, 11, MUTED).pack(anchor='w')
                button(row, 'Desactivar', lambda value=id_empleado, title=correo: self._eliminar_usuario(value, title), width=100, height=34).pack(side='right', padx=10)
            if not rows:
                label(self.usuario_list, 'No hay usuarios registrados.', 13, MUTED).pack(pady=20)
        except (ConnectionError, RuntimeError, ValueError) as error:
            messagebox.showerror('Usuarios', str(error), parent=self)

    def _agregar_usuario(self):
        try:
            if not self.areas_disponibles:
                raise ValueError('Primero debes registrar un área.')
            id_area = int(self.area_seleccionada.get().split(' · ', 1)[0])
            agregar_empleado(self.usuario_correo.get(), id_area)
            self.usuario_correo.delete(0, 'end')
            self._refrescar_usuarios()
            messagebox.showinfo('Usuarios', 'El usuario se agregó o reactivó correctamente.', parent=self)
        except (ConnectionError, RuntimeError, ValueError) as error:
            messagebox.showerror('No se pudo agregar', str(error), parent=self)

    def _eliminar_usuario(self, id_empleado, nombre):
        if not messagebox.askyesno('Desactivar usuario', f'¿Deseas desactivar a «{nombre}»? Se conservarán su registro y sus asignaciones históricas.', parent=self):
            return
        try:
            eliminar_empleado(id_empleado)
            self._refrescar_usuarios()
        except (ConnectionError, RuntimeError, ValueError) as error:
            messagebox.showerror('No se pudo desactivar', str(error), parent=self)
