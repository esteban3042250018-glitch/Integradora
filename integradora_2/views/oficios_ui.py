"""Dashboard institucional y gestión de oficios por área."""
from pathlib import Path
import os
import shutil
from tkinter import filedialog, messagebox
import customtkinter as ctk
from views.ui_helpers import Shell, BG, WHITE, TEXT, MUTED, ACCENT, GREEN, BLUE, PINK, LINE, button, card, entry, label
from model.oficios import (
    listar_oficios_dashboard, listar_oficios_area, obtener_archivos_oficio,
    marcar_creado, marcar_enviado, marcar_aprobado, marcar_acusado,
    obtener_historial_estados,
)

COLORES = {
    'creado': ('#FFF4D6', '#946200'), 'creado / reservado': ('#FFF4D6', '#946200'),
    'enviado': ('#E8F1FF', '#2459A6'), 'aprobado': ('#E7F6EC', '#217346'),
    'acusado': ('#F2EAFE', '#7040A0'),
}


def _fecha_texto(valor):
    if hasattr(valor, 'strftime'):
        return valor.strftime('%d/%m/%Y %H:%M')
    return str(valor or 'Sin registro')


def _ruta_archivo_principal(registro):
    ruta = Path(str(registro.get('ruta') or '')).expanduser()
    if ruta.is_file():
        return ruta
    if ruta.is_dir():
        candidatos = sorted([p for p in ruta.iterdir() if p.is_file() and p.suffix.lower() in {'.pdf', '.doc', '.docx'}])
        # Priorizar PDF para vista rápida; si no existe, abrir el documento Word.
        return next((p for p in candidatos if p.suffix.lower() == '.pdf'), candidatos[0] if candidatos else None)
    return None


def _carpeta_oficio(registro):
    ruta = Path(str(registro.get('ruta') or '')).expanduser()
    return ruta if ruta.is_dir() or not ruta.suffix else ruta.parent


def _copiar_adjunto(registro, tipo, origen=None):
    if not origen:
        origen = filedialog.askopenfilename(
            title=f'Seleccionar {tipo.lower()}',
            filetypes=[('Documentos e imágenes', '*.pdf *.doc *.docx *.png *.jpg *.jpeg *.webp'), ('Todos los archivos', '*.*')],
        )
    if not origen:
        return None
    origen = Path(origen).expanduser()
    if not origen.is_file():
        raise ValueError('El archivo seleccionado no existe.')
    carpeta = _carpeta_oficio(registro)
    if not str(carpeta) or str(carpeta) == '.':
        raise ValueError('El oficio no tiene una ruta de carpeta válida registrada.')
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f'{tipo}_{registro["folio"]}{origen.suffix.lower()}'
    if destino.exists():
        from datetime import datetime
        destino = carpeta / f'{tipo}_{registro["folio"]}_{datetime.now():%Y%m%d_%H%M%S}{origen.suffix.lower()}'
    shutil.copy2(origen, destino)
    return str(destino.resolve())


def _activar_drop(widget, callback):
    """Activa drag-and-drop si TkDND está instalado; conserva selector como alternativa."""
    try:
        from tkinterdnd2 import TkinterDnD
        TkinterDnD._require(widget)
        widget.tk.call('package', 'require', 'tkdnd')
        widget.tk.call('tkdnd::drop_target', 'register', widget._w, '*')
        def recibir(datos):
            try:
                # %D entrega la lista Tcl de rutas y respeta espacios en nombres.
                rutas = widget.tk.splitlist(datos)
                if rutas:
                    callback(str(rutas[0]))
            except Exception as error:
                messagebox.showerror('Arrastrar archivo', str(error), parent=widget)
        comando = widget.register(recibir)
        widget.tk.call('bind', widget._w, '<<Drop>>', f'{comando} %D')
        return True
    except Exception:
        return False


