from starfish_api_client.abstract_client import AbstractClient
from starfish_api_client.constants import (CERTPATH, CONNECT_TIMEOUT, 
                                           READ_TIMEOUT, RETRIES, 
                                           VERIFY_CERTS)


class RedashAPIClient(AbstractClient):
    def __init__(self, starfish_host, query_id, api_key):
        super().__init__(starfish_host, token=api_key, verify_certs=VERIFY_CERTS, cert_path=CERTPATH,
                         connect_timeout=CONNECT_TIMEOUT, read_timeout=READ_TIMEOUT, retries=RETRIES,
                         auth_method='Key')
        self.url = f'https://{starfish_host}/redash/api/'
        self.query_id = query_id
    
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
    