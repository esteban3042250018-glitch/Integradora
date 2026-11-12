"""Listado local de PDF generados."""
import os
from pathlib import Path
import sys
from tkinter import messagebox

import customtkinter as ctk

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from model.document_store import listar_pdfs_locales
from views.ui_helpers import ACCENT, BG, MUTED, TEXT, Shell, button, card, label


class EnviadosApp(Shell):
    def __init__(self, master):
        super().__init__(master, 'Enviada')
        self.title('Gestión Institucional - Enviados')

        contenido = ctk.CTkFrame(self.body, fg_color='transparent')
        contenido.pack(fill='x', padx=22, pady=20)

        encabezado = ctk.CTkFrame(contenido, fg_color='transparent')
        encabezado.pack(fill='x', pady=(0, 18))
        texto = ctk.CTkFrame(encabezado, fg_color='transparent')
        texto.pack(side='left')
        label(texto, 'Documentos enviados', 28, TEXT, True).pack(anchor='w')
        label(
            texto,
            'PDF guardados en este equipo.',
            13, MUTED,
        ).pack(anchor='w', pady=(4, 0))
        button(encabezado, '↻  Actualizar', self.cargar_documentos, width=130).pack(
            side='right', pady=8)

        self.listado = card(contenido)
        self.listado.pack(fill='x')

    def on_show(self):
        self.cargar_documentos()

    def navigate(self, name):
        if name == 'Enviada':
            self.cargar_documentos()
        else:
            super().navigate(name)

    def cargar_documentos(self):
        for elemento in self.listado.winfo_children():
            elemento.destroy()

        try:
            documentos = listar_pdfs_locales()
        except (OSError, ValueError) as error:
            label(
                self.listado,
                f'No se pudieron cargar los documentos: {error}',
                12, ACCENT, wraplength=800, justify='left',
            ).pack(anchor='w', padx=22, pady=24)
            return

        if not documentos:
            label(
                self.listado, 'Todavía no hay PDF guardados en este equipo.',
                13, MUTED,
            ).pack(anchor='w', padx=22, pady=24)
            return

        encabezados = ctk.CTkFrame(self.listado, fg_color='transparent')
        encabezados.pack(fill='x', padx=18, pady=(14, 8))
        encabezados.grid_columnconfigure(1, weight=1)
        label(encabezados, 'FOLIO', 10, MUTED, True, width=190, anchor='w').grid(
            row=0, column=0, sticky='w', padx=(4, 12))
        label(encabezados, 'ARCHIVO LOCAL', 10, MUTED, True, anchor='w').grid(
            row=0, column=1, sticky='w', padx=8)
        label(encabezados, 'REGISTRADO', 10, MUTED, True, width=155, anchor='w').grid(
            row=0, column=2, sticky='w', padx=8)

        for documento in documentos:
            self._crear_fila(documento)

    def _crear_fila(self, documento):
        fila = ctk.CTkFrame(self.listado, fg_color=BG, corner_radius=8)
        fila.pack(fill='x', padx=18, pady=5)
        fila.grid_columnconfigure(1, weight=1)

        folio = str(documento['folio'])
        ruta = str(documento['ruta_archivo'])
        fecha = documento.get('fecha_registro')
        fecha_texto = fecha.strftime('%Y-%m-%d %H:%M') if hasattr(fecha, 'strftime') else str(fecha or '')

        label(fila, folio, 12, TEXT, True, width=190, anchor='w').grid(
            row=0, column=0, sticky='w', padx=(12, 8), pady=12)
        label(fila, ruta, 11, MUTED, anchor='w', wraplength=560, justify='left').grid(
            row=0, column=1, sticky='ew', padx=8, pady=10)
        label(fila, fecha_texto, 11, MUTED, width=155, anchor='w').grid(
            row=0, column=2, sticky='w', padx=8, pady=10)
        button(
            fila, 'Abrir PDF', width=105, height=34,
            command=lambda path=ruta, number=folio: self.abrir_documento(path, number),
        ).grid(row=0, column=3, sticky='e', padx=12, pady=8)

    def abrir_documento(self, ruta, folio):
        archivo = Path(ruta).expanduser()
        if not archivo.is_file():
            messagebox.showerror(
                'Archivo no encontrado',
                f'No se encontró el PDF registrado para {folio}:\n{archivo}',
                parent=self,
            )
            return

        try:
            os.startfile(str(archivo))
        except OSError as error:
            messagebox.showerror(
                'No se pudo abrir el PDF',
                f'Ruta: {archivo}\n\n{error}',
                parent=self,
            )
