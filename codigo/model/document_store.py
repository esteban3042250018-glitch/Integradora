"""Registro local de folios y documentos."""
from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4


def ruta_documentos():
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home())
    return base / 'GestionInstitucional' / 'documentos.json'


def leer_documentos(ruta=None):
    ruta = Path(ruta) if ruta is not None else ruta_documentos()
    if not ruta.exists():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise ValueError('El historial de documentos está dañado.') from error
    if not isinstance(datos, list) or not all(isinstance(d, dict) for d in datos):
        raise ValueError('El archivo de documentos no tiene un formato válido.')
    return datos


def _escribir_documentos(ruta, registros):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(f'{ruta.name}.{uuid4().hex}.tmp')
    try:
        temporal.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding='utf-8')
        temporal.replace(ruta)
    finally:
        if temporal.exists():
            temporal.unlink()


@contextmanager
def _bloqueo(ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    carpeta = ruta.with_name(ruta.name + '.lock')
    inicio = time.monotonic()
    while True:
        try:
            carpeta.mkdir()
            break
        except FileExistsError:
            if carpeta.exists() and time.time() - carpeta.stat().st_mtime > 60:
                try:
                    carpeta.rmdir()
                except OSError:
                    pass
            if time.monotonic() - inicio > 5:
                raise OSError('Otro proceso está usando el historial. Vuelve a intentar.')
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            carpeta.rmdir()
        except OSError:
            pass


def _nuevo_folio(registros, anio):
    regex = re.compile(rf'IPN/CVDRD/(\d+)/{anio}\Z')
    numeros = []
    for registro in registros:
        identificador = str(registro.get('folio') or registro.get('id', ''))
        coincidencia = regex.fullmatch(identificador)
        if coincidencia:
            numeros.append(int(coincidencia.group(1)))
    siguiente = max(numeros, default=0) + 1
    return f'IPN/CVDRD/{siguiente:03d}/{anio}'


def reservar_folio(ruta=None):
    ruta = Path(ruta) if ruta is not None else ruta_documentos()
    with _bloqueo(ruta):
        registros = leer_documentos(ruta)
        ahora = datetime.now()
        folio = _nuevo_folio(registros, ahora.year)
        registros.append({
            'id': folio,
            'folio': folio,
            'estado': 'Reservado',
            'asunto': '',
            'area_emisora': '',
            'recepcion': '',
            'cuerpo': '',
            'reservado_el': ahora.isoformat(timespec='seconds'),
        })
        _escribir_documentos(ruta, registros)
    return folio


def obtener_documento(folio, ruta=None):
    for registro in leer_documentos(ruta):
        if registro.get('folio') == folio or registro.get('id') == folio:
            return registro.copy()
    return None


def guardar_documento(asunto, area_emisora, recepcion, cuerpo, ruta=None, *, folio=None):
    campos = {
        'asunto': asunto.strip(),
        'area_emisora': area_emisora.strip(),
        'recepcion': recepcion.strip(),
        'cuerpo': cuerpo.strip(),
    }
    for nombre, valor in campos.items():
        if not valor and nombre != 'cuerpo': # El cuerpo puede ser flexible pero validamos los principales
            raise ValueError('Completa el campo: ' + nombre.replace('_', ' ').capitalize())

    ruta = Path(ruta) if ruta is not None else ruta_documentos()
    with _bloqueo(ruta):
        registros = leer_documentos(ruta)
        if folio is None:
            folio = _nuevo_folio(registros, datetime.now().year)
            registros.append({'id': folio, 'folio': folio, 'estado': 'Reservado',
                              'reservado_el': datetime.now().isoformat(timespec='seconds')})
        for registro in registros:
            if registro.get('folio') != folio:
                continue
            if registro.get('estado') == 'Creado':
                raise ValueError(f'El folio {folio} ya se utilizó para un documento.')
            registro.update(campos)
            registro['estado'] = 'Creado'
            registro['creado_el'] = datetime.now().isoformat(timespec='seconds')
            _escribir_documentos(ruta, registros)
            return registro.copy()
        raise ValueError(f'No se encontró la reserva {folio}. Regresa y reserva otro folio.')