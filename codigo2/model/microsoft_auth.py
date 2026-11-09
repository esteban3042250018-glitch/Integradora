# microsoft_auth.py
import msal
import requests
from decouple import AutoConfig
from controller.app_paths import application_dir, user_data_dir

CLIENT_ID = AutoConfig(search_path=str(application_dir()))(
    'MICROSOFT_AUTH_API', default='').strip()
AUTHORITY = "https://login.microsoftonline.com/common"
# Todos los permisos se piden en el login para dar el consentimiento una sola vez:
# correo (bandeja del home) y OneDrive/Word (crear documento).
SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Files.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]
AUTH_SUCCESS_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Listo</title>
  <script>window.close();</script>
</head>
<body>
  <p>Inicio de sesión listo. Puedes volver a la aplicación.</p>
</body>
</html>"""

TOKEN_CACHE_DIR = user_data_dir()
CACHE_FILE = TOKEN_CACHE_DIR / "token_cache.bin"

def _cargar_cache():
    cache = msal.SerializableTokenCache()
    if CACHE_FILE.exists():
        with CACHE_FILE.open("r", encoding="utf-8") as archivo:
            cache.deserialize(archivo.read())
    return cache

def _guardar_cache(cache):
    if cache.has_state_changed:
        TOKEN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("w", encoding="utf-8") as archivo:
            archivo.write(cache.serialize())


def _validar_configuracion():
    if not CLIENT_ID or CLIENT_ID.lower().startswith('your-'):
        raise RuntimeError(
            "La API de Microsoft no está configurada. Edita el archivo .env "
            "junto al programa y asigna MICROSOFT_AUTH_API con el ID de "
            "cliente de tu aplicación Microsoft Entra."
        )


def obtener_cliente_msal():
    _validar_configuracion()
    cache = _cargar_cache()
    return msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache
    )

def iniciar_sesion_interactivo():
    app = obtener_cliente_msal()
    result = app.acquire_token_interactive(
        scopes=SCOPES,
        prompt="select_account",
        success_template=AUTH_SUCCESS_TEMPLATE,
    )
    _guardar_cache(app.token_cache)
    return result

def obtener_token_silencioso():
    app = obtener_cliente_msal()
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _guardar_cache(app.token_cache)   # guarda el token renovado
            return result["access_token"]
    return None

def obtener_token_graph():
    """Token de Microsoft Graph usando la sesión del login.

    Solo abre la ventana de Microsoft si no hay sesión válida, o si la sesión
    guardada no incluye el permiso de OneDrive (pasa una vez, tras actualizar).
    """
    token = obtener_token_silencioso()
    if token:
        return token

    app = obtener_cliente_msal()
    cuentas = app.get_accounts()
    hint = cuentas[0].get("username") if cuentas else None
    result = app.acquire_token_interactive(
        scopes=SCOPES,
        login_hint=hint,
        success_template=AUTH_SUCCESS_TEMPLATE,
    )
    _guardar_cache(app.token_cache)
    if "access_token" not in result:
        raise RuntimeError(
            "No se pudo autenticar con Microsoft 365: "
            f"{result.get('error_description', 'error desconocido')}"
        )
    return result["access_token"]