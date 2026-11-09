import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import winreg
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

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


def crear_o_abrir_word(folio, asunto):
    if os.name != 'nt':
        raise OSError('La apertura de Microsoft Word está disponible en Windows.')

    ruta = ruta_docx_oficio(folio)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists():
        documento = Document()
        documento.core_properties.title = f'Oficio {folio}'
        documento.core_properties.subject = asunto
        documento.save(ruta)

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
