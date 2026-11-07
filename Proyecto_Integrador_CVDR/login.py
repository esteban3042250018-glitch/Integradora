"""Pantalla de acceso (se muestra antes del marco principal)."""

import customtkinter as ctk
from PIL import Image, ImageDraw

from ui_helpers import Theme, UIComponents


class BrandingPanel(ctk.CTkFrame):
    LOGO_SIZE = 120
    FEATURES = (
        "Acceso organizado a las herramientas",
        "Información centralizada",
        "Interfaz sencilla y consistente",
    )

    def __init__(self, master):
        super().__init__(master, fg_color=Theme.WINE, corner_radius=0)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew", padx=50, pady=45)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(8, weight=1)

        self._build_logo(content)
        self._build_texts(content)
        self._build_features(content)

        ctk.CTkLabel(
            content,
            text="PLATAFORMA ADMINISTRATIVA",
            font=UIComponents.font(10, "bold"),
            text_color="#CBAAB7",
            anchor="w"
        ).grid(row=8, column=0, sticky="sw", pady=(45, 0))

    def _load_logo(self):
        """Devuelve el logo cuadrado y circular, o None si no se puede leer."""
        size = self.LOGO_SIZE
        ruta = UIComponents.find_asset("cvdr.jpg")
        if ruta is None:
            return None
        try:
            with Image.open(ruta) as origen:
                original = origen.convert("RGBA")
        except OSError:
            return None

        # Lienzo cuadrado blanco para no cortar la imagen.
        ancho, alto = original.size
        lado = max(ancho, alto)
        lienzo = Image.new("RGBA", (lado, lado), (255, 255, 255, 255))
        lienzo.paste(original, ((lado - ancho) // 2, (lado - alto) // 2), mask=original)
        lienzo = lienzo.resize((size, size), Image.Resampling.LANCZOS)

        mascara = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, size - 1, size - 1), fill=255)
        lienzo.putalpha(mascara)
        return lienzo

    def _build_logo(self, content):
        size = self.LOGO_SIZE
        logo = ctk.CTkFrame(
            content, width=size, height=size, corner_radius=0, fg_color="transparent"
        )
        logo.grid(row=0, column=0, sticky="w", pady=(0, 25))
        logo.grid_propagate(False)

        imagen = self._load_logo()
        if imagen is not None:
            self.logo_image = ctk.CTkImage(
                light_image=imagen, dark_image=imagen, size=(size, size)
            )
            ctk.CTkLabel(
                logo, image=self.logo_image, text="", fg_color="transparent"
            ).place(relx=0.5, rely=0.5, anchor="center")
        else:
            ctk.CTkLabel(
                logo,
                text="CVDR",
                font=UIComponents.font(30, "bold"),
                text_color=Theme.WHITE
            ).place(relx=0.5, rely=0.5, anchor="center")

    def _build_texts(self, content):
        ctk.CTkLabel(
            content,
            text="CENTRO DE VINCULACIÓN Y DE DESARROLLO\nREGIONAL",
            font=UIComponents.font(17, "bold"),
            text_color=Theme.WHITE,
            justify="left",
            anchor="w"
        ).grid(row=1, column=0, sticky="w")

        ctk.CTkLabel(
            content,
            text=(
                "Una plataforma centralizada para facilitar\n"
                "la administración, organización y seguimiento "
                "de los\nprocesos institucionales."
            ),
            font=UIComponents.font(16),
            text_color="#E8DCE1",
            wraplength=470,
            justify="left",
            anchor="w"
        ).grid(row=2, column=0, sticky="w", pady=(18, 0))

        ctk.CTkFrame(
            content, width=85, height=4, corner_radius=2, fg_color="#C58A9E"
        ).grid(row=3, column=0, sticky="w", pady=(28, 25))

    def _build_features(self, content):
        for index, feature in enumerate(self.FEATURES):
            item = ctk.CTkFrame(content, fg_color="transparent")
            item.grid(row=4 + index, column=0, sticky="w", pady=6)

            ctk.CTkLabel(
                item,
                text="✓",
                font=UIComponents.font(16, "bold"),
                text_color=Theme.WHITE,
                width=28
            ).pack(side="left")

            ctk.CTkLabel(
                item,
                text=feature,
                font=UIComponents.font(14),
                text_color="#F2E9ED",
                anchor="w"
            ).pack(side="left")


class LoginPanel(ctk.CTkFrame):
    def __init__(self, master, on_login):
        super().__init__(master, fg_color=Theme.BG, corner_radius=0)
        self.on_login = on_login

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_form()

    def _build_form(self):
        container = ctk.CTkFrame(self, fg_color="transparent", width=430)
        container.grid(row=0, column=0, sticky="", padx=35, pady=35)
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container,
            text="Bienvenido",
            font=UIComponents.font(32, "bold"),
            text_color=Theme.TEXT,
            anchor="w"
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            container,
            text="Iniciar sesión",
            font=UIComponents.font(14),
            text_color=Theme.MUTED,
            anchor="w"
        ).grid(row=1, column=0, sticky="ew", pady=(8, 30))

        form_card = UIComponents.card(container)
        form_card.grid(row=2, column=0, sticky="ew")
        form_card.grid_columnconfigure(0, weight=1)

        form = ctk.CTkFrame(form_card, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=28, pady=30)
        form.grid_columnconfigure(0, weight=1)

        UIComponents.button(
            form,
            "Ingresar al sistema",
            self.on_login,
            color=Theme.ACCENT,
            width=374,
            height=48
        ).grid(row=0, column=0, sticky="ew")


class LoginView(ctk.CTkFrame):
    """Pantalla completa de acceso."""

    def __init__(self, master, on_login):
        super().__init__(master, fg_color=Theme.BG, corner_radius=0)
        self.on_login = on_login

        self.grid_columnconfigure(0, weight=41, uniform="panels")
        self.grid_columnconfigure(1, weight=59, uniform="panels")
        self.grid_rowconfigure(0, weight=1)

        self.branding_panel = BrandingPanel(self)
        self.branding_panel.grid(row=0, column=0, sticky="nsew")

        self.login_panel = LoginPanel(self, on_login=self.submit)
        self.login_panel.grid(row=0, column=1, sticky="nsew")

    def submit(self):
        # Aquí se conectará la validación real de credenciales.
        self.on_login()