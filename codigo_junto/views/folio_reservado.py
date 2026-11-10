"""Segunda pantalla: visualización de folio reservado, antes del formulario."""
import sys
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk

RAIZ = Path(__file__).resolve().parent.parent  # carpeta "codigo"
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from views.ui_helpers import (
    Shell, ACCENT, BG, WHITE, LINE, TEXT, MUTED, PINK, GREEN, SOFT,
    label, card, button, open_screen, font,
)
from model.document_store import (
    obtener_documento, registrar_pdf_local, ruta_pdf_oficio,
)
from controller.pdf_generator import generar_pdf_oficio
from controller.database_conecction import Database_connection

class PantallaFolio(Shell):
    def __init__(self, master, folio):
        super().__init__(master, 'Crear documento')
        self.title('Gestión Institucional — Folio reservado')
        self.folio = folio
        self.registro = obtener_documento(folio)
        if self.registro is None:
            messagebox.showerror('Folio', 'No se encontró el folio reservado.', parent=self)
            self.after(50, lambda: open_screen(self, 'home.py'))
            return

        contenido = ctk.CTkFrame(self.body, fg_color='transparent')
        contenido.pack(fill='x', padx=28, pady=24)
        button(contenido, '←  Volver', lambda: open_screen(self, 'home.py'), width=120).pack(anchor='w', pady=(0, 22))
        panel = card(contenido)
        panel.pack(fill='x', padx=55, pady=6)
        interior = ctk.CTkFrame(panel, fg_color='transparent')
        interior.pack(fill='x', padx=72, pady=32)
        sello = ctk.CTkFrame(interior, width=120, height=120, fg_color=PINK, corner_radius=60)
        sello.pack(pady=(0, 16))
        sello.pack_propagate(False)
        label(sello, '▤', 65, ACCENT).pack(expand=True)
        label(interior, 'Tu folio es:', 31, TEXT, True).pack(pady=(3, 14))
        folio_caja = ctk.CTkFrame(interior, fg_color='#F5E8EE', corner_radius=11)
        folio_caja.pack(fill='x', padx=85)
        label(folio_caja, folio, 24, ACCENT, True).pack(pady=22, padx=18)
        label(interior, 'Conserva este número para identificar tu documento.', 12, MUTED).pack(pady=(14, 28))
        self.btn_crear = button(interior, '▤  Crear documento', self.crear, primary=True,
                                height=62, fg_color=GREEN, hover_color='#18764F', font=font(19, True))
        self.btn_crear.pack(fill='x', padx=86, pady=(0, 14))
        self.btn_generar_pdf = button(
            interior, '↓  Generar PDF del Oficio', self.generar_pdf, height=58,
            text_color=ACCENT, border_color=ACCENT, font=font(17, True))
        self.btn_generar_pdf.pack(fill='x', padx=86)
        self.estado_folio = label(interior, '', 12, GREEN, True)
        self.estado_folio.pack(pady=(16, 0))
        self._actualizar_estado()

    def on_show(self):
        self._actualizar_estado()

    def _actualizar_estado(self):
        self.registro = obtener_documento(self.folio)
        if self.registro is None:
            return
        if self.registro.get('estado') == 'Creado':
            self.estado_folio.configure(
                text='Documento guardado. Puedes generar su PDF o volver al inicio.',
                text_color=GREEN,
            )
            self.btn_crear.configure(text='✓  Documento creado', state='disabled')
        else:
            self.estado_folio.configure(
                text='Primero completa Asunto, Área emisora, Recepción y Cuerpo.',
                text_color=MUTED,
            )
            self.btn_crear.configure(text='▤  Crear documento', state='normal')

    def navigate(self, name):
        if name == 'Crear documento':
            if self.registro.get('estado') != 'Creado':
                self.crear()
        else:
            super().navigate(name)

    def crear(self):
        open_screen(self, 'crear_documento.py', self.folio)

    def generar_pdf(self):
        registro = obtener_documento(self.folio)
        if not registro or registro.get('estado') != 'Creado':
            messagebox.showwarning('Generar PDF', 'Debes completar y guardar el documento primero.', parent=self)
            self.crear()
            return
        
        destino = ruta_pdf_oficio(self.folio)

        asunto = registro.get('asunto', '')
        cuerpo_texto = registro.get('cuerpo', '')
        area_emisora = registro.get('area_emisora', '')
        recepcion = registro.get('recepcion', '')

        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            generar_pdf_oficio(
                str(destino), self.folio, asunto, cuerpo_texto, area_emisora, recepcion)
        except Exception as error:
            messagebox.showerror('Error al generar PDF', str(error), parent=self)
            return

        try:
            registrar_pdf_local(self.folio, destino)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                'Historial local',
                f'El PDF se generó, pero no se pudo actualizar el historial local.\n\n'
                f'Archivo: {destino}\n\n{error}',
                parent=self,
            )
            return

        try:
            Database_connection().registrar_pdf_generado(self.folio)
        except (ConnectionError, RuntimeError) as error:
            messagebox.showwarning(
                'PDF guardado localmente',
                f'El PDF y su ruta quedaron guardados en este equipo:\n{destino}\n\n'
                'No se pudo actualizar el estado del borrador ni crear el aviso '
                f'en PostgreSQL:\n{error}',
                parent=self,
            )
            return

        messagebox.showinfo(
            'Generar PDF',
            f'El oficio y su ruta quedaron guardados en este equipo:\n{destino}',
            parent=self,
        )
    
