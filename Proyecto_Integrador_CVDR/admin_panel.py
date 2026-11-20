"""Panel de administración agregado al proyecto existente.

Incluye cuatro secciones dentro de una sola interfaz:
1) Imagen institucional
2) Estructura dinámica de folio
3) Empleados
4) Generar reporte
"""
import csv
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import calendar as pycalendar

import tkinter as tk

import customtkinter as ctk
from PIL import Image

from screen import Screen
from windows_dragdrop import WindowsFileDrop

from ui_helpers import (
    ACCENT, BG, GOLD, GREEN, LINE, MUTED, PINK, SOFT, TEXT, WHITE,
    WINE, button, card, entry, font, label, select,
)


class AdminPanelScreen(Screen):
    title = "Gestión Institucional - Panel de administración"
    nav_key = "Panel de administración"
    show_cut = False
    scrollable = True

    ADMIN_BUTTONS = (
        ("admin1", "Admin 1", "Imagen institucional"),
        ("admin2", "Admin 2", "Estructura de folio"),
        ("admin3", "Admin 3", "Empleados"),
        ("admin4", "Admin 4", "Generar reporte"),
    )

    def build(self):
        self.base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "GestionInstitucional"
        self.base.mkdir(parents=True, exist_ok=True)
        self.config_path = self.base / "administracion.json"
        self.config = self._load_config()
        self.active_admin = "admin1"
        self._drag_drop = None

        outer = ctk.CTkFrame(self.body, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=22, pady=20)

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        label(title_box, "Panel de administración", 28).pack(anchor="w")
        label(
            title_box,
            "Configura la información administrativa desde una sola interfaz.",
            12, MUTED
        ).pack(anchor="w", pady=(3, 0))

        self.nav = ctk.CTkFrame(outer, fg_color=WHITE, corner_radius=12,
                                border_width=1, border_color=LINE, height=58)
        self.nav.pack(fill="x", pady=(0, 14))
        self.nav.pack_propagate(False)

        self.nav_buttons = {}
        for key, short, text_value in self.ADMIN_BUTTONS:
            btn = button(
                self.nav, f"{short}  ·  {text_value}",
                command=lambda k=key: self.show_admin(k),
                width=190 if key != "admin4" else 180,
                height=40,
                border_width=0,
                fg_color=PINK if key == self.active_admin else WHITE,
                text_color=ACCENT if key == self.active_admin else TEXT,
                hover_color=PINK,
                font=font(12, True),
            )
            btn.pack(side="left", padx=(8 if key == "admin1" else 3, 3), pady=8)
            self.nav_buttons[key] = btn

        self.content = ctk.CTkFrame(outer, fg_color="transparent")
        self.content.pack(fill="both", expand=True)
        self.show_admin("admin1")

    # ------------------------------------------------------------------
    # configuración
    def _default_config(self):
        return {
            "image": "",
            "folio": {
                "segments": [
                    {"type": "Texto", "parameter": "CVDR"},
                    {"type": "Texto", "parameter": "AÑO"},
                    {"type": "Numero", "parameter": ""},
                ]
            },
            "areas": [
                {"name": "Dirección General", "description": ""},
                {"name": "Dirección Administrativa", "description": ""},
                {"name": "Coordinación Jurídica", "description": ""},
                {"name": "Secretaría de Finanzas", "description": ""},
            ],
            "employees": [
                {"name": "Laura", "apellido1": "Méndez", "apellido2": "", "area": "Dirección General"},
            ],
        }

    def _load_config(self):
        default = self._default_config()
        if not self.config_path.exists():
            return default
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return default
            for key, value in default.items():
                if key not in data:
                    data[key] = value
            if not isinstance(data.get("folio", {}).get("segments"), list):
                data["folio"] = default["folio"]
            else:
                # La estructura solo admite un bloque numérico. Si una
                # configuración anterior tenía más, conserva el primero y
                # convierte los demás en bloques de texto.
                seen_number = False
                for segment in data["folio"]["segments"]:
                    if segment.get("type") == "Numero":
                        if seen_number:
                            segment["type"] = "Texto"
                            segment["parameter"] = ""
                        else:
                            seen_number = True
                    elif segment.get("type") not in ("Texto", "Numero"):
                        segment["type"] = "Texto"
                if not data["folio"]["segments"]:
                    data["folio"]["segments"] = default["folio"]["segments"]
                elif not any(s.get("type") == "Numero" for s in data["folio"]["segments"]):
                    data["folio"]["segments"][-1]["type"] = "Numero"
                    data["folio"]["segments"][-1]["parameter"] = ""
            if not isinstance(data.get("areas"), list):
                data["areas"] = default["areas"]
            if not isinstance(data.get("employees"), list):
                data["employees"] = default["employees"]
            else:
                # Actualiza registros del formato anterior: elimina perfil/puesto
                # y agrega los dos apellidos sin reutilizar ese dato como apellido.
                for employee in data["employees"]:
                    if not isinstance(employee, dict):
                        continue
                    employee.pop("profile", None)
                    employee.setdefault("name", "")
                    employee.setdefault("apellido1", "")
                    employee.setdefault("apellido2", "")
                    employee.setdefault("area", "")
            return data
        except (OSError, json.JSONDecodeError):
            return default

    def _save_config(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(self.config, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except OSError as error:
            messagebox.showerror("Administración", str(error), parent=self.window)
            return False
        return True

    def show_admin(self, key):
        self.active_admin = key
        for name, btn in self.nav_buttons.items():
            selected = name == key
            btn.configure(
                fg_color=PINK if selected else WHITE,
                text_color=ACCENT if selected else TEXT,
                font=font(12, True if selected else False),
            )
        for child in self.content.winfo_children():
            child.destroy()

        builders = {
            "admin1": self._build_admin1,
            "admin2": self._build_admin2,
            "admin3": self._build_admin3,
            "admin4": self._build_admin4,
        }
        builders[key]()

    # ------------------------------------------------------------------
    # Admin 1
    def _build_admin1(self):
        panel = card(self.content)
        panel.pack(fill="x", padx=2, pady=2)

        label(panel, "Admin 1 · Imagen institucional", 20, TEXT, True).pack(
            anchor="w", padx=24, pady=(22, 3)
        )
        label(
            panel,
            "Sube o cambia la imagen que se utilizará en la configuración administrativa.",
            12, MUTED
        ).pack(anchor="w", padx=24)

        body = ctk.CTkFrame(panel, fg_color="transparent")
        body.pack(fill="x", padx=24, pady=22)

        preview = ctk.CTkFrame(body, width=220, height=180, fg_color=SOFT,
                               corner_radius=12, border_width=1, border_color=LINE)
        preview.pack(side="left", padx=(0, 25))
        preview.pack_propagate(False)
        self.image_preview = ctk.CTkLabel(
            preview, text="Sin imagen", text_color=MUTED, font=font(13, True)
        )
        self.image_preview.place(relx=.5, rely=.5, anchor="center")

        controls = ctk.CTkFrame(body, fg_color="transparent")
        controls.pack(side="left", fill="x", expand=True)
        label(controls, "Imagen actual", 12, TEXT, True).pack(anchor="w")
        self.image_name = label(controls, "Ninguna seleccionada", 12, MUTED)
        self.image_name.pack(anchor="w", pady=(3, 14))
        button(
            controls, "↑  Subir / cambiar imagen", self.choose_image,
            primary=True, width=220
        ).pack(anchor="w")
        button(
            controls, "Restablecer", self.reset_image,
            width=140, height=38
        ).pack(anchor="w", pady=(9, 0))

        self.drop_zone = ctk.CTkFrame(controls, fg_color=SOFT, corner_radius=10,
                                      border_width=1, border_color=LINE, height=78)
        self.drop_zone.pack(fill="x", pady=(16, 0))
        self.drop_zone.pack_propagate(False)
        label(self.drop_zone, "Arrastra una imagen aquí", 12, TEXT, True).pack(
            pady=(12, 2)
        )
        label(self.drop_zone, "PNG, JPG, JPEG, WEBP o BMP", 10, MUTED).pack()

        # Registrar Drag & Drop directamente sobre la zona visible donde se
        # suelta la imagen. Así Windows entrega WM_DROPFILES al widget correcto.
        self._drag_drop = WindowsFileDrop(self.drop_zone, self._on_files_dropped)

        self._refresh_image_preview()

    def _on_files_dropped(self, paths):
        """Recibe archivos soltados sobre la ventana; usa el primero que sea imagen."""
        if not paths:
            return
        for path in paths:
            if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                self._save_image_from_path(path)
                return
        messagebox.showwarning(
            "Imagen",
            "El archivo arrastrado no es una imagen compatible.",
            parent=self.window,
        )

    def _save_image_from_path(self, path):
        try:
            with Image.open(path) as img:
                img.verify()
            extension = Path(path).suffix.lower() or ".png"
            destination = self.base / f"admin_image{extension}"
            for old in self.base.glob("admin_image.*"):
                if old != destination:
                    try:
                        old.unlink()
                    except OSError:
                        pass
            shutil.copy2(path, destination)
            self.config["image"] = str(destination)
            if self._save_config():
                self._refresh_image_preview()
                messagebox.showinfo(
                    "Imagen", "La imagen se guardó correctamente.", parent=self.window
                )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Imagen", f"No se pudo guardar la imagen.\n{error}", parent=self.window
            )

    def choose_image(self):
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Seleccionar imagen",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if path:
            self._save_image_from_path(path)

    def reset_image(self):
        old = self.config.get("image", "")
        if old:
            try:
                Path(old).unlink(missing_ok=True)
            except OSError:
                pass
        self.config["image"] = ""
        self._save_config()
        self._refresh_image_preview()

    def _refresh_image_preview(self):
        path = Path(self.config.get("image", "")) if self.config.get("image") else None
        if path and path.is_file():
            try:
                with Image.open(path) as img:
                    image = img.convert("RGB")
                image.thumbnail((190, 150), Image.Resampling.LANCZOS)
                self.admin_image = ctk.CTkImage(light_image=image, dark_image=image,
                                                size=image.size)
                self.image_preview.configure(image=self.admin_image, text="")
                self.image_name.configure(text=path.name)
                return
            except OSError:
                pass
        self.image_preview.configure(image=None, text="Sin imagen")
        self.image_name.configure(text="Ninguna seleccionada")

    # ------------------------------------------------------------------
    # Admin 2
    def _build_admin2(self):
        panel = card(self.content)
        panel.pack(fill="x", padx=2, pady=2)

        label(panel, "Admin 2 · Modificar estructura de folio", 20, TEXT, True).pack(
            anchor="w", padx=24, pady=(22, 3)
        )
        label(
            panel,
            "Agrega los bloques que quieras. Cada bloque puede ser Texto o Número. "
            "Siempre debe existir al menos un bloque numérico.",
            12, MUTED
        ).pack(anchor="w", padx=24)

        self.folio_rows = ctk.CTkFrame(panel, fg_color="transparent")
        self.folio_rows.pack(fill="x", padx=24, pady=(18, 8))

        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 22))
        button(actions, "+  Agregar combobox", self.add_folio_segment,
               width=180).pack(side="left")
        button(actions, "Guardar estructura", self.save_folio,
               primary=True, width=180).pack(side="right")

        self.folio_hint = label(panel, "", 11, MUTED)
        self.folio_hint.pack(anchor="w", padx=24, pady=(0, 18))
        self._render_folio_segments()

    def _render_folio_segments(self):
        for child in self.folio_rows.winfo_children():
            child.destroy()
        self.folio_controls = []

        segments = self.config["folio"].get("segments", [])
        if not segments:
            segments = [{"type": "Numero", "parameter": ""}]
            self.config["folio"]["segments"] = segments

        for index, segment in enumerate(segments, 1):
            row = ctk.CTkFrame(self.folio_rows, fg_color=SOFT, corner_radius=9)
            row.pack(fill="x", pady=4)

            label(row, f"Bloque {index}", 11, TEXT, True, width=80).pack(
                side="left", padx=(12, 8), pady=9
            )

            current_type = segment.get("type", "Texto")
            number_exists = any(
                s.get("type") == "Numero" for j, s in enumerate(segments) if j != index - 1
            )
            combo_values = ["Texto", "Numero"] if current_type == "Numero" or not number_exists else ["Texto"]
            combo = select(row, combo_values, width=120)
            combo.set(current_type)
            combo.pack(side="left", padx=5, pady=8)

            parameter = None
            if combo.get() == "Texto":
                parameter = entry(row, "Parámetro del texto", height=38)
                parameter.insert(0, str(segment.get("parameter", "")))
                parameter.pack(side="left", fill="x", expand=True, padx=7, pady=8)
            else:
                label(row, "Número consecutivo", 11, MUTED).pack(
                    side="left", padx=12
                )

            remove = button(
                row, "×", lambda i=index - 1: self.remove_folio_segment(i),
                width=34, height=34, border_width=0, text_color=ACCENT
            )
            remove.pack(side="right", padx=8)

            def changed(value, i=index - 1):
                self._change_segment_type(i, value)

            combo.configure(command=changed)
            self.folio_controls.append((combo, parameter))

        text_count = sum(
            1 for combo, _ in self.folio_controls if combo.get() == "Texto"
        )
        number_count = len(self.folio_controls) - text_count
        self.folio_hint.configure(
            text=f"{len(self.folio_controls)} combobox(s): {text_count} parámetro(s) "
                 f"de texto · {number_count} bloque(s) numérico(s)."
        )

    def _change_segment_type(self, index, value):
        segments = self.config["folio"]["segments"]
        if value == "Numero" and any(
            s.get("type") == "Numero" for j, s in enumerate(segments) if j != index
        ):
            messagebox.showwarning(
                "Estructura de folio",
                "Solo puede existir un bloque de tipo Número.",
                parent=self.window,
            )
            self._render_folio_segments()
            return
        segments[index]["type"] = value
        if value == "Numero":
            segments[index]["parameter"] = ""
        self._render_folio_segments()

    def add_folio_segment(self):
        segments = self.config["folio"]["segments"]
        if any(s.get("type") == "Numero" for s in segments):
            segments.append({"type": "Texto", "parameter": ""})
        else:
            segments.append({"type": "Numero", "parameter": ""})
        self._render_folio_segments()

    def remove_folio_segment(self, index):
        segments = self.config["folio"]["segments"]
        if len(segments) <= 1:
            messagebox.showwarning(
                "Estructura de folio",
                "Debe existir al menos un bloque.",
                parent=self.window
            )
            return
        del segments[index]
        if not any(s.get("type") == "Numero" for s in segments):
            segments[-1]["type"] = "Numero"
            segments[-1]["parameter"] = ""
        self._render_folio_segments()

    def save_folio(self):
        segments = []
        numeric = 0
        for combo, parameter in self.folio_controls:
            kind = combo.get()
            if kind == "Numero":
                numeric += 1
                value = ""
            else:
                value = parameter.get().strip() if parameter else ""
                if not value:
                    messagebox.showwarning(
                        "Estructura de folio",
                        "Completa todos los parámetros de los bloques de texto.",
                        parent=self.window
                    )
                    return
            segments.append({"type": kind, "parameter": value})

        if numeric != 1:
            messagebox.showwarning(
                "Estructura de folio",
                "Debe existir exactamente un bloque de tipo Número. "
                "Los demás bloques serán parámetros de texto.",
                parent=self.window
            )
            return

        self.config["folio"]["segments"] = segments
        if self._save_config():
            messagebox.showinfo("Estructura de folio", "La estructura se guardó correctamente.",
                                parent=self.window)

    # ------------------------------------------------------------------
    # Admin 3 · Empleados
    def _build_admin3(self):
        self._build_catalog(
            title="Admin 3 · Empleados",
            subtitle="Ingresa, borra y edita empleados y su información.",
            kind="employees",
            fields=(("name", "Nombre"),
                    ("apellido1", "Apellido 1"),
                    ("apellido2", "Apellido 2"),
                    ("area", "Área")),
        )

    def _build_catalog(self, title, subtitle, kind, fields):
        panel = card(self.content)
        panel.pack(fill="x", padx=2, pady=2)
        label(panel, title, 20, TEXT, True).pack(anchor="w", padx=24, pady=(22, 3))
        label(panel, subtitle, 12, MUTED).pack(anchor="w", padx=24)

        form = ctk.CTkFrame(panel, fg_color=SOFT, corner_radius=10)
        form.pack(fill="x", padx=24, pady=18)
        form.grid_columnconfigure(tuple(range(len(fields))), weight=1)

        controls = {}
        for col, (key, caption) in enumerate(fields):
            label(form, caption, 10, TEXT, True).grid(
                row=0, column=col, sticky="w", padx=(12 if col == 0 else 6, 6), pady=(10, 3)
            )
            controls[key] = entry(form, caption, height=38)
            controls[key].grid(
                row=1, column=col, sticky="ew",
                padx=(12 if col == 0 else 6, 6), pady=(0, 10)
            )

        editing = {"index": None}

        def clear():
            for control in controls.values():
                control.delete(0, "end")
            editing["index"] = None
            save_btn.configure(text="Agregar")

        def save_item():
            values = {key: control.get().strip() for key, control in controls.items()}
            if not values.get("name"):
                messagebox.showwarning("Administración", "El nombre es obligatorio.",
                                       parent=self.window)
                return

            records = self.config[kind]
            if editing["index"] is None:
                records.append(values)
            else:
                records[editing["index"]] = values
            if self._save_config():
                clear()
                render()

        save_btn = button(form, "Agregar", save_item, primary=True, width=110, height=38)
        save_btn.grid(row=1, column=len(fields), padx=8, pady=10)
        # El botón se ubica después de los campos sin alterar el estilo general.
        form.grid_columnconfigure(len(fields), weight=0)

        list_card = card(panel)
        list_card.pack(fill="x", padx=24, pady=(0, 24))
        head = ctk.CTkFrame(list_card, fg_color=SOFT, corner_radius=8)
        head.pack(fill="x", padx=10, pady=10)
        label(head, "REGISTROS", 9, MUTED, True).pack(side="left", padx=12, pady=8)
        self.catalog_rows = ctk.CTkFrame(list_card, fg_color="transparent")
        self.catalog_rows.pack(fill="x", padx=10, pady=(0, 10))

        def render():
            for child in self.catalog_rows.winfo_children():
                child.destroy()
            records = self.config.get(kind, [])
            if not records:
                label(self.catalog_rows, "No hay registros.", 12, MUTED).pack(pady=18)
                return
            for index, record in enumerate(records):
                row = ctk.CTkFrame(self.catalog_rows, fg_color=WHITE, corner_radius=8,
                                   border_width=1, border_color=LINE, height=48)
                row.pack(fill="x", pady=3)
                row.grid_columnconfigure(0, weight=1)
                summary = " · ".join(str(record.get(key, "")) for key, _ in fields if record.get(key))
                label(row, summary, 11, TEXT, anchor="w").grid(
                    row=0, column=0, sticky="ew", padx=14, pady=10
                )
                button(
                    row, "Editar", lambda i=index: edit_item(i),
                    width=70, height=30, border_width=0, text_color=ACCENT
                ).grid(row=0, column=1, padx=4)
                button(
                    row, "Borrar", lambda i=index: delete_item(i),
                    width=70, height=30, border_width=0, text_color=ACCENT
                ).grid(row=0, column=2, padx=(4, 10))

        def edit_item(index):
            record = self.config[kind][index]
            for key, control in controls.items():
                control.delete(0, "end")
                control.insert(0, str(record.get(key, "")))
            editing["index"] = index
            save_btn.configure(text="Guardar cambios")
            controls["name"].focus_set()

        def delete_item(index):
            record = self.config[kind][index]
            if not messagebox.askyesno(
                "Confirmar eliminación",
                f"¿Borrar {record.get('name', 'este registro')}?",
                parent=self.window
            ):
                return
            del self.config[kind][index]
            self._save_config()
            if editing["index"] == index:
                clear()
            render()

        render()

    # ------------------------------------------------------------------
    # Admin 4
    def _build_admin4(self):
        panel = card(self.content)
        panel.pack(fill="x", padx=2, pady=2)

        label(panel, "Admin 4 · Generar reporte", 20, TEXT, True).pack(
            anchor="w", padx=24, pady=(22, 3)
        )
        label(
            panel,
            "Ingresa la fecha de inicio y la fecha final. El reporte incluirá ambas fechas.",
            12, MUTED
        ).pack(anchor="w", padx=24)

        form = ctk.CTkFrame(panel, fg_color=SOFT, corner_radius=10)
        form.pack(fill="x", padx=24, pady=18)
        form.grid_columnconfigure((0, 1), weight=1)

        label(form, "Fecha de inicio", 11, TEXT, True).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        label(form, "Fecha final", 11, TEXT, True).grid(
            row=0, column=1, sticky="w", padx=12, pady=(12, 4)
        )
        self.report_start = ctk.CTkButton(
            form, text="Seleccionar fecha", command=lambda: self._open_date_picker("start"),
            height=40, corner_radius=9, fg_color=WHITE, hover_color=PINK,
            text_color=TEXT, border_width=1, border_color=LINE, font=font(13),
        )
        self.report_end = ctk.CTkButton(
            form, text="Seleccionar fecha", command=lambda: self._open_date_picker("end"),
            height=40, corner_radius=9, fg_color=WHITE, hover_color=PINK,
            text_color=TEXT, border_width=1, border_color=LINE, font=font(13),
        )
        self.report_start.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.report_end.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 12))
        self.report_start_date = None
        self.report_end_date = None

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        button(actions, "Generar reporte", self.generate_report,
               primary=True, width=170).pack(side="left")
        button(actions, "Descargar ZIP", self.download_report_zip,
               width=150).pack(side="left", padx=8)

        self.report_status = label(panel, "Elige un rango de fechas para generar el reporte.",
                                   11, MUTED)
        self.report_status.pack(anchor="w", padx=24, pady=(0, 20))

        self.report_preview = card(panel)
        self.report_preview.pack(fill="x", padx=24, pady=(0, 24))
        label(self.report_preview, "Vista previa", 14, TEXT, True).pack(
            anchor="w", padx=16, pady=(14, 5)
        )
        self.report_text = ctk.CTkTextbox(
            self.report_preview, height=220, fg_color=SOFT, text_color=TEXT,
            border_width=1, border_color=LINE, corner_radius=8,
            font=font(11)
        )
        self.report_text.pack(fill="x", padx=16, pady=(0, 16))

    def _open_date_picker(self, which):
        selected = self.report_start_date if which == "start" else self.report_end_date
        if selected is None:
            selected = datetime.now().date()
        year, month = selected.year, selected.month

        popup = ctk.CTkToplevel(self.window)
        popup.title("Seleccionar fecha")
        popup.geometry("330x330")
        popup.resizable(False, False)
        popup.transient(self.window)
        popup.grab_set()

        header = ctk.CTkFrame(popup, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(14, 8))
        title = label(header, "", 15, TEXT, True)
        title.pack(side="left", expand=True)

        grid = ctk.CTkFrame(popup, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        state = {"year": year, "month": month}

        def select_day(day):
            value = datetime(state["year"], state["month"], day).date()
            text_value = value.strftime("%Y-%m-%d")
            if which == "start":
                self.report_start_date = value
                self.report_start.configure(text=text_value)
            else:
                self.report_end_date = value
                self.report_end.configure(text=text_value)
            popup.destroy()

        def draw():
            for child in grid.winfo_children():
                child.destroy()
            title.configure(text=f"{pycalendar.month_name[state['month']]} {state['year']}")
            nav = ctk.CTkFrame(grid, fg_color="transparent")
            nav.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 7))
            button(nav, "‹", lambda: move(-1), width=34, height=30, border_width=0).pack(side="left")
            button(nav, "›", lambda: move(1), width=34, height=30, border_width=0).pack(side="right")
            for col, name in enumerate(("L", "M", "M", "J", "V", "S", "D")):
                label(grid, name, 10, MUTED, True).grid(row=1, column=col, pady=3)
            cal = pycalendar.monthcalendar(state["year"], state["month"])
            for r, week in enumerate(cal, start=2):
                for c, day in enumerate(week):
                    if day:
                        button(grid, str(day), lambda d=day: select_day(d),
                               width=36, height=32, border_width=0,
                               fg_color=PINK if selected == datetime(state["year"], state["month"], day).date() else WHITE,
                               text_color=ACCENT if selected == datetime(state["year"], state["month"], day).date() else TEXT,
                               hover_color=PINK).grid(row=r, column=c, padx=2, pady=2)

        def move(delta):
            new_month = state["month"] + delta
            if new_month < 1:
                state["month"] = 12
                state["year"] -= 1
            elif new_month > 12:
                state["month"] = 1
                state["year"] += 1
            else:
                state["month"] = new_month
            draw()

        draw()

    def _parse_report_dates(self):
        start = self.report_start_date
        end = self.report_end_date
        if start is None or end is None:
            messagebox.showwarning(
                "Reporte", "Selecciona la fecha de inicio y la fecha final en los calendarios.",
                parent=self.window
            )
            return None
        if start > end:
            messagebox.showwarning(
                "Reporte", "La fecha de inicio no puede ser posterior a la fecha final.",
                parent=self.window
            )
            return None
        return start, end

    def _report_records(self):
        dates = self._parse_report_dates()
        if not dates:
            return None
        start, end = dates
        records = []
        for doc in self.app.store.leer():
            raw = doc.creado_el or doc.reservado_el
            if not raw:
                continue
            try:
                current = datetime.fromisoformat(raw).date()
            except ValueError:
                continue
            if start <= current <= end:
                records.append(doc)
        return start, end, records

    def _report_content(self, start, end, records):
        lines = [
            "REPORTE DE GESTIÓN DE CORRESPONDENCIA",
            "SISTEMA DE CONTROL DOCUMENTAL — CVDR DURANGO",
            "",
            f"Fecha de inicio: {start.isoformat()}",
            f"Fecha final: {end.isoformat()}",
            f"Total de registros: {len(records)}",
            "",
            "FOLIO | ESTADO | ASUNTO | ÁREA EMISORA | RECEPCIÓN | ELABORÓ | REVISÓ | AUTORIZÓ | FECHA",
        ]
        for doc in records:
            fecha = doc.creado_el or doc.reservado_el
            lines.append(" | ".join([
                doc.folio, doc.estado, doc.asunto, doc.area_emisora, doc.recepcion,
                doc.elaboro, doc.reviso, doc.autorizo, fecha
            ]))
        return "\n".join(lines)

    def generate_report(self):
        result = self._report_records()
        if not result:
            return
        start, end, records = result
        content = self._report_content(start, end, records)
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", content)
        self.report_status.configure(
            text=f"Reporte generado: {len(records)} registro(s) entre "
                 f"{start.isoformat()} y {end.isoformat()}.",
            text_color=GREEN
        )

    def download_report_zip(self):
        result = self._report_records()
        if not result:
            return
        start, end, records = result

        destination = filedialog.asksaveasfilename(
            parent=self.window,
            title="Guardar reporte ZIP",
            defaultextension=".zip",
            initialfile=f"reporte_{start.isoformat()}_{end.isoformat()}.zip",
            filetypes=[("Archivo ZIP", "*.zip")],
        )
        if not destination:
            return

        content = self._report_content(start, end, records)
        try:
            with tempfile.TemporaryDirectory() as temp:
                temp_path = Path(temp)
                txt = temp_path / "reporte.txt"
                csv_path = temp_path / "reporte.csv"
                txt.write_text(content, encoding="utf-8-sig")

                with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
                    writer = csv.writer(fh)
                    writer.writerow(["Fecha de inicio", start.isoformat()])
                    writer.writerow(["Fecha final", end.isoformat()])
                    writer.writerow([])
                    writer.writerow([
                        "Folio", "Estado", "Asunto", "Área emisora", "Recepción",
                        "Elaboró", "Revisó", "Autorizó", "Fecha"
                    ])
                    for doc in records:
                        writer.writerow([
                            doc.folio, doc.estado, doc.asunto, doc.area_emisora,
                            doc.recepcion, doc.elaboro, doc.reviso, doc.autorizo,
                            doc.creado_el or doc.reservado_el
                        ])

                with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.write(txt, "reporte.txt")
                    archive.write(csv_path, "reporte.csv")
            messagebox.showinfo(
                "Reporte", "El reporte ZIP se generó correctamente.",
                parent=self.window
            )
        except OSError as error:
            messagebox.showerror("Reporte", f"No se pudo generar el ZIP.\n{error}",
                                 parent=self.window)
