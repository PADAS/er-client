import json
import logging
from xml.sax.saxutils import escape

import dateparser
import gpxpy
import pytz

from .client import ERClient
from .schemas import EREvent

logger = logging.getLogger(__name__)


class DasGpxConverter(object):

    event_types = None

    def __init__(self, er_client):
        self.er_client = er_client
        self.gpx = gpxpy.gpx.GPX()
        return

    def _get_event_type_name(self, type):
        if (self.event_types == None):
            self.event_types = self.er_client.get_event_types()

        for event_type in self.event_types:
            if (event_type['value'] == type):
                return event_type['display']

        return type

    def add_events(self, events, event_details, symbols):

        for eventdict in events:
            event = EREvent(**eventdict)
            if (event.location != None):
                type = self._get_event_type_name(event.event_type)

                point = gpxpy.gpx.GPXWaypoint(
                    event.location.latitude, event.location.longitude)
                point.time = event.time.astimezone(pytz.utc)
                point.name = str(event.serial_number) + " " + \
                    (event.title if event.title else type)
                point.type = type

                descstr = f""

                if (event.event_type in symbols.keys()):
                    point.symbol = symbols[event.event_type]

                for k in event_details:
                    if (k in event.event_details):
                        field_name, field_value = self.process_field(
                            k, event.event_details[k])
                        descstr += str(field_name) + ": " + \
                            str(field_value) + "\n"
                point.description = escape(descstr)
                self.gpx.waypoints.append(point)

    def add_events_from_er(self, filter, event_details=[], symbols={}):

        events = self.er_client.get_events(filter=json.dumps(filter) if filter else None,
                                           include_notes=False,
                                           include_related_events=False,
                                           include_files=False,
                                           include_details=True,
                                           include_updates=False,
                                           page_size=100)

        self._add_events(events, event_details, symbols)

    def process_field(self, field_name, field_value):
        return (field_name, field_value)

    @staticmethod
    def _convert_array_to_gpx(points, times):
        gpx_segments = []
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        for i in range(len(points)):
            gpxpoint = gpxpy.gpx.GPXTrackPoint(points[i][1], points[i][0])
            if (len(points[i]) > 2):
                gpxpoint.elevation = points[i][2]
            if (len(times) > i):
                gpxpoint.time = dateparser.parse(times[i])

            gpx_segment.points.append(gpxpoint)

        gpx_segments.append(gpx_segment)
        return (gpx_segments)

    def add_paths(self, lower=None, upper=None, subject_group_id=None):

        logger.info(f"Loading subject data")
        subjects = self.er_client.get_subjects(subject_group=subject_group_id)

        for subject in subjects:
            logger.debug(f"Getting data points for {subject['name']}")
            track = self.er_client.get_subject_tracks(
                subject['id'], lower, upper)
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx_track.name = subject['name']
            for path in track['features']:
                if ((path['geometry'] != None) and (path['geometry']['type'] == 'LineString')):
                    segments = self._convert_array_to_gpx(
                        path['geometry']['coordinates'], path['properties']['coordinateProperties']['times'])
                    gpx_track.segments += segments
            self.gpx.tracks.append(gpx_track)

    def export_to_xml(self):
        return self.gpx.to_xml()


if __name__ == '__main__':

    """
    Example usage:
    """
    ER_SERVER = os.getenv('ER_SERVER', '')
    ER_TOKEN = os.getenv('ER_TOKEN', '')
    HOURS = 240
    FILENAME = "output.gpx"

    er_client = ERClient(
        token=ER_TOKEN,
        service_root=ER_SERVER
    )

    start_time = datetime.now()
    start_time -= timedelta(hours=HOURS)
    converter = dasgpxconverter.DasGpxConverter(er_client)

    filter = {'date_range': {
        'lower': start_time.strftime("%Y-%m-%dT%H:%M:%S")}}

    converter.add_events_from_er(filter)
    converter.add_paths(subject_group_id='<your_subject_group_id>')

    result = converter.export_to_xml()

    f = open(FILENAME, "w")
    f.write(result)
    f.close()
