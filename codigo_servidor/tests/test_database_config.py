import os
import ssl
import unittest
from unittest.mock import patch

from controller.config import load_db_config
from controller.database_conecction import Database_connection, dbapi


class DatabaseConfigTests(unittest.TestCase):
    @staticmethod
    def reader(settings):
        def read_setting(name, default=None, cast=None):
            value = settings.get(name, default)
            return cast(value) if cast and value is not None else value

        return read_setting

    def test_loads_remote_connection_and_tls_settings_from_environment(self):
        settings = {
            'POSTGRES_HOST': 'postgres.example.net',
            'POSTGRES_PORT': '6432',
            'POSTGRES_DB': 'institucional',
            'POSTGRES_USER': 'app_user',
            'POSTGRES_PASSWORD': 'not-a-real-password',
            'POSTGRES_SSLMODE': 'verify-full',
            'POSTGRES_SSLROOTCERT': 'C:\\certs\\ca.crt',
            'POSTGRES_SSLCERT': 'C:\\certs\\client.crt',
            'POSTGRES_SSLKEY': 'C:\\certs\\client.key',
        }

        with patch.dict(os.environ, settings):
            config = load_db_config()

        self.assertEqual(config['host'], 'postgres.example.net')
        self.assertEqual(config['port'], 6432)
        self.assertEqual(config['database'], 'institucional')
        self.assertEqual(config['user'], 'app_user')
        self.assertEqual(config['password'], 'not-a-real-password')
        self.assertEqual(config['sslmode'], 'verify-full')
        self.assertEqual(config['sslrootcert'], 'C:\\certs\\ca.crt')
        self.assertEqual(config['sslcert'], 'C:\\certs\\client.crt')
        self.assertEqual(config['sslkey'], 'C:\\certs\\client.key')

    def test_does_not_assume_localhost_or_add_empty_tls_options(self):
        config = load_db_config(self.reader({}))

        self.assertEqual(config['host'], '')
        self.assertNotIn('sslmode', config)
        self.assertNotIn('sslrootcert', config)

    @patch('controller.database_conecction.dbapi.connect')
    def test_connection_requires_explicit_server_host(self, connect):
        database = Database_connection()
        database.config = {'host': '', 'port': 5432, 'database': 'db'}

        with self.assertRaisesRegex(ConnectionError, 'POSTGRES_HOST'):
            database.get_connection()

        connect.assert_not_called()

    def test_ssl_modes_map_to_pg8000_contexts(self):
        from controller.database_conecction import _build_ssl_context

        self.assertIsNone(_build_ssl_context({'sslmode': 'prefer'}))
        self.assertIs(_build_ssl_context({'sslmode': 'disable'}), False)
        required = _build_ssl_context({'sslmode': 'require'})
        self.assertEqual(required.verify_mode, ssl.CERT_NONE)
        verified = _build_ssl_context({'sslmode': 'verify-full'})
        self.assertTrue(verified.check_hostname)
        self.assertEqual(verified.verify_mode, ssl.CERT_REQUIRED)

    def test_pg8000_connection_receives_dbapi_settings_and_timeout(self):
        database = Database_connection()
        database.config = {
            'host': 'postgres.example.net',
            'port': 6432,
            'database': 'institucional',
            'user': 'app_user',
            'password': 'password',
            'sslmode': 'require',
        }

        with patch.object(dbapi, 'connect', return_value=object()) as connect:
            database.get_connection()

        arguments = connect.call_args.kwargs
        self.assertEqual(arguments['database'], 'institucional')
        self.assertEqual(arguments['timeout'], 8)
        self.assertEqual(
            arguments['ssl_context'].verify_mode, ssl.CERT_NONE)


if __name__ == '__main__':
    unittest.main()
