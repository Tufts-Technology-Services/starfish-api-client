import requests
import os

from starfish_api_client.abstract_client import AbstractClient


class RedashAPIClient(AbstractClient):
    def __init__(self, starfish_host, query_id, api_key):
        self.url = f'https://{starfish_host}/redash/api/'
        self.token = api_key
        self.query_id = query_id
        self.auth_method = 'Key'
    
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
    