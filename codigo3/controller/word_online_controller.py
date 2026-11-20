"""Microsoft Graph operations for editing an oficio with Word for the web."""
from pathlib import Path
import tempfile
from urllib.parse import quote, urlparse
import webbrowser

import requests

from controller.word_controller import (
    leer_texto_word, preparar_documento_word,
)
from model.microsoft_auth import obtener_token_graph
from model.document_store import ruta_docx_oficio


GRAPH_ROOT = 'https://graph.microsoft.com/v1.0'
ONEDRIVE_FOLDER = 'GestionInstitucional'


def _url_archivo(nombre):
    carpeta = quote(ONEDRIVE_FOLDER, safe='')
    archivo = quote(nombre, safe='')
    return f'{GRAPH_ROOT}/me/drive/root:/{carpeta}/{archivo}'


def _url_carpeta():
    return f'{GRAPH_ROOT}/me/drive/root:/{quote(ONEDRIVE_FOLDER, safe="")}'


def _comprobar_respuesta(response, operacion):
    if response.ok:
        return
    try:
        detalle = response.json().get('error', {}).get('message')
    except (ValueError, AttributeError):
        detalle = None
    if response.status_code in (401, 403):
        mensaje = (
            'Microsoft rechazó el acceso a OneDrive. Comprueba que la cuenta '
            'tenga OneDrive configurado y que la aplicación tenga permiso '
            'Files.ReadWrite consentido.'
        )
    elif response.status_code == 507:
        mensaje = 'OneDrive no tiene espacio disponible para guardar el documento.'
    else:
        mensaje = detalle or response.reason or f'HTTP {response.status_code}'
    raise RuntimeError(f'{operacion}: {mensaje}')


def _crear_carpeta_si_falta(headers):
    try:
        response = requests.get(_url_carpeta(), headers=headers, timeout=30)
    except requests.RequestException as error:
        raise RuntimeError(
            'No se pudo conectar con OneDrive para preparar la carpeta.'
        ) from error
    if response.status_code != 404:
        _comprobar_respuesta(response, 'No se pudo consultar la carpeta de OneDrive')
        return

    try:
        response = requests.post(
            f'{GRAPH_ROOT}/me/drive/root/children',
            headers={**headers, 'Content-Type': 'application/json'},
            json={
                'name': ONEDRIVE_FOLDER,
                'folder': {},
                '@microsoft.graph.conflictBehavior': 'fail',
            },
            timeout=30,
        )
    except requests.RequestException as error:
        raise RuntimeError(
            'No se pudo crear la carpeta de documentos en OneDrive.'
        ) from error
    if response.status_code == 409:
        return
    _comprobar_respuesta(response, 'No se pudo crear la carpeta de OneDrive')


def abrir_word_online(
    folio, asunto, cuerpo_html='', usuario_email=None, reemplazar=False
):
    """Create the OneDrive item if needed, then open its Word for the web URL."""
    try:
        token = obtener_token_graph(usuario_email)
    except requests.RequestException as error:
        raise RuntimeError(
            'No se pudo autenticar con Microsoft para acceder a OneDrive.'
        ) from error
    headers = {'Authorization': f'Bearer {token}'}
    _crear_carpeta_si_falta(headers)

    local_path = preparar_documento_word(folio, asunto, cuerpo_html)
    item_url = _url_archivo(local_path.name)
    try:
        response = requests.get(item_url, headers=headers, timeout=30)
    except requests.RequestException as error:
        raise RuntimeError(
            'No se pudo consultar el documento en OneDrive.'
        ) from error

    if response.status_code != 404:
        _comprobar_respuesta(
            response, 'No se pudo abrir el documento de OneDrive')
    if response.status_code == 404 or reemplazar:
        try:
            with local_path.open('rb') as archivo:
                response = requests.put(
                    f'{item_url}:/content',
                    headers=headers,
                    data=archivo,
                    timeout=60,
                )
        except OSError as error:
            raise RuntimeError(
                f'No se pudo leer el documento local {local_path}.'
            ) from error
        except requests.RequestException as error:
            raise RuntimeError(
                'No se pudo subir el documento inicial a OneDrive.'
            ) from error
        _comprobar_respuesta(response, 'No se pudo subir el documento a OneDrive')

    _comprobar_respuesta(response, 'No se pudo abrir el documento de OneDrive')
    try:
        web_url = response.json().get('webUrl')
    except (ValueError, AttributeError) as error:
        raise RuntimeError(
            'OneDrive devolvió una respuesta inválida al abrir el documento.'
        ) from error
    parsed_url = urlparse(web_url or '')
    if parsed_url.scheme != 'https' or not parsed_url.netloc:
        raise RuntimeError(
            'OneDrive no devolvió un enlace HTTPS válido para el documento.'
        )
    try:
        opened = webbrowser.open(web_url)
    except webbrowser.Error as error:
        raise RuntimeError(
            'No se pudo abrir el navegador predeterminado. '
            f'Puedes abrir manualmente este enlace: {web_url}'
        ) from error
    if not opened:
        raise RuntimeError(
            'No se pudo abrir el navegador predeterminado. '
            f'Puedes abrir manualmente este enlace: {web_url}'
        )
    return local_path


def descargar_cambios_word_online(folio, destino, usuario_email=None):
    """Download the latest OneDrive version and atomically replace the local copy."""
    if Path(destino).name != ruta_docx_oficio(folio).name:
        raise ValueError('La ruta local no coincide con el folio del documento.')
    token = obtener_token_graph(usuario_email)
    headers = {'Authorization': f'Bearer {token}'}
    _crear_carpeta_si_falta(headers)
    item_url = _url_archivo(Path(destino).name)
    temporal = None
    try:
        response = requests.get(
            f'{item_url}:/content', headers=headers, timeout=60)
    except requests.RequestException as error:
        raise RuntimeError(
            'No se pudieron descargar los cambios guardados en Word Online.'
        ) from error
    _comprobar_respuesta(
        response, 'No se pudieron descargar los cambios de OneDrive')

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(
                dir=destino.parent, suffix='.docx.part', delete=False) as archivo:
            temporal = Path(archivo.name)
            archivo.write(response.content)
        leer_texto_word(temporal)
        temporal.replace(destino)
    except (OSError, ValueError) as error:
        raise RuntimeError(
            'OneDrive no devolvió un documento .docx válido. '
            'Guarda el archivo en Word Online e inténtalo de nuevo.'
        ) from error
    finally:
        if temporal is not None and temporal.exists():
            temporal.unlink()
    return destino
