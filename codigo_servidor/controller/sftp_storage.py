"""Transfer generated files to the configured server using SFTP."""
import base64
from contextlib import contextmanager
from datetime import datetime
import hashlib
import hmac
import posixpath
import re
import shutil
import stat
import tempfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

import paramiko

from controller.app_paths import user_data_dir
from controller.config import load_sftp_config

EXTENSIONES_ADJUNTOS = frozenset({
    '.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.webp',
})


def _host_key_fingerprint_matches(host_key, expected):
    expected = expected.strip()
    if expected.lower().startswith('sha256:'):
        actual = base64.b64encode(
            hashlib.sha256(host_key.asbytes()).digest()
        ).decode('ascii').rstrip('=')
        return hmac.compare_digest(
            actual, expected.split(':', 1)[1].rstrip('=')
        )

    if re.fullmatch(r'(?:[0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}', expected):
        actual = ':'.join(
            f'{value:02x}' for value in host_key.get_fingerprint()
        )
        return hmac.compare_digest(actual.lower(), expected.lower())

    return False


@contextmanager
def _sftp_session(config=None):
    settings = config if config is not None else load_sftp_config()
    host = str(settings.get('host') or '').strip()
    username = str(settings.get('username') or '').strip()
    password = settings.get('password') or ''
    remote_dir = str(settings.get('remote_dir') or '').strip()
    fingerprint = str(settings.get('host_key_fingerprint') or '').strip()
    try:
        port = int(settings.get('port') or 22)
    except (TypeError, ValueError) as error:
        raise ValueError('SFTP_PORT debe ser un número válido.') from error

    if not host or not username or not password or not remote_dir:
        raise RuntimeError(
            'Configura SFTP_HOST, SFTP_USER, SFTP_PASSWORD y '
            'SFTP_REMOTE_DIR en .env.'
        )
    if not fingerprint:
        raise RuntimeError(
            'Configura SFTP_HOST_KEY_FINGERPRINT en .env para validar el servidor.'
        )

    remote_directory = PurePosixPath(remote_dir)
    if not remote_directory.is_absolute() or '..' in remote_directory.parts:
        raise ValueError('SFTP_REMOTE_DIR debe ser una ruta absoluta del servidor.')

    transport = None
    sftp = None
    try:
        transport = paramiko.Transport((host, port))
        transport.start_client(timeout=20)
        host_key = transport.get_remote_server_key()
        if not _host_key_fingerprint_matches(host_key, fingerprint):
            raise RuntimeError(
                'La huella del servidor SFTP no coincide con '
                'SFTP_HOST_KEY_FINGERPRINT.'
            )
        transport.auth_password(username=username, password=password)
        if not transport.is_authenticated():
            raise RuntimeError('El servidor SFTP rechazó la autenticación.')

        sftp = paramiko.SFTPClient.from_transport(transport)
        yield sftp, remote_directory
    except RuntimeError:
        raise
    except (OSError, paramiko.SSHException) as error:
        raise RuntimeError(
            f'No se pudo conectar con el servidor SFTP: {error}'
        ) from error
    finally:
        if sftp is not None:
            sftp.close()
        if transport is not None:
            transport.close()


def upload_file_to_server(local_path, config=None):
    """Upload a file to SFTP and return its absolute remote path."""
    source = Path(local_path).expanduser()
    if not source.is_file():
        raise ValueError(f'No se encontró el archivo que se va a transferir: {source}')
    with _sftp_session(config) as (sftp, remote_directory):
        directory_attributes = sftp.stat(str(remote_directory))
        if not stat.S_ISDIR(directory_attributes.st_mode):
            raise RuntimeError('SFTP_REMOTE_DIR no es una carpeta del servidor.')
        remote_path = posixpath.join(str(remote_directory), source.name)
        uploaded = sftp.put(str(source), remote_path, confirm=True)
        if uploaded.st_size != source.stat().st_size:
            raise RuntimeError(
                'El archivo transferido al servidor no coincide en tamaño.'
            )
        return remote_path


def upload_adjunto_oficio(local_path, folio, tipo, config=None):
    """Sube un adjunto con nombre único y asociado al folio indicado."""
    source = Path(local_path).expanduser()
    if not source.is_file():
        raise ValueError(f'No se encontró el archivo seleccionado: {source}')
    extension = source.suffix.lower()
    if extension not in EXTENSIONES_ADJUNTOS:
        raise ValueError(
            'El archivo debe ser PDF, DOC, DOCX o una imagen PNG, JPG, JPEG o WEBP.'
        )
    prefijos = {'Aprobado': 'Aprobado', 'Acuse': 'Acuse'}
    if tipo not in prefijos:
        raise ValueError('El tipo de adjunto no es válido.')
    folio_seguro = re.sub(r'[^A-Za-z0-9._-]+', '_', str(folio)).strip('._-')
    if not folio_seguro:
        raise ValueError('El folio del oficio no es válido.')

    nombre = (
        f'{prefijos[tipo]}_{folio_seguro}_{uuid4().hex}{extension}'
    )
    with tempfile.TemporaryDirectory(prefix='adjunto_oficio_') as directory:
        archivo_temporal = Path(directory) / nombre
        shutil.copy2(source, archivo_temporal)
        return upload_file_to_server(archivo_temporal, config)


