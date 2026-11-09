import psycopg
from psycopg.rows import dict_row
from .config import DB_config
from datetime import date


class Database_connection:
    def __init__(self):
        self.config = DB_config

    def get_connection(self):
        try:
            conexion = psycopg.connect(**self.config, connect_timeout=8)
            return conexion
        except psycopg.Error as error:
            raise ConnectionError(
                'No fue posible conectar con PostgreSQL en '
                f'{self.config["host"]}:{self.config["port"]}, '
                f'base "{self.config["dbname"]}": {error}'
            ) from error

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

    def reservar_folio(self, max_folio_local=0):
        anio = date.today().year
        expresion = rf'^IPN/CVDRD/([0-9]+)/{anio}$'
        conexion = self.get_connection()
        try:
            with conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_xact_lock(%s, %s)', (18673, anio))
                    cursor.execute(
                        """
                        SELECT COALESCE(
                            MAX((regexp_match(folio, %s))[1]::BIGINT), 0
                        )
                        FROM (
                            SELECT folio FROM correspondencia.oficios_envio
                            UNION ALL
                            SELECT folio FROM correspondencia.oficios_recibido
                            UNION ALL
                            SELECT folio FROM correspondencia.borradores
                        ) AS folios
                        WHERE folio ~ %s
                        """,
                        (expresion, expresion),
                    )
                    maximo_existente = cursor.fetchone()[0]
                    cursor.execute(
                        """
                        SELECT ultimo_numero
                        FROM correspondencia.folios_anuales
                        WHERE anio = %s
                        FOR UPDATE
                        """,
                        (anio,),
                    )
                    fila = cursor.fetchone()
                    ultimo = fila[0] if fila else 0
                    siguiente = max(
                        ultimo, maximo_existente, max_folio_local
                    ) + 1
                    cursor.execute(
                        """
                        INSERT INTO correspondencia.folios_anuales
                            (anio, ultimo_numero)
                        VALUES (%s, %s)
                        ON CONFLICT (anio) DO UPDATE
                        SET ultimo_numero = EXCLUDED.ultimo_numero
                        """,
                        (anio, siguiente),
                    )
                    return f'IPN/CVDRD/{siguiente:03d}/{anio}'
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudo reservar el folio en PostgreSQL. Verifica que '
                'todos los equipos usen la base compartida y que existan las '
                'tablas correspondencia.folios_anuales, borradores, '
                'oficios_envio y oficios_recibido. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()
