from pathlib import Path
import mimetypes
import sys

try:
    from PIL import Image
except ImportError:
    Image = None


# Este archivo se encuentra en codigo/model/administracion.py.
CARPETA_CODIGO = Path(__file__).resolve().parent.parent
if str(CARPETA_CODIGO) not in sys.path:
    sys.path.insert(0, str(CARPETA_CODIGO))

try:
    from controller.database_conecction import Database_connection
except ImportError as error:
    raise ImportError(
        "No se pudo importar Database_connection. Verifica que este archivo "
        "esté en codigo/controller/database_conecction.py o ajusta el nombre "
        "del módulo al nombre real del archivo."
    ) from error


PREFIJO_FOLIO = "CVDR-DGO-"
DIGITOS_FOLIO = 4
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
            with conexion.cursor() as cursor:
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

def reiniciar_folios():
    """Reinicia el contador sin borrar ni modificar oficios."""
    conexion = obtener_conexion()
    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE personalizacion.configuracion_folios
                    SET siguiente_numero = 1,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    WHERE id_configuracion = 1
                    """
                )
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "No existe el registro id_configuracion=1 en "
                        "personalizacion.configuracion_folios. Ejecuta el SQL "
                        "de inicialización en DBeaver."
                    )
    finally:
        conexion.close()

    return "Contador reiniciado a 1. No se borró ni modificó ningún oficio."


def _folio_esta_ocupado(cursor, folio):
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM correspondencia.oficios_envio WHERE folio = %s
            UNION ALL
            SELECT 1 FROM correspondencia.oficios_recibido WHERE folio = %s
        )
        """,
        (folio, folio),
    )
    return cursor.fetchone()[0]


def obtener_siguiente_folio():
    """
    Reserva un folio y avanza el contador en una transacción.
    Omite folios que ya existan en enviados o recibidos.
    """
    conexion = obtener_conexion()
    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT siguiente_numero
                    FROM personalizacion.configuracion_folios
                    WHERE id_configuracion = 1
                    FOR UPDATE
                    """
                )
                fila = cursor.fetchone()
                if fila is None:
                    raise RuntimeError(
                        "No existe el registro del contador en "
                        "personalizacion.configuracion_folios."
                    )

                numero = fila[0]
                while True:
                    folio = f"{PREFIJO_FOLIO}{numero:0{DIGITOS_FOLIO}d}"
                    numero += 1
                    if not _folio_esta_ocupado(cursor, folio):
                        break

                cursor.execute(
                    """
                    UPDATE personalizacion.configuracion_folios
                    SET siguiente_numero = %s,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    WHERE id_configuracion = 1
                    """,
                    (numero,),
                )
    finally:
        conexion.close()

    return folio


def consultar_siguiente_folio():
    """Consulta el siguiente folio libre sin reservarlo."""
    conexion = obtener_conexion()
    try:
        with conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT siguiente_numero
                    FROM personalizacion.configuracion_folios
                    WHERE id_configuracion = 1
                    """
                )
                fila = cursor.fetchone()
                if fila is None:
                    raise RuntimeError(
                        "No existe el registro del contador en "
                        "personalizacion.configuracion_folios."
                    )

                numero = fila[0]
                while True:
                    folio = f"{PREFIJO_FOLIO}{numero:0{DIGITOS_FOLIO}d}"
                    if not _folio_esta_ocupado(cursor, folio):
                        return folio
                    numero += 1
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
