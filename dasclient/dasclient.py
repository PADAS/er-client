from datetime import datetime, timedelta
import pytz
import logging

# Remove these once the socketio stuff is working properly
logging.getLogger('requests').setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)

import requests

import io
import dateutil.parser as dp
import json
from .version import __version__

version_string = __version__

def linkify(url, params):
    p = ['='.join((str(x),str(y))) for x,y in params.items()]
    p = '&'.join(p)
    return '?'.join((url, p))

def split_link(url):
    url, qs = url.split('?')
    params = dict([p.split('=') for p in qs.split('&')])
    return (url, params)

class DasClient(object):
    """
    DasClient provides basic access to a DAS API. It requires the coordinates of a DAS API service as well 
    as valid credentials for a user.
    
    The boiler-plate code handles authentication, so you don't have to think about Oauth2 or refresh tokens.
    
    As of May 12, 2017 it includes just a basic set of functions to access Subject data and to post observations.

    June 6, 2017: Added methods to add a photo or document to an Event.
        
    """
    def __init__(self, **kwargs):

        """
        Initialize a DasClient instance.
        
        :param username: DAS username 
        :param password: DAS password
        :param service_root: The root of the DAS API (Ex. https://demo.pamdas.org/api/v1.0)
        :param token_url: The auth token url for DAS (Ex. https://demo.pamdas.org/oauth2/token)
        :param provider_key: provider-key for posting observation data (Ex. xyz_provider)
        :param client_id: Auth client ID (Ex. das_web_client)
        """

        self.auth = None
        self.auth_expires = pytz.utc.localize(datetime.min)

        self.service_root = kwargs.get('service_root')
        self.client_id = kwargs.get('client_id')
        self.provider_key = kwargs.get('provider_key')

        self.token_url = kwargs.get('token_url')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.realtime_url = kwargs.get('realtime_url')

        if kwargs.get('token'):
            self.token = kwargs.get('token')
            self.auth = dict(token_type='Bearer',
                             access_token=kwargs.get('token'))
            self.auth_expires = datetime(2099, 1, 1, tzinfo=pytz.utc)

        self.user_agent = 'das-client/{}'.format(version_string)

        self.logger = logging.getLogger(self.__class__.__name__)

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

        response = requests.get(self._das_url(path), headers=headers, params=kwargs.get('params'))
        if response.ok:
            if kwargs.get('return_response', False):
                return response
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

        def time_converter(t):
            if isinstance(t, datetime):
                return t.__str__()

        body = json.dumps(payload, default=time_converter)

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

        self.logger.error('provider_key: %s, path: %s\n\tBad result from das service. Message: %s',
            self.provider_key, path, response.text if response else '<no response')
        raise DasClientException('Failed to post to DAS web service.')

    def _post_form(self, path, body=None, files=None):

        headers = {'User-Agent': self.user_agent}
        headers.update(self.auth_headers())

        body = body or {}
        response = requests.post(self._das_url(path), data=body, headers=headers, files=files)
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

        self.logger.error('provider_key: %s, path: %s\n\tBad result from das service. Message: %s',
            self.provider_key, path, response.text)
        raise DasClientException('Failed to post to DAS web service.')

    def post_event_photo(self, event_id, image):

        raise ValueError('post_event_photo is no longer valid.')
        photos_path = 'activity/event/' + str(event_id) + '/photos/'

        with open(image, "rb") as image_file:
            files = {'image': image_file}
            return self._post_form(photos_path, files=files)

    def post_event_file(self, event_id, filepath=None, comment=''):

        documents_path = 'activity/event/' + str(event_id) + '/files/'

        with open(filepath, "rb") as f:
            files = {'filecontent.file': f}
            return self._post_form(documents_path, body={'comment': comment}, files=files)

    def post_event_note(self, event_id, note=None):

        notes_path = 'activity/event/' + str(event_id) + '/notes/'
        return self._post(notes_path, payload={'text': note})

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
        self.logger.debug('Posting source for manufacturer_id: %s', source.get('manufacturer_id'))
        return self._post('sources', payload=source)

    def _clean_observation(self, observation):
        if hasattr(observation['recorded_at'], 'isoformat'):
            observation['recorded_at'] = observation['recorded_at'].isoformat()
        return observation

    def _clean_event(self, event):
        return event

    def post_radio_observation(self, observation):
        # Clean-up data before posting
        observation['recorded_at'] = observation['recorded_at'].isoformat()
        self.logger.debug('Posting observation: %s', observation)
        result = self._post('sensors/dasradioagent/{}/status'.format(self.provider_key), payload=observation)
        self.logger.debug('Result of post is: %s', result)
        return result

    def post_radio_heartbeat(self, data):
        self.logger.debug('Posting heartbeat: %s', data)
        result = self._post('sensors/dasradioagent/{}/status'.format(self.provider_key), payload=data)
        self.logger.debug('Result of heartbeat post is: %s', result)

    def post_observation(self, observation):
        """
        Post a new observation, or a list of observations.
        """
        if isinstance(observation, (list, set)):
            payload = [self._clean_observation(o) for o in observation]
        else:
            payload = self._clean_observation(observation)

        self.logger.debug('Posting observation: %s', payload)
        return self._post('observations', payload=payload)

    def post_sensor_observation(self, observation, sensor_type='generic'):
        # Clean-up data before posting
        # observation['recorded_at'] = observation['recorded_at'].isoformat()
        self.logger.debug('Posting observation: %s', observation)
        result = self._post('sensors/{}/{}/status'.format(sensor_type, self.provider_key), payload=observation)
        self.logger.debug('Result of post is: %s', result)
        return result

    def post_report(self, data):
        payload = self._clean_event(data)
        self.logger.debug('Posting report: %s', payload)
        result = self._post('activity/events', payload=payload)
        self.logger.debug('Result of report post is: %s', result)
        return result

    def post_event(self, event):
        """
        Post a new Event.
        """
        return self.post_report(event)

    def get_events(self, **kwargs):

        params = dict((k, v) for k, v in kwargs.items() if k in ('state', 'page_size', 'page', 'event_type', 'filter'))

        events = self._get('activity/events', params=params)

        while True:
            if events and events.get('results'):
                for result in events['results']:
                    yield result
            if events['next']:
                url, params = split_link(events['next'])
                events = self._get('activity/events', params=params)
            else:
                break

    def get_events_export(self, filter=None):
        params = None
        if filter:
            params = {
                'filter': filter}

        response = self._get('activity/events/export/', params=params, return_response=True)
        return response

    def pulse(self, message=None):
        """
        Convenience method for getting status of the DAS api.
        :param message: 
        :return: 
        """
        return self._get('status')

    def get_subject_tracks(self, subject_id='', start=None, end=None):
        """
        Get the latest tracks for the Subject having the given subject_id.
        """
        p = {}
        if start is not None and isinstance(start, datetime):
            p['since'] = start.isoformat()
        if end is not None and isinstance(end, datetime):
            p['until'] = end.isoformat()

        return self._get(path='subject/{0}/tracks'.format(subject_id), params=p)

    def get_subject_trackingdata(self, subject_id='', include_inactive=True, start=None, end=None,
                                 out_format='json', filter_flag=0, current_status=False):
        p = {}
        if start is not None and isinstance(start, datetime):
            p['after_date'] = start.isoformat()
        if end is not None and isinstance(end, datetime):
            p['before_date'] = end.isoformat()
        p['subject_id'] = subject_id
        p['include_inactive'] = include_inactive
        p['format'] = out_format  # should be 'json' or 'csv'
        p['filter'] = filter_flag
        p['current_status'] = current_status
        return self._get(path='trackingdata/export', params=p)

    def get_subject_observations(self, subject_id='', start=None, end=None,
                                 filter_flag=0, include_details=True, page_size=1000):
        p = {}
        if start is not None and isinstance(start, datetime):
            p['since'] = start.isoformat()
        if end is not None and isinstance(end, datetime):
            p['until'] = end.isoformat()
        p['subject_id'] = subject_id
        p['filter'] = filter_flag
        p['include_details'] = include_details
        p['page_size'] = page_size  # current limit
        
        results = self._get(path='observations', params=p)

        while True:
            if results and results.get('results'):
                for r in results['results']:
                    yield r
                    
            if results['next']:
                url, params = split_link(results['next'])
                p['page'] = params['page']
                results = self._get(path='observations', params=p)
            else:
                break

    def get_subjects(self, subject_group_id='', include_inactive=False):
        """
        Get the list of subjects to whom the user has access.
        :return: 
        """
        p = dict()
        p['subject_group'] = subject_group_id
        p['include_inactive'] = include_inactive

        return self._get('subjects', params=p)

    def get_subject(self, subject_id=''):
        """
        get the subject given the subject id
        :param subject_id: the UUID for the subject
        :return:
        """
        return self._get(path='subject/{0}'.format(subject_id))

    def get_subjectgroups(self, include_inactive=False):
        p = dict()
        p['include_inactive'] = include_inactive
        return self._get('subjectgroups', params=p)

    def get_sources(self):
        return self._get('sources')

    def get_users(self):
        return self._get('users')


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
    MY_REALTIME_URL = 'https://demo.pamdas.org/socket.io'

    dc = DasClient(username=MY_USERNAME, password=MY_PASSWORD,
                   service_root=MY_SERVICE_ROOT,
                   token_url=MY_TOKEN_URL,
                   provider_key=MY_PROVIDER_KEY,
                   client_id=MY_CLIENT_ID,
                   realtime_url=MY_REALTIME_URL,
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


    # Example 4: Create an Event and attach a photo to it.
    event_data = {'priority': 0,
             'event_type': 'other',
             'message': 'A new event, with a photo.'}

    new_event = dc.post_event(event_data)
    response = dc.post_event_file(new_event['id'], 'somefilename.jpg', comment='This is my photo.')
