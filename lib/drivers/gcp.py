##
##

import logging
import os
import json
from lib.exceptions import GCPDriverError


class GCPBase(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.auth_directory = os.environ['HOME'] + '/.config/gcloud'

        if 'GCP_ACCOUNT_FILE' in os.environ:
            self.gcp_account_file = os.environ['GCP_ACCOUNT_FILE']
        else:
            print("Please set GCP_ACCOUNT_FILE to reference the path to your auth json file")
            raise GCPDriverError("can not locate auth json file")

        if 'GCP_PROJECT_ID' in os.environ:
            self.gcp_project = os.environ['GCP_PROJECT_ID']
        else:
            file_handle = open(self.gcp_account_file, 'r')
            auth_data = json.load(file_handle)
            file_handle.close()
            if 'project_id' in auth_data:
                gcp_auth_json_project_id = auth_data['project_id']
                self.gcp_project = gcp_auth_json_project_id
            else:
                print("can not determine GCP project, please set GCP_PROJECT_ID")
                raise GCPDriverError("can not determine project ID")


