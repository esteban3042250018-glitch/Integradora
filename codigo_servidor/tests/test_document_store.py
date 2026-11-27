import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from database.migrar_documentos_json import migrar_documentos_json
from model.document_store import obtener_documento


class DocumentStoreTests(unittest.TestCase):
    @patch('model.document_store.Database_connection')
    def test_document_lookup_is_scoped_to_the_authenticated_user(self, database):
        record = {'folio': 'IPN/001', 'estado': 'Creado'}
        database.return_value.obtener_borrador.return_value = record

        self.assertIs(obtener_documento('IPN/001', 'user-1'), record)
        database.return_value.obtener_borrador.assert_called_once_with(
            'IPN/001', 'user-1')

    def test_document_lookup_requires_the_authenticated_user(self):
        with self.assertRaisesRegex(ValueError, 'cuenta autenticada'):
            obtener_documento('IPN/001', '')

    def test_legacy_pdf_paths_import_only_when_file_and_folio_exist(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            existing_pdf = root / 'oficio.pdf'
            existing_pdf.write_bytes(b'%PDF')
            missing_pdf = root / 'missing.pdf'
            history = root / 'documentos.json'
            history.write_text(json.dumps([
                {'folio': 'IPN/001', 'ruta_pdf': str(existing_pdf)},
                {'folio': 'IPN/002', 'ruta_pdf': str(existing_pdf)},
                {'folio': 'IPN/003', 'ruta_pdf': str(missing_pdf)},
                {'folio': 'IPN/004'},
            ]), encoding='utf-8')
            database = MagicMock()
            database.actualizar_ruta_oficio.side_effect = [True, False]

            resultado = migrar_documentos_json(history, database)

        self.assertEqual(resultado, {
            'importados': 1,
            'sin_ruta': 1,
            'archivo_ausente': 1,
            'folio_no_encontrado': 1,
        })
        self.assertEqual(database.actualizar_ruta_oficio.call_count, 2)

    def test_legacy_import_rejects_malformed_json_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            history = Path(temporary_directory) / 'documentos.json'
            history.write_text('{bad json', encoding='utf-8')
            database = MagicMock()

            with self.assertRaisesRegex(ValueError, 'está dañado'):
                migrar_documentos_json(history, database)

        database.actualizar_ruta_oficio.assert_not_called()


if __name__ == '__main__':
    unittest.main()
