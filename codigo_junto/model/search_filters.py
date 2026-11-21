"""Funciones puras de filtrado para la bandeja de correspondencia.

La vista entrega registros con el formato consumido por HomeScreen:
folio en la posición 0, tipo en 1, prioridad en 5 y estado en 8.
"""
from collections.abc import Iterable, Sequence
from typing import Any


def matching_records(
    records: Iterable[Sequence[Any]],
    query: str = "",
    state: str = "Estado",
    priority: str = "Prioridad",
    category: str = "all",
) -> list[Sequence[Any]]:
    """Filtra registros por texto, estado, prioridad y categoría.

    Todos los términos de la consulta deben aparecer en el registro. La
    comparación ignora mayúsculas/minúsculas y conserva los filtros originales
    usados por la bandeja de correspondencia.
    """
    terms = str(query or "").casefold().split()
    matches = []

    for record in records:
        if len(record) < 9:
            continue

        searchable_text = " ".join(str(value or "") for value in record).casefold()
        if not all(term in searchable_text for term in terms):
            continue
        if state != "Estado" and str(record[8]) != state:
            continue
        if priority != "Prioridad" and str(record[5]) != priority:
            continue

        record_state = str(record[8])
        record_type = str(record[1])
        has_folio = bool(record[0])

        category_matches = (
            category == "all"
            or (category == "con_folio" and has_folio)
            or record_state == category
            or (category == "seguimiento" and record_state in {"En atención", "Turnada"})
            or (category == "enviada" and record_type == "ENVIADA")
        )
        if category_matches:
            matches.append(record)

    return matches
