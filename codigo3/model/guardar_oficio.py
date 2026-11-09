from io import BytesIO
from pathlib import Path
import sys
from controller.database_conecction import Database_connection

def obtener_conexion():
    """Abre una conexión usando el conector existente del proyecto."""
    conexion = Database_connection().get_connection()
    if conexion is None:
        raise ConnectionError(
            "No fue posible conectar con PostgreSQL. Revisa controller/config.py."
        )
    return conexion

def obtener_asunto(conexion):
    asunto = input("Ingresa el asunto: ")
    
    conexion = obtener_conexion()
    
    try:
        with conexion:
            with conexion.cursor() as cursor:
    
                    cursor.execute("""
                        INSERT INTO correspondencia.asuntos (
                            asunto
                        )
                        VALUES (%s,)
                    """, (asunto))
    finally:
            conexion.close()

def guardar_oficio():
    conexion = obtener_conexion()

    try:
        asunto = obtener_asunto(conexion) 
    finally:
        conexion.close()

