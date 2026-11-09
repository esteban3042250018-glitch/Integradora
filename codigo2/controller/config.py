from decouple import AutoConfig
from controller.app_paths import application_dir


config = AutoConfig(search_path=str(application_dir()))


DB_config = {
    'host': config('POSTGRES_HOST', default='localhost'),
    'user': config('POSTGRES_USER', default='postgres'),
    'password': config('POSTGRES_PASSWORD', default=''),
    'dbname': config('POSTGRES_DB', default='postgres'),
    'port': config('POSTGRES_PORT', default=5432, cast=int),
}

SFTP_config = {
    'host': config('SFTP_HOST', default=''),
    'port': config('SFTP_PORT', default=22, cast=int),
    'user': config('SFTP_USER', default=''),
    'password': config('SFTP_PASSWORD', default=''),
    'remote_dir': config('SFTP_REMOTE_DIR', default=''),
    'host_key_fingerprint': config('SFTP_HOST_KEY_FINGERPRINT', default=''),
}