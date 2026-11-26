"""Small, dependency-free HTML bridge for Word and ReportLab content."""
import base64
from html import escape
from html.parser import HTMLParser
from io import BytesIO
import re
from urllib.parse import urlparse

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Inches, Pt, RGBColor
from docx.text.run import Run

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Image as PdfImage,
    ListFlowable,
    ListItem,
    Paragraph,
    Table as PdfTable,
    TableStyle,
)


_VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
              'link', 'meta', 'param', 'source', 'track', 'wbr'}
_BLOCK_TAGS = {'blockquote', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
               'ol', 'p', 'table', 'ul'}
_INLINE_TAGS = {
    'b': 'b', 'strong': 'b', 'i': 'i', 'em': 'i', 'u': 'u',
    's': 'strike', 'strike': 'strike', 'del': 'strike',
    'sup': 'super', 'sub': 'sub',
}
_SUPPORTED_IMAGE_MIMES = {
    'image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/tiff',
}
_CSS_COLORS = {
    'black': '#000000', 'blue': '#0000FF', 'gray': '#808080',
    'green': '#008000', 'red': '#FF0000', 'white': '#FFFFFF',
}


class HtmlNode:
    def __init__(self, tag=None, attrs=None, children=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = list(children or [])


class _FragmentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode()
        self.stack = [self.root]
        self.suppressed = 0

    def handle_starttag(self, tag, attrs):
        if self.suppressed:
            if tag in ('script', 'style'):
                self.suppressed += 1
            return
        if tag in ('script', 'style'):
            self.suppressed = 1
            return
        node = HtmlNode(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in _VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        if not self.suppressed and tag not in ('script', 'style'):
            self.stack[-1].children.append(HtmlNode(tag, attrs))

    def handle_endtag(self, tag):
        if self.suppressed:
            if tag in ('script', 'style'):
                self.suppressed -= 1
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        if data and not self.suppressed:
            self.stack[-1].children.append(data)


def parse_html_fragment(markup):
    parser = _FragmentParser()
    parser.feed(markup or '')
    parser.close()
    return parser.root.children


def _style_map(node):
    result = {}
    for declaration in node.attrs.get('style', '').split(';'):
        if ':' in declaration:
            key, value = declaration.split(':', 1)
            result[key.strip().lower()] = value.strip()
    return result


def _safe_url(value):
    parsed = urlparse(value or '')
    if parsed.scheme.lower() in ('http', 'https', 'mailto'):
        return value
    return None


def _parse_color(value):
    normalized = (value or '').strip().lower()
    normalized = _CSS_COLORS.get(normalized, normalized)
    if re.fullmatch(r'#[0-9a-f]{6}', normalized):
        return RGBColor.from_string(normalized[1:].upper())
    return None


def _style_for_inline(node, parent):
    style = dict(parent)
    tag = node.tag or ''
    if tag in ('b', 'strong'):
        style['bold'] = True
    elif tag in ('i', 'em'):
        style['italic'] = True
    elif tag == 'u':
        style['underline'] = True
    elif tag in ('s', 'strike', 'del'):
        style['strike'] = True
    elif tag == 'sup':
        style['superscript'] = True
    elif tag == 'sub':
        style['subscript'] = True

    css = _style_map(node)
    if css.get('font-weight', '').lower() in ('bold', '600', '700', '800', '900'):
        style['bold'] = True
    if css.get('font-style', '').lower() == 'italic':
        style['italic'] = True
    decoration = css.get('text-decoration', '').lower()
    if 'underline' in decoration:
        style['underline'] = True
    if 'line-through' in decoration:
        style['strike'] = True
    color = _parse_color(css.get('color'))
    if color is not None:
        style['color'] = color
    size = re.fullmatch(r'(\d+(?:\.\d+)?)(pt|px)?', css.get('font-size', ''))
    if size:
        style['size'] = float(size.group(1)) * (
            0.75 if size.group(2) == 'px' else 1)
    family = css.get('font-family', '').split(',')[0].strip().strip('"\'')
    if family:
        style['font'] = family
    return style


def _new_run(paragraph, parent_element):
    run_element = OxmlElement('w:r')
    parent_element.append(run_element)
    return Run(run_element, paragraph)


def _format_run(run, style):
    run.bold = style.get('bold', False)
    run.italic = style.get('italic', False)
    run.underline = style.get('underline', False)
    run.font.strike = style.get('strike', False)
    if style.get('superscript'):
        run.font.superscript = True
    if style.get('subscript'):
        run.font.subscript = True
    if style.get('color') is not None:
        run.font.color.rgb = style['color']
    if style.get('size') is not None:
        run.font.size = Pt(style['size'])
    if style.get('font'):
        run.font.name = style['font']
    return run


def _image_bytes(node):
    source = node.attrs.get('src', '')
    match = re.fullmatch(
        r'(data:(image/[a-zA-Z0-9.+-]+);base64),([A-Za-z0-9+/=\r\n]+)',
        source,
    )
    if not match or match.group(2).lower() not in _SUPPORTED_IMAGE_MIMES:
        return None
    try:
        return base64.b64decode(match.group(3), validate=True)
    except ValueError:
        return None


def _append_inline(paragraph, nodes, style=None, parent_element=None):
    style = dict(style or {})
    if parent_element is None:
        parent_element = paragraph._p
    for node in nodes:
        if isinstance(node, str):
            if node:
                _format_run(_new_run(paragraph, parent_element), style).text = node
            continue

        current_style = _style_for_inline(node, style)
        if node.tag == 'br':
            _format_run(_new_run(paragraph, parent_element), current_style).add_break()
        elif node.tag == 'img':
            content = _image_bytes(node)
            if content:
                _format_run(_new_run(paragraph, parent_element), current_style).add_picture(
                    BytesIO(content))
            elif node.attrs.get('alt'):
                _format_run(_new_run(paragraph, parent_element), current_style).text = (
                    node.attrs['alt'])
        elif node.tag == 'a' and _safe_url(node.attrs.get('href')):
            hyperlink = OxmlElement('w:hyperlink')
            relationship_id = paragraph.part.relate_to(
                node.attrs['href'], RT.HYPERLINK, is_external=True)
            hyperlink.set(qn('r:id'), relationship_id)
            parent_element.append(hyperlink)
            _append_inline(
                paragraph, node.children, current_style, hyperlink)
        else:
            _append_inline(paragraph, node.children, current_style, parent_element)


def _paragraph_style(document, node, list_tag=None, list_level=0):
    if list_tag:
        base = 'List Bullet' if list_tag == 'ul' else 'List Number'
        name = base if list_level == 0 else f'{base} {list_level + 1}'
        try:
            document.styles[name]
            return name
        except KeyError:
            return base
    if node.tag and re.fullmatch(r'h[1-6]', node.tag):
        return f'Heading {node.tag[1]}'
    return None


def _apply_paragraph_attributes(paragraph, node):
    alignment = _style_map(node).get('text-align', '').lower()
    paragraph.alignment = {
        'left': WD_ALIGN_PARAGRAPH.LEFT,
        'center': WD_ALIGN_PARAGRAPH.CENTER,
        'right': WD_ALIGN_PARAGRAPH.RIGHT,
        'justify': WD_ALIGN_PARAGRAPH.JUSTIFY,
    }.get(alignment)
    style = _style_map(node)
    margin = re.fullmatch(r'(\d+(?:\.\d+)?)(pt|px)?', style.get('margin-left', ''))
    if margin:
        points = float(margin.group(1)) * (0.75 if margin.group(2) == 'px' else 1)
        paragraph.paragraph_format.left_indent = Pt(points)


def _new_paragraph(parent, document, node, list_tag=None, list_level=0,
                   first_paragraph=None):
    style = _paragraph_style(document, node, list_tag, list_level)
    if first_paragraph is not None:
        paragraph = first_paragraph
        paragraph.text = ''
        if style:
            paragraph.style = style
    else:
        paragraph = parent.add_paragraph(style=style)
    _apply_paragraph_attributes(paragraph, node)
    _append_inline(paragraph, node.children)
    return paragraph


def _row_nodes(table_node):
    for child in table_node.children:
        if isinstance(child, HtmlNode) and child.tag == 'tr':
            yield child
        elif isinstance(child, HtmlNode) and child.tag in ('tbody', 'thead', 'tfoot'):
            for row in child.children:
                if isinstance(row, HtmlNode) and row.tag == 'tr':
                    yield row


def _add_table(parent, document, table_node):
    rows = []
    for row_node in _row_nodes(table_node):
        cells = [
            cell for cell in row_node.children
            if isinstance(cell, HtmlNode) and cell.tag in ('td', 'th')
        ]
        if cells:
            rows.append(cells)
    column_count = max((len(row) for row in rows), default=0)
    if not column_count:
        return

    if hasattr(parent, '_tc'):
        table = parent.add_table(
            rows=len(rows), cols=column_count, width=Inches(7))
    else:
        table = parent.add_table(rows=len(rows), cols=column_count)
    try:
        table.style = 'Table Grid'
    except KeyError:
        pass
    table.autofit = True

    for row_index, row in enumerate(rows):
        for column_index in range(column_count):
            cell = table.cell(row_index, column_index)
            cell.text = ''
            if column_index >= len(row):
                continue
            contents = row[column_index].children
            _add_blocks(
                cell, contents, document, first_paragraph=cell.paragraphs[0])


def _add_list(parent, document, list_node, level=0):
    list_tag = list_node.tag if list_node.tag in ('ul', 'ol') else 'ul'
    for item in list_node.children:
        if not isinstance(item, HtmlNode) or item.tag != 'li':
            continue
        inline = []

        def flush():
            if not inline:
                return
            paragraph = parent.add_paragraph(
                style=_paragraph_style(document, list_node, list_tag, level))
            _append_inline(paragraph, inline)
            inline.clear()

        for child in item.children:
            if isinstance(child, HtmlNode) and child.tag in ('ul', 'ol', 'table'):
                flush()
                if child.tag == 'table':
                    _add_table(parent, document, child)
                else:
                    _add_list(parent, document, child, level + 1)
            elif isinstance(child, HtmlNode) and child.tag in _BLOCK_TAGS:
                flush()
                if child.tag in ('ul', 'ol'):
                    _add_list(parent, document, child, level + 1)
                elif child.tag == 'table':
                    _add_table(parent, document, child)
                else:
                    paragraph = parent.add_paragraph(
                        style=_paragraph_style(document, child, list_tag, level))
                    _apply_paragraph_attributes(paragraph, child)
                    _append_inline(paragraph, child.children)
            else:
                inline.append(child)
        flush()


def _add_blocks(parent, nodes, document, first_paragraph=None):
    reusable = first_paragraph
    inline = []

    def flush_inline():
        nonlocal reusable
        if inline:
            wrapper = HtmlNode('p', children=list(inline))
            _new_paragraph(parent, document, wrapper, first_paragraph=reusable)
            reusable = None
            inline.clear()

    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                inline.append(node)
            continue
        if node.tag in _BLOCK_TAGS:
            flush_inline()
            if node.tag == 'table':
                _add_table(parent, document, node)
            elif node.tag in ('ul', 'ol'):
                _add_list(parent, document, node)
            elif node.tag == 'div' and any(
                isinstance(child, HtmlNode) and child.tag in _BLOCK_TAGS
                for child in node.children
            ):
                _add_blocks(parent, node.children, document, reusable)
                reusable = None
            else:
                _new_paragraph(parent, document, node, first_paragraph=reusable)
                reusable = None
        else:
            inline.append(node)
    flush_inline()


def html_to_word_document(document, fragment):
    """Append supported rich HTML blocks to a python-docx document."""
    _add_blocks(document, parse_html_fragment(fragment), document)


def html_to_plain_text(fragment):
    """Extract visible text for empty-document checks and legacy callers."""
    output = []

    def visit(nodes):
        for node in nodes:
            if isinstance(node, str):
                output.append(node)
            elif node.tag == 'img':
                output.append(node.attrs.get('alt') or '[imagen]')
            elif node.tag in ('br', 'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5',
                              'h6', 'li', 'tr'):
                visit(node.children)
                output.append('\n')
            else:
                visit(node.children)

    visit(parse_html_fragment(fragment))
    return ''.join(output)


def _inline_markup(nodes):
    output = []
    for node in nodes:
        if isinstance(node, str):
            output.append(escape(node).replace('\n', '<br/>'))
            continue
        if node.tag == 'br':
            output.append('<br/>')
            continue
        if node.tag == 'img':
            if node.attrs.get('alt'):
                output.append(escape(node.attrs['alt']))
            continue
        content = _inline_markup(node.children)
        tag = _INLINE_TAGS.get(node.tag)
        if node.tag == 'a':
            url = _safe_url(node.attrs.get('href'))
            if url:
                output.append(f'<link href="{escape(url, quote=True)}">{content}</link>')
            else:
                output.append(content)
        elif node.tag == 'span':
            css = _style_map(node)
            font_attributes = []
            color = css.get('color', '')
            color = _CSS_COLORS.get(color.lower(), color)
            if re.fullmatch(r'#[0-9a-fA-F]{6}', color):
                font_attributes.append(f'color="{color}"')
            size = re.fullmatch(r'(\d+(?:\.\d+)?)(pt|px)?', css.get('font-size', ''))
            if size:
                points = float(size.group(1)) * (
                    0.75 if size.group(2) == 'px' else 1)
                font_attributes.append(f'size="{points:g}"')
            family = css.get('font-family', '').split(',')[0].strip().strip('"\'')
            font_name = {
                'arial': 'Helvetica', 'calibri': 'Helvetica',
                'segoe ui': 'Helvetica', 'times new roman': 'Times-Roman',
                'courier new': 'Courier',
            }.get(family.lower())
            if font_name:
                font_attributes.append(f'name="{font_name}"')
            if font_attributes:
                output.append(f'<font {" ".join(font_attributes)}>{content}</font>')
            else:
                output.append(content)
        elif tag:
            output.append(f'<{tag}>{content}</{tag}>')
        elif node.tag == 'th':
            output.append(f'<b>{content}</b>')
        else:
            output.append(content)
    return ''.join(output)


def _pdf_image(node, max_width):
    content = _image_bytes(node)
    if not content:
        return None
    image = PdfImage(BytesIO(content))
    image._restrictSize(max_width, 500)
    return image


def _paragraph_style_for_node(node, base_style, serial):
    if not (node.tag and re.fullmatch(r'h[1-6]', node.tag)):
        style = ParagraphStyle(f'RichParagraph{serial}', parent=base_style)
    else:
        level = int(node.tag[1])
        style = ParagraphStyle(
            f'RichHeading{level}_{serial}',
            parent=base_style,
            fontName='Helvetica-Bold',
            fontSize=max(12, 18 - level),
            leading=max(16, 23 - level),
            spaceBefore=10,
            spaceAfter=8,
        )
    alignment = _style_map(node).get('text-align', '').lower()
    style.alignment = {
        'left': TA_LEFT, 'center': TA_CENTER, 'right': TA_RIGHT,
        'justify': TA_JUSTIFY,
    }.get(alignment, style.alignment)
    margin = re.fullmatch(r'(\d+(?:\.\d+)?)(pt|px)?', _style_map(node).get('margin-left', ''))
    if margin:
        style.leftIndent = float(margin.group(1)) * (
            0.75 if margin.group(2) == 'px' else 1)
    return style


def _paragraph_flowables(node, base_style, max_width, serial):
    markup = _inline_markup(node.children).strip()
    if not markup:
        markup = '&nbsp;'
    flowables = [Paragraph(
        markup, _paragraph_style_for_node(node, base_style, serial))]

    def add_images(nodes):
        for child in nodes:
            if isinstance(child, HtmlNode):
                if child.tag == 'img':
                    image = _pdf_image(child, max_width)
                    if image is not None:
                        flowables.append(image)
                else:
                    add_images(child.children)

    add_images(node.children)
    return flowables


def _render_list(node, base_style, max_width, serial):
    bullet_type = 'bullet' if node.tag == 'ul' else node.attrs.get('type', '1')
    items = []
    for child in node.children:
        if isinstance(child, HtmlNode) and child.tag == 'li':
            contents = _render_blocks(child.children, base_style, max_width, serial)
            if not contents:
                contents = [Paragraph('&nbsp;', base_style)]
            items.append(ListItem(contents))
    if not items:
        return []
    return [ListFlowable(
        items,
        bulletType=bullet_type,
        start=node.attrs.get('start', '1'),
        leftIndent=18,
        bulletFontName='Helvetica',
        bulletFontSize=10,
        spaceAfter=8,
    )]


def _render_table(node, base_style, max_width, serial):
    rows = []
    for row_node in _row_nodes(node):
        cells = [
            cell for cell in row_node.children
            if isinstance(cell, HtmlNode) and cell.tag in ('td', 'th')
        ]
        if cells:
            rows.append(cells)
    column_count = max((len(row) for row in rows), default=0)
    if not column_count:
        return []

    data = []
    for row in rows:
        rendered_row = []
        for index in range(column_count):
            if index >= len(row):
                rendered_row.append([Paragraph('&nbsp;', base_style)])
                continue
            contents = row[index].children
            if row[index].tag == 'th':
                contents = [HtmlNode('strong', children=contents)]
            cell_flowables = _render_blocks(
                contents, base_style, max_width / column_count, serial)
            rendered_row.append(cell_flowables or [Paragraph('&nbsp;', base_style)])
        data.append(rendered_row)

    has_header = any(
        isinstance(child, HtmlNode) and child.tag == 'thead'
        for child in node.children
    )
    table = PdfTable(
        data, colWidths=[max_width / column_count] * column_count,
        repeatRows=1 if has_header else 0,
        hAlign='LEFT',
    )
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#B8B8B8')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return [table]


def _render_blocks(nodes, base_style, max_width, serial):
    flowables = []
    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                flowables.append(Paragraph(escape(node), base_style))
        elif node.tag in ('p', 'div', 'blockquote', 'h1', 'h2', 'h3',
                          'h4', 'h5', 'h6'):
            if node.tag == 'div' and any(
                isinstance(child, HtmlNode) and child.tag in _BLOCK_TAGS
                for child in node.children
            ):
                flowables.extend(_render_blocks(
                    node.children, base_style, max_width, serial))
            else:
                flowables.extend(_paragraph_flowables(
                    node, base_style, max_width, serial))
                serial += 1
        elif node.tag in ('ul', 'ol'):
            flowables.extend(_render_list(
                node, base_style, max_width, serial))
            serial += 1
        elif node.tag == 'table':
            flowables.extend(_render_table(
                node, base_style, max_width, serial))
            serial += 1
        elif node.tag == 'img':
            image = _pdf_image(node, max_width)
            if image is not None:
                flowables.append(image)
    return flowables


def html_to_pdf_flowables(fragment, paragraph_style, max_width):
    """Convert semantic HTML blocks to ReportLab flowables."""
    flowables = _render_blocks(
        parse_html_fragment(fragment), paragraph_style, max_width, 1)
    return flowables or [Paragraph('&nbsp;', paragraph_style)]
