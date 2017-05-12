from datetime import datetime, timedelta
import dateutil, pytz
import requests

import io
import dateutil.parser as dp
import json

version_string = '1.0.0'


DEFAULT_USERNAME = '<put a username here>'
DEFAULT_PASSWORD = '<put a password here>'
DEFAULT_CLIENT_ID = 'das_web_client'
DEFAULT_PROVIDER_KEY = 'demoloader'
DEFAULT_SERVICE_ROOT = 'https://demo.pamdas.org/api/v1.0'
DEFAULT_TOKEN_URL = 'https://demo.pamdas.org/oauth2/token'

class DasClientException(Exception):
    pass


class DasClientPermissionDenied(DasClientException):
    pass


class DasClientNotFound(DasClientException):
    pass


class DasClient(object):

    def __init__(self, *args, **kwargs):
        self.service_root = kwargs.get('service_root', DEFAULT_SERVICE_ROOT)
        self.token_url = kwargs.get('token_url', DEFAULT_TOKEN_URL)

        self.username = kwargs.get('username', DEFAULT_USERNAME)
        self.password = kwargs.get('password', DEFAULT_PASSWORD)
        self.client_id = kwargs.get('client_id', DEFAULT_CLIENT_ID)
        self.provider_key = kwargs.get('provider_key', DEFAULT_PROVIDER_KEY)
        self.auth = None
        self.auth_expires = pytz.utc.localize(datetime.min)

        self.user_agent = 'das-client/{}'.format(version_string)

    def _auth_is_valid(self):
        return self.auth_expires > datetime.now(tz=pytz.utc)

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
            self.auth_expires = datetime.now(tz=pytz.utc) + timedelta(seconds=expires_in)
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
        return self._get('user/me')

    def post_source(self, source):
        print('Posting source for manufacturer_id: %s' % source.get('manufacturer_id'))
        return self._post('sources', payload=source)

    def _clean_observation(self, observation):
        if hasattr(observation['recorded_at'], 'isoformat'):
            observation['recorded_at'] = observation['recorded_at'].isoformat()
        return observation

    def post_observation(self, observation):

        if isinstance(observation, (list, set)):
            payload = [self._clean_observation(o) for o in observation]
        else:
            payload = self._clean_observation(observation)

        print('Posting observation: %s' % payload)
        return self._post('observations', payload=payload)

    def pulse(self, message=None):
        return self._get('status')

    def get_subject_tracks(self, subject_id):
        return self._get('subject/{0}/tracks'.format(subject_id))

    def get_subjects(self):
        return self._get('subjects')

