import unittest
from unittest.mock import MagicMock, patch

from model.administracion import desactivar_membrete, obtener_membrete_activo
from controller.pdf_generator import cargar_membrete_activo


class AdministracionTests(unittest.TestCase):
    @patch('model.administracion.obtener_conexion')
    def test_configuration_update_commits_and_closes_connection_once(
            self, get_connection):
        connection = MagicMock()
        connection.close.side_effect = [
            None,
            RuntimeError('connection is closed'),
        ]
        connection.__exit__.side_effect = lambda *_args: connection.close()
        connection.cursor.return_value.rowcount = 1
        get_connection.return_value = connection

        self.assertEqual(desactivar_membrete(), 1)

        connection.commit.assert_called_once()
        connection.close.assert_called_once()

    @patch('model.administracion.obtener_conexion')
    def test_obtener_membrete_activo_returns_database_image(self, get_connection):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchall.return_value = [
            (7, 'membrete.png', 'image/png', b'image-bytes', None),
        ]
        get_connection.return_value = connection

        result = obtener_membrete_activo()

        self.assertEqual(
            result,
            (7, 'membrete.png', 'image/png', b'image-bytes', None),
        )
        connection.close.assert_called_once()

    @patch('model.administracion.obtener_conexion')
    def test_obtener_membrete_activo_reports_missing_image(self, get_connection):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchall.return_value = []
        get_connection.return_value = connection

        with self.assertRaisesRegex(RuntimeError, 'No hay un membrete activo'):
            obtener_membrete_activo()

        connection.close.assert_called_once()


class PdfLetterheadTests(unittest.TestCase):
    @patch('controller.pdf_generator.obtener_imagen_membrete')
    @patch('controller.pdf_generator.obtener_conexion')
    def test_pdf_load_uses_and_closes_database_connection(
            self, get_connection, get_letterhead):
        connection = MagicMock()
        get_connection.return_value = connection
        get_letterhead.return_value = ('membrete.png', 'image/png', b'bytes')

        self.assertEqual(cargar_membrete_activo(), b'bytes')

        get_letterhead.assert_called_once_with(connection)
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
