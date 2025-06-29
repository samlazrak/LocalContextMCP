import os
import psycopg2
from psycopg2 import pool

DB_HOST = os.environ.get('PGHOST', 'localhost')
DB_PORT = int(os.environ.get('PGPORT', 5432))
DB_NAME = os.environ.get('PGDATABASE', 'mcp_memory')
DB_USER = os.environ.get('PGUSER', 'postgres')
DB_PASSWORD = os.environ.get('PGPASSWORD', '')
SCHEMA_PATH = 'schema.sql'

# Connection pool
pg_pool = psycopg2.pool.SimpleConnectionPool(
    1, 10,
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

def get_connection():
    return pg_pool.getconn()

def release_connection(conn):
    pg_pool.putconn(conn)

def setup_database(schema_path=SCHEMA_PATH):
    with open(schema_path, 'r') as f:
        schema = f.read()
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(schema)
    release_connection(conn)

def get_schema_version():
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute('SELECT version FROM schema_version ORDER BY version DESC LIMIT 1;')
            row = cur.fetchone()
    release_connection(conn)
    return row[0] if row else None

if __name__ == '__main__':
    setup_database()
    print('Database and schema setup complete.') 