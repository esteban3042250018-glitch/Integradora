"""Controlador para la integración con Microsoft 365 (Microsoft Graph API)."""
import io
import msal
import requests
import webbrowser
from docx import Document
from decouple import config
# Reemplaza estos valores con los que obtuviste al registrar tu app en Azure Portal
CLIENT_ID = config('MICROSOFT_AUTH_API')          # Application (client) ID
TENANT_ID = "common"                     # O tu Tenant ID específico si es solo para tu organización
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Files.ReadWrite", "User.Read"]

def obtener_token():
    """Autentica al usuario de forma interactiva mediante una ventana de inicio de sesión."""
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    
    # Buscar si ya hay una sesión guardada en caché
    cuentas = app.get_accounts()
    if cuentas:
        resultado = app.acquire_token_silent(SCOPES, account=cuentas[0])
        if resultado and "access_token" in resultado:
            return resultado["access_token"]
            
    # Si no hay sesión, abre el navegador para que el usuario inicie sesión con su cuenta de Microsoft 365
    resultado = app.acquire_token_interactive(scopes=SCOPES)
    if "access_token" in resultado:
        return resultado["access_token"]
    
    raise Exception("No se pudo completar la autenticación con Microsoft 365.")

def crear_y_abrir_word_en_nube(folio, asunto):
    """Crea un documento de Word en el OneDrive del usuario y lo abre en Word Online."""
    token = obtener_token()
    
    # Nombre del archivo en OneDrive
    nombre_archivo = f"Oficio_{folio.replace('/', '_')}.docx"
    
    # 1. Crear un archivo en la raíz del OneDrive del usuario con el encabezado inicial
    url_subida = f"https://graph.microsoft.com/v1.0/me/drive/root:/{nombre_archivo}:/content"
    
    # Creamos un documento base en memoria con python-docx para que no esté vacío
    doc_base = Document()
    doc_base.add_heading(f"Oficio No. {folio}", level=1)
    doc_base.add_paragraph(f"Asunto: {asunto}")
    doc_base.add_paragraph("Escribe aquí el contenido principal de tu oficio...")
    
    buffer = io.BytesIO()
    doc_base.save(buffer)
    contenido_binario = buffer.getvalue()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
    
    respuesta = requests.put(url_subida, headers=headers, data=contenido_binario)
    
    if respuesta.status_code not in [200, 201]:
        raise Exception(f"Error al crear el archivo en OneDrive: {respuesta.text}")
        
    datos_archivo = respuesta.json()
    web_url = datos_archivo.get("webUrl") # Enlace directo para abrir en Word Online
    file_id = datos_archivo.get("id")     # ID único del archivo en la nube
    
    # 2. Abrir automáticamente Word Online en el navegador predeterminado del usuario
    if web_url:
        webbrowser.open(web_url)
        
    return file_id, web_url

def obtener_texto_desde_onedrive(file_id):
    """Descarga el documento .docx actualizado desde OneDrive y extrae su texto plano."""
    token = obtener_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
    respuesta = requests.get(url, headers=headers)
    
    if respuesta.status_code == 200:
        # Leemos el archivo binario descargado usando python-docx
        f = io.BytesIO(respuesta.content)
        doc = Document(f)
        
        # Unimos los párrafos ignorando el título y asunto inicial si se desea, 
        # o devolvemos todo el texto redactado por el usuario.
        texto_completo = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return texto_completo
    else:
        raise Exception(f"No se pudo sincronizar el contenido desde OneDrive: {respuesta.text}")

def descargar_pdf_desde_onedrive(file_id, ruta_destino_pdf):
    """Convierte y descarga el archivo editado desde OneDrive directamente en formato PDF."""
    token = obtener_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    url_export = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content?format=pdf"
    
    respuesta = requests.get(url_export, headers=headers)
    if respuesta.status_code == 200:
        with open(ruta_destino_pdf, "wb") as f:
            f.write(respuesta.content)
    else:
        raise Exception(f"No se pudo exportar el PDF desde OneDrive: {respuesta.text}")