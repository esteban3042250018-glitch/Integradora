"""Consultas y filtros del dashboard institucional de oficios."""
from collections import Counter

import pg8000.dbapi as dbapi

from controller.database_conecction import (
    Database_connection,
    database_cursor,
    database_transaction,
)

ESTADOS_COMUNES = (
    'Registrado', 'Creado', 'Enviado', 'Aprobado', 'Acusado', 'Sin estado',
)

_AREAS_OFICIO_CTE = """
areas_oficio AS (
    SELECT oa.id_oficio, oa.id_area
    FROM correspondencia.oficios_area_emision oa
    JOIN correspondencia.areas a
      ON a.id_area = oa.id_area AND a.activo = TRUE
    UNION
    SELECT o.id_oficio, a.id_area
    FROM correspondencia.oficios_envio o
    JOIN correspondencia.borradores b ON b.folio = o.folio
    JOIN correspondencia.areas a
      ON a.activo = TRUE
     AND LOWER(BTRIM(a.nombre)) = LOWER(BTRIM(b.area_emisora))
)
"""


def listar_oficios_dashboard(correo=None):
    """Devuelve los oficios activos con su área y estado vigente."""
    registros = Database_connection().ejecutar_consulta(f"""
        WITH {_AREAS_OFICIO_CTE}
        SELECT o.id_oficio, o.folio, o.asunto, o.fecha,
               o.ruta,
               COALESCE(areas.nombre, 'Área no identificada') AS area,
               COALESCE(e.estatus_oficio::text, 'Sin estado') AS estado,
               COALESCE(oe.fecha_modificacion, o.fecha::timestamp) AS fecha_estado
        FROM correspondencia.oficios_envio o
        LEFT JOIN (
            SELECT ao.id_oficio,
                   STRING_AGG(DISTINCT a.nombre, ', ' ORDER BY a.nombre) AS nombre
            FROM areas_oficio ao
            JOIN correspondencia.areas a
              ON a.id_area = ao.id_area AND a.activo = TRUE
            GROUP BY ao.id_oficio
        ) areas ON areas.id_oficio = o.id_oficio
        LEFT JOIN LATERAL (
            SELECT historial.id_estatus, historial.fecha_modificacion
            FROM correspondencia.oficios_estatus historial
            WHERE historial.id_oficio = o.id_oficio AND historial.activo = TRUE
            ORDER BY historial.fecha_modificacion DESC,
                     historial.id_oficio_estatus DESC
            LIMIT 1
        ) oe ON TRUE
        LEFT JOIN correspondencia.estatus_oficios e
          ON e.id_estatus = oe.id_estatus
        WHERE COALESCE(LOWER(o.estatus_actividad), 'activo') = 'activo'
        ORDER BY o.fecha DESC, o.id_oficio DESC
    """)
    ids_gestionables = {
        registro['id_oficio'] for registro in listar_oficios_area(correo)
    } if str(correo or '').strip() else set()
    for registro in registros:
        registro['puede_gestionar'] = registro['id_oficio'] in ids_gestionables
    return registros


def listar_oficios_area(correo):
    """Devuelve oficios asignados a las áreas activas del usuario."""
    correo = str(correo or '').strip()
    if not correo:
        raise ValueError('No se identificó el correo del usuario autenticado.')
    return Database_connection().ejecutar_consulta(f"""
        WITH {_AREAS_OFICIO_CTE}
        SELECT DISTINCT o.id_oficio, o.folio, o.asunto, o.fecha, o.ruta,
               a.nombre AS area,
               COALESCE(e.estatus_oficio::text, 'Sin estado') AS estado,
               COALESCE(oe.fecha_modificacion, o.fecha::timestamp) AS fecha_estado
        FROM correspondencia.oficios_envio o
        JOIN areas_oficio ao ON ao.id_oficio = o.id_oficio
        JOIN correspondencia.areas a
          ON a.id_area = ao.id_area AND a.activo = TRUE
        JOIN correspondencia.area_empleado ae
          ON ae.id_area = a.id_area AND ae.activo = TRUE
        JOIN correspondencia.empleado em
          ON em.id_empleado = ae.id_empleado AND em.activo = TRUE
        LEFT JOIN LATERAL (
            SELECT historial.id_estatus, historial.fecha_modificacion
            FROM correspondencia.oficios_estatus historial
            WHERE historial.id_oficio = o.id_oficio AND historial.activo = TRUE
            ORDER BY historial.fecha_modificacion DESC,
                     historial.id_oficio_estatus DESC
            LIMIT 1
        ) oe ON TRUE
        LEFT JOIN correspondencia.estatus_oficios e
          ON e.id_estatus = oe.id_estatus
        WHERE LOWER(BTRIM(em.correo)) = LOWER(BTRIM(%s))
          AND COALESCE(LOWER(o.estatus_actividad), 'activo') = 'activo'
        ORDER BY o.fecha DESC, o.id_oficio DESC
    """, (correo,))


