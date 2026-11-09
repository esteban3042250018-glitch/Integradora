import base64
import hashlib
import hmac
from pathlib import Path
import posixpath
import re
import tempfile

import paramiko

from .config import SFTP_config


class RemoteStorageError(RuntimeError):
    pass


def _fingerprint(key):
    digest = hashlib.sha256(key.asbytes()).digest()
    encoded = base64.b64encode(digest).decode('ascii').rstrip('=')
    return f'SHA256:{encoded}'


def _conectar_sftp():
    required = ('host', 'user', 'password', 'remote_dir', 'host_key_fingerprint')
    missing = [key for key in required if not SFTP_config.get(key)]
    if missing:
        names = ', '.join(f'SFTP_{key.upper()}' for key in missing)
        raise RemoteStorageError(f'Falta configurar en .env: {names}.')

    expected_fingerprint = SFTP_config['host_key_fingerprint'].strip()
    if not expected_fingerprint.startswith('SHA256:'):
        raise RemoteStorageError(
            'SFTP_HOST_KEY_FINGERPRINT debe tener formato SHA256:...'
        )

    transport = paramiko.Transport(
        (SFTP_config['host'], SFTP_config['port'])
    )
    try:
        security_options = transport.get_security_options()
        if 'ssh-ed25519' not in security_options.key_types:
            raise RemoteStorageError(
                'La versión instalada de Paramiko no ofrece claves de host Ed25519.'
            )
        security_options.key_types = ('ssh-ed25519',)
        transport.start_client(timeout=15)
        host_key = transport.get_remote_server_key()
        if not isinstance(host_key, paramiko.Ed25519Key):
            raise RemoteStorageError(
                'El servidor SFTP no presentó una clave de host Ed25519.'
            )

        actual_fingerprint = _fingerprint(host_key)
        if not hmac.compare_digest(actual_fingerprint, expected_fingerprint):
            raise RemoteStorageError(
                'La huella SSH de la VM no coincide con SFTP_HOST_KEY_FINGERPRINT. '
                'Verifica la huella desde la consola de Ubuntu antes de continuar.'
            )

        transport.auth_password(
            username=SFTP_config['user'],
            password=SFTP_config['password'],
        )
        if not transport.is_authenticated():
            raise RemoteStorageError('El servidor SSH rechazó la autenticación.')

        return transport, paramiko.SFTPClient.from_transport(transport)
    except Exception:
        transport.close()
        raise


def subir_pdf_al_servidor(ruta_pdf_local, callback=None):
    local_path = Path(ruta_pdf_local)
    if not local_path.is_file():
        raise FileNotFoundError(f'No se encontró el PDF local: {local_path}')
    with local_path.open('rb'):
        pass

    transport, sftp = _conectar_sftp()
    try:
        remote_path = posixpath.join(
            SFTP_config['remote_dir'].rstrip('/'),
            local_path.name,
        )
        try:
            sftp.put(
                str(local_path),
                remote_path,
                callback=callback,
                confirm=True,
            )
        except PermissionError as error:
            raise RemoteStorageError(
                'El servidor SFTP denegó la escritura en SFTP_REMOTE_DIR. '
                'Verifica que SFTP_USER tenga permiso para crear archivos allí.'
            ) from error
        return remote_path
    finally:
        sftp.close()
        transport.close()


def descargar_pdf_del_servidor(ruta_remota, folio):
    if not SFTP_config.get('remote_dir'):
        raise RemoteStorageError(
            'Falta configurar SFTP_REMOTE_DIR en el archivo .env.'
        )
    base_remota = posixpath.normpath(SFTP_config.get('remote_dir', ''))
    ruta_remota = posixpath.normpath(str(ruta_remota))
    try:
        dentro_de_carpeta = (
            base_remota not in ('', '.', '/')
            and posixpath.commonpath((base_remota, ruta_remota)) == base_remota
            and ruta_remota != base_remota
        )
    except ValueError:
        dentro_de_carpeta = False
    if not dentro_de_carpeta:
        raise RemoteStorageError(
            'La ruta registrada no pertenece a la carpeta SFTP configurada.'
        )

    transporte, sftp = _conectar_sftp()
    temporal = None
    try:
        carpeta_local = Path(tempfile.gettempdir()) / 'GestionInstitucional' / 'Enviados'
        carpeta_local.mkdir(parents=True, exist_ok=True)
        nombre_seguro = re.sub(r'[\\/:*?"<>|]+', '_', str(folio)).strip('._')
        destino = carpeta_local / f'{nombre_seguro or "documento"}.pdf'
        with tempfile.NamedTemporaryFile(
                dir=carpeta_local, suffix='.part', delete=False) as archivo:
            temporal = Path(archivo.name)
        sftp.get(ruta_remota, str(temporal))
        if temporal.stat().st_size != sftp.stat(ruta_remota).st_size:
            raise RemoteStorageError(
                'La validación del tamaño del PDF descargado no coincidió.'
            )
        temporal.replace(destino)
        return destino
    finally:
        if temporal is not None and temporal.exists():
            temporal.unlink()
        sftp.close()
        transporte.close()
