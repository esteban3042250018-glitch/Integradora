import base64
import hashlib
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import winreg
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from controller.database_conecction import database_cursor
from model.generar_membrete import (
    ALTO_PAGINA, ANCHO_PAGINA, DESPLAZAMIENTO_FOLIO, agregar_folio,
    agregar_imagen_fondo, obtener_conexion, obtener_imagen_membrete,
)
from model.document_store import ruta_docx_oficio
from model.folio_format import read_configuration
from controller.rich_content import (
    HtmlNode, html_to_word_document, parse_html_fragment,
)


def _buscar_word():
    encontrado = shutil.which('WINWORD.EXE')
    if encontrado:
        return encontrado

    rutas_registro = (
        r'Software\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE',
        r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE',
    )
    for raiz in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for ruta in rutas_registro:
            try:
                with winreg.OpenKey(raiz, ruta) as clave:
                    ejecutable = winreg.QueryValue(clave, None)
            except OSError:
                continue
            ejecutable = os.path.expandvars(ejecutable.strip('"'))
            if Path(ejecutable).is_file():
                return ejecutable

    for variable in ('ProgramFiles', 'ProgramFiles(x86)'):
        base = os.environ.get(variable)
        if not base:
            continue
        for version in ('Office16', 'Office15'):
            ejecutable = Path(base) / 'Microsoft Office' / 'root' / version / 'WINWORD.EXE'
            if ejecutable.is_file():
                return str(ejecutable)
    raise FileNotFoundError(
        'No se encontró Microsoft Word de escritorio. Instálalo para abrir y editar el oficio.'
    )


def preparar_documento_word(folio, asunto, cuerpo_html=''):
    ruta = ruta_docx_oficio(folio)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists():
        conexion = obtener_conexion()
        try:
            _, _, imagen_membrete = obtener_imagen_membrete(conexion)
            with database_cursor(conexion) as cursor:
                configuracion_folio = read_configuration(cursor)
        finally:
            conexion.close()

        documento = Document()
        documento.core_properties.title = f'Oficio {folio}'
        documento.core_properties.subject = asunto
        seccion = documento.sections[0]
        seccion.page_width = Inches(ANCHO_PAGINA)
        seccion.page_height = Inches(ALTO_PAGINA)
        # Match the writing area used by the PDF generator (margins in points).
        seccion.top_margin = Inches(290 / 72)
        seccion.bottom_margin = Inches(110 / 72)
        seccion.left_margin = Inches(54 / 72)
        seccion.right_margin = Inches(54 / 72)
        seccion.header_distance = Inches(0.1)
        seccion.footer_distance = Inches(0)

        encabezado = seccion.header
        encabezado.is_linked_to_previous = False
        parrafo_folio = encabezado.paragraphs[0]
        parrafo_folio.paragraph_format.space_before = Inches(
            DESPLAZAMIENTO_FOLIO)
        agregar_folio(parrafo_folio, folio, configuracion_folio)
        agregar_imagen_fondo(
            encabezado.add_paragraph(),
            imagen_membrete,
            ANCHO_PAGINA,
            ALTO_PAGINA,
        )

        if cuerpo_html:
            html_to_word_document(documento, cuerpo_html)
        documento.save(ruta)
    return ruta


def crear_o_abrir_word(folio, asunto, cuerpo_html=''):
    if os.name != 'nt':
        raise OSError('La apertura de Microsoft Word está disponible en Windows.')

    ruta = preparar_documento_word(folio, asunto, cuerpo_html)
    subprocess.Popen([_buscar_word(), str(ruta)])
    return ruta


def leer_texto_word(ruta):
    try:
        documento = Document(ruta)
    except (BadZipFile, PackageNotFoundError) as error:
        raise ValueError('El archivo de Word no es un documento .docx válido.') from error
    lineas = [parrafo.text for parrafo in documento.paragraphs]
    for tabla in documento.tables:
        for fila in tabla.rows:
            lineas.append('\t'.join(celda.text for celda in fila.cells))
    return '\n'.join(lineas).strip()


def _safe_hyperlink(value):
    from urllib.parse import urlparse

    scheme = urlparse(value or '').scheme.lower()
    return value if scheme in ('http', 'https', 'mailto') else None


