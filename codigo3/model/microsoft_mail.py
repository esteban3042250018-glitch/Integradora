import requests

from .microsoft_auth import obtener_token_graph


GRAPH_MESSAGES_URL = (
    "https://graph.microsoft.com/v1.0/me/messages"
    "?$top=10&$select=id,subject,from,receivedDateTime"
)


def _obtener_mensajes(headers):
    try:
        response = requests.get(GRAPH_MESSAGES_URL, headers=headers, timeout=30)
    except requests.RequestException as error:
        raise RuntimeError(
            "No se pudo conectar con Microsoft Graph. Revisa tu conexión a Internet."
        ) from error

    if not response.ok:
        try:
            error_data = response.json().get("error", {})
        except (ValueError, AttributeError):
            error_data = {}
        codigo = error_data.get("code", f"HTTP {response.status_code}")
        mensaje = error_data.get("message", response.reason)
        raise RuntimeError(
            f"Microsoft Graph rechazó la solicitud ({codigo}): {mensaje}"
        )

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "Microsoft Graph devolvió una respuesta inválida."
        ) from error
    if not isinstance(data, dict) or not isinstance(data.get("value"), list):
        raise RuntimeError("Microsoft Graph devolvió una respuesta inválida.")
    return data["value"]


def obtener_correos_graph(usuario_email):
    """Obtiene correos recientes de Microsoft Graph o informa el error real."""
    usuario_email = str(usuario_email or '').strip()
    if not usuario_email:
        raise RuntimeError(
            "No se pudo identificar la cuenta autenticada para consultar el correo."
        )
    token = obtener_token_graph(usuario_email)
    headers = {"Authorization": f"Bearer {token}"}

    mensajes = _obtener_mensajes(headers)

    registros = []
    for index, mensaje in enumerate(mensajes):
        remitente = mensaje.get("from", {}).get("emailAddress", {})
        nombre = remitente.get("name") or remitente.get("address") or "Desconocido"
        nombres = nombre.split()
        iniciales = "".join(parte[0].upper() for parte in nombres[:2]) if nombres else "MS"
        registros.append((
            f"MSK-{1000 + index}",
            "RECIBIDA",
            mensaje.get("subject") or "Sin asunto",
            nombre,
            "Bandeja de Entrada",
            "Normal",
            iniciales,
            "Asignado",
            "En atención" if index % 2 == 0 else "Por asignar",
            mensaje.get("receivedDateTime", "")[:10],
        ))
    return registros
