"""Pantalla Crear documento con integración de Editor Web tipo Word y Microsoft 365 (Word Online)."""

from tkinter import messagebox
import sys
import os
from pathlib import Path
import webview
import customtkinter as ctk
from controller.ms_graph_controller import crear_y_abrir_word_en_nube, obtener_texto_desde_onedrive

from ui_helpers import (
    Shell, ACCENT, BG, WHITE, LINE, MUTED, TEXT, SOFT, PINK,
    label, card, button, entry, font, open_screen,
)
from document_store import guardar_documento, obtener_documento, reservar_folio


AREAS_EMISORAS = [
    'Dirección General',
    'Dirección Administrativa',
    'Coordinación Jurídica',
    'Secretaría de Finanzas',
    'Subdirección de Planeación',
    'Unidad de Recursos Materiales',
    'Enlace de Vinculación',
]


class ApiWeb:
    """Puente de comunicación entre el Editor Web (HTML/JS) y Python."""
    def __init__(self, ventana_app):
        self.ventana_app = ventana_app

    def guardar_desde_web(self, html_content):
        self.ventana_app.cuerpo_html = html_content
        self.ventana_app.lbl_estado_editor.configure(text="✓ Texto editado y listo en el editor web", text_color="green")
        webview.destroy_window()


class CrearDocumentoApp(Shell):
    def __init__(self, folio):
        super().__init__('Crear documento')
        self.folio = folio
        self.cuerpo_html = "<p>Escribe aquí el contenido principal de tu oficio...</p>"
        self.file_id = None  # Almacenará el ID de OneDrive para sincronizar después
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

        intro = ctf = ctk.CTkFrame(formulario, fg_color='transparent')
        ctf.pack(fill='x', padx=28, pady=(25, 12))
        label(ctf, 'Información del documento', 19, TEXT, True).pack(anchor='w')
        label(ctf, 'Captura los datos y elige el método de redacción para el oficio.', 12, MUTED).pack(anchor='w', pady=(4, 0))

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

        # 4. Opción A: Editor Web Flotante
        seccion_editor = ctk.CTkFrame(campos, fg_color=SOFT, corner_radius=10)
        seccion_editor.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(10, 12))
        
        lbl_info_ed = ctk.CTkFrame(seccion_editor, fg_color='transparent')
        lbl_info_ed.pack(side='left', padx=18, pady=14)
        label(lbl_info_ed, 'Procesador de Textos Local', 13, TEXT, True).pack(anchor='w')
        self.lbl_estado_editor = label(lbl_info_ed, 'Editor web listo para usar', 11, MUTED)
        self.lbl_estado_editor.pack(anchor='w')

        button(seccion_editor, '📝 Abrir Editor Web', self.abrir_editor_web, primary=True,
               width=220, height=42).pack(side='right', padx=15, pady=14)

        # 5. Opción B: Microsoft 365 (Word Online en Azure)
        seccion_m365 = ctk.CTkFrame(campos, fg_color=SOFT, corner_radius=10)
        seccion_m365.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(0, 12))
        
        lbl_info_m365 = ctk.CTkFrame(seccion_m365, fg_color='transparent')
        lbl_info_m365.pack(side='left', padx=18, pady=14)
        label(lbl_info_m365, 'Microsoft 365 (Word Online)', 13, TEXT, True).pack(anchor='w')
        label(lbl_info_m365, 'Edita en la nube usando tu cuenta institucional', 11, MUTED).pack(anchor='w')

        button(seccion_m365, '☁️ Abrir en Word', self.abrir_en_microsoft_word, primary=True,
               width=180, height=42).pack(side='right', padx=15, pady=14)

        # 6. Botón de Sincronización desde la Nube (NUEVO)
        seccion_sync = ctk.CTkFrame(campos, fg_color=SOFT, corner_radius=10)
        seccion_sync.grid(row=6, column=0, columnspan=2, sticky='ew', pady=(0, 24))
        
        lbl_info_sync = ctk.CTkFrame(seccion_sync, fg_color='transparent')
        lbl_info_sync.pack(side='left', padx=18, pady=14)
        label(lbl_info_sync, 'S sincronizar Nube', 13, TEXT, True).pack(anchor='w')
        self.lbl_estado_sync = label(lbl_info_sync, 'Descarga los cambios hechos en Word Online', 11, MUTED)
        self.lbl_estado_sync.pack(anchor='w')

        button(seccion_sync, '🔄 Sincronizar Cambios', self.sincronizar_desde_nube, primary=False,
               fg_color='#107C41', hover_color='#0B522B', width=180, height=42).pack(side='right', padx=15, pady=14)

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

    def abrir_editor_web(self):
        """Abre la ventana flotante con el editor web tipo Word."""
        api = ApiWeb(self)
        ruta_html = Path(__file__).parent / 'editor.html'
        
        def on_loaded():
            window.evaluate_js(f"setContent({repr(self.cuerpo_html)});")

        window = webview.create_window(
            'Editor de Oficio - Estilo Word',
            str(ruta_html),
            js_api=api,
            width=900,
            height=650,
            resizable=True
        )
        webview.start(on_loaded)

    def abrir_en_microsoft_word(self):
        """Abre Microsoft Word Online a través de Microsoft Graph API."""
        asunto = self.asunto.get().strip()
        if not asunto:
            messagebox.showwarning("Aviso", "Primero ingresa el asunto del oficio.", parent=self)
            return
            
        try:
            # Crea el documento en la nube y abre Word Online en el navegador
            file_id, web_url = crear_y_abrir_word_en_nube(self.folio, asunto)
            self.file_id = file_id  # Guardamos el ID para sincronizar después
            messagebox.showinfo("Microsoft 365", 
                                "Se ha abierto Word Online en tu navegador.\n"
                                "Edita tu documento y al terminar presiona el botón 'Sincronizar Cambios' en la app.", 
                                parent=self)
        except Exception as e:
            messagebox.showerror("Error de conexión", str(e), parent=self)

    def sincronizar_desde_nube(self):
        """Función que descarga el texto editado en Word Online y lo refleja en la app."""
        if not self.file_id:
            messagebox.showwarning("Aviso", "Primero debes abrir el documento en Word Online desde la aplicación.", parent=self)
            return
            
        try:
            # Llama a la función del controlador para obtener el texto actualizado
            texto_sincronizado = obtener_texto_desde_onedrive(self.file_id)
            
            # Formateamos el texto para que la aplicación lo reconozca
            self.cuerpo_html = f"<p>{texto_sincronizado.replace(chr(10), '<br>')}</p>"
            
            self.lbl_estado_sync.configure(text="✓ Sincronizado correctamente desde OneDrive", text_color="green")
            messagebox.showinfo("Sincronización exitosa", "¡Los cambios de Word Online se han sincronizado en la aplicación!", parent=self)
        except Exception as e:
            messagebox.showerror("Error de sincronización", str(e), parent=self)

    def navigate(self, name):
        if name == 'Crear documento':
            self.asunto.focus_set()
        else:
            super().navigate(name)

    def limpiar(self):
        self.asunto.delete(0, 'end')
        self.area_emisora.set('Selecciona un área')
        self.recepcion.delete(0, 'end')
        self.cuerpo_html = "<p>Escribe aquí el contenido principal de tu oficio...</p>"
        self.file_id = None
        self.lbl_estado_editor.configure(text="Editor web listo para usar", text_color=MUTED)
        self.lbl_estado_sync.configure(text="Descarga los cambios hechos en Word Online", text_color=MUTED)
        self.estado.configure(text='')
        self.asunto.focus_set()

    def guardar(self):
        asunto = self.asunto.get().strip()
        area = self.area_emisora.get().strip()
        recepcion = self.recepcion.get().strip()
        
        # Obtenemos el cuerpo directamente asegurando que no quede el texto por defecto
        cuerpo = getattr(self, 'cuerpo_html', '').strip()
        if not cuerpo or "Escribe aquí el contenido principal" in cuerpo:
            cuerpo = "<p>Documento oficial emitido sin observaciones adicionales.</p>"

        if not asunto:
            return self.advertir('Completa el campo Asunto.', self.asunto)
        if not area or area == 'Selecciona un área':
            return self.advertir('Selecciona un Área emisora.', self.area_emisora)
        if not recepcion:
            return self.advertir('Completa el campo Recepción.', self.recepcion)

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


if __name__ == '__main__':
    folio = sys.argv[1] if len(sys.argv) > 1 else reservar_folio()
    existente = obtener_documento(folio)
    if existente and existente.get('estado') == 'Creado':
        folio = reservar_folio()
    CrearDocumentoApp(folio).mainloop()