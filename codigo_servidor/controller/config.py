from decouple import AutoConfig
from controller.app_paths import application_dir


config = AutoConfig(search_path=str(application_dir()))


def load_db_config(read_setting=config):
    """Load PostgreSQL connection settings without assuming a local server."""
    settings = {
        'host': read_setting('POSTGRES_HOST', default=''),
        'user': read_setting('POSTGRES_USER', default='postgres'),
        'password': read_setting('POSTGRES_PASSWORD', default=''),
        'database': read_setting('POSTGRES_DB', default='postgres'),
        'port': read_setting('POSTGRES_PORT', default=5432, cast=int),
    }

    for environment_name, connection_option in (
        ('POSTGRES_SSLMODE', 'sslmode'),
        ('POSTGRES_SSLROOTCERT', 'sslrootcert'),
        ('POSTGRES_SSLCERT', 'sslcert'),
        ('POSTGRES_SSLKEY', 'sslkey'),
    ):
        value = read_setting(environment_name, default='').strip()
        if value:
            settings[connection_option] = value

    return settings


def load_sftp_config(read_setting=config):
    """Load SFTP settings for storing generated files on the shared server."""
    return {
        'host': read_setting('SFTP_HOST', default='').strip(),
        'port': read_setting('SFTP_PORT', default=22, cast=int),
        'username': read_setting('SFTP_USER', default='').strip(),
        'password': read_setting('SFTP_PASSWORD', default=''),
        'remote_dir': read_setting('SFTP_REMOTE_DIR', default='').strip(),
        'host_key_fingerprint': read_setting(
            'SFTP_HOST_KEY_FINGERPRINT', default=''
        ).strip(),
    }


DB_config = load_db_config()