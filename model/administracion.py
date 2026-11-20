import json
import mimetypes
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    Image = None


# Este archivo se encuentra en codigo/model/administracion.py.
CARPETA_CODIGO = Path(__file__).resolve().parent.parent
if str(CARPETA_CODIGO) not in sys.path:
    sys.path.insert(0, str(CARPETA_CODIGO))

from controller.database_connection import Database_connection, database_cursor

from model.folio_format import (
    build_configuration,
    configuration_from_row,
    preview_next_folio,
    read_configuration,
    reserve_next_folio,
)

FORMATOS_IMAGEN = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def obtener_conexion():
    """Usa la configuración que Database_connection ya importa internamente."""
    conexion = Database_connection().get_connection()
    if conexion is None:
        raise ConnectionError(
            "No se pudo conectar con PostgreSQL. Revisa controller/config.py "
            "y la salida de conexión en la terminal."
        )
    return conexion


def validar_imagen(ruta):
    """Devuelve (ruta, MIME, bytes) después de validar la imagen."""
    texto_ruta = ruta.strip().strip('"').strip("'")
    origen = Path(texto_ruta).expanduser()

    if not origen.exists():
        raise FileNotFoundError("La ruta indicada no existe.")
    if not origen.is_file():
        raise ValueError("La ruta indicada no corresponde a un archivo.")
    if origen.suffix.lower() not in FORMATOS_IMAGEN:
        raise ValueError(
            "Formato no admitido. Usa PNG, JPG/JPEG, BMP, GIF, TIFF o WEBP."
        )
    if Image is None:
        raise RuntimeError(
            "Falta Pillow para validar imágenes. Instálalo con: "
            "python -m pip install Pillow"
        )

    try:
        with Image.open(origen) as imagen:
            imagen.verify()
        with Image.open(origen) as imagen:
            formato = (imagen.format or "").upper()
    except Exception as error:
        raise ValueError(
            "El archivo no contiene una imagen válida o está dañado."
        ) from error

    mime = Image.MIME.get(formato) or mimetypes.guess_type(origen.name)[0]
    if not mime or not mime.startswith("image/"):
        raise ValueError("No se pudo determinar un tipo MIME válido para la imagen.")

    return origen, mime, origen.read_bytes()



def cambiar_imagen_membrete(ruta):
    origen, tipo_mime, contenido = validar_imagen(ruta)

    conexion = obtener_conexion()

    try:
        with conexion:
            with database_cursor(conexion) as cursor:
                # Desactivar el membrete vigente, sin borrar registros.
                cursor.execute("""
                    UPDATE personalizacion.membrete
                    SET estatus = FALSE
                    WHERE estatus = TRUE
                """)

                # Insertar el nuevo membrete como activo.
                cursor.execute("""
                    INSERT INTO personalizacion.membrete (
                        nombre_archivo,
                        tipo_mime,
                        imagen,
                        fecha_actualizacion,
                        estatus
                    )
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, TRUE)
                    RETURNING id_membrete
                """, (origen.name, tipo_mime, contenido))

                nuevo_id = cursor.fetchone()[0]

        return (
            "Membrete actualizado correctamente.\n"
            f"ID del nuevo membrete: {nuevo_id}\n"
            f"Archivo: {origen.name}\n"
            "El membrete anterior se conservó, pero quedó inactivo."
        )

    finally:
        conexion.close()


def obtener_membrete_activo():
    """Devuelve los datos del único membrete activo, sin exponer más filas."""
    conexion = obtener_conexion()
    try:
        with database_cursor(conexion) as cursor:
            cursor.execute(
                """
                SELECT id_membrete, nombre_archivo, tipo_mime, imagen,
                       fecha_actualizacion
                FROM personalizacion.membrete
                WHERE estatus = TRUE
                ORDER BY fecha_actualizacion DESC, id_membrete DESC
                LIMIT 2
                """
            )
            filas = cursor.fetchall()
    finally:
        conexion.close()

    if not filas:
        raise RuntimeError(
            "No hay un membrete activo en personalizacion.membrete."
        )
    if len(filas) > 1:
        raise RuntimeError(
            "Hay más de un membrete activo en personalizacion.membrete."
        )

    id_membrete, nombre, tipo_mime, imagen, actualizado = filas[0]
    if not imagen:
        raise RuntimeError(
            f"El membrete activo ({nombre}) no contiene datos de imagen."
        )
    return id_membrete, nombre, tipo_mime, bytes(imagen), actualizado


