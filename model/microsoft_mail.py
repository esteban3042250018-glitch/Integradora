"""Consulta de correos entrantes con folio mediante Microsoft Graph."""
import os
import re
from collections import Counter
from urllib.parse import quote

import requests
from decouple import AutoConfig

from controller.app_paths import application_dir
from .folio import extraer_folio
from .administracion import obtener_configuraciones_folio
from .folio_format import folio_search_pattern, render_folio
from .microsoft_auth import obtener_token_graph

CONFIG = AutoConfig(search_path=str(application_dir()))
GRAPH = 'https://graph.microsoft.com/v1.0'


def _inbox_url():
    buzon = CONFIG('CVDR_MAILBOX_EMAIL', default='').strip()
    if buzon:
        return f'{GRAPH}/users/{quote(buzon, safe="")}/mailFolders/inbox/messages'
    return f'{GRAPH}/me/mailFolders/inbox/messages'


def _message_url(message_id):
    buzon = CONFIG('CVDR_MAILBOX_EMAIL', default='').strip()
    message = quote(str(message_id), safe='')
    if buzon:
        return f'{GRAPH}/users/{quote(buzon, safe="")}/messages/{message}'
    return f'{GRAPH}/me/messages/{message}'


def _detalle_error(respuesta):
    try:
        detalle = respuesta.json().get('error') or {}
    except (ValueError, AttributeError, TypeError):
        detalle = {}
    codigo = detalle.get('code') or f'HTTP {respuesta.status_code}'
    mensaje = detalle.get('message') or respuesta.reason or 'Error de Microsoft Graph'
    codigo_bajo = str(codigo).lower()
    mensaje_bajo = str(mensaje).lower()
    buzon = CONFIG('CVDR_MAILBOX_EMAIL', default='').strip()
    cuenta = os.environ.get('GI_USUARIO_EMAIL', '').strip()

    if respuesta.status_code == 401:
        ayuda = ('Tu sesión de Microsoft expiró o el token fue rechazado. '
                 'Vuelve a iniciar sesión con la cuenta correcta.')
    elif any(palabra in codigo_bajo + ' ' + mensaje_bajo for palabra in (
            'mailboxnotenabled', 'mailboxnotsupported', 'mailboxnotfound',
            'nonexistentmailbox', 'errornonexistentmailbox', 'mailbox is not enabled',
            'mailbox not found', 'no mailbox', 'not a mailbox')):
        ayuda = ('La cuenta autenticada no tiene un buzón Outlook/Exchange disponible para Microsoft Graph. '
                 'Utiliza una cuenta Microsoft 365 con Exchange Online o una cuenta Outlook.com con buzón activo.')
    elif not buzon and cuenta.lower().endswith('@gmail.com') and respuesta.status_code in (403, 404):
        ayuda = ('Has iniciado sesión en Microsoft con una dirección Gmail, pero Microsoft Graph no '
                 'puede leer tu bandeja de Gmail. Para esta prueba inicia sesión con una cuenta '
                 'Outlook.com o Microsoft 365 que tenga buzón de correo. Puedes enviarle mensajes desde Gmail.')
    elif respuesta.status_code == 403:
        ayuda = ('Microsoft Graph denegó acceso al buzón. Comprueba el permiso delegado '
                 'Mail.ReadWrite y el consentimiento; para un buzón compartido, '
                 'Mail.ReadWrite.Shared y acceso delegado. '
                 'Confirma también que tu cuenta pueda consultar ese buzón.')
    elif respuesta.status_code == 404:
        ayuda = ('Microsoft Graph no encontró el buzón indicado. Revisa CVDR_MAILBOX_EMAIL '
                 'y confirma que el buzón existe y está disponible en Exchange/Outlook.')
    elif respuesta.status_code == 429:
        ayuda = 'Microsoft Graph está limitando temporalmente las consultas. Intenta actualizar después.'
    else:
        ayuda = 'Comprueba la cuenta, los permisos de Microsoft Graph y tu conexión a Internet.'
    return RuntimeError(f'{ayuda}\n\nDetalle de Microsoft Graph: {codigo}: {mensaje}')


def _obtener_mensajes(usuario_email):
    token = obtener_token_graph(usuario_email)
    url = _inbox_url()
    headers = {'Authorization': f'Bearer {token}'}
    limite = max(1, min(CONFIG('CVDR_MAX_MESSAGES', default=300, cast=int), 1000))
    params = {
        '$top': min(100, limite),
        '$select': 'id,subject,from,receivedDateTime,isRead,hasAttachments',
        '$orderby': 'receivedDateTime desc',
    }
    mensajes = []
    while url and len(mensajes) < limite:
        try:
            respuesta = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.RequestException as error:
            raise RuntimeError('No fue posible conectar con Microsoft Graph. Comprueba Internet.') from error
        if not respuesta.ok:
            raise _detalle_error(respuesta)
        try:
            datos = respuesta.json()
            pagina = datos['value']
            if not isinstance(pagina, list):
                raise ValueError('Respuesta de mensajes incorrecta')
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise RuntimeError('Microsoft Graph devolvió una respuesta de correo inválida.') from error
        mensajes.extend(pagina[:limite - len(mensajes)])
        url = datos.get('@odata.nextLink')
        if url and not url.startswith(GRAPH + '/'):
            raise RuntimeError('Microsoft Graph devolvió una página con dirección inválida.')
        params = None
    return mensajes


