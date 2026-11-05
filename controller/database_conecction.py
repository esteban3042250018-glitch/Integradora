import psycopg
from psycopg.rows import dict_row
from .config import DB_config
from pathlib import Path


class Database_connection:
    def __init__(self):
        self.config = DB_config

    def get_connection(self):
        try:
            conexion = psycopg.connect(**self.config)
            return conexion
        except psycopg.Error as e:
            print(f"Error al conectar con PostgreSQL: {e}")
            raise ConnectionError("No fue posible conectar con PostgreSQL.") from e

    def ejecutar_consulta(self, query, params=()):
        conexion = self.get_connection()

        try:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, params)
                resultados = cursor.fetchall()
                return resultados

        except psycopg.Error as e:
            print(f"Error en la consulta SQL: {e}")
            return None

        finally:
            conexion.close()

    def registrar_ruta_documento(self, folio, ruta_archivo):
        conexion = self.get_connection()
        try:
            with conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO correspondencia.oficios_documentos
                            (folio, ruta_archivo)
                        VALUES (%s, %s)
                        ON CONFLICT (folio) DO UPDATE
                        SET ruta_archivo = EXCLUDED.ruta_archivo,
                            fecha_actualizacion = CURRENT_TIMESTAMP
                        """,
                        (folio, str(Path(ruta_archivo).resolve())),
                    )
        except psycopg.Error as error:
            raise RuntimeError(
                "No se pudo registrar la ruta del documento en PostgreSQL. "
                "Verifica la conexión y ejecuta database/crear_tabla_documentos.sql."
            ) from error
        finally:
            conexion.close()
