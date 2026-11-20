import customtkinter as ctk
from tkinter import messagebox

from screen import Screen
from ui_helpers import (
    ACCENT, GREEN, LINE, MUTED, PINK, SOFT, TEXT, WHITE, WINE, BLUE,
    UIComponents, button, card, entry, font, label, select,
)

RECORDS = [
    ("REC-1048", "RECIBIDA", "Solicitud de ampliación presupuestal", "Secretaría de Finanzas", "Dirección Administrativa", "Alta", "AR", "A. Ríos", "Por asignar", "Hoy · 16:00"),
    ("REC-1047", "RECIBIDA", "Invitación a sesión del Comité Técnico", "Coordinación Jurídica", "Secretaría Particular", "Media", "MD", "M. Díaz", "En atención", "Mañana"),
    ("ENV-0831", "ENVIADA", "Respuesta al oficio DGA/229/2026", "Dirección General", "Órgano Interno de Control", "Normal", "LS", "L. Soto", "Respondida", "04 oct"),
    ("REC-1046", "RECIBIDA", "Actualización del padrón de proveedores", "Unidad de Recursos Materiales", "Adquisiciones", "Media", "JL", "J. León", "Turnada", "07 oct"),
    ("REC-1045", "RECIBIDA", "Informe trimestral de actividades", "Subdirección de Planeación", "Dirección General", "Alta", "CM", "C. Mora", "En atención", "08 oct"),
    ("ENV-0830", "ENVIADA", "Confirmación de mesa interinstitucional", "Enlace de Vinculación", "Secretaría Técnica", "Normal", "PC", "P. Cruz", "Respondida", "02 oct"),
]

STATUS = {
    "Por asignar": ("#FFF7D5", "#775500"),
    "En atención": ("#EAF2FA", "#276C9E"),
    "Respondida": ("#E6F4EE", "#22865E"),
    "Turnada": ("#F5E8EE", "#801537"),
}

PRIORITY = {
    "Alta": ACCENT,
    "Media": "#B78600",
    "Normal": MUTED,
}

TOTAL = len(RECORDS)
PENDIENTES = sum(1 for record in RECORDS if record[8] != "Respondida")


