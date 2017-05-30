from datetime import datetime, timedelta
import dateutil, pytz
import requests

import io
import dateutil.parser as dp
import json

version_string = '1.0.0'


class DasClient(object):
    """
    DasClient provides basic access to a DAS API. It requires the coordinates of a DAS API service as well 
    as valid credentials for a user.
    
    The boiler-plate code handles authentication, so you don't have to think about Oauth2 or refresh tokens.
    
    As of May 12, 2017 it includes just a basic set of functions to access Subject data and to post observations.
    
    """
    def __init__(self, username=None, password=None,
                   service_root=None,
                   token_url=None,
                   provider_key=None,
                   client_id=None):

        """
        Initialize a DasClient instance.
        
        :param username: DAS username 
        :param password: DAS password
        :param service_root: The root of the DAS API (Ex. https://demo.pamdas.org/api/v1.0)
        :param token_url: The auth token url for DAS (Ex. https://demo.pamdas.org/oauth2/token)
        :param provider_key: provider-key for posting observation data (Ex. xyz_provider)
        :param client_id: Auth client ID (Ex. das_web_client)
        """
        self.service_root = service_root
        self.token_url = token_url
        self.username = username
        self.password = password
        self.client_id = client_id
        self.provider_key = provider_key

        self.auth = None
        self.auth_expires = pytz.utc.localize(datetime.min)

        self.user_agent = 'das-client/{}'.format(version_string)

    def _auth_is_valid(self):
        return self.auth_expires > pytz.utc.localize(datetime.utcnow())

    def auth_headers(self):

        if self.auth:
            if not self._auth_is_valid():
                if not self.refresh_token():
                    if not self.login():
                        raise DasClientException('Login failed.')
        else:
            if not self.login():
                raise DasClientException('Login failed.')

        return {'Authorization': '{} {}'.format(self.auth['token_type'],
                                                self.auth['access_token']),
                'Accept-Type': 'application/json'}

    def refresh_token(self):
        payload = {'grant_type': 'refresh_token',
                   'refresh_token': self.auth['refresh_token'],
                   'client_id': self.client_id
                   }
        return self._token_request(payload)

    def login(self):

        payload = {'grant_type': 'password',
                   'username': self.username,
                   'password': self.password,
                   'client_id': self.client_id
                   }
        return self._token_request(payload)

    def _token_request(self, payload):

        response = requests.post(self.token_url, data=payload)
        if response.ok:
            self.auth = json.loads(response.text)
            expires_in = int(self.auth['expires_in']) - 5 * 60
            self.auth_expires = pytz.utc.localize(datetime.utcnow()) + timedelta(seconds=expires_in)
            return True

        self.auth = None
        self.auth_expires = pytz.utc.localize(datetime.min)
        return False

    def _das_url(self, path):
        return '/'.join((self.service_root, path))

    def _get(self, path, **kwargs):
        headers = {'User-Agent': self.user_agent}

        headers.update(self.auth_headers())

        response = requests.get(self._das_url(path), headers=headers)
        if response.ok:
            return json.loads(response.text)['data']

        if response.status_code == 404:  # not found
            raise DasClientNotFound()

        if response.status_code == 403:  # forbidden
            try:
                _ = json.loads(response.text)
                reason = _['status']['detail']
            except:
                reason = 'unknown reason'
            raise DasClientPermissionDenied(reason)

        raise DasClientException('Failed to call DAS web service.')

    def _post(self, path, payload):
        headers = {'Content-Type': 'application/json',
                   'User-Agent': self.user_agent}
        headers.update(self.auth_headers())
        body = json.dumps(payload)

        try:
            response = requests.post(self._das_url(path), data=body, headers=headers)
            if response and response.ok:
                return json.loads(response.text)['data']

            if response.status_code == 404:  # not found
                raise DasClientNotFound()

            if response.status_code == 403:  # forbidden
                try:
                    _ = json.loads(response.text)
                    reason = _['status']['detail']
                except:
                    reason = 'unknown reason'
                raise DasClientPermissionDenied(reason)

            print('provider_key: %s, path: %s\n\tBad result from das service. Message: %s' % (
                self.provider_key, path, response.text))
            raise DasClientException('Failed to post to DAS web service.')

        except Exception as e:
            print('Posting observation. provider_key: %s, path: %s, message: %s' %
                  (self.provider_key, path, (response.text if response else '<no response text>')))

    def get_me(self):
        """
        Get details for the 'me', the current DAS user.
        :return: 
        """
        return self._get('user/me')

    def post_source(self, source):
        '''
        Post a source payload to create a new source.
        :param source: 
        :return: 
        '''
        print('Posting source for manufacturer_id: %s' % source.get('manufacturer_id'))
        return self._post('sources', payload=source)

    def _clean_observation(self, observation):
        if hasattr(observation['recorded_at'], 'isoformat'):
            observation['recorded_at'] = observation['recorded_at'].isoformat()
        return observation

    def _clean_event(self, event):
        return event

    def post_observation(self, observation):
        """
        Post a new observation, or a list of observations.
        """
        if isinstance(observation, (list, set)):
            payload = [self._clean_observation(o) for o in observation]
        else:
            payload = self._clean_observation(observation)

        print('Posting observation: %s' % payload)
        return self._post('observations', payload=payload)

    def post_event(self, event):
        """
        Post a new Event.
        """
        payload = self._clean_event(event)

        print('Posting event: %s' % payload)
        return self._post('activity/events', payload=payload)

    def pulse(self, message=None):
        """
        Convenience method for getting status of the DAS api.
        :param message: 
        :return: 
        """
        return self._get('status')

    def get_subject_tracks(self, subject_id):
        """
        Get the latest tracks for the Subject having the given subject_id.
        """
        return self._get('subject/{0}/tracks'.format(subject_id))

    def get_subjects(self):
        """
        Get the list of subjects to whom the user has access.
        :return: 
        """
        return self._get('subjects')

class DasClientException(Exception):
    pass


class DasClientPermissionDenied(DasClientException):
    pass


class DasClientNotFound(DasClientException):
    pass



if __name__ == '__main__':
    """
    Here's an example for using the client. You'll need to provide the valid arguments to the 
    DasClient constructor.
    """

    MY_USERNAME = '<your username>'
    MY_PASSWORD = '<your password>'
    MY_SERVICE_ROOT = 'https://demo.pamdas.org/api/v1.0'
    MY_TOKEN_URL = 'https://demo.pamdas.org/oauth2/token'
    MY_PROVIDER_KEY = 'demo-provider'
    MY_CLIENT_ID = 'das_web_client'

    dc = DasClient(username=MY_USERNAME, password=MY_PASSWORD,
                   service_root=MY_SERVICE_ROOT,
                   token_url=MY_TOKEN_URL,
                   provider_key=MY_PROVIDER_KEY,
                   client_id=MY_CLIENT_ID
                )

    # Example 1: use the pulse() function be sure you can reach the API.
    print (dc.pulse())

    # Example 2: Use the get_subjects() function to fetch a list of Subjects that the user may see.
    subjects = dc.get_subjects()

    # Example 3: Take a Subject ID from the results of the last call, and fetch tracks.
    for sub in subjects:
        print(sub)
        if sub.get('tracks_available', False):
            print('Getting tracks for %s' % (sub['name']))
            tracks = dc.get_subject_tracks(sub['id'])
            print(tracks)

