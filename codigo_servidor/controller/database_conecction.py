import ssl
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


@contextmanager
def database_transaction(connection):
    try:
        yield
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()


def _row_as_dict(cursor, row):
    if row is None:
        return None
    return {
        column[0]: value
        for column, value in zip(cursor.description, row)
    }


def _rows_as_dicts(cursor, rows):
    return [_row_as_dict(cursor, row) for row in rows]


def _build_ssl_context(config):
    mode = str(config.get('sslmode') or 'prefer').strip().lower()
    root_cert = config.get('sslrootcert')
    client_cert = config.get('sslcert')
    client_key = config.get('sslkey')

    if mode == 'disable':
        return False
    if mode == 'allow':
        raise ValueError(
            'pg8000 no admite POSTGRES_SSLMODE=allow. Usa disable o prefer.'
        )
    if mode not in {'prefer', 'require', 'verify-ca', 'verify-full'}:
        raise ValueError(f'POSTGRES_SSLMODE no válido: {mode}')
    if mode == 'prefer' and not root_cert and not client_cert and not client_key:
        return None

    if mode in {'verify-ca', 'verify-full'} or (
        mode == 'require' and root_cert
    ):
        context = ssl.create_default_context(cafile=root_cert or None)
        context.check_hostname = mode == 'verify-full'
    else:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    if client_cert:
        context.load_cert_chain(client_cert, client_key)
    elif client_key:
        raise ValueError('POSTGRES_SSLKEY requiere POSTGRES_SSLCERT.')

    return context


