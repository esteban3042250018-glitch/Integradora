from contextlib import contextmanager
from datetime import date

import pg8000.dbapi as dbapi
from .config import DB_config


@contextmanager
def database_cursor(connection):
    cursor = connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def _row_as_dict(cursor, row):
    if row is None:
        return None
    return {
        column[0]: value
        for column, value in zip(cursor.description, row)
    }


def _rows_as_dicts(cursor, rows):
    return [_row_as_dict(cursor, row) for row in rows]


class Database_connection:
    def __init__(self):
        self.config = DB_config

    def get_connection(self):
        try:
            conexion = dbapi.connect(**self.config)
            return conexion
        except dbapi.Error as e:
            print(f"Error al conectar con PostgreSQL: {e}")
            raise ConnectionError("No fue posible conectar con PostgreSQL.") from e

    def ejecutar_consulta(self, query, params=()):
        conexion = self.get_connection()

        try:
            with database_cursor(conexion) as cursor:
                cursor.execute(query, params)
                return _rows_as_dicts(cursor, cursor.fetchall())

        except dbapi.Error as e:
            print(f"Error en la consulta SQL: {e}")
            return None

        finally:
            conexion.close()

    def registrar_pdf_generado(self, folio):
        conexion = self.get_connection()
        try:
            with conexion:
                with database_cursor(conexion) as cursor:
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
        except dbapi.Error as error:
            raise RuntimeError(
                "No se pudo actualizar el estado del borrador ni crear la "
                "notificación del PDF en PostgreSQL."
            ) from error
        finally:
            conexion.close()

    def reservar_folio(self, max_folio_local=0):
        anio = date.today().year
        conexion = self.get_connection()
        try:
            with conexion:
                with database_cursor(conexion) as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_xact_lock(%s, %s)', (18673, anio))
                    from model.folio_format import reserve_next_folio
                    return reserve_next_folio(cursor, max_folio_local)
        except dbapi.Error as error:
            raise RuntimeError(
                'No se pudo reservar el folio en PostgreSQL. Verifica que '
                'todos los equipos usen la base compartida y que existan '
                'personalizacion.configuracion_folios, '
                'personalizacion.configuracion_formato_folio y las tablas '
                'correspondencia.borradores, oficios_envio y oficios_recibido. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def reservar_borrador(self, usuario_id, usuario_nombre, max_folio_local=0):
        if not usuario_id:
            raise ValueError(
                'No se pudo identificar la cuenta autenticada para reservar el folio.'
            )

        anio = date.today().year
        conexion = self.get_connection()
        try:
            with conexion:
                with database_cursor(conexion) as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_xact_lock(%s, %s)', (18673, anio))
                    from model.folio_format import reserve_next_folio
                    folio = reserve_next_folio(cursor, max_folio_local)
                    cursor.execute(
                        """
                        INSERT INTO correspondencia.borradores
                            (folio, usuario_id, usuario_nombre)
                        VALUES (%s, %s, %s)
                        """,
                        (folio, usuario_id, usuario_nombre),
                    )
                    return folio
        except dbapi.Error as error:
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
            with database_cursor(conexion) as cursor:
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
                return _row_as_dict(cursor, cursor.fetchone())
        except dbapi.Error as error:
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
            with database_cursor(conexion) as cursor:
                cursor.execute(
                    """
                    SELECT folio, asunto, estado, actualizado_en
                    FROM correspondencia.borradores
                    WHERE usuario_id = %s AND estado IN ('Borrador', 'Creado')
                    ORDER BY actualizado_en DESC
                    """,
                    (usuario_id,),
                )
                return _rows_as_dicts(cursor, cursor.fetchall())
        except dbapi.Error as error:
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
                with database_cursor(conexion) as cursor:
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
        except dbapi.Error as error:
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
                with database_cursor(conexion) as cursor:
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
        except dbapi.Error as error:
            raise RuntimeError(
                'No se pudo finalizar el borrador en PostgreSQL. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def contar_notificaciones_no_leidas(self, usuario_id):
        conexion = self.get_connection()
        try:
            with database_cursor(conexion) as cursor:
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
        except dbapi.Error as error:
            raise RuntimeError(
                'No se pudo consultar el contador de notificaciones. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def listar_notificaciones(self, usuario_id, limite=50):
        conexion = self.get_connection()
        try:
            with database_cursor(conexion) as cursor:
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
                return _rows_as_dicts(cursor, cursor.fetchall())
        except dbapi.Error as error:
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
                with database_cursor(conexion) as cursor:
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
        except dbapi.Error as error:
            raise RuntimeError(
                'No se pudieron marcar las notificaciones como leídas. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()