def _run_to_html(run):
    fragments = []
    text = html.escape(run.text).replace('\n', '<br/>').replace('\t', '&#9;')
    if text:
        fragments.append(text)

    for image in run._r.xpath('.//a:blip'):
        relationship_id = image.get(qn('r:embed'))
        related = run.part.related_parts.get(relationship_id)
        if related is None or related.content_type.lower() not in {
            'image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/tiff',
        }:
            continue
        encoded = base64.b64encode(related.blob).decode('ascii')
        fragments.append(
            f'<img src="data:{related.content_type};base64,{encoded}" alt=""/>')

    content = ''.join(fragments)
    if not content:
        return ''
    if run.bold:
        content = f'<strong>{content}</strong>'
    if run.italic:
        content = f'<em>{content}</em>'
    if run.underline:
        content = f'<u>{content}</u>'
    if run.font.strike:
        content = f'<del>{content}</del>'
    if run.font.superscript:
        content = f'<sup>{content}</sup>'
    if run.font.subscript:
        content = f'<sub>{content}</sub>'

    styles = []
    if run.font.name:
        styles.append(f'font-family:{html.escape(run.font.name, quote=True)}')
    if run.font.size:
        styles.append(f'font-size:{run.font.size.pt:g}pt')
    if run.font.color.rgb:
        styles.append(f'color:#{run.font.color.rgb}')
    if styles:
        content = f'<span style="{";".join(styles)}">{content}</span>'
    return content


def _paragraph_inline_html(paragraph):
    fragments = []
    for child in paragraph._p.iterchildren():
        if child.tag == qn('w:r'):
            fragments.append(_run_to_html(Run(child, paragraph)))
        elif child.tag == qn('w:hyperlink'):
            relationship_id = child.get(qn('r:id'))
            relationship = paragraph.part.rels.get(relationship_id)
            content = ''.join(
                _run_to_html(Run(run, paragraph))
                for run in child.iterchildren()
                if run.tag == qn('w:r')
            )
            target = _safe_hyperlink(
                relationship.target_ref if relationship is not None else None)
            fragments.append(
                f'<a href="{html.escape(target, quote=True)}">{content}</a>'
                if target else content
            )
    return ''.join(fragments)


def _paragraph_to_node(paragraph):
    style_name = paragraph.style.name if paragraph.style else ''
    heading = re.match(r'^Heading ([1-6])$', style_name or '')
    node = HtmlNode(f'h{heading.group(1)}' if heading else 'p')
    alignment = paragraph.alignment
    alignment_names = {
        0: 'left', 1: 'center', 2: 'right', 3: 'justify',
    }
    if alignment in alignment_names:
        node.attrs['style'] = f'text-align:{alignment_names[alignment]}'
    if paragraph.paragraph_format.left_indent:
        margin = paragraph.paragraph_format.left_indent.pt
        existing = node.attrs.get('style', '')
        node.attrs['style'] = f'{existing};margin-left:{margin:g}pt'.lstrip(';')
    node.children = parse_html_fragment(_paragraph_inline_html(paragraph))
    return node


def _list_info(paragraph, document):
    style_name = paragraph.style.name if paragraph.style else ''
    style_match = re.match(r'^List (Bullet|Number)(?:\s+(\d+))?$', style_name or '')
    depth = max(int(style_match.group(2) or 1) - 1, 0) if style_match else 0

    paragraph_properties = paragraph._p.pPr
    numbering_properties = (
        paragraph_properties.numPr if paragraph_properties is not None else None)
    if numbering_properties is None and paragraph.style is not None:
        style_properties = paragraph.style._element.pPr
        numbering_properties = (
            style_properties.numPr if style_properties is not None else None)
    if numbering_properties is None:
        if style_match:
            return depth, 'ul' if style_match.group(1) == 'Bullet' else 'ol', '1'
        return None

    num_id = (
        numbering_properties.numId.val
        if numbering_properties.numId is not None else None
    )
    if numbering_properties.ilvl is not None:
        depth = numbering_properties.ilvl.val
    number_format = (
        'bullet' if style_match and style_match.group(1) == 'Bullet'
        else 'decimal'
    )
    numbering = document.part.numbering_part.element
    if num_id is not None:
        number = next((
            item for item in numbering.num_lst
            if int(item.get(qn('w:numId'))) == num_id
        ), None)
        if number is not None:
            abstract_id = number.abstractNumId.val
            abstract = next((
                item for item in numbering.findall(qn('w:abstractNum'))
                if int(item.get(qn('w:abstractNumId'))) == abstract_id
            ), None)
            if abstract is not None:
                level = next((
                    item for item in abstract.findall(qn('w:lvl'))
                    if int(item.get(qn('w:ilvl'))) == depth
                ), None)
                if level is not None:
                    number_format_node = level.find(qn('w:numFmt'))
                    if number_format_node is not None:
                        number_format = number_format_node.get(qn('w:val'))

    if number_format == 'bullet':
        return depth, 'ul', '1'
    type_name = {
        'lowerLetter': 'a', 'upperLetter': 'A',
        'lowerRoman': 'i', 'upperRoman': 'I',
    }.get(number_format, '1')
    return depth, 'ol', type_name


