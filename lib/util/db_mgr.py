##
##

from sqlite_utils import Database
from enum import Enum
from lib.config_values import CloudTable
import lib.config as config


class LocalDB(object):

    def __init__(self):
        self.config = f"{config.cfg_dir}/config.db"
        self.cloud = f"{config.cfg_dir}/cloud.db"

    def get_config(self):
        db = Database(self.config)
        table = f"{config.cloud}_config"

        try:
            result = list(db[table].rows)[0]
            return result
        except IndexError:
            return None

    def update_config(self):
        db = Database(self.config)
        table = f"{config.cloud}_config"
        records = dict(config.cloud_config.as_dict)
        records.update({"id": 1})

        db[table].upsert(records, pk="id")

    def get_cloud(self, data_type: Enum):
        pass

    def update_cloud(self, table_type: Enum, values: dict):
        db = Database(self.config)
        table = f"{config.cloud}_{table_type.name.lower()}"
        table_obj = CloudTable[table_type.name].value()

        table_obj.from_dict(values)
        records = dict(table_obj.as_dict)

        db[table].upsert(records, pk=table_obj.get_pk)
