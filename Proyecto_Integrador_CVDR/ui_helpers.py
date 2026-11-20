"""Tema y componentes visuales reutilizables.

Aquí ya no hay navegación: las pantallas se cambian dentro de una sola
ventana (ver main.py), por eso no se lanzan procesos nuevos de Python.
"""
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image


class Theme:
    WINE = "#510F26"
    ACCENT = "#C2185B"
    BG = "#F5F6F8"
    WHITE = "#FFFFFF"
    TEXT = "#1F2937"
    MUTED = "#6B7280"
    LINE = "#E5E7EB"
    SOFT = "#F9FAFB"

    PINK = "#FCE7F3"
    BLUE = "#2563EB"
    GREEN = "#16A34A"
    GOLD = "#F5D447"

    @classmethod
    def configure(cls):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")


# Alias cortos para no escribir Theme.X en cada pantalla.
WINE = Theme.WINE
ACCENT = Theme.ACCENT
BG = Theme.BG
WHITE = Theme.WHITE
TEXT = Theme.TEXT
MUTED = Theme.MUTED
LINE = Theme.LINE
SOFT = Theme.SOFT
PINK = Theme.PINK
BLUE = Theme.BLUE
GREEN = Theme.GREEN
GOLD = Theme.GOLD


class WindowManager:
    """Configura la ventana principal (se hace una sola vez)."""

    @staticmethod
    def maximize(window):
        try:
            window.state("zoomed")
        except Exception:
            try:
                window.attributes("-zoomed", True)
            except Exception:
                pass

    @classmethod
    def setup(cls, window, title, height=900):
        window.title(title)
        window.geometry(f"1440x{height}")
        window.minsize(800, 600)
        window.configure(fg_color=Theme.BG)
        # Se retrasa porque en Windows customtkinter ignora el maximizado
        # si se pide antes de que la ventana exista en pantalla.
        window.after(300, lambda: cls.maximize(window))


