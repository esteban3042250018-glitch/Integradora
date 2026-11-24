"""Consultas, historial de estados y archivos asociados a oficios enviados."""
from pathlib import Path
import pg8000.dbapi as dbapi
from controller.database_connection import Database_connection, database_cursor, database_transaction

ESTADOS = ('Creado', 'Enviado', 'Aprobado', 'Acusado')


def _db():
    return Database_connection()


def _filas(cursor):
    columnas = [c[0] for c in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def listar_oficios_dashboard():
    """Todos los oficios institucionales activos con su estado vigente."""
    conexion = _db().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            cursor.execute("""
                SELECT o.id_oficio, o.folio, o.asunto, o.fecha, o.ruta,
                       a.nombre AS area,
                       COALESCE(e.estatus_oficio::text, 'Sin estado') AS estado,
                       COALESCE(oe.fecha_modificacion, o.fecha::timestamp) AS fecha_estado
                FROM correspondencia.oficios_envio o
                LEFT JOIN correspondencia.oficios_area_emision oa ON oa.id_oficio = o.id_oficio
                LEFT JOIN correspondencia.areas a ON a.id_area = oa.id_area
                LEFT JOIN correspondencia.oficios_estatus oe
                  ON oe.id_oficio = o.id_oficio AND oe.activo = TRUE
                LEFT JOIN correspondencia.estatus_oficios e ON e.id_estatus = oe.id_estatus
                WHERE COALESCE(LOWER(o.estatus_actividad), 'activo') = 'activo'
                ORDER BY o.fecha DESC, o.id_oficio DESC
            """)
            return _filas(cursor)
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudo consultar el Dashboard institucional: {error}') from error
    finally:
        conexion.close()


def listar_oficios_area(correo):
    """Oficios de todas las áreas activas asignadas al usuario autenticado."""
    correo = str(correo or '').strip().casefold()
    if not correo:
        raise ValueError('No se identificó el correo del usuario autenticado.')
    conexion = _db().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            cursor.execute("""
                SELECT DISTINCT o.id_oficio, o.folio, o.asunto, o.fecha, o.ruta,
                       a.nombre AS area,
                       COALESCE(e.estatus_oficio::text, 'Sin estado') AS estado,
                       COALESCE(oe.fecha_modificacion, o.fecha::timestamp) AS fecha_estado
                FROM correspondencia.oficios_envio o
                JOIN correspondencia.oficios_area_emision oa ON oa.id_oficio = o.id_oficio
                JOIN correspondencia.areas a ON a.id_area = oa.id_area AND a.activo = TRUE
                JOIN correspondencia.area_empleado ae ON ae.id_area = a.id_area AND ae.activo = TRUE
                JOIN correspondencia.empleado em ON em.id_empleado = ae.id_empleado AND em.activo = TRUE
                LEFT JOIN correspondencia.oficios_estatus oe
                  ON oe.id_oficio = o.id_oficio AND oe.activo = TRUE
                LEFT JOIN correspondencia.estatus_oficios e ON e.id_estatus = oe.id_estatus
                WHERE LOWER(BTRIM(em.correo)) = %s
                  AND COALESCE(LOWER(o.estatus_actividad), 'activo') = 'activo'
                ORDER BY o.fecha DESC, o.id_oficio DESC
            """, (correo,))
            return _filas(cursor)
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudieron consultar los oficios de tu área: {error}') from error
    finally:
        conexion.close()


def obtener_archivos_oficio(id_oficio, correo=None, validar_area=False):
    """Devuelve oficio original, todas las aprobaciones y todos los acuses."""
    conexion = _db().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            if validar_area:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM correspondencia.oficios_area_emision oa
                        JOIN correspondencia.area_empleado ae ON ae.id_area = oa.id_area AND ae.activo = TRUE
                        JOIN correspondencia.empleado em ON em.id_empleado = ae.id_empleado AND em.activo = TRUE
                        JOIN correspondencia.areas ar ON ar.id_area = ae.id_area AND ar.activo = TRUE
                        WHERE oa.id_oficio = %s AND LOWER(BTRIM(em.correo)) = LOWER(BTRIM(%s))
                    )
                """, (int(id_oficio), str(correo or '')))
                if not cursor.fetchone()[0]:
                    raise PermissionError('No tienes permiso para consultar los archivos de este oficio.')
            cursor.execute("SELECT folio, ruta FROM correspondencia.oficios_envio WHERE id_oficio = %s", (int(id_oficio),))
            oficio = cursor.fetchone()
            if not oficio:
                raise ValueError('No se encontró el oficio solicitado.')
            cursor.execute("SELECT id_aprobado, ruta, fecha_ingreso FROM correspondencia.aprobados WHERE id_oficio = %s ORDER BY fecha_ingreso DESC, id_aprobado DESC", (int(id_oficio),))
            aprobados = _filas(cursor)
            cursor.execute("SELECT id_acuse, ruta, fecha_ingreso, comentario FROM correspondencia.acuses WHERE id_oficio = %s ORDER BY fecha_ingreso DESC, id_acuse DESC", (int(id_oficio),))
            acuses = _filas(cursor)
            return {'folio': oficio[0], 'ruta': oficio[1], 'aprobados': aprobados, 'acuses': acuses}
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudieron consultar los archivos del oficio: {error}') from error
    finally:
        conexion.close()


def obtener_historial_estados(id_oficio, correo=None, validar_area=False):
    """Historial cronológico de estados; permite consulta institucional o por área."""
    conexion = _db().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            if validar_area:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM correspondencia.oficios_area_emision oa
                        JOIN correspondencia.area_empleado ae ON ae.id_area = oa.id_area AND ae.activo = TRUE
                        JOIN correspondencia.empleado em ON em.id_empleado = ae.id_empleado AND em.activo = TRUE
                        JOIN correspondencia.areas ar ON ar.id_area = ae.id_area AND ar.activo = TRUE
                        WHERE oa.id_oficio = %s AND LOWER(BTRIM(em.correo)) = LOWER(BTRIM(%s))
                    )
                """, (int(id_oficio), str(correo or '')))
                if not cursor.fetchone()[0]:
                    raise PermissionError('No tienes permiso para consultar el historial de este oficio.')
            cursor.execute("""
                SELECT e.estatus_oficio::text AS estado, oe.fecha_modificacion, oe.activo
                FROM correspondencia.oficios_estatus oe
                JOIN correspondencia.estatus_oficios e ON e.id_estatus = oe.id_estatus
                WHERE oe.id_oficio = %s
                ORDER BY oe.fecha_modificacion DESC, oe.id_oficio_estatus DESC
            """, (int(id_oficio),))
            return _filas(cursor)
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudo consultar el historial de estados: {error}') from error
    finally:
        conexion.close()


