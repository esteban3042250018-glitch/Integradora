import os
import sys
import threading
from pathlib import Path

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))
import re
from datetime import date
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
from views.ui_helpers import *
import msal
import requests
from decouple import AutoConfig
from controller.app_paths import application_dir
from model.microsoft_auth import obtener_token_silencioso
from model.microsoft_mail import obtener_correos_graph
from model.document_store import (
    guardar_documento, max_folio_local, registrar_folio_local,
)
from controller.database_conecction import Database_connection
# Configuración de MSAL para Microsoft Entra ID
CLIENT_ID = AutoConfig(search_path=str(application_dir()))('MICROSOFT_AUTH_API', default='')
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["https://graph.microsoft.com/Mail.Read"]

msal_app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY) if CLIENT_ID else None
STATUS = {
    'Recibido': ('#E6F4EE', '#22865E'),
    'Por asignar': ('#FFF7D5', '#775500'), 
    'En atención': ('#EAF2FA', '#276C9E'),
    'Respondida': ('#E6F4EE', '#22865E'), 
    'Turnada': ('#F5E8EE', '#801537')
}
PRIORITY = {'Alta': ACCENT, 'Media': '#B78600', 'Normal': MUTED}





class AppGestiónInstitucional(Shell):
    def __init__(self, master):
        super().__init__(master, 'Correspondencia')
        self.category = 'all'
        self.records = []
        self._mail_loading = True
        self._actualizando_correos = False
        self._actualizacion_programada = None
        
        self.content = ctk.CTkFrame(self.body, fg_color='transparent')
        self.content.pack(fill='x', padx=22, pady=20)
        
        header = ctk.CTkFrame(self.content, fg_color='transparent')
        header.pack(fill='x', pady=(0, 18))
        heading = ctk.CTkFrame(header, fg_color='transparent')
        heading.pack(side='left')
        label(heading, 'Correspondencia (Correos de Microsoft)', 28).pack(anchor='w')
        label(heading, 'Bandeja de entrada sincronizada mediante Microsoft Graph', 13, MUTED).pack(anchor='w')
        
        button(header, '↻  Retomar borrador', self.retomar_borrador,
               width=175).pack(side='right', anchor='n', padx=(0, 10), pady=8)
        button(header, '↻  Actualizar correos', lambda: self.actualizar_correos(True),
               width=175).pack(side='right', anchor='n', padx=(0, 10), pady=8)
        button(header, '▤  Crear documento', self.crear_documento, primary=True, width=190).pack(side='right', anchor='n', pady=8)
        button(header, '✦  Registrar correspondencia', lambda: unavailable(self, 'Registrar correspondencia'), width=226).pack(side='right', anchor='n', padx=(0, 12), pady=8)
        
        metrics = ctk.CTkFrame(self.content, fg_color='transparent')
        metrics.pack(fill='x', pady=(0, 22))
        metrics.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform='metrics')
        
        total_registros = len(self.records)
        self.metric_value_labels = {}
        for index, (title, value, subtitle, color, soft, symbol, progress) in enumerate([
            ('CORREOS TOTALES', str(total_registros), 'Sincronizados', ACCENT, PINK, '▣', .56),
            ('POR ASIGNAR', '0', 'Pendientes', '#775500', '#FFF7D5', '♙', .32),
            ('EN SEGUIMIENTO', '0', 'Activos', BLUE, '#EAF2FA', '☷', .63),
            ('CONCLUIDOS', '0', 'Este mes', GREEN, '#E6F4EE', '✓', .68)]):
            
            tile = card(metrics, height=116)
            tile.grid(row=0, column=index, sticky='nsew', padx=(0, 16 if index < 3 else 0))
            tile.grid_propagate(False)
            tile.grid_columnconfigure(0, weight=1)
            label(tile, title, 10, MUTED, True, height=18).grid(row=0, column=0, sticky='w', padx=16, pady=(14, 0))
            amount = ctk.CTkFrame(tile, fg_color='transparent')
            amount.grid(row=1, column=0, sticky='w', padx=16)
            self.metric_value_labels[title] = label(amount, value, 32)
            self.metric_value_labels[title].pack(side='left')
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
        label(title, 'Correos con folio', 21).pack(anchor='w')
        self.mail_summary = label(
            title, 'Consultando correos con folio en Microsoft Graph...', 12, MUTED)
        self.mail_summary.pack(anchor='w')
        
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
        self.render_rows(self.records)
        self.after(100, lambda: self.actualizar_correos(True))

    def actualizar_correos(self, mostrar_error=False):
        if self._actualizando_correos or not self.winfo_exists():
            return
        if self._actualizacion_programada is not None:
            self.after_cancel(self._actualizacion_programada)
            self._actualizacion_programada = None
        self._actualizando_correos = True
        threading.Thread(
            target=self._cargar_correos, args=(mostrar_error,), daemon=True,
        ).start()

    def _cargar_correos(self, mostrar_error):
        try:
            records = obtener_correos_graph(self.usuario_email)
            error = None
        except Exception as excepcion:
            records = None
            error = str(excepcion)
        try:
            self.after(0, lambda: self._mostrar_correos(records, error, mostrar_error))
        except RuntimeError:
            pass

    def _mostrar_correos(self, records, error, mostrar_error):
        self._actualizando_correos = False
        self._mail_loading = False
        if error:
            self.mail_summary.configure(
                text='Error al consultar Microsoft Graph: ' + error.split('\n')[0]
            )
            if mostrar_error:
                messagebox.showerror('Microsoft Graph', error, parent=self)
        else:
            self.records = records
            por_asignar = sum(r[8] == 'Por asignar' for r in records)
            en_seguimiento = sum(r[8] in ('En atención', 'Turnada') for r in records)
            recibidos = sum(r[8] == 'Recibido' for r in records)
            coincidentes = sum(bool(r[10]) for r in records)
            self.metric_value_labels['CORREOS TOTALES'].configure(text=str(len(records)))
            self.metric_value_labels['POR ASIGNAR'].configure(text=str(por_asignar))
            self.metric_value_labels['EN SEGUIMIENTO'].configure(text=str(en_seguimiento))
            self.mail_summary.configure(
                text=(f'{len(records)} correos con folio · {recibidos} leídos' +
                      (f' · {coincidentes} con posible folio repetido' if coincidentes else ''))
                if records else 'Conexión Microsoft correcta · Sin mensajes con folio en la bandeja consultada'
            )
            self.nav_buttons['Correspondencia · 18'].configure(text=f'Correspondencia · {len(records)}')
            self.nav_buttons['Por asignar · 7'].configure(text=f'Por asignar · {por_asignar}')
            self.nav_buttons['Seguimiento · 12'].configure(text=f'Seguimiento · {en_seguimiento}')
            self.filter_rows()
        if self.winfo_exists():
            self._actualizacion_programada = self.after(60000, self.actualizar_correos)

    def on_show(self):
        super().on_show()
        if not self._mail_loading:
            self.actualizar_correos()

    def navigate(self, name):
        if name == 'Enviada':
            open_screen(self, 'enviados.py')
            return
        if name.startswith('Correspondencia'):
            self.category = 'all'
        elif name.startswith('Por asignar'):
            self.category = 'Por asignar'
        elif name.startswith('Seguimiento'):
            self.category = 'seguimiento'
        else:
            return super().navigate(name)
        self.filter_rows()

    def crear_documento(self):
        """Reserva un folio nuevo y abre el flujo: folio reservado → crear documento → PDF."""
        if not self.usuario_id:
            messagebox.showerror(
                'Crear documento',
                'No se encontró el identificador de tu cuenta de Microsoft. '
                'Cierra sesión y vuelve a iniciar sesión.',
                parent=self,
            )
            return
        try:
            folio = Database_connection().reservar_borrador(
                self.usuario_id,
                self.usuario,
                max_folio_local(date.today().year),
            )
            registrar_folio_local(folio)
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror('Crear documento', str(error), parent=self)
            return
        open_screen(self, 'folio_reservado.py', folio)

    def retomar_borrador(self):
        if not self.usuario_id:
            messagebox.showerror(
                'Retomar borrador',
                'No se encontró el identificador de tu cuenta de Microsoft. '
                'Cierra sesión y vuelve a iniciar sesión.',
                parent=self,
            )
            return
        try:
            borradores = Database_connection().listar_borradores(self.usuario_id)
        except (ConnectionError, RuntimeError) as error:
            messagebox.showerror('Retomar borrador', str(error), parent=self)
            return

        if not borradores:
            messagebox.showinfo(
                'Retomar borrador',
                'No tienes borradores pendientes.',
                parent=self,
            )
            return

        ventana = ctk.CTkToplevel(self)
        ventana.title('Retomar borrador')
        ventana.geometry('620x460')
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        label(ventana, 'Borradores pendientes', 21, TEXT, True).pack(
            anchor='w', padx=22, pady=(20, 12))
        lista = ctk.CTkScrollableFrame(ventana, fg_color='transparent')
        lista.pack(fill='both', expand=True, padx=14, pady=(0, 16))

        for borrador in borradores:
            actualizado = borrador['actualizado_en'].strftime('%d/%m/%Y %H:%M')
            asunto = borrador['asunto'] or 'Sin asunto'
            accion = (
                'Generar PDF' if borrador['estado'] == 'Creado'
                else 'Continuar borrador'
            )
            pantalla = (
                'folio_reservado.py' if borrador['estado'] == 'Creado'
                else 'crear_documento.py'
            )
            button(
                lista,
                f"{borrador['folio']}  ·  {asunto}  ·  {accion}\n"
                f"Actualizado: {actualizado}",
                lambda folio=borrador['folio'], estado=borrador['estado'],
                archivo=pantalla: self._abrir_borrador(
                    ventana, folio, estado, archivo,
                ),
                height=58,
                anchor='w',
            ).pack(fill='x', padx=6, pady=5)

    def _abrir_borrador(self, ventana, folio, estado, pantalla):
        try:
            registrar_folio_local(folio)
            if estado == 'Creado':
                borrador = Database_connection().obtener_borrador(
                    folio, self.usuario_id)
                if borrador is None:
                    raise ValueError(
                        'No se encontró el contenido guardado para este folio.'
                    )
                guardar_documento(
                    borrador['asunto'],
                    borrador['area_emisora'],
                    borrador['recepcion'],
                    borrador['cuerpo'],
                    folio=folio,
                )
        except (ConnectionError, OSError, RuntimeError, ValueError) as error:
            messagebox.showerror('Retomar documento', str(error), parent=self)
            return
        ventana.destroy()
        open_screen(self, pantalla, folio)

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
        records = self.matching(self.records, query, self.state_filter.get(), self.priority_filter.get(), self.category)
        self.render_rows(records)
        filtered = query.strip() or self.state_filter.get() != 'Estado' or self.priority_filter.get() != 'Prioridad' or self.category != 'all'
        self.count_label.configure(text=f'{len(records)} resultados encontrados' if filtered else f'Mostrando {len(self.records)} registros')

    def render_rows(self, records):
        for child in self.rows.winfo_children():
            child.destroy()
        widths = [154, 236, 116, 202, 118, 104]
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
                cell = ctk.CTkFrame(row, fg_color='transparent', width=widths[i]-16, height=91)
                cell.grid(row=0, column=i, sticky='nsew', padx=8)
                cell.grid_propagate(False)
                cell.grid_columnconfigure(0, weight=1)
                if i == 0:
                    label(cell, record[0], 11, ACCENT, height=30, wraplength=145,
                          justify='left', anchor='w').grid(row=0, column=0, sticky='w', pady=(5, 0))
                    label(cell, record[1], 10, '#9A94A0', True, height=15).grid(row=1, column=0, sticky='w')
                    if len(record) > 11 and record[10]:
                        button(cell, f'⚠ Repetido ({record[11]})',
                               lambda r=record: self.record_detail(r),
                               width=136, height=21, corner_radius=5,
                               border_width=0, fg_color='#FFF4D9',
                               text_color='#A34C09', font=font(10, True)).grid(
                                   row=2, column=0, sticky='w')
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
                    label(initials, record[7], 10, anchor='w', justify='left',
                          wraplength=146, width=150, height=58).pack(side='left')
                elif i == 4:
                    bg, fg = STATUS[record[8]]
                    label(cell, record[8], 10, fg, True, height=23, width=78, fg_color=bg, corner_radius=12).place(relx=0, rely=.5, anchor='w')
                else:
                    label(cell, record[9], 10, MUTED).place(relx=0, rely=.5, anchor='w')
                    button(cell, '⋮', lambda r=record: self.record_detail(r), width=22, height=28, border_width=0, text_color=MUTED).place(x=88, rely=.5, anchor='w')
        if not records:
            empty_text = (
                'Cargando correos...' if self._mail_loading
                else 'No se encontraron resultados o correos.'
            )
            label(self.rows, empty_text, 13, MUTED).pack(pady=28)
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
        detalles = [record[2], 'Remitente: ' + record[3],
                    'Correo: ' + (record[13] if len(record) > 13 else ''),
                    'Área: ' + record[4], 'Prioridad: ' + record[5],
                    'Responsable: ' + record[7], 'Estado: ' + record[8],
                    'Fecha de recepción: ' + (record[12] if len(record) > 12 else record[9])]
        if len(record) > 11 and record[10]:
            detalles.extend(['', '⚠ Posible folio repetido: ' + record[11] +
                             ' correos comparten este folio.',
                             'Revisa remitentes, asuntos y documentos antes de registrarlos.'])
        messagebox.showinfo(record[0], '\n'.join(detalles), parent=self)
