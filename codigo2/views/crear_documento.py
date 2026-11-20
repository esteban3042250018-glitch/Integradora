"""Captura de oficio y sincronización con Microsoft Word de escritorio."""

from tkinter import messagebox
import sys
import html
from pathlib import Path
import customtkinter as ctk
from controller.word_controller import (
    crear_o_abrir_word, firma_documento_word, leer_texto_word,
)

from views.ui_helpers import (
    Shell, ACCENT, BG, WHITE, LINE, MUTED, TEXT, SOFT, PINK,
    label, card, button, entry, font, open_screen,
)
from model.document_store import guardar_documento


AREAS_EMISORAS = [
    'Dirección General',
    'Dirección Administrativa',
    'Coordinación Jurídica',
    'Secretaría de Finanzas',
    'Subdirección de Planeación',
    'Unidad de Recursos Materiales',
    'Enlace de Vinculación',
]

class CrearDocumentoApp(Shell):
    def __init__(self, master, folio):
        super().__init__(master, 'Crear documento')
        self.folio = folio
        self.cuerpo_html = ''
        self.word_path = None
        self.word_opened = False
        self.word_synced = False
        self.word_signature = None
        self.title('Gestión Institucional - Crear documento')

        content = ctk.CTkFrame(self.body, fg_color='transparent')
        content.pack(fill='x', padx=22, pady=20)

        encabezado = ctk.CTkFrame(content, fg_color='transparent')
        encabezado.pack(fill='x', pady=(0, 18))
        titulo = ctk.CTkFrame(encabezado, fg_color='transparent')
        titulo.pack(side='left')
        label(titulo, 'Crear documento', 28).pack(anchor='w')
        label(titulo, f'Folio reservado: {self.folio}', 14, ACCENT, True).pack(anchor='w')
        button(encabezado, '←  Volver a correspondencia',
               lambda: open_screen(self, 'folio_reservado.py', self.folio), width=216).pack(side='right', pady=8)

        formulario = card(content)
        formulario.pack(fill='x', pady=(0, 18))

        intro = ctk.CTkFrame(formulario, fg_color='transparent')
        intro.pack(fill='x', padx=28, pady=(25, 12))
        label(intro, 'Información del documento', 19, TEXT, True).pack(anchor='w')
        label(intro, 'Captura los datos y elige el método de redacción para el oficio.', 12, MUTED).pack(anchor='w', pady=(4, 0))

        separador = ctk.CTkFrame(formulario, height=1, corner_radius=0, fg_color=LINE)
        separador.pack(fill='x', padx=28, pady=(4, 18))

        campos = ctk.CTkFrame(formulario, fg_color='transparent')
        campos.pack(fill='x', padx=28)
        campos.grid_columnconfigure((0, 1), weight=1, uniform='fields')

        # 1. Asunto
        label(campos, 'Asunto', 12, TEXT, True).grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))
        self.asunto = entry(campos, 'Escribe el asunto del documento', height=44)
        self.asunto.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 24))

        # 2. Área emisora
        label(campos, 'Área emisora', 12, TEXT, True).grid(
            row=2, column=0, sticky='w', pady=(0, 6), padx=(0, 12))
        self.area_emisora = ctk.CTkComboBox(
            campos, values=AREAS_EMISORAS, height=44,
            corner_radius=8, border_width=1, border_color=LINE,
            fg_color=WHITE, button_color=WHITE, button_hover_color=SOFT,
            text_color=TEXT, font=font(12),
            dropdown_fg_color=WHITE, dropdown_text_color=TEXT,
            dropdown_hover_color=PINK,
        )
        self.area_emisora.grid(row=3, column=0, sticky='ew', padx=(0, 12), pady=(0, 24))
        self.area_emisora.set('Selecciona un área')

        # 3. Recepción
        label(campos, 'Recepción', 12, TEXT, True).grid(
            row=2, column=1, sticky='w', pady=(0, 6), padx=(12, 0))
        self.recepcion = entry(campos, 'Escribe los datos de recepción', height=44)
        self.recepcion.grid(row=3, column=1, sticky='ew', padx=(12, 0), pady=(0, 24))

        seccion_word = ctk.CTkFrame(campos, fg_color=SOFT, corner_radius=10)
        seccion_word.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(10, 12))
        info_word = ctk.CTkFrame(seccion_word, fg_color='transparent')
        info_word.pack(side='left', padx=18, pady=14)
        label(info_word, 'Microsoft Word de escritorio', 13, TEXT, True).pack(anchor='w')
        self.lbl_estado_word = label(info_word, 'El documento se guardará en este equipo.', 11, MUTED)
        self.lbl_estado_word.pack(anchor='w')
        button(seccion_word, 'Abrir en Word', self.abrir_en_word, primary=True,
               width=180, height=42).pack(side='right', padx=15, pady=14)

        seccion_sync = ctk.CTkFrame(campos, fg_color=SOFT, corner_radius=10)
        seccion_sync.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(0, 24))
        info_sync = ctk.CTkFrame(seccion_sync, fg_color='transparent')
        info_sync.pack(side='left', padx=18, pady=14)
        label(info_sync, 'Sincronizar cambios', 13, TEXT, True).pack(anchor='w')
        self.lbl_estado_sync = label(
            info_sync, 'Guarda el archivo en Word y sincronízalo aquí.', 11, MUTED)
        self.lbl_estado_sync.pack(anchor='w')
        button(seccion_sync, 'Sincronizar cambios', self.sincronizar_desde_word,
               width=190, height=42).pack(side='right', padx=15, pady=14)

        # Barra inferior de acciones
        barra = ctk.CTkFrame(formulario, fg_color=SOFT, corner_radius=10)
        barra.pack(fill='x', padx=28, pady=(2, 24))
        label(barra, 'Todos los campos son obligatorios.', 11, MUTED).pack(
            side='left', padx=18, pady=14)
        button(barra, 'Limpiar', self.limpiar, width=112, height=38).pack(
            side='right', padx=(0, 15), pady=10)
        button(barra, '▣  Guardar documento', self.guardar, primary=True,
               width=204, height=38).pack(side='right', padx=10, pady=10)

        self.estado = label(content, '', 12, ACCENT)
        self.estado.pack(anchor='w', padx=8)
        self.asunto.focus_set()

    def abrir_en_word(self):
        asunto = self.asunto.get().strip()
        if not asunto:
            messagebox.showwarning('Aviso', 'Primero ingresa el asunto del oficio.', parent=self)
            return

        try:
            self.word_path = crear_o_abrir_word(self.folio, asunto)
        except (OSError, ValueError) as error:
            messagebox.showerror('Microsoft Word', str(error), parent=self)
            return
        self.word_opened = True
        self.word_synced = False
        self.lbl_estado_word.configure(text=f'Abierto en Word: {self.word_path}', text_color=GREEN)
        self.lbl_estado_sync.configure(
            text='Guarda los cambios en Word antes de sincronizar.', text_color=MUTED)

    def sincronizar_desde_word(self):
        if not self.word_opened or self.word_path is None:
            messagebox.showwarning(
                'Aviso', 'Primero abre el documento en Word desde la aplicación.', parent=self)
            return
        try:
            firma_inicial = firma_documento_word(self.word_path)
            texto = leer_texto_word(self.word_path)
            firma = firma_documento_word(self.word_path)
        except (OSError, ValueError) as error:
            messagebox.showerror('Error de sincronización', str(error), parent=self)
            return
        if firma_inicial != firma:
            messagebox.showwarning(
                'Documento en uso',
                'El archivo cambió durante la lectura. Espera a que Word termine de guardar y vuelve a sincronizar.',
                parent=self,
            )
            return

        if not texto.strip():
            messagebox.showwarning(
                'Aviso',
                'El documento de Word todavía no tiene texto. Guarda tus cambios y vuelve a sincronizar.',
                parent=self)
            return

        self.cuerpo_html = "<p>" + html.escape(texto).replace("\n", "<br>") + "</p>"
        self.word_synced = True
        self.word_signature = firma
        self.lbl_estado_sync.configure(
            text='✓ Cambios de Word sincronizados con la aplicación.', text_color=GREEN)
        messagebox.showinfo(
            'Sincronización exitosa',
            'Los cambios guardados en Word ya están listos para guardarse en el oficio.',
            parent=self,
        )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def navigate(self, name):
        if name == 'Crear documento':
            self.asunto.focus_set()
        else:
            super().navigate(name)

    def limpiar(self):
        self.asunto.delete(0, 'end')
        self.area_emisora.set('Selecciona un área')
        self.recepcion.delete(0, 'end')
        self.cuerpo_html = ''
        self.word_path = None
        self.word_opened = False
        self.word_synced = False
        self.word_signature = None
        self.lbl_estado_word.configure(text='El documento se guardará en este equipo.', text_color=MUTED)
        self.lbl_estado_sync.configure(
            text='Guarda el archivo en Word y sincronízalo aquí.', text_color=MUTED)
        self.estado.configure(text='')
        self.asunto.focus_set()

    def guardar(self):
        asunto = self.asunto.get().strip()
        area = self.area_emisora.get().strip()
        recepcion = self.recepcion.get().strip()
        cuerpo = (self.cuerpo_html or '').strip()

        if not asunto:
            return self.advertir('Completa el campo Asunto.', self.asunto)
        if not area or area == 'Selecciona un área':
            return self.advertir('Selecciona un Área emisora.', self.area_emisora)
        if not recepcion:
            return self.advertir('Completa el campo Recepción.', self.recepcion)

        sin_contenido = not cuerpo or cuerpo in ('<p></p>', '<p><br></p>')

        if self.word_opened and not self.word_synced:
            messagebox.showwarning(
                'Crear documento',
                'Abre y guarda los cambios en Word, luego presiona "Sincronizar cambios" antes de guardar.',
                parent=self)
            return
        if self.word_synced and self.word_path is not None:
            try:
                archivo_cambio = firma_documento_word(self.word_path) != self.word_signature
            except OSError as error:
                messagebox.showerror('Sincronizar cambios', str(error), parent=self)
                return
            if archivo_cambio:
                messagebox.showwarning(
                    'Cambios pendientes',
                    'El archivo cambió después de la última sincronización. '
                    'Vuelve a sincronizar antes de guardar.',
                    parent=self,
                )
                return

        if sin_contenido:
            cuerpo = "<p>Documento oficial emitido sin observaciones adicionales.</p>"

        try:
            registro = guardar_documento(asunto, area, recepcion, cuerpo, folio=self.folio)
        except (OSError, ValueError) as error:
            messagebox.showerror('Guardar documento', str(error), parent=self)
            return

        self.estado.configure(text=f"Documento {registro['folio']} guardado localmente.")
        messagebox.showinfo('Documento guardado',
                            f"Se registró {registro['folio']} correctamente.\n"
                            'Ya puedes generar tu PDF institucional.', parent=self)
        open_screen(self, 'folio_reservado.py', self.folio)

    def advertir(self, mensaje, control):
        messagebox.showwarning('Crear documento', mensaje, parent=self)
        control.focus_set()
