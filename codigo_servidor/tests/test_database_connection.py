import unittest
from unittest.mock import MagicMock, patch

from controller.database_conecction import (
    Database_connection,
    _row_as_dict,
    database_cursor,
    database_transaction,
    dbapi,
)


class DatabaseConnectionTests(unittest.TestCase):
    def test_row_as_dict_preserves_selected_column_names(self):
        cursor = MagicMock()
        cursor.description = [('folio',), ('estado',)]

        self.assertEqual(
            _row_as_dict(cursor, ('IPN/CVDRD/001/2026', 'Borrador')),
            {'folio': 'IPN/CVDRD/001/2026', 'estado': 'Borrador'},
        )
        self.assertIsNone(_row_as_dict(cursor, None))

    def test_database_cursor_closes_cursor_after_use(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value

        with database_cursor(connection) as opened_cursor:
            self.assertIs(opened_cursor, cursor)

        cursor.close.assert_called_once()

    def test_database_transaction_commits_success_and_rolls_back_failure(self):
        connection = MagicMock()

        with database_transaction(connection):
            pass

        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()

        connection.reset_mock()
        with self.assertRaisesRegex(ValueError, 'abort'):
            with database_transaction(connection):
                raise ValueError('abort')

        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()

    def test_pdf_route_update_commits_matching_office_row(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = ('IPN/001',)
        database = Database_connection()

        with patch.object(database, 'get_connection', return_value=connection):
            updated = database.actualizar_ruta_oficio(
                'IPN/001', 'C:/documentos/Oficio.pdf')

        self.assertTrue(updated)
        self.assertIn(
            'UPDATE correspondencia.oficios_envio',
            cursor.execute.call_args.args[0],
        )
        connection.commit.assert_called_once()
        connection.close.assert_called_once()

    def test_draft_lookup_reads_the_route_from_office_table(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        database = Database_connection()

        with patch.object(database, 'get_connection', return_value=connection):
            database.obtener_borrador('IPN/001', 'user-1')

        query = cursor.execute.call_args.args[0]
        self.assertIn('o.ruta AS ruta_pdf', query)
        self.assertIn('LEFT JOIN correspondencia.oficios_envio', query)
        self.assertNotIn('ruta_pdf_local', query)

    def test_query_failure_raises_and_closes_connection(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.execute.side_effect = dbapi.DatabaseError('sql failure')
        database = Database_connection()

        with patch.object(database, 'get_connection', return_value=connection):
            with self.assertRaisesRegex(RuntimeError, 'PostgreSQL'):
                database.ejecutar_consulta('SELECT 1')

        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    def test_register_generated_pdf_creates_office_with_server_path(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [None, (2,), (1,), (42,)]
        database = Database_connection()

        with patch.object(database, 'get_connection', return_value=connection):
            database.registrar_pdf_generado(
                'IPN/CVDRD/001/2026',
                'Asunto de prueba',
                '/srv/gestion-institucional/oficios/Oficio_001.pdf',
                'user-id',
            )

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        office_insert = next(
            statement for statement in statements
            if 'INSERT INTO correspondencia.oficios_envio' in statement
        )
        self.assertIn('id_prioridad', office_insert)
        self.assertIn('ruta', office_insert)
        self.assertIn('estatus_actividad', office_insert)
        status_insert = next(
            statement for statement in statements
            if 'INSERT INTO correspondencia.oficios_estatus' in statement
        )
        self.assertIn('(id_oficio, id_estatus)', status_insert)
        self.assertFalse(any('correspondencia.tipos_oficios' in q for q in statements))
        office_call = next(
            call for call in cursor.execute.call_args_list
            if 'INSERT INTO correspondencia.oficios_envio' in call.args[0]
        )
        self.assertEqual(
            office_call.args[1],
            (
                'IPN/CVDRD/001/2026',
                'Asunto de prueba',
                2,
                '/srv/gestion-institucional/oficios/Oficio_001.pdf',
            ),
        )
        self.assertTrue(
            any('VALUES (%s, ' in statement for statement in statements)
        )
        self.assertFalse(any('correspondencia.borradores' in q for q in statements))
        connection.commit.assert_called_once()

    def test_register_generated_pdf_updates_route_for_existing_office(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = (42,)
        database = Database_connection()

        with patch.object(database, 'get_connection', return_value=connection):
            database.registrar_pdf_generado(
                'IPN/CVDRD/001/2026',
                'Asunto actualizado',
                '/srv/gestion-institucional/oficios/Oficio_001.pdf',
                'user-id',
            )

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        update = next(
            statement for statement in statements
            if 'UPDATE correspondencia.oficios_envio' in statement
        )
        self.assertIn('SET asunto = %s, ruta = %s', update)
        self.assertFalse(any('INSERT INTO correspondencia.prioridad' in q for q in statements))
        connection.commit.assert_called_once()

    def test_register_generated_pdf_links_the_selected_active_area(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [(42,), (3,)]
        database = Database_connection()

        with patch.object(database, 'get_connection', return_value=connection):
            database.registrar_pdf_generado(
                'IPN/CVDRD/001/2026',
                'Asunto actualizado',
                '/srv/gestion-institucional/oficios/Oficio_001.pdf',
                'user-id',
                'Dirección',
            )

        area_link = next(
            call for call in cursor.execute.call_args_list
            if 'INSERT INTO correspondencia.oficios_area_emision' in call.args[0]
        )
        self.assertEqual(area_link.args[1], (42, 3, 42, 3))
        connection.commit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
