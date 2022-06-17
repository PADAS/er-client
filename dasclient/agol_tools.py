import logging
import urllib
import tempfile
import json
import copy
import concurrent.futures
from datetime import datetime, timedelta, timezone
import dateparser
from arcgis.gis import GIS
from arcgis.features import FeatureLayer, Feature
from arcgis.geometry import Point, Polyline
from .dasclient import DasClient
from .version import __version__
from .schemas import EREvent, ERLocation

class AgolTools(object):

    UPDATE_TIME_PADDING = 24*60  # minutes

    event_types = None
    temp_dir = None
    ER_TO_ESRI_FIELD_TYPE = {
        'string': 'esriFieldTypeString',
        'number': 'esriFieldTypeDouble',
        'default': 'esriFieldTypeString'
    }

    DISALLOWED_FILE_EXTENSIONS = ["jfif"]

    def __init__(self, er_token, er_service_root, esri_url, esri_username, esri_password):
        """
        Initialized an AgolTools object.  Establishes sessions to both ER
        and ArcGIS Online

        :param er_token: Token for connecting to EarthRanger
        :param er_service_root: URL to the API service root of EarthRanger
        :param esri_url: URL for logging in to ArcGIS Online
        :param esri_username: Username for ArcGIS Online
        :param esri_password: Password for ArcGIS Online
        :return: None
        """

        self.logger = logging.getLogger(self.__class__.__name__)

        self.das_client = DasClient(
            token=er_token, service_root=er_service_root)
        self.logger.info(f"Logged in to ER: {er_service_root}")

        self.gis = GIS(esri_url, esri_username, esri_password)
        self.logger.info("Logged in to AGOL as " +
                         str(self.gis.properties.user.username))

        return

    def _clean_field_alias(self, alias):
        """
        Exists as an interface to allow calling functions to modify the handling
        of a field alias.

        :param field: Field alias to clean
        :return: Clean field alias
        """
        return alias

    def _clean_field_value(self, value):
        """
        Exists as an interface to allow callers to modify the handling of a
        field's value.

        :param value: Field value to clean
        :return: Clean field value
        """
        return value

    def _clean_field_name(self, field):
        """
        Cleans a field name to make sure that Esri doesn't choke on it.
        Currently, it just replaces -'s with _'s, but there could be other
        characters discovered in the future.

        :param field: Field name to clean
        :return: Clean field name
        """
        field = field.replace("-", "_")
        field = field.replace(".", "_")
        field = field.replace(":", "_")
        return field

    def _field_already_exists(self, field, esri_layer, additional_fields):
        """
        Helper method to checks if a field already exists in either Esri or in
        the list of fields we're about to submit

        :param field: Field to check
        :param esri_layer: AGO layer to look for that field name
        :param additional_fields: Additional list to check for the field.  Each entry is of the format [name, type].
        :return: Whether or not the field name is already in either AGO or the passed-in list
        """
        for esri_field in esri_layer.properties.fields:
            if(esri_field.name.lower() == field.lower()):
                return True
        for new_field in additional_fields:
            if(new_field[0].lower() == field.lower()):
                return True
        return False

    def _ensure_attributes_in_layer(self, esri_layer, fields):
        """
        Makes sure that a list of attributes is already in an AGO layer.  If one
        is missing, it's created.

        :param esri_layer: AGO layer to check
        :param fields: Fields to check or add to the layer
        :return: None
        """
        new_fields = []
        for field in fields:
            field_name = self._clean_field_name(field['name'])
            if(not(self._field_already_exists(field_name, esri_layer, new_fields))):
                new_fields.append([field['name'], field['type'], field['alias']])

        if(not new_fields):
            self.logger.info("Fields already exist in layer")
        else:
            self._add_fields_to_layer(new_fields, esri_layer)

    def _get_existing_esri_points(self, points_layer, oldest_date, er_subject_id=None):
        """
        Grabs existing Esri track points from AGOL.

        :param points_layer: AGO layer to check
        :param oldest_date: Start date for date range
        :param er_subject_id: ER subject ID for which to grab points (optional)
        :return: None
        """

        query = "EditDate > '" + \
            oldest_date.strftime("%Y-%m-%d %H:%M:%S") + "'"

        if(er_subject_id != None):
            query += f" and ER_SUBJECT_ID = '{er_subject_id}'"

        try:
            existing = points_layer.query(where=query)
        except Exception as e:
            self.logger.error(f'Error when running query {query}: {e}')
            raise e

        existing_ids = {}
        for event in existing:
            existing_ids[str(event.attributes['ER_OBSERVATION_ID'])] = [
                event.attributes['OBJECTID'], event.attributes['EditDate']]
        return existing_ids

    def _get_existing_esri_events(self, events_layer, oldest_date, count_only = False):
        """
        Loads the existing EarthRanger reports contained within an AGO layer.
        EarthRanger reports are determined by the field ER_REPORT_NUMBER not
        being blank.

        :param esri_layer: AGO layer to query
        :return: Dictionary with keys = ER serial number and value = AGO object ID
        """
        query = "ER_REPORT_NUMBER<>''"
        if(oldest_date):
            query += " and EditDate > '" + \
                oldest_date.strftime("%Y-%m-%d %H:%M:%S") + "'"

        try:
            existing = events_layer.query(where=query, return_count_only=count_only)
        except Exception as e:
            self.logger.error(f'Error when running query {query}: {e}')
            if("'Invalid field: ER_REPORT_NUMBER' parameter is invalid" in str(e)):
                return {}
            raise e

        if(count_only):
            return existing

        existing_ids = {}
        for event in existing:
            existing_ids[str(event.attributes['ER_REPORT_NUMBER'])] = [
                event.attributes['OBJECTID'], event.attributes['EditDate']]
        return existing_ids

    def _get_existing_esri_tracks(self, esri_layer):
        """
        Loads the existing EarthRanger tracks contained within an AGO layer.
        EarthRanger tracks are determined by the field ER_ID not being blank.

        :param esri_layer: AGO layer to query
        :return: Dictionary with keys = ER subject ID and value = AGO object ID
        """
        existing = esri_layer.query(where="'ER_ID'<>''")
        existing_ids = {}
        for event in existing:
            existing_ids[event.attributes['ER_ID']
                         ] = event.attributes['OBJECTID']
        return existing_ids

    def __get_value_map_from_prop_def(self, schema_defs, key):
        """
        Helper method to find a schema definition map to use for mapping field
        values to strings

        :param schema_defs: The schema definition for the field
        :param key: The field to look for
        :return: A map of key/value pairs for input/output field values, if one
            exists within the schema definition.  An empty dictionary is
            returned otherwise.
        """
        value_map = {}
        for schema_def in schema_defs:
            for item in schema_def.get('items', []):
                if(('key' in item) and (item['key'] == key)):
                    if('titleMap' in item):
                        for map_item in item['titleMap']:
                            value_map[map_item['value']] = map_item['name']
                        return value_map
        return {}

    def _get_er_field_definitions(self):
        """
        Loads information about ER schemas into class variable event_schemas
        """
        self.event_schemas = {}
        event_types = self.das_client.get_event_types(include_inactive = True)
        for event_type in event_types:
            schema = self.das_client.get_event_schema(event_type['value'])
            field_defs = {}
            props = schema['schema']['properties']
            for prop_name in props:
                prop = props[prop_name]
                field_defs[prop_name] = prop
                if('key' in prop):
                    field_defs[prop_name]['value_map'] = self.__get_value_map_from_prop_def(
                        schema['definition'], prop_name)
                elif('enumNames' in field_defs[prop_name]):
                    field_defs[prop_name]['value_map'] = field_defs[prop_name].pop('enumNames')

            self.event_schemas[event_type['value']] = {
                'name': event_type['display'],
                'schema': field_defs
            }

    def _add_fields_to_layer(self, fields, esri_layer):
        """
        Adds a list of fields to an AGO layer.  Right now we create all fields
        as esriFieldTypeString fields.  This is something to improve in the
        future.

        :param fields: List of field names descriptors.  Each is a 3-element array of field name, Esri field type and (optionally) field alias
        :return: None
        """
        new_fields = []
        for field in fields:
            new_field = {'name': self._clean_field_name(
                field[0]), 'type': field[1]}

            if(len(field) == 3):
                new_field['alias'] = self._clean_field_alias(field[2])

            new_fields.append(new_field)

        result = esri_layer.manager.add_to_definition({'fields': new_fields})
        if(result['success'] != True):
            raise Exception(f"Error when creating fields: {result}")
        return

    def _chunk(self, lst, chunk_size):
        """
        Simple helper method to chunk a list into pieces

        :param lst: List to chunk
        :param chunk_size: How large of chunks to return
        :return: Iterator over the chunks
        """
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    def _upsert_features(self, add_features, update_features, esri_layer, chunk_size=5):
        """
        Adds or updates a list of features in an AGO layer

        :param add_features: List of features to add (as either Esri Feature objects or similar dictionaries)
        :return: None
        """
        added = self._add_features(add_features, esri_layer, chunk_size)
        updated = self._update_features(
            update_features, esri_layer, chunk_size)
        return (added, updated)

    def _add_features(self, add_features, esri_layer, chunk_size=5):
        """
        Adds features to an Esri layer

        :param add_features: A list of features to create
        :param esri_layer: The feature layer to add to
        :param chunk_size: How many features to add at a time (particularly
            import when updating large line features)
        :return: Number of added features
        """
        added = 0
        sent_count = 0
        for chunk in self._chunk(add_features, chunk_size):
            self.logger.info(f"Sending features {sent_count+1}-{sent_count + len(chunk)} of {len(add_features)} to Esri")
            sent_count += len(chunk)
            results = esri_layer.edit_features(adds=chunk)
            for result in results['addResults']:
                if(result['success'] != True):
                    self.logger.error(f"Error when creating feature: {result}")
                else:
                    added += 1

        return added

    def _update_features(self, update_features, esri_layer, chunk_size=100):
        """
        Updates features in an Esri layer

        :param update_features: A list of features to update, each of which
            contains an Esri global ID to identify which feature to update
        :param esri_layer: The feature layer to update within
        :param chunk_size: How many features to update at a time (particularly
            import when updating large line features)
        :return: Number of updated features
        """
        sent_count = 0
        updated = 0
        for chunk in self._chunk(update_features, chunk_size):
            self.logger.info(f"Updating features {sent_count+1}-{sent_count + len(chunk)} of {len(update_features)} to Esri")
            sent_count += len(chunk)
            results = esri_layer.edit_features(updates=chunk)
            for result in results['updateResults']:
                if(result['success'] != True):
                    self.logger.error(f"Error when updating feature: {result}")
                else:
                    updated += 1

        return updated

    def _replace_attachments_for_event(self, esri_layer, esri_object_id, event, event_files):
        """
        Replaces all of the attachments for an event in Esri with the versions
        attached to the event in EarthRanger.

        :param esri_layer: Esri layer to work with
        :param esri_object_id: Feature to update in Esri
        :param event: EarthRanger event to read attachments from
        :return: None
        """
        existing_attachments = esri_layer.attachments.get_list(esri_object_id)

        for existing_file in existing_attachments:
            self.logger.info(
                f"Removing attachment {existing_file['name']} from feature {esri_object_id}")
            esri_layer.attachments.delete(esri_object_id, existing_file['id'])

        i = 0
        for file in event_files:
            i += 1
            allowed_extension = True
            for ext in self.DISALLOWED_FILE_EXTENSIONS:
                if(file['filename'].endswith("." + ext)):
                    allowed_extension = False
                    break
            if(not allowed_extension):
                self.logger.warn(f"Filtering out file {file['filename']} - file type not allowed.")
                continue

            self.logger.info(f"Adding attachment {file['filename']} from ER event {event} to Esri feature {esri_object_id}.")

            tmppath = self.temp_dir.name + "/" + file['filename']
            result = self.das_client.get_file(file['url'])
            open(tmppath, 'wb').write(result.content)

            tries = 0
            while(tries < 3):
                tries += 1
                try:
                    esri_layer.attachments.add(esri_object_id, tmppath)
                    break
                except Exception as e:
                    if(tries == 3):
                        self.logger.error(f"Error when attaching {file['filename']} from ER event {event} to Esri feature {esri_object_id}: {e}")
                        raise e
                    else:
                        self.logger.warn(f'Error when processing attachment.  Retrying.')

    def _replace_attachments(self, esri_layer, oldest_date, event_files, threads = 10):
        """
        Replaces the attachments of Esri features with the attachments described
        by the event_files parameter.

        :param esri_layer: The AGO layer to work with.  Features are loaded
            which match the ER report numbers specified within the event_files
            paramter
        :param oldest_date: As far back to look for matching Esri features
        :param event_files: Describes the files to upload.  This is a dictionary of the form:
            {
                er_report_number: {
                    'url': URL to load the file from
                    'filename': Filename to give the file
                }
            }
        :return: None
        """
        existing_events = self._get_existing_esri_events(esri_layer, oldest_date)
        self.temp_dir = tempfile.TemporaryDirectory()

        futures = []
        i = 0
        for event in event_files.keys():
            self._replace_attachments_for_event(esri_layer, existing_events[event][0], event, event_files[event])
            i += 1
            if(i % 10 == 0):
                self.logger.info(f"{round(i/len(event_files) * 100)}% done with attachments")
        self.logger.info(f"Attachment sync complete")

        self.temp_dir.cleanup()

    def _get_tracks_to_send_for_subject(self, since, subject, existing_track):
        """
        Grabs the tracks for a subject to send over to Esri

        :param since: The start date of the track to grab
        :param subject: The ER subjet whose track to grab
        :param existing_track: The existing Esri track (if one exists, a new track
            is only returned if the subject has moved in the last UPDATE_TIME_PADDING minutes)
        :return: Two lists of tracks to be added and updated, respectively
        """
        if(('last_position_date' not in subject) or (subject['last_position_date'] == None)):
            return([],[])

        if(existing_track):
            last_position_date = dateparser.parse(
                subject['last_position_date'])
            cutoff = datetime.now(tz=timezone.utc) - \
                timedelta(minutes=self.UPDATE_TIME_PADDING)

            if(last_position_date < cutoff):
                self.logger.info(
                    f"Subject {subject['name']} not updated since {cutoff}... Skipping.")
                return([],[])

        results = self.das_client.get_subject_tracks(
            subject_id=subject['id'], start=since)
        self.logger.debug(
            f"Loaded {len(results['features'])} tracks from ER for subject {subject['name']}")

        features_to_add = []
        features_to_update = []
        for feature in results['features']:

            if(not('geometry' in feature.keys()) or (feature['geometry'] == None)
                    or not('coordinates' in feature['geometry'].keys()) or (feature['geometry']['coordinates'] == None)):
                continue

            self.logger.debug(
                f"Track for {subject['name']} contains {len(feature['geometry']['coordinates'])} points")

            polyline = {
                "geometry": {
                    "paths": [feature['geometry']['coordinates']],
                    "spatialReference": {"wkid": 4326}
                },
                "attributes": {
                    "ER_ID": subject['id'],
                    "SUBJECT_NAME": subject['name']
                }
            }

            if(existing_track):
                polyline['attributes']['OBJECTID'] = existing_track
                features_to_update.append(polyline)
            else:
                features_to_add.append(polyline)

        return (features_to_add, features_to_update)


    def upsert_tracks_from_er(self, esri_layer, since, threads = 10):
        """
        Queries all EarthRanger subjects from the active ER connection, grabs
        their tracks, and creates or updates polylines in AGO to match.  The
        EarthRanger subject ID is stored in AGO as a parameter ER_ID on each
        linestring.

        Right now, this method is very brute force: It either adds a track or
        replaces the whole track.  There are also not (yet) any parameters
        around track length, date ranges, which subjects to include, etc.

        :param esri_layer: The AGO layer to upsert
        :param since: The start date/time of the track to load
        :return: None
        """
        self._ensure_attributes_in_layer(esri_layer, [
            {'name': 'ER_ID', 'alias': 'ER ID', 'type': 'esriFieldTypeString'},
            {'name': 'SUBJECT_NAME', 'alias': 'Subject Name',
                'type': 'esriFieldTypeString'}
        ])

        subjects = self.das_client.get_subjects()
        existing_tracks = self._get_existing_esri_tracks(esri_layer)
        features_to_add = []
        features_to_update = []

        if(since == None):
            since = datetime.now(tz=timezone.utc) - timedelta(days=30)

        with concurrent.futures.ThreadPoolExecutor(max_workers = threads) as executor:
            futures = []
            for subject in subjects:
                futures.append(executor.submit(self._get_tracks_to_send_for_subject, since, subject, existing_tracks.get(subject['id'])))
            for future in concurrent.futures.as_completed(futures):
                (subject_features_to_add, subject_features_to_update) = future.result()
                features_to_add.extend(subject_features_to_add)
                features_to_update.extend(subject_features_to_update)

        if((len(features_to_add) > 0) or (len(features_to_update) > 0)):
            (added, updated) = self._upsert_features(
                features_to_add, features_to_update, esri_layer, 2)
            self.logger.info(
                f"Created {added} and updated {updated} track features in Esri")
        else:
            self.logger.info(f"No tracks to add or update")

    def _get_existing_esri_event_from_er_event(self, events_layer, er_serial_number):
        """
        Loads an existing EarthRanger reports contained within an AGO layer based
        on that report's serial number.

        :param esri_layer: AGO layer to query
        :param er_serial_number: EarthRanger report serial number to look for
        :return: AGO object ID of matching report or None if no match found
        """
        query = f"ER_REPORT_NUMBER='{er_serial_number}'"

        try:
            existing = events_layer.query(where=query)
        except Exception as e:
            self.logger.error(f'Error when running query {query}: {e}')
            raise e

        existing_ids = {}
        for event in existing:
            existing_ids[str(event.attributes['ER_REPORT_NUMBER'])] = [
                event.attributes['OBJECTID'], event.attributes['EditDate']]
        return existing_ids

    def upsert_events_from_er(self, esri_layer, oldest_date=None, include_attachments=True,
                              include_incidents=True, include_display_version_of_choices=True,
                              image_version=None):
        """
        Queries all EarthRanger events from the active ER connection and creates
        or updates points in AGO to match.  The EarthRanger report serial number
        is stored in AGO as the parameter ER_REPORT_NUMBER, which is used as the
        unique identifer.

        Right now, this method is very brute force: It either adds or replaces
        every event.  There are not (yet) any parameters around which events to
        include.  It also does not include attachments, notes, or take incidents
        into consideration.

        :param esri_layer: The AGO layer to upsert
        :param oldest_date: The start-date of the date range to synchronize
        :param include_attachments: Whether to synchronize event attachment files
        :param include_incidents: Whether to include ER incidents with a reference to its included reports
        :param image_version: If present, when transferring attachments, if an attachment
            is an image, include this version.  Likely values are one of:
            "original", "icon", "thumbnail", "large" or "xlarge".
        :return: None
        """

        base_attributes = [
            {'name': 'ER_REPORT_NUMBER', 'alias': 'ER Report Number',
                'type': 'esriFieldTypeInteger'},
            {'name': 'ER_REPORT_TIME', 'alias': 'ER Report Time',
                'type': 'esriFieldTypeDate'},
            {'name': 'ER_REPORT_TITLE', 'alias': 'ER Report Title',
                'type': 'esriFieldTypeString'},
            {'name': 'ER_REPORT_TYPE', 'alias': 'ER Report Type',
                'type': 'esriFieldTypeString'},
            {'name': 'REPORTED_BY', 'alias': 'Reported By',
                'type': 'esriFieldTypeString'},
            {'name': 'NOTES', 'alias': 'Notes',
                'type': 'esriFieldTypeString'},
            {'name': 'LATITUDE', 'alias': 'Latitude',
                'type': 'esriFieldTypeDouble'},
            {'name': 'LONGITUDE', 'alias': 'Longitude', 'type': 'esriFieldTypeDouble'}]

        if(include_incidents):
            base_attributes.append({'name': 'PARENT_INCIDENT',
                                    'alias': 'Parent Incident', 'type': 'esriFieldTypeString'})

        self._ensure_attributes_in_layer(esri_layer, base_attributes)

        if(oldest_date == None):
            oldest_date = datetime.now(tz=timezone.utc) - timedelta(days=30)

        self.logger.info(f"Loading events from ER")
        er_events = self.das_client.get_objects_multithreaded(object="activity/events", include_notes=True,
                                               include_related_events=include_incidents, include_files=True,
                                               include_updates=False, updated_since=oldest_date)

        self.logger.info("Loading ER event schemas")
        self._get_er_field_definitions()

        existing_events = self._get_existing_esri_events(esri_layer, oldest_date)
        self.logger.info(f"Loaded {len(existing_events)} existing events from Esri since {oldest_date}")

        empty_layer = False
        if(len(existing_events) == 0):
            event_count = self._get_existing_esri_events(esri_layer, None, True)
            self.logger.info(f"{event_count} events exist in total.")
            if(event_count == 0):
                empty_layer = True

        features_to_add = []
        features_to_update = []
        fields_to_add = []
        er_event_files = {}
        event_count = 0
        for event in er_events:
            event_count += 1

            if(event['event_type'] not in self.event_schemas):
                self.logger.warn(f"Event {event['serial_number']} is of type {event['event_type']}, which is not contained in schema downloaded from ER.  That event type might be part of a disabled event category.")
                continue

            if(str(event['serial_number']) in existing_events.keys()):
                esri_event = existing_events[str(event['serial_number'])]
                esri_update_time = esri_event[1]
                er_update_time = dateparser.parse(
                    event['updated_at']).timestamp() * 1000

                # If the Esri event was updated more recently than an hour after the ER one was, skip it
                if(esri_update_time > (er_update_time + self.UPDATE_TIME_PADDING * 60*1000)):
                    continue

            elif(not empty_layer):
                # If the ER event was not in the Esri event, it's either new or outside of the
                # time range of the Esri event load.
                er_create_time = dateparser.parse(event['created_at'])
                if(er_create_time < oldest_date):
                    # If the event was created before the load time, specifically look for it in Esri
                    additional_events = self._get_existing_esri_event_from_er_event(esri_layer, str(event['serial_number']))
                    if(additional_events):
                        self.logger.debug(f"ER event {event['serial_number']} was created before the date threshold and explicitly loaded from AGOL.")
                        existing_events.update(additional_events)
                    else:
                        self.logger.debug(f"ER event {event['serial_number']} was created before the date threshold but not found in AGOL.")

            if(not include_incidents and event.get('is_collection')):
                continue

            feature = {
                "attributes": {
                    'ER_REPORT_NUMBER': str(event['serial_number']),
                    'ER_REPORT_TIME': dateparser.parse(event['time']).timestamp()*1000
                }
            }

            if(event.get('location')):
                feature['geometry'] = Point(
                    {'y': event['location']['latitude'], 'x': event['location']['longitude'],
                     'spatialReference': {'wkid': 4326}})

                feature['attributes']['LATITUDE'] = str(
                    event['location']['latitude'])
                feature['attributes']['LONGITUDE'] = str(
                    event['location']['longitude'])

            if(event.get('reported_by')):
                feature['attributes']['REPORTED_BY'] = str(
                    event['reported_by'].get('name', ''))

            feature['attributes']['ER_REPORT_TYPE'] = self._clean_field_value(self.event_schemas[event['event_type']]['name'])

            if(event['title'] == None):
                feature['attributes']['ER_REPORT_TITLE'] = self._clean_field_value(
                    feature['attributes']['ER_REPORT_TYPE'])
            else:
                feature['attributes']['ER_REPORT_TITLE'] = self._clean_field_value(
                    str(event['title']))

            for field in event['event_details'].keys():

                if(field not in self.event_schemas[event['event_type']]['schema'].keys()):
                    self.logger.warning(
                        f"Additional data entry field {field} for event {event['serial_number']} not in event type model - skipping")
                    continue

                field_def = self.event_schemas[event['event_type']]['schema'][field]
                field_type = field_def.get('type', 'string')
                esri_type = self.ER_TO_ESRI_FIELD_TYPE.get(
                    field_type, self.ER_TO_ESRI_FIELD_TYPE['default'])
                field_name = self._clean_field_name(field + "_" + field_type)

                if not(self._field_already_exists(field_name, esri_layer, fields_to_add)):
                    fields_to_add.append(
                        [field_name, esri_type, field_def.get('title', field)])

                field_value = event['event_details'][field]
                if(type(field_value) != list):
                    field_value = [field_value]

                replaced_value = False
                raw_values = []
                if('value_map' in field_def.keys()):
                    for i in range(0, len(field_value)):
                        raw_values.append(field_value[i])
                        field_value[i] = field_def['value_map'].get(
                            field_value[i], field_value[i])
                        replaced_value = True

                # Clean and comma-separate the values
                for i in range(0, len(field_value)):
                    field_value[i] = self._clean_field_value(
                        str(field_value[i]))

                if((not replaced_value) or include_display_version_of_choices):
                    feature['attributes'][field_name] = ",".join(field_value)

                if(replaced_value):
                    value_field = field_name
                    if(include_display_version_of_choices):
                        value_field += "_key"
                    if not(self._field_already_exists(value_field, esri_layer, fields_to_add)):
                        new_field_name = field_def.get('title', field)
                        if(include_display_version_of_choices):
                            new_field_name += "_key"
                        fields_to_add.append([value_field, "esriFieldTypeString", new_field_name])

                    for i in range(0, len(raw_values)):
                        raw_values[i] = self._clean_field_value(str(raw_values[i]))
                    feature['attributes'][value_field] = ",".join(raw_values)

            if(include_incidents):
                for potential_parent in event.get('is_contained_in'):
                    if(potential_parent.get('type') == 'contains'):
                        feature['attributes']['PARENT_INCIDENT'] = potential_parent['related_event']['serial_number']
                        break

            if(str(event['serial_number']) in existing_events.keys()):
                feature['attributes']['OBJECTID'] = existing_events[str(
                    event['serial_number'])][0]
                features_to_update.append(feature)
            else:
                features_to_add.append(feature)

            if(event['files']):


                er_event_files[str(event['serial_number'])] = []
                for file in event['files']:

                    url = None
                    if(image_version and file.get('file_type') == 'image'):
                            url = file['images'].get(image_version)

                    if(not url):
                        url = file['url']

                    er_event_files[str(event['serial_number'])].append({
                        'url': url,
                        'filename': file['filename']
                    })

            if(event['notes']):
                note_vals = []
                for note in event['notes']:
                    note_vals.append(note['text'])
                feature['attributes']['NOTES'] = "; ".join(note_vals)

        self.logger.info(f"Processed {event_count} events from ER")
        if(not fields_to_add):
            self.logger.info(f"No new fields to add to the Esri layer.")
        else:
            new_fields = self._add_fields_to_layer(fields_to_add, esri_layer)
            self.logger.info(
                f"Added {len(fields_to_add)} new fields to the Esri layer")

        if((len(features_to_add) > 0) or (len(features_to_update) > 0)):
            (added, updated) = self._upsert_features(
                features_to_add, features_to_update, esri_layer, 50)
            self.logger.info(
                f"Created {added} and updated {updated} point features in Esri")
        else:
            self.logger.info(f"No event features to add or update")

        if(include_attachments):
            if(len(er_event_files) > 0):
                self._replace_attachments(
                    esri_layer, oldest_date, er_event_files)
            else:
                self.logger.info(f"No attachments to add")

    def _get_track_points_to_send_for_subject(self, esri_layer, oldest_date, subject):
        """
        Grabs the track points for a subject to send over to Esri

        :param esri_layer: The esri layer we're working with.  Points already in Esri will be skipped.
        :param oldest_date: The start date of the track points to grab
        :param subject: The ER subject to grab track points for
        :return: Two lists: The first contains track points to add, the second
            contains attribute columns to ensure exist in Esri before sending the data
        """
        if(not subject.get('tracks_available')):
            return([],[])

        last_position_date = subject.get('last_position_date')
        if(not last_position_date):
            return([],[])

        last_position_datetime = dateparser.parse(last_position_date)
        if(last_position_datetime < oldest_date):
            self.logger.info(f"No new track points for {subject['name']}")
            return([],[])

        existing_points = self._get_existing_esri_points(esri_layer, oldest_date, subject['id'])
        self.logger.info(
            f"Loaded {len(existing_points)} existing points from Esri for subject {subject['name']} (ER ID {subject['id']})")

        features_to_add = []
        attr_columns = {}
        point_count = 0

        er_observations = self.das_client.get_subject_observations(subject['id'], oldest_date, None, 0, True, 10000)
        for point in er_observations:
            point_count += 1
            if(point_count % 10000 ==0):
                self.logger.info(f"Loaded {point_count} points for subject {subject['name']} so far.")
            if(str(point['id']) in existing_points.keys()):
                continue

            feature = {
                "attributes": {
                    'ER_OBSERVATION_ID': point['id'],
                    'ER_SUBJECT_ID': subject['id'],
                    'SUBJECT_NAME': subject['name'],
                    'OBSERVATION_TIME': dateparser.parse(point['recorded_at']).timestamp()*1000
                }
            }

            if(point.get('location')):
                feature['geometry'] = Point(
                    {'y': point['location']['latitude'], 'x': point['location']['longitude'],
                     'spatialReference': {'wkid': 4326}})

                feature['attributes']['LATITUDE'] = str(
                    point['location']['latitude'])
                feature['attributes']['LONGITUDE'] = str(
                    point['location']['longitude'])

            details = point.get("observation_details")
            for k,v in details.items():
                feature['attributes'][k] = v
                col_name = "additional_" + k
                if(col_name not in attr_columns.keys()):
                    attr_columns[col_name] = {
                        'name': col_name,
                        'alias': k,
                        'type': 'esriFieldTypeString'}

            features_to_add.append(feature)

        self.logger.info(f"Processed {point_count} track points from ER for subject {subject['name']}")
        return (features_to_add, attr_columns)

    def upsert_track_points_from_er(self, esri_layer, oldest_date=None, threads = 1):
        """
        Updates an AGOL point layer, adding any missing observation points from
        EarthRanger.  Each point in the track layer represents a single
        observation object from EarthRanger.  Points that already exist in AGOL
        are skipped.

        :param esri_layer: The AGO layer to upsert
        :param oldest_date: The start-date of the date range to synchronize
        :return: None
        """

        base_attributes = [
            {'name': 'ER_OBSERVATION_ID', 'alias': 'Observation ID',
                'type': 'esriFieldTypeString'},
            {'name': 'SUBJECT_NAME', 'alias': 'Subject Name',
                'type': 'esriFieldTypeString'},
            {'name': 'OBSERVATION_TIME', 'alias': 'Observation Time',
                'type': 'esriFieldTypeDate'},
            {'name': 'ER_SUBJECT_ID', 'alias': 'Subject ID',
                'type': 'esriFieldTypeString'},
            {'name': 'LATITUDE', 'alias': 'Latitude',
                'type': 'esriFieldTypeDouble'},
            {'name': 'LONGITUDE', 'alias': 'Longitude', 'type': 'esriFieldTypeDouble'}]
        self._ensure_attributes_in_layer(esri_layer, base_attributes)

        if(oldest_date == None):
            oldest_date = datetime.now(tz=timezone.utc) - timedelta(days=30)

        subjects = self.das_client.get_subjects()
        self.logger.info(f"Loaded {len(subjects)} subjects to process.")

        features_to_add = []
        all_attr_columns = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers = threads) as executor:
            futures = []
            for subject in subjects:
                futures.append(executor.submit(self._get_track_points_to_send_for_subject, esri_layer, oldest_date, subject))
            for future in concurrent.futures.as_completed(futures):
                (subject_features_to_add, subject_attr_columns) = future.result()
                features_to_add.extend(subject_features_to_add)
                all_attr_columns.update(subject_attr_columns)

        if(len(features_to_add) > 0):

            if(len(all_attr_columns) > 0):
                self._ensure_attributes_in_layer(esri_layer, all_attr_columns.values())

            (added, updated) = self._upsert_features(features_to_add, [], esri_layer, 250)
            self.logger.info(f"Created {added} point features in Esri")


if __name__ == '__main__':
    pass