class Database_connection:
    def __init__(self):
        self.config = DB_config

    def get_connection(self):
        host = str(self.config.get('host') or '').strip()
        if not host:
            raise ConnectionError(
                'Configura POSTGRES_HOST en .env con el nombre o la dirección '
                'del servidor PostgreSQL compartido.'
            )
        try:
            parameters = {
                key: value
                for key, value in self.config.items()
                if key not in {
                    'sslmode', 'sslrootcert', 'sslcert', 'sslkey',
                }
            }
            parameters['timeout'] = 8
            parameters['ssl_context'] = _build_ssl_context(self.config)
            conexion = dbapi.connect(**parameters)
            return conexion
        except (dbapi.Error, OSError, ValueError) as error:
            raise ConnectionError(
                'No fue posible conectar con PostgreSQL en '
                f'{host}:{self.config.get("port", 5432)}, '
                f'base "{self.config.get("database", "postgres")}": {error}'
            ) from error

    def ejecutar_consulta(self, query, params=()):
        conexion = self.get_connection()

        try:
            with database_cursor(conexion) as cursor:
                cursor.execute(query, params)
                return _rows_as_dicts(cursor, cursor.fetchall())

        except dbapi.Error as error:
            raise RuntimeError(
                'No fue posible ejecutar la consulta en PostgreSQL.'
            ) from error

        finally:
            conexion.close()

    def registrar_pdf_generado(
        self, folio, asunto, ruta_archivo, usuario_id, area_emisora=None
    ):
        if not ruta_archivo:
            raise ValueError('Falta la ruta del PDF guardado en el servidor.')
        if not asunto:
            raise ValueError('Falta el asunto del oficio que se va a registrar.')
        if not usuario_id:
            raise ValueError(
                'No se pudo identificar la cuenta que generó el PDF.')
        conexion = self.get_connection()
        try:
            with database_transaction(conexion):
                with database_cursor(conexion) as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_xact_lock(%s, hashtext(%s))',
                        (18674, folio),
                    )
                    cursor.execute(
                        """
                        SELECT id_oficio
                        FROM correspondencia.oficios_envio
                        WHERE folio = %s
                        FOR UPDATE
                        """,
                        (folio,),
                    )
                    documento = cursor.fetchone()
                    if documento is not None:
                        id_oficio = documento[0]
                        cursor.execute(
                            """
                            UPDATE correspondencia.oficios_envio
                            SET asunto = %s, ruta = %s
                            WHERE folio = %s
                            """,
                            (asunto, ruta_archivo, folio),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO correspondencia.prioridad (prioridad)
                            VALUES ('Media')
                            ON CONFLICT (prioridad) DO NOTHING
                            """
                        )
                        cursor.execute(
                            """
                            SELECT id_prioridad
                            FROM correspondencia.prioridad
                            WHERE prioridad = 'Media'
                            """
                        )
                        prioridad = cursor.fetchone()
                        if prioridad is None:
                            raise RuntimeError(
                                'No se encontró la prioridad predeterminada Media.'
                            )

                        cursor.execute(
                            """
                            INSERT INTO correspondencia.estatus_oficios
                                (estatus_oficio)
                            VALUES ('Creado'::correspondencia.estatus_enum)
                            ON CONFLICT (estatus_oficio) DO NOTHING
                            """
                        )
                        cursor.execute(
                            """
                            SELECT id_estatus
                            FROM correspondencia.estatus_oficios
                            WHERE estatus_oficio = 'Creado'
                            """
                        )
                        estado = cursor.fetchone()
                        if estado is None:
                            raise RuntimeError(
                                'No se encontró el estatus predeterminado Creado.'
                            )

                        cursor.execute(
                            """
                            INSERT INTO correspondencia.oficios_envio
                                (folio, asunto, fecha, id_prioridad, ruta,
                                 estatus_actividad)
                            VALUES (%s, %s, CURRENT_DATE, %s, %s, 'activo')
                            RETURNING id_oficio
                            """,
                            (folio, asunto, prioridad[0], ruta_archivo),
                        )
                        oficio = cursor.fetchone()
                        if oficio is None:
                            raise RuntimeError(
                                f'No se pudo crear el oficio {folio} '
                                'en correspondencia.oficios_envio.'
                            )
                        id_oficio = oficio[0]

                        cursor.execute(
                            """
                            INSERT INTO correspondencia.oficios_estatus
                                (id_oficio, id_estatus)
                            VALUES (%s, %s)
                            """,
                            (oficio[0], estado[0]),
                        )

                    if area_emisora:
                        cursor.execute(
                            """
                            SELECT id_area
                            FROM correspondencia.areas
                            WHERE activo = TRUE
                              AND LOWER(BTRIM(nombre)) = LOWER(BTRIM(%s))
                            """,
                            (area_emisora,),
                        )
                        area = cursor.fetchone()
                        if area is None:
                            raise ValueError(
                                f'El área emisora "{area_emisora}" no existe '
                                'o está inactiva. Regístrala en Áreas y usuarios.'
                            )
                        cursor.execute(
                            """
                            INSERT INTO correspondencia.oficios_area_emision
                                (id_oficio, id_area)
                            SELECT %s, %s
                            WHERE NOT EXISTS (
                                SELECT 1
                                FROM correspondencia.oficios_area_emision
                                WHERE id_oficio = %s AND id_area = %s
                            )
                            """,
                            (id_oficio, area[0], id_oficio, area[0]),
                        )

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
                            usuario_id,
                        ),
                    )
        except dbapi.Error as error:
            raise RuntimeError(
                "No se pudo crear/actualizar el oficio ni guardar la ruta del "
                "PDF en PostgreSQL."
            ) from error
        finally:
            conexion.close()

    def registrar_notificacion_pdf(self, folio, usuario_id):
        if not usuario_id:
            raise ValueError(
                'No se pudo identificar la cuenta que generó el PDF.')
        conexion = self.get_connection()
        try:
            with database_transaction(conexion):
                with database_cursor(conexion) as cursor:
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
                            usuario_id,
                        ),
                    )
        except dbapi.Error as error:
            raise RuntimeError(
                'No se pudo crear la notificación del PDF en PostgreSQL. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def actualizar_ruta_oficio(self, folio, ruta_pdf):
        if not ruta_pdf:
            raise ValueError('Falta la ruta del PDF.')
        conexion = self.get_connection()
        try:
            with database_transaction(conexion):
                with database_cursor(conexion) as cursor:
                    cursor.execute(
                        """
                        UPDATE correspondencia.oficios_envio
                        SET ruta = %s
                        WHERE folio = %s
                        RETURNING folio
                        """,
                        (str(ruta_pdf), folio),
                    )
                    return cursor.fetchone() is not None
        except dbapi.Error as error:
            raise RuntimeError(
                'No se pudo guardar la ruta del PDF del oficio en PostgreSQL.'
            ) from error
        finally:
            conexion.close()

    def reservar_folio(self):
        anio = date.today().year
        conexion = self.get_connection()
        try:
            with database_transaction(conexion):
                with database_cursor(conexion) as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_xact_lock(%s, %s)', (18673, anio))
                    from model.folio_format import reserve_next_folio
                    return reserve_next_folio(cursor)
        except dbapi.Error as error:
            raise RuntimeError(
                'No se pudo reservar el folio en PostgreSQL. Verifica que '
                'todos los equipos usen la base compartida y que existan '
                'personalizacion.configuracion_folios, '
                'personalizacion.configuracion_formato_folio y las tablas '
                'correspondencia.borradores y correspondencia.oficios_envio. '
                f'Detalle: {error}'
            ) from error
        finally:
            conexion.close()

    def reservar_borrador(self, usuario_id, usuario_nombre):
        if not usuario_id:
            raise ValueError(
                'No se pudo identificar la cuenta autenticada para reservar el folio.'
            )

        anio = date.today().year
        conexion = self.get_connection()
        try:
            with database_transaction(conexion):
                with database_cursor(conexion) as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_xact_lock(%s, %s)', (18673, anio))
                    from model.folio_format import reserve_next_folio
                    folio = reserve_next_folio(cursor)
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
                    SELECT b.folio, b.usuario_id, b.usuario_nombre, b.asunto,
                           b.area_emisora, b.recepcion, b.cuerpo, b.estado,
                           b.actualizado_en,
                           o.ruta AS ruta_pdf
                    FROM correspondencia.borradores b
                    LEFT JOIN correspondencia.oficios_envio o
                      ON o.folio = b.folio
                    WHERE b.folio = %s AND b.usuario_id = %s
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
            with database_transaction(conexion):
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
            with database_transaction(conexion):
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
            with database_transaction(conexion):
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
