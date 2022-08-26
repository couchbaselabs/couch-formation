##
##

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse
import json
import logging
from .capauth import capella_auth
from .capexceptions import *


class capella_session(object):

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
            raise CapellaNotAuthorized(f"Capella API: Forbidden: Insufficient privileges{url}")
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

    def api_get(self, endpoint, items=[]):
        ep = f"{self.capella_url}{endpoint}"

        response = self.session.get(ep, auth=capella_auth())

        try:
            self.check_status_code(response.status_code, ep)
        except Exception:
            raise

        response_json = json.loads(response.text)

        if "cursor" in response_json:
            if "pages" in response_json["cursor"]:
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
        response = self.session.post(self.capella_url + endpoint, auth=capella_auth(), json=body)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        response_json = json.loads(response.text)
        return response_json