def _validar_acceso_area(cursor, id_oficio, correo):
    if not str(correo or '').strip():
        raise ValueError('No se identificó el correo del usuario autenticado.')
    cursor.execute(f"""
        WITH {_AREAS_OFICIO_CTE}
        SELECT EXISTS (
            SELECT 1
            FROM areas_oficio ao
            JOIN correspondencia.areas a
              ON a.id_area = ao.id_area AND a.activo = TRUE
            JOIN correspondencia.area_empleado ae
              ON ae.id_area = a.id_area AND ae.activo = TRUE
            JOIN correspondencia.empleado em
              ON em.id_empleado = ae.id_empleado AND em.activo = TRUE
            WHERE ao.id_oficio = %s
              AND LOWER(BTRIM(em.correo)) = LOWER(BTRIM(%s))
        )
    """, (int(id_oficio), str(correo).strip()))
    acceso = cursor.fetchone()
    if not acceso or not acceso[0]:
        raise PermissionError(
            'No tienes permiso para consultar o modificar este oficio.'
        )


def obtener_archivos_oficio(id_oficio, correo=None, validar_area=False):
    """Devuelve el oficio original y los documentos de aprobación y acuse."""
    conexion = Database_connection().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            if validar_area:
                _validar_acceso_area(cursor, id_oficio, correo)
            cursor.execute(
                """
                SELECT folio, ruta
                FROM correspondencia.oficios_envio
                WHERE id_oficio = %s
                """,
                (int(id_oficio),),
            )
            oficio = cursor.fetchone()
            if not oficio:
                raise ValueError('No se encontró el oficio solicitado.')
            cursor.execute(
                """
                SELECT id_aprobado, ruta, fecha_ingreso
                FROM correspondencia.aprobados
                WHERE id_oficio = %s
                ORDER BY fecha_ingreso DESC, id_aprobado DESC
                """,
                (int(id_oficio),),
            )
            aprobados = _filas(cursor)
            cursor.execute(
                """
                SELECT id_acuse, ruta, fecha_ingreso, comentario
                FROM correspondencia.acuses
                WHERE id_oficio = %s
                ORDER BY fecha_ingreso DESC, id_acuse DESC
                """,
                (int(id_oficio),),
            )
            acuses = _filas(cursor)
            return {
                'folio': oficio[0], 'ruta': oficio[1],
                'aprobados': aprobados, 'acuses': acuses,
            }
    except dbapi.Error as error:
        raise RuntimeError(
            f'No se pudieron consultar los archivos del oficio: {error}'
        ) from error
    finally:
        conexion.close()


def obtener_historial_estados(id_oficio, correo=None, validar_area=False):
    """Devuelve los estados históricos más recientes primero."""
    conexion = Database_connection().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            if validar_area:
                _validar_acceso_area(cursor, id_oficio, correo)
            cursor.execute(
                """
                SELECT e.estatus_oficio::text AS estado,
                       oe.fecha_modificacion, oe.activo
                FROM correspondencia.oficios_estatus oe
                JOIN correspondencia.estatus_oficios e
                  ON e.id_estatus = oe.id_estatus
                WHERE oe.id_oficio = %s
                ORDER BY oe.fecha_modificacion DESC,
                         oe.id_oficio_estatus DESC
                """,
                (int(id_oficio),),
            )
            return _filas(cursor)
    except dbapi.Error as error:
        raise RuntimeError(
            f'No se pudo consultar el historial de estados: {error}'
        ) from error
    finally:
        conexion.close()


