"""Rutas de archivos locales y consultas de documentos en PostgreSQL."""
import os
from pathlib import Path
import re

from controller.database_conecction import Database_connection


def ruta_carpeta_archivos():
    configurada = os.environ.get('GESTION_INSTITUCIONAL_DOCUMENTS_DIR')
    if configurada:
        return Path(configurada).expanduser()
    return Path.home() / 'Documents' / 'GestionInstitucional' / 'Oficios'


def ruta_pdf_oficio(folio):
    nombre_seguro = re.sub(r'[\\/:*?"<>|]', '_', str(folio))
    return ruta_carpeta_archivos() / f'Oficio_{nombre_seguro}.pdf'


def ruta_docx_oficio(folio):
    nombre_seguro = re.sub(r'[\\/:*?"<>|]', '_', str(folio))
    return ruta_carpeta_archivos() / f'Oficio_{nombre_seguro}.docx'


def obtener_documento(folio, usuario_id):
    if not usuario_id:
        raise ValueError('No se pudo identificar la cuenta autenticada.')
    return Database_connection().obtener_borrador(folio, usuario_id)
