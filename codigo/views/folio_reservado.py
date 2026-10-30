"""Segunda pantalla: visualización de folio reservado, antes del formulario."""
from datetime import datetime
from pathlib import Path
import sys
from tkinter import filedialog, messagebox
import customtkinter as ctk
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent  # carpeta "codigo"
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from ui_helpers import (
    Shell, ACCENT, BG, WHITE, LINE, TEXT, MUTED, PINK, GREEN, SOFT,
    label, card, button, open_screen, font,
)
from model.document_store import obtener_documento, reservar_folio
from controller.pdf_generator import generar_pdf_oficio

class PantallaFolio(Shell):
    def __init__(self, folio):
        super().__init__('Crear documento')
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
        estado = self.registro.get('estado', 'Creado' if str(folio).startswith('DOC-') else 'Reservado')
        self.btn_crear = button(interior, '▤  Crear documento', self.crear, primary=True,
                                height=62, fg_color=GREEN, hover_color='#18764F', font=font(19, True))
        self.btn_crear.pack(fill='x', padx=86, pady=(0, 14))
        button(interior, '↓  Generar PDF del Oficio', self.generar_pdf, height=58,
               text_color=ACCENT, border_color=ACCENT, font=font(17, True)).pack(fill='x', padx=86)
        if estado == 'Creado':
            label(interior, 'Documento guardado. Puedes generar su PDF o volver al inicio.',
                  12, GREEN, True).pack(pady=(16, 0))
            self.btn_crear.configure(text='✓  Documento creado', state='disabled')
        else:
            label(interior, 'Primero completa Asunto, Área emisora, Recepción y Cuerpo.', 11, MUTED).pack(pady=(16, 0))

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
        
        destino = filedialog.asksaveasfilename(
            parent=self, title='Guardar Oficio en PDF',
            defaultextension='.pdf', initialfile=f"Oficio_{self.folio.replace('/', '_')}.pdf",
            filetypes=[('Archivo PDF', '*.pdf')])
        if not destino:
            return

        asunto = registro.get('asunto', '')
        cuerpo_texto = registro.get('cuerpo', '')
        area_emisora = registro.get('area_emisora', '')
        recepcion = registro.get('recepcion', '')

        try:
            generar_pdf_oficio(destino, self.folio, asunto, cuerpo_texto, area_emisora, recepcion)
            messagebox.showinfo('Generar PDF', 'El oficio se ha generado y guardado con éxito.', parent=self)
        except Exception as error:
            messagebox.showerror('Error al generar PDF', str(error), parent=self)
            

    


def main():
    folio = sys.argv[1] if len(sys.argv) > 1 else reservar_folio()
    PantallaFolio(folio).mainloop()


if __name__ == '__main__':
    main()