"""Consultas y operaciones del catálogo de áreas y empleados con borrado lógico."""

import pg8000.dbapi as dbapi

from controller.database_conecction import (
    Database_connection,
    database_cursor,
    database_transaction,
)


def usuario_puede_administrar(correo):
    """Comprueba el permiso de administración configurado en el catálogo."""
    correo = str(correo or '').strip().casefold()
    if not correo:
        return False
    conexion = Database_connection().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            cursor.execute(
                f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM correspondencia.empleado e
                    JOIN correspondencia.area_empleado ae
                      ON ae.id_empleado = e.id_empleado AND ae.activo = TRUE
                    JOIN correspondencia.areas a
                      ON a.id_area = ae.id_area AND a.activo = TRUE
                    WHERE LOWER(BTRIM(e.correo)) = %s
                      AND e.activo = TRUE
                      AND a.puede_administrar = TRUE
                )
                """,
                (correo,),
            )
            row = cursor.fetchone()
            return bool(row and row[0])
    except dbapi.Error as error:
        raise RuntimeError(
            f'No se pudo validar el permiso de administración: {error}'
        ) from error
    finally:
        conexion.close()


def listar_areas():
    """Devuelve todas las áreas activas del catálogo de PostgreSQL."""
    conexion = Database_connection().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            cursor.execute(
                """SELECT id_area, nombre
                   FROM correspondencia.areas
                   WHERE activo = TRUE
                   ORDER BY nombre"""
            )
            return cursor.fetchall()
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudieron consultar las áreas: {error}') from error
    finally:
        conexion.close()


def agregar_area(nombre):
    """Agrega un área al catálogo o reactiva la existente."""
    nombre = str(nombre or '').strip()
    if not nombre:
        raise ValueError('El nombre del área es obligatorio.')
    conexion = Database_connection().get_connection()
    try:
        with database_transaction(conexion):
            with database_cursor(conexion) as cursor:
                cursor.execute(
                    """INSERT INTO correspondencia.areas (nombre, activo)
                       VALUES (%s, TRUE)
                       ON CONFLICT (nombre) DO UPDATE
                           SET activo = TRUE
                       RETURNING id_area""",
                    (nombre,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError('PostgreSQL no devolvió el área guardada.')
                return row[0]
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudo guardar el área: {error}') from error
    finally:
        conexion.close()


def eliminar_area(id_area):
    """Desactiva un área y sus asignaciones sin borrar el historial."""
    conexion = Database_connection().get_connection()
    try:
        with database_transaction(conexion):
            with database_cursor(conexion) as cursor:
                cursor.execute(
                    """UPDATE correspondencia.areas
                       SET activo = FALSE
                       WHERE id_area = %s AND activo = TRUE""",
                    (int(id_area),),
                )
                if cursor.rowcount == 0:
                    raise ValueError('El área seleccionada no existe o ya está inactiva.')
                cursor.execute(
                    """UPDATE correspondencia.area_empleado
                       SET activo = FALSE
                       WHERE id_area = %s AND activo = TRUE""",
                    (int(id_area),),
                )
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudo desactivar el área: {error}') from error
    finally:
        conexion.close()


def listar_empleados():
    """Lista empleados y todas sus asignaciones activas del catálogo."""
    conexion = Database_connection().get_connection()
    try:
        with database_cursor(conexion) as cursor:
            cursor.execute(
                """SELECT e.id_empleado, e.correo,
                          COALESCE(
                              STRING_AGG(a.nombre, ', ' ORDER BY a.nombre)
                                  FILTER (WHERE a.id_area IS NOT NULL),
                              'Sin área'
                          ) AS areas
                   FROM correspondencia.empleado e
                   LEFT JOIN correspondencia.area_empleado ae
                     ON ae.id_empleado = e.id_empleado AND ae.activo = TRUE
                   LEFT JOIN correspondencia.areas a
                     ON a.id_area = ae.id_area AND a.activo = TRUE
                   WHERE e.activo = TRUE
                   GROUP BY e.id_empleado, e.correo
                   ORDER BY e.correo"""
            )
            return cursor.fetchall()
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudieron consultar los usuarios: {error}') from error
    finally:
        conexion.close()


def agregar_empleado(correo, id_area):
    """Crea un empleado o reactiva uno inactivo y reactiva/crea su asignación."""
    correo = str(correo or '').strip().casefold()
    if not correo:
        raise ValueError('El correo es obligatorio.')
    if '@' not in correo:
        raise ValueError('Ingresa un correo electrónico válido.')
    conexion = Database_connection().get_connection()
    try:
        with database_transaction(conexion):
            with database_cursor(conexion) as cursor:
                cursor.execute(
                    """SELECT id_area FROM correspondencia.areas
                       WHERE id_area = %s AND activo = TRUE""",
                    (int(id_area),),
                )
                if cursor.fetchone() is None:
                    raise ValueError('El área seleccionada no existe o está inactiva.')

                cursor.execute(
                    """INSERT INTO correspondencia.empleado (correo, activo)
                       VALUES (%s, TRUE)
                       ON CONFLICT ((LOWER(BTRIM(correo)))) DO UPDATE
                           SET activo = TRUE
                       RETURNING id_empleado""",
                    (correo,),
                )
                id_empleado = cursor.fetchone()[0]
                cursor.execute(
                    """INSERT INTO correspondencia.area_empleado
                           (id_empleado, id_area, activo)
                       VALUES (%s, %s, TRUE)
                       ON CONFLICT (id_empleado, id_area) DO UPDATE
                           SET activo = TRUE""",
                    (id_empleado, int(id_area)),
                )
                return id_empleado
    except dbapi.IntegrityError as error:
        raise ValueError('No fue posible registrar el usuario o su asignación.') from error
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudo registrar el usuario: {error}') from error
    finally:
        conexion.close()


def eliminar_empleado(id_empleado):
    """Desactiva al empleado y sus asignaciones sin borrar datos."""
    conexion = Database_connection().get_connection()
    try:
        with database_transaction(conexion):
            with database_cursor(conexion) as cursor:
                cursor.execute(
                    """UPDATE correspondencia.empleado
                       SET activo = FALSE
                       WHERE id_empleado = %s AND activo = TRUE""",
                    (int(id_empleado),),
                )
                if cursor.rowcount == 0:
                    raise ValueError('El usuario seleccionado no existe o ya está inactivo.')
                cursor.execute(
                    """UPDATE correspondencia.area_empleado
                       SET activo = FALSE
                       WHERE id_empleado = %s AND activo = TRUE""",
                    (int(id_empleado),),
                )
    except dbapi.Error as error:
        raise RuntimeError(f'No se pudo desactivar el usuario: {error}') from error
    finally:
        conexion.close()
