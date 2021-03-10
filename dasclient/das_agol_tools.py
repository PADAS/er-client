import logging
from arcgis.gis import GIS
from arcgis.features import FeatureLayer, Feature
from arcgis.geometry import Point, Polyline
from .dasclient import DasClient
from .version import __version__
from .schemas import EREvent, ERLocation

class das_agol_tools(object):

    event_types = None

    def __init__(self, er_token, er_service_root, esri_url, esri_username, esri_password):
        """
        Initialized a das_agol_tools object.  Establishes sessions to both ER
        and ArcGIS Online

        :param er_token: Token for connecting to EarthRanger
        :param er_service_root: URL to the API service root of EarthRanger
        :param esri_url: URL for logging in to ArcGIS Online
        :param esri_username: Username for ArcGIS Online
        :param esri_password: Password for ArcGIS Online
        :return: None
        """

        self.logger = logging.getLogger(self.__class__.__name__)

        self.das_client = DasClient(token=er_token, service_root=er_service_root)
        self.gis = GIS(esri_url, esri_username, esri_password)
        self.logger.info("Logged in to AGOL as " + str(self.gis.properties.user.username))

        return

    def _clean_field_name(self, field):
        """
        Cleans a field name to make sure that Esri doesn't choke on it.
        Currently, it just replaces -'s with _'s, but there could be other
        characters discovered in the future.

        :param field: Field name to clean
        :return: Clean field name
        """
        field = field.replace("-","_")
        return field

    def _field_already_exists(self, field, esri_layer, additional_fields):
        """
        Helper method to checks if a field already exists in either Esri or in
        the list of fields we're about to submit

        :param field: Field to check
        :param esri_layer: AGO layer to look for that field name
        :param additional_fields: Additional list to check for the field
        :return: Whether or not the field name is already in either AGO or the passed-in list
        """
        clean = self._clean_field_name(field)
        for esri_field in esri_layer.properties.fields:
            if(esri_field.name == clean):
                return True
        for new_field in additional_fields:
            if(new_field == clean):
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
            if(not(self._field_already_exists(field['name'], esri_layer, []))):
                new_fields.append(field)

        if(len(new_fields) == 0):
            self.logger.info("Fields already exist")
        else:
            self.logger.info("Creating fields")
            esri_layer.manager.add_to_definition({'fields': new_fields})

    def _get_existing_esri_events(self, events_layer):
        """
        Loads the existing EarthRanger reports contained within an AGO layer.
        EarthRanger reports are determined by the field ER_REPORT_NUMBER not
        being blank.

        :param esri_layer: AGO layer to query
        :return: Dictionary with keys = ER serial number and value = AGO object ID
        """
        existing = events_layer.query(where="ER_REPORT_NUMBER<>''")
        existing_ids = {}
        for event in existing:
            existing_ids[event.attributes['ER_REPORT_NUMBER']] = event.attributes['OBJECTID']
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
            existing_ids[event.attributes['ER_ID']] = event.attributes['OBJECTID']
        return existing_ids

    def _add_fields_to_layer(self, fields, esri_layer):
        """
        Adds a list of fields to an AGO layer.  Right now we create all fields
        as esriFieldTypeString fields.  This is something to improve in the
        future.

        :param fields: List of field names to add.
        :return: None
        """
        new_fields = []
        for field in fields:
            new_field = {'name': self._clean_field_name(field), 'type': 'esriFieldTypeString'}
            new_fields.append(new_field)
        result = esri_layer.manager.add_to_definition({'fields': new_fields})
        if(result['success'] != True):
            raise Exception(f"Error when creating fields: {result}")
        return

    def _upsert_features(self, add_features, update_features, esri_layer):
        """
        Adds or updates a list of features in an AGO layer

        :param add_features: List of features to add (as either Esri Feature objects or similar dictionaries)
        :return: None
        """
        results = esri_layer.edit_features(adds = add_features, updates = update_features)
        added = 0
        updated = 0
        for result in results['addResults']:
            if(result['success'] != True):
                self.logger.error(f"Error when creating feature: {result}")
            else:
                added += 1
        for result in results['updateResults']:
            if(result['success'] != True):
                self.logger.error(f"Error when updating feature: {result}")
            else:
                updated += 1
        return (results, added, updated)

    def upsert_tracks_from_er(self, esri_layer):
        """
        Queries all EarthRanger subjects from the active ER connection, grabs
        their tracks, and creates or updates polylines in AGO to match.  The
        EarthRanger subject ID is stored in AGO as a parameter ER_ID on each
        linestring.

        Right now, this method is very brute force: It either adds a track or
        replaces the whole track.  There are also not (yet) any parameters
        around track length, date ranges, which subjects to include, etc.

        :param esri_layer: The AGO layer to upsert
        :return: None
        """
        self._ensure_attributes_in_layer(esri_layer, [
            {'name':'ER_ID', 'alias': 'ER ID', 'type': 'esriFieldTypeString'},
            {'name':'SUBJECT_NAME', 'alias': 'Subject Name', 'type': 'esriFieldTypeString'}
        ])

        subjects = self.das_client.get_subjects()
        existing_tracks = self._get_existing_esri_tracks(esri_layer)
        features_to_add = []
        features_to_update = []
        for subject in subjects:
            results = self.das_client.get_subject_tracks(subject_id = subject['id'])

            for feature in results['features']:

                polyline = {
                    "geometry": {
                        "paths": [feature['geometry']['coordinates']],
                        "spatialReference": {"wkid" : 4326}
                    },
                    "attributes": {
                        "ER_ID": subject['id'],
                        "SUBJECT_NAME": subject['name']
                    }
                }

                if(str(subject['id']) in existing_tracks.keys()):
                    polyline['attributes']['OBJECTID'] = existing_tracks[str(subject['id'])]
                    features_to_update.append(polyline)
                else:
                    features_to_add.append(polyline)

        if((len(features_to_add) > 0) or (len(features_to_update) > 0)):
            (results, added, updated) = self._upsert_features(features_to_add, features_to_update, esri_layer)
            self.logger.info(f"Created {added} and updated {updated} new track features in Esri")

    def upsert_events_from_er(self, esri_layer):
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
        :return: None
        """
        self._ensure_attributes_in_layer(esri_layer, [
            {'name':'ER_REPORT_NUMBER', 'alias': 'ER Report Number', 'type': 'esriFieldTypeString'},
            {'name':'REPORT_TIME', 'alias': 'Report Time', 'type': 'esriFieldTypeString'},
            {'name':'REPORTED_BY', 'alias': 'Reported By', 'type': 'esriFieldTypeString'},
            {'name':'LATITUDE', 'alias': 'Latitude', 'type': 'esriFieldTypeString'},
            {'name':'LONGITUDE', 'alias': 'Longitude', 'type': 'esriFieldTypeString'},
        ])

        er_events = self.das_client.get_events(max_results = 500)
        existing_events = self._get_existing_esri_events(esri_layer)
        self.logger.info(f"Loaded {len(existing_events)} existing events from Esri")

        features_to_add = []
        features_to_update = []
        fields_to_add = []
        for event in er_events:
            if(('location' in event) and (event['location'] != None)):

                feature = {
                    "attributes":{
                        'ER_REPORT_NUMBER': str(event['serial_number']),
                        'REPORT_TIME': str(event['time']),
                        'REPORTED_BY': str(event['reported_by']),
                        'LATITUDE': str(event['location']['latitude']),
                        'LONGITUDE': str(event['location']['longitude'])
                    },
                    "geometry": Point(
                        {'y': event['location']['latitude'], 'x': event['location']['longitude'],
                        'spatialReference': {'wkid': 4326}})
                }
                for field in event['event_details'].keys():
                    if not(self._field_already_exists(field, esri_layer, fields_to_add)):
                        fields_to_add.append(field)
                    feature['attributes'][self._clean_field_name(field)] = str(event['event_details'][field])

                if(str(event['serial_number']) in existing_events.keys()):
                    feature['attributes']['OBJECTID'] = existing_events[str(event['serial_number'])]
                    features_to_update.append(feature)
                else:
                    features_to_add.append(feature)

        if(len(fields_to_add) == 0):
            self.logger.info(f"No new fields to add to the Esri layer.")
        else:
            new_fields = self._add_fields_to_layer(fields_to_add, esri_layer)
            self.logger.info(f"Added {len(fields_to_add)} new fields to the Esri layer")

        if((len(features_to_add) > 0) or (len(features_to_update) > 0)):
            (results, added, updated) = self._upsert_features(features_to_add, features_to_update, esri_layer)
            self.logger.info(f"Created {added} and updated {updated} features in Esri")

if __name__ == '__main__':
    pass
