from pathlib import Path
import re
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
from ui_helpers import *


class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        window_setup(self, '01 — Acceso | Gestión Institucional')
        self.minsize(1440, 900)
        self.grid_columnconfigure(0, weight=41, uniform='panels')
        self.grid_columnconfigure(1, weight=59, uniform='panels')
        self.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(self, fg_color=WINE, corner_radius=0)
        left.grid(row=0, column=0, sticky='nsew')
        right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        right.grid(row=0, column=1, sticky='nsew')
        ctk.CTkFrame(left, width=440, height=440, corner_radius=220, fg_color=WINE, border_width=70, border_color='#74203C').place(x=-180, rely=1, y=-280)
        brand(left, large=True).place(x=58, y=54)
        ring = ctk.CTkFrame(left, width=246, height=246, corner_radius=123,
            fg_color=WHITE, border_width=7, border_color=ACCENT)
        ring.place(x=58, y=168)
        circle = ring
        try:
            with Image.open(Path(__file__).resolve().parent / 'assets' / 'cvdr.jpg') as source:
                original = source.convert('RGB')
            self.logo_image = ctk.CTkImage(light_image=original, size=(184, 138))
            ctk.CTkLabel(circle, text='', image=self.logo_image).place(relx=.5, rely=.5, anchor='center')
        except OSError:
            label(circle, '[ Logo Institucional ]', 14, ACCENT, True).place(relx=.5, rely=.5, anchor='center')
        copy = ctk.CTkFrame(left, fg_color='transparent')
        copy.place(relx=.098, rely=.53, relwidth=.85)
        ctk.CTkFrame(copy, width=54, height=5, corner_radius=2, fg_color=GOLD).pack(anchor='w', pady=(0, 23))
        label(copy, 'Correspondencia clara,\natención oportuna.', 40, WHITE,
            justify='left', anchor='w').pack(anchor='w')
        label(copy, 'Centraliza el registro, turnado, seguimiento y archivo de la\ndocumentación institucional en un espacio seguro.',
            14, '#D6BDC7', justify='left', anchor='w').pack(anchor='w', pady=(20, 20))
        for text in ['Trazabilidad de cada movimiento', 'Alertas y plazos institucionales', 'Resguardo y consulta documental']:
            row = ctk.CTkFrame(copy, fg_color='transparent')
            row.pack(anchor='w', pady=6)
            label(row, '✓', 12, GOLD, True, width=22, height=22, fg_color=ACCENT, corner_radius=11).pack(side='left', padx=(0, 10))
            label(row, text, 12, WHITE).pack(side='left')
        label(left, '© 2026 Gestión Institucional · Acceso restringido', 10, '#C9A7B5').place(x=58, rely=.94)
        form = ctk.CTkFrame(right, fg_color='transparent', width=520)
        form.place(relx=.5, rely=.10, anchor='n')
        form.grid_columnconfigure(0, weight=1)
        label(form, 'Bienvenida', 36, TEXT, anchor='w').grid(row=0, column=0, sticky='w')
        label(form, 'Ingresa tus credenciales institucionales para continuar.', 14, MUTED).grid(row=1, column=0, sticky='w', pady=(2, 20))
        label(form, 'Correo institucional', 12, TEXT, True).grid(row=2, column=0, sticky='w')
        self.entry_correo = entry(form, '@   nombre@institucion.gob.mx', width=520, height=50)
        self.entry_correo.grid(row=3, column=0, sticky='ew', pady=(2, 12))
        pass_header = ctk.CTkFrame(form, fg_color='transparent')
        pass_header.grid(row=4, column=0, sticky='ew')
        label(pass_header, 'Contraseña', 12, TEXT, True).pack(side='left')
        button(pass_header, '¿Olvidaste tu contraseña?', lambda: unavailable(self, 'Recuperar contraseña'),
            border_width=0, fg_color='transparent', text_color=ACCENT, font=font(12, True), height=26, width=160).pack(side='right')
        password = ctk.CTkFrame(form, fg_color=WHITE, border_width=1, border_color=LINE, corner_radius=9)
        password.grid(row=5, column=0, sticky='ew', pady=(2, 10))
        self.entry_pass = entry(password, '◆  ••••••••••••', show='•', height=48, border_width=0)
        self.entry_pass.pack(side='left', fill='x', expand=True, padx=(2, 0))
        self.show_pass = button(password, '◉', self.toggle_password, width=42, height=40, border_width=0, text_color=MUTED)
        self.show_pass.pack(side='right', padx=4)
        self.remember = ctk.CTkCheckBox(form, text='Mantener mi sesión iniciada en este equipo',
            font=font(12), text_color=MUTED, checkbox_width=18, checkbox_height=18,
            fg_color=ACCENT, hover_color=WINE, border_color=LINE, corner_radius=4,
            command=self.remember_notice)
        self.remember.select()
        self.remember.grid(row=6, column=0, sticky='w', pady=(0, 20))
        button(form, 'Ingresar al sistema', self.accion_ingresar, primary=True, height=50).grid(row=7, column=0, sticky='ew')
        divider = ctk.CTkFrame(form, fg_color='transparent')
        divider.grid(row=8, column=0, sticky='ew', pady=21)
        for side in ('left', 'right'):
            ctk.CTkFrame(divider, height=2, width=203, corner_radius=0, fg_color=LINE).pack(side=side, pady=9)
        label(divider, 'O CONTINÚA CON', 10, '#9C96A1', height=18).pack()
        button(form, 'G   Iniciar sesión con Google', lambda: unavailable(self, 'Iniciar sesión con Google'), height=50).grid(row=9, column=0, sticky='ew')
        alert = ctk.CTkFrame(form, fg_color='#FFF8D8', border_color='#F0D36E', border_width=1, corner_radius=10)
        alert.grid(row=10, column=0, sticky='ew', pady=(24, 0))
        label(alert, '?', 16, '#775500', True).pack(side='left', padx=(16, 12), pady=9)
        label(alert, 'Si no puedes acceder, contacta a la Mesa de Servicio en la extensión 204.', 11, '#775500').pack(side='left', padx=(0, 12))
        label(right, '✓   Conexión segura · Tus credenciales están protegidas', 10, MUTED).place(relx=.19, rely=.92)
        self.bind('<Return>', lambda event: self.accion_ingresar())
        self.after(120, self.entry_correo.focus_set)

    def toggle_password(self):
        self.entry_pass.configure(show='' if self.entry_pass.cget('show') else '•')

    def remember_notice(self):
        if self.remember.get():
            messagebox.showinfo('Sesión de demostración', 'No se conservan sesiones ni contraseñas porque la autenticación todavía no está conectada.', parent=self)

    def accion_ingresar(self):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', self.entry_correo.get().strip()):
            messagebox.showwarning('Acceso', 'Escribe un correo institucional válido.', parent=self)
            self.entry_correo.focus_set()
            return
        if not self.entry_pass.get().strip():
            messagebox.showwarning('Acceso', 'Escribe tu contraseña.', parent=self)
            self.entry_pass.focus_set()
            return
        messagebox.showinfo('Acceso de demostración', 'Se abrirá la demostración. No hay autenticación conectada: las credenciales no se validan ni se guardan.', parent=self)
        self.entry_pass.delete(0, 'end')
        open_screen(self, 'home.py')


if __name__ == '__main__':
    LoginApp().mainloop()
