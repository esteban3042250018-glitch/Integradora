# microsoft_auth.py
import msal
import requests
import os
from decouple import config
CLIENT_ID = config('MICROSOFT_AUTH_API')
AUTHORITY = "https://login.microsoftonline.com/common"
# Todos los permisos se piden en el login para dar el consentimiento una sola vez:
# correo (bandeja del home) y OneDrive/Word (crear documento).
SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Files.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "token_cache.bin")

def _cargar_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache

def _guardar_cache(cache):
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())

def obtener_cliente_msal():
    cache = _cargar_cache()
    return msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache
    )

def iniciar_sesion_interactivo():
    app = obtener_cliente_msal()
    result = app.acquire_token_interactive(scopes=SCOPES, prompt="select_account")
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
    result = app.acquire_token_interactive(scopes=SCOPES, login_hint=hint)
    _guardar_cache(app.token_cache)
    if "access_token" not in result:
        raise RuntimeError(
            "No se pudo autenticar con Microsoft 365: "
            f"{result.get('error_description', 'error desconocido')}"
        )
    return result["access_token"]