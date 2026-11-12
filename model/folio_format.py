"""Formato configurable y reserva compartida de folios."""
from datetime import date
import json
import re


DEFAULT_TEMPLATE = 'IPN/CVDRD/{numero}/{ano}'
DEFAULT_DIGITS = 3
DEFAULT_FONT = 'Arial'
DEFAULT_FONT_SIZE = 10
_TOKENS = re.compile(r'\{(numero|año|ano|year)\}', re.IGNORECASE)


def build_configuration(template, digits, font, font_size, year=None):
    template = str(template or '').strip()
    matches = list(_TOKENS.finditer(template))
    number_matches = [
        match for match in matches if match.group(1).lower() == 'numero'
    ]
    year_matches = [
        match for match in matches if match.group(1).lower() != 'numero'
    ]
    if len(number_matches) != 1:
        raise ValueError('El formato debe incluir {numero} exactamente una vez.')
    if len(year_matches) > 1:
        raise ValueError('El formato solo puede incluir un marcador de año.')
    remainder = _TOKENS.sub('', template)
    if '{' in remainder or '}' in remainder:
        raise ValueError('El formato contiene una variable no reconocida.')

    try:
        digits = int(digits)
    except (TypeError, ValueError) as error:
        raise ValueError('La cantidad de dígitos debe ser un entero.') from error
    if not 1 <= digits <= 12:
        raise ValueError('La cantidad de dígitos debe estar entre 1 y 12.')

    font = str(font or '').strip()
    if font not in {
        'Arial', 'Calibri', 'Helvetica', 'Times New Roman', 'Courier New',
    }:
        raise ValueError('Selecciona una fuente admitida.')
    try:
        font_size = float(font_size)
    except (TypeError, ValueError) as error:
        raise ValueError('El tamaño de fuente debe ser numérico.') from error
    if not 1 <= font_size <= 100:
        raise ValueError('El tamaño de fuente debe estar entre 1 y 100 puntos.')

    year_text = str(year).strip() if year is not None else ''
    if not year_text:
        year = None
    else:
        try:
            year = int(year_text)
        except (TypeError, ValueError) as error:
            raise ValueError('El año debe ser un entero de cuatro dígitos.') from error
        if not 1000 <= year <= 9999:
            raise ValueError('El año debe estar entre 1000 y 9999.')

    segments = []
    position = 0
    for match in matches:
        if match.start() > position:
            segments.append({
                'tipo': 'texto',
                'valor': template[position:match.start()],
            })
        token = match.group(1).lower()
        segments.append({
            'tipo': 'numero' if token == 'numero' else 'anio',
            'valor': '',
        })
        position = match.end()
    if position < len(template):
        segments.append({'tipo': 'texto', 'valor': template[position:]})

    return {
        'segmentos': segments,
        'digitos': digits,
        'fuente': font,
        'tamano': font_size,
        'anio_folio': year,
    }


def template_from_segments(segments):
    if isinstance(segments, str):
        segments = json.loads(segments)
    if not isinstance(segments, list) or not segments:
        raise ValueError('La configuración de folio no contiene segmentos válidos.')

    parts = []
    number_count = 0
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError('La configuración contiene un segmento inválido.')
        kind = str(segment.get('tipo', '')).strip().lower()
        if kind == 'numero':
            number_count += 1
            parts.append('{numero}' + str(segment.get('valor', '')))
        elif kind == 'anio':
            parts.append('{ano}' + str(segment.get('valor', '')))
        elif kind == 'texto':
            value = str(segment.get('valor', ''))
            if value.strip().upper() in {'AÑO', 'ANO', '{ANO}', '{AÑO}'}:
                parts.append('{ano}')
            else:
                parts.append(value)
        else:
            raise ValueError('La configuración contiene un tipo de segmento inválido.')
    if number_count != 1:
        raise ValueError('La configuración debe incluir un segmento numérico.')
    return ''.join(parts)


def template_from_editor_segments(segments):
    if not isinstance(segments, list) or not segments:
        raise ValueError('Agrega al menos un cuadro al formato del folio.')
    parts = []
    number_count = 0
    year_count = 0
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            raise ValueError(f'El cuadro {index} no es válido.')
        kind = str(segment.get('tipo', '')).strip().lower()
        value = str(segment.get('valor', '')).strip()
        if kind == 'texto':
            if not value:
                raise ValueError(f'Completa el texto del cuadro {index}.')
            parts.append(value)
        elif kind == 'numero':
            number_count += 1
            parts.append('{numero}' + value)
        elif kind == 'anio':
            year_count += 1
            parts.append('{ano}' + value)
        else:
            raise ValueError(f'El tipo del cuadro {index} no es válido.')
    if number_count != 1:
        raise ValueError('Debe existir exactamente un cuadro numérico.')
    if year_count > 1:
        raise ValueError('Solo puedes agregar un cuadro de año.')
    return ''.join(parts)


