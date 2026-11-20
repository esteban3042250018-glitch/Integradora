"""Marco fijo de la aplicación: menú lateral, barra superior y área de contenido.

Se construye una sola vez; solo cambia la pantalla que se muestra en
`MainShell.content`.
"""
import customtkinter as ctk

from ui_helpers import (
    ACCENT, BG, GOLD, MUTED, PINK, SOFT, TEXT, WHITE, WINE,
    UIComponents, brand, button, entry, font, label,
)


class Sidebar(ctk.CTkFrame):
    SECTIONS = (
        ("OPERACIÓN", (
            "Correspondencia · 18",
            "Por asignar · 7",
            "Seguimiento · 12",
            "Enviada",
        )),
        ("CONSULTA Y CONTROL", (
            "Búsqueda avanzada",
            "Archivo",
            "Reportes",
        )),
        ("ADMINISTRACIÓN", (
            "Áreas y usuarios",
            "Catálogos",
            "Configuración",
            "Panel de administración",
        )),
    )

    def __init__(self, master, on_select):
        super().__init__(master, width=248, corner_radius=0, fg_color=WINE)
        self.on_select = on_select
        self.items = {}
        self.grid_propagate(False)
        self.pack_propagate(False)

        brand(self, compact=True, on_dark=True).pack(
            anchor="w", padx=22, pady=(24, 18)
        )

        for title_text, names in self.SECTIONS:
            label(self, title_text, 9, "#CFACB9", True, height=18).pack(
                anchor="w", padx=18,
                pady=(0 if title_text == "OPERACIÓN" else 16, 3)
            )
            for name in names:
                self._add_item(name)

        self.cut = ctk.CTkFrame(self, fg_color="#671630", corner_radius=15)
        label(self.cut, "●  Corte de recepción", 11, WHITE, True, height=22).pack(
            anchor="w", padx=14, pady=(10, 0)
        )
        label(
            self.cut, "Ventanilla abierta hasta las 17:00 h.", 10,
            "#D6B2C0", height=18
        ).pack(anchor="w", padx=14, pady=(0, 10))
        self.cut.pack(fill="x", padx=18, pady=24)

    def _add_item(self, name):
        line = ctk.CTkFrame(self, fg_color="transparent", height=26)
        line.pack(fill="x", padx=18)

        marker = ctk.CTkFrame(
            line, width=6, height=14, corner_radius=0, fg_color=WINE
        )
        marker.pack(side="left", padx=(0, 7))

        control = ctk.CTkButton(
            line,
            text=name,
            height=26,
            width=195,
            fg_color="transparent",
            hover_color=ACCENT,
            text_color=WHITE,
            anchor="w",
            font=font(13, False),
            corner_radius=4,
            command=lambda n=name: self.on_select(n),
        )
        control.pack(side="left", fill="x", expand=True)
        self.items[name] = (marker, control)

    def set_active(self, key, show_cut=True):
        """Resalta la opción cuyo texto empieza con `key`."""
        for name, (marker, control) in self.items.items():
            shown = "Actualización" if (
                name == "Configuración" and key == "Actualización"
            ) else name
            selected = shown.startswith(key)
            marker.configure(fg_color=GOLD if selected else WINE)
            control.configure(
                text=shown,
                text_color=GOLD if selected else WHITE,
                font=font(13, selected),
            )

        if show_cut:
            if not self.cut.winfo_manager():
                self.cut.pack(fill="x", padx=18, pady=24)
        else:
            self.cut.pack_forget()


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_search):
        super().__init__(master, fg_color=WHITE, height=76, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)

        self.search_entry = entry(
            self,
            "⌕   Buscar por folio, asunto, remitente o área...",
            width=510,
            height=42,
            fg_color=SOFT,
            border_width=0,
        )
        self.search_entry.grid(row=0, column=0, sticky="w", padx=28, pady=17)
        self.search_entry.bind(
            "<KeyRelease>", lambda event: on_search(self.search_entry.get())
        )

        profile = ctk.CTkFrame(self, fg_color="transparent")
        profile.grid(row=0, column=1, padx=(8, 28))

        for glyph, topic in (("?", "Ayuda"), ("♢", "Notificaciones")):
            button(
                profile, glyph,
                lambda name=topic: UIComponents.unavailable(self.winfo_toplevel(), name),
                width=24, border_width=0, height=32
            ).pack(side="left", padx=2)

        label(
            profile, "LM", 12, ACCENT, True,
            width=38, height=38, fg_color=PINK, corner_radius=19
        ).pack(side="left", padx=(10, 12))
        label(profile, "Laura Méndez · Oficialía de Partes", 12, TEXT, True).pack(side="left")
        label(profile, "⌄", 12, MUTED).pack(side="left", padx=(10, 0))

    @property
    def text(self):
        return self.search_entry.get()

    def clear_search(self):
        self.search_entry.delete(0, "end")

    def focus_search(self):
        self.search_entry.focus_set()


class MainShell(ctk.CTkFrame):
    def __init__(self, master, on_menu, on_search):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, on_menu)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        self.topbar = TopBar(main, on_search)
        self.topbar.grid(row=0, column=0, sticky="ew")

        self.content = ctk.CTkFrame(main, fg_color=BG, corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def mount(self, screen):
        screen.grid(row=0, column=0, sticky="nsew")

    def unmount(self, screen):
        screen.grid_forget()
