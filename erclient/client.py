import concurrent.futures
import csv
import json
import logging
import math
import re
import time
from datetime import datetime, timedelta
from http import HTTPStatus

import httpx
import pytz
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .er_errors import (ERClientBadCredentials, ERClientBadRequest,
                        ERClientException, ERClientInternalError,
                        ERClientNotFound, ERClientPermissionDenied,
                        ERClientRateLimitExceeded, ERClientServiceUnreachable)
from .version import __version__

version_string = __version__


def linkify(url, params):
    p = ['='.join((str(x), str(y))) for x, y in params.items()]
    p = '&'.join(p)
    return '?'.join((url, p))


def split_link(url):
    url, qs = url.split('?')
    params = dict([p.split('=') for p in qs.split('&')])
    return (url, params)


class ERClient(object):
    """
    ERClient provides basic access to the EarthRanger server API. You will need the server hostname as well as credentials in the form of a username/password or access token.

    The boiler-plate code handles authentication, so you don't have to think about Oauth2 or refresh tokens.
    """

    def __init__(self, **kwargs):
        """
        Initialize an ERClient instance.

        :param service_root: The root of the ER API (Ex. https://sandbox.pamdas.org/api/v1.0)

        :param username: username
        :param password: password
        :param client_id: Auth client ID (Ex. er_web_client)
        :param token_url: The auth token url for ER (Ex. https://sandbox.pamdas.org/oauth2/token)

        or

        :param token: authorization token

        If posting to the sensors API, the default provider key
        :param provider_key: provider-key for posting observation data (Ex. xyz_provider)

        :param max_http_retries: number of retries, default is 5

        """

        self.auth = None
        self.auth_expires = pytz.utc.localize(datetime.min)
        self._http_session = None
        self.max_retries = kwargs.get('max_http_retries', 5)

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

        self._http_session = requests.Session()
        retries = Retry(total=5, backoff_factor=1.5, status_forcelist=[502])
        self._http_session.mount("http", HTTPAdapter(max_retries=retries))
        self._http_session.mount("https", HTTPAdapter(max_retries=retries))

    def _auth_is_valid(self):
        return self.auth_expires > pytz.utc.localize(datetime.utcnow())

    def auth_headers(self):

        if self.auth:
            if not self._auth_is_valid():
                if not self.refresh_token():
                    if not self.login():
                        raise ERClientException('Login failed.')
        else:
            if not self.login():
                raise ERClientException('Login failed.')

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
            self.auth_expires = pytz.utc.localize(
                datetime.utcnow()) + timedelta(seconds=expires_in)
            return True

        self.auth = None
        self.auth_expires = pytz.utc.localize(datetime.min)
        return False

    def _er_url(self, path):
        return '/'.join((self.service_root, path))

    def _get(self, path, stream=False, max_retries=5, seconds_between_attempts=5, **kwargs):
        headers = {'User-Agent': self.user_agent}

        headers.update(self.auth_headers())
        if (not path.startswith("http")):
            path = self._er_url(path)

        attempts = 0
        while (attempts <= max_retries):
            attempts += 1

            response = None
            if (self._http_session):
                response = self._http_session.get(path, headers=headers,
                                                  params=kwargs.get('params'), stream=stream)
            else:
                response = requests.get(path, headers=headers,
                                        params=kwargs.get('params'), stream=stream)

            if response.ok:
                if kwargs.get('return_response', False):
                    return response
                data = json.loads(response.text)
                if 'metadata' in data:
                    return data['metadata']
                elif 'data' in data:
                    return data['data']
                else:
                    return data

            if response.status_code == 404:  # not found
                self.logger.error(f"404 when calling {path}")
                raise ERClientNotFound()

            if response.status_code == 401:  # bad credentials
                try:
                    _ = json.loads(response.text)
                    reason = _['status']['detail']
                except:
                    reason = 'unknown reason'
                raise ERClientBadCredentials(reason)

            if response.status_code == 403:  # forbidden
                try:
                    _ = json.loads(response.text)
                    reason = _['status']['detail']
                except:
                    reason = 'unknown reason'
                raise ERClientPermissionDenied(reason)

            self.logger.warn(
                f"Fail attempt {attempts} of {max_retries+1}: {response.text}")
            if (attempts >= max_retries):
                raise ERClientException(
                    f"Failed to call ER web service at {response.url} after {attempts} tries. {response.status_code} {response.text}")
            time.sleep(seconds_between_attempts)

    def _call(self, path, payload, method, params=None):
        headers = {'Content-Type': 'application/json',
                   'User-Agent': self.user_agent}
        headers.update(self.auth_headers())

        def time_converter(t):
            if isinstance(t, datetime):
                return t.isoformat()

        body = json.dumps(payload, default=time_converter)

        fmap = None
        if (self._http_session):
            fmap = {'POST': self._http_session.post,
                    'PATCH': self._http_session.patch}
        else:
            fmap = {'POST': requests.post, 'PATCH': requests.patch}
        try:
            fn = fmap[method]
        except KeyError:
            self.logger.error('method must be one of...')
        else:
            response = fn(self._er_url(path), data=body,
                          headers=headers, params=params)

        if response and response.ok:
            res_json = response.json()
            if res_json and 'data' in res_json and res_json['data']:
                return res_json['data']
            else:
                return res_json

        if response.status_code == 404:  # not found
            self.logger.error(f"Could not load {path}")
            raise ERClientNotFound()

        try:
            _ = json.loads(response.text)
            reason = _['status']['detail']
        except:
            reason = 'unknown reason'

        if response.status_code == 403:  # forbidden
            raise ERClientPermissionDenied(reason)

        if response.status_code == 504 or response.status_code == 502:  # gateway timeout or bad gateway
            self.logger.error(f"ER service unavailable", extra=dict(provider_key=self.provider_key,
                                                                    service=self.service_root,
                                                                    path=path,
                                                                    status_code=response.status_code,
                                                                    reason=reason,
                                                                    text=response.text))
            raise ERClientServiceUnreachable(f"ER service unavailable")

        self.logger.error(f"ER returned bad response", extra=dict(provider_key=self.provider_key,
                                                                  service=self.service_root,
                                                                  path=path,
                                                                  status_code=response.status_code,
                                                                  reason=reason,
                                                                  text=response.text))
        message = f"provider_key: {self.provider_key}, service: {self.service_root}, path: {path},\n\t {response.status_code} from ER. Message: {reason} {response.text}"
        raise ERClientException(
            f"Failed to {fn} to ER web service. {message}")

    def _post(self, path, payload, params=None):
        return self._call(path, payload, "POST", params)

    def _patch(self, path, payload, params=None):
        return self._call(path, payload, "PATCH", params)

    def add_event_to_incident(self, event_id, incident_id):

        params = {
            'to_event_id': event_id,
            'type': 'contains'
        }

        result = self._post('activity/event/' +
                            incident_id + '/relationships', params)

    def remove_event_from_incident(self, event_id, incident_id, relationship_type='contains'):
        result = self._delete(
            f'activity/event/{incident_id}/relationship/{relationship_type}/{event_id}/')

    def _delete(self, path):

        headers = {'User-Agent': self.user_agent}
        headers.update(self.auth_headers())

        if (self._http_session):
            response = self._http_session.delete(
                self._er_url(path), headers=headers)
        else:
            response = requests.delete(self._er_url(path), headers=headers)

        if response.ok:
            return True

        if response.status_code == 404:  # not found
            self.logger.error(f"404 when calling {path}")
            raise ERClientNotFound()

        if response.status_code == 403:  # forbidden
            try:
                _ = json.loads(response.text)
                reason = _['status']['detail']
            except:
                reason = 'unknown reason'
            raise ERClientPermissionDenied(reason)

        raise ERClientException(
            f'Failed to delete: {response.status_code} {response.text}')

    def delete_event(self, event_id):
        self._delete('activity/event/' + event_id + '/')

    def delete_source(self, source_id):
        self._delete('source/' + source_id + '/')

    def delete_subject(self, subject_id):
        self._delete('subject/' + subject_id + '/')

    def delete_message(self, message_id):
        self._delete('messages/' + message_id + '/')

    def delete_patrol(self, patrol_id):
        self._delete('activity/patrols/' + patrol_id + '/')

    def _post_form(self, path, body=None, files=None):

        headers = {'User-Agent': self.user_agent}
        headers.update(self.auth_headers())

        body = body or {}
        response = requests.post(self._er_url(
            path), data=body, headers=headers, files=files)
        if response and response.ok:
            return json.loads(response.text)['data']

        if response.status_code == 404:  # not found
            raise ERClientNotFound()

        if response.status_code == 403:  # forbidden
            try:
                _ = json.loads(response.text)
                reason = _['status']['detail']
            except:
                reason = 'unknown reason'
            raise ERClientPermissionDenied(reason)

        self.logger.error('provider_key: %s, path: %s\n\tBad result from ER service. Message: %s',
                          self.provider_key, path, response.text)
        raise ERClientException('Failed to post to ER web service.')

    def post_eventprovider(self, eventprovider):
        self.logger.debug('Posting eventprovider: %s', eventprovider)
        result = self._post('activity/eventproviders/', payload=eventprovider)
        self.logger.debug('Result of eventprovider post is: %s', result)
        return result

    def post_eventsource(self, eventprovider_id, eventsource):
        self.logger.debug('Posting eventsource: %s', eventsource)
        result = self._post(
            f'activity/eventprovider/{eventprovider_id}/eventsources', payload=eventsource)
        self.logger.debug('Result of eventsource post is: %s', result)
        return result

    def post_event_photo(self, event_id, image):

        raise ValueError('post_event_photo is no longer valid.')
        photos_path = 'activity/event/' + str(event_id) + '/photos/'

        with open(image, "rb") as image_file:
            files = {'image': image_file}
            return self._post_form(photos_path, files=files)

    def post_camera_trap_report(self, camera_trap_payload, file=None):

        camera_trap_report_path = f'sensors/camera-trap/' + self.provider_key + '/status/'

        if file:
            files = {'filecontent.file': file}
            return self._post_form(camera_trap_report_path, body=camera_trap_payload, files=files)
        else:
            file_path = camera_trap_payload.get('file')

            with open(file_path, "rb") as f:
                files = {'filecontent.file': f}
            return self._post_form(camera_trap_report_path, body=camera_trap_payload, files=files)

    def delete_event_file(self, event_id, file_id):
        self._delete(f"activity/event/{event_id}/file/{file_id}")

    def delete_event_note(self, event_id, note_id):

        path = f"activity/event/{event_id}/note/{note_id}"
        self._delete(path)

    def post_event_file(self, event_id, filepath=None, comment=''):

        documents_path = 'activity/event/' + str(event_id) + '/files/'

        with open(filepath, "rb") as f:
            files = {'filecontent.file': f}
            return self._post_form(documents_path, body={'comment': comment}, files=files)

    def post_event_note(self, event_id, notes):

        created = []

        if (not isinstance(notes, list)):
            notes = [notes, ]

        for note in notes:
            notesRequest = {
                'event': event_id,
                'text': note
            }

            result = self._post('activity/event/' +
                                event_id + '/notes', notesRequest)
            created.append(result)

        return created

    def get_me(self):
        """
        Get details for the 'me', the current ER user.
        :return:
        """
        return self._get('user/me')

    def post_subject(self, subject):
        '''
        Post a subject payload to create a new subject.
        :param subject:
        :return:
        '''
        self.logger.debug(f"Posting subject {subject.get('name')}")
        return self._post('subjects', payload=subject)

    def post_source(self, source):
        '''
        Post a source payload to create a new source.
        :param source:
        :return:
        '''
        self.logger.debug('Posting source for manufacturer_id: %s',
                          source.get('manufacturer_id'))
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
        result = self._post(
            'sensors/dasradioagent/{}/status'.format(self.provider_key), payload=observation)
        self.logger.debug('Result of post is: %s', result)
        return result

    def post_radio_heartbeat(self, data):
        self.logger.debug('Posting heartbeat: %s', data)
        result = self._post(
            'sensors/dasradioagent/{}/status'.format(self.provider_key), payload=data)
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
            [self._clean_observation(o) for o in observation]
        else:
            self._clean_observation(observation)

        self.logger.debug('Posting observation: %s', observation)
        result = self._post(
            'sensors/{}/{}/status'.format(sensor_type, self.provider_key), payload=observation)
        self.logger.debug('Result of post is: %s', result)
        return result

    def post_patrol(self, data):
        payload = self._clean_event(data)
        self.logger.debug('Posting patrol: %s', payload)
        result = self._post('activity/patrols', payload=payload)
        self.logger.debug('Result of patrol post is: %s', result)
        return result

    def patch_event_type(self, event_type):
        self.logger.debug('Patching event type: %s', event_type)
        result = self._patch(
            f"activity/events/eventtypes/{event_type['id']}", payload=event_type)
        self.logger.debug('Result of event type patch is: %s', result)
        return result

    def post_event_type(self, event_type):
        self.logger.debug('Posting event type: %s', event_type)
        result = self._post('activity/events/eventtypes/', payload=event_type)
        self.logger.debug('Result of event type post is: %s', result)
        return result

    def post_report(self, data):
        payload = self._clean_event(data)
        self.logger.debug('Posting report: %s', payload)
        result = self._post('activity/events', payload=payload)
        self.logger.debug('Result of report post is: %s', result)
        return result

    def post_event_category(self, data):
        self.logger.debug('Posting event category: %s', data)
        result = self._post('activity/events/categories', payload=data)
        self.logger.debug('Result of report category post is: %s', result)
        return result

    def patch_event_category(self, data):
        self.logger.debug('Patching event category: %s', data)
        result = self._patch(
            f'activity/events/categories/{data["id"]}', payload=data)
        self.logger.debug('Result of report category patch is: %s', result)
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

            result = self._patch(
                f"activity/event/{event['id']}", payload=payload)

    def patch_event(self, event_id, payload):
        self.logger.debug('Patching event: %s', payload)
        result = self._patch('activity/event/' + event_id, payload=payload)
        self.logger.debug('Result of event patch is: %s', result)
        return result

    def get_file(self, url):
        return self._get(url, stream=True, return_response=True)

    def get_event_type(self, event_type_name):
        return self._get(f'activity/events/schema/eventtype/{event_type_name}')

    def get_event_categories(self, include_inactive=False):
        return self._get(f'activity/events/categories', params={"include_inactive": include_inactive})

    def get_messages(self):

        results = self._get(path='messages')

        while True:
            if results and results.get('results'):
                for r in results['results']:
                    yield r

            if results and results['next']:
                url, params = split_link(results['next'])
                # FixMe: p is not defined in this context
                p['page'] = params['page']
                results = self._get(path='messages')
            else:
                break

    def get_event_types(self, include_inactive=False, include_schema=False):
        return self._get('activity/events/eventtypes', params={"include_inactive": include_inactive, "include_schema": include_schema})

    def get_event_schema(self, event_type):
        return self._get(f'activity/events/schema/eventtype/{event_type}')

    def _get_objects_count(self, params):
        params = params.copy()
        params["page"] = 1
        params["page_size"] = 1
        events = self._get(params['object'], params=params)
        if events and events.get('count'):
            return events['count']
        return 0

    def get_objects(self, **kwargs):
        params = dict((k, v) for k, v in kwargs.items() if k not in ('page'))
        if (not params.get('object')):
            raise ValueError("Must specify object URL")

        self.logger.debug(f"Getting {params['object']}: ", params)
        count = 0
        results = self._get(params['object'], params=params)

        while True:
            if (not results):
                break

            if ('results' in results):
                for result in results['results']:
                    yield result
                    count += 1
                    if (('max_results' in params) and (count >= params['max_results'])):
                        return
                next = results.get('next')
                if (next and ('page' not in params)):
                    url = next
                    self.logger.debug('Getting more objects: ' + url)
                    results = self._get(url)
                else:
                    break
            elif (type(results) == list):
                for o in results:
                    yield o
                break
            else:
                yield results
                break

    def get_objects_multithreaded(self, **kwargs):
        threads = kwargs.get("threads", 5)
        params = dict((k, v) for k, v in kwargs.items() if k not in ('page'))
        if (not params.get('object')):
            raise ValueError("Must specify object URL")

        if (not params.get('page_size')):
            params['page_size'] = 100

        count = self._get_objects_count(params)

        if (count == 0):
            self.logger.debug(f"No {params['object']} to load from ER.")
            return []

        self.logger.debug(
            f"Loading {count} {params['object']} from ER with page size {params['page_size']} and {threads} threads")
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for page in range(1, math.ceil(count/params['page_size'])+1):
                temp_params = params.copy()
                temp_params["page"] = page
                futures.append(executor.submit(self._get, path=params['object'],
                                               max_retries=5, params=temp_params))

            for future in concurrent.futures.as_completed(futures):
                max_retries = kwargs.get("retries", 0)
                tries = 0
                while (True):
                    tries += 1
                    try:
                        result = future.result()
                        for e in result['results']:
                            yield e
                        break
                    except Exception as e:
                        if (tries > max_retries):
                            logging.error(
                                f"Error occurred loading events: {e}")
                            raise e
                        else:
                            logging.warning(
                                f"Attempt {tries} of {max_retries}: Error occurred loading events: {e}.")

    def get_events(self, **kwargs):
        params = dict((k, v) for k, v in kwargs.items() if k in
                      ('state', 'page_size', 'page', 'event_type', 'filter', 'include_notes',
                       'include_related_events', 'include_files', 'include_details', 'updated_since',
                       'include_updates', 'max_results', 'oldest_update_date', 'event_ids'))

        self.logger.debug('Getting events: ', params)
        events = self._get('activity/events', params=params)

        count = 0
        while True:
            if events and events.get('results'):
                for result in events['results']:
                    yield result
                    count += 1
                    if (('max_results' in params) and (count >= params['max_results'])):
                        return
            if events['next'] and ('page' not in params):
                url = events['next']
                url = re.sub('.*activity/events?',
                             'activity/events', events['next'])
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
                url = re.sub('.*activity/patrols?',
                             'activity/patrols', patrols['next'])
                self.logger.debug('Getting more patrols: ' + url)
                patrols = self._get(url)
            else:
                break

    def __result_to_dict(self, result):
        dict = {}
        for row in result:
            dict[row['id']] = row
        return dict

    def export_observations_to_csv(self, start_date, end_date, subject_groups, include_inactive, outputfile):

        subjects = {}
        if (subject_groups):
            for subject_group in subject_groups:
                more_subjects = self.__result_to_dict(self.get_objects_multithreaded(
                    object="subjects", subject_group=subject_group,
                    include_inactive=include_inactive))
                subjects.update(more_subjects)
        else:
            subject = self.__result_to_dict(
                self.get_objects_multithreaded(object="subjects"))

        obs = {}
        total = 0
        for subject_key, subject in sorted(subjects.items(), key=lambda item: item[1]['name']):
            obs[subject_key] = self.__result_to_dict(self.get_objects_multithreaded(
                object="observations", since=start_date.isoformat(), until=end_date.isoformat(),
                subject_id=subject_key, include_details="true"))
            num = len(obs[subject_key])
            total += num
            self.logger.info(
                f"Loaded {num} observations for {subject['name']}")
        self.logger.info(f"Loaded {total} observations for all subjects")

        csvfile = open(outputfile, 'w')
        csvwriter = csv.writer(csvfile, delimiter=',',
                               quotechar='"', quoting=csv.QUOTE_MINIMAL)

        additional_fields = []
        for subject_id, s_obs in obs.items():
            for ob in s_obs.values():
                for k in ob.get('observation_details', {}).keys():
                    if (k not in additional_fields):
                        additional_fields.append(k)

        headers = ["Subject", "Recorded At", "Lat", "Lon"]
        headers.extend(additional_fields)
        csvwriter.writerow(headers)

        for subject_id, s_obs in obs.items():
            subject = subjects[subject_id]
            for ob in s_obs.values():
                output = [subject['name'], ob['recorded_at'],
                          ob['location']['latitude'], ob['location']['longitude']]
                for k in additional_fields:
                    output.append(ob['observation_details'].get(k, ''))
                csvwriter.writerow(output)

    def get_events_export(self, filter=None):
        params = None
        if filter:
            params = {
                'filter': filter}

        response = self._get('activity/events/export/',
                             params=params, return_response=True)
        return response

    def pulse(self, message=None):
        """
        Convenience method for getting status of the ER api.
        :param message:
        :return:
        """
        return self._get('status')

    def get_subject_sources(self, subject_id):
        return self._get(path=f'subject/{subject_id}/sources')

    def get_subjectsources(self, subject_id):
        return self._get(path=f'subject/{subject_id}/subjectsources')

    def get_source_provider(self, provider_key):
        results = self.get_objects(object="sourceproviders")

        for r in results:
            if (r.get('provider_key') == provider_key):
                return r

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

    def get_subject_source_tracks(self, subject_id='', src_id='', start=None):
        """
        Get the latest tracks for the Subject having the given subject_id and a source ID.
        """
        p = {}
        if start:
            assert isinstance(start, datetime)
            p['since'] = start.isoformat()
        return self._get(path='subject/{0}/source/{1}/tracks'.format(subject_id, src_id), params=p)

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
        return self.get_observations(subject_id=subject_id, start=start, end=end,
                                     filter_flag=filter_flag, include_details=include_details, page_size=page_size)

    def get_source_observations(self, source_id, start=None, end=None,
                                filter_flag=0, include_details=True, page_size=10000):
        return self.get_observations(source_id=source_id, start=start, end=end,
                                     filter_flag=filter_flag, include_details=include_details, page_size=page_size)

    def get_observations(self, subject_id=None, source_id=None, start=None, end=None,
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

        p['filter'] = 'null' if filter_flag is None else filter_flag
        p['include_details'] = include_details
        p['page_size'] = page_size  # current limit

        results = self._get(path='observations', params=p)

        while True:
            if results and results.get('results'):
                for r in results['results']:
                    yield r

            if results and results['next']:
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

    def get_sources(self, page_size=100):
        """Return all sources"""
        params = dict(page_size=page_size)
        params = dict(page_size=page_size)
        sources = 'sources'
        results = self._get(path=sources, params=params)

        while True:
            if results and results.get('results'):
                for r in results['results']:
                    yield r

            if results and results['next']:
                _, qparam = split_link(results['next'])
                params['page'] = qparam['page']
                results = self._get(path=sources, params=params)
            else:
                break

    def get_users(self):
        return self._get('users')


class AsyncERClient(object):
    """
    AsyncERClient asynchronous usage of EarthRanger server API (asyncio).
    Notice: This client is experimental and only supports a reduced set of features.
    ToDo: Move common logic from async and syc clients into a common place such as a base class
    """

    DEFAULT_CONNECT_TIMEOUT_SECONDS = 3.1
    DEFAULT_DATA_TIMEOUT_SECONDS = 20
    DEFAULT_CONNECTION_RETRIES = 5

    def __init__(self, **kwargs):
        """
        Initialize an ERClient instance.

        :param service_root: The root of the ER API (Ex. https://sandbox.pamdas.org/api/v1.0)

        :param username: username
        :param password: password
        :param client_id: Auth client ID (Ex. er_web_client)
        :param token_url: The auth token url for ER (Ex. https://sandbox.pamdas.org/oauth2/token)

        or

        :param token: authorization token

        If posting to the sensors API, the default provider key
        :param provider_key: provider-key for posting observation data (Ex. xyz_provider)

        :param max_http_retries: Number of retries on connection errors. default is 5
        :param connect_timeout [seconds]: Maximum amount of time to wait until a socket connection to the requested host is established. Default is 3.1
        :param data_timeout [seconds]:  Maximum duration to wait for a chunk of data to be sent or received. Default is 20

        """

        self.auth = None
        self.auth_expires = pytz.utc.localize(datetime.min)
        self._http_session = None
        self.max_retries = kwargs.get(
            'max_http_retries', self.DEFAULT_CONNECTION_RETRIES)

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

        # ToDo: rename the agent name to er-client, or should we keep it for backward compatibility?
        self.user_agent = f'das-client/{version_string}'
        self.logger = logging.getLogger(self.__class__.__name__)

        transport = httpx.AsyncHTTPTransport(retries=self.max_retries)
        connect_timeout = kwargs.get(
            'connect_timeout', self.DEFAULT_CONNECT_TIMEOUT_SECONDS)
        data_timeout = kwargs.get(
            'data_timeout', self.DEFAULT_DATA_TIMEOUT_SECONDS)
        timeout = httpx.Timeout(
            data_timeout, connect=connect_timeout, pool=connect_timeout)
        self._http_session = httpx.AsyncClient(
            transport=transport, timeout=timeout)

    async def close(self):
        await self._http_session.aclose()

    # Support using this client as an async context manager.
    async def __aenter__(self):
        await self._http_session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._http_session.__aexit__()

    async def post_sensor_observation(self, observation, sensor_type='generic'):
        """
        Post a new observation, or a list of observations.
        """
        observations_list = observation if isinstance(
            observation, (list, set)) else [observation]
        for observation in observations_list:
            self._clean_observation(observation)

        self.logger.debug('Posting observation: %s', observation)
        result = await self._post(
            f'sensors/{sensor_type}/{self.provider_key}/status', payload=observation
        )
        self.logger.debug('Result of post is: %s', result)
        return result

    async def post_report(self, data):
        payload = self._clean_event(data)
        self.logger.debug(f'Posting report: {payload}', )
        result = await self._post('activity/events', payload=payload)
        self.logger.debug(f'Result of report post is: {result}')
        return result

    async def patch_report(self, event_id, data):
        self.logger.debug('Patching event: %s', data)
        result = await self._patch('activity/event/' + event_id, payload=data)
        self.logger.debug('Result of event patch is: %s', result)
        return result

    async def get_events(self, **kwargs):
        """
        Returns an async generator to iterate over events.
        Optional kwargs passed as query params:
        filter: json string with filter criteria
                i.e: "date_range": {
                    "lower": "2023-11-14T06:00:00-06:00",
                    "upper": "2023-11-14T09:14:35-06:00",
                }
        sort_by, valid values are event_time, updated_at, created_at, serial_number (prefix with '-' for reverse order)
        * default is by '-sort_at' which is a special value representing reverse by updated_at.
        page_size: Change the page size. Default 100.
        batch_size: The generator returns observations in batches (list) instead of one by one. Default 0 (means no batching)
                    If both page_size and batch_size are specified, the page_size will be modified to match batch_size.
        """
        params = {**kwargs}
        batch_size = kwargs.get('batch_size', 0)
        if batch_size and kwargs.get('page_size'):
            params['page_size'] = batch_size
        if not params.get('page_size'):
            params['page_size'] = 100
        async for event in self._get_data(endpoint='activity/events', params=params, batch_size=batch_size):
            yield event

    async def get_observations(self, **kwargs):
        """
        Returns an async generator to iterate over observations.
        Optional kwargs passed as query params:
        subject_id: filter to a single subject.
        source_id: filter to a single source.
        start: get observations after this date (ISO8061 or datetime), include timezone
        end: get observations up to this date (ISO8061 or datetime), include timezone
        include_details: brings back the observation additional field. Default True.
        created_after.
        page_size: Change the page size. Default 100.
        batch_size: The generator returns observations in batches (list) instead of one by one. Default 0 (means no batching)
        """
        subject_id = kwargs.get('subject_id')
        source_id = kwargs.get('source_id')
        start = kwargs.get('start')
        end = kwargs.get('end')
        filter_flag = kwargs.get('filter_flag')
        include_details = kwargs.get('include_details', True)
        page_size = kwargs.get('page_size', 100)
        batch_size = kwargs.get('batch_size', 0)  # 0 means no batching
        params = {}
        if start:
            params['since'] = start.isoformat() if isinstance(
                start, datetime) else start
        if end:
            params['until'] = end.isoformat() if isinstance(
                end, datetime) else end
        if subject_id:
            params['subject_id'] = subject_id
        elif source_id:
            params['source_id'] = source_id

        params['filter'] = filter_flag or 'null'
        params['include_details'] = include_details
        params['page_size'] = page_size  # current limit
        if batch_size and page_size:
            params['page_size'] = batch_size
        async for observation in self._get_data(endpoint='observations', params=params, batch_size=batch_size):
            yield observation

    async def post_camera_trap_report(self, camera_trap_payload, file=None):
        camera_trap_report_path = f'sensors/camera-trap/{self.provider_key}/status/'

        if file:
            files = {'filecontent.file': file}
            return await self._post_form(camera_trap_report_path, body=camera_trap_payload, files=files)
        # Open the file
        file_path = camera_trap_payload.get('file')
        # ToDo: open the files using async (aiofiles)
        with open(file_path, 'rb') as f:
            files = {'filecontent.file': f}
            return await self._post_form(camera_trap_report_path, body=camera_trap_payload, files=files)

    async def post_report_attachment(self, report_id, file):
        report_attachments_endpoint = f'activity/event/{report_id}/files/'
        files = {'filecontent.file': file}
        return await self._post_form(report_attachments_endpoint, files=files)

    async def post_message(self, message, params=None):
        self.logger.debug(f'Posting message: {message}')
        return await self._post('messages', payload=message, params=params)

    def _clean_observation(self, observation):
        if hasattr(observation['recorded_at'], 'isoformat'):
            observation['recorded_at'] = observation['recorded_at'].isoformat()
        return observation

    def _clean_event(self, event):
        return event

    def _auth_is_valid(self):
        return self.auth_expires > pytz.utc.localize(datetime.utcnow())

    async def auth_headers(self):
        if self.auth:
            if not self._auth_is_valid():
                if not await self.refresh_token():
                    await self.login()
        else:
            await self.login()

        return {
            'Authorization': f'{self.auth["token_type"]} {self.auth["access_token"]}',
            'Accept-Type': 'application/json'
        }

    async def refresh_token(self):
        return await self._token_request(
            payload={
                'grant_type': 'refresh_token',
                'refresh_token': self.auth['refresh_token'],
                'client_id': self.client_id
            }
        )

    async def login(self):
        return await self._token_request(
            payload={
                'grant_type': 'password',
                'username': self.username,
                'password': self.password,
                'client_id': self.client_id
            }
        )

    async def get_me(self):
        return await self._get('user/me')

    async def _token_request(self, payload):
        response = await self._http_session.post(self.token_url, data=payload)

        if response.status_code != httpx.codes.OK:
            self.auth = None
            self.auth_expires = pytz.utc.localize(datetime.min)
            response.raise_for_status()

        self.auth = response.json()
        expires_in = int(self.auth['expires_in']) - 5 * 60
        self.auth_expires = pytz.utc.localize(datetime.utcnow()) + timedelta(seconds=expires_in)
        return True

    def _er_url(self, path):
        return '/'.join((self.service_root, path))

    async def _post_form(self, path, body=None, files=None):

        try:
            auth_headers = await self.auth_headers()
        except httpx.HTTPStatusError as e:
            self._handle_http_status_error(path, "POST", e)
        else:
            body = body or {}
            headers = {
                'User-Agent': self.user_agent,
                **auth_headers
            }
            try:
                response = await self._http_session.post(
                    self._er_url(path),
                    data=body,  # # payload is automatically encoded as form data
                    headers=headers,
                    files=files
                )
                response.raise_for_status()
            except httpx.RequestError as e:
                # Network errors, timeouts
                # ToDo: Check if we want a more granular error handling defining more specific exception classes
                reason = str(e)
                self.logger.error('Request to ER failed', extra=dict(provider_key=self.provider_key,
                                                                     service=self.service_root,
                                                                     path=path,
                                                                     status_code=None,
                                                                     reason=reason,
                                                                     text=""))
                raise ERClientException(f'Request to ER failed: {reason}')
            except httpx.HTTPStatusError as e:
                self._handle_http_status_error(path, "POST", e)
            else:  # Parse the response
                json_response = response.json()
                return json_response.get('data', json_response)

    async def _get_data(self, endpoint, params, batch_size=0):
        if "page" not in params:  # Use cursor paginator unless the user has specified a page
            params["use_cursor"] = "true"
        if batch_size > params.get("page_size", 0):
            params["page_size"] = batch_size
        response = await self._get(endpoint, params=params)
        while results := response.get('results'):
            if batch_size > 0:
                for batch in self._get_batches(results, batch_size):
                    yield batch
            else:
                for obj in results:
                    yield obj

            # Deal with pagination
            if response.get('next') and 'page' not in params:
                url, query_params = split_link(response['next'])
                # Try to discover the pagination method
                if "page" in query_params:
                    new_params = {**params, 'page': query_params['page']}
                elif "cursor" in query_params:
                    new_params = {**params, 'cursor': query_params['cursor']}
                elif "offset" in query_params:
                    new_params = {**params, 'offset': query_params['offset']}
                else:  # Unknown pagination method
                    break
                response = await self._get(endpoint, params=new_params)
            else:
                break

    async def _get(self, path, params=None):
        return await self._call(path=path, payload=None, method="GET", params=params)

    async def _post(self, path, payload, params=None):
        return await self._call(path, payload, "POST", params)

    async def _patch(self, path, payload, params=None):
        return await self._call(path, payload, "PATCH", params)

    async def _call(self, path, payload, method, params=None):
        try:
            auth_headers = await self.auth_headers()
        except httpx.HTTPStatusError as e:
            self._handle_http_status_error(path, method, e)
        else:
            params = params or {}
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': self.user_agent,
                **auth_headers
            }
            try:
                response = await self._http_session.request(
                    method,
                    self._er_url(path),
                    json=payload if method in ["POST", "PUT", "PATCH"] else None,  # payload is automatically encoded as json data
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
            except httpx.RequestError as e:
                # Network errors, timeouts
                # ToDo: Check if we want a more granular error handling defining more specific exception classes
                reason = str(e)
                self.logger.error('Request to ER failed', extra=dict(provider_key=self.provider_key,
                                                                     service=self.service_root,
                                                                     path=path,
                                                                     status_code=None,
                                                                     reason=reason,
                                                                     text=""))
                raise ERClientException(f'Request to ER failed: {reason}')
            except httpx.HTTPStatusError as e:
                self._handle_http_status_error(path, method, e)
            else:  # Parse the response
                json_response = response.json()
                return json_response.get('data', json_response)

    def _get_batches(self, data, batch_size):
        for i in range(0, len(data), batch_size):
            yield data[i:i + batch_size]

    def _handle_http_status_error(self, path, method, e):
        """Handles httpx.HTTPStatusError exceptions."""
        status_name = HTTPStatus(e.response.status_code).phrase
        error_details = f"ER {status_name} ON {method} {self.service_root}/{path}."
        error_details_log = f"{error_details}. Response Body: {e.response.text}"
        self.logger.exception(error_details_log)

        exception_map = {
            httpx.codes.UNAUTHORIZED: ERClientBadCredentials,
            httpx.codes.FORBIDDEN: ERClientPermissionDenied,
            httpx.codes.NOT_FOUND: ERClientNotFound,
            httpx.codes.BAD_REQUEST: ERClientBadRequest,
            httpx.codes.INTERNAL_SERVER_ERROR: ERClientInternalError,
            httpx.codes.SERVICE_UNAVAILABLE: ERClientServiceUnreachable,
            httpx.codes.BAD_GATEWAY: ERClientServiceUnreachable,
            httpx.codes.GATEWAY_TIMEOUT: ERClientServiceUnreachable,
            httpx.codes.TOO_MANY_REQUESTS: ERClientRateLimitExceeded,
            httpx.codes.CONFLICT: ERClientRateLimitExceeded  # Only one observation per second per source is allowed
        }

        if e.response.status_code in exception_map:
            raise exception_map[e.response.status_code](
                message=error_details,
                status_code=e.response.status_code,
                response_body=e.response.text
            )

        raise ERClientException(
            message=error_details,
            status_code=e.response.status_code,
            response_body=e.response.text
        )