class UIComponents:
    """Fábrica de widgets con el estilo de la aplicación."""

    @staticmethod
    def font(size=14, weight="normal", family="Segoe UI"):
        if weight is True:
            weight = "bold"
        elif weight is False or weight is None:
            weight = "normal"
        return ctk.CTkFont(family=family, size=size, weight=weight)

    @staticmethod
    def label(parent, text, size=14, color=None, weight="normal", bold=None, **kwargs):
        if bold is not None:
            weight = bold
        return ctk.CTkLabel(
            parent,
            text=text,
            font=UIComponents.font(size, weight),
            text_color=color or Theme.TEXT,
            **kwargs
        )

    @staticmethod
    def button(
        parent,
        text,
        command=None,
        primary=False,
        color=None,
        hover_color=None,
        text_color=None,
        height=42,
        **kwargs
    ):
        filled = bool(primary) or color is not None

        if filled:
            background = color or Theme.ACCENT
            hover = hover_color or (
                Theme.SOFT if background == Theme.WHITE else Theme.WINE
            )
            foreground = text_color or Theme.WHITE
            border = 0
        else:
            background = Theme.WHITE
            hover = hover_color or Theme.SOFT
            foreground = text_color or Theme.TEXT
            border = 1

        options = {
            "text": text,
            "command": command,
            "height": height,
            "corner_radius": 10,
            "font": UIComponents.font(13, "bold"),
            "fg_color": background,
            "hover_color": hover,
            "text_color": foreground,
            "border_width": border,
            "border_color": Theme.LINE,
        }
        options.update(kwargs)
        return ctk.CTkButton(parent, **options)

    @staticmethod
    def entry(parent, placeholder="", show=None, height=44, **kwargs):
        options = {
            "placeholder_text": placeholder,
            "height": height,
            "corner_radius": 9,
            "border_width": 1,
            "border_color": Theme.LINE,
            "fg_color": Theme.WHITE,
            "text_color": Theme.TEXT,
            "placeholder_text_color": Theme.MUTED,
            "font": UIComponents.font(14),
        }
        if show is not None:
            options["show"] = show
        options.update(kwargs)
        return ctk.CTkEntry(parent, **options)

    @staticmethod
    def card(parent, **kwargs):
        options = {
            "corner_radius": 16,
            "border_width": 1,
            "border_color": Theme.LINE,
            "fg_color": Theme.WHITE,
        }
        options.update(kwargs)
        return ctk.CTkFrame(parent, **options)

    @staticmethod
    def select(parent, values, command=None, width=140, **kwargs):
        options = {
            "values": values,
            "command": command,
            "width": width,
            "height": 40,
            "corner_radius": 9,
            "fg_color": Theme.WHITE,
            "button_color": Theme.ACCENT,
            "button_hover_color": Theme.WINE,
            "border_color": Theme.LINE,
            "text_color": Theme.TEXT,
            "font": UIComponents.font(13),
            "dropdown_fg_color": Theme.WHITE,
            "dropdown_text_color": Theme.TEXT,
            "dropdown_hover_color": Theme.PINK,
        }
        options.update(kwargs)
        return ctk.CTkComboBox(parent, **options)

    @staticmethod
    def unavailable(parent, feature="Esta función"):
        messagebox.showinfo(
            "Función no disponible",
            f"{feature} todavía no está disponible.",
            parent=parent
        )

    @staticmethod
    def find_asset(filename):
        """Busca en ./assets y en ../assets (junto o encima de la carpeta del código)."""
        folder = Path(__file__).resolve().parent
        for candidate in (folder / "assets" / filename,
                          folder.parent / "assets" / filename):
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _find_logo():
        return UIComponents.find_asset("Halcones.jpg")

    @staticmethod
    def image(filename, height):
        """CTkImage de assets/<filename> con alto fijo y proporción original.

        Devuelve None si el archivo no existe o no se puede leer.
        """
        ruta = UIComponents.find_asset(filename)
        if ruta is None:
            return None
        try:
            with Image.open(ruta) as source:
                original = source.convert("RGBA")
        except OSError:
            return None
        ancho = round(original.width * height / original.height)
        return ctk.CTkImage(light_image=original, dark_image=original,
                            size=(ancho, height))

    @staticmethod
    def brand(parent, compact=False, large=False, on_dark=False):
        frame = ctk.CTkFrame(parent, fg_color="transparent")

        mark_size = 42 if compact else 52 if large else 50
        mark = ctk.CTkFrame(
            frame,
            width=mark_size,
            height=mark_size,
            corner_radius=12,
            fg_color=Theme.ACCENT if on_dark else Theme.WINE
        )
        mark.pack(side="left", padx=(0, 12))
        mark.pack_propagate(False)

        logo_path = UIComponents._find_logo()
        logo_ready = False

        if logo_path is not None:
            try:
                with Image.open(logo_path) as source:
                    original = source.convert("RGB")
                imagen = ctk.CTkImage(
                    light_image=original, size=(mark_size, mark_size)
                )
                ctk.CTkLabel(mark, image=imagen, text="").place(
                    relx=0.5, rely=0.5, anchor="center"
                )
                logo_ready = True
            except OSError:
                logo_ready = False

        if not logo_ready:
            UIComponents.label(
                mark, "CG", 17, Theme.WHITE, True
            ).place(relx=0.5, rely=0.5, anchor="center")

        text_frame = ctk.CTkFrame(frame, fg_color="transparent")
        text_frame.pack(side="left", fill="y")

        ctk.CTkLabel(
            text_frame,
            text="GESTIÓN INSTITUCIONAL",
            font=UIComponents.font(13 if compact else 17, "bold"),
            text_color=Theme.WHITE if on_dark else Theme.WINE,
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_frame,
            text="CONTROL DOCUMENTAL" if compact else "PLATAFORMA ADMINISTRATIVA",
            font=UIComponents.font(9 if compact else 10, "normal"),
            text_color="#C9A7B5" if on_dark else Theme.MUTED,
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        return frame


Theme.configure()

font = UIComponents.font
label = UIComponents.label
button = UIComponents.button
entry = UIComponents.entry
card = UIComponents.card
select = UIComponents.select
unavailable = UIComponents.unavailable
brand = UIComponents.brand