import json
from datetime import datetime, timedelta

from erclient import ERClient

if __name__ == '__main__':
    MY_SERVICE_ROOT = 'https://<your_site>.pamdas.org/api/v1.0'
    MY_TOKEN = 'https://<your_site>.pamdas.org/oauth2/token'

    er_client = ERClient(service_root=MY_SERVICE_ROOT,
                         token=MY_TOKEN)

    # Example 1: use the pulse() function be sure you can reach the API.
    print("Example 1 - Check status\n########")
    print(er_client.pulse())

    # Example 2: Use the get_subjects() function to fetch a list of Subjects that the user may see.
    print("\n\nExample 2 - Get Subjects\n########")
    subjects = er_client.get_subjects()
    print(subjects)

    # Example 3: Take a Subject ID from the results of the last call, and fetch tracks.
    print("\n\nExample 3 - Get Tracks\n########")
    for sub in subjects:
        print(sub)
        if sub.get('tracks_available', False):
            print('Getting tracks for %s' % (sub['name']))
            tracks = er_client.get_subject_tracks(sub['id'])
            print(tracks)

    # Example 4: Create an Event
    print("\n\nExample 4 - Create Event\n########")
    event_data = {
        'priority': 0,
        # Must match an event type in the ER system
        'event_type': 'wildlife_sighting_rep',
        'title': 'A new event',
        'state': 'active',
        'location': {
            'latitude': 47.5978393,
            'longitude': -122.3308366
        },
        'event_details': {  # These should match the properties section of your event type
            'wildlifesightingrep_species': 'giraffe',
            'wildlifesightingrep_numberanimals': 3
        }
    }

    new_event = er_client.post_event(event_data)
    print(new_event)

    # Example 5: Attach a photo to the event
    print("\n\nExample 5 - Attach file\n########")
    response = er_client.post_event_file(
        new_event['id'], 'LogoEarthRanger.png', comment='This is my photo.')
    print(response)

    # Example 6: Query for events
    # Filter - use any or all of the below:
    print("\n\nExample 6 - Query events\n########")
    now = datetime.now()
    filter = {
        'date_range': {
            'lower': (now-timedelta(days=7)).isoformat(),
            'upper': now.isoformat()
        },
        'text': 'new event'
    }

    result = er_client.get_events(filter=json.dumps(filter))
    for event in result:
        print(event)
