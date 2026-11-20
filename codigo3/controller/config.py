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