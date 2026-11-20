import os
import sys
from tkinter import messagebox

import customtkinter as ctk

from views.applogin import LoginApp
from views.ui_helpers import BG, window_setup


class GestionInstitucionalApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        window_setup(self, 'Gestión Institucional - Control Documental')
        self.minsize(1440, 740)
        self.protocol('WM_DELETE_WINDOW', self.close)

        self.page_host = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.page_host.pack(fill='both', expand=True)
        self.pages = {}
        self.login = LoginApp(self.page_host)
        self.login.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.active_page = self.login

    def show_screen(self, filename, extra_args=None):
        extra_args = extra_args or []
        if isinstance(extra_args, (str, int)):
            extra_args = [str(extra_args)]

        if filename == 'home.py' and extra_args:
            os.environ['GI_USUARIO'] = str(extra_args[0])
            if len(extra_args) > 1:
                os.environ['GI_USUARIO_ID'] = str(extra_args[1])
            if len(extra_args) > 2:
                os.environ['GI_USUARIO_EMAIL'] = str(extra_args[2])

        if filename == 'applogin.py':
            if self.active_page is not self.login:
                self.active_page.place_forget()
                self.active_page = self.login
                self.login.place(relx=0, rely=0, relwidth=1, relheight=1)
                self.title('01 — Acceso | Gestión Institucional')
            return

        constructors = {
            'home.py': self._home,
            'folio_reservado.py': self._folio,
            'crear_documento.py': self._crear_documento,
            'enviados.py': self._enviados,
            'update.py': self._actualizacion,
        }
        constructor = constructors.get(filename)
        if constructor is None:
            messagebox.showerror('Navegación', f'Pantalla no reconocida: {filename}', parent=self)
            return

        if filename == 'home.py':
            key_args = tuple(extra_args[1:]) if len(extra_args) > 1 else ()
        elif filename in {'folio_reservado.py', 'crear_documento.py'}:
            key_args = tuple(extra_args)
        else:
            key_args = ()
        key = (filename, key_args)
        page = self.pages.get(key)
        if page is self.active_page:
            return

        if page is None:
            try:
                page = constructor(extra_args)
            except (ImportError, OSError, RuntimeError, ValueError) as error:
                messagebox.showerror('Navegación', str(error), parent=self)
                return
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.pages[key] = page

        self.active_page.place_forget()
        self.active_page = page
        page.place(relx=0, rely=0, relwidth=1, relheight=1)
        page.lift()
        on_show = getattr(page, 'on_show', None)
        if on_show is not None:
            on_show()

    def _folio(self, args):
        from views.folio_reservado import PantallaFolio
        if not args:
            raise ValueError('Falta el folio reservado.')
        return PantallaFolio(self.page_host, str(args[0]))

    def _crear_documento(self, args):
        from views.crear_documento import CrearDocumentoApp
        if not args:
            raise ValueError('Falta el folio del documento.')
        return CrearDocumentoApp(self.page_host, str(args[0]))

    def _enviados(self, _args):
        from views.enviados import EnviadosApp
        return EnviadosApp(self.page_host)

    def _actualizacion(self, _args):
        from views.update import DashboardApp
        return DashboardApp(self.page_host)

    def _home(self, _args):
        from views.home import AppGestiónInstitucional
        return AppGestiónInstitucional(self.page_host)

    def close(self):
        for page in self.pages.values():
            guardar_borrador = getattr(page, 'guardar_borrador_pendiente', None)
            if guardar_borrador is not None and not guardar_borrador():
                messagebox.showerror(
                    'Borrador sin guardar',
                    'No se pudo respaldar un borrador en PostgreSQL. '
                    'La aplicación permanecerá abierta para que puedas reintentar.',
                    parent=self,
                )
                return
        dirty_pages = [
            page for page in self.pages.values() if getattr(page, 'unsaved', False)
        ]
        if dirty_pages and not messagebox.askyesno(
            'Cambios sin guardar',
            '¿Cerrar sin guardar los cambios?',
            parent=self,
        ):
            return
        self.destroy()


def main():
    if len(sys.argv) > 1:
        messagebox.showerror('Inicio', 'No se admiten argumentos de pantalla.')
        return
    GestionInstitucionalApp().mainloop()


if __name__ == '__main__':
    main()
