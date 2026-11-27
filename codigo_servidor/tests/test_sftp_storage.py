import base64
import hashlib
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from controller.config import load_sftp_config
from controller.sftp_storage import (
    _host_key_fingerprint_matches,
    descargar_adjunto_del_servidor,
    descargar_archivo_del_servidor,
    listar_archivos_servidor,
    upload_adjunto_oficio,
    ruta_cache_pdf_servidor,
    ruta_cache_adjunto_servidor,
    upload_file_to_server,
)


class FakeHostKey:
    def asbytes(self):
        return b'test SFTP host key'

    def get_fingerprint(self):
        return hashlib.md5(self.asbytes()).digest()


class SftpStorageTests(unittest.TestCase):
    def test_sftp_config_reads_server_settings(self):
        values = {
            'SFTP_HOST': ' sftp.example.org ',
            'SFTP_PORT': '2222',
            'SFTP_USER': ' user ',
            'SFTP_PASSWORD': 'password',
            'SFTP_REMOTE_DIR': '/srv/oficios',
            'SFTP_HOST_KEY_FINGERPRINT': 'SHA256:fingerprint',
        }

        def read_setting(name, default=None, cast=None):
            value = values.get(name, default)
            return cast(value) if cast and value is not None else value

        self.assertEqual(
            load_sftp_config(read_setting),
            {
                'host': 'sftp.example.org',
                'port': 2222,
                'username': 'user',
                'password': 'password',
                'remote_dir': '/srv/oficios',
                'host_key_fingerprint': 'SHA256:fingerprint',
            },
        )

    def test_host_key_fingerprint_supports_sha256_and_md5(self):
        host_key = FakeHostKey()
        sha256_fingerprint = base64.b64encode(
            hashlib.sha256(host_key.asbytes()).digest()
        ).decode('ascii').rstrip('=')
        md5_fingerprint = ':'.join(
            f'{value:02x}' for value in host_key.get_fingerprint()
        )

        self.assertTrue(
            _host_key_fingerprint_matches(
                host_key, f'SHA256:{sha256_fingerprint}')
        )
        self.assertTrue(_host_key_fingerprint_matches(host_key, md5_fingerprint))
        self.assertFalse(
            _host_key_fingerprint_matches(host_key, 'SHA256:incorrect')
        )

    def test_upload_file_sends_pdf_to_configured_remote_folder(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_file = Path(temporary_directory) / 'Oficio_123.pdf'
            local_file.write_bytes(b'%PDF')
            host_key = FakeHostKey()
            fingerprint = base64.b64encode(
                hashlib.sha256(host_key.asbytes()).digest()
            ).decode('ascii').rstrip('=')
            transport = MagicMock()
            transport.get_remote_server_key.return_value = host_key
            transport.is_authenticated.return_value = True
            sftp = MagicMock()
            sftp.stat.return_value = SimpleNamespace(st_mode=stat.S_IFDIR)
            sftp.put.return_value = SimpleNamespace(st_size=4)
            settings = {
                'host': 'sftp.example.org',
                'port': 22,
                'username': 'user',
                'password': 'password',
                'remote_dir': '/srv/oficios',
                'host_key_fingerprint': f'SHA256:{fingerprint}',
            }

            with patch(
                'controller.sftp_storage.paramiko.Transport',
                return_value=transport,
            ), patch(
                'controller.sftp_storage.paramiko.SFTPClient.from_transport',
                return_value=sftp,
            ):
                remote_path = upload_file_to_server(local_file, settings)

        self.assertEqual(remote_path, '/srv/oficios/Oficio_123.pdf')
        sftp.put.assert_called_once_with(
            str(local_file), remote_path, confirm=True)
        sftp.close.assert_called_once()
        transport.close.assert_called_once()

    def test_upload_file_rejects_unverified_host_key(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_file = Path(temporary_directory) / 'Oficio_123.pdf'
            local_file.write_bytes(b'%PDF')
            transport = MagicMock()
            transport.get_remote_server_key.return_value = FakeHostKey()
            settings = {
                'host': 'sftp.example.org',
                'port': 22,
                'username': 'user',
                'password': 'password',
                'remote_dir': '/srv/oficios',
                'host_key_fingerprint': 'SHA256:incorrect',
            }

            with patch(
                'controller.sftp_storage.paramiko.Transport',
                return_value=transport,
            ), self.assertRaisesRegex(RuntimeError, 'huella'):
                upload_file_to_server(local_file, settings)

            transport.auth_password.assert_not_called()
            transport.close.assert_called_once()

    def test_office_attachment_upload_uses_unique_name_containing_folio(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_file = Path(temporary_directory) / 'aprobacion.pdf'
            local_file.write_bytes(b'%PDF')
            uploaded = {}

            def capture_upload(staged_file, config):
                staged_file = Path(staged_file)
                uploaded['name'] = staged_file.name
                uploaded['content'] = staged_file.read_bytes()
                uploaded['config'] = config
                return f'/srv/oficios/{staged_file.name}'

            with patch(
                'controller.sftp_storage.upload_file_to_server',
                side_effect=capture_upload,
            ):
                remote_path = upload_adjunto_oficio(
                    local_file, 'IPN/CVDRD/001/2026', 'Aprobado')

            self.assertEqual(local_file.read_bytes(), b'%PDF')

        self.assertRegex(
            uploaded['name'],
            r'^Aprobado_IPN_CVDRD_001_2026_[0-9a-f]{32}\.pdf$',
        )
        self.assertEqual(uploaded['content'], b'%PDF')
        self.assertTrue(remote_path.endswith(uploaded['name']))

    def test_office_attachment_upload_rejects_unapproved_extensions(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_file = Path(temporary_directory) / 'script.exe'
            local_file.write_bytes(b'not an attachment')

            with patch(
                'controller.sftp_storage.upload_file_to_server',
            ) as upload:
                with self.assertRaisesRegex(ValueError, 'archivo debe ser'):
                    upload_adjunto_oficio(local_file, 'IPN/001', 'Acuse')

            upload.assert_not_called()

    def test_download_file_fetches_server_pdf_to_local_cache(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_file = Path(temporary_directory) / 'Oficio_123.pdf'
            host_key = FakeHostKey()
            fingerprint = base64.b64encode(
                hashlib.sha256(host_key.asbytes()).digest()
            ).decode('ascii').rstrip('=')
            transport = MagicMock()
            transport.get_remote_server_key.return_value = host_key
            transport.is_authenticated.return_value = True
            sftp = MagicMock()
            sftp.stat.return_value = SimpleNamespace(
                st_mode=stat.S_IFREG, st_size=4)
            sftp.get.side_effect = lambda _remote, local: Path(local).write_bytes(b'%PDF')
            settings = {
                'host': 'sftp.example.org',
                'port': 22,
                'username': 'user',
                'password': 'password',
                'remote_dir': '/srv/oficios',
                'host_key_fingerprint': f'SHA256:{fingerprint}',
            }

            with patch(
                'controller.sftp_storage.paramiko.Transport',
                return_value=transport,
            ), patch(
                'controller.sftp_storage.paramiko.SFTPClient.from_transport',
                return_value=sftp,
            ):
                result = descargar_archivo_del_servidor(
                    '/srv/oficios/Oficio_123.pdf', local_file, settings)

            self.assertEqual(result, local_file)
            self.assertEqual(local_file.read_bytes(), b'%PDF')
            sftp.get.assert_called_once()
            sftp.close.assert_called_once()
            transport.close.assert_called_once()

    def test_download_office_attachment_supports_word_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_file = Path(temporary_directory) / 'Aprobado_001.docx'
            host_key = FakeHostKey()
            fingerprint = base64.b64encode(
                hashlib.sha256(host_key.asbytes()).digest()
            ).decode('ascii').rstrip('=')
            transport = MagicMock()
            transport.get_remote_server_key.return_value = host_key
            transport.is_authenticated.return_value = True
            sftp = MagicMock()
            sftp.stat.return_value = SimpleNamespace(
                st_mode=stat.S_IFREG, st_size=4)
            sftp.get.side_effect = (
                lambda _remote, local: Path(local).write_bytes(b'DOCX')
            )
            settings = {
                'host': 'sftp.example.org',
                'port': 22,
                'username': 'user',
                'password': 'password',
                'remote_dir': '/srv/oficios',
                'host_key_fingerprint': f'SHA256:{fingerprint}',
            }

            with patch(
                'controller.sftp_storage.paramiko.Transport',
                return_value=transport,
            ), patch(
                'controller.sftp_storage.paramiko.SFTPClient.from_transport',
                return_value=sftp,
            ):
                result = descargar_adjunto_del_servidor(
                    '/srv/oficios/Aprobado_001.docx', local_file, settings)

            self.assertEqual(result, local_file)
            self.assertEqual(local_file.read_bytes(), b'DOCX')
            sftp.get.assert_called_once()

    def test_download_file_rejects_path_outside_configured_folder(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            host_key = FakeHostKey()
            fingerprint = base64.b64encode(
                hashlib.sha256(host_key.asbytes()).digest()
            ).decode('ascii').rstrip('=')
            transport = MagicMock()
            transport.get_remote_server_key.return_value = host_key
            transport.is_authenticated.return_value = True
            sftp = MagicMock()
            settings = {
                'host': 'sftp.example.org',
                'port': 22,
                'username': 'user',
                'password': 'password',
                'remote_dir': '/srv/oficios',
                'host_key_fingerprint': f'SHA256:{fingerprint}',
            }

            with patch(
                'controller.sftp_storage.paramiko.Transport',
                return_value=transport,
            ), patch(
                'controller.sftp_storage.paramiko.SFTPClient.from_transport',
                return_value=sftp,
            ), self.assertRaisesRegex(ValueError, 'SFTP_REMOTE_DIR'):
                descargar_archivo_del_servidor(
                    '/other/Oficio_123.pdf',
                    Path(temporary_directory) / 'Oficio_123.pdf',
                    settings,
                )

            sftp.get.assert_not_called()

    def test_list_server_files_uses_sftp_directory_not_local_history(self):
        host_key = FakeHostKey()
        fingerprint = base64.b64encode(
            hashlib.sha256(host_key.asbytes()).digest()
        ).decode('ascii').rstrip('=')
        transport = MagicMock()
        transport.get_remote_server_key.return_value = host_key
        transport.is_authenticated.return_value = True
        sftp = MagicMock()
        sftp.stat.return_value = SimpleNamespace(st_mode=stat.S_IFDIR)
        sftp.listdir_attr.return_value = [
            SimpleNamespace(
                filename='Oficio_001.pdf',
                st_mode=stat.S_IFREG,
                st_mtime=200,
            ),
            SimpleNamespace(
                filename='Oficio_002.PDF',
                st_mode=stat.S_IFREG,
                st_mtime=100,
            ),
            SimpleNamespace(
                filename='subcarpeta',
                st_mode=stat.S_IFDIR,
                st_mtime=300,
            ),
            SimpleNamespace(
                filename='notas.txt',
                st_mode=stat.S_IFREG,
                st_mtime=400,
            ),
        ]
        settings = {
            'host': 'sftp.example.org',
            'port': 22,
            'username': 'user',
            'password': 'password',
            'remote_dir': '/srv/oficios',
            'host_key_fingerprint': f'SHA256:{fingerprint}',
        }

        with patch(
            'controller.sftp_storage.paramiko.Transport',
            return_value=transport,
        ), patch(
            'controller.sftp_storage.paramiko.SFTPClient.from_transport',
            return_value=sftp,
        ):
            files = listar_archivos_servidor(settings)

        self.assertEqual(
            [file['nombre'] for file in files],
            ['Oficio_001.pdf', 'Oficio_002.PDF'],
        )
        self.assertEqual(files[0]['ruta'], '/srv/oficios/Oficio_001.pdf')
        sftp.listdir_attr.assert_called_once_with('/srv/oficios')
        sftp.close.assert_called_once()
        transport.close.assert_called_once()

    def test_server_pdf_cache_uses_safe_server_filename(self):
        with patch(
            'controller.sftp_storage.user_data_dir',
            return_value=Path('C:/user-data'),
        ):
            cached = ruta_cache_pdf_servidor(
                'Oficio_IPN_CVDRD_001.pdf')

        self.assertEqual(
            cached,
            Path('C:/user-data/pdf_servidor/Oficio_IPN_CVDRD_001.pdf'),
        )

    def test_server_attachment_cache_preserves_supported_extension(self):
        with patch(
            'controller.sftp_storage.user_data_dir',
            return_value=Path('C:/user-data'),
        ):
            cached = ruta_cache_adjunto_servidor('Aprobado_001.docx')

        self.assertEqual(
            cached,
            Path('C:/user-data/adjuntos_servidor/Aprobado_001.docx'),
        )


if __name__ == '__main__':
    unittest.main()
