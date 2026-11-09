"""Segunda pantalla: visualización de folio reservado, antes del formulario."""
import sys
import threading
from queue import Empty, Queue
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
from model.document_store import obtener_documento, ruta_pdf_oficio
from controller.pdf_generator import generar_pdf_oficio
from controller.database_conecction import Database_connection
from controller.remote_storage import subir_pdf_al_servidor

class PantallaFolio(Shell):
    def __init__(self, master, folio):
        super().__init__(master, 'Crear documento')
        self.title('Gestión Institucional — Folio reservado')
        self.folio = folio
        self._resultado_subida_pdf = Queue()
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

        self.btn_generar_pdf.configure(
            state='disabled', text='Conectando con servidor SFTP...')
        threading.Thread(
            target=self._subir_y_registrar_pdf,
            args=(destino,),
            daemon=True,
        ).start()
        self.after(100, self._revisar_resultado_subida_pdf)

    def _subir_y_registrar_pdf(self, destino):
        try:
            ruta_remota = subir_pdf_al_servidor(
                destino,
                callback=lambda transferidos, total: self._resultado_subida_pdf.put(
                    ('progress', transferidos, total)
                ),
            )
        except Exception as error:
            self._resultado_subida_pdf.put(('upload_error', error))
            return

        self._resultado_subida_pdf.put(('registering',))
        try:
            Database_connection().registrar_ruta_documento(
                self.folio, ruta_remota)
        except Exception as error:
            self._resultado_subida_pdf.put(
                ('database_error', error, ruta_remota))
            return

        self._resultado_subida_pdf.put(('success', ruta_remota))

    def _revisar_resultado_subida_pdf(self):
        if not self.winfo_exists():
            return
        while True:
            try:
                resultado = self._resultado_subida_pdf.get_nowait()
            except Empty:
                self.after(100, self._revisar_resultado_subida_pdf)
                return

            if resultado[0] == 'progress':
                transferidos, total = resultado[1:]
                porcentaje = int(transferidos * 100 / total) if total else 0
                self.btn_generar_pdf.configure(
                    text=f'Subiendo PDF a la VM... {porcentaje}%')
            elif resultado[0] == 'registering':
                self.btn_generar_pdf.configure(
                    text='Registrando ruta en PostgreSQL...')
            elif resultado[0] == 'upload_error':
                self._mostrar_error_subida(resultado[1])
                return
            elif resultado[0] == 'database_error':
                self._mostrar_error_registro(resultado[1], resultado[2])
                return
            else:
                self._mostrar_exito(resultado[1])
                return

    def _restaurar_boton_pdf(self):
        if self.winfo_exists():
            self.btn_generar_pdf.configure(
                state='normal', text='↓  Generar PDF del Oficio')

    def _mostrar_error_subida(self, error):
        self._restaurar_boton_pdf()
        if self.winfo_exists():
            messagebox.showerror(
                'Error al subir PDF a la VM',
                f'El PDF local se generó, pero no se pudo subir al servidor.\n\n{error}',
                parent=self,
            )

    def _mostrar_error_registro(self, error, ruta_remota):
        self._restaurar_boton_pdf()
        if self.winfo_exists():
            messagebox.showerror(
                'Ruta no registrada',
                'El PDF sí se subió a la VM, pero no se pudo guardar su ruta '
                f'en PostgreSQL.\n\nRuta remota: {ruta_remota}\n\n{error}',
                parent=self,
            )

    def _mostrar_exito(self, ruta_remota):
        self._restaurar_boton_pdf()
        if self.winfo_exists():
            messagebox.showinfo(
                'Generar PDF',
                'El PDF se subió a la VM y su ruta quedó registrada en PostgreSQL:\n'
                f'{ruta_remota}',
                parent=self,
            )
    
