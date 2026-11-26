"""Importa las rutas de PDF del historial JSON local a PostgreSQL."""
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from controller.app_paths import user_data_dir
from controller.database_conecction import Database_connection


def migrar_documentos_json(ruta=None, database=None):
    historial = Path(ruta) if ruta is not None else user_data_dir() / 'documentos.json'
    if not historial.is_file():
        return {
            'importados': 0,
            'sin_ruta': 0,
            'archivo_ausente': 0,
            'folio_no_encontrado': 0,
        }

    try:
        registros = json.loads(historial.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise ValueError('El historial de documentos está dañado; no se migró.') from error
    if not isinstance(registros, list) or not all(
        isinstance(registro, dict) for registro in registros
    ):
        raise ValueError('El historial de documentos no tiene un formato válido.')

    if database is None:
        database = Database_connection()
    resultado = {
        'importados': 0,
        'sin_ruta': 0,
        'archivo_ausente': 0,
        'folio_no_encontrado': 0,
    }
    for registro in registros:
        folio = str(registro.get('folio') or registro.get('id') or '').strip()
        ruta_pdf = str(registro.get('ruta_pdf') or '').strip()
        if not folio or not ruta_pdf:
            resultado['sin_ruta'] += 1
            continue
        archivo = Path(ruta_pdf).expanduser()
        if not archivo.is_file():
            resultado['archivo_ausente'] += 1
            continue
        if database.actualizar_ruta_oficio(folio, str(archivo.resolve())):
            resultado['importados'] += 1
        else:
            resultado['folio_no_encontrado'] += 1
    return resultado


def main():
    resultado = migrar_documentos_json()
    print(
        'Rutas importadas: {importados}; sin ruta/folio: {sin_ruta}; '
        'archivo no encontrado: {archivo_ausente}; sin oficio en PostgreSQL: '
        '{folio_no_encontrado}.'.format(**resultado)
    )


if __name__ == '__main__':
    main()
