import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from docx import Document

from controller.word_controller import leer_contenido_word
from controller.word_online_controller import descargar_cambios_word_online


class WordOnlineControllerTests(unittest.TestCase):
    def test_download_preserves_rich_docx_content_for_sync(self):
        folio = 'IPN/CVDRD/1/2026'
        source = Document()
        paragraph = source.add_paragraph()
        paragraph.add_run('Bold').bold = True
        source.add_paragraph('Bullet', style='List Bullet')
        table = source.add_table(rows=1, cols=1)
        table.cell(0, 0).text = 'Table cell'
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / 'Oficio_test.docx'
            source_path = Path(temporary_directory) / 'source.docx'
            source.save(source_path)
            response = MagicMock(ok=True, content=source_path.read_bytes())

            with (
                patch('controller.word_online_controller.ruta_docx_oficio',
                      return_value=destination),
                patch('controller.word_online_controller.obtener_token_graph',
                      return_value='token'),
                patch('controller.word_online_controller._crear_carpeta_si_falta'),
                patch('controller.word_online_controller.requests.get',
                      return_value=response),
            ):
                result = descargar_cambios_word_online(
                    folio, destination, 'user@example.com')

            self.assertEqual(result, destination)
            content = leer_contenido_word(destination)

        self.assertIn('<strong>Bold</strong>', content)
        self.assertIn('<ul', content)
        self.assertIn('<table>', content)
        self.assertIn('Table cell', content)


if __name__ == '__main__':
    unittest.main()
