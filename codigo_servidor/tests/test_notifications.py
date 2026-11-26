import unittest
from unittest.mock import MagicMock, patch

from controller.database_conecction import Database_connection


class NotificationDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.database = Database_connection()
        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.connection.cursor.return_value = self.cursor

    @patch.object(Database_connection, 'get_connection')
    def test_counts_notifications_unread_for_account(self, get_connection):
        get_connection.return_value = self.connection
        self.cursor.fetchone.return_value = (3,)

        result = self.database.contar_notificaciones_no_leidas('tenant:user')

        self.assertEqual(result, 3)
        self.cursor.execute.assert_called_once()
        self.assertIn('notificaciones_leidas', self.cursor.execute.call_args.args[0])

    @patch.object(Database_connection, 'get_connection')
    def test_marks_only_requested_notifications_read(self, get_connection):
        get_connection.return_value = self.connection

        self.database.marcar_notificaciones_leidas(
            'tenant:user', [4, 9])

        self.cursor.execute.assert_called_once()
        self.assertEqual(
            self.cursor.execute.call_args.args[1], ('tenant:user', [4, 9]))

    @patch.object(Database_connection, 'get_connection')
    def test_pdf_notification_is_idempotent(self, get_connection):
        get_connection.return_value = self.connection

        self.database.registrar_notificacion_pdf(
            'IPN/CVDRD/059/2026', 'tenant:user')

        sql, params = self.cursor.execute.call_args.args
        self.assertIn('ON CONFLICT (folio, tipo) DO NOTHING', sql)
        self.assertEqual(params[0], 'IPN/CVDRD/059/2026')
        self.assertEqual(params[2], 'tenant:user')


if __name__ == '__main__':
    unittest.main()
