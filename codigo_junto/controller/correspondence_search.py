"""Búsqueda combinable de correspondencia en PostgreSQL.

La consulta usa únicamente nombres de tablas y columnas definidos en el esquema
correspondencia. Los valores recibidos desde la interfaz siempre viajan como
parámetros de Psycopg.
"""
from datetime import date, datetime
from typing import Any


BASE_QUERY = """
SELECT tipo, id_oficio, folio, asunto, fecha, departamento, estado
FROM (
    SELECT
        'Enviado'::varchar AS tipo,
        envio.id_oficio,
        envio.folio,
        envio.asunto,
        envio.fecha,
        COALESCE(STRING_AGG(DISTINCT area.nombre, ', '), '') AS departamento,
        envio.estatus_actividad AS estado
    FROM correspondencia.oficios_envio AS envio
    LEFT JOIN correspondencia.oficios_area_emision AS relacion
        ON relacion.id_oficio = envio.id_oficio
    LEFT JOIN correspondencia.areas AS area
        ON area.id_area = relacion.id_area
    GROUP BY envio.id_oficio, envio.folio, envio.asunto,
             envio.fecha, envio.estatus_actividad

    UNION ALL

    SELECT
        'Recibido'::varchar AS tipo,
        recibido.id_oficio_recibido AS id_oficio,
        recibido.folio,
        recibido.asunto,
        recibido.fecha,
        COALESCE(STRING_AGG(DISTINCT area.nombre, ', '), '') AS departamento,
        NULL::varchar AS estado
    FROM correspondencia.oficios_recibido AS recibido
    LEFT JOIN correspondencia.oficios_area_recepcion AS relacion
        ON relacion.id_oficio_recibido = recibido.id_oficio_recibido
    LEFT JOIN correspondencia.areas AS area
        ON area.id_area = relacion.id_area
    GROUP BY recibido.id_oficio_recibido, recibido.folio,
             recibido.asunto, recibido.fecha
) AS coincidencias
"""


def _normalizar_fecha(value: date | datetime | str | None) -> date | None:
    """Convert an ISO date or datetime to a date suitable for Psycopg."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError("La fecha debe tener el formato AAAA-MM-DD.") from error


def build_search_query(
    *,
    folio: str | None = None,
    asunto: str | None = None,
    fecha_desde: date | datetime | str | None = None,
    fecha_hasta: date | datetime | str | None = None,
    departamento: str | None = None,
) -> tuple[str, tuple[Any, ...]]:
    """Build a parameterized query for received and sent correspondence.

    Empty criteria are ignored. All supplied values are bound separately,
    which keeps user-provided text out of the SQL statement.
    """
    desde = _normalizar_fecha(fecha_desde)
    hasta = _normalizar_fecha(fecha_hasta)
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")

    filters: list[str] = []
    params: list[Any] = []

    for column, value in (
        ("folio", folio),
        ("asunto", asunto),
        ("departamento", departamento),
    ):
        normalized = str(value).strip() if value is not None else ""
        if normalized:
            filters.append(f"{column} ILIKE %s")
            params.append(f"%{normalized}%")

    if desde:
        filters.append("fecha >= %s")
        params.append(desde)
    if hasta:
        filters.append("fecha <= %s")
        params.append(hasta)

    query = BASE_QUERY
    if filters:
        query += "\nWHERE " + "\n  AND ".join(filters)
    query += "\nORDER BY fecha DESC, folio ASC"
    return query, tuple(params)
