from pathlib import Path
import re
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
import sys
from pathlib import Path

<<<<<<< HEAD
VIEWS = Path(__file__).resolve().parent   # carpeta "views" (aquí vive ui_helpers.py)
RAIZ = VIEWS.parent                        # carpeta "codigo"
for ruta in (RAIZ, VIEWS):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))
=======
RAIZ = Path(__file__).resolve().parent.parent  # carpeta "codigo"
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
>>>>>>> 8343474b4b8d1b842960ee1c4d06b1e2e5cd2c67
from ui_helpers import *
import msal
from model.microsoft_auth import iniciar_sesion_interactivo
import requests
from decouple import config

# Configuración de MSAL para Microsoft Entra ID
CLIENT_ID = config('MICROSOFT_AUTH_API')
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["https://graph.microsoft.com/Mail.Read"]

msal_app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        window_setup(self, '01 — Acceso | Gestión Institucional')
        self.minsize(1440, 900)
        self.grid_columnconfigure(0, weight=41, uniform='panels')
        self.grid_columnconfigure(1, weight=59, uniform='panels')
        self.grid_rowconfigure(0, weight=1)

        # Panel Izquierdo
        left = ctk.CTkFrame(self, fg_color=WINE, corner_radius=0)
        left.grid(row=0, column=0, sticky='nsew')
        
        # Panel Derecho
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

        # Panel del Formulario (Derecho)
        form = ctk.CTkFrame(right, fg_color='transparent', width=520)
        form.place(relx=.5, rely=.25, anchor='n')
        form.grid_columnconfigure(0, weight=1)

        label(form, 'Bienvenida', 36, TEXT, anchor='w').grid(row=0, column=0, sticky='w')
        label(form, 'Inicia sesión con tu cuenta institucional para continuar.', 14, MUTED).grid(row=1, column=0, sticky='w', pady=(2, 40))

        # Botón principal de Iniciar Sesión con Microsoft
        self.btn_microsoft = button(
            form, 
            '❖   Iniciar sesión con Microsoft', 
            self.iniciar_sesion_microsoft, 
            primary=True, 
            height=52
        )
        self.btn_microsoft.grid(row=2, column=0, sticky='ew', pady=(10, 20))

        # Alerta informativa inferior
        alert = ctk.CTkFrame(form, fg_color='#FFF8D8', border_color='#F0D36E', border_width=1, corner_radius=10)
        alert.grid(row=3, column=0, sticky='ew', pady=(40, 0))
        label(alert, '?', 16, '#775500', True).pack(side='left', padx=(16, 12), pady=9)
        label(alert, 'Si no puedes acceder, contacta a la Mesa de Servicio en la extensión 204.', 11, '#775500').pack(side='left', padx=(0, 12))

        label(right, '✓   Conexión segura · Tus credenciales están protegidas', 10, MUTED).place(relx=.19, rely=.92)

    # (En tu clase LoginApp, dentro de la función del botón de Microsoft)

    def iniciar_sesion_microsoft(self):
        self.btn_microsoft.configure(state='disabled', text='Autenticando...')

        def background_task():
            try:
                result = iniciar_sesion_interactivo()
                if "access_token" in result:
                    nombre = result.get("id_token_claims", {}).get("name", "Usuario")
                    self.after(0, lambda: self.abrir_home(nombre))
                else:
                    error = result.get("error_description", "Error desconocido")
                    self.after(0, lambda: messagebox.showerror("Error", error, parent=self))
            finally:
                self.after(0, lambda: self.btn_microsoft.configure(state='normal', text='❖   Iniciar sesión con Microsoft'))

        import threading
        threading.Thread(target=background_task, daemon=True).start()

    def abrir_home(self, nombre_usuario):
        
        open_screen(self, 'home.py', extra_args=[nombre_usuario]) # O el nombre de tu archivo home


if __name__ == '__main__':
    LoginApp().mainloop()
