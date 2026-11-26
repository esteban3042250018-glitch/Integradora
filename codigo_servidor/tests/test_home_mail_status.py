import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from views.home import AppGestiónInstitucional


class HomeMailStatusTests(unittest.TestCase):
    def test_pagination_slices_records_and_clamps_out_of_range_pages(self):
        records = list(range(51))

        page, page_number, total_pages = AppGestiónInstitucional.page_slice(
            records, 1, 25)
        self.assertEqual(page, list(range(25, 50)))
        self.assertEqual((page_number, total_pages), (1, 3))

        final_page, page_number, total_pages = AppGestiónInstitucional.page_slice(
            records, 99, 25)
        self.assertEqual(final_page, [50])
        self.assertEqual((page_number, total_pages), (2, 3))

    def test_pagination_rejects_non_positive_page_size(self):
        with self.assertRaises(ValueError):
            AppGestiónInstitucional.page_slice([1], 0, 0)

    def test_opening_unread_message_marks_it_read(self):
        record = ('IPN/CVDRD/050/2026', 'RECIBIDA', 'Asunto', 'Ana',
                  'Bandeja de Entrada', 'Normal', 'A', 'Sin asignar',
                  'No leído', '2026-11-09', '', '1',
                  '2026-11-09T12:00:00Z', 'ana@example.com', 'message-id')
        app = SimpleNamespace(
            records=[record],
            _actualizar_metricas_correos=Mock(),
            filter_rows=Mock(),
        )

        AppGestiónInstitucional._mostrar_correo_leido(app, 'message-id')

        self.assertEqual(app.records[0][8], 'Recibido')
        app._actualizar_metricas_correos.assert_called_once_with()
        app.filter_rows.assert_called_once_with()

    @patch('views.home.threading.Thread')
    def test_only_unread_messages_are_marked_read(self, thread):
        unread = ('folio', 'RECIBIDA', 'Asunto', 'Ana', 'Bandeja', 'Normal',
                  'A', 'Sin asignar', 'No leído', '2026-11-09', '', '1',
                  '2026-11-09T12:00:00Z', 'ana@example.com', 'unread-id')
        read = unread[:8] + ('Recibido',) + unread[9:]
        app = SimpleNamespace(
            usuario_email='ana@example.com',
            _actualizar_estado_correo=Mock(),
        )

        AppGestiónInstitucional._marcar_correo_leido(app, unread)
        AppGestiónInstitucional._marcar_correo_leido(app, read)

        thread.assert_called_once()
        thread.return_value.start.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
