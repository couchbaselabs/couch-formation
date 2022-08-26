##
##

import base64
import hmac
import hashlib
import datetime
from urllib.parse import urlparse
from requests.auth import AuthBase
from .capexceptions import *


class capella_auth(AuthBase):

    def __init__(self):
        if 'CBC_ACCESS_KEY' in os.environ:
            self.capella_key = os.environ['CBC_ACCESS_KEY']
        else:
            raise CapellaMissingAuthKey("Please set CBC_ACCESS_KEY for Capella API access")

        if 'CBC_SECRET_KEY' in os.environ:
            self.capella_secret = os.environ['CBC_SECRET_KEY']
        else:
            raise CapellaMissingSecretKey("Please set CBC_SECRET_KEY for Capella API access")

    def __call__(self, r):
        ep_path = urlparse(r.url).path
        ep_params = urlparse(r.url).query
        if len(ep_params) > 0:
            cbc_api_endpoint = ep_path + f"?{ep_params}"
        else:
            cbc_api_endpoint = ep_path
        cbc_api_method = r.method
        cbc_api_now = int(datetime.datetime.now().timestamp() * 1000)
        cbc_api_message = cbc_api_method + '\n' + cbc_api_endpoint + '\n' + str(cbc_api_now)
        cbc_api_signature = base64.b64encode(hmac.new(bytes(self.capella_secret, 'utf-8'),
                                                      bytes(cbc_api_message, 'utf-8'),
                                                      digestmod=hashlib.sha256).digest())
        cbc_api_request_headers = {
            'Authorization': 'Bearer ' + self.capella_key + ':' + cbc_api_signature.decode(),
            'Couchbase-Timestamp': str(cbc_api_now)
        }
        r.headers.update(cbc_api_request_headers)
        return r
