"""Clase base de todas las pantallas internas de la aplicación."""
import customtkinter as ctk

from ui_helpers import Theme, UIComponents


class Screen(ctk.CTkFrame):
    """Pantalla que vive dentro de la ventana principal.

    Las pantallas se construyen UNA sola vez y después solo se muestran u
    ocultan, por eso el cambio entre ellas es inmediato.

    Atributos de clase que cada pantalla puede redefinir:
        title      Título de la ventana mientras está visible.
        nav_key    Opción del menú lateral que se resalta.
        scrollable Si el cuerpo tiene barra de desplazamiento.
        show_cut   Si se muestra el recuadro "Corte de recepción".

    Métodos que cada pantalla puede redefinir:
        build()          Construye los widgets (se llama una vez).
        on_show(**kw)    Se llama cada vez que la pantalla se muestra.
        can_leave()      Devuelve False para impedir que el usuario salga.
        handle_menu(n)   Devuelve True si la pantalla atendió la opción del menú.
        on_search(texto) Se llama al escribir en el buscador superior.
    """

    title = "Gestión Institucional - Control Documental"
    nav_key = "Correspondencia"
    scrollable = True
    show_cut = True

    def __init__(self, master, app):
        super().__init__(master, fg_color=Theme.BG, corner_radius=0)
        self.app = app
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.body = self._create_body()
        self.body.grid(row=0, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

        self.build()

    def _create_body(self):
        if self.scrollable:
            return ctk.CTkScrollableFrame(
                self,
                fg_color=Theme.BG,
                corner_radius=0,
                scrollbar_button_color=Theme.LINE,
                scrollbar_button_hover_color=Theme.MUTED,
            )
        return ctk.CTkFrame(self, fg_color=Theme.BG, corner_radius=0)

    # ---- ganchos para las subclases -------------------------------------
    def build(self):
        raise NotImplementedError

    def on_show(self, **params):
        pass

    def can_leave(self):
        return True

    def handle_menu(self, name):
        return False

    def on_search(self, text):
        pass

    # ---- utilidades ------------------------------------------------------
    @property
    def window(self):
        """Ventana raíz; úsala como `parent` de los cuadros de diálogo."""
        return self.winfo_toplevel()

    def unavailable(self, feature):
        UIComponents.unavailable(self.window, feature)
