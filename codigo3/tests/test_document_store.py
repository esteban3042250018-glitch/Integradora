import tempfile
import unittest
from pathlib import Path

from model.document_store import (
    listar_pdfs_locales, registrar_folio_local, registrar_pdf_local,
)


class DocumentStoreTests(unittest.TestCase):
    def test_pdf_history_is_stored_and_listed_locally(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            history = root / 'documentos.json'
            pdf = root / 'oficio.pdf'
            pdf.write_bytes(b'%PDF')
            folio = 'IPN/CVDRD/1/2026'
            registrar_folio_local(folio, history)

            registrar_pdf_local(folio, pdf, history)

            documents = listar_pdfs_locales(history)
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]['folio'], folio)
            self.assertEqual(documents[0]['ruta_archivo'], str(pdf.resolve()))
            self.assertTrue(documents[0]['fecha_registro'])

    def test_pdf_history_rejects_unknown_folio(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaisesRegex(ValueError, 'No se encontró el documento'):
                registrar_pdf_local('folio-inexistente', root / 'oficio.pdf',
                                    root / 'documentos.json')


if __name__ == '__main__':
    unittest.main()