def _cambiar_estado(id_oficio, estado_nuevo, correo, tabla_archivo=None, ruta=None, comentario=None):
    """Cambia a cualquier estado sin exigir estados previos; conserva historial."""
    conexion = _db().get_connection()
    try:
        with database_transaction(conexion):
            with database_cursor(conexion) as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM correspondencia.oficios_area_emision oa
                        JOIN correspondencia.area_empleado ae ON ae.id_area = oa.id_area AND ae.activo = TRUE
                        JOIN correspondencia.empleado em ON em.id_empleado = ae.id_empleado AND em.activo = TRUE
                        JOIN correspondencia.areas ar ON ar.id_area = ae.id_area AND ar.activo = TRUE
                        WHERE oa.id_oficio = %s AND LOWER(BTRIM(em.correo)) = LOWER(BTRIM(%s))
                    )
                """, (int(id_oficio), str(correo or '')))
                if not cursor.fetchone()[0]:
                    raise PermissionError('No puedes modificar un oficio que no pertenece a tu área.')
                cursor.execute("SELECT folio FROM correspondencia.oficios_envio WHERE id_oficio = %s", (int(id_oficio),))
                oficio_base = cursor.fetchone()
                if not oficio_base:
                    raise ValueError('No se encontró el oficio que intentas actualizar.')
                folio = oficio_base[0]
                cursor.execute("SELECT id_estatus FROM correspondencia.estatus_oficios WHERE LOWER(estatus_oficio::text) = LOWER(%s) LIMIT 1", (estado_nuevo,))
                estado = cursor.fetchone()
                if not estado:
                    raise ValueError(f'No existe el estado {estado_nuevo}. Ejecuta la migración SQL.')
                if tabla_archivo == 'aprobados':
                    if not ruta:
                        raise ValueError('Debes adjuntar el documento de aprobación.')
                    cursor.execute("INSERT INTO correspondencia.aprobados (id_oficio, ruta, fecha_ingreso) VALUES (%s, %s, CURRENT_TIMESTAMP)", (int(id_oficio), str(ruta)))
                elif tabla_archivo == 'acuses':
                    if not ruta and not str(comentario or '').strip():
                        raise ValueError('Adjunta un archivo o escribe un comentario para registrar el acuse.')
                    cursor.execute("INSERT INTO correspondencia.acuses (id_oficio, ruta, fecha_ingreso, comentario) VALUES (%s, %s, CURRENT_TIMESTAMP, %s)", (int(id_oficio), str(ruta) if ruta else None, str(comentario or '').strip() or None))
                cursor.execute("UPDATE correspondencia.oficios_estatus SET activo = FALSE WHERE id_oficio = %s AND activo = TRUE", (int(id_oficio),))
                cursor.execute("INSERT INTO correspondencia.oficios_estatus (id_oficio, id_estatus, activo, fecha_modificacion) VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP)", (int(id_oficio), estado[0]))
                # Conserva los nombres de los adjuntos para actualizar sus rutas tras moverlos.
                cursor.execute(
                    "SELECT id_aprobado, ruta FROM correspondencia.aprobados WHERE id_oficio = %s AND ruta IS NOT NULL",
                    (int(id_oficio),),
                )
                aprobados = cursor.fetchall()
                cursor.execute(
                    "SELECT id_acuse, ruta FROM correspondencia.acuses WHERE id_oficio = %s AND ruta IS NOT NULL",
                    (int(id_oficio),),
                )
                acuses = cursor.fetchall()

                # La carpeta del oficio siempre refleja su estado vigente.
                from model.document_store import mover_archivos_estado, actualizar_estado_local
                carpeta_destino = mover_archivos_estado(folio, estado_nuevo)
                ruta_destino = carpeta_destino.resolve()
                cursor.execute(
                    "UPDATE correspondencia.oficios_envio SET ruta = %s WHERE id_oficio = %s",
                    (str(ruta_destino), int(id_oficio)),
                )
                for id_aprobado, ruta_anterior in aprobados:
                    cursor.execute(
                        "UPDATE correspondencia.aprobados SET ruta = %s WHERE id_aprobado = %s",
                        (str(ruta_destino / Path(str(ruta_anterior)).name), id_aprobado),
                    )
                for id_acuse, ruta_anterior in acuses:
                    cursor.execute(
                        "UPDATE correspondencia.acuses SET ruta = %s WHERE id_acuse = %s",
                        (str(ruta_destino / Path(str(ruta_anterior)).name), id_acuse),
                    )
                actualizar_estado_local(folio, estado_nuevo)
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudo actualizar el estado del oficio: {error}') from error
    finally:
        conexion.close()


def marcar_enviado(id_oficio, correo):
    _cambiar_estado(id_oficio, 'Enviado', correo)


def marcar_aprobado(id_oficio, ruta, correo):
    _cambiar_estado(id_oficio, 'Aprobado', correo, 'aprobados', ruta)


def marcar_acusado(id_oficio, correo, ruta=None, comentario=None):
    _cambiar_estado(id_oficio, 'Acusado', correo, 'acuses', ruta, comentario)


def marcar_creado(id_oficio, correo):
    _cambiar_estado(id_oficio, 'Creado', correo)
