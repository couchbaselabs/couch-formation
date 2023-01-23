##
##

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse
from requests.auth import AuthBase
import json
import logging
import os
import base64
import datetime
import hmac
import hashlib
from lib.exceptions import CapellaMissingSecretKey, CapellaMissingAuthKey, CapellaForbidden, CapellaNotAuthorized, CapellaNotImplemented, CapellaInternalServerError, \
    CapellaRequestValidationError


class CapellaAuth(AuthBase):

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


class CapellaSession(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.capella_url = 'https://cloudapi.cloud.couchbase.com'
        self.session = requests.Session()
        retries = Retry(total=60,
                        backoff_factor=0.1,
                        status_forcelist=[500, 501, 503])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self._response = None

    def check_status_code(self, code, ep=None):
        url = f": {ep}" if ep is not None else ""
        self.logger.debug("Capella API call status code {}".format(code))
        if code == 200:
            return True
        elif code == 401:
            raise CapellaNotAuthorized(f"Capella API: Unauthorized{url}")
        elif code == 403:
            raise CapellaForbidden(f"Capella API: Forbidden: Insufficient privileges{url}")
        elif code == 404:
            raise CapellaNotImplemented(f"Capella API: Not Found{url}")
        elif code == 422:
            raise CapellaRequestValidationError(f"Capella API: Request Validation Error{url}")
        elif code == 500:
            raise CapellaInternalServerError(f"Capella API: Server Error{url}")
        else:
            raise Exception("Unknown Capella API call status code {}".format(code))

    @property
    def response(self):
        return self._response

    def json(self):
        return json.loads(self._response)

    def http_get(self, endpoint, headers=None, verify=False):
        response = self.session.get(self.capella_url + endpoint, headers=headers, verify=verify)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        self._response = response.text
        return self

    def http_post(self, endpoint, data=None, headers=None, verify=False):
        response = self.session.post(self.capella_url + endpoint, data=data, headers=headers, verify=verify)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        self._response = response.text
        return self

    def api_get(self, endpoint, items=None):
        if items is None:
            items = []
        ep = f"{self.capella_url}{endpoint}"

        response = self.session.get(ep, auth=CapellaAuth())

        try:
            self.check_status_code(response.status_code, ep)
        except Exception:
            raise

        response_json = json.loads(response.text)

        if "cursor" in response_json:
            if "pages" in response_json["cursor"]:
                if "items" in response_json["data"]:
                    items.extend(response_json["data"]["items"])
                else:
                    items.extend(response_json["data"])
                if "next" in response_json["cursor"]["pages"]:
                    cur_page = response_json["cursor"]["pages"]["page"]
                    next_page = response_json["cursor"]["pages"]["next"]
                    last_page = response_json["cursor"]["pages"]["last"]
                    per_page = response_json["cursor"]["pages"]["perPage"]
                    ep_path = urlparse(endpoint).path
                    if cur_page != last_page:
                        self.api_get(f"{ep_path}?page={next_page}&perPage={per_page}", items)
        else:
            items.append(response_json)

        return items

    def api_post(self, endpoint, body):
        response = self.session.post(self.capella_url + endpoint, auth=CapellaAuth(), json=body)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        response_json = json.loads(response.text)
        return response_json
