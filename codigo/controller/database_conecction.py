import psycopg
from psycopg.rows import dict_row
from .config import DB_config


class Database_connection:
    def __init__(self):
        self.config = DB_config

    def get_connection(self):
        try:
            conexion = psycopg.connect(**self.config)
            return conexion
        except psycopg.Error as e:
            print(f"Error al conectar con PostgreSQL: {e}")
            return None

    def ejecutar_consulta(self, query, params=()):
        conexion = self.get_connection()

        if not conexion:
            return None

        try:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, params)
                resultados = cursor.fetchall()
                return resultados

        except psycopg.Error as e:
            print(f"Error en la consulta SQL: {e}")
            return None

        finally:
            conexion.close()
