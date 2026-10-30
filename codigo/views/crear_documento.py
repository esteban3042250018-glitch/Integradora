"""Pantalla Crear documento con integración de Editor Web tipo Word y Microsoft 365 (Word Online)."""

from tkinter import messagebox
import sys
import os
import json
<<<<<<< HEAD
import html
import webbrowser
=======
>>>>>>> 8343474b4b8d1b842960ee1c4d06b1e2e5cd2c67
from pathlib import Path
import webview
import customtkinter as ctk
from controller.ms_graph_controller import crear_y_abrir_word_en_nube, obtener_texto_desde_onedrive

from ui_helpers import (
    Shell, ACCENT, BG, WHITE, LINE, MUTED, TEXT, SOFT, PINK,
    label, card, button, entry, font, open_screen,
)
from model.document_store import guardar_documento, obtener_documento, reservar_folio


AREAS_EMISORAS = [
    'Dirección General',
    'Dirección Administrativa',
    'Coordinación Jurídica',
    'Secretaría de Finanzas',
    'Subdirección de Planeación',
    'Unidad de Recursos Materiales',
    'Enlace de Vinculación',
]

TEXTO_POR_DEFECTO = "<p>Escribe aquí el contenido principal de tu oficio...</p>"
MARCA_POR_DEFECTO = "Escribe aquí el contenido principal"


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
        self.cuerpo_html = TEXTO_POR_DEFECTO
        self.file_id = None   # ID del archivo en OneDrive
        self.web_url = None   # URL de Word Online para reabrir el mismo archivo
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

        # 4. Opción A: Editor Web
        seccion_editor = ctk.CTkFrame(campos, fg_color=SOFT, corner_radius=10)
        seccion_editor.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(10, 12))

        lbl_info_ed = ctk.CTkFrame(seccion_editor, fg_color='transparent')
        lbl_info_ed.pack(side='left', padx=18, pady=14)
        label(lbl_info_ed, 'Procesador de Textos Local', 13, TEXT, True).pack(anchor='w')
        self.lbl_estado_editor = label(lbl_info_ed, 'Editor web listo para usar', 11, MUTED)
        self.lbl_estado_editor.pack(anchor='w')

        button(seccion_editor, '📝 Abrir Editor Web', self.abrir_editor_web, primary=True,
               width=220, height=42).pack(side='right', padx=15, pady=14)

        # 5. Opción B: Microsoft 365 (Word Online)
        seccion_m365 = ctk.CTkFrame(campos, fg_color=SOFT, corner_radius=10)
        seccion_m365.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(0, 12))

        lbl_info_m365 = ctk.CTkFrame(seccion_m365, fg_color='transparent')
        lbl_info_m365.pack(side='left', padx=18, pady=14)
        label(lbl_info_m365, 'Microsoft 365 (Word Online)', 13, TEXT, True).pack(anchor='w')
        label(lbl_info_m365, 'Edita en la nube usando tu cuenta institucional', 11, MUTED).pack(anchor='w')

        button(seccion_m365, '☁️ Abrir en Word', self.abrir_en_microsoft_word, primary=True,
               width=180, height=42).pack(side='right', padx=15, pady=14)

        # 6. Sincronización desde la nube
        seccion_sync = ctk.CTkFrame(campos, fg_color=SOFT, corner_radius=10)
        seccion_sync.grid(row=6, column=0, columnspan=2, sticky='ew', pady=(0, 24))

        lbl_info_sync = ctk.CTkFrame(seccion_sync, fg_color='transparent')
        lbl_info_sync.pack(side='left', padx=18, pady=14)
        label(lbl_info_sync, 'Sincronizar con la nube', 13, TEXT, True).pack(anchor='w')
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

    # ------------------------------------------------------------------
    # Editor web local
    # ------------------------------------------------------------------
    def abrir_editor_web(self):
<<<<<<< HEAD
=======
    
