import os
import time
import logging

from starfish_api_client.abstract_client import AbstractClient

logger = logging.getLogger(__name__)

CERTPATH = os.getenv('SF_CERT_PATH', None)
VERIFY_CERTS = os.getenv('SF_VERIFY_CERTS', 'True').lower() in ['true', '1', 'yes']
CONNECT_TIMEOUT = int(os.getenv('SF_CONNECT_TIMEOUT', '10'))
READ_TIMEOUT = int(os.getenv('SF_READ_TIMEOUT', '60'))
RETRIES = int(os.getenv('SF_RETRIES', '3'))


class StarfishAPIClient(AbstractClient):

    def __init__(self, host=None, token=None, username=None, password=None):
        self.url = f'https://{host}/api/'
        self.cert_path = CERTPATH
        self.verify_certs = VERIFY_CERTS
        self.read_timeout = READ_TIMEOUT 
        self.connect_timeout = CONNECT_TIMEOUT
        self.retries = RETRIES
        self.token = token
        if self.token is None:
            self.token = self.get_auth_token(username, password)
    
    def get_auth_token(self, username, password):
        """Obtain a token through the auth endpoint.
        """
        data = {'username': username, 'password': password}
        r = self._send_post_request('auth/', data, skip_auth=True)
        return r['token']

    def get_volumes(self, exclude_vols=(), include_vols=()):
        res = self._send_get_request('volume')
        return [i for i in res if i['vol'] not in exclude_vols and (not include_vols or i['vol'] in include_vols)]
    
    def get_volume_attributes(self):
        return self.get_volumes()
    
    def get_volume_names(self, exclude_vols=(), include_vols=()):
        """
        Get a list of volume names
        :param exclude_vols: list of volume names to exclude
        :return: list of volume names
        """
        return [i['vol'] for i in self.get_volumes(exclude_vols, include_vols)]
    
    def get_groups(self):
        """get set of group names on starfish"""
        response = self._send_get_request('mapping/group/')
        groupnames = {g['name'] for g in response}
        return groupnames
    
    def get_vol_membership(self, volume, voltype):
        params = {'volume_name': volume}
        return self._send_get_request(f'mapping/{voltype}_membership', params=params)

    def get_vol_user_name_ids(self, volume):
        params = {'volume_name': volume}
        users = self._send_get_request('mapping/user', params=params)
        return {u['uid']: u['name'] for u in users}
    
    def get_starfish_groups(self):
        group_dict = self._send_get_request('mapping/user_membership')
        return [g['name'] for g in group_dict]
    
    def get_zones(self, zone_id=''):
        """Get all zones from the API, or the zone with the corresponding ID
        """
        zone_endpoint = 'zone' if zone_id == '' else f'zone/{zone_id}'
        return self._send_get_request(zone_endpoint)

    def get_zone_by_name(self, zone_name):
        """Get a zone by name"""
        zones = self.get_zones()
        return next((z for z in zones if z['name'] == zone_name), None)
    
    def create_zone(self, zone_name, paths, managers, managing_groups):
        """Create a zone via the API"""        
        data = {
            "name": zone_name,
            "paths": paths,
            "managers": managers,
            "managing_groups": managing_groups,
        }
        response = self._send_post_request('zone', data)
        return response
    
    def delete_zone(self, zone_id, zone_name=None):
        """Delete a zone via the API"""
        if not zone_id:
            if not zone_name:
                raise ValueError("Either zone_id or zone_name must be provided.")
            zone = self.get_zone_by_name(zone_name)
            zone_id = zone['id']
            if not zone_id:
                raise ValueError(f"Zone {zone_name} not found.")
        return self._send_delete_request(f'zone/{zone_id}')
    
    def update_zone(self, zone, paths=[], managers=[], managing_groups=[]):
        """Update a zone via the API"""
        zone_id = zone['id']
        data = {'name': zone['name']}
        data['paths'] = paths if paths else zone['paths']
        data['managers'] = managers if managers else zone['managers']
        data['managing_groups'] = managing_groups if managing_groups else zone['managing_groups']
        
        return self._send_put_request(f'zone/{zone_id}/', data)

    def request_volumes_query(self):
        return self.query(query_terms={'depth': 0})

    def request_subfolder_query(self, vol, path=''):
        return self.request_query(vol, path, query_terms={'depth': 1})

    def request_query(self, vol, path='', query_terms=None):
        # the path needs to urlencode any forward slashes
        #path = urllib.parse.quote(path, safe='')
        query_terms = query_terms if query_terms is not None else {}
        return self.query(f'{vol}:{path}', query_terms=query_terms)
    
    def query(self, volumes_paths=None, query_terms=None, async_after=5, wait= True, poll_interval=5, timeout=300):
        cols = ['aggrs', 'rec_aggrs', 'rec_aggrs.mtime', 'username', 'groupname', 'gid', 'tags_explicit',
                'tags_inherited', 'nlinks', 'errors', 'type_hum', 'valid_from', 'valid_to', 'cost',
                'total_capacity', 'logical_size', 'physical_size', 'physical_nlinks_size',
                'size_nlinks', 'entries_count', 'mode', 'mode_hum', 'mount_path']
        response =  self.__request_query(volumes_paths, query_terms=query_terms, columns=cols, async_after=async_after)
        if not wait or response['complete']:
            sync_result = response['results']
            if isinstance(sync_result, dict) and 'error' in sync_result:
                raise ValueError(f'Error in starfish result:\n{sync_result}')
            return sync_result
        query_id = response['query_id']
        for _ in range(poll_interval, timeout, poll_interval):
            time.sleep(poll_interval)
            if self.status_query(query_id):
                query_result = self.download_query_result(query_id)
                if isinstance(query_result, dict) and 'error' in query_result:
                    raise ValueError(f'Error in starfish result:\n{query_result}')
                return query_result
        raise TimeoutError(f"Query {query_id} did not complete within {timeout} seconds.")

    def status_query(self, query_id):
        """
        GET /async/query/{query_id}
        :param query_id:
        :return: True if finished, False otherwise
        """
        res = self._send_get_request(f'async/query/{query_id}')
        return res['is_done']

    def download_query_result(self, query_id):
        """
        Download query output
        GET /async/query_result/{query_id}
        :param query_id:
        :return:
        """
        return self._send_get_request(f'async/query_result/{query_id}')

    def delete_query_result(self, query_id):
        """
        cancel if still running and delete result from server
        DELETE /async/query_result/{query_id}
        raises an error if it fails
        :param query_id:
        :return: True if successful
        """
        self._send_delete_request(f'async/query_result/{query_id}')
        return True
    
    def get_tags(self):
        return self._send_get_request('tag')

    def add_tag(self, vol_path, new_tag):
        """
        :return:
        """
        if not isinstance(vol_path, list):
            vol_path = [vol_path]
        if not isinstance(new_tag, list):
            new_tag = [new_tag]
        return self._send_post_request('tag/bulk',
                                       {"paths": vol_path, "tags": new_tag, "strict": False},
                                       {'Content-Type': 'application/vnd.sf.tag.bulk+json'})

    def rename_tag(self, old_tag, new_tag):
        """
        :return:
        """
        if not isinstance(old_tag, list):
            old_tag = [old_tag]
        if not isinstance(new_tag, list):
            new_tag = [new_tag]
        return self._send_post_request('tag/rename',
                                       {"tag": old_tag, "new_tag": new_tag},
                                       {'Content-Type': 'application/vnd.sf.tag.rename+json'})

    def detach_tag(self, vol_path, tag):
        if not isinstance(vol_path, list):
            vol_path = [vol_path]
        if not isinstance(tag, list):
            tag = [tag]
        return self._send_post_request('tag/detach',
                                       {"paths": vol_path, "tags": tag},
                                       {'Content-Type': 'application/vnd.sf.tag.detach+json'})

    def purge_tag(self, vol_path, tag):
        return self._send_post_request('tag/purge',
                                       {"paths": vol_path, "tags": tag},
                                       {'Content-Type': 'application/vnd.sf.tag.purge+json'})
    
    def scan_new(self, volume, path=''):
        """
        Initiate a scan of a volume or a path within a volume to pick up changes in top level 
        directories between full scans. Needed to add tags to new directories without waiting
        for the next full scan.
        :param volume: volume name
        :param path: path within the volume
        :param force: whether to force a scan even if one is already running
        :return: scan job details
        """
        data = {
            'crawler_options': {
                'depth': 0,
                'start_points': [path] if path else [],
            },
            'immediate': True,
            'requested_by': 'client',
            'type': 'diff',
            'volume': volume
        }
        return self._send_post_request('scan/', data)
    
    def get_scan(self, scan_id):
        """
        Get details of a specific scan by its ID.
        :param scan_id: ID of the scan
        :return: scan details
        """
        return self._send_get_request(f'scan/{scan_id}')
    
    def get_scans(self, volumes=None):
        """
        Collect scans of all passed volumes, or all scans if no volumes are passed.
        :param volumes: list of volumes to query
        :return: list of recent scan data
        """
        scan_endpoint = 'scan'
        if volumes is not None:
            scan_endpoint = 'scan/?' + '&'.join([f'volume={v}' for v in volumes])

        return self._send_get_request(scan_endpoint)
    
    def __request_query(self, volumes_paths=None, groupby=None, query_terms=None, columns=None,
               async_after=5):

        if query_terms is None:
            query_terms = {}

        query_terms.update({
            'type': 'd'
        })
        query = []
        for k, v in query_terms.items():
            query.append(f'{k}={v}')

        body = {'queries': [' '.join(query)],
                'limit': 100000,
                'sort_by': groupby,
                'group_by': groupby,
                'async_after_sec': async_after,
                'format': ' '.join(columns) if columns is not None else '',
                'force_tag_inherit': 'false',
                'output_format': 'json',
                'delimiter': ',',
                'escape_paths': 'false',
                'print_headers': 'true',
                'size_unit': 'B',
                'humanize_nested': 'false',
                'mount_agent': 'None',
            }
        if volumes_paths is not None:
            body['volumes_and_paths'] = volumes_paths

        r = self._send_body('POST', 'async/query/', body)
        if r.status_code == 200:
            # return query result
            query_id = None
            if 'SF-Query-Id' in r.headers:
                query_id = r.headers.get('SF-Query-Id')
            return {'query_id': query_id, 'complete': True, 'results': r.json()}
        elif r.status_code == 202:
            query_id = r.json()['query_id']
            return {'query_id': query_id, 'complete': False, 'results': None}
