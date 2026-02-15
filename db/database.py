import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT")
        self.dbname = os.getenv("DB_NAME")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASS")
        self.conn = None

    def _connect_default(self):
        """Connect to the default 'postgres' DB for creation check."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database="postgres",
            user=self.user,
            password=self.password
        )

    def _create_db_if_not_exists(self):
        """Check if DB exists; create if missing."""
        conn = self._connect_default()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s;", (self.dbname,))
        exists = cur.fetchone()
        if not exists:
            print(f"⚡ Database '{self.dbname}' not found. Creating...")
            cur.execute(f"CREATE DATABASE {self.dbname};")
            print(f"✅ Database '{self.dbname}' created")
        cur.close()
        conn.close()

    def connect(self):
        """Main connection method."""
        if self.conn is None:
            # Ensure DB exists
            self._create_db_if_not_exists()

            # Connect to the actual database
            try:
                self.conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.dbname,
                    user=self.user,
                    password=self.password,
                    cursor_factory=RealDictCursor
                )
                print(f"✅ Connected to database '{self.dbname}'")
            except Exception as e:
                print("❌ Connection failed:", e)
        return self.conn

    def query(self, sql, params=None):
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                return cur.fetchall()
            conn.commit()
            return None

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            print("✅ Database connection closed")