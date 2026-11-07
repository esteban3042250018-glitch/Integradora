import json
import os
from pathlib import Path
from tkinter import messagebox
from ui_helpers import *

QUEUE = [
    ('REC-1048', 'Solicitud de ampliación presupuestal', 'Secretaría de Finanzas', 'Alta', 'Hoy · 16:00'),
    ('REC-1051', 'Consulta sobre lineamientos de adquisiciones', 'Contraloría Interna', 'Alta', 'Hoy · 17:30'),
    ('REC-1050', 'Invitación a jornada de transparencia', 'Instituto de Acceso', 'Media', '07 oct 16:50'),
    ('REC-1049', 'Actualización del inventario institucional', 'Recursos Materiales', 'Normal', '09 oct 12:34'),
]


class DashboardApp(Shell):
    def __init__(self):
        super().__init__('Actualización')
        self.fields = {}
        self.settings_path = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'GestionInstitucional' / 'preferencias.json'
        self.selection = {r[0]: ctk.BooleanVar(value=(i == 0)) for i, r in enumerate(QUEUE)}
        self.unsaved = False
        self.protocol('WM_DELETE_WINDOW', self.close)
        content = ctk.CTkFrame(self.body, fg_color='transparent')
        content.pack(fill='x', padx=22, pady=20)
        header = ctk.CTkFrame(content, fg_color='transparent')
        header.pack(fill='x', pady=(0, 18))
        titles = ctk.CTkFrame(header, fg_color='transparent')
        titles.pack(side='left')
        label(titles, 'Actualizar', 28).pack(anchor='w')
        label(titles, 'Nombre del oficio', 13, MUTED).pack(anchor='w')
        button(header, '▣  Guardar cambios', self.save_changes, primary=True, width=165).pack(side='right', pady=8)
        upper = ctk.CTkFrame(content, fg_color='transparent')
        upper.pack(fill='x')
        upper.grid_columnconfigure(1, weight=1)
        prefs = card(upper, width=260, height=348)
        prefs.grid(row=0, column=0, sticky='nw', padx=(0, 20))
        prefs.grid_propagate(False)
        for i, (symbol, title) in enumerate([('▥', 'Preferencias institucionales'), ('#', 'Folios y consecutivos'), ('◷', 'Plazos de atención'), ('♢', 'Notificaciones'), ('◫', 'Horario de recepción'), ('✓', 'Seguridad'), ('▦', 'Integraciones')]):
            button(prefs, f'{symbol}   {title}', self.focus_form if i == 0 else lambda name=title: unavailable(self, name),
                fg_color=PINK if i == 0 else WHITE, text_color=ACCENT if i == 0 else TEXT,
                font=font(12, i == 0), border_width=0, anchor='w', height=42, corner_radius=8).pack(fill='x', padx=12, pady=(12 if i == 0 else 3, 3))
        queue = card(upper)
        queue.grid(row=0, column=1, sticky='nsew')
        queue_header = ctk.CTkFrame(queue, fg_color='transparent')
        queue_header.pack(fill='x', padx=20, pady=(16, 12))
        title_frame = ctk.CTkFrame(queue_header, fg_color='transparent')
        title_frame.pack(side='left')
        label(title_frame, 'Oficios', 18, bold=True).pack(anchor='w')
        self.selection_label = label(title_frame, '1 seleccionados de 7 documentos', 12, MUTED)
        self.selection_label.pack(anchor='w')
        button(queue_header, 'Revisar reglas de asignación', lambda: unavailable(self, 'Reglas de asignación'),
            height=30, width=177, border_width=0, text_color=ACCENT, font=font(12, True)).pack(side='right')
        controls = ctk.CTkFrame(queue, fg_color='transparent')
        controls.pack(fill='x', padx=20, pady=(0, 20))
        self.queue_search = entry(controls, '⌕  Buscar en la cola...', height=38, width=190, fg_color=SOFT, border_width=0)
        self.queue_search.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.area_filter = select(controls, ['Área sugerida'], lambda value: unavailable(self, 'Catálogo de áreas'), 113)
        self.area_filter.pack(side='left', padx=(0, 8))
        self.priority_filter = select(controls, ['Prioridad', 'Alta', 'Media', 'Normal'], lambda value: self.render_queue(), 88)
        self.priority_filter.pack(side='left', padx=(0, 8))
        button(controls, '⇄  Turnar', lambda: self.action_selected('Turnar'), width=94, height=42).pack(side='left', padx=(0, 8))
        button(controls, '✓  Asignar seleccionados', lambda: self.action_selected('Asignar seleccionados'), width=195, primary=True).pack(side='left')
        self.queue_rows = ctk.CTkFrame(queue, fg_color='transparent', corner_radius=0)
        self.queue_rows.pack(fill='x', padx=1)
        footer = ctk.CTkFrame(queue, fg_color='transparent')
        footer.pack(fill='x', padx=15, pady=12)
        self.queue_footer = label(footer, '1 seleccionados · 7 documentos pendientes', 10, MUTED)
        self.queue_footer.pack(side='left')
        pager = ctk.CTkFrame(footer, fg_color='transparent')
        pager.pack(side='right')
        for text in ['‹', '1', '2', '3', '›']:
            button(pager, text, self.render_queue if text == '1' else lambda: unavailable(self, 'Más documentos'), width=27, height=27, border_width=0,
                fg_color=ACCENT if text == '1' else WHITE, text_color=WHITE if text == '1' else MUTED, corner_radius=4, font=font(11)).pack(side='left')
        self.render_queue()
        self.queue_search.bind('<KeyRelease>', lambda event: self.render_queue())
        self.search_entry.bind('<KeyRelease>', lambda event: self.render_queue())
        form = card(self.body, height=500)
        form.pack(fill='x', padx=(0, 4), pady=(20, 36))
        form.pack_propagate(False)
        label(form, 'Actualizar Campos:', 18, bold=True).pack(anchor='w', padx=20, pady=(16, 0))
        label(form, 'Datos visibles en documentos, notificaciones y reportes', 12, MUTED).pack(anchor='w', padx=20)
        grid = ctk.CTkFrame(form, fg_color='transparent')
        grid.pack(fill='x', padx=20, pady=10)
        grid.grid_columnconfigure((0, 1), weight=1, uniform='fields')
        for i, (name, default, choices) in enumerate([
            ('Nombre de la institución', 'Gestión Institucional', ['Gestión Institucional']),
            ('Nombre del sistema', 'Control Documental', ['Control Documental']),
            ('Unidad responsable', 'Oficialía de Partes', ['Oficialía de Partes']),
            ('Zona horaria', 'Ciudad de México (UTC−6)', ['Ciudad de México (UTC−6)']),
            ('Formato de fecha', 'DD/MM/AAAA', ['DD/MM/AAAA', 'AAAA-MM-DD']),
            ('Prioridad', 'Normal', ['Normal', 'Media', 'Alta']),
            ('Asunto', '', None)]):
            field = ctk.CTkFrame(grid, fg_color='transparent')
            field.grid(row=i//2, column=i%2, columnspan=2 if i == 6 else 1, sticky='ew', padx=(0, 7) if i%2 == 0 and i != 6 else (7, 0) if i%2 else 0, pady=(0, 12))
            label(field, name, 11, TEXT, True, height=20).pack(anchor='w', pady=(0, 3))
            if choices:
                control = ctk.CTkComboBox(field, values=choices, height=40, corner_radius=7, border_width=1, border_color=LINE,
                    fg_color=WHITE, button_color=WHITE, button_hover_color=SOFT, text_color=MUTED, font=font(12),
                    dropdown_fg_color=WHITE, dropdown_text_color=TEXT, dropdown_hover_color=PINK,
                    command=lambda value: self.mark_dirty())
                control.set(default)
            else:
                control = entry(field, 'Descripción del asunto', height=40)
            control.pack(fill='x')
            control.bind('<KeyRelease>', lambda event: self.mark_dirty())
            self.fields[name] = control
        self.load_settings()

    def mark_dirty(self):
        self.unsaved = True

    def focus_form(self):
        self.body._parent_canvas.yview_moveto(1)
        self.fields['Nombre de la institución'].focus_set()

    def close(self):
        if not self.unsaved or messagebox.askyesno('Cambios sin guardar', '¿Cerrar sin guardar los cambios?', parent=self):
            self.destroy()

    def navigate(self, name):
        if name.startswith('Correspondencia') and self.unsaved:
            if not messagebox.askyesno('Cambios sin guardar', '¿Salir sin guardar los cambios?', parent=self):
                return
        if name == 'Actualización':
            self.focus_form()
        else:
            super().navigate(name)

    def selected_changed(self):
        self.render_queue()

    def render_queue(self):
        for child in self.queue_rows.winfo_children():
            child.destroy()
        query = (self.queue_search.get()+' '+self.search_entry.get()).casefold().split()
        records = [r for r in QUEUE if all(q in ' '.join(r).casefold() for q in query)
            and (self.priority_filter.get() == 'Prioridad' or r[3] == self.priority_filter.get())]
        widths = [130, 260, 190, 120, 140]
        # Anchos proporcionales: se conserva la tabla de cinco columnas al redimensionar.
        def row(background, height):
            frame = ctk.CTkFrame(self.queue_rows, fg_color=background, height=height, corner_radius=0)
            frame.pack(fill='x')
            frame.pack_propagate(False)
            return frame
        head = row(SOFT, 36)
        names = ['SELECCIÓN / FOLIO', 'ASUNTO', 'REMITENTE', 'PRIORIDAD', 'ÚLTIMA ACTUALIZACIÓN:']
        total = sum(widths)
        for i, name in enumerate(names):
            label(head, name, 9, MUTED, True, anchor='w').place(relx=sum(widths[:i])/total, x=14, rely=.5, anchor='w', relwidth=widths[i]/total-.02)
        for record in records:
            ctk.CTkFrame(self.queue_rows, height=2, corner_radius=0, fg_color=LINE).pack(fill='x')
            frame = row('#FFF9E8' if self.selection[record[0]].get() else WHITE, 64)
            check = ctk.CTkCheckBox(frame, text=record[0], variable=self.selection[record[0]], command=self.selected_changed,
                checkbox_width=12, checkbox_height=12, corner_radius=2, border_width=1, border_color='#555555',
                fg_color='#555555', hover_color=MUTED, text_color=TEXT, font=font(12), width=110)
            check.place(x=14, rely=.5, anchor='w')
            for i, value in enumerate(record[1:], 1):
                text = label(frame, value, 12, TEXT, i == 1, anchor='w', justify='left', wraplength=max(80, int(widths[i]*.85)))
                text.place(relx=sum(widths[:i])/total, x=14, rely=.5, anchor='w', relwidth=widths[i]/total-.025)
        if not records:
            label(self.queue_rows, 'No se encontraron resultados.', 12, MUTED).pack(pady=24)
        ctk.CTkFrame(self.queue_rows, height=2, corner_radius=0, fg_color=LINE).pack(fill='x')
        count = sum(v.get() for v in self.selection.values())
        self.selection_label.configure(text=f'{count} seleccionados de 7 documentos')
        if hasattr(self, 'queue_footer'):
            self.queue_footer.configure(text=f'{count} seleccionados · 7 documentos pendientes')

    def action_selected(self, name):
        if not any(v.get() for v in self.selection.values()):
            messagebox.showwarning(name, 'Selecciona al menos un oficio.', parent=self)
        else:
            unavailable(self, name)

    def load_settings(self):
        if not self.settings_path.exists():
            return
        try:
            data = json.loads(self.settings_path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('Formato de preferencias inválido')
            for name, control in self.fields.items():
                if isinstance(data.get(name), str):
                    if isinstance(control, ctk.CTkComboBox):
                        control.set(data[name])
                    else:
                        control.delete(0, 'end')
                        control.insert(0, data[name])
        except (OSError, ValueError) as error:
            messagebox.showwarning('Preferencias', f'No se pudieron leer las preferencias locales.\n{error}', parent=self)

    def save_changes(self):
        data = {name: control.get().strip() for name, control in self.fields.items()}
        for name, value in data.items():
            if name != 'Asunto' and not value:
                messagebox.showwarning('Guardar cambios', f'Completa el campo: {name}.', parent=self)
                self.fields[name].focus_set()
                return
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(self.settings_path)
        except OSError as error:
            messagebox.showerror('Guardar cambios', str(error), parent=self)
            return
        self.unsaved = False
        messagebox.showinfo('Guardar cambios', 'Cambios guardados en este equipo. No se enviaron a un servidor.', parent=self)


if __name__ == '__main__':
    DashboardApp().mainloop()
