import unittest
from unittest.mock import MagicMock, patch

from controller.database_conecction import Database_connection


class FolioReservationTests(unittest.TestCase):
    @patch('model.folio_format.reserve_next_folio',
           return_value='IPN/CVDRD/016/2026')
    def test_reservation_uses_shared_transaction_lock_and_personalization(
            self, reserve_next):
        connection = MagicMock()
        cursor = connection.cursor.return_value

        with patch.object(Database_connection, 'get_connection',
                          return_value=connection):
            folio = Database_connection().reservar_folio()

        self.assertEqual(folio, 'IPN/CVDRD/016/2026')
        calls = cursor.execute.call_args_list
        self.assertIn('pg_advisory_xact_lock', calls[0].args[0])
        self.assertEqual(calls[0].args[1], (18673, 2026))
        reserve_next.assert_called_once_with(cursor)
        connection.close.assert_called_once()

    @patch('model.folio_format.reserve_next_folio',
           return_value='IPN/CVDRD/016/2026')
    def test_reserving_draft_commits_and_closes_connection_once(
            self, reserve_next):
        connection = MagicMock()
        connection.close.side_effect = [
            None,
            RuntimeError('connection is closed'),
        ]
        connection.__exit__.side_effect = lambda *_args: connection.close()
        cursor = connection.cursor.return_value

        with patch.object(Database_connection, 'get_connection',
                          return_value=connection):
            folio = Database_connection().reservar_borrador(
                'tenant:user', 'Test User')

        self.assertEqual(folio, 'IPN/CVDRD/016/2026')
        reserve_next.assert_called_once_with(cursor)
        connection.commit.assert_called_once()
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
