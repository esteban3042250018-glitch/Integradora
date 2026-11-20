"""Administración del membrete institucional y los folios."""
from datetime import date
from io import BytesIO
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from model.administracion import (
    cambiar_imagen_membrete,
    consultar_siguiente_folio,
    desactivar_membrete,
    guardar_configuracion_folio,
    obtener_configuracion_folio,
    obtener_membrete_activo,
    reiniciar_folios,
)
from model.folio_format import (
    DEFAULT_DIGITS,
    DEFAULT_FONT,
    DEFAULT_FONT_SIZE,
    DEFAULT_TEMPLATE,
    build_configuration,
    editor_segments_from_configuration,
    render_folio,
    template_from_editor_segments,
)
from views.ui_helpers import (
    ACCENT,
    BG,
    MUTED,
    TEXT,
    WHITE,
    Shell,
    button,
    card,
    entry,
    font,
    label,
)


FONT_OPTIONS = [
    'Arial', 'Calibri', 'Helvetica', 'Times New Roman', 'Courier New',
]


class DashboardApp(Shell):
    def __init__(self, master):
        super().__init__(master, 'Configuración')
        self._imagen_preview = None
        self.active_section = 'membrete'
        content = ctk.CTkFrame(self.body, fg_color='transparent')
        content.pack(fill='both', expand=True, padx=30, pady=24)
        heading = ctk.CTkFrame(content, fg_color='transparent')
        heading.pack(fill='x', pady=(0, 18))
        titles = ctk.CTkFrame(heading, fg_color='transparent')
        titles.pack(side='left')
        label(titles, 'Administración institucional', 30, TEXT, True).pack(
            anchor='w')
        label(
            titles,
            'Gestiona la identidad visual y el formato de los folios.',
            15,
            MUTED,
        ).pack(anchor='w', pady=(4, 0))

        self.folio_segments = [
            {'tipo': 'texto', 'valor': 'IPN/CVDRD/'},
            {'tipo': 'numero', 'valor': ''},
            {'tipo': 'texto', 'valor': '/'},
            {'tipo': 'anio', 'valor': ''},
        ]
        self.admin_nav = ctk.CTkFrame(
            content, fg_color=WHITE, corner_radius=12,
            border_width=1, border_color='#E5E7EB', height=66)
        self.admin_nav.pack(fill='x', pady=(0, 18))
        self.admin_nav.pack_propagate(False)
        self.admin_buttons = {}
        for key, title in (
            ('membrete', 'Admin 1  ·  Imagen institucional'),
            ('folios', 'Admin 2  ·  Estructura de folio'),
        ):
            control = button(
                self.admin_nav, title,
                command=lambda section=key: self.mostrar_seccion(section),
                width=285 if key == 'membrete' else 280,
                height=46, border_width=0,
                fg_color='#FCE7F3' if key == self.active_section else WHITE,
                text_color=ACCENT if key == self.active_section else TEXT,
                hover_color='#FCE7F3',
                font=font(14, key == self.active_section),
            )
            control.pack(side='left', padx=(10, 4), pady=9)
            self.admin_buttons[key] = control
        self.admin_content = ctk.CTkFrame(
            content, fg_color='transparent')
        self.admin_content.pack(fill='both', expand=True)
        self.mostrar_seccion(self.active_section)

    def mostrar_seccion(self, section):
        self.active_section = section
        for key, control in self.admin_buttons.items():
            selected = key == section
            control.configure(
                fg_color='#FCE7F3' if selected else WHITE,
                text_color=ACCENT if selected else TEXT,
                font=font(14, selected),
            )
        for child in self.admin_content.winfo_children():
            child.destroy()
        if section == 'folios':
            self._crear_panel_folio(self.admin_content)
            self.cargar_configuracion()
        else:
            self._crear_panel_membrete(self.admin_content)
            self.cargar_membrete()

    def _crear_panel_folio(self, parent):
        panel = card(parent)
        panel.pack(fill='both', expand=True, pady=(0, 18))
        label(panel, 'Estructura y consecutivo de folio', 22, TEXT, True).pack(
            anchor='w', padx=28, pady=(26, 6))
        label(
            panel,
            'Edita cada cuadro para cambiar separadores; en Número y Año '
            'puedes escribir el texto que va después. Usa las flechas para '
            'reordenar los cuadros.',
            14,
            MUTED,
        ).pack(anchor='w', padx=28, pady=(0, 20))

        grid = ctk.CTkFrame(panel, fg_color='transparent')
        grid.pack(fill='x', padx=28)
        grid.grid_columnconfigure(0, weight=3)
        grid.grid_columnconfigure((1, 2, 3), weight=1)

        grid.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform='folio-fields')
        self.digits_entry = self._form_field(
            grid, 'Dígitos del consecutivo', row=0, column=0,
            placeholder=str(DEFAULT_DIGITS))
        self.digits_entry.bind(
            '<KeyRelease>', lambda _event: self.actualizar_vista_previa())

        font_field = ctk.CTkFrame(grid, fg_color='transparent')
        font_field.grid(row=0, column=1, sticky='ew', padx=(8, 8))
        label(font_field, 'Fuente', 11, TEXT, True).pack(anchor='w', pady=(0, 4))
        self.font_selector = ctk.CTkComboBox(
            font_field,
            values=FONT_OPTIONS,
            height=40,
            corner_radius=8,
            fg_color=WHITE,
            border_color='#DEDCE2',
            text_color=TEXT,
            font=font(12),
            command=lambda _value: self.actualizar_vista_previa(),
        )
        self.font_selector.pack(fill='x')
        self.font_selector.set(DEFAULT_FONT)

        self.size_entry = self._form_field(
            grid, 'Tamaño de fuente (pt)', row=0, column=2,
            placeholder=str(DEFAULT_FONT_SIZE))
        self.size_entry.bind(
            '<KeyRelease>', lambda _event: self.actualizar_vista_previa())
        self.year_entry = self._form_field(
            grid, 'Año (vacío = año actual)', row=1, column=0,
            placeholder='Automático')
        self.year_entry.bind(
            '<KeyRelease>', lambda _event: self.actualizar_vista_previa())

        self.format_preview = label(
            grid, f'Vista previa: {DEFAULT_TEMPLATE.replace("{numero}", "001").replace("{ano}", str(date.today().year))}',
            12, ACCENT, True)
        self.format_preview.grid(
            row=1, column=1, columnspan=3, sticky='w', padx=(12, 0))

        segments_heading = ctk.CTkFrame(panel, fg_color='transparent')
        segments_heading.pack(fill='x', padx=22, pady=(18, 8))
        label(segments_heading, 'Estructura del folio', 16, TEXT, True).pack(
            side='left')
        button(
            segments_heading,
            '+ Cuadro de texto',
            lambda: self.agregar_segmento('texto'),
            width=164,
            height=40,
        ).pack(side='right', padx=(8, 0))
        button(
            segments_heading,
            '+ Número',
            lambda: self.agregar_segmento('numero'),
            width=132,
            height=40,
        ).pack(side='right', padx=(8, 0))
        button(
            segments_heading,
            '+ Año',
            lambda: self.agregar_segmento('anio'),
            width=110,
            height=40,
        ).pack(side='right')
        self.segments_frame = ctk.CTkFrame(panel, fg_color='transparent')
        self.segments_frame.pack(fill='x', padx=28)
        self.render_segments()

        actions = ctk.CTkFrame(panel, fg_color='transparent')
        actions.pack(fill='x', padx=28, pady=(24, 28))
        button(
            actions,
            'Guardar formato',
            self.guardar_formato,
            primary=True,
            width=160,
        ).pack(side='left')
        button(
            actions,
            'Consultar siguiente folio',
            self.actualizar_siguiente,
            width=205,
        ).pack(side='left', padx=(10, 0))
        button(
            actions,
            'Reiniciar consecutivo',
            self.confirmar_reinicio,
            width=185,
        ).pack(side='left', padx=(10, 0))
        self.next_folio_label = label(
            actions, 'Siguiente folio: —', 15, ACCENT, True)
        self.next_folio_label.pack(side='right', padx=(12, 0))

    def _form_field(self, parent, title, *, row, column, placeholder):
        field = ctk.CTkFrame(parent, fg_color='transparent')
        field.grid(row=row, column=column, sticky='ew', padx=(0, 8))
        label(field, title, 11, TEXT, True).pack(anchor='w', pady=(0, 4))
        control = entry(field, placeholder)
        control.pack(fill='x')
        return control

    def render_segments(self):
        for child in self.segments_frame.winfo_children():
            child.destroy()

        for index, segment in enumerate(self.folio_segments):
            tile = card(self.segments_frame, width=220, height=142)
            tile.grid(
                row=index // 4,
                column=index % 4,
                sticky='nsew',
                padx=(0, 10),
                pady=(0, 10),
            )
            tile.grid_propagate(False)
            tile.grid_columnconfigure(0, weight=1)
            header = ctk.CTkFrame(tile, fg_color='transparent')
            header.grid(row=0, column=0, sticky='ew', padx=14, pady=(12, 6))
            label(header, f'Cuadro {index + 1}', 13, TEXT, True).pack(side='left')
            button(
                header,
                '×',
                lambda position=index: self.eliminar_segmento(position),
                width=32,
                height=30,
                border_width=0,
                text_color=MUTED,
            ).pack(side='right')
            move_up = button(
                header,
                '↑',
                lambda position=index: self.mover_segmento(position, -1),
                width=28,
                height=30,
                border_width=0,
                text_color=MUTED,
            )
            move_up.pack(side='right')
            if index == 0:
                move_up.configure(state='disabled')
            move_down = button(
                header,
                '↓',
                lambda position=index: self.mover_segmento(position, 1),
                width=28,
                height=30,
                border_width=0,
                text_color=MUTED,
            )
            move_down.pack(side='right')
            if index == len(self.folio_segments) - 1:
                move_down.configure(state='disabled')

            selector = ctk.CTkComboBox(
                tile,
                values=['Texto', 'Número', 'Año'],
                height=38,
                corner_radius=7,
                fg_color=WHITE,
                border_color='#DEDCE2',
                text_color=TEXT,
                font=font(11),
                command=lambda value, position=index: self.cambiar_tipo_segmento(
                    position, value),
            )
            selector.grid(row=1, column=0, sticky='ew', padx=14, pady=(0, 6))
            selector.set({
                'texto': 'Texto',
                'numero': 'Número',
                'anio': 'Año',
            }[segment['tipo']])
            value_entry = entry(
                tile,
                {
                    'texto': 'Contenido del cuadro',
                    'numero': 'Texto después del consecutivo',
                    'anio': 'Texto después del año',
                }[segment['tipo']],
                height=38,
            )
            value_entry.grid(row=2, column=0, sticky='ew', padx=14, pady=(0, 12))
            value_entry.insert(0, segment['valor'])
            value_entry.bind(
                '<KeyRelease>',
                lambda _event, position=index, control=value_entry:
                    self.actualizar_texto_segmento(position, control.get()),
            )

        for column in range(4):
            self.segments_frame.grid_columnconfigure(column, weight=1)
        self.actualizar_vista_previa()

    def agregar_segmento(self, kind):
        if kind == 'numero' and any(
            segment['tipo'] == 'numero' for segment in self.folio_segments
        ):
            messagebox.showwarning(
                'Estructura del folio',
                'Solo se permite un cuadro numérico.',
                parent=self,
            )
            return
        if kind == 'anio' and any(
            segment['tipo'] == 'anio' for segment in self.folio_segments
        ):
            messagebox.showwarning(
                'Estructura del folio',
                'Solo se permite un cuadro de año.',
                parent=self,
            )
            return
        self.folio_segments.append({
            'tipo': kind,
            'valor': 'TEXTO' if kind == 'texto' else '',
        })
        self.render_segments()

    def cambiar_tipo_segmento(self, index, value):
        kind = {'Texto': 'texto', 'Número': 'numero', 'Año': 'anio'}[value]
        if kind in {'numero', 'anio'} and any(
            segment['tipo'] == kind and position != index
            for position, segment in enumerate(self.folio_segments)
        ):
            messagebox.showwarning(
                'Estructura del folio',
                'Solo se permite un cuadro numérico y un cuadro de año.',
                parent=self,
            )
            self.render_segments()
            return
        self.folio_segments[index] = {
            'tipo': kind,
            'valor': self.folio_segments[index]['valor'] if kind == 'texto'
            and self.folio_segments[index]['tipo'] == 'texto' else (
                'TEXTO' if kind == 'texto' else ''),
        }
        self.render_segments()

    def actualizar_texto_segmento(self, index, value):
        self.folio_segments[index]['valor'] = value
        self.actualizar_vista_previa()

    def mover_segmento(self, index, direction):
        destination = index + direction
        if not 0 <= destination < len(self.folio_segments):
            return
        self.folio_segments[index], self.folio_segments[destination] = (
            self.folio_segments[destination],
            self.folio_segments[index],
        )
        self.render_segments()

    def eliminar_segmento(self, index):
        self.folio_segments.pop(index)
        self.render_segments()

    def obtener_plantilla(self):
        return template_from_editor_segments(self.folio_segments)

    def actualizar_vista_previa(self):
        try:
            configuration = build_configuration(
                self.obtener_plantilla(),
                self.digits_entry.get() or DEFAULT_DIGITS,
                self.font_selector.get() or DEFAULT_FONT,
                self.size_entry.get() or DEFAULT_FONT_SIZE,
                self.year_entry.get(),
            )
            preview = render_folio(1, configuration)
            self.format_preview.configure(text=f'Vista previa: {preview}')
        except ValueError:
            self.format_preview.configure(
                text='Vista previa: completa los cuadros del folio')

    def _crear_panel_membrete(self, parent):
        panel = card(parent)
        panel.pack(fill='both', expand=True)
        label(panel, 'Identidad institucional · Membrete', 22, TEXT, True).pack(
            anchor='w', padx=28, pady=(26, 6))
        label(
            panel,
            'El membrete activo se utilizará en los próximos documentos.',
            14, MUTED,
        ).pack(anchor='w', padx=28, pady=(0, 20))
        body = ctk.CTkFrame(panel, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=28, pady=(0, 28))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        self.preview = ctk.CTkLabel(
            body, text='Cargando membrete…', fg_color=BG,
            corner_radius=12, height=300, text_color=MUTED,
            font=font(15),
        )
        self.preview.grid(row=0, column=0, rowspan=4, sticky='nsew',
                          padx=(0, 24))
        details = ctk.CTkFrame(body, fg_color='transparent')
        details.grid(row=0, column=1, sticky='new', pady=(10, 0))
        label(details, 'Membrete actual', 16, TEXT, True).pack(anchor='w')
        self.details = label(details, 'Consultando el membrete activo…', 14, MUTED)
        self.details.pack(anchor='w', pady=(8, 12))
        self.status = label(details, '', 13, MUTED, wraplength=480,
                            justify='left', anchor='w')
        self.status.pack(anchor='w', pady=(0, 20))

        actions = ctk.CTkFrame(body, fg_color='transparent')
        actions.grid(row=1, column=1, sticky='w')
        button(
            actions, '↑  Seleccionar nuevo membrete',
            self.seleccionar_membrete, primary=True,
            width=270, height=46,
        ).pack(anchor='w', pady=(0, 12))
        button(
            actions, 'Actualizar vista', self.cargar_membrete,
            width=190, height=44,
        ).pack(anchor='w', pady=(0, 12))
        button(
            actions, 'Desactivar membrete',
            self.confirmar_desactivacion, width=200, height=44,
        ).pack(anchor='w')

    def on_show(self):
        if self.active_section == 'folios':
            self.cargar_configuracion()
        else:
            self.cargar_membrete()

    def cargar_configuracion(self):
        try:
            configuration = obtener_configuracion_folio()
            self.folio_segments = editor_segments_from_configuration(
                configuration)
            self.render_segments()
            self.digits_entry.delete(0, 'end')
            self.digits_entry.insert(0, str(configuration['digitos']))
            self.font_selector.set(configuration['fuente'])
            self.size_entry.delete(0, 'end')
            self.size_entry.insert(0, str(configuration['tamano']))
            self.year_entry.delete(0, 'end')
            if configuration['anio_folio'] is not None:
                self.year_entry.insert(0, str(configuration['anio_folio']))
            self.actualizar_siguiente()
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror(
                'Configuración de folios',
                f'No se pudo cargar la configuración de folios.\n{error}',
                parent=self,
            )

    def guardar_formato(self):
        try:
            guardar_configuracion_folio(
                self.obtener_plantilla(),
                self.digits_entry.get(),
                self.font_selector.get(),
                self.size_entry.get(),
                self.year_entry.get(),
            )
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror(
                'Guardar formato',
                f'No se pudo guardar el formato de folio.\n{error}',
                parent=self,
            )
            return

        self.actualizar_siguiente()
        messagebox.showinfo(
            'Guardar formato',
            'El formato quedó guardado. Los oficios ya generados no se '
            'modificaron.',
            parent=self,
        )

    def actualizar_siguiente(self):
        try:
            folio = consultar_siguiente_folio()
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            self.next_folio_label.configure(
                text='No disponible', text_color=ACCENT)
            messagebox.showerror(
                'Consultar folio',
                f'No se pudo consultar el siguiente folio.\n{error}',
                parent=self,
            )
            return
        self.next_folio_label.configure(
            text=f'Siguiente folio: {folio}', text_color=ACCENT)

    def confirmar_reinicio(self):
        if not messagebox.askyesno(
            'Reiniciar consecutivo',
            'Se registrará un nuevo contador desde 1. No se borrarán '
            'oficios ni el historial; la aplicación omitirá folios que ya '
            'existan para evitar duplicados.\n\n¿Continuar?',
            parent=self,
        ):
            return
        try:
            reiniciar_folios()
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror(
                'Reiniciar consecutivo',
                f'No se pudo reiniciar el contador.\n{error}',
                parent=self,
            )
            return
        self.actualizar_siguiente()
        messagebox.showinfo(
            'Reiniciar consecutivo',
            'Se registró el reinicio. Los folios existentes se conservaron.',
            parent=self,
        )

    def cargar_membrete(self):
        try:
            id_membrete, nombre, tipo_mime, contenido, actualizado = (
                obtener_membrete_activo()
            )
            with Image.open(BytesIO(contenido)) as image:
                preview = image.convert('RGBA')
            preview.thumbnail((1100, 420))
            self._imagen_preview = ctk.CTkImage(
                light_image=preview,
                dark_image=preview,
                size=preview.size,
            )
            self.preview.configure(image=self._imagen_preview, text='')
            self.details.configure(
                text=f'{nombre} · {tipo_mime} · ID {id_membrete}'
            )
            fecha = (
                actualizado.strftime('%d/%m/%Y %H:%M')
                if actualizado else 'No disponible'
            )
            self.status.configure(text=f'Última actualización: {fecha}')
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            self._imagen_preview = None
            self.preview.configure(
                image=None, text='No hay un membrete activo.')
            self.details.configure(text='')
            self.status.configure(text=str(error))

    def seleccionar_membrete(self):
        ruta = filedialog.askopenfilename(
            parent=self,
            title='Seleccionar membrete institucional',
            filetypes=[
                ('Imágenes', '*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp'),
                ('Todos los archivos', '*.*'),
            ],
        )
        if not ruta:
            return

        if not messagebox.askyesno(
            'Cambiar membrete',
            'El nuevo membrete se usará en los próximos documentos. '
            'El anterior se conservará como inactivo.\n\n¿Continuar?',
            parent=self,
        ):
            return

        try:
            cambiar_imagen_membrete(ruta)
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror(
                'Cambiar membrete',
                f'No se pudo actualizar el membrete.\n{error}',
                parent=self,
            )
            return

        self.cargar_membrete()
        messagebox.showinfo(
            'Cambiar membrete',
            'El membrete se actualizó correctamente y se aplicará a los '
            'próximos documentos.',
            parent=self,
        )

    def confirmar_desactivacion(self):
        if not messagebox.askyesno(
            'Desactivar membrete',
            'Sin un membrete activo no se podrán generar nuevos documentos. '
            '¿Deseas desactivarlo?',
            parent=self,
        ):
            return
        try:
            desactivados = desactivar_membrete()
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror(
                'Desactivar membrete',
                f'No se pudo desactivar el membrete.\n{error}',
                parent=self,
            )
            return
        self.cargar_membrete()
        messagebox.showinfo(
            'Desactivar membrete',
            f'Membretes desactivados: {desactivados}.',
            parent=self,
        )
