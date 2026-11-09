import psycopg
from psycopg.rows import dict_row
from .config import DB_config
from pathlib import Path
from datetime import date


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
                    cursor.execute(
                        """
                        UPDATE correspondencia.borradores
                        SET estado = 'PDF generado',
                            actualizado_en = CURRENT_TIMESTAMP
                        WHERE folio = %s
                        RETURNING usuario_id, usuario_nombre
                        """,
                        (folio,),
                    )
                    creador = cursor.fetchone()
                    cursor.execute(
                        """
                        INSERT INTO correspondencia.notificaciones
                            (folio, tipo, titulo, mensaje, creado_por)
                        VALUES (%s, 'pdf_disponible', 'Nuevo PDF disponible',
                                %s, %s)
                        ON CONFLICT (folio, tipo) DO NOTHING
                        """,
                        (
                            folio,
                            f'El PDF del oficio {folio} ya está disponible.',
                            creador[0] if creador else 'sistema',
                        ),
                    )
        except psycopg.Error as error:
            raise RuntimeError(
                "No se pudo registrar la ruta del documento en PostgreSQL. "
                "Verifica la conexión y que la base existente tenga las tablas "
                "requeridas."
            ) from error
        finally:
            conexion.close()

    def reservar_borrador(self, usuario_id, usuario_nombre, max_folio_local=0):
        if not usuario_id:
            raise ValueError(
                'No se pudo identificar la cuenta autenticada para reservar el folio.'
            )

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
                            SELECT folio FROM correspondencia.oficios_documentos
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
                    folio = f'IPN/CVDRD/{siguiente:03d}/{anio}'
                    cursor.execute(
                        """
                        INSERT INTO correspondencia.borradores
                            (folio, usuario_id, usuario_nombre)
                        VALUES (%s, %s, %s)
                        """,
                        (folio, usuario_id, usuario_nombre),
                    )
                    return folio
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudo reservar el folio en PostgreSQL. Verifica la conexión '
                'y que la base existente tenga las tablas requeridas. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def obtener_borrador(self, folio, usuario_id):
        return self._consultar_borrador(folio, usuario_id)

    def _consultar_borrador(self, folio, usuario_id):
        conexion = self.get_connection()
        try:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT folio, usuario_id, usuario_nombre, asunto,
                           area_emisora, recepcion, cuerpo, estado,
                           actualizado_en
                    FROM correspondencia.borradores
                    WHERE folio = %s AND usuario_id = %s
                    """,
                    (folio, usuario_id),
                )
                return cursor.fetchone()
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudo recuperar el borrador de PostgreSQL. '
                'Verifica la conexión y que la base existente tenga las tablas '
                f'requeridas. Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def listar_borradores(self, usuario_id):
        conexion = self.get_connection()
        try:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT folio, asunto, estado, actualizado_en
                    FROM correspondencia.borradores
                    WHERE usuario_id = %s AND estado IN ('Borrador', 'Creado')
                    ORDER BY actualizado_en DESC
                    """,
                    (usuario_id,),
                )
                return cursor.fetchall()
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudieron consultar los borradores. Verifica la conexión '
                'y que la base existente tenga las tablas requeridas. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def guardar_borrador(
        self, folio, usuario_id, asunto, area_emisora, recepcion, cuerpo
    ):
        conexion = self.get_connection()
        try:
            with conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE correspondencia.borradores
                        SET asunto = %s, area_emisora = %s, recepcion = %s,
                            cuerpo = %s, estado = 'Borrador',
                            actualizado_en = CURRENT_TIMESTAMP
                        WHERE folio = %s AND usuario_id = %s
                          AND estado IN ('Borrador', 'Creado')
                        """,
                        (
                            asunto, area_emisora, recepcion, cuerpo,
                            folio, usuario_id,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise ValueError(
                            'No se encontró un borrador editable para este folio '
                            'y cuenta.'
                        )
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudo guardar el borrador en PostgreSQL. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def finalizar_borrador(
        self, folio, usuario_id, asunto, area_emisora, recepcion, cuerpo
    ):
        conexion = self.get_connection()
        try:
            with conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE correspondencia.borradores
                        SET asunto = %s, area_emisora = %s, recepcion = %s,
                            cuerpo = %s, estado = 'Creado',
                            actualizado_en = CURRENT_TIMESTAMP
                        WHERE folio = %s AND usuario_id = %s
                          AND estado IN ('Borrador', 'Creado')
                        """,
                        (
                            asunto, area_emisora, recepcion, cuerpo,
                            folio, usuario_id,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise ValueError(
                            'No se encontró un borrador editable para este folio '
                            'y cuenta.'
                        )
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudo finalizar el borrador en PostgreSQL. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def contar_notificaciones_no_leidas(self, usuario_id):
        conexion = self.get_connection()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM correspondencia.notificaciones n
                    LEFT JOIN correspondencia.notificaciones_leidas l
                      ON l.notificacion_id = n.id AND l.usuario_id = %s
                    WHERE l.notificacion_id IS NULL
                    """,
                    (usuario_id,),
                )
                return cursor.fetchone()[0]
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudo consultar el contador de notificaciones. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def listar_notificaciones(self, usuario_id, limite=50):
        conexion = self.get_connection()
        try:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT n.id, n.folio, n.titulo, n.mensaje,
                           n.creada_en,
                           (l.notificacion_id IS NOT NULL) AS leida
                    FROM correspondencia.notificaciones n
                    LEFT JOIN correspondencia.notificaciones_leidas l
                      ON l.notificacion_id = n.id AND l.usuario_id = %s
                    ORDER BY n.creada_en DESC
                    LIMIT %s
                    """,
                    (usuario_id, limite),
                )
                return cursor.fetchall()
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudieron cargar las notificaciones. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def marcar_notificaciones_leidas(self, usuario_id, notificacion_ids):
        if not notificacion_ids:
            return
        conexion = self.get_connection()
        try:
            with conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO correspondencia.notificaciones_leidas
                            (notificacion_id, usuario_id)
                        SELECT n.id, %s
                        FROM correspondencia.notificaciones n
                        WHERE n.id = ANY(%s)
                        ON CONFLICT (notificacion_id, usuario_id) DO NOTHING
                        """,
                        (usuario_id, notificacion_ids),
                    )
        except psycopg.Error as error:
            raise RuntimeError(
                'No se pudieron marcar las notificaciones como leídas. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def listar_rutas_documentos(self):
        conexion = self.get_connection()
        try:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT folio, ruta_archivo, fecha_registro
                    FROM correspondencia.oficios_documentos
                    ORDER BY fecha_registro DESC, folio
                    """
                )
                return cursor.fetchall()
        except psycopg.Error as error:
            raise RuntimeError(
                "No se pudieron consultar los documentos enviados en PostgreSQL. "
                "Verifica la conexión y que la base existente tenga las tablas "
                "requeridas."
            ) from error
        finally:
            conexion.close()
