import os
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))
import re
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
from ui_helpers import *
import msal
import requests
from decouple import config
from model.microsoft_auth import obtener_token_silencioso
from model.microsoft_mail import obtener_correos_graph
from model.document_store import reservar_folio
# Configuración de MSAL para Microsoft Entra ID
CLIENT_ID = config('MICROSOFT_AUTH_API')
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["https://graph.microsoft.com/Mail.Read"]

msal_app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
RECORDS = []
STATUS = {
    'Por asignar': ('#FFF7D5', '#775500'), 
    'En atención': ('#EAF2FA', '#276C9E'),
    'Respondida': ('#E6F4EE', '#22865E'), 
    'Turnada': ('#F5E8EE', '#801537')
}
PRIORITY = {'Alta': ACCENT, 'Media': '#B78600', 'Normal': MUTED}





class AppGestiónInstitucional(Shell):
    def __init__(self):
        super().__init__('Correspondencia')
        self.category = 'all'
        
        # Cargar los correos reales desde Microsoft Graph usando el caché
        global RECORDS
        correos_cargados = obtener_correos_graph()
        if correos_cargados:
            RECORDS = correos_cargados
        
        self.content = ctk.CTkFrame(self.body, fg_color='transparent')
        self.content.pack(fill='x', padx=22, pady=20)
        
        header = ctk.CTkFrame(self.content, fg_color='transparent')
        header.pack(fill='x', pady=(0, 18))
        heading = ctk.CTkFrame(header, fg_color='transparent')
        heading.pack(side='left')
        label(heading, 'Correspondencia (Correos de Microsoft)', 28).pack(anchor='w')
        label(heading, 'Bandeja sincronizada con tu cuenta institucional de Microsoft 365', 13, MUTED).pack(anchor='w')
        
        button(header, '▤  Crear documento', self.crear_documento, primary=True, width=190).pack(side='right', anchor='n', pady=8)
        button(header, '✦  Registrar correspondencia', lambda: unavailable(self, 'Registrar correspondencia'), width=226).pack(side='right', anchor='n', padx=(0, 12), pady=8)
        
        metrics = ctk.CTkFrame(self.content, fg_color='transparent')
        metrics.pack(fill='x', pady=(0, 22))
        metrics.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform='metrics')
        
        total_registros = len(RECORDS)
        for index, (title, value, subtitle, color, soft, symbol, progress) in enumerate([
            ('CORREOS TOTALES', str(total_registros), 'Sincronizados', ACCENT, PINK, '▣', .56),
            ('POR ASIGNAR', str(len([r for r in RECORDS if r[8] == 'Por asignar'])), 'Pendientes', '#775500', '#FFF7D5', '♙', .32),
            ('EN SEGUIMIENTO', str(len([r for r in RECORDS if r[8] == 'En atención'])), 'Activos', BLUE, '#EAF2FA', '☷', .63),
            ('CONCLUIDOS', '0', 'Este mes', GREEN, '#E6F4EE', '✓', .68)]):
            
            tile = card(metrics, height=116)
            tile.grid(row=0, column=index, sticky='nsew', padx=(0, 16 if index < 3 else 0))
            tile.grid_propagate(False)
            tile.grid_columnconfigure(0, weight=1)
            label(tile, title, 10, MUTED, True, height=18).grid(row=0, column=0, sticky='w', padx=16, pady=(14, 0))
            amount = ctk.CTkFrame(tile, fg_color='transparent')
            amount.grid(row=1, column=0, sticky='w', padx=16)
            label(amount, value, 32).pack(side='left')
            label(amount, subtitle, 10, color).pack(side='left', padx=(12, 0), pady=(9, 0))
            label(tile, symbol, 23, color, width=38, height=38, fg_color=soft, corner_radius=10).place(relx=1, x=-16, y=16, anchor='ne')
            bar = ctk.CTkProgressBar(tile, height=4, progress_color=color, fg_color=SOFT, corner_radius=2)
            bar.grid(row=2, column=0, sticky='ew', padx=16, pady=(4, 16))
            bar.set(progress)
            
        self.table_card = card(self.content)
        self.table_card.pack(fill='x')
        
        table_top = ctk.CTkFrame(self.table_card, fg_color='transparent')
        table_top.pack(fill='x', padx=20, pady=(16, 8))
        title = ctk.CTkFrame(table_top, fg_color='transparent')
        title.pack(side='left')
        label(title, 'Buzón de entrada', 21).pack(anchor='w')
        label(title, f'{total_registros} mensajes cargados desde tu cuenta', 12, MUTED).pack(anchor='w')
        
        button(table_top, 'Ver bandeja completa  →', self.reset_filters, border_width=0,
            text_color=ACCENT, height=30, width=170, font=font(12, True)).pack(side='right')
            
        filters = ctk.CTkFrame(self.table_card, fg_color='transparent')
        filters.pack(fill='x', padx=20, pady=(0, 16))
        
        self.filter_entry = entry(filters, '⌕  Filtrar esta bandeja...', fg_color=SOFT, border_width=0, height=34)
        self.filter_entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.state_filter = select(filters, ['Estado', *STATUS], lambda value: self.filter_rows(), 94)
        self.state_filter.pack(side='left', padx=(0, 8))
        self.priority_filter = select(filters, ['Prioridad', 'Alta', 'Media', 'Normal'], lambda value: self.filter_rows(), 94)
        self.priority_filter.pack(side='left', padx=(0, 8))
        
        button(filters, '☷  Más filtros  ⌄', lambda: unavailable(self, 'Más filtros'), width=115, height=34, font=font(10)).pack(side='left')
        
        self.rows = ctk.CTkFrame(self.table_card, fg_color='transparent', corner_radius=0)
        self.rows.pack(fill='x', padx=1)
        
        footer = ctk.CTkFrame(self.table_card, fg_color='transparent')
        footer.pack(fill='x', padx=16, pady=12)
        self.count_label = label(footer, f'Mostrando {total_registros} registros', 10, MUTED)
        self.count_label.pack(side='left')
        
        paging = ctk.CTkFrame(footer, fg_color='transparent')
        paging.pack(side='right')
        
        for text in ['‹', '1', '2', '3', '›']:
            button(paging, text, self.reset_filters if text == '1' else lambda: unavailable(self, 'Más registros'), width=27, height=27,
                fg_color=ACCENT if text == '1' else WHITE, text_color=WHITE if text == '1' else MUTED,
                border_width=0, corner_radius=4, font=font(11)).pack(side='left', padx=2)
                
        self.search_entry.bind('<KeyRelease>', self.filter_rows)
        self.filter_entry.bind('<KeyRelease>', self.filter_rows)
        self.render_rows(RECORDS)

    def navigate(self, name):
        categories = {'Correspondencia · 18': 'all', 'Por asignar · 7': 'Por asignar', 'Seguimiento · 12': 'seguimiento', 'Enviada': 'enviada'}
        if name in categories:
            self.category = categories[name]
            self.filter_rows()
        else:
            super().navigate(name)

    def crear_documento(self):
        """Reserva un folio nuevo y abre el flujo: folio reservado → crear documento → PDF."""
        try:
            folio = reservar_folio()
        except (OSError, ValueError) as error:
            messagebox.showerror('Crear documento', str(error), parent=self)
            return
        open_screen(self, 'folio_reservado.py', folio)

    def reset_filters(self):
        self.category = 'all'
        self.search_entry.delete(0, 'end')
        self.filter_entry.delete(0, 'end')
        self.state_filter.set('Estado')
        self.priority_filter.set('Prioridad')
        self.filter_rows()

    @staticmethod
    def matching(records, query='', state='Estado', priority='Prioridad', category='all'):
        terms = query.casefold().split()
        return [r for r in records if all(term in ' '.join(r).casefold() for term in terms)
            and (state == 'Estado' or r[8] == state) and (priority == 'Prioridad' or r[5] == priority)
            and (category == 'all' or r[8] == category or (category == 'seguimiento' and r[8] in ('En atención', 'Turnada'))
                 or (category == 'enviada' and r[1] == 'ENVIADA'))]

    def filter_rows(self, event=None):
        query = self.search_entry.get() + ' ' + self.filter_entry.get()
        records = self.matching(RECORDS, query, self.state_filter.get(), self.priority_filter.get(), self.category)
        self.render_rows(records)
        filtered = query.strip() or self.state_filter.get() != 'Estado' or self.priority_filter.get() != 'Prioridad' or self.category != 'all'
        self.count_label.configure(text=f'{len(records)} resultados encontrados' if filtered else f'Mostrando {len(RECORDS)} registros')

    def render_rows(self, records):
        for child in self.rows.winfo_children():
            child.destroy()
        widths = [88, 236, 116, 96, 118, 104]
        def row_frame(background):
            frame = ctk.CTkFrame(self.rows, fg_color=background, corner_radius=0)
            frame.pack(fill='x')
            for i, width in enumerate(widths):
                frame.grid_columnconfigure(i, weight=1 if i == 5 else 0, minsize=width)
            return frame
        head = row_frame(SOFT)
        for i, name in enumerate(['FOLIO', 'ASUNTO / REMITENTE', 'ÁREA / PRIORIDAD', 'RESPONSABLE', 'ESTADO', 'FECHA']):
            label(head, name, 10, MUTED, True, width=widths[i]-16, anchor='w').grid(row=0, column=i, sticky='ew', padx=8, pady=5)
        for record in records:
            ctk.CTkFrame(self.rows, height=2, fg_color=LINE, corner_radius=0).pack(fill='x')
            row = row_frame(WHITE)
            for i in range(6):
                cell = ctk.CTkFrame(row, fg_color='transparent', width=widths[i]-16, height=75)
                cell.grid(row=0, column=i, sticky='nsew', padx=8)
                cell.grid_propagate(False)
                cell.grid_columnconfigure(0, weight=1)
                if i == 0:
                    label(cell, record[0], 12, ACCENT, height=20).grid(row=0, column=0, sticky='w', pady=(17, 0))
                    label(cell, record[1], 10, '#9A94A0', True, height=18).grid(row=1, column=0, sticky='w')
                elif i == 1:
                    label(cell, self.fit_subject(record[2], widths[i]-18), 13, anchor='w', height=22).grid(row=0, column=0, sticky='ew', pady=(16, 0))
                    label(cell, record[3], 10, MUTED, anchor='w', height=18).grid(row=1, column=0, sticky='ew')
                elif i == 2:
                    label(cell, record[4], 10, wraplength=98, justify='left', anchor='w', height=27).grid(row=0, column=0, sticky='w', pady=(13, 0))
                    label(cell, '●  '+record[5], 10, PRIORITY[record[5]], height=18).grid(row=1, column=0, sticky='w')
                elif i == 3:
                    initials = ctk.CTkFrame(cell, fg_color='transparent')
                    initials.place(relx=0, rely=.5, anchor='w')
                    label(initials, record[6], 9, TEXT, width=27, height=27, fg_color=SOFT, corner_radius=14).pack(side='left', padx=(0, 6))
                    label(initials, record[7], 10).pack(side='left')
                elif i == 4:
                    bg, fg = STATUS[record[8]]
                    label(cell, record[8], 10, fg, True, height=23, width=78, fg_color=bg, corner_radius=12).place(relx=0, rely=.5, anchor='w')
                else:
                    label(cell, record[9], 10, MUTED).place(relx=0, rely=.5, anchor='w')
                    button(cell, '⋮', lambda r=record: self.record_detail(r), width=22, height=28, border_width=0, text_color=MUTED).place(x=88, rely=.5, anchor='w')
        if not records:
            label(self.rows, 'No se encontraron resultados o correos.', 13, MUTED).pack(pady=28)
        ctk.CTkFrame(self.rows, height=2, fg_color=LINE, corner_radius=0).pack(fill='x')

    @staticmethod
    def fit_subject(text, max_width):
        measure = font(13)
        if measure.measure(text) <= max_width:
            return text
        shortened = text.rstrip('.')
        while shortened and measure.measure(shortened + '…') > max_width:
            shortened = shortened[:-1]
        return shortened.rstrip() + '…'

    def record_detail(self, record):
        messagebox.showinfo(record[0], '\n'.join([record[2], 'Remitente: '+record[3], 'Área: '+record[4], 'Prioridad: '+record[5], 'Responsable: '+record[7], 'Estado: '+record[8], 'Fecha: '+record[9]]), parent=self)


if __name__ == '__main__':
    # El login pasa el nombre del usuario como argumento; las demás pantallas lo heredan por GI_USUARIO.
    if len(sys.argv) > 1:
        os.environ['GI_USUARIO'] = sys.argv[1]
    AppGestiónInstitucional().mainloop()