import base64
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches

from controller.rich_content import html_to_word_document
from controller.word_controller import (
    leer_contenido_word, preparar_documento_word,
)


def _png_1x1():
    def chunk(kind, data):
        body = kind + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff\xff"))
        + chunk(b"IEND", b"")
    )


class WordControllerTests(unittest.TestCase):
    def test_word_read_preserves_inline_formatting_lists_and_table_order(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / 'rich.docx'
            document = Document()
            paragraph = document.add_paragraph()
            paragraph.add_run('Bold').bold = True
            paragraph.add_run(' italic').italic = True
            document.add_paragraph('Bullet item', style='List Bullet')
            document.add_paragraph('Nested bullet', style='List Bullet 2')
            document.add_paragraph('Numbered item', style='List Number')
            direct_list_item = document.add_paragraph('Direct Word bullet')
            numbering_id = document.styles['List Bullet']._element.pPr.numPr.numId.val
            num_properties = OxmlElement('w:numPr')
            level = OxmlElement('w:ilvl')
            level.set(qn('w:val'), '0')
            num_id = OxmlElement('w:numId')
            num_id.set(qn('w:val'), str(numbering_id))
            num_properties.append(level)
            num_properties.append(num_id)
            direct_list_item._p.get_or_add_pPr().append(num_properties)
            table = document.add_table(rows=1, cols=2)
            table.cell(0, 0).text = 'Cell A'
            table.cell(0, 1).text = 'Cell B'
            document.save(path)

            content = leer_contenido_word(path)

        self.assertIn('<strong>Bold</strong>', content)
        self.assertIn('<em> italic</em>', content)
        self.assertIn('<ul', content)
        self.assertIn('<ol', content)
        self.assertIn('Direct Word bullet', content)
        self.assertIn('<table>', content)
        self.assertLess(content.index('Bullet item'), content.index('Cell A'))
        self.assertIn('Cell B', content)

    def test_rich_html_creates_formatted_word_paragraphs_and_tables(self):
        document = Document()

        html_to_word_document(
            document,
            '<h1>Heading</h1><p>Text <strong>bold</strong></p>'
            '<ul><li>Bullet<ul><li>Nested</li></ul></li></ul>'
            '<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>',
        )

        self.assertEqual(document.paragraphs[0].style.name, 'Heading 1')
        self.assertTrue(document.paragraphs[1].runs[1].bold)
        self.assertIn('List Bullet', document.paragraphs[2].style.name)
        self.assertIn('List Bullet 2', document.paragraphs[3].style.name)
        self.assertEqual(document.tables[0].cell(0, 1).text, 'B')
        self.assertEqual(document.tables[0].cell(1, 0).text, '1')

    def test_rich_html_roundtrip_keeps_hyperlinks_and_embedded_images(self):
        image_data = base64.b64encode(_png_1x1()).decode('ascii')
        document = Document()
        html_to_word_document(
            document,
            '<p><a href="https://example.com">Link</a></p>'
            f'<p><img src="data:image/png;base64,{image_data}" alt="Logo"/></p>',
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / 'rich.docx'
            document.save(path)
            content = leer_contenido_word(path)
            image_count = len(Document(path).inline_shapes)

        self.assertIn('href="https://example.com"', content)
        self.assertIn('>Link</a>', content)
        self.assertIn('data:image/png;base64,', content)
        self.assertEqual(image_count, 1)

    def test_new_desktop_document_includes_active_letterhead(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "oficio.docx"
            connection = MagicMock()
            cursor = connection.cursor.return_value
            cursor.fetchall.return_value = [
                ("membrete.png", "image/png", _png_1x1()),
            ]

            with (
                patch("controller.word_controller.obtener_conexion",
                      return_value=connection),
                patch("controller.word_controller.read_configuration",
                      return_value={"fuente": "Arial", "tamano": 10}),
                patch("controller.word_controller.ruta_docx_oficio",
                      return_value=path),
            ):
                result = preparar_documento_word(
                    "IPN/CVDRD/1/2026", "Asunto", "<p>Texto inicial</p>")

            self.assertEqual(result, path)
            connection.close.assert_called_once()

            document = Document(path)
            section = document.sections[0]
            self.assertEqual(section.page_width, Inches(8.5))
            self.assertEqual(section.top_margin, Inches(290 / 72))
            self.assertEqual(
                section.header.paragraphs[0].text,
                "FOLIO: IPN/CVDRD/1/2026",
            )
            self.assertEqual(
                section.header.paragraphs[0].runs[0].font.name,
                "Arial",
            )
            self.assertEqual(
                section.header.paragraphs[0].runs[0].font.size,
                Inches(10 / 72),
            )
            self.assertEqual(
                section.header.paragraphs[0].paragraph_format.space_before,
                Inches(3.0),
            )
            self.assertIn("Texto inicial", "\n".join(
                paragraph.text for paragraph in document.paragraphs))
            self.assertIn("<wp:anchor", section.header._element.xml)
            with ZipFile(path) as archive:
                self.assertTrue(any(
                    name.startswith("word/media/") for name in archive.namelist()
                ))


if __name__ == "__main__":
    unittest.main()
