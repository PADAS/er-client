import logging
import html
import gpxpy
import json
import dateparser
import pytz
from .version import __version__
from .schemas import EREvent, ERLocation

class DasGpxConverter(object):
    
    event_types = None
    
    def __init__(self, dasclient):
        self.dasclient = dasclient
        return

    def _get_event_type_name(self, type):
        if(self.event_types == None):
            self.event_types = self.dasclient.get_event_types()
        
        for event_type in self.event_types:
            if(event_type['value'] == type):
                return event_type['display']
        
        return type

    def _add_events(self, gpx, filter):
        events = self.dasclient.get_events(filter = json.dumps(filter), 
            include_notes = False,
            include_related_events = False,
            include_files = False,
            include_details = True,
            include_updates = False,
            page_size = 100)
        
        
        for eventdict in events:
            event = EREvent(**eventdict)
            if(event.location != None):
                type = self._get_event_type_name(event.event_type)
                
                point = gpxpy.gpx.GPXWaypoint(event.location.latitude, event.location.longitude)
                point.time = event.time
                point.name = str(event.serial_number) + " " + (event.title if event.title else type)
                point.type = type
                
                descstr = f"Priority: {event.priority_label}"
                for k,v in event.event_details.items():
                    descstr += "\n" + str(k) + ": " + str(v)
                point.description = html.escape(descstr, quote=True)
                gpx.waypoints.append(point)

    @staticmethod
    def _convert_array_to_gpx(points, times):
        gpx_segments = []
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        for i in range(len(points)):
            gpxpoint = gpxpy.gpx.GPXTrackPoint(points[i][1], points[i][0])
            if(len(points[i]) > 2):
                gpxpoint.elevation = points[i][2]
            if(len(times) > i):
                gpxpoint.time = dateparser.parse(times[i])
                
            gpx_segment.points.append(gpxpoint)
            
        gpx_segments.append(gpx_segment)
        return(gpx_segments)
        
    def _add_paths(self, gpx, filter):
        
        lower = None
        upper = None
        try:
            lower = dateparser.parse(filter['date_range']['lower'])
            upper = dateparser.parse(filter['date_range']['upper'])
        except KeyError as e:
            pass
        
        subjects = self.dasclient.get_subjects()
        
        for subject in subjects:
            if((subject['tracks_available'] != True) or 
                (dateparser.parse(subject['last_position_date']).astimezone(pytz.utc) < lower.astimezone(pytz.utc))):
                continue
                
            track = self.dasclient.get_subject_tracks(subject['id'], lower, upper)
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx_track.name = subject['name']
            for path in track['features']:
                if((path['geometry'] != None) and (path['geometry']['type'] == 'LineString')):
                    segments = self._convert_array_to_gpx(path['geometry']['coordinates'], path['properties']['coordinateProperties']['times'])
                    gpx_track.segments += segments
            gpx.tracks.append(gpx_track)
            
    def convert_to_gpx(self, filter=None):        
        gpx = gpxpy.gpx.GPX()
        self._add_events(gpx, filter)
        self._add_paths(gpx, filter)
        return gpx.to_xml()

if __name__ == '__main__':
    
    """
    Example usage:
    """
    ER_SERVER = "https://yourserver.pamdas.org/api/v1.0"
    ER_TOKEN = "your er token"
    HOURS = 240
    FILENAME = "output.gpx"
    
    das_client = dasclient.DasClient(
        token=ER_TOKEN,
        service_root=ER_SERVER
    )

    start_time = datetime.now()
    start_time -= timedelta(hours=HOURS)
    converter = dasgpxconverter.DasGpxConverter(das_client)
    filter = {'date_range' : {'lower': start_time.strftime("%Y-%m-%dT%H:%M:%S")}}

    result = converter.convert_to_gpx(json.dumps(filter))
    
    f = open(FILENAME, "w")
    f.write(result)
    f.close()