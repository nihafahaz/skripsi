import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

class CompatibleConnection(pymysql.connections.Connection):
    def cursor(self, cursor=None, dictionary=False):
        if dictionary:
            return super().cursor(pymysql.cursors.DictCursor)
        return super().cursor(cursor)

def get_db_connection():
    connection = CompatibleConnection(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "db_cabai")
    )

    return connection