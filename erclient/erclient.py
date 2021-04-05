from datetime import datetime, timedelta
import urllib.parse
import pytz
import logging
import re
import dateparser
import requests
import io
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

    def _get(self, path, stream=False, **kwargs):
        headers = {'User-Agent': self.user_agent}

        headers.update(self.auth_headers())
        if(not path.startswith("http")):
            path = self._das_url(path)

        response = requests.get(path, headers=headers, params=kwargs.get('params'), stream = stream)
        if response.ok:
            if kwargs.get('return_response', False):
                return response
            data = json.loads(response.text)
            if 'metadata' in data:
                return data['metadata']
            return data['data']

        if response.status_code == 404:  # not found
            raise DasClientNotFound()

        if response.status_code == 403:  # forbidden
            try:
                _ = json.loads(response.text)
                reason = _['status']['detail']
            except:
                reason = 'unknown reason'
            raise DasClientPermissionDenied(reason)

        self.logger.debug("Fail: " + response.text)
        raise DasClientException(f'Failed to call DAS web service. {response.status_code} {response.text}')


    def _call(self, path, payload, method):
        headers = {'Content-Type': 'application/json',
                   'User-Agent': self.user_agent}
        headers.update(self.auth_headers())

        def time_converter(t):
            if isinstance(t, datetime):
                return t.isoformat()

        body = json.dumps(payload, default=time_converter)

        fmap = {'POST': requests.post, 'PATCH': requests.patch}
        try:
            fn = fmap[method]
        except KeyError:
            self.logger.error('method must be one of...')
        else:
            response = fn(self._das_url(path), data=body, headers=headers)

        if response and response.ok:
            return response.json()['data']

        if response.status_code == 404:  # not found
            raise DasClientNotFound()

        try:
            _ = json.loads(response.text)
            reason = _['status']['detail']
        except:
            reason = 'unknown reason'

        if response.status_code == 403:  # forbidden
            raise DasClientPermissionDenied(reason)

        message = f"provider_key: {self.provider_key}, service: {self.service_root}, path: {path},\n\t {response.status_code} from ER. Message: {reason} {response.text}"
        self.logger.error(message)
        raise DasClientException(f"Failed to {fn} to DAS web service. {message}")

    def _post(self, path, payload):
        return self._call(path, payload, "POST")

    def _patch(self, path, payload):
        return self._call(path, payload, "PATCH")

    def add_event_to_incident(self, event_id, incident_id):

        params = {
            'to_event_id': event_id,
            'type': 'contains'
        }

        result = self._patch('activity/event/' + incident_id + '/relationships', params)

    def delete_event(self, event_id):
        headers = {'User-Agent': self.user_agent}
        headers.update(self.auth_headers())

        path = 'activity/event/' + event_id + '/'

        response = requests.delete(self._das_url(path), headers=headers)
        if response.ok:
            return True

        if response.status_code == 404:  # not found
            raise DasClientNotFound()

        if response.status_code == 403:  # forbidden
            try:
                _ = json.loads(response.text)
                reason = _['status']['detail']
            except:
                reason = 'unknown reason'
            raise DasClientPermissionDenied(reason)

        raise DasClientException('Failed to delete event.')

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

    def post_event_note(self, event_id, notes):

        created = []

        if(not isinstance(notes, list)):
            notes = [notes,]

        for note in notes:
            notesRequest = {
                'event': event_id,
                'text': note
            }

            result = self._post('activity/event/' + event_id + '/notes', notesRequest)
            created.append(result)

        return created

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
        """
        Post a new observation, or a list of observations.
        """
        if isinstance(observation, (list, set)):
            payload = [self._clean_observation(o) for o in observation]
        else:
            payload = self._clean_observation(observation)

        self.logger.debug('Posting observation: %s', observation)
        result = self._post('sensors/{}/{}/status'.format(sensor_type, self.provider_key), payload=observation)
        self.logger.debug('Result of post is: %s', result)
        return result

    def post_patrol(self, data):
        payload = self._clean_event(data)
        self.logger.debug('Posting patrol: %s', payload)
        result = self._post('activity/patrols', payload=payload)
        self.logger.debug('Result of patrol post is: %s', result)
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

    def add_events_to_patrol_segment(self, events, patrol_segment):
        for event in events:
            payload = {
                'id': event['id'],
                'patrol_segments': [
                    patrol_segment['id']
                ]
            }

            result = self._patch(f"activity/event/{event['id']}", payload=payload)

    def patch_event(self, event_id, payload):
        self.logger.debug('Patching event: %s', payload)
        result = self._patch('activity/event/' + event_id, payload=payload)
        self.logger.debug('Result of event patch is: %s', result)
        return result

    def get_file(self, url):
        return self._get(url, stream = True, return_response = True)

    def get_event_types(self):
        return self._get('activity/events/eventtypes')

    def get_event_schema(self, event_type):
        return self._get(f'activity/events/schema/eventtype/{event_type}')

    def get_events(self, **kwargs):
        params = dict((k, v) for k, v in kwargs.items() if k in
            ('state', 'page_size', 'page', 'event_type', 'filter', 'include_notes',
            'include_related_events','include_files', 'include_details',
            'include_updates', 'max_results', 'oldest_update_date'))
        self.logger.debug('Getting events: ', params)
        events = self._get('activity/events', params=params)

        count = 0
        while True:
            if events and events.get('results'):
                for result in events['results']:
                    if 'oldest_update_date' in params:
                        if(dateparser.parse(result['updated_at']) < params['oldest_update_date']):
                            return
                    yield result
                    count += 1
                    if(('max_results' in params) and (count >= params['max_results'])):
                        return
            if events['next']:
                url = events['next']
                url = re.sub('.*activity/events?','activity/events', events['next'])
                self.logger.debug('Getting more events: ' + url)
                events = self._get(url)
            else:
                break

    def get_patrols(self, **kwargs):
        params = dict((k, v) for k, v in kwargs.items() if k in
            ('state', 'page_size', 'page', 'event_type', 'filter'))
        self.logger.debug('Getting patrols: ', params)
        patrols = self._get('activity/patrols', params=params)

        while True:
            if patrols and patrols.get('results'):
                for result in patrols['results']:
                    yield result
            if patrols['next']:
                url = patrols['next']
                url = re.sub('.*activity/patrols?','activity/patrols', patrols['next'])
                self.logger.debug('Getting more patrols: ' + url)
                patrols = self._get(url)
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

    def get_subject_sources(self, subject_id):
        return self._get(path=f'subject/{subject_id}/sources')

    def get_source_provider(self, provider_key):
        providers = self._get('sourceproviders')

        if providers and providers.get('results'):
            for provider in providers['results']:
                if(provider['provider_key'] == provider_key):
                    return provider

        return None

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

    def get_subject_trackingdata(self, subject_id=None, subject_chronofile=None, include_inactive=True, start=None, end=None,
                                 out_format='json', filter_flag=0, current_status=False):
        p = {}
        if start is not None and isinstance(start, datetime):
            p['after_date'] = start.isoformat()
        if end is not None and isinstance(end, datetime):
            p['before_date'] = end.isoformat()
        if subject_id:
            p['subject_id'] = subject_id
        elif subject_chronofile:
            p['subject_chronofile'] = subject_chronofile
        else:
            raise ValueError('specify subject_id or subject_chronofile')
        p['include_inactive'] = include_inactive
        p['format'] = out_format  # should be 'json' or 'csv'
        p['filter'] = 'null' if filter_flag is None else filter_flag
        p['current_status'] = current_status
        return self._get(path='trackingdata/export', params=p)

    def get_subject_trackingmetadata(self, include_inactive=True, out_format='json'):
        p = {}
        p['include_inactive'] = include_inactive
        p['format'] = out_format  # should be 'json' or 'csv'
        return self._get(path='trackingmetadata/export', params=p)

    def get_subject_observations(self, subject_id, start=None, end=None,
                                 filter_flag=0, include_details=True, page_size=10000):
        return self._get_observations(subject_id=subject_id, start=start, end=end,
            filter_flag=filter_flag, include_details=include_details, page_size=page_size)

    def get_source_observations(self, source_id, start=None, end=None,
                                 filter_flag=0, include_details=True, page_size=10000):
        return self._get_observations(source_id=source_id, start=start, end=end,
            filter_flag=filter_flag, include_details=include_details, page_size=page_size)

    def _get_observations(self, subject_id=None, source_id=None, start=None, end=None,
                                 filter_flag=0, include_details=True, page_size=10000):
        p = {}
        if start is not None and isinstance(start, datetime):
            p['since'] = start.isoformat()
        if end is not None and isinstance(end, datetime):
            p['until'] = end.isoformat()
        if subject_id:
            p['subject_id'] = subject_id
        elif source_id:
            p['source_id'] = source_id
        else:
            raise ValueError('subject_id or source_id missing')
        p['filter'] = 'null' if filter_flag is None else filter_flag
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

    def get_subjects(self, subject_group_id=None, **kwargs):
        """
        Get the list of subjects to whom the user has access.
        :return:
        """
        params = dict((k, v) for k, v in kwargs.items() if k in
            ('subject_group', 'include_inactive'))
        
        return self._get('subjects', params=params)

    def get_subject(self, subject_id=''):
        """
        get the subject given the subject id
        :param subject_id: the UUID for the subject
        :return:
        """
        return self._get(path='subject/{0}'.format(subject_id))

    def get_source_by_id(self, id):
        """
        get the source by id
        :param id: source id
        :return:
        """
        return self._get(path='source/{0}'.format(id))

    def get_source_by_manufacturer_id(self, id):
        """
        get the source by manufacturer id or collar id
        :param id: the manufacturer id
        :return:
        """
        return self._get(path='source/{0}'.format(id))

    def get_subjectgroups(self, include_inactive=False,
                          include_hidden=True, isvisible=True, flat=True, group_name=None):
        """Get the list of visible subjectgroups including members.
         By default don't include inactive subjects
         to get all subject groups whether visible or not, call with include_hidden=True

        Args:
            include_inactive (bool, optional): set to True to include inactive subjects. Defaults to False.
            include_hidden (bool, optional): include subject groups that are not visible (isvisible flag is false). Defaults to True.
            isvisible (bool, optional): either include all visible groups, or only include not visible groups. Defaults to True.
            flat (bool, optional): unnest parent/child subjectgroups returning a flat list of subjectgroups
            group_name (string, optional): filter the subjectgroups to this name

        Returns:
            [type]: [description]
        """
        p = dict()
        p['include_inactive'] = include_inactive
        p['include_hidden'] = include_hidden
        p['isvisible'] = isvisible
        p['flat'] = flat
        p['group_name'] = group_name

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
