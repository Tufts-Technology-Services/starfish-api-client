from urllib.parse import urljoin
import os
import logging
import requests


logger = logging.getLogger(__name__)


class AbstractClient:
    url = None
    refresh_token = None
    token = None
    cert_path: str = None
    verify_certs: bool = True
    connect_timeout: int = 5
    read_timeout: int = 20

    def renew_token(self, refresh_token):
        raise NotImplementedError
    
    def _get_certs(self):
        if self.cert_path is not None and self.verify_certs:
            if not os.path.exists(self.cert_path):
                logger.error("Certificate path %s does not exist.", self.cert_path)
                raise FileNotFoundError(f"Certificate path {self.cert_path} does not exist.")
            return self.cert_path
        return self.verify_certs
    
    def _get_timeout(self):
        return (self.connect_timeout, self.read_timeout)
    
    def _get_headers(self, additional_headers=None, skip_auth=False):
        headers = {
            'Accept': 'application/json'
        }
        if not skip_auth:
            headers['Authorization'] = f'Bearer {self.token}'
        if additional_headers is not None:
            headers.update(additional_headers)
        return headers

    def _send_get_request(self, endpoint, params=None, retries=RETRIES):
        if self.token is None and self.refresh_token is not None:
            self.renew_token(self.refresh_token)

        logger.debug("%s %s payload: %s", "GET", urljoin(self.url, endpoint), params)
        headers = self._get_headers()
        logger.debug("Headers: %s", headers)
        r = requests.get(urljoin(self.url, endpoint),
                         params=params if params is not None else {},
                         headers=headers,
                         verify=self._get_certs(),
                         timeout=self._get_timeout())
        try:
            logger.debug("Response status: %s", r.status_code)
            logger.debug("Response body: %s", r.text)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if self.refresh_token is not None and retries > 0 and e.response.status_code in [401, 403]:
                self.renew_token(self.refresh_token)
                self._send_get_request(endpoint, params, retries=(retries - 1))
            else:
                raise e
        except requests.exceptions.Timeout as e:
            logger.error("Timeout: %s", e)
            if retries > 0:
                logger.info("Retrying GET request to %s, retries left: %s", endpoint, retries)
                self._send_get_request(endpoint, params, retries=(retries - 1))
            else:
                raise e
        return r.json()

    def _send_post_request(self, endpoint, payload, headers=None, skip_auth=False):
        r = self._send_body('POST', endpoint, payload, headers, skip_auth)
        return r.json()
    
    def _send_put_request(self, endpoint, payload, headers=None, skip_auth=False):
        r = self._send_body('PUT', endpoint, payload, headers, skip_auth)
        return r.json()
    
    def _send_patch_request(self, endpoint, payload, headers=None, skip_auth=False):
        r = self._send_body('PATCH', endpoint, payload, headers, skip_auth)
        return r.json()
    
    def _send_body(self, http_method, endpoint, payload, headers=None, skip_auth=False, retries=RETRIES):
        if not skip_auth and self.token is None and self.refresh_token is not None:
            self.renew_token(self.refresh_token)

        # list of valid http methods
        if http_method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            raise ValueError(f'Invalid http method: {http_method}')
        
        headers = headers if headers is not None else {}
        headers.update({'Content-Type': 'application/json'})

        logger.debug("%s %s payload: %s", http_method, urljoin(self.url, endpoint), payload)
        headers = self._get_headers(headers, skip_auth=skip_auth)
        logger.debug("Headers: %s", headers)
        r = requests.request(http_method, urljoin(self.url, endpoint),
                          json=payload,
                          headers=headers,
                          verify=self._get_certs(),
                          timeout=self._get_timeout())
        
        try:
            logger.debug("Response status: %s", r.status_code)
            logger.debug("Response body: %s", r.text)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if self.refresh_token is not None and retries > 0 and e.response.status_code in [401, 403]:
                self.renew_token(self.refresh_token)
                return self._send_body(http_method, endpoint, payload, headers, skip_auth, retries=(retries - 1))
            else:
                raise e
        except requests.exceptions.Timeout as e:
            logger.error("Timeout: %s", e)
            if retries > 0:
                logger.info("Retrying %s request to %s, retries left: %s", http_method, endpoint, retries)
                return self._send_body(http_method, endpoint, payload, headers, skip_auth, retries=(retries - 1))
            else:
                raise e
        #print(r.headers)
        return r

    def _send_delete_request(self, endpoint, body=None, retries=RETRIES):
        if body is not None:
            return self._send_body('DELETE', endpoint, body)
        if self.token is None and self.refresh_token is not None:
            self.renew_token(self.refresh_token)

        logger.debug("%s %s payload: %s", "DELETE", urljoin(self.url, endpoint), body)
        headers = self._get_headers()
        logger.debug("Headers: %s", headers)
        r = requests.delete(urljoin(self.url, endpoint),
                            headers=headers,
                            verify=self._get_certs(),
                            timeout=self._get_timeout())

        try:
            logger.debug("Response status: %s", r.status_code)
            logger.debug("Response body: %s", r.text)
            r.raise_for_status()
            return {'status': r.status_code}
        except requests.exceptions.HTTPError as e:
            if self.refresh_token is not None and retries > 0 and e.response.status_code in [401, 403]:
                self.renew_token(self.refresh_token)
                return self._send_delete_request(endpoint, body, retries=(retries - 1))
            else:
                raise e
        except requests.exceptions.Timeout as e:
            logger.error("Timeout: %s", e)
            if retries > 0:
                logger.info("Retrying DELETE request to %s, retries left: %s", endpoint, retries)
                return self._send_delete_request(endpoint, body, retries=(retries - 1))
            else:
                raise e