class ListaOficiosApp(Shell):
    modo = 'dashboard'

    def __init__(self, master):
        activo = 'Dashboard' if self.modo == 'dashboard' else 'Enviados'
        super().__init__(master, activo)
        self.title('Gestión Institucional - ' + activo)
        self.registros = []
        contenido = ctk.CTkFrame(self.body, fg_color='transparent')
        contenido.pack(fill='both', expand=True, padx=24, pady=22)
        cabecera = ctk.CTkFrame(contenido, fg_color='transparent')
        cabecera.pack(fill='x', pady=(0, 16))
        textos = ctk.CTkFrame(cabecera, fg_color='transparent')
        textos.pack(side='left')
        label(textos, 'Dashboard institucional' if self.modo == 'dashboard' else 'Oficios enviados por mi área', 27, TEXT, True).pack(anchor='w')
        subtitulo = ('Consulta institucional de todos los oficios enviados.' if self.modo == 'dashboard' else 'Consulta, actualiza estados y administra los archivos de los oficios de tus áreas.')
        label(textos, subtitulo, 13, MUTED).pack(anchor='w', pady=(4, 0))
        button(cabecera, '↻  Actualizar', self.cargar, width=130).pack(side='right', pady=8)
        self.panel = card(contenido)
        self.panel.pack(fill='both', expand=True)
        self.lista = ctk.CTkScrollableFrame(
            self.panel, fg_color=WHITE, corner_radius=12, height=640,
            scrollbar_button_color=LINE, scrollbar_button_hover_color=MUTED)
        self.lista.pack(fill='both', expand=True, padx=10, pady=10)
        self.lista.update_idletasks()

    def on_show(self):
        self.cargar()

    def navigate(self, name):
        if name == ('Dashboard' if self.modo == 'dashboard' else 'Enviados'):
            self.cargar()
        else:
            super().navigate(name)

    def cargar(self):
        for widget in self.lista.winfo_children():
            widget.destroy()
        try:
            self.registros = listar_oficios_dashboard() if self.modo == 'dashboard' else listar_oficios_area(self.usuario_email)
        except Exception as error:
            label(self.lista, f'No se pudieron cargar los oficios: {error}', 13, ACCENT, wraplength=900).pack(anchor='w', padx=18, pady=22)
            return
        if not self.registros:
            label(self.lista, 'No hay oficios registrados para mostrar.', 14, MUTED).pack(anchor='w', padx=20, pady=24)
            return
        for registro in self.registros:
            self._fila(registro)

    def _fila(self, registro):
        contenedor = ctk.CTkFrame(self.lista, fg_color='transparent')
        contenedor.pack(fill='x', padx=8, pady=5)
        fila = ctk.CTkFrame(contenedor, fg_color=BG, corner_radius=12)
        fila.pack(fill='x')
        fila.grid_columnconfigure(1, weight=1)
        estado = str(registro.get('estado') or 'Sin estado')
        fondo, tinta = COLORES.get(estado.casefold(), ('#EEF0F3', MUTED))
        pill = label(fila, estado.upper(), 10, tinta, True, fg_color=fondo, corner_radius=10, padx=10, pady=5)
        pill.grid(row=0, column=0, padx=(12, 10), pady=12, sticky='w')
        datos = ctk.CTkFrame(fila, fg_color='transparent')
        datos.grid(row=0, column=1, sticky='ew', padx=4, pady=9)
        label(datos, str(registro.get('area') or 'Área no identificada'), 11, MUTED, True).pack(anchor='w')
        label(datos, str(registro.get('asunto') or 'Sin asunto'), 14, TEXT, True, wraplength=780, justify='left').pack(anchor='w', pady=(2, 0))
        label(datos, str(registro.get('folio') or ''), 11, MUTED).pack(anchor='w', pady=(2, 0))
        fecha_creacion = _fecha_texto(registro.get('fecha'))
        fecha_estado = _fecha_texto(registro.get('fecha_estado'))
        label(datos, f'Creado: {fecha_creacion}   ·   Último cambio: {fecha_estado}', 10, MUTED).pack(anchor='w', pady=(4, 0))
        texto_boton = '⌄' if self.modo == 'enviados' else 'Archivos / historial  ⌄'
        button(fila, texto_boton, width=145 if self.modo == 'dashboard' else 42, height=36,
               command=lambda: self._alternar_detalle(contenedor, registro)).grid(row=0, column=2, padx=12, pady=8)

    def _alternar_detalle(self, contenedor, registro):
        existente = getattr(contenedor, '_detalle', None)
        if existente is not None and existente.winfo_exists():
            existente.destroy(); contenedor._detalle = None; return
        detalle = ctk.CTkFrame(contenedor, fg_color='#FBFBFC', corner_radius=12, border_width=1, border_color=LINE)
        detalle.pack(fill='x', pady=(7, 2), padx=4)
        detalle.grid_columnconfigure(0, weight=1)
        contenedor._detalle = detalle
        if self.modo == 'enviados':
            label(detalle, 'ACTUALIZAR ESTADO', 12, TEXT, True).pack(anchor='w', padx=20, pady=(18, 8))
            acciones = ctk.CTkFrame(detalle, fg_color='transparent')
            acciones.pack(fill='x', padx=16, pady=(0, 12))
            acciones.grid_columnconfigure((0, 1), weight=1, uniform='estado')
            button(acciones, 'Marcar como creado / reservado', lambda: self._cambiar_simple(registro, 'creado'), height=40).grid(row=0, column=0, padx=5, pady=5, sticky='ew')
            button(acciones, 'Marcar como enviado', lambda: self._cambiar_simple(registro, 'enviado'), height=40).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
            self._zona_carga(detalle, registro, 'Documento de aprobación', 'Aprobado', self._subir_aprobacion)
            self._zona_carga(detalle, registro, 'Acuse (documento o captura)', 'Acuse', self._subir_acuse)
        if self.modo == 'enviados':
            label(detalle, 'Comentario del acuse (opcional si adjuntas un archivo)', 11, MUTED).pack(anchor='w', padx=20, pady=(8, 3))
        comentario = ctk.CTkTextbox(detalle, height=65, font=('Segoe UI', 12)) if self.modo == 'enviados' else None
        if comentario is not None:
            comentario.pack(fill='x', padx=20, pady=(0, 10))
        detalle._comentario_acuse = comentario
        if self.modo == 'enviados':
            button(detalle, 'Registrar acuse / marcar como acusado', lambda: self._confirmar_acuse(registro, detalle), primary=True, width=310, height=38).pack(anchor='e', padx=20, pady=(0, 14))

        label(detalle, 'ARCHIVOS DISPONIBLES', 12, TEXT, True).pack(anchor='w', padx=20, pady=(12, 8))
        self._mostrar_archivos(detalle, registro)
        self._mostrar_historial(detalle, registro)

    def _zona_carga(self, parent, registro, titulo, tipo, callback):
        """Zona de carga amplia; mantiene visibles selector y botón de acción."""
        zona = ctk.CTkFrame(
            parent, fg_color='#F4F6F9', corner_radius=12,
            border_width=1, border_color=LINE,
        )
        zona.pack(fill='x', padx=20, pady=9)
        # La altura fija anterior (104 px) recortaba los controles en Windows.
        zona.configure(height=158)
        zona.pack_propagate(False)
        zona.grid_columnconfigure(0, weight=1)
        zona.grid_rowconfigure(0, weight=0)
        zona.grid_rowconfigure(1, weight=0)
        zona.grid_rowconfigure(2, weight=0)

        label(
            zona, f'{titulo}: arrastra un archivo aquí o selecciónalo',
            12, MUTED, True,
        ).grid(row=0, column=0, sticky='w', padx=18, pady=(13, 5))

        zona._archivo_seleccionado = None
        nombre = label(zona, 'Ningún archivo seleccionado', 11, MUTED)
        nombre.grid(row=1, column=0, sticky='w', padx=18, pady=(0, 7))
        zona._nombre_archivo = nombre

        def asignar(origen):
            zona._archivo_seleccionado = origen
            nombre.configure(text=Path(origen).name)

        controles = ctk.CTkFrame(zona, fg_color='transparent')
        controles.grid(row=2, column=0, sticky='ew', padx=14, pady=(0, 12))
        controles.grid_columnconfigure(0, weight=1)
        button(
            controles, 'Seleccionar archivo',
            lambda: self._seleccionar_archivo(asignar),
            width=155, height=34,
        ).grid(row=0, column=0, sticky='w')

        texto_accion = (
            'Subir y marcar como aprobado'
            if tipo == 'Aprobado' else 'Adjuntar acuse'
        )
        button(
            controles, texto_accion,
            lambda: callback(registro, zona._archivo_seleccionado)
            if zona._archivo_seleccionado else messagebox.showwarning(
                'Archivo requerido',
                'Selecciona o arrastra un archivo primero.',
                parent=self,
            ),
            width=235, height=34, primary=(tipo == 'Aprobado'),
        ).grid(row=0, column=1, sticky='e', padx=(10, 0))

        activo = _activar_drop(zona, asignar)
        if not activo:
            label(
                zona,
                'Arrastrar y soltar requiere tkinterdnd2; también puedes usar el selector.',
                10, MUTED,
            ).grid(row=3, column=0, sticky='w', padx=18, pady=(0, 8))
            zona.configure(height=176)

        setattr(parent, '_zona_' + tipo.casefold(), zona)

    def _seleccionar_archivo(self, callback):
        origen = filedialog.askopenfilename(title='Seleccionar archivo', filetypes=[('Documentos e imágenes', '*.pdf *.doc *.docx *.png *.jpg *.jpeg *.webp'), ('Todos los archivos', '*.*')])
        if origen:
            callback(origen)

    def _cambiar_simple(self, registro, accion):
        try:
            if accion == 'enviado':
                if not messagebox.askyesno('Confirmar envío', '¿Confirmas que este oficio ya fue enviado por Outlook?', parent=self): return
                marcar_enviado(registro['id_oficio'], self.usuario_email)
            else:
                marcar_creado(registro['id_oficio'], self.usuario_email)
            messagebox.showinfo('Estado actualizado', 'El estado del oficio se actualizó correctamente.', parent=self)
            self.cargar()
        except Exception as error:
            messagebox.showerror('No se pudo actualizar', str(error), parent=self)

    def _subir_aprobacion(self, registro, origen):
        try:
            ruta = _copiar_adjunto(registro, 'Aprobado', origen)
            if not ruta: return
            try: marcar_aprobado(registro['id_oficio'], ruta, self.usuario_email)
            except Exception:
                Path(ruta).unlink(missing_ok=True); raise
            messagebox.showinfo('Aprobación registrada', 'El documento aprobado quedó guardado en la carpeta del folio.', parent=self)
            self.cargar()
        except Exception as error:
            messagebox.showerror('No se pudo registrar la aprobación', str(error), parent=self)

    def _subir_acuse(self, registro, origen):
        detalle = None
        # La zona pertenece al detalle expandido; guardar la ruta temporalmente en el registro UI.
        try:
            ruta = _copiar_adjunto(registro, 'Acuse', origen)
            if ruta:
                registro['_acuse_pendiente'] = ruta
                messagebox.showinfo('Archivo adjuntado', 'El archivo quedó preparado. Pulsa «Registrar acuse» para guardar el registro.', parent=self)
        except Exception as error:
            messagebox.showerror('No se pudo adjuntar el acuse', str(error), parent=self)

    def _confirmar_acuse(self, registro, detalle):
        ruta = registro.pop('_acuse_pendiente', None)
        comentario = detalle._comentario_acuse.get('1.0', 'end').strip() if detalle._comentario_acuse is not None else ''
        try:
            marcar_acusado(registro['id_oficio'], self.usuario_email, ruta, comentario)
            messagebox.showinfo('Acuse registrado', 'El acuse quedó guardado y el estado se actualizó.', parent=self)
            self.cargar()
        except Exception as error:
            if ruta: Path(ruta).unlink(missing_ok=True)
            messagebox.showerror('No se pudo registrar el acuse', str(error), parent=self)

    def _mostrar_archivos(self, detalle, registro):
        try:
            archivos = obtener_archivos_oficio(registro['id_oficio'], self.usuario_email, validar_area=(self.modo == 'enviados'))
            principal = _ruta_archivo_principal(registro)
            self._fila_archivo(detalle, f'Oficio original · {_fecha_texto(registro.get("fecha"))}', str(principal) if principal else None)
            for i, archivo in enumerate(archivos['aprobados'], 1):
                self._fila_archivo(detalle, f'Aprobación {i} · {_fecha_texto(archivo.get("fecha_ingreso"))}', archivo.get('ruta'))
            for i, archivo in enumerate(archivos['acuses'], 1):
                self._fila_archivo(detalle, f'Acuse {i} · {_fecha_texto(archivo.get("fecha_ingreso"))}', archivo.get('ruta'))
                if archivo.get('comentario'):
                    label(detalle, f'Comentario del acuse {i}: {archivo["comentario"]}', 11, MUTED, wraplength=850, justify='left').pack(anchor='w', padx=24, pady=(0, 5))
        except Exception as error:
            label(detalle, f'No se pudieron consultar los archivos: {error}', 11, ACCENT, wraplength=850).pack(anchor='w', padx=16, pady=6)

    def _mostrar_historial(self, detalle, registro):
        label(detalle, 'HISTORIAL DE ESTADOS', 12, TEXT, True).pack(anchor='w', padx=20, pady=(16, 7))
        try:
            historial = obtener_historial_estados(
                registro['id_oficio'], self.usuario_email,
                validar_area=(self.modo == 'enviados'))
            if not historial:
                label(detalle, 'No hay movimientos de estado registrados.', 11, MUTED).pack(anchor='w', padx=22, pady=(0, 14))
                return
            for movimiento in historial:
                vigente = bool(movimiento.get('activo'))
                linea = ctk.CTkFrame(detalle, fg_color='#F3F5F8', corner_radius=8)
                linea.pack(fill='x', padx=20, pady=3)
                estado = str(movimiento.get('estado') or 'Sin estado')
                fondo, tinta = COLORES.get(estado.casefold(), ('#EEF0F3', MUTED))
                label(linea, estado.upper(), 10, tinta, True, fg_color=fondo, corner_radius=9, padx=9, pady=4).pack(side='left', padx=10, pady=8)
                label(linea, _fecha_texto(movimiento.get('fecha_modificacion')), 11, MUTED).pack(side='left', padx=8)
                if vigente:
                    label(linea, 'ESTADO ACTUAL', 9, GREEN, True).pack(side='right', padx=12)
        except Exception as error:
            label(detalle, f'No se pudo consultar el historial: {error}', 11, ACCENT, wraplength=850).pack(anchor='w', padx=20, pady=6)

    def _fila_archivo(self, parent, titulo, ruta):
        fila = ctk.CTkFrame(parent, fg_color='transparent')
        fila.pack(fill='x', padx=16, pady=3)
        label(fila, titulo, 11, TEXT, True, width=170, anchor='w').pack(side='left')
        if ruta and Path(str(ruta)).is_file():
            label(fila, Path(str(ruta)).name, 11, MUTED).pack(side='left', fill='x', expand=True, padx=8)
            button(fila, 'Abrir', lambda p=str(ruta): self._abrir(p), width=70, height=28).pack(side='right', padx=3)
            button(fila, 'Descargar', lambda p=str(ruta): self._descargar(p), width=90, height=28).pack(side='right', padx=3)
        else:
            label(fila, 'Archivo no disponible', 11, MUTED).pack(side='left', padx=8)

    def _abrir(self, ruta):
        try:
            if not Path(ruta).is_file(): raise FileNotFoundError(ruta)
            os.startfile(str(ruta))
        except Exception as error:
            messagebox.showerror('No se pudo abrir el archivo', str(error), parent=self)

    def _descargar(self, ruta):
        origen = Path(ruta)
        destino = filedialog.asksaveasfilename(title='Guardar una copia', initialfile=origen.name, defaultextension=origen.suffix)
        if destino:
            try: shutil.copy2(origen, destino)
            except OSError as error: messagebox.showerror('Descarga', str(error), parent=self)


class DashboardOficiosApp(ListaOficiosApp):
    modo = 'dashboard'


class EnviadosApp(ListaOficiosApp):
    modo = 'enviados'