class HomeScreen(Screen):
    """Bandeja general de correspondencia."""

    nav_key = "Correspondencia"
    scrollable = False

    # Opciones del menú lateral que filtran esta bandeja.
    CATEGORIAS = {
        "Correspondencia · 18": "all",
        "Por asignar · 7": "Por asignar",
        "Seguimiento · 12": "seguimiento",
        "Enviada": "enviada",
    }

    def build(self):
        self.category = "all"

        self.content = ctk.CTkFrame(
            self.body, fg_color="transparent"
        )
        self.content.pack(
            fill="both", expand=True, padx=22, pady=12
        )

        header = ctk.CTkFrame(
            self.content, fg_color="transparent"
        )
        header.pack(fill="x", pady=(0, 10))

        # Logo del CVDR (assets/cvdr.jpg o ../assets/cvdr.jpg).
        self.logo_image = UIComponents.image("cvdr.jpg", 72)
        if self.logo_image is not None:
            ctk.CTkLabel(
                header, image=self.logo_image, text=""
            ).pack(side="left", padx=(0, 16))

        heading = ctk.CTkFrame(
            header, fg_color="transparent"
        )
        heading.pack(side="left")

        label(heading, "Correspondencia", 28).pack(anchor="w")

        label(
            heading,
            "Bandeja general de documentos recibidos y enviados",
            13,
            MUTED
        ).pack(anchor="w")

        button(
            header,
            "✦  Crear Oficio",
            self.app.nuevo_oficio,
            color=ACCENT,
            width=226
        ).pack(side="right", anchor="n", pady=8)

        metrics = ctk.CTkFrame(
            self.content, fg_color="transparent"
        )
        metrics.pack(fill="x", pady=(0, 12))

        for index in range(3):
            metrics.grid_columnconfigure(
                index, weight=1, uniform="metrics"
            )

        metric_data = [
            ("RECIBIDA", "24", ACCENT, PINK, "▣", 1),
            ("CONCLUIDA", "126", GREEN, "#E6F4EE", "✓", 1),
            ("PENDIENTES", "24", ACCENT, PINK, "◷", 1),
        ]

        for index, (
            title, value, color, soft, symbol, progress
        ) in enumerate(metric_data):

            tile = card(metrics, height=92)
            tile.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=(0, 16 if index < len(metric_data) - 1 else 0)
            )
            tile.grid_propagate(False)
            tile.grid_columnconfigure(0, weight=1)

            label(
                tile, title, 10, MUTED, True, height=16
            ).grid(
                row=0, column=0, sticky="w",
                padx=16, pady=(10, 0)
            )

            amount = ctk.CTkFrame(
                tile, fg_color="transparent"
            )
            amount.grid(row=1, column=0, sticky="w", padx=16)

            label(amount, value, 26).pack(side="left")

            label(
                tile, symbol, 18, color,
                width=30, height=30,
                fg_color=soft, corner_radius=8
            ).place(relx=1, x=-14, y=12, anchor="ne")

            bar = ctk.CTkProgressBar(
                tile,
                height=4,
                progress_color=color,
                fg_color=SOFT,
                corner_radius=2
            )
            bar.grid(
                row=2, column=0, sticky="ew",
                padx=16, pady=(2, 12)
            )
            bar.set(progress)

        self.table_card = card(self.content)
        self.table_card.pack(fill="both", expand=True)

        table_top = ctk.CTkFrame(
            self.table_card, fg_color="transparent"
        )
        table_top.pack(fill="x", padx=20, pady=(12, 4))

        title_frame = ctk.CTkFrame(
            table_top, fg_color="transparent"
        )
        title_frame.pack(side="left")

        label(
            title_frame, "Correspondencia reciente", 21
        ).pack(anchor="w")

        label(
            title_frame,
            f"{PENDIENTES} movimientos pendientes de revisión",
            12,
            MUTED
        ).pack(anchor="w")

        button(
            table_top,
            "Ver bandeja completa  →",
            self.reset_filters,
            border_width=0,
            height=30,
            width=170,
            font=font(12, "bold")
        ).pack(side="right")

        filters = ctk.CTkFrame(
            self.table_card, fg_color="transparent"
        )
        filters.pack(fill="x", padx=20, pady=(0, 10))

        self.filter_entry = entry(
            filters,
            "⌕  Filtrar esta bandeja...",
            fg_color=SOFT,
            border_width=0,
            height=30
        )
        self.filter_entry.pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )

        self.state_filter = select(
            filters,
            ["Estado", *STATUS.keys()],
            command=lambda value: self.filter_rows(),
            width=125,
            height=30,
            state="readonly",
            fg_color=SOFT,
            border_width=0,
            button_color=LINE,
            button_hover_color="#D1D5DB"
        )
        self.state_filter.set("Estado")
        self.state_filter.pack(side="left", padx=(0, 8))

        self.priority_filter = select(
            filters,
            ["Prioridad", "Alta", "Media", "Normal"],
            command=lambda value: self.filter_rows(),
            width=110,
            height=30,
            state="readonly",
            fg_color=SOFT,
            border_width=0,
            button_color=LINE,
            button_hover_color="#D1D5DB"
        )
        self.priority_filter.set("Prioridad")
        self.priority_filter.pack(side="left", padx=(0, 8))

        self.rows = ctk.CTkScrollableFrame(
            self.table_card,
            fg_color=WHITE,
            corner_radius=0,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=WINE
        )
        self.rows.pack(
            fill="both", expand=True, padx=1, pady=0
        )

        footer = ctk.CTkFrame(
            self.table_card, fg_color="transparent"
        )
        footer.pack(fill="x", padx=16, pady=8)

        self.count_label = label(
            footer, f"Mostrando 1–{TOTAL} de {TOTAL} registros", 10, MUTED
        )
        self.count_label.pack(side="left")

        paging = ctk.CTkFrame(
            footer, fg_color="transparent"
        )
        paging.pack(side="right")

        for page_text in ["‹", "1", "2", "3", "›"]:
            button(
                paging,
                page_text,
                self.reset_filters if page_text == "1"
                else lambda: self.unavailable("Más registros"),
                width=27,
                height=27,
                color=ACCENT if page_text == "1" else WHITE,
                text_color=WHITE if page_text == "1" else MUTED,
                border_width=0,
                corner_radius=4,
                font=font(11)
            ).pack(side="left", padx=2)

        self.filter_entry.bind(
            "<KeyRelease>", self.filter_rows
        )
        self.render_rows(RECORDS)

    def _is_filtered(self):
        return (
            bool(self.filter_entry.get().strip())
            or self.state_filter.get() != "Estado"
            or self.priority_filter.get() != "Prioridad"
            or self.category != "all"
        )

    def on_show(self, category=None):
        if category is None:
            # Solo se reconstruye la tabla si había filtros aplicados.
            if self._is_filtered():
                self.reset_filters()
        else:
            self.category = category
            self.filter_rows()

    def handle_menu(self, name):
        if name in self.CATEGORIAS:
            self.category = self.CATEGORIAS[name]
            self.filter_rows()
            return True
        return False

    def reset_filters(self):
        self.category = "all"
        self.filter_entry.delete(0, "end")
        self.state_filter.set("Estado")
        self.priority_filter.set("Prioridad")
        self.filter_rows()

    @staticmethod
    def matching(
        records,
        query="",
        state="Estado",
        priority="Prioridad",
        category="all"
    ):
        terms = query.casefold().split()

        return [
            record for record in records
            if all(
                term in " ".join(record).casefold()
                for term in terms
            )
            and (state == "Estado" or record[8] == state)
            and (
                priority == "Prioridad"
                or record[5] == priority
            )
            and (
                category == "all"
                or record[8] == category
                or (
                    category == "seguimiento"
                    and record[8] in ("En atención", "Turnada")
                )
                or (
                    category == "enviada"
                    and record[1] == "ENVIADA"
                )
            )
        ]

    def filter_rows(self, event=None):
        query = self.filter_entry.get()

        records = self.matching(
            RECORDS,
            query,
            self.state_filter.get(),
            self.priority_filter.get(),
            self.category
        )

        self.render_rows(records)

        filtered = (
            bool(query.strip())
            or self.state_filter.get() != "Estado"
            or self.priority_filter.get() != "Prioridad"
            or self.category != "all"
        )

        if filtered:
            self.count_label.configure(
                text=f"{len(records)} resultados de {len(RECORDS)} registros"
            )
        else:
            self.count_label.configure(
                text=f"Mostrando 1–{TOTAL} de {TOTAL} registros"
            )

    def render_rows(self, records):
        for child in self.rows.winfo_children():
            child.destroy()

        widths = [120, 360, 240, 180, 150, 160]

        def row_frame(background, height):
            frame = ctk.CTkFrame(
                self.rows,
                fg_color=background,
                corner_radius=0,
                height=height,
                border_width=0
            )

            frame.pack(fill="x", padx=0, pady=0)
            frame.pack_propagate(False)
            frame.grid_propagate(False)

            for index, width in enumerate(widths):
                frame.grid_columnconfigure(
                    index,
                    minsize=width,
                    weight=1 if index == 1 else 0
                )

            frame.grid_rowconfigure(0, weight=1)

            return frame

        head = row_frame(SOFT, 28)

        columns = [
            "FOLIO",
            "ASUNTO / REMITENTE",
            "ÁREA / PRIORIDAD",
            "RESPONSABLE",
            "ESTADO",
            "VENCE"
        ]

        for index, name in enumerate(columns):
            label(
                head, name, 10, MUTED, True, anchor="w"
            ).grid(
                row=0,
                column=index,
                sticky="w",
                padx=14,
                pady=0
            )

        if not records:
            label(
                self.rows,
                "No se encontraron resultados.",
                13,
                MUTED,
                height=40
            ).pack(fill="x", pady=0)
            return

        for record in records:
            row = row_frame(WHITE, 46)

            folio = ctk.CTkFrame(
                row, fg_color="transparent", width=1, height=1
            )
            folio.grid(
                row=0, column=0, sticky="nsew", padx=14, pady=0
            )

            label(
                folio, record[0], 11, ACCENT, anchor="w"
            ).place(x=0, rely=0.27, anchor="w")

            label(
                folio, record[1], 9, MUTED, True, anchor="w"
            ).place(x=0, rely=0.74, anchor="w")

            subject = ctk.CTkFrame(
                row, fg_color="transparent", width=1, height=1
            )
            subject.grid(
                row=0, column=1, sticky="nsew", padx=14, pady=0
            )

            label(
                subject,
                self.fit_subject(record[2], 900),
                12,
                anchor="w"
            ).place(x=0, rely=0.27, anchor="w")

            label(
                subject, record[3], 9, MUTED, anchor="w"
            ).place(x=0, rely=0.74, anchor="w")

            area = ctk.CTkFrame(
                row, fg_color="transparent", width=1, height=1
            )
            area.grid(
                row=0, column=2, sticky="nsew", padx=14, pady=0
            )

            label(
                area,
                record[4],
                9,
                anchor="w",
                justify="left"
            ).place(x=0, rely=0.27, anchor="w")

            label(
                area,
                "●  " + record[5],
                9,
                PRIORITY[record[5]],
                anchor="w"
            ).place(x=0, rely=0.74, anchor="w")

            responsible = ctk.CTkFrame(
                row, fg_color="transparent", width=1, height=1
            )
            responsible.grid(
                row=0, column=3, sticky="nsew", padx=14, pady=0
            )

            label(
                responsible,
                record[6],
                9,
                TEXT,
                width=30,
                height=30,
                fg_color=SOFT,
                corner_radius=15
            ).place(relx=0, rely=0.5, anchor="w")

            label(
                responsible, record[7], 10
            ).place(x=42, rely=0.5, anchor="w")

            status = ctk.CTkFrame(
                row, fg_color="transparent", width=1, height=1
            )
            status.grid(
                row=0, column=4, sticky="nsew", padx=14, pady=0
            )

            bg, fg = STATUS[record[8]]

            label(
                status,
                record[8],
                9,
                fg,
                True,
                height=20,
                fg_color=bg,
                corner_radius=10
            ).place(relx=0, rely=0.5, anchor="w")

            due = ctk.CTkFrame(
                row, fg_color="transparent", width=1, height=1
            )
            due.grid(
                row=0, column=5, sticky="nsew", padx=14, pady=0
            )

            label(
                due,
                record[9],
                10,
                ACCENT if "Hoy" in record[9] else MUTED
            ).place(relx=0, rely=0.5, anchor="w")

            button(
                due,
                "⋮",
                lambda r=record: self.record_detail(r),
                width=24,
                height=24,
                border_width=0,
                text_color=WHITE,
                color=ACCENT,
                corner_radius=6
            ).place(relx=1, x=-6, rely=0.5, anchor="e")

            ctk.CTkFrame(
                self.rows,
                height=1,
                fg_color=LINE,
                corner_radius=0
            ).pack(fill="x", padx=14, pady=(4, 4))

    @staticmethod
    def fit_subject(text, max_width):
        measure = font(12)

        if measure.measure(text) <= max_width:
            return text

        shortened = text.rstrip(".")

        while (
            shortened
            and measure.measure(shortened + "…") > max_width
        ):
            shortened = shortened[:-1]

        return shortened.rstrip() + "…"

    def record_detail(self, record):
        messagebox.showinfo(
            record[0],
            "\n".join([
                record[2],
                record[3],
                record[4],
                "Prioridad: " + record[5],
                "Responsable: " + record[7],
                "Estado: " + record[8],
                "Vence: " + record[9]
            ]),
            parent=self.window
        )