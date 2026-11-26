import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from controller.pdf_generator import generar_pdf_oficio
from controller.rich_content import html_to_pdf_flowables
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import ListFlowable, SimpleDocTemplate, Table


class PdfGeneratorTests(unittest.TestCase):
    def test_rich_content_builds_pdf_paragraphs_lists_and_tables(self):
        html = (
            '<p>Text <strong>bold</strong> and <em>italic</em></p>'
            '<p><span style="font-size:14pt;color:#008000;font-family:Arial">'
            'Styled text</span></p>'
            '<ol><li>First<ul><li>Nested</li></ul></li><li>Second</li></ol>'
            '<table><thead><tr><th>Column</th></tr></thead>'
            '<tbody><tr><td>Value</td></tr></tbody></table>'
        )
        style = ParagraphStyle(
            'TestBody', parent=getSampleStyleSheet()['Normal'])
        flowables = html_to_pdf_flowables(html, style, letter[0] - 108)

        self.assertIn('bold', flowables[0].getPlainText())
        self.assertIn('italic', flowables[0].getPlainText())
        self.assertTrue(any(isinstance(item, ListFlowable) for item in flowables))
        tables = [item for item in flowables if isinstance(item, Table)]
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].repeatRows, 1)

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = f'{temporary_directory}\\rich.pdf'
            SimpleDocTemplate(path, pagesize=letter).build(flowables)
            self.assertGreater(os.path.getsize(path), 0)

    @patch('controller.pdf_generator.cargar_configuracion_folio',
           return_value={'fuente': 'Arial', 'tamano': 10})
    @patch('controller.pdf_generator.cargar_membrete_activo',
           return_value=b'active-letterhead')
    @patch('controller.pdf_generator.dibujar_fondo_membrete')
    @patch('controller.pdf_generator.SimpleDocTemplate')
    def test_metadata_starts_below_letterhead_and_body_moves_down(
            self, simple_doc_template, draw_letterhead, load_letterhead,
            load_folio_config):
        template = simple_doc_template.return_value
        with tempfile.TemporaryDirectory() as temporary_directory:
            generar_pdf_oficio(
                f'{temporary_directory}\\oficio.pdf',
                'IPN/CVDRD/1/2026', 'Asunto', 'Cuerpo',
                'Área', 'Recepción')

        self.assertEqual(
            simple_doc_template.call_args.kwargs['topMargin'], 290)
        first_page = template.build.call_args.kwargs['onFirstPage']
        canvas = MagicMock()
        document = MagicMock()
        first_page(canvas, document)

        positions = [
            call.args[1] for call in canvas.drawString.call_args_list
        ]
        self.assertEqual(positions, [566, 551, 536, 521])
        self.assertIn(
            ('Helvetica-Bold', 10),
            [call.args for call in canvas.setFont.call_args_list],
        )
        draw_letterhead.assert_called_once_with(
            canvas, document, b'active-letterhead')
        load_letterhead.assert_called_once()
        load_folio_config.assert_called_once()


if __name__ == '__main__':
    unittest.main()