def reiniciar_folios():
    """Registra el reinicio del contador y conserva su historial."""
    conexion = obtener_conexion()
    try:
        with conexion:
            with database_cursor(conexion) as cursor:
                cursor.execute(
                    'LOCK TABLE personalizacion.configuracion_folios '
                    'IN SHARE ROW EXCLUSIVE MODE'
                )
                cursor.execute(
                    """
                    INSERT INTO personalizacion.configuracion_folios
                        (siguiente_numero)
                    VALUES (1)
                    """
                )
    finally:
        conexion.close()

    return (
        "Se registró el reinicio del contador a 1. El historial y los "
        "documentos existentes se conservaron; la reserva omitirá folios "
        "duplicados."
    )


def obtener_siguiente_folio():
    """Reserva y devuelve el siguiente folio usando el formato configurado."""
    conexion = obtener_conexion()
    try:
        with conexion:
            with database_cursor(conexion) as cursor:
                folio = reserve_next_folio(cursor)
    finally:
        conexion.close()

    return folio


def consultar_siguiente_folio():
    """Consulta el siguiente folio libre sin avanzar el contador."""
    conexion = obtener_conexion()
    try:
        with database_cursor(conexion) as cursor:
            return preview_next_folio(cursor)
    finally:
        conexion.close()


def obtener_configuracion_folio():
    conexion = obtener_conexion()
    try:
        with database_cursor(conexion) as cursor:
            return read_configuration(cursor)
    finally:
        conexion.close()


def obtener_configuraciones_folio():
    conexion = obtener_conexion()
    try:
        with database_cursor(conexion) as cursor:
            cursor.execute(
                """
                SELECT segmentos, digitos, fuente_membrete,
                       tamano_membrete, anio_folio
                FROM personalizacion.configuracion_formato_folio
                ORDER BY id_configuracion DESC
                """
            )
            filas = cursor.fetchall()
        if not filas:
            raise RuntimeError(
                'No existe el formato de folio en personalizacion. '
                'Ejecuta database\\personalizacion.sql.'
            )
        return [configuration_from_row(fila) for fila in filas]
    finally:
        conexion.close()


def guardar_configuracion_folio(template, digits, font, font_size, year=None):
    configuration = build_configuration(
        template, digits, font, font_size, year)
    conexion = obtener_conexion()
    try:
        with conexion:
            with database_cursor(conexion) as cursor:
                cursor.execute(
                    'LOCK TABLE personalizacion.configuracion_formato_folio '
                    'IN SHARE ROW EXCLUSIVE MODE'
                )
                cursor.execute(
                    """
                    INSERT INTO personalizacion.configuracion_formato_folio
                        (segmentos, digitos, fuente_membrete, tamano_membrete,
                         anio_folio, fecha_actualizacion)
                    VALUES (%s::jsonb, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id_configuracion
                    """,
                    (
                        json.dumps(
                            configuration['segmentos'], ensure_ascii=False),
                        configuration['digitos'],
                        configuration['fuente'],
                        configuration['tamano'],
                        configuration['anio_folio'],
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError(
                        'PostgreSQL no confirmó el guardado del formato de folio.'
                    )
                return int(row[0])
    finally:
        conexion.close()


def desactivar_membrete():
    conexion = obtener_conexion()
    try:
        with conexion:
            with database_cursor(conexion) as cursor:
                cursor.execute(
                    """
                    UPDATE personalizacion.membrete
                    SET estatus = FALSE
                    WHERE estatus IS TRUE
                    """
                )
                return cursor.rowcount
    finally:
        conexion.close()

def menu():
    while True:
        print("\n=== ADMINISTRACIÓN DEL CVDR ===")
        print("1. Reiniciar contador de folios")
        print("2. Cambiar imagen del membrete")
        print("3. Consultar siguiente folio disponible")
        print("0. Salir")

        opcion = input("Selecciona una opción: ").strip()

        try:
            if opcion == "1":
                confirmar = input(
                    "¿Confirmas reiniciar el contador a 1? "
                    "No se borrarán ni modificarán oficios (s/n): "
                ).strip().lower()
                if confirmar == "s":
                    print(reiniciar_folios())
                else:
                    print("Operación cancelada.")

            elif opcion == "2":
                ruta = input("Introduce la ruta completa de la imagen: ").strip()
                print(cambiar_imagen_membrete(ruta))

            elif opcion == "3":
                print(f"Siguiente folio disponible: {consultar_siguiente_folio()}")

            elif opcion == "0":
                print("Saliendo.")
                break

            else:
                print("Opción no válida.")

        except Exception as error:
            print(f"\nNo se pudo completar la operación: {error}")


if __name__ == "__main__":
    menu()