def _append_list_paragraph(nodes, stack, paragraph_node, depth, tag, type_name, key):
    depth = min(max(depth, 0), 8)
    while len(stack) > depth + 1:
        stack.pop()
    if len(stack) == depth + 1 and stack[-1]['key'] != key:
        del stack[depth:]

    while len(stack) <= depth:
        level_tag = tag if len(stack) == depth else 'ul'
        attrs = {'type': type_name} if level_tag == 'ol' else {}
        list_node = HtmlNode(level_tag, attrs)
        if stack:
            parent_entry = stack[-1]
            if parent_entry['last_item'] is None:
                parent_entry['last_item'] = HtmlNode('li')
                parent_entry['node'].children.append(parent_entry['last_item'])
            parent_entry['last_item'].children.append(list_node)
        else:
            nodes.append(list_node)
        stack.append({
            'node': list_node,
            'last_item': None,
            'key': key if len(stack) == depth else (level_tag, None),
        })

    item = HtmlNode('li', children=[paragraph_node])
    stack[-1]['node'].children.append(item)
    stack[-1]['last_item'] = item


def _container_nodes(element, owner, document):
    nodes = []
    list_stack = []
    for child in element.iterchildren():
        if child.tag == qn('w:p'):
            paragraph = Paragraph(child, owner)
            list_info = _list_info(paragraph, document)
            paragraph_node = _paragraph_to_node(paragraph)
            if list_info:
                depth, tag, type_name = list_info
                properties = paragraph._p.pPr
                number_properties = (
                    properties.numPr if properties is not None else None)
                if number_properties is None and paragraph.style is not None:
                    style_properties = paragraph.style._element.pPr
                    number_properties = (
                        style_properties.numPr
                        if style_properties is not None else None)
                num_id = (
                    number_properties.numId.val
                    if number_properties is not None
                    and number_properties.numId is not None else None
                )
                _append_list_paragraph(
                    nodes, list_stack, paragraph_node, depth, tag, type_name,
                    (tag, type_name, num_id),
                )
            else:
                list_stack.clear()
                nodes.append(paragraph_node)
        elif child.tag == qn('w:tbl'):
            list_stack.clear()
            table = Table(child, owner)
            rows = []
            for row in table.rows:
                row_node = HtmlNode('tr')
                for cell in row.cells:
                    cell_node = HtmlNode('td')
                    cell_node.children = _container_nodes(cell._tc, cell, document)
                    row_node.children.append(cell_node)
                rows.append(row_node)
            nodes.append(HtmlNode('table', children=[
                HtmlNode('tbody', children=rows)]))
    return nodes


def _node_to_html(node):
    if isinstance(node, str):
        return html.escape(node)
    attrs = ''.join(
        f' {name}="{html.escape(value, quote=True)}"'
        for name, value in node.attrs.items()
    )
    content = ''.join(_node_to_html(child) for child in node.children)
    if node.tag in ('br', 'img'):
        return f'<{node.tag}{attrs}/>'
    return f'<{node.tag}{attrs}>{content}</{node.tag}>'


def leer_contenido_word(ruta):
    """Read a DOCX into semantic HTML while preserving common Word structure."""
    try:
        documento = Document(ruta)
    except (BadZipFile, PackageNotFoundError) as error:
        raise ValueError('El archivo de Word no es un documento .docx válido.') from error
    nodes = _container_nodes(documento.element.body, documento, documento)
    return ''.join(_node_to_html(node) for node in nodes).strip()


def firma_documento_word(ruta):
    digest = hashlib.sha256()
    with open(ruta, 'rb') as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
            digest.update(bloque)
    return digest.digest()
