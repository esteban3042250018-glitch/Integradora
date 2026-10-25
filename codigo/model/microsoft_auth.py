# microsoft_auth.py
import msal
import requests
import os
from decouple import config
CLIENT_ID = config('MICROSOFT_AUTH_API')
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["https://graph.microsoft.com/Mail.Read"]

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
            return result["access_token"]
    return None