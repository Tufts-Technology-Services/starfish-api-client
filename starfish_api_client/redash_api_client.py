from starfish_api_client.abstract_client import AbstractClient
from starfish_api_client.constants import (CERTPATH, CONNECT_TIMEOUT, 
                                           READ_TIMEOUT, RETRIES, 
                                           VERIFY_CERTS)


class RedashAPIClient(AbstractClient):
    def __init__(self, starfish_host, query_id, api_key):
        self.url = f'https://{starfish_host}/redash/api/'
        self.token = api_key
        self.query_id = query_id
        self.configure_certs(VERIFY_CERTS, CERTPATH)
        self.configure_timeout(CONNECT_TIMEOUT, READ_TIMEOUT)
        self.configure_retries(RETRIES)
        self.set_auth_token_name('Key')
    
    def query(self):
        """submit a query and return a json of the results."""
        return self._send_get_request(f'queries/{self.query_id}/results')

    def download_query_results(self, local_filename: str):
        """
        get the results of a query from redash
        :param query_id: id of the
        :return:
        """
        self._download_file(f'queries/{self.query_id}/results.csv', f'{local_filename}.csv')
    