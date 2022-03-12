from pathlib import Path

from sqlalchemy import create_engine


class DB:
    def __init__(self, conn_string):
        self.conn_string = conn_string

    def select(self, db_name):
        args = {
            'dbname': db_name,
            'sslrootcert': f'{Path(__file__).parent}/DigiCertGlobalRootCA.crt.pem',
            'sslmode': 'verify-full'
        }
        db = create_engine(self.conn_string, connect_args=args)
        return db
