# model/microsoft_mail.py
import requests
from .microsoft_auth import obtener_token_silencioso

def obtener_correos_graph():
    """Obtiene los correos de Microsoft Graph usando el token guardado en caché"""
    token = obtener_token_silencioso()
    
    if not token:
        print("[DEBUG] No se encontró un token válido en la caché.")
        return []  
        
    headers = {"Authorization": f"Bearer {token}"}
    graph_url = "https://graph.microsoft.com/v1.0/me/messages?$top=10&$select=id,subject,from,receivedDateTime"
    
    response = requests.get(graph_url, headers=headers)
    if response.status_code == 200:
        mensajes = response.json().get("value", [])
        registros_dinamicos = []
        
        for index, msg in enumerate(mensajes):
            folio = f"MSK-{1000 + index}"
            tipo = "RECIBIDA"
            asunto = msg.get("subject") or "Sin asunto"
            remitente_dict = msg.get("from", {}).get("emailAddress", {})
            remitente_nombre = remitente_dict.get("name") or remitente_dict.get("address") or "Desconocido"
            
            nombres = remitente_nombre.split()
            iniciales = "".join([n[0].upper() for n in nombres[:2]]) if nombres else "MS"
            
            # Asignar estado dinámico
            estado = "En atención" if index % 2 == 0 else "Por asignar"
            
            registros_dinamicos.append((
                folio, tipo, asunto, remitente_nombre, "Bandeja de Entrada", "Normal", iniciales, "Asignado", estado, msg.get("receivedDateTime", "")[:10]
            ))
        return registros_dinamicos
    else:
        print(f"[DEBUG] Error al obtener correos: {response.text}")
        return []