import ctypes
import queue
import sys
import threading
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
import requests
from msal.exceptions import MsalError
from PIL import Image, ImageDraw

VIEWS = Path(__file__).resolve().parent   # carpeta "views" (aquí vive ui_helpers.py)
RAIZ = VIEWS.parent                        # carpeta "codigo"
for ruta in (RAIZ, VIEWS):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

from views.ui_helpers import *
from controller.app_paths import resource_path
from model.microsoft_auth import iniciar_sesion_interactivo


def _autenticar(cancel_event):
    try:
        return iniciar_sesion_interactivo(cancel_event=cancel_event), None
    except (MsalError, OSError, requests.RequestException, RuntimeError, ValueError) as error:
        return None, error


class LoginApp(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.winfo_toplevel().title('01 — Acceso | Gestión Institucional')
        self.grid_columnconfigure(0, weight=41, uniform='panels')
        self.grid_columnconfigure(1, weight=59, uniform='panels')
        self.grid_rowconfigure(0, weight=1)

        self._auth_dialog = None
        self._auth_status_lbl = None
        self._auth_cancel_btn = None
        self._cancel_event = None

        left = ctk.CTkFrame(self, fg_color=WINE, corner_radius=0)
        left.grid(row=0, column=0, sticky='nsew')
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)
        left.grid_rowconfigure(7, weight=1)

        right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        right.grid(row=0, column=1, sticky='nsew')

        content = ctk.CTkFrame(left, fg_color='transparent')
        content.grid(row=0, column=0, sticky='nsew', padx=42, pady=38)
        content.grid_columnconfigure(0, weight=1)

        logo = ctk.CTkFrame(
            content, width=120, height=120, fg_color='transparent',
            corner_radius=0,
        )
        logo.grid(row=0, column=0, sticky='w', pady=(0, 24))
        logo.grid_propagate(False)

        try:
            with Image.open(resource_path('views', 'assets', 'cvdr.jpg')) as source:
                original = source.convert('RGBA')
            width, height = original.size
            side = max(width, height)
            canvas = Image.new('RGBA', (side, side), (255, 255, 255, 255))
            canvas.paste(
                original, ((side - width) // 2, (side - height) // 2),
                mask=original,
            )
            canvas = canvas.resize((120, 120), Image.Resampling.LANCZOS)
            mask = Image.new('L', (120, 120), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 119, 119), fill=255)
            canvas.putalpha(mask)
            self.logo_image = ctk.CTkImage(
                light_image=canvas, dark_image=canvas, size=(120, 120))
            ctk.CTkLabel(
                logo, image=self.logo_image, text='', fg_color='transparent',
            ).place(relx=.5, rely=.5, anchor='center')
        except OSError:
            label(
                logo, 'CVDR', 30, WHITE, True,
            ).place(relx=.5, rely=.5, anchor='center')

        label(
            content,
            'CENTRO DE VINCULACIÓN Y DE DESARROLLO\nREGIONAL',
            20, WHITE, True, justify='left', anchor='w',
        ).grid(row=1, column=0, sticky='w')
        label(
            content,
            'Una plataforma centralizada para facilitar la administración, '
            'organización y seguimiento de los procesos institucionales.',
            16, '#E8DCE1', wraplength=470, justify='left', anchor='w',
        ).grid(row=2, column=0, sticky='w', pady=(16, 0))

        ctk.CTkFrame(
            content, width=72, height=3, corner_radius=2, fg_color='#C58A9E',
        ).grid(row=3, column=0, sticky='w', pady=(24, 22))

        for index, text in enumerate((
            'Acceso organizado a las herramientas',
            'Información centralizada',
            'Interfaz sencilla y consistente',
        )):
            item = ctk.CTkFrame(content, fg_color='transparent')
            item.grid(row=4 + index, column=0, sticky='w', pady=5)
            label(item, '✓', 17, WHITE, True, width=30).pack(side='left')
            label(item, text, 14, '#F2E9ED', anchor='w').pack(side='left')

        label(
            content, 'PLATAFORMA ADMINISTRATIVA',
            11, '#CBAAB7', True, anchor='w',
        ).grid(row=8, column=0, sticky='sw', pady=(28, 0))

        form = ctk.CTkFrame(right, fg_color='transparent', width=370)
        form.place(relx=.5, rely=.5, anchor='center')
        form.grid_columnconfigure(0, weight=1)

        label(form, 'Bienvenido', 40, TEXT, True, anchor='w').grid(
            row=0, column=0, sticky='ew')
        label(
            form, 'Iniciar sesión', 16, MUTED, anchor='w',
        ).grid(row=1, column=0, sticky='ew', pady=(8, 30))

        form_card = card(form)
        form_card.grid(row=2, column=0, sticky='ew')
        form_card.grid_columnconfigure(0, weight=1)
        button_area = ctk.CTkFrame(form_card, fg_color='transparent')
        button_area.pack(fill='both', expand=True, padx=24, pady=24)
        button_area.grid_columnconfigure(0, weight=1)

        self.btn_microsoft = button(
            button_area, 'Ingresar al sistema',
            self.iniciar_sesion_microsoft, primary=True, height=56,
            corner_radius=9, font=font(16, True),
        )
        self.btn_microsoft.grid(row=0, column=0, sticky='ew')

    # ---------------------------------------------------------
    # DIÁLOGO DE ESPERA Y FLUJO DE AUTENTICACIÓN
    # ---------------------------------------------------------
    def _traer_al_frente(self):
        root = self.winfo_toplevel()
        root.deiconify()
        root.lift()
        root.attributes('-topmost', True)
        root.after(200, lambda: root.attributes('-topmost', False))
        root.focus_force()
        try:
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _abrir_dialogo_espera(self):
        self._cerrar_dialogo_espera()
        root = self.winfo_toplevel()

        dlg = ctk.CTkToplevel(root)
        dlg.title('Inicio de sesión')
        dlg.configure(fg_color=BG)
        dlg.resizable(False, False)
        dlg.transient(root)
        dlg.grab_set()
        dlg.protocol('WM_DELETE_WINDOW', self._cancelar_autenticacion)

        ancho, alto = 380, 175
        root.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() - ancho) // 2
        y = root.winfo_rooty() + (root.winfo_height() - alto) // 2
        dlg.geometry(f'{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}')

        contenedor = card(dlg)
        contenedor.pack(fill='both', expand=True, padx=16, pady=16)

        self._auth_status_lbl = label(
            contenedor,
            'Esperando inicio de sesión en Microsoft…',
            15, TEXT, True, wraplength=320, justify='center',
        )
        self._auth_status_lbl.pack(expand=True, pady=(18, 10), padx=16)

        self._auth_cancel_btn = button(
            contenedor,
            'Cancelar',
            self._cancelar_autenticacion,
            primary=False,
            height=36,
            width=130,
        )
        self._auth_cancel_btn.pack(pady=(0, 16))

        self._auth_dialog = dlg

    def _cerrar_dialogo_espera(self):
        if self._auth_dialog is not None and self._auth_dialog.winfo_exists():
            try:
                self._auth_dialog.grab_release()
            except Exception:
                pass
            self._auth_dialog.destroy()
        self._auth_dialog = None
        self._auth_status_lbl = None
        self._auth_cancel_btn = None

    def _cancelar_autenticacion(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._cerrar_dialogo_espera()
        self.btn_microsoft.configure(state='normal', text='Ingresar al sistema')

    def iniciar_sesion_microsoft(self):
        self.btn_microsoft.configure(state='disabled', text='Autenticando...')
        self._cancel_event = threading.Event()
        self._abrir_dialogo_espera()

        cancel_event = self._cancel_event
        outcomes = queue.Queue()

        def background_task():
            outcomes.put(_autenticar(cancel_event))

        threading.Thread(target=background_task, daemon=True).start()
        self.after(100, self._comprobar_autenticacion, outcomes, cancel_event)

    def _comprobar_autenticacion(self, outcomes, cancel_event):
        if cancel_event.is_set():
            return

        try:
            result, error = outcomes.get_nowait()
        except queue.Empty:
            self.after(100, self._comprobar_autenticacion, outcomes, cancel_event)
            return

        if cancel_event.is_set():
            return

        if error is not None:
            self._cerrar_dialogo_espera()
            self.btn_microsoft.configure(state='normal', text='Ingresar al sistema')
            messagebox.showerror('Error de autenticación', str(error), parent=self)
            return

        if not result or 'access_token' not in result:
            self._cerrar_dialogo_espera()
            self.btn_microsoft.configure(state='normal', text='Ingresar al sistema')
            detail = (result or {}).get(
                'error_description', 'Microsoft no devolvió un token de acceso.')
            messagebox.showerror('Error de autenticación', detail, parent=self)
            return

        claims = result.get('id_token_claims') or {}
        nombre = claims.get('name', 'Usuario')
        tenant_id = claims.get('tid')
        object_id = claims.get('oid')
        usuario_id = (
            f'{tenant_id}:{object_id}'
            if tenant_id and object_id
            else claims.get('preferred_username')
            or claims.get('email')
            or claims.get('sub')
        )
        usuario_id = str(usuario_id).strip().casefold() if usuario_id else ''
        if not usuario_id:
            self._cerrar_dialogo_espera()
            self.btn_microsoft.configure(state='normal', text='Ingresar al sistema')
            messagebox.showerror(
                'Identidad de Microsoft',
                'Microsoft no devolvió un identificador de cuenta. '
                'No se puede asociar el borrador al empleado.',
                parent=self,
            )
            return

        usuario_email = (
            claims.get('preferred_username')
            or claims.get('upn')
            or claims.get('email')
        )

        # Traer la ventana de la app al frente encima de cualquier ventana
        self._traer_al_frente()

        # Cambiar estado del diálogo a "Sesión iniciada" y pasar al home
        if self._auth_dialog is not None and self._auth_dialog.winfo_exists():
            if self._auth_status_lbl is not None:
                self._auth_status_lbl.configure(text='Sesión iniciada', text_color='#1E7E34')
            if self._auth_cancel_btn is not None:
                self._auth_cancel_btn.pack_forget()
            self.after(900, lambda: self._completar_acceso(nombre, usuario_id, usuario_email))
        else:
            self._completar_acceso(nombre, usuario_id, usuario_email)

    def _completar_acceso(self, nombre, usuario_id, usuario_email):
        self._cerrar_dialogo_espera()
        self.btn_microsoft.configure(state='normal', text='Ingresar al sistema')
        self.abrir_home(nombre, usuario_id, usuario_email)

    def abrir_home(self, nombre_usuario, usuario_id, usuario_email=None):
        open_screen(
            self, 'home.py',
            extra_args=[nombre_usuario, usuario_id, usuario_email or ''],
        )