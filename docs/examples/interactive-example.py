"""Sign in to EarthRanger as yourself, with no credentials in the script.

A client constructed with only a service_root signs the user in through
their browser (the OAuth device-authorization grant). login() prints a URL
and a short code, waits for you to approve the request, and then holds the
token. The token lasts about two days and is not refreshed; when it expires,
call login() again.

Run this from a terminal, or call login() explicitly as it does here. A
client that has to sign in on its own, from inside a request, refuses to do
so when there is no terminal to show the prompt on.
"""

from erclient import ERClient, ERClientBadCredentials

if __name__ == '__main__':
    MY_SERVICE_ROOT = 'https://sandbox.pamdas.org'

    er_client = ERClient(service_root=MY_SERVICE_ROOT)

    # Example 1: sign in. The prompt goes to stderr; approve it in a browser.
    print("Example 1 - Sign in\n########")
    try:
        er_client.login()
    except ERClientBadCredentials as e:
        # The code expired, the sign-in was declined, or the site does not
        # offer an Auth0 tenant this release knows how to sign in against.
        print(f"Sign-in failed: {e}")
        raise SystemExit(1)

    # Example 2: who did we sign in as?
    print("\n\nExample 2 - Who am I\n########")
    me = er_client.get_me()
    print(me['username'])

    # Example 3: list a page of events.
    print("\n\nExample 3 - Recent events\n########")
    for event in er_client.get_events(max_results=10):
        print(event['serial_number'], event['event_type'], event['title'])
