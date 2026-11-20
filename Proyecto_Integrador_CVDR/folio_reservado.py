"""Pantalla de folio reservado, antes del formulario."""
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from screen import Screen
from ui_helpers import (
    ACCENT, GREEN, MUTED, PINK, TEXT,
    button, card, font, label,
)


class FolioScreen(Screen):
    title = "Gestión Institucional — Folio reservado"
    nav_key = "Crear documento"

    def build(self):
        self.folio = None
        self.documento = None

        contenido = ctk.CTkFrame(self.body, fg_color="transparent")
        contenido.pack(fill="x", padx=28, pady=24)
        button(contenido, "←  Volver", lambda: self.app.show("home"),
               width=120).pack(anchor="w", pady=(0, 22))

        panel = card(contenido)
        panel.pack(fill="x", padx=55, pady=6)
        interior = ctk.CTkFrame(panel, fg_color="transparent")
        interior.pack(fill="x", padx=72, pady=32)

        sello = ctk.CTkFrame(interior, width=120, height=120, fg_color=PINK, corner_radius=60)
        sello.pack(pady=(0, 16))
        sello.pack_propagate(False)
        label(sello, "▤", 65, ACCENT).pack(expand=True)

        label(interior, "Tu folio es:", 31, TEXT, True).pack(pady=(3, 14))
        caja = ctk.CTkFrame(interior, fg_color="#F5E8EE", corner_radius=11)
        caja.pack(fill="x", padx=85)
        self.folio_label = label(caja, "", 37, ACCENT, True)
        self.folio_label.pack(pady=22, padx=18)

        label(interior, "Conserva este número para identificar tu documento.",
              12, MUTED).pack(pady=(14, 28))

        self.btn_crear = button(
            interior, "▤  Crear documento", self.crear, primary=True,
            height=62, fg_color=GREEN, hover_color="#18764F", font=font(19, True))
        self.btn_crear.pack(fill="x", padx=86, pady=(0, 14))

        self.btn_generar = button(
            interior, "↓  Generar documento", self.generar, height=58,
            text_color=ACCENT, border_color=ACCENT, font=font(17, True))
        self.btn_generar.pack(fill="x", padx=86)

        self.nota = label(interior, "", 11, MUTED)
        self.nota.pack(pady=(16, 0))

    # ---- ciclo de vida ---------------------------------------------------
    def on_show(self, folio=None):
        self.folio = folio
        self.documento = self.app.store.obtener(folio) if folio else None
        if self.documento is None:
            messagebox.showerror("Folio", "No se encontró el folio reservado.",
                                 parent=self.window)
            self.after(50, lambda: self.app.show("home"))
            return
        self._actualizar()

    def _actualizar(self):
        self.folio_label.configure(text=self.folio)
        if self.documento.creado:
            self.btn_crear.configure(text="✓  Documento creado", state="disabled")
            self.btn_generar.configure(state="normal")
            self.nota.configure(
                text="Documento guardado. Puedes generar su ficha o volver al inicio.",
                text_color=GREEN, font=font(12, True))
        else:
            self.btn_crear.configure(text="▤  Crear documento", state="normal")
            self.btn_generar.configure(state="disabled")
            self.nota.configure(
                text="Primero completa Asunto, Área emisora, Recepción y responsables.",
                text_color=MUTED, font=font(11))

    def handle_menu(self, name):
        if name == "Crear documento" and self.documento and not self.documento.creado:
            self.crear()
            return True
        return False

    # ---- acciones --------------------------------------------------------
    def crear(self):
        self.app.show("crear", folio=self.folio)

    def generar(self):
        documento = self.app.store.obtener(self.folio)
        if documento is None or not documento.creado:
            # No se genera un documento vacío: conduce al formulario.
            self.crear()
            return
        destino = filedialog.asksaveasfilename(
            parent=self.window, title="Guardar ficha del documento",
            defaultextension=".txt", initialfile=self.folio + ".txt",
            filetypes=[("Documento de texto", "*.txt")])
        if not destino:
            return
        contenido = (
            "SISTEMA DE CONTROL DE CORRESPONDENCIA — CVDR DURANGO\n"
            f"Folio: {documento.folio}\n"
            f"Asunto: {documento.asunto}\n"
            f"Área emisora: {documento.area_emisora}\n"
            f"Recepción: {documento.recepcion}\n"
            f"Elaboró: {documento.elaboro}\n"
            f"Revisó: {documento.reviso}\n"
            f"Autorizó: {documento.autorizo}\n"
        )
        try:
            Path(destino).write_text(contenido, encoding="utf-8-sig")
        except OSError as error:
            messagebox.showerror("Generar documento", str(error), parent=self.window)
            return
        messagebox.showinfo("Generar documento",
                            "Se guardó la ficha de texto del documento.",
                            parent=self.window)