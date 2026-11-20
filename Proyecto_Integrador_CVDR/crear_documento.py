"""Pantalla Crear documento: Asunto, Área emisora, Recepción y responsables."""
from tkinter import messagebox

import customtkinter as ctk

from document_store import Documento
from screen import Screen
from ui_helpers import (
    ACCENT, LINE, MUTED, PINK, SOFT, TEXT, WHITE,
    button, card, entry, font, label,
)

# Áreas presentes en la demostración; el combo permite escribir otra si procede.
AREAS_EMISORAS = (
    "Dirección General",
    "Dirección Administrativa",
    "Coordinación Jurídica",
    "Secretaría de Finanzas",
    "Subdirección de Planeación",
    "Unidad de Recursos Materiales",
    "Enlace de Vinculación",
)

AREA_PLACEHOLDER = "Selecciona un área"

# (clave en Documento, texto del placeholder)
RESPONSABLES = (
    ("elaboro", "Nombre de quien elaboró"),
    ("reviso", "Nombre de quien revisó"),
    ("autorizo", "Nombre de quien autorizó"),
)


class CrearDocumentoScreen(Screen):
    title = "Gestión Institucional - Crear documento"
    nav_key = "Crear documento"

    def build(self):
        self.folio = None
        self.entradas = {}          # clave -> CTkEntry (campos de texto)

        content = ctk.CTkFrame(self.body, fg_color="transparent")
        content.pack(fill="x", padx=22, pady=20)

        self._build_encabezado(content)

        formulario = card(content)
        formulario.pack(fill="x", pady=(0, 18))
        self._build_intro(formulario)

        campos = ctk.CTkFrame(formulario, fg_color="transparent")
        campos.pack(fill="x", padx=28)
        campos.grid_columnconfigure((0, 1), weight=1, uniform="fields")
        self._build_datos(campos)
        self._build_responsables(formulario)
        self._build_barra(formulario)

        self.estado = label(content, "", 12, ACCENT)
        self.estado.pack(anchor="w", padx=8)

    # ---- construcción ----------------------------------------------------
    def _build_encabezado(self, content):
        encabezado = ctk.CTkFrame(content, fg_color="transparent")
        encabezado.pack(fill="x", pady=(0, 18))
        titulo = ctk.CTkFrame(encabezado, fg_color="transparent")
        titulo.pack(side="left")
        label(titulo, "Crear documento", 28).pack(anchor="w")
        self.folio_label = label(titulo, "", 14, ACCENT, True)
        self.folio_label.pack(anchor="w")
        button(encabezado, "←  Volver a correspondencia",
               lambda: self.app.show("folio", folio=self.folio),
               width=216).pack(side="right", pady=8)

    def _build_intro(self, formulario):
        intro = ctk.CTkFrame(formulario, fg_color="transparent")
        intro.pack(fill="x", padx=28, pady=(25, 12))
        label(intro, "Información del documento", 19, TEXT, True).pack(anchor="w")
        label(intro, "Captura los datos para crear un registro.", 12, MUTED).pack(
            anchor="w", pady=(4, 0))
        ctk.CTkFrame(formulario, height=1, corner_radius=0, fg_color=LINE).pack(
            fill="x", padx=28, pady=(4, 18))

    def _build_datos(self, campos):
        # 1. Asunto
        label(campos, "Asunto", 12, TEXT, True).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.entradas["asunto"] = entry(
            campos, "Escribe el asunto del documento", height=44)
        self.entradas["asunto"].grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 24))

        # 2. Área emisora (combo editable)
        label(campos, "Área emisora", 12, TEXT, True).grid(
            row=2, column=0, sticky="w", pady=(0, 6), padx=(0, 12))
        self.area_emisora = ctk.CTkComboBox(
            campos, values=list(AREAS_EMISORAS), height=44,
            corner_radius=8, border_width=1, border_color=LINE,
            fg_color=WHITE, button_color=WHITE, button_hover_color=SOFT,
            text_color=TEXT, font=font(12),
            dropdown_fg_color=WHITE, dropdown_text_color=TEXT,
            dropdown_hover_color=PINK,
        )
        self.area_emisora.grid(row=3, column=0, sticky="ew", padx=(0, 12), pady=(0, 24))
        self.area_emisora.set(AREA_PLACEHOLDER)

        # 3. Recepción
        label(campos, "Recepción", 12, TEXT, True).grid(
            row=2, column=1, sticky="w", pady=(0, 6), padx=(12, 0))
        self.entradas["recepcion"] = entry(
            campos, "Escribe los datos de recepción", height=44)
        self.entradas["recepcion"].grid(
            row=3, column=1, sticky="ew", padx=(12, 0), pady=(0, 24))

    def _build_responsables(self, formulario):
        ctk.CTkFrame(formulario, height=1, corner_radius=0, fg_color=LINE).pack(
            fill="x", padx=28, pady=(0, 18))
        label(formulario, "Responsables del documento", 15, TEXT, True).pack(
            anchor="w", padx=28, pady=(0, 12))

        fila = ctk.CTkFrame(formulario, fg_color="transparent")
        fila.pack(fill="x", padx=28)
        fila.grid_columnconfigure((0, 1, 2), weight=1, uniform="responsables")

        ultimo = len(RESPONSABLES) - 1
        for columna, (clave, placeholder) in enumerate(RESPONSABLES):
            padx = (0 if columna == 0 else 8, 0 if columna == ultimo else 8)
            label(fila, Documento.ETIQUETAS[clave], 12, TEXT, True).grid(
                row=0, column=columna, sticky="w", pady=(0, 6), padx=padx)
            campo = entry(fila, placeholder, height=44)
            campo.grid(row=1, column=columna, sticky="ew", padx=padx, pady=(0, 24))
            self.entradas[clave] = campo

    def _build_barra(self, formulario):
        barra = ctk.CTkFrame(formulario, fg_color=SOFT, corner_radius=10)
        barra.pack(fill="x", padx=28, pady=(2, 24))
        label(barra, "Los seis campos son obligatorios.", 11, MUTED).pack(
            side="left", padx=18, pady=14)
        button(barra, "Limpiar", self.limpiar, width=112, height=38).pack(
            side="right", padx=(0, 15), pady=10)
        button(barra, "▣  Guardar documento", self.guardar, primary=True,
               width=204, height=38).pack(side="right", padx=10, pady=10)

    # ---- ciclo de vida ---------------------------------------------------
    def on_show(self, folio=None):
        self.folio = folio
        self.folio_label.configure(text=f"Folio reservado: {folio}")
        self.limpiar()

    def handle_menu(self, name):
        if name == "Crear documento":
            self.entradas["asunto"].focus_set()
            return True
        return False

    # ---- acciones --------------------------------------------------------
    def limpiar(self):
        for campo in self.entradas.values():
            campo.delete(0, "end")
        self.area_emisora.set(AREA_PLACEHOLDER)
        self.estado.configure(text="")
        self.entradas["asunto"].focus_set()

    def _capturar(self):
        """Devuelve (campos, None) o (None, (mensaje, control)) si falta algo."""
        campos = {clave: campo.get().strip() for clave, campo in self.entradas.items()}
        area = self.area_emisora.get().strip()
        campos["area_emisora"] = "" if area == AREA_PLACEHOLDER else area

        # Se valida en el orden en que aparecen en pantalla.
        orden = ("asunto", "area_emisora", "recepcion", *(c for c, _ in RESPONSABLES))
        for clave in orden:
            if not campos[clave]:
                control = self.area_emisora if clave == "area_emisora" else self.entradas[clave]
                mensaje = (
                    "Selecciona un Área emisora." if clave == "area_emisora"
                    else f"Completa el campo {Documento.ETIQUETAS[clave]}."
                )
                return None, (mensaje, control)
        return campos, None

    def guardar(self):
        campos, error = self._capturar()
        if error:
            return self.advertir(*error)

        try:
            documento = self.app.store.guardar(campos, folio=self.folio)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Guardar documento", str(exc), parent=self.window)
            return

        messagebox.showinfo(
            "Documento guardado",
            f"Se registró {documento.folio} en este equipo.\n"
            "No se envió a ningún servidor ni base de datos.",
            parent=self.window)
        self.app.show("folio", folio=self.folio)

    def advertir(self, mensaje, control):
        messagebox.showwarning("Crear documento", mensaje, parent=self.window)
        control.focus_set()