def editor_segments_from_configuration(configuration):
    template = template_from_segments(configuration['segmentos'])
    segments = []
    position = 0
    for match in _TOKENS.finditer(template):
        if match.start() > position:
            segments.append({
                'tipo': 'texto',
                'valor': template[position:match.start()],
            })
        segments.append({
            'tipo': 'numero' if match.group(1).lower() == 'numero' else 'anio',
            'valor': '',
        })
        position = match.end()
    if position < len(template):
        segments.append({'tipo': 'texto', 'valor': template[position:]})
    return segments


def configuration_from_row(row):
    if not row:
        raise RuntimeError(
            'No existe el formato de folio en personalizacion. '
            'Ejecuta database\\personalizacion.sql.'
        )
    segments, digits, font, font_size, *year_value = row
    template = template_from_segments(segments)
    year = year_value[0] if year_value else None
    return build_configuration(template, digits, font, font_size, year)


def read_configuration(cursor):
    cursor.execute(
        """
        SELECT segmentos, digitos, fuente_membrete, tamano_membrete,
               anio_folio
        FROM personalizacion.configuracion_formato_folio
        ORDER BY id_configuracion DESC
        LIMIT 1
        """
    )
    return configuration_from_row(cursor.fetchone())


def render_folio(number, configuration, year=None):
    if year is None:
        year = configuration.get('anio_folio') or date.today().year
    template = template_from_segments(configuration['segmentos'])
    result = []
    position = 0
    for match in _TOKENS.finditer(template):
        result.append(template[position:match.start()])
        token = match.group(1).lower()
        if token == 'numero':
            result.append(str(int(number)).zfill(configuration['digitos']))
        else:
            result.append(str(year))
        position = match.end()
    result.append(template[position:])
    return ''.join(result)


def _folio_pattern(configuration):
    template = template_from_segments(configuration['segmentos'])
    parts = []
    position = 0
    for match in _TOKENS.finditer(template):
        parts.append(re.escape(template[position:match.start()]))
        if match.group(1).lower() == 'numero':
            parts.append(r'(?P<numero>\d+)')
        else:
            parts.append(r'(?P<anio>\d{4})')
        position = match.end()
    parts.append(re.escape(template[position:]))
    return re.compile(''.join(parts))


def folio_search_pattern(configuration):
    """Compila el formato vigente para localizar folios dentro de asuntos."""
    pattern = _folio_pattern(configuration)
    return re.compile(
        rf'(?<![A-Za-z0-9])(?P<folio>{pattern.pattern})(?![A-Za-z0-9])',
        re.IGNORECASE,
    )


def folio_number(folio, configuration, year=None):
    match = _folio_pattern(configuration).fullmatch(str(folio))
    if not match:
        return None
    folio_year = match.groupdict().get('anio')
    if year is not None and folio_year not in (None, str(year)):
        return None
    return int(match.group('numero'))


def _folios_existentes(cursor):
    cursor.execute(
        """
        SELECT folio FROM correspondencia.oficios_envio WHERE folio IS NOT NULL
        UNION ALL
        SELECT folio FROM correspondencia.oficios_recibido WHERE folio IS NOT NULL
        UNION ALL
        SELECT folio FROM correspondencia.borradores WHERE folio IS NOT NULL
        """
    )
    return {str(row[0]) for row in cursor.fetchall()}


def _siguiente_numero(cursor, configuration, existing, max_local=0):
    cursor.execute(
        """
        SELECT siguiente_numero
        FROM personalizacion.configuracion_folios
        ORDER BY id_configuracion DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    number = int(row[0]) if row else 1

    folio_year = configuration.get('anio_folio') or date.today().year
    used = []
    for folio in existing:
        value = folio_number(folio, configuration, str(folio_year))
        if value is not None:
            used.append(value)
    return max(number, int(max_local) + 1, max(used, default=0) + 1)


def reserve_next_folio(cursor, max_local=0):
    cursor.execute('LOCK TABLE personalizacion.configuracion_folios IN SHARE ROW EXCLUSIVE MODE')
    configuration = read_configuration(cursor)
    existing = _folios_existentes(cursor)
    number = _siguiente_numero(cursor, configuration, existing, max_local)

    while True:
        folio = render_folio(number, configuration)
        if folio not in existing:
            break
        number += 1

    cursor.execute(
        """
        INSERT INTO personalizacion.configuracion_folios (siguiente_numero)
        VALUES (%s)
        """,
        (number + 1,),
    )
    return folio


def preview_next_folio(cursor):
    configuration = read_configuration(cursor)
    existing = _folios_existentes(cursor)
    number = _siguiente_numero(cursor, configuration, existing)
    while True:
        folio = render_folio(number, configuration)
        if folio not in existing:
            return folio
        number += 1


def reportlab_font(font, bold=False):
    base = {
        'Arial': 'Helvetica',
        'Calibri': 'Helvetica',
        'Helvetica': 'Helvetica',
        'Times New Roman': 'Times',
        'Courier New': 'Courier',
    }.get(font, 'Helvetica')
    if not bold:
        return {
            'Helvetica': 'Helvetica',
            'Times': 'Times-Roman',
            'Courier': 'Courier',
        }[base]
    return {
        'Helvetica': 'Helvetica-Bold',
        'Times': 'Times-Bold',
        'Courier': 'Courier-Bold',
    }[base]