def listar_archivos_servidor(config=None):
    """List PDFs directly from the configured server folder."""
    with _sftp_session(config) as (sftp, remote_directory):
        directory_attributes = sftp.stat(str(remote_directory))
        if not stat.S_ISDIR(directory_attributes.st_mode):
            raise RuntimeError('SFTP_REMOTE_DIR no es una carpeta del servidor.')

        archivos = []
        for item in sftp.listdir_attr(str(remote_directory)):
            if not item.filename.lower().endswith('.pdf'):
                continue
            if stat.S_ISDIR(item.st_mode):
                continue
            archivos.append({
                'nombre': item.filename,
                'ruta': posixpath.join(str(remote_directory), item.filename),
                'fecha': (
                    datetime.fromtimestamp(item.st_mtime)
                    if item.st_mtime is not None else None
                ),
            })
        return sorted(
            archivos,
            key=lambda archivo: archivo['fecha'] or datetime.min,
            reverse=True,
        )


def descargar_archivo_del_servidor(remote_path, local_path, config=None):
    """Download a PDF from the configured SFTP folder to a local cache."""
    remote_file = PurePosixPath(str(remote_path))
    local_file = Path(local_path).expanduser()
    temporary = None

    with _sftp_session(config) as (sftp, remote_directory):
        if (
            not remote_file.is_absolute()
            or '..' in remote_file.parts
            or remote_file.parent != remote_directory
            or remote_file.suffix.lower() != '.pdf'
        ):
            raise ValueError(
                'La ruta registrada no corresponde a un PDF de '
                'SFTP_REMOTE_DIR.'
            )

        local_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(
                dir=local_file.parent, suffix='.pdf.part', delete=False
            ) as file:
                temporary = Path(file.name)

            remote_attributes = sftp.stat(str(remote_file))
            if stat.S_ISDIR(remote_attributes.st_mode):
                raise ValueError('La ruta SFTP apunta a una carpeta, no a un PDF.')
            sftp.get(str(remote_file), str(temporary))
            if temporary.stat().st_size != remote_attributes.st_size:
                raise RuntimeError(
                    'El PDF descargado del servidor no coincide en tamaño.'
                )
            temporary.replace(local_file)
            return local_file
        except (OSError, paramiko.SSHException) as error:
            raise RuntimeError(
                f'No se pudo descargar el PDF del servidor: {error}'
            ) from error
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def ruta_cache_pdf_servidor(nombre_archivo):
    nombre = PurePosixPath(str(nombre_archivo)).name
    nombre_seguro = re.sub(r'[\\/:*?"<>|]', '_', nombre)
    if not nombre_seguro.lower().endswith('.pdf'):
        raise ValueError('El archivo del servidor no es un PDF.')
    return user_data_dir() / 'pdf_servidor' / nombre_seguro


def descargar_adjunto_del_servidor(remote_path, local_path, config=None):
    """Descarga un adjunto del directorio SFTP configurado de forma segura."""
    remote_file = PurePosixPath(str(remote_path))
    local_file = Path(local_path).expanduser()

    with _sftp_session(config) as (sftp, remote_directory):
        if (
            not remote_file.is_absolute()
            or '..' in remote_file.parts
            or remote_file.parent != remote_directory
            or remote_file.suffix.lower() not in EXTENSIONES_ADJUNTOS
        ):
            raise ValueError(
                'La ruta registrada no corresponde a un adjunto permitido '
                'de SFTP_REMOTE_DIR.'
            )

        local_file.parent.mkdir(parents=True, exist_ok=True)
        temporal = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=local_file.parent,
                suffix=f'{remote_file.suffix}.part',
                delete=False,
            ) as archivo:
                temporal = Path(archivo.name)

            atributos = sftp.stat(str(remote_file))
            if stat.S_ISDIR(atributos.st_mode):
                raise ValueError('La ruta SFTP apunta a una carpeta, no a un archivo.')
            sftp.get(str(remote_file), str(temporal))
            if temporal.stat().st_size != atributos.st_size:
                raise RuntimeError(
                    'El adjunto descargado no coincide en tamaño con el servidor.'
                )
            temporal.replace(local_file)
            return local_file
        except (OSError, paramiko.SSHException) as error:
            raise RuntimeError(
                f'No se pudo descargar el adjunto del servidor: {error}'
            ) from error
        finally:
            if temporal is not None and temporal.exists():
                temporal.unlink()


def ruta_cache_adjunto_servidor(nombre_archivo):
    nombre = PurePosixPath(str(nombre_archivo)).name
    nombre_seguro = re.sub(r'[\\/:*?"<>|]', '_', nombre)
    if Path(nombre_seguro).suffix.lower() not in EXTENSIONES_ADJUNTOS:
        raise ValueError('El archivo del servidor no tiene un formato permitido.')
    return user_data_dir() / 'adjuntos_servidor' / nombre_seguro
