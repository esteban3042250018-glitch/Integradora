"""
Punto de entrada: ejecuta python main.py

Una sola ventana y un solo proceso. Las pantallas se construyen una vez
(en segundo plano, mientras el usuario ve el login) y después solo se
muestran u ocultan, por eso el cambio entre ellas es inmediato.
"""

import os
import time
import ctypes

from tkinter import messagebox
import customtkinter as ctk

from crear_documento import CrearDocumentoScreen
from document_store import DocumentStore
from folio_reservado import FolioScreen
from home import HomeScreen
from admin_panel import AdminPanelScreen
from login import LoginView
from shell import MainShell
from ui_helpers import UIComponents, WindowManager
from update import UpdateScreen

from PIL import Image, ImageTk


class Application(ctk.CTk):

    LOGIN_TITLE = "01 — Acceso | Halcones Dev"

    DEBUG_TIMING = False   # True: imprime en consola cuánto tarda cada cambio de pantalla

    # Clave de pantalla -> clase
    SCREENS = {
        "home": HomeScreen,
        "folio": FolioScreen,
        "crear": CrearDocumentoScreen,
        "update": UpdateScreen,
        "admin": AdminPanelScreen,
    }

    def __init__(self):

        # Identidad de la aplicación en Windows
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "HalconesDev.Correspondencia"
            )
        except Exception:
            pass

        super().__init__()

        WindowManager.setup(self, self.LOGIN_TITLE)

        # --------------------------------------------------
        # CONFIGURAR ICONO DE LA APLICACIÓN
        # --------------------------------------------------

        try:

            base_dir = os.path.dirname(os.path.abspath(__file__))

            icon_path = os.path.join(
                base_dir,
                "assets",
                "icon_app.png"
            )

            icon_ico = os.path.join(
                base_dir,
                "assets",
                "icon_app.ico"
            )

            # Cargar imagen original
            img_icon = Image.open(icon_path).convert("RGBA")

            # Generar archivo ICO automáticamente
            img_icon.save(
                icon_ico,
                format="ICO",
                sizes=[
                    (16, 16),
                    (32, 32),
                    (48, 48),
                    (64, 64),
                    (128, 128),
                    (256, 256)
                ]
            )

            # Mantener referencia de la imagen
            self._icon_image = ImageTk.PhotoImage(img_icon)

            # Aplicar icono PNG a Tkinter
            self.iconphoto(True, self._icon_image)

            # Aplicar icono ICO a Windows
            self.iconbitmap(default=icon_ico)

        except Exception as e:

            print(f"No se pudo configurar el icono: {e}")

        # --------------------------------------------------
        # INICIALIZAR APLICACIÓN
        # --------------------------------------------------

        self.store = DocumentStore()

        self.shell = None
        self.screens = {}
        self.current = None

        self._pendientes = list(self.SCREENS)

        # Login
        self.login = LoginView(
            self,
            on_login=self.start_session
        )

        self.login.pack(fill="both", expand=True)

        # Eventos
        self.bind("<Return>", self._on_return)
        self.protocol("WM_DELETE_WINDOW", self.close)

        # Iniciar precarga
        self.after(10, self._precargar)

    # --------------------------------------------------
    # PRECARGA
    # --------------------------------------------------

    def _construir_shell(self):

        self.shell = MainShell(
            self,
            on_menu=self.on_menu,
            on_search=self.on_search
        )

    def _construir_pantalla(self, clave):

        pantalla = self.SCREENS[clave](
            self.shell.content,
            self
        )

        self.screens[clave] = pantalla

        return pantalla

    def _precargar(self):
        """Construye una pieza por turno para no congelar la ventana."""

        if self.shell is None:

            self._construir_shell()

        elif self._pendientes:

            clave = self._pendientes.pop(0)

            if clave not in self.screens:
                self._construir_pantalla(clave)

        if self._pendientes:
            self.after(1, self._precargar)

    def _completar_precarga(self):
        """Completa la precarga si el usuario ingresa antes de terminar."""

        if self.shell is None:
            self._construir_shell()

        while self._pendientes:

            clave = self._pendientes.pop(0)

            if clave not in self.screens:
                self._construir_pantalla(clave)

    # --------------------------------------------------
    # SESIÓN
    # --------------------------------------------------

    def _on_return(self, event):

        if self.shell is None or not self.shell.winfo_ismapped():
            self.login.submit()

    def start_session(self):

        self._completar_precarga()

        self.login.pack_forget()

        self.shell.pack(fill="both", expand=True)

        self.show("home")

    # --------------------------------------------------
    # NAVEGACIÓN
    # --------------------------------------------------

    def show(self, clave, *, verificar=True, **params):
        """Muestra una pantalla. Devuelve False si la actual no deja salir."""

        inicio = time.perf_counter()

        destino = (
            self.screens.get(clave)
            or self._construir_pantalla(clave)
        )

        actual = self.current

        cambia = destino is not actual

        if cambia and actual is not None and verificar:

            if not actual.can_leave():
                return False

        if cambia and actual is not None:
            self.shell.unmount(actual)

        self.shell.topbar.clear_search()

        destino.on_show(**params)

        self.current = destino

        self.shell.sidebar.set_active(
            destino.nav_key,
            destino.show_cut
        )

        self.title(destino.title)

        if cambia:
            self.shell.mount(destino)

        if self.DEBUG_TIMING:

            self.update_idletasks()

            print(
                f"{clave}: "
                f"{(time.perf_counter() - inicio) * 1000:.0f} ms"
            )

        return True

    # --------------------------------------------------
    # CREAR NUEVO OFICIO
    # --------------------------------------------------

    def nuevo_oficio(self):
        """Reserva un folio nuevo y abre su pantalla."""

        if self.current is not None:

            if not self.current.can_leave():
                return

        try:

            folio = self.store.reservar_folio()

        except (OSError, ValueError) as error:

            messagebox.showerror(
                "Folio",
                str(error),
                parent=self
            )

            return

        self.show(
            "folio",
            verificar=False,
            folio=folio
        )

    # --------------------------------------------------
    # MENÚ
    # --------------------------------------------------

    def on_menu(self, nombre):

        if self.current is not None:

            if self.current.handle_menu(nombre):
                return

        if nombre in HomeScreen.CATEGORIAS:

            self.show(
                "home",
                category=HomeScreen.CATEGORIAS[nombre]
            )

        elif nombre == "Crear documento":

            self.nuevo_oficio()

        elif nombre in ("Configuración", "Actualización"):

            self.show("update")

        elif nombre == "Panel de administración":

            self.show("admin")

        elif nombre == "Búsqueda avanzada":

            self.shell.topbar.focus_search()

        else:

            UIComponents.unavailable(
                self,
                nombre
            )

    # --------------------------------------------------
    # BÚSQUEDA
    # --------------------------------------------------

    def on_search(self, texto):

        if self.current is not None:
            self.current.on_search(texto)

    def search_text(self):

        return (
            self.shell.topbar.text
            if self.shell is not None
            else ""
        )

    # --------------------------------------------------
    # CERRAR APLICACIÓN
    # --------------------------------------------------

    def close(self):

        if self.current is None or self.current.can_leave():
            self.destroy()


# ------------------------------------------------------
# PUNTO DE ENTRADA
# ------------------------------------------------------

if __name__ == "__main__":

    app = Application()

    app.mainloop()
