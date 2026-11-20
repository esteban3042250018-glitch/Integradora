import unittest
from unittest.mock import MagicMock, patch

from controller.database_conecction import Database_connection


class FolioReservationTests(unittest.TestCase):
    def test_reservation_uses_shared_transaction_lock_and_counter(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(12,), (15,)]

        with patch.object(Database_connection, 'get_connection',
                          return_value=connection):
            folio = Database_connection().reservar_folio(14)

        year = folio.rsplit('/', 1)[1]
        self.assertEqual(folio, f'IPN/CVDRD/016/{year}')
        calls = cursor.execute.call_args_list
        self.assertIn('pg_advisory_xact_lock', calls[0].args[0])
        self.assertEqual(calls[0].args[1], (18673, int(year)))
        self.assertIn('correspondencia.oficios_envio', calls[1].args[0])
        self.assertIn('correspondencia.oficios_recibido', calls[1].args[0])
        self.assertIn('correspondencia.borradores', calls[1].args[0])
        self.assertIn('INSERT INTO correspondencia.folios_anuales',
                      calls[3].args[0])
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