def _clave_folio(folio, configuracion_folio=None):
    """Identifica el mismo folio sin distinguir mayúsculas ni ceros iniciales."""
    if configuracion_folio is not None:
        coincidencia = folio_search_pattern(
            configuracion_folio).fullmatch(folio.strip())
        if coincidencia:
            anio = coincidencia.groupdict().get('anio')
            return render_folio(
                int(coincidencia.group('numero')),
                configuracion_folio,
                int(anio) if anio else None,
            ).upper()

    clave = re.sub(r'\s*([/-])\s*', r'\1', folio.strip().upper())
    partes = clave.split('/')
    if len(partes) >= 2 and len(partes[-1]) == 4 and partes[-1].isdigit() and partes[-2].isdigit():
        partes[-2] = str(int(partes[-2]))
        return '/'.join(partes)
    coincidencia = re.fullmatch(r'(CVDR-DGO-)(\d+)', clave)
    if coincidencia:
        return coincidencia.group(1) + str(int(coincidencia.group(2)))
    return clave


def _mensajes_con_folio(mensajes, configuracion_folio=None):
    """Conserva cada mensaje y señala los folios coincidentes."""
    configuraciones = (
        configuracion_folio
        if isinstance(configuracion_folio, (list, tuple))
        else [configuracion_folio]
    )
    if not configuraciones:
        configuraciones = [None]

    encontrados = []
    for mensaje in mensajes:
        folio = None
        configuracion_coincidente = None
        for configuracion in configuraciones:
            folio = extraer_folio(mensaje.get('subject'), configuracion)
            if folio:
                configuracion_coincidente = configuracion
                break
        if folio:
            encontrados.append((
                mensaje,
                folio.upper(),
                _clave_folio(folio, configuracion_coincidente),
            ))

    cantidades = Counter(clave for _, _, clave in encontrados)
    encontrados.sort(key=lambda dato: dato[0].get('receivedDateTime') or '', reverse=True)
    return [(mensaje, folio, cantidades[clave]) for mensaje, folio, clave in encontrados]


def obtener_correos_graph(usuario_email, incluir_sin_folio=False):
    """Devuelve mensajes de la bandeja y, opcionalmente, los que no tienen folio."""
    if not str(usuario_email or "").strip():
        raise RuntimeError("No se identificó la cuenta Microsoft para consultar el correo.")
    mensajes = _obtener_mensajes(usuario_email)
    encontrados = _mensajes_con_folio(
        mensajes, obtener_configuraciones_folio())
    if incluir_sin_folio:
        con_folio = {id(mensaje) for mensaje, _, _ in encontrados}
        encontrados.extend(
            (mensaje, '', 1) for mensaje in mensajes
            if id(mensaje) not in con_folio
        )
        encontrados.sort(
            key=lambda dato: dato[0].get('receivedDateTime') or '',
            reverse=True)

    registros = []
    for mensaje, folio, cantidad in encontrados:
        remitente = (mensaje.get('from') or {}).get('emailAddress') or {}
        nombre = remitente.get('name') or remitente.get('address') or 'Desconocido'
        iniciales = ''.join(palabra[0].upper() for palabra in nombre.split()[:2]) or 'CV'
        registros.append((
            folio,
            'RECIBIDA',
            mensaje.get('subject') or 'Sin asunto',
            nombre,
            'Bandeja de Entrada',
            'Normal',
            iniciales,
            'Sin asignar',
            'Recibido' if mensaje.get('isRead') is True else 'No leído',
            (mensaje.get('receivedDateTime') or '')[:10],
            'Posible folio repetido' if cantidad > 1 else '',
            str(cantidad),
            mensaje.get('receivedDateTime') or '',
            remitente.get('address') or '',
            str(mensaje.get('id') or ''),
        ))
    return registros


def marcar_correo_leido(usuario_email, message_id):
    """Marca como leído en Graph un mensaje abierto desde la aplicación."""
    if not str(usuario_email or '').strip():
        raise RuntimeError('No se identificó la cuenta Microsoft para actualizar el correo.')
    if not str(message_id or '').strip():
        raise RuntimeError('Microsoft Graph no devolvió el identificador del correo.')
    token = obtener_token_graph(usuario_email)
    try:
        respuesta = requests.patch(
            _message_url(message_id),
            headers={'Authorization': f'******'},
            json={'isRead': True},
            timeout=30,
        )
    except requests.RequestException as error:
        raise RuntimeError(
            'No fue posible actualizar el estado del correo en Microsoft Graph.'
        ) from error
    if not respuesta.ok:
        raise _detalle_error(respuesta)
