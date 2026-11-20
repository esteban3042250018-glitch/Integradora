import hashlib
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import winreg
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.shared import Inches

from model.generar_membrete import (
    ALTO_PAGINA, ANCHO_PAGINA, agregar_folio, agregar_imagen_fondo,
    obtener_conexion, obtener_imagen_membrete,
)
from model.document_store import ruta_docx_oficio


def _buscar_word():
    encontrado = shutil.which('WINWORD.EXE')
    if encontrado:
        return encontrado

    rutas_registro = (
        r'Software\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE',
        r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE',
    )
    for raiz in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for ruta in rutas_registro:
            try:
                with winreg.OpenKey(raiz, ruta) as clave:
                    ejecutable = winreg.QueryValue(clave, None)
            except OSError:
                continue
            ejecutable = os.path.expandvars(ejecutable.strip('"'))
            if Path(ejecutable).is_file():
                return ejecutable

    for variable in ('ProgramFiles', 'ProgramFiles(x86)'):
        base = os.environ.get(variable)
        if not base:
            continue
        for version in ('Office16', 'Office15'):
            ejecutable = Path(base) / 'Microsoft Office' / 'root' / version / 'WINWORD.EXE'
            if ejecutable.is_file():
                return str(ejecutable)
    raise FileNotFoundError(
        'No se encontró Microsoft Word de escritorio. Instálalo para abrir y editar el oficio.'
    )


def preparar_documento_word(folio, asunto, cuerpo_html=''):
    ruta = ruta_docx_oficio(folio)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists():
        conexion = obtener_conexion()
        try:
            _, _, imagen_membrete = obtener_imagen_membrete(conexion)
        finally:
            conexion.close()

        documento = Document()
        documento.core_properties.title = f'Oficio {folio}'
        documento.core_properties.subject = asunto
        seccion = documento.sections[0]
        seccion.page_width = Inches(ANCHO_PAGINA)
        seccion.page_height = Inches(ALTO_PAGINA)
        # Match the writing area used by the PDF generator (margins in points).
        seccion.top_margin = Inches(230 / 72)
        seccion.bottom_margin = Inches(110 / 72)
        seccion.left_margin = Inches(54 / 72)
        seccion.right_margin = Inches(54 / 72)
        seccion.header_distance = Inches(0.1)
        seccion.footer_distance = Inches(0)

        encabezado = seccion.header
        encabezado.is_linked_to_previous = False
        agregar_folio(encabezado.paragraphs[0], folio)
        agregar_imagen_fondo(
            encabezado.add_paragraph(),
            imagen_membrete,
            ANCHO_PAGINA,
            ALTO_PAGINA,
        )

        if cuerpo_html:
            texto = re.sub(
                r'<br\s*/?>|</p>', '\n', cuerpo_html, flags=re.IGNORECASE)
            texto = html.unescape(re.sub(r'<[^>]+>', '', texto))
            for linea in texto.splitlines():
                documento.add_paragraph(linea)
        documento.save(ruta)
    return ruta


def crear_o_abrir_word(folio, asunto, cuerpo_html=''):
    if os.name != 'nt':
        raise OSError('La apertura de Microsoft Word está disponible en Windows.')

    ruta = preparar_documento_word(folio, asunto, cuerpo_html)
    subprocess.Popen([_buscar_word(), str(ruta)])
    return ruta


def leer_texto_word(ruta):
    try:
        documento = Document(ruta)
    except (BadZipFile, PackageNotFoundError) as error:
        raise ValueError('El archivo de Word no es un documento .docx válido.') from error
    lineas = [parrafo.text for parrafo in documento.paragraphs]
    for tabla in documento.tables:
        for fila in tabla.rows:
            lineas.append('\t'.join(celda.text for celda in fila.cells))
    return '\n'.join(lineas).strip()


def firma_documento_word(ruta):
    digest = hashlib.sha256()
    with open(ruta, 'rb') as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
            digest.update(bloque)
    return digest.digest()
