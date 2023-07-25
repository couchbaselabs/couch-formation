##
##

import sqlite3
from lib.exceptions import DBError
import lib.config as config
from lib.util.db_config import *


class LocalDB(object):

    def __init__(self):
        self.config = f"{config.cfg_dir}/config.db"
        self.cloud = f"{config.cfg_dir}/cloud.db"

    def init_config(self):
        connection = sqlite3.connect(self.config)
        cursor = connection.cursor()

        try:
            cursor.execute(AWS_CONFIG)
            cursor.execute(GCP_CONFIG)
            cursor.execute(AZURE_CONFIG)
            cursor.execute(VMWARE_CONFIG)
            cursor.execute(CAPELLA_CONFIG)
        except Exception as err:
            raise DBError(f"auth db init error: {err}")

    def get_config(self):
        connection = sqlite3.connect(self.config)
        cursor = connection.cursor()
        table = f"{config.cloud}_config"

        cursor.execute(f"SELECT * FROM {table} WHERE priority=?", (1,))
        rows = cursor.fetchall()
        print(rows)