def _filas(cursor):
    columnas = [columna[0] for columna in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def _cambiar_estado(
    id_oficio, estado_nuevo, correo, tabla_archivo=None, ruta=None,
    comentario=None,
):
    """Actualiza el estado y conserva el historial, validando el área asignada."""
    if tabla_archivo not in (None, 'aprobados', 'acuses'):
        raise ValueError('El tipo de archivo asociado no es válido.')
    conexion = Database_connection().get_connection()
    try:
        with database_transaction(conexion):
            with database_cursor(conexion) as cursor:
                _validar_acceso_area(cursor, id_oficio, correo)
                cursor.execute(
                    """
                    SELECT id_estatus
                    FROM correspondencia.estatus_oficios
                    WHERE LOWER(estatus_oficio::text) = LOWER(%s)
                    LIMIT 1
                    """,
                    (estado_nuevo,),
                )
                estado = cursor.fetchone()
                if not estado:
                    raise ValueError(
                        f'No existe el estado {estado_nuevo} en PostgreSQL.'
                    )
                if tabla_archivo == 'aprobados':
                    if not ruta:
                        raise ValueError(
                            'Debes adjuntar el documento de aprobación.'
                        )
                    cursor.execute(
                        """
                        INSERT INTO correspondencia.aprobados
                            (id_oficio, ruta, fecha_ingreso)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        """,
                        (int(id_oficio), str(ruta)),
                    )
                elif tabla_archivo == 'acuses':
                    if not ruta and not str(comentario or '').strip():
                        raise ValueError(
                            'Adjunta un archivo o escribe un comentario para '
                            'registrar el acuse.'
                        )
                    cursor.execute(
                        """
                        INSERT INTO correspondencia.acuses
                            (id_oficio, ruta, fecha_ingreso, comentario)
                        VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
                        """,
                        (
                            int(id_oficio),
                            str(ruta) if ruta else None,
                            str(comentario or '').strip() or None,
                        ),
                    )
                cursor.execute(
                    """
                    UPDATE correspondencia.oficios_estatus
                    SET activo = FALSE
                    WHERE id_oficio = %s AND activo = TRUE
                    """,
                    (int(id_oficio),),
                )
                cursor.execute(
                    """
                    INSERT INTO correspondencia.oficios_estatus
                        (id_oficio, id_estatus, activo, fecha_modificacion)
                    VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP)
                    """,
                    (int(id_oficio), estado[0]),
                )
    except dbapi.Error as error:
        raise RuntimeError(
            f'No se pudo actualizar el estado del oficio: {error}'
        ) from error
    finally:
        conexion.close()


def marcar_creado(id_oficio, correo):
    _cambiar_estado(id_oficio, 'Creado', correo)


def marcar_enviado(id_oficio, correo):
    _cambiar_estado(id_oficio, 'Enviado', correo)


def marcar_aprobado(id_oficio, ruta, correo):
    _cambiar_estado(id_oficio, 'Aprobado', correo, 'aprobados', ruta)


def marcar_acusado(id_oficio, correo, ruta=None, comentario=None):
    _cambiar_estado(id_oficio, 'Acusado', correo, 'acuses', ruta, comentario)


def resumir_estados(registros):
    """Cuenta todos los estados presentes, incluidos estados no conocidos."""
    nombres_comunes = {estado.casefold(): estado for estado in ESTADOS_COMUNES}
    totales = Counter()
    adicionales = {}
    for registro in registros:
        estado = str(registro.get('estado') or 'Sin estado').strip() or 'Sin estado'
        clave = estado.casefold()
        etiqueta = nombres_comunes.get(clave)
        if etiqueta is None:
            etiqueta = adicionales.setdefault(clave, estado)
        totales[etiqueta] += 1
    estados = list(ESTADOS_COMUNES)
    estados.extend(sorted(adicionales.values(), key=str.casefold))
    cantidad = len(registros)
    return [
        {
            'estado': estado,
            'total': totales.get(estado, 0),
            'porcentaje': (
                totales.get(estado, 0) * 100 / cantidad if cantidad else 0
            ),
        }
        for estado in estados
    ]


def filtrar_oficios(registros, estado='Todos', area='Todas las áreas', consulta=''):
    """Filtra por estado, área y texto de folio, asunto o área."""
    estado_buscado = str(estado or 'Todos').strip().casefold()
    area_buscada = str(area or 'Todas las áreas').strip().casefold()
    texto = str(consulta or '').strip().casefold()

    resultado = []
    for registro in registros:
        estado_registro = str(registro.get('estado') or 'Sin estado').strip()
        area_registro = str(registro.get('area') or 'Área no identificada').strip()
        if estado_buscado not in ('', 'todos') and estado_registro.casefold() != estado_buscado:
            continue
        if area_buscada not in ('', 'todas las áreas') and area_registro.casefold() != area_buscada:
            continue
        if texto:
            campos = (
                registro.get('folio'), registro.get('asunto'), registro.get('area'),
            )
            if not any(texto in str(campo or '').casefold() for campo in campos):
                continue
        resultado.append(registro)
    return resultado
