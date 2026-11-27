import unittest
from unittest.mock import MagicMock, patch

from model.areas_usuarios import (
    agregar_area,
    listar_areas,
    usuario_puede_administrar,
)


class AreasUsuariosTests(unittest.TestCase):
    @patch('model.areas_usuarios.Database_connection')
    @patch('model.areas_usuarios.database_cursor')
    def test_area_list_returns_active_database_catalog(self, database_cursor, database):
        connection = database.return_value.get_connection.return_value
        cursor = MagicMock()
        database_cursor.return_value.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            (7, 'Departamento X'),
            (1, 'Dirección Y'),
        ]

        self.assertEqual(
            listar_areas(),
            [(7, 'Departamento X'), (1, 'Dirección Y')],
        )
        query = cursor.execute.call_args.args[0]
        self.assertIn('FROM correspondencia.areas', query)
        self.assertIn('WHERE activo = TRUE', query)
        self.assertNotIn('IN (', query)
        self.assertEqual(len(cursor.execute.call_args.args), 1)
        connection.close.assert_called_once()

    @patch('model.areas_usuarios.Database_connection')
    @patch('model.areas_usuarios.database_cursor')
    @patch('model.areas_usuarios.database_transaction')
    def test_new_area_is_saved_in_database_catalog(
        self, transaction, database_cursor, database,
    ):
        connection = database.return_value.get_connection.return_value
        cursor = MagicMock()
        database_cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = (42,)

        self.assertEqual(agregar_area('Área agregada desde BD'), 42)
        query = cursor.execute.call_args.args[0]
        self.assertIn('INSERT INTO correspondencia.areas', query)
        self.assertEqual(
            cursor.execute.call_args.args[1],
            ('Área agregada desde BD',),
        )
        transaction.assert_called_once_with(connection)
        connection.close.assert_called_once()

    @patch('model.areas_usuarios.Database_connection')
    def test_empty_area_name_is_rejected_without_database_access(self, database):
        with self.assertRaises(ValueError):
            agregar_area('  ')

        database.assert_not_called()

    @patch('model.areas_usuarios.Database_connection')
    @patch('model.areas_usuarios.database_cursor')
    def test_administration_permission_is_read_from_database(
        self, database_cursor, database,
    ):
        connection = database.return_value.get_connection.return_value
        cursor = MagicMock()
        database_cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = (True,)

        self.assertTrue(usuario_puede_administrar('Admin@Example.org'))
        query, params = cursor.execute.call_args.args
        self.assertIn('a.puede_administrar = TRUE', query)
        self.assertNotIn('a.nombre', query)
        self.assertEqual(params, ('admin@example.org',))
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
