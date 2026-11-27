import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from controller.pdf_publication import publicar_pdf_oficio


class PdfPublicationTests(unittest.TestCase):
    def test_publication_generates_uploads_and_records_pdf_path(self):
        events = []
        registro = {
            'asunto': 'Asunto',
            'cuerpo': '<p>Texto</p>',
            'area_emisora': 'Dirección',
            'recepcion': 'Destinatario',
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_path = Path(temporary_directory) / 'Oficio_001.pdf'
            database = MagicMock()
            database.registrar_pdf_generado.side_effect = (
                lambda *args: events.append(('database', args))
            )

            with patch(
                'controller.pdf_publication.ruta_pdf_oficio',
                return_value=local_path,
            ), patch(
                'controller.pdf_publication.generar_pdf_oficio',
                side_effect=lambda *args: events.append(('generate', args)),
            ), patch(
                'controller.pdf_publication.upload_file_to_server',
                side_effect=lambda path: events.append(('upload', path))
                or '/srv/oficios/Oficio_001.pdf',
            ), patch(
                'controller.pdf_publication.Database_connection',
                return_value=database,
            ):
                remote_path = publicar_pdf_oficio(
                    'IPN/CVDRD/001/2026', registro, 'user-id')

        self.assertEqual(remote_path, '/srv/oficios/Oficio_001.pdf')
        self.assertEqual(
            [event[0] for event in events],
            ['generate', 'upload', 'database'],
        )
        self.assertEqual(
            events[2][1],
            (
                'IPN/CVDRD/001/2026',
                'Asunto',
                '/srv/oficios/Oficio_001.pdf',
                'user-id',
                'Dirección',
            ),
        )


if __name__ == '__main__':
    unittest.main()