>>>>>>> 8343474b4b8d1b842960ee1c4d06b1e2e5cd2c67
        api = ApiWeb(self)
        RAIZ = Path(__file__).resolve().parent.parent   # carpeta "codigo"
        EDITOR = RAIZ / 'editor.html'

        if not EDITOR.is_file():
            messagebox.showerror('Editor', f'No existe el editor:\n{EDITOR}', parent=self)
            return

        def on_loaded():
            window.evaluate_js(f"setContent({json.dumps(self.cuerpo_html)});")

        window = webview.create_window(
            'Editor de Oficio - Estilo Word',
            str(EDITOR),
            js_api=api,
            width=900,
            height=650,
            resizable=True,
        )
        webview.start(on_loaded)

    # ------------------------------------------------------------------
    # Microsoft 365 / Word Online
    # ------------------------------------------------------------------
    def abrir_en_microsoft_word(self):
        """Abre Word Online. Si ya existe el archivo de este folio, lo reabre en vez de crear otro."""
        asunto = self.asunto.get().strip()
        if not asunto:
            messagebox.showwarning("Aviso", "Primero ingresa el asunto del oficio.", parent=self)
            return

        try:
            if self.file_id and self.web_url:
                webbrowser.open(self.web_url)
                return

            self.file_id, self.web_url = crear_y_abrir_word_en_nube(self.folio, asunto)
            messagebox.showinfo(
                "Microsoft 365",
                "Se abrió Word Online en tu navegador.\n"
                "Escribe el contenido, espera unos segundos a que Word lo guarde\n"
                "y después presiona 'Sincronizar Cambios' en la app.",
                parent=self)
        except Exception as e:
            messagebox.showerror("Error de conexión", str(e), parent=self)

    def sincronizar_desde_nube(self):
        """Descarga el texto editado en Word Online y lo guarda como cuerpo del oficio."""
        if not self.file_id:
            messagebox.showwarning(
                "Aviso", "Primero debes abrir el documento en Word Online desde la aplicación.", parent=self)
            return

        try:
            texto = obtener_texto_desde_onedrive(self.file_id)
        except Exception as e:
            messagebox.showerror("Error de sincronización", str(e), parent=self)
            return

        if not texto.strip():
            messagebox.showwarning(
                "Aviso",
                "El documento en Word Online no tiene texto todavía.\n"
                "Espera unos segundos a que se guarde y vuelve a sincronizar.",
                parent=self)
            return

        # Se escapa el texto para que &, < o > no rompan el PDF (ReportLab).
        self.cuerpo_html = "<p>" + html.escape(texto).replace("\n", "<br>") + "</p>"
        print("SYNC (file_id):", self.file_id)
        print("SYNC (texto):", repr(texto[:300]))

        self.lbl_estado_sync.configure(text="✓ Sincronizado correctamente desde OneDrive", text_color="green")
        messagebox.showinfo("Sincronización exitosa",
                            "¡Los cambios de Word Online se sincronizaron en la aplicación!", parent=self)

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
        self.cuerpo_html = TEXTO_POR_DEFECTO
        self.file_id = None
        self.web_url = None
        self.lbl_estado_editor.configure(text="Editor web listo para usar", text_color=MUTED)
        self.lbl_estado_sync.configure(text="Descarga los cambios hechos en Word Online", text_color=MUTED)
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

        sin_contenido = (not cuerpo) or (MARCA_POR_DEFECTO in cuerpo) or cuerpo in ('<p></p>', '<p><br></p>')

        # Si abrió Word Online pero no sincronizó, avisamos en vez de guardar el texto por defecto.
        if sin_contenido and self.file_id:
            messagebox.showwarning(
                'Crear documento',
                'Abriste Word Online pero todavía no has sincronizado los cambios.\n'
                "Presiona 'Sincronizar Cambios' antes de guardar.",
                parent=self)
            return

        if sin_contenido:
            cuerpo = "<p>Documento oficial emitido sin observaciones adicionales.</p>"

        print("GUARDAR (cuerpo):", repr(cuerpo[:300]))

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
