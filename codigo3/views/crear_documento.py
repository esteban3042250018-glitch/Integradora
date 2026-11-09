"""Captura de oficio y sincronización con Microsoft Word de escritorio."""

from tkinter import messagebox
import html
import customtkinter as ctk
from controller.word_controller import (
    crear_o_abrir_word, firma_documento_word, leer_texto_word,
)
from controller.database_conecction import Database_connection
from controller.word_online_controller import (
    abrir_word_online, descargar_cambios_word_online,
)

from views.ui_helpers import (
    Shell, ACCENT, BG, WHITE, LINE, MUTED, TEXT, SOFT, PINK, GREEN,
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
        self.word_mode = None
        self.word_synced = False
        self.word_signature = None
        self._autosave_job = None
        self._draft_needs_retry = False
        self._primera_muestra = True
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
        label(
            intro, 'Redacta el oficio en Word de escritorio o Word Online.',
            12, MUTED,
        ).pack(anchor='w', pady=(4, 0))

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
            command=self._programar_autoguardado,
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
        label(info_word, 'Microsoft Word', 13, TEXT, True).pack(anchor='w')
        self.lbl_estado_word = label(
            info_word, 'Elige escritorio o Word Online.', 11, MUTED)
        self.lbl_estado_word.pack(anchor='w')
        botones_word = ctk.CTkFrame(seccion_word, fg_color='transparent')
        botones_word.pack(side='right', padx=15, pady=14)
        button(
            botones_word, 'Word de escritorio', self.abrir_en_word,
            primary=True, width=170, height=42,
        ).pack(side='left', padx=(0, 8))
        button(
            botones_word, 'Word Online', self.abrir_word_online,
            width=145, height=42,
        ).pack(side='left')

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
        self._cargar_borrador()
        self.asunto.bind('<KeyRelease>', self._programar_autoguardado)
        self.recepcion.bind('<KeyRelease>', self._programar_autoguardado)
        self.area_emisora.bind('<KeyRelease>', self._programar_autoguardado)
        self.asunto.focus_set()

    def _cargar_borrador(self):
        if not self.usuario_id:
            raise RuntimeError(
                'No se encontró el identificador de tu cuenta de Microsoft. '
                'Vuelve a iniciar sesión.'
            )
        borrador = Database_connection().obtener_borrador(
            self.folio, self.usuario_id)
        if borrador is None:
            raise ValueError(
                'No se encontró un borrador de este folio para tu cuenta.'
            )
        self.asunto.delete(0, 'end')
        self.asunto.insert(0, borrador['asunto'])
        self.area_emisora.set(
            borrador['area_emisora'] or 'Selecciona un área')
        self.recepcion.delete(0, 'end')
        self.recepcion.insert(0, borrador['recepcion'])
        self.cuerpo_html = borrador['cuerpo']
        if borrador['asunto'] or borrador['recepcion'] or borrador['cuerpo']:
            self.estado.configure(
                text='Borrador recuperado. Se guardará automáticamente mientras editas.',
                text_color=GREEN,
            )

    def _programar_autoguardado(self, _event=None):
        self._draft_needs_retry = True
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(800, self._autoguardar_borrador)

    def _autoguardar_borrador(self):
        self._autosave_job = None
        try:
            Database_connection().guardar_borrador(
                self.folio,
                self.usuario_id,
                self.asunto.get().strip(),
                self.area_emisora.get().strip()
                if self.area_emisora.get() != 'Selecciona un área' else '',
                self.recepcion.get().strip(),
                self.cuerpo_html,
            )
        except (ConnectionError, RuntimeError, ValueError) as error:
            self.estado.configure(
                text=f'No se pudo guardar el borrador: {error}',
                text_color=PINK,
            )
            self._draft_needs_retry = True
            return False
        self._draft_needs_retry = False
        self.estado.configure(
            text='Borrador guardado automáticamente.', text_color=GREEN)
        return True

    def guardar_borrador_pendiente(self):
        if self._autosave_job is None and not self._draft_needs_retry:
            return True
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
            self._autosave_job = None
        return self._autoguardar_borrador()

    def on_show(self):
        if self._primera_muestra:
            self._primera_muestra = False
            return
        self.guardar_borrador_pendiente()

    def abrir_en_word(self):
        if self.word_opened and self.word_mode != 'desktop' and not self.word_synced:
            messagebox.showwarning(
                'Cambios pendientes',
                'Sincroniza primero los cambios del editor actual antes de '
                'cambiar a Word de escritorio.',
                parent=self,
            )
            return
        asunto = self.asunto.get().strip()
        if not asunto:
            messagebox.showwarning('Aviso', 'Primero ingresa el asunto del oficio.', parent=self)
            return
        if not self.guardar_borrador_pendiente():
            messagebox.showerror(
                'Borrador',
                'No se pudo respaldar el borrador en PostgreSQL. '
                'Revisa la conexión antes de continuar.',
                parent=self,
            )
            return

        try:
            self.word_path = crear_o_abrir_word(
                self.folio, asunto, self.cuerpo_html)
        except (OSError, RuntimeError, ValueError) as error:
            messagebox.showerror('Microsoft Word', str(error), parent=self)
            return
        self.word_opened = True
        self.word_mode = 'desktop'
        self.word_synced = False
        self.lbl_estado_word.configure(text=f'Abierto en Word: {self.word_path}', text_color=GREEN)
        self.lbl_estado_sync.configure(
            text='Guarda los cambios en Word antes de sincronizar.', text_color=MUTED)

    def abrir_word_online(self):
        if self.word_opened and self.word_mode != 'online' and not self.word_synced:
            messagebox.showwarning(
                'Cambios pendientes',
                'Sincroniza primero los cambios del editor actual antes de '
                'cambiar a Word Online.',
                parent=self,
            )
            return
        asunto = self.asunto.get().strip()
        if not asunto:
            messagebox.showwarning(
                'Aviso', 'Primero ingresa el asunto del oficio.', parent=self)
            return
        if not self.usuario_email:
            messagebox.showerror(
                'Word Online',
                'No se encontró el correo de la cuenta autenticada. '
                'Cierra sesión y vuelve a iniciar sesión.',
                parent=self,
            )
            return
        if not self.guardar_borrador_pendiente():
            messagebox.showerror(
                'Borrador',
                'No se pudo respaldar el borrador en PostgreSQL. '
                'Revisa la conexión antes de continuar.',
                parent=self,
            )
            return

        reemplazar_online = (
            self.word_opened
            and self.word_mode == 'desktop'
            and self.word_synced
        )
        try:
            self.word_path = abrir_word_online(
                self.folio,
                asunto,
                self.cuerpo_html,
                self.usuario_email,
                reemplazar_online,
            )
        except (OSError, RuntimeError, ValueError) as error:
            messagebox.showerror('Word Online', str(error), parent=self)
            return
        self.word_opened = True
        self.word_mode = 'online'
        self.word_synced = False
        self.lbl_estado_word.configure(
            text='Abierto en el navegador; guarda en Word Online antes de sincronizar.',
            text_color=GREEN,
        )
        self.lbl_estado_sync.configure(
            text='Después de guardar en el navegador, sincroniza aquí.',
            text_color=MUTED,
        )

    def sincronizar_desde_word(self):
        if not self.word_opened or self.word_path is None:
            messagebox.showwarning(
                'Aviso', 'Primero abre el documento en Word desde la aplicación.', parent=self)
            return
        try:
            if self.word_mode == 'online':
                descargar_cambios_word_online(
                    self.folio, self.word_path, self.usuario_email)
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
        try:
            Database_connection().guardar_borrador(
                self.folio,
                self.usuario_id,
                self.asunto.get().strip(),
                self.area_emisora.get().strip()
                if self.area_emisora.get() != 'Selecciona un área' else '',
                self.recepcion.get().strip(),
                self.cuerpo_html,
            )
        except (ConnectionError, RuntimeError, ValueError) as error:
            messagebox.showerror(
                'Error al guardar borrador',
                f'El texto se leyó desde Word, pero no se pudo respaldar en PostgreSQL.\n\n{error}',
                parent=self,
            )
            return
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
        self.word_mode = None
        self.word_synced = False
        self.word_signature = None
        self._programar_autoguardado()
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

        print("GUARDAR (cuerpo):", repr(cuerpo[:300]))

        try:
            Database_connection().guardar_borrador(
                self.folio, self.usuario_id, asunto, area, recepcion, cuerpo)
            registro = guardar_documento(
                asunto, area, recepcion, cuerpo, folio=self.folio)
            Database_connection().finalizar_borrador(
                self.folio, self.usuario_id, asunto, area, recepcion, cuerpo)
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror('Guardar documento', str(error), parent=self)
            return

        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
            self._autosave_job = None
        self._draft_needs_retry = False
        self.estado.configure(text=f"Documento {registro['folio']} guardado localmente.")
        messagebox.showinfo('Documento guardado',
                            f"Se registró {registro['folio']} correctamente.\n"
                            'Ya puedes generar tu PDF institucional.', parent=self)
        open_screen(self, 'folio_reservado.py', self.folio)

    def advertir(self, mensaje, control):
        messagebox.showwarning('Crear documento', mensaje, parent=self)
        control.focus_set()
