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
from model.microsoft_mail import marcar_correo_leido, obtener_correos_graph
from model.document_store import (
    guardar_documento, max_folio_local, registrar_folio_local,
)
from controller.database_connection import Database_connection
STATUS = {
    'Recibido': ('#E6F4EE', '#22865E'),
    'No leído': ('#FFF7D5', '#775500'),
    'En atención': ('#EAF2FA', '#276C9E'),
    'Respondida': ('#E6F4EE', '#22865E'), 
    'Turnada': ('#F5E8EE', '#801537')
}
PRIORITY = {'Alta': ACCENT, 'Media': '#B78600', 'Normal': MUTED}





class AppGestiónInstitucional(Shell):
    def __init__(self, master):
        super().__init__(master, 'Correspondencia')
        self.category = 'con_folio'
        self.records = []
        self._mail_loading = True
        self._actualizando_correos = False
        self._actualizacion_programada = None
        
        self.content = ctk.CTkFrame(self.body, fg_color='transparent')
        self.content.pack(fill='both', expand=True, padx=30, pady=24)
        
        header = ctk.CTkFrame(self.content, fg_color='transparent')
        header.pack(fill='x', pady=(0, 22))
        logo = image('cvdr.jpg', 76)
        if logo is not None:
            self.logo_image = logo
            ctk.CTkLabel(header, image=self.logo_image, text='').pack(
                side='left', padx=(0, 16))
        heading = ctk.CTkFrame(header, fg_color='transparent')
        heading.pack(side='left')
        label(heading, 'Correspondencia', 30).pack(anchor='w')
        label(heading, 'Bandeja general de correos recibidos', 15, MUTED).pack(anchor='w')
        
        button(header, '↻  Retomar borrador', self.retomar_borrador,
               width=190, height=46).pack(side='right', anchor='n', padx=(0, 12), pady=10)
        button(header, '↻  Actualizar correos', lambda: self.actualizar_correos(True),
               width=190, height=46).pack(side='right', anchor='n', padx=(0, 12), pady=10)
        button(header, '✦  Crear oficio', self.crear_documento, primary=True,
               width=200, height=46).pack(side='right', anchor='n', pady=10)
        
        metrics = ctk.CTkFrame(self.content, fg_color='transparent')
        metrics.pack(fill='x', pady=(0, 22))
        metrics.grid_columnconfigure((0, 1, 2), weight=1, uniform='metrics')
        
        self.metric_value_labels = {}
        for index, (title, value, subtitle, color, soft, symbol) in enumerate([
            ('CORREOS TOTALES', '0', 'En el buzón', ACCENT, PINK, '▣'),
            ('NO LEÍDOS', '0', 'Pendientes de revisar', BLUE, '#EAF2FA', '◷'),
            ('EN SEGUIMIENTO', '0', 'Activos', GREEN, '#E6F4EE', '✓')]):
            
            tile = card(metrics, height=124)
            tile.grid(row=0, column=index, sticky='nsew', padx=(0, 18 if index < 2 else 0))
            tile.grid_propagate(False)
            tile.grid_columnconfigure(0, weight=1)
            label(tile, title, 12, MUTED, True, height=20).grid(row=0, column=0, sticky='w', padx=20, pady=(16, 0))
            amount = ctk.CTkFrame(tile, fg_color='transparent')
            amount.grid(row=1, column=0, sticky='w', padx=20, pady=(0, 3))
            self.metric_value_labels[title] = label(amount, value, 34)
            self.metric_value_labels[title].pack(side='left')
            label(amount, subtitle, 12, color).pack(side='left', padx=(14, 0), pady=(10, 0))
            label(tile, symbol, 24, color, width=42, height=42, fg_color=soft, corner_radius=12).place(relx=1, x=-20, y=18, anchor='ne')
            
        self.table_card = card(self.content)
        self.table_card.pack(fill='both', expand=True)
        
        table_top = ctk.CTkFrame(self.table_card, fg_color='transparent')
        table_top.pack(fill='x', padx=24, pady=(20, 12))
        title = ctk.CTkFrame(table_top, fg_color='transparent')
        title.pack(side='left')
        label(title, 'Correspondencia reciente', 23).pack(anchor='w')
        self.mail_summary = label(
            title, 'Consultando la bandeja de Microsoft...', 14, MUTED)
        self.mail_summary.pack(anchor='w')
        
        button(table_top, 'Ver toda la correspondencia  →', self.reset_filters,
               border_width=0, text_color=ACCENT, height=38, width=220,
               font=font(13, True)).pack(side='right')
            
        filters = ctk.CTkFrame(self.table_card, fg_color='transparent')
        filters.pack(fill='x', padx=24, pady=(0, 16))
        
        self.filter_entry = entry(filters, '⌕  Filtrar esta bandeja...', fg_color=SOFT, border_width=0, height=40)
        self.filter_entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.state_filter = select(filters, ['Estado', *STATUS], lambda value: self.filter_rows(), 142)
        self.state_filter.pack(side='left', padx=(0, 8))
        self.priority_filter = select(filters, ['Prioridad', 'Alta', 'Media', 'Normal'], lambda value: self.filter_rows(), 142)
        self.priority_filter.pack(side='left', padx=(0, 8))
        
        button(filters, '☷  Más filtros  ⌄', lambda: unavailable(self, 'Más filtros'),
               width=150, height=40, font=font(12)).pack(side='left')
        
        self.rows = ctk.CTkScrollableFrame(
            self.table_card, fg_color=WHITE, corner_radius=0,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=WINE)
        self.rows.pack(fill='both', expand=True, padx=1)
        
        footer = ctk.CTkFrame(self.table_card, fg_color='transparent')
        footer.pack(fill='x', padx=22, pady=12)
        self.count_label = label(footer, 'Mostrando 0 registros', 12, MUTED)
        self.count_label.pack(side='left')
        
        paging = ctk.CTkFrame(footer, fg_color='transparent')
        paging.pack(side='right')
        
        for text in ['‹', '1', '›']:
            button(paging, text, self.reset_filters, width=34, height=32,
                fg_color=ACCENT if text == '1' else WHITE, text_color=WHITE if text == '1' else MUTED,
                border_width=0, corner_radius=6, font=font(12)).pack(side='left', padx=3)
                
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
            self._actualizar_metricas_correos()
            self.filter_rows()
        if self.winfo_exists():
            self._actualizacion_programada = self.after(60000, self.actualizar_correos)

    def on_show(self):
        super().on_show()
        if not self._mail_loading:
            self.actualizar_correos()

    def _actualizar_metricas_correos(self):
        no_leidos = sum(r[8] == 'No leído' for r in self.records)
        en_seguimiento = sum(r[8] in ('En atención', 'Turnada') for r in self.records)
        recibidos = sum(r[8] == 'Recibido' for r in self.records)
        con_folio = sum(bool(r[0]) for r in self.records)
        coincidentes = sum(bool(r[10]) for r in self.records)
        self.metric_value_labels['CORREOS TOTALES'].configure(
            text=str(len(self.records)))
        self.metric_value_labels['NO LEÍDOS'].configure(text=str(no_leidos))
        self.metric_value_labels['EN SEGUIMIENTO'].configure(
            text=str(en_seguimiento))
        self.mail_summary.configure(
            text=(f'{len(self.records)} correos en bandeja · {con_folio} con folio · '
                  f'{recibidos} leídos' +
                  (f' · {coincidentes} con posible folio repetido'
                   if coincidentes else ''))
            if self.records else
            'Conexión Microsoft correcta · Sin mensajes en la bandeja consultada'
        )
        self.nav_buttons['Correspondencia'].configure(
            text=f'Correspondencia · {len(self.records)}')
        self.nav_buttons['No leídos'].configure(
            text=f'No leídos · {no_leidos}')
        self.nav_buttons['Seguimiento'].configure(
            text=f'Seguimiento · {en_seguimiento}')

    def _marcar_correo_leido(self, record):
        if record[8] != 'No leído' or len(record) <= 14 or not record[14]:
            return
        threading.Thread(
            target=self._actualizar_estado_correo,
            args=(record[14],),
            daemon=True,
        ).start()

    def _actualizar_estado_correo(self, message_id):
        try:
            marcar_correo_leido(self.usuario_email, message_id)
        except Exception as error:
            try:
                self.after(0, lambda error=error: messagebox.showerror(
                    'Estado del correo',
                    f'No se pudo marcar el mensaje como leído.\n\n{error}',
                    parent=self,
                ))
            except RuntimeError:
                pass
            return
        try:
            self.after(0, lambda: self._mostrar_correo_leido(message_id))
        except RuntimeError:
            pass

    def _mostrar_correo_leido(self, message_id):
        self.records = [
            record[:8] + ('Recibido',) + record[9:]
            if len(record) > 14 and record[14] == message_id else record
            for record in self.records
        ]
        self._actualizar_metricas_correos()
        self.filter_rows()

    def navigate(self, name):
        if name == 'Enviada':
            open_screen(self, 'enviados.py')
            return
        if name.startswith('Correspondencia'):
            self.category = 'all'
        elif name.startswith('No leídos'):
            self.category = 'No leído'
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
            and (category == 'all' or (category == 'con_folio' and bool(r[0]))
                 or r[8] == category or (category == 'seguimiento' and r[8] in ('En atención', 'Turnada'))
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
        widths = [125, 295, 175, 145, 130, 120]

        def row_frame(background, height):
            frame = ctk.CTkFrame(
                self.rows, fg_color=background, corner_radius=0,
                height=height)
            frame.pack(fill='x')
            frame.pack_propagate(False)
            frame.grid_propagate(False)
            for index, width in enumerate(widths):
                frame.grid_columnconfigure(
                    index, minsize=width, weight=1 if index == 1 else 0)
            frame.grid_rowconfigure(0, weight=1)
            return frame

        head = row_frame(SOFT, 42)
        columns = (
            'FOLIO', 'ASUNTO / REMITENTE', 'ÁREA / PRIORIDAD',
            'RESPONSABLE', 'ESTADO', 'FECHA',
        )
        for index, name in enumerate(columns):
            label(head, name, 11, MUTED, True, anchor='w').grid(
                row=0, column=index, sticky='w', padx=10)

        for record in records:
            row = row_frame(WHITE, 72)
            folio = ctk.CTkFrame(row, fg_color='transparent')
            folio.grid(row=0, column=0, sticky='nsew', padx=10, pady=8)
            label(folio, record[0] or 'Sin folio', 12, ACCENT, True,
                  anchor='w').pack(anchor='w')
            label(folio, record[1], 10, MUTED, True,
                  anchor='w').pack(anchor='w', pady=(3, 0))
            if len(record) > 11 and record[10]:
                button(
                    folio, f'⚠ Repetido ({record[11]})',
                    lambda r=record: self.record_detail(r),
                    width=132, height=25, corner_radius=6,
                    border_width=0, fg_color='#FFF4D9',
                    text_color='#A34C09', font=font(10, True),
                ).pack(anchor='w', pady=(3, 0))

            subject = ctk.CTkFrame(row, fg_color='transparent')
            subject.grid(row=0, column=1, sticky='nsew', padx=10, pady=8)
            label(subject, self.fit_subject(record[2], widths[1] - 32),
                  14, TEXT, anchor='w').pack(anchor='w')
            label(subject, record[3], 12, MUTED,
                  anchor='w').pack(anchor='w', pady=(4, 0))

            area = ctk.CTkFrame(row, fg_color='transparent')
            area.grid(row=0, column=2, sticky='nsew', padx=10, pady=8)
            label(area, record[4], 12, TEXT, anchor='w',
                  wraplength=widths[2] - 28, justify='left').pack(anchor='w')
            label(area, '●  ' + record[5], 11, PRIORITY[record[5]],
                  anchor='w').pack(anchor='w', pady=(4, 0))

            responsible = ctk.CTkFrame(row, fg_color='transparent')
            responsible.grid(row=0, column=3, sticky='nsew', padx=10)
            label(responsible, record[6], 11, TEXT, True, width=32, height=32,
                  fg_color=SOFT, corner_radius=16).pack(side='left', padx=(0, 8))
            label(responsible, record[7], 12, TEXT).pack(side='left')

            status = ctk.CTkFrame(row, fg_color='transparent')
            status.grid(row=0, column=4, sticky='nsew', padx=10)
            status_bg, status_fg = STATUS[record[8]]
            label(status, record[8], 11, status_fg, True, height=26,
                  fg_color=status_bg, corner_radius=13).place(
                      relx=0, rely=.5, anchor='w')

            date_cell = ctk.CTkFrame(row, fg_color='transparent')
            date_cell.grid(row=0, column=5, sticky='nsew', padx=10)
            label(date_cell, record[9], 12, MUTED,
                  anchor='w').place(relx=0, rely=.5, anchor='w')
            button(
                date_cell, '⋮', lambda r=record: self.record_detail(r),
                width=30, height=32, border_width=0, text_color=ACCENT,
            ).place(relx=1, rely=.5, anchor='e')
            ctk.CTkFrame(
                self.rows, height=1, fg_color=LINE, corner_radius=0,
            ).pack(fill='x', padx=10)
        if not records:
            empty_text = (
                'Cargando correos...' if self._mail_loading
                else 'No se encontraron resultados o correos.'
            )
            label(self.rows, empty_text, 15, MUTED).pack(pady=36)

    @staticmethod
    def fit_subject(text, max_width):
        measure = font(14)
        if measure.measure(text) <= max_width:
            return text
        shortened = text.rstrip('.')
        while shortened and measure.measure(shortened + '…') > max_width:
            shortened = shortened[:-1]
        return shortened.rstrip() + '…'

    def record_detail(self, record):
        self._marcar_correo_leido(record)
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
