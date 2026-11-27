import os
import shutil
import subprocess
import tempfile
import webbrowser
from contextlib import contextmanager
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
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Files.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]
if AutoConfig(search_path=str(application_dir()))('CVDR_MAILBOX_EMAIL', default='').strip():
    SCOPES.append('https://graph.microsoft.com/Mail.ReadWrite.Shared')

# Página mínima/vacía que intenta cerrarse automáticamente en el navegador
AUTH_SUCCESS_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Listo</title>
  <script>
    window.onload = function() {
      window.open('', '_self', '');
      window.close();
    };
  </script>
</head>
<body style="margin:0;background:#fff;"></body>
</html>"""

AUTH_ERROR_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Listo</title>
  <script>window.close();</script>
</head>
<body style="margin:0;background:#fff;"></body>
</html>"""

TOKEN_CACHE_DIR = user_data_dir()
CACHE_FILE = TOKEN_CACHE_DIR / "token_cache.bin"


def _buscar_navegador_app():
    """Busca Microsoft Edge o Google Chrome en Windows para abrirlo en modo ventana limpia."""
    rutas_posibles = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for ruta in rutas_posibles:
        if os.path.isfile(ruta):
            return ruta
    return shutil.which("msedge") or shutil.which("chrome")


@contextmanager
def _ventana_emergente_login():
    """Redirige webbrowser.open hacia una ventana emergente limpia y la cierra al finalizar."""
    original_open = webbrowser.open
    navegador = _buscar_navegador_app()
    proceso = None
    perfil_temporal = None

    def abrir_popup(url, new=0, autoraise=True):
        nonlocal proceso, perfil_temporal
        if navegador:
            perfil_temporal = tempfile.mkdtemp(prefix="msal_popup_")
            proceso = subprocess.Popen([
                navegador,
                f"--app={url}",
                f"--user-data-dir={perfil_temporal}",
                "--window-size=480,640",
                "--window-position=500,150",
                "--no-first-run",
                "--no-default-browser-check",
            ])
            return True
        return original_open(url, new=new, autoraise=autoraise)

    webbrowser.open = abrir_popup
    try:
        yield
    finally:
        webbrowser.open = original_open
        if proceso is not None:
            try:
                proceso.terminate()
            except Exception:
                pass
        if perfil_temporal:
            shutil.rmtree(perfil_temporal, ignore_errors=True)


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


def iniciar_sesion_interactivo(cancel_event=None):
    app = obtener_cliente_msal()
    with _ventana_emergente_login():
        result = app.acquire_token_interactive(
            scopes=SCOPES,
            prompt="select_account",
            success_template=AUTH_SUCCESS_TEMPLATE,
            error_template=AUTH_ERROR_TEMPLATE,
        )
    if cancel_event and cancel_event.is_set():
        return None
    _guardar_cache(app.token_cache)
    return result


def obtener_token_silencioso(usuario_email=None):
    app = obtener_cliente_msal()
    accounts = app.get_accounts()
    if usuario_email:
        usuario_normalizado = usuario_email.strip().casefold()
        accounts = [
            account for account in accounts
            if str(account.get('username') or '').casefold() == usuario_normalizado
        ]
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _guardar_cache(app.token_cache)
            return result["access_token"]
    return None


def obtener_token_graph(usuario_email=None):
    """Token de Microsoft Graph usando la sesión del login."""
    usuario_email = str(usuario_email or '').strip()
    if not usuario_email:
        raise RuntimeError(
            "No se pudo identificar la cuenta autenticada para acceder a Microsoft Graph."
        )

    token = obtener_token_silencioso(usuario_email)
    if token:
        return token

    app = obtener_cliente_msal()
    with _ventana_emergente_login():
        result = app.acquire_token_interactive(
            scopes=SCOPES,
            login_hint=usuario_email,
            success_template=AUTH_SUCCESS_TEMPLATE,
            error_template=AUTH_ERROR_TEMPLATE,
        )
    if "access_token" not in result:
        raise RuntimeError(
            "No se pudo autenticar con Microsoft 365: "
            f"{result.get('error_description', 'error desconocido')}"
        )
    claims = result.get("id_token_claims") or {}
    identidades = {
        str(claims.get(clave) or '').strip().casefold()
        for clave in ('preferred_username', 'upn', 'email')
    }
    if usuario_email.casefold() not in identidades:
        raise RuntimeError(
            "La cuenta seleccionada en Microsoft no coincide con la cuenta "
            "que inició sesión en la aplicación."
        )
    _guardar_cache(app.token_cache)
    return result["access_token"]