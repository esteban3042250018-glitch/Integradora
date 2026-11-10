"""Reconocimiento de folios en asuntos de correo."""
import re

from decouple import AutoConfig

from controller.app_paths import application_dir


CONFIG = AutoConfig(search_path=str(application_dir()))
FOLIO_PATRON = re.compile(
    r'(?<![A-Za-z0-9])(?P<folio>'
    r'(?:[A-Z]{2,12}\s*/\s*){1,3}\d{1,6}\s*/\s*(?:19|20)\d{2}'
    r'|CVDR\s*-\s*DGO\s*-\s*\d{1,8}'
    r'|(?:FOLIO|OFICIO)\s*(?:N[O°º.]*)?\s*[:#-]?\s*\d{1,6}\s*[/\-]\s*(?:19|20)\d{2}'
    r')(?![A-Za-z0-9])',
    re.IGNORECASE,
)


def extraer_folio(asunto):
    """Devuelve el folio real del asunto, o None si no existe."""
    patron_personalizado = CONFIG('CVDR_FOLIO_REGEX', default='').strip()
    try:
        patron = re.compile(patron_personalizado, re.IGNORECASE) if patron_personalizado else FOLIO_PATRON
    except re.error as error:
        raise ValueError(f'CVDR_FOLIO_REGEX no es válida: {error}') from error
    coincidencia = patron.search(asunto or '')
    if not coincidencia:
        return None
    folio = coincidencia.groupdict().get('folio') or (
        coincidencia.group(1) if coincidencia.lastindex else coincidencia.group(0)
    )
    folio = re.sub(r'\s*([/-])\s*', r'\1', folio).strip()
    if not patron_personalizado:
        folio = re.sub(r'^(?:FOLIO|OFICIO)\s*(?:N[O°º.]*)?\s*[:#-]?\s*', '', folio, flags=re.IGNORECASE)
    return folio or None
