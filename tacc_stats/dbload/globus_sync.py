#!/usr/bin/env python

# Most code coppied from the copius examples in the globus sdk documentation

import json
import sys
import os
import six
import argparse
import logging
import pprint
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from datetime import datetime
from tacc_stats.daterange import daterange

from globus_sdk import NativeAppAuthClient, TransferClient, RefreshTokenAuthorizer, TransferData
from globus_sdk.exc import GlobusAPIError


# Globus Tutorial Endpoint 1
SOURCE_ENDPOINT = '142d715e-8939-11e9-b807-0a37f382de32'
# Globus Tutorial Endpoint 2
DESTINATION_ENDPOINT = '27363a9a-f4fc-42a6-a2a1-2369a83d2c75'
# Copy data off of the endpoint share

ACCOUNTING_SOURCE_PATH = '/scratch1/projects/tacc/tacc_stats/frontera/xms-accounting/'
ACCOUNTING_DESTINATION_PATH = '/xms-accounting/'

PERFORMANCE_SOURCE_PATH = '/scratch1/projects/tacc/tacc_stats/frontera/archive/'
PERFORMANCE_DESTINATION_PATH = '/'

TRANSFER_LABEL = 'TACC STATS DATA COPY'

REDIRECT_URI = "https://auth.globus.org/v2/web/auth-code"


# You will need to register a *Native App* at https://developers.globus.org/
# Your app should include the following:
#     - The scopes should match the SCOPES variable below
#     - Your app's clientid should match the CLIENT_ID var below
#     - "Native App" should be checked
# For more information:
# https://docs.globus.org/api/auth/developer-guide/#register-app
CLIENT_ID = '900c3e14-cc2e-4a8d-819f-7eb2cf2ad854'
TOKEN_FILE = 'taccstats-tokens.json'
DATA_FILE = 'transfer-data.json'
REDIRECT_URI = 'https://auth.globus.org/v2/web/auth-code'
SCOPES = ('openid email profile '
          'urn:globus:auth:scope:transfer.api.globus.org:all')

APP_NAME = 'TACC STATS DATA COPY'

PREVIOUS_TASK_RUN_CASES = ['SUCCEEDED', 'FAILED']

CREATE_DESTINATION_FOLDER = True

get_input = getattr(__builtins__, 'raw_input', input)

def enable_requests_logging():
    http.client.HTTPConnection.debuglevel = 4

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def is_remote_session():
    return os.environ.get("SSH_TTY", os.environ.get("SSH_CONNECTION"))


def load_data_from_file(filepath):
    """Load a set of saved tokens."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        tokens = json.load(f)

    return tokens


def save_data_to_file(filepath, key, data):
    """Save data to a file"""
    try:
        store = load_data_from_file(filepath)
    except:
        store = {}
    if len(store) > 0:
        store[key] = data
    with open(filepath, 'w') as f:
        json.dump(store, f)


def load_tokens_from_file(filepath):
    """Load a set of saved tokens."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        tokens = json.load(f)

    return tokens

def save_tokens_to_file(filepath, tokens):
    """Save a set of tokens for later use."""
    with open(filepath, "w") as f:
        json.dump(tokens, f)

def update_tokens_file_on_refresh(token_response):
    """
    Callback function passed into the RefreshTokenAuthorizer.
    Will be invoked any time a new access token is fetched.
    """
    save_tokens_to_file(TOKEN_FILE, token_response.by_resource_server)

def do_native_app_authentication(client_id, redirect_uri, requested_scopes=None):
    """
    Does a Native App authentication flow and returns a
    dict of tokens keyed by service name.
    """
    client = NativeAppAuthClient(client_id=client_id)
    # pass refresh_tokens=True to request refresh tokens
    client.oauth2_start_flow(
        requested_scopes=requested_scopes,
        redirect_uri=redirect_uri,
        refresh_tokens=True,
    )

    url = client.oauth2_get_authorize_url()

    print("Native App Authorization URL: \n{}".format(url))

    if not is_remote_session():
        webbrowser.open(url, new=1)

    auth_code = input("Enter the auth code: ").strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    # return a set of tokens, organized by resource server name
    return token_response.by_resource_server



def check_endpoint_path(transfer_client, endpoint, path):
    """Check the endpoint path exists"""
    try:
        transfer_client.operation_ls(endpoint, path=path)
    except Exception as tapie:
        print('Failed to query endpoint "{}": {}'.format(
            endpoint,
            tapie.message
        ))
        sys.exit(1)



def main():
    parser = argparse.ArgumentParser(description='Run Globus Transfer')
    parser.add_argument('start', type=parse, nargs='?', default = (datetime.now()- relativedelta(days = 1)).strftime("%Y-%m-%d"),
                        help = 'Start (YYYY-mm-dd)')
    parser.add_argument('end', type=parse,  nargs='?', default = False,
                        help = 'End (YYYY-mm-dd)')
    parser.add_argument('--reauth', dest='reauth', action='store_true',
                        default=False, required=False, help="reauth with globus" )


    args = parser.parse_args()


    start = args.start
    end   = args.end
    if not end: end = start
        

    tokens = None
    try:
        # if we already have tokens, load and use them
        tokens = load_tokens_from_file(TOKEN_FILE)
    except:
        pass

    if not tokens:
        # if we need to get tokens, start the Native App authentication process
        tokens = do_native_app_authentication(CLIENT_ID, REDIRECT_URI, SCOPES)

        try:
            save_tokens_to_file(TOKEN_FILE, tokens)
        except:
            pass

    transfer_tokens = tokens["transfer.api.globus.org"]

    auth_client = NativeAppAuthClient(client_id=CLIENT_ID)

    authorizer = RefreshTokenAuthorizer(
        transfer_tokens["refresh_token"],
        auth_client,
        access_token=transfer_tokens["access_token"],
        expires_at=transfer_tokens["expires_at_seconds"], 
        on_refresh=update_tokens_file_on_refresh,
    )

    transfer = TransferClient(authorizer=authorizer)




    try:
        data = load_data_from_file(DATA_FILE)
        if len(data) > 0:
            task_data = data['task']
            task = transfer.get_task(task_data['task_id'])
            if task['status'] not in PREVIOUS_TASK_RUN_CASES:
                print('The last transfer status is {}, skipping run...'.format(
                    task['status']
                ))
                sys.exit(1)
    except KeyError:
        # Ignore if there is no previous task
        pass

    check_endpoint_path(transfer, SOURCE_ENDPOINT, ACCOUNTING_SOURCE_PATH)
    check_endpoint_path(transfer, DESTINATION_ENDPOINT, ACCOUNTING_DESTINATION_PATH)
    check_endpoint_path(transfer, SOURCE_ENDPOINT, PERFORMANCE_SOURCE_PATH)
    check_endpoint_path(transfer, DESTINATION_ENDPOINT, PERFORMANCE_DESTINATION_PATH)

    tdata = TransferData(
        transfer,
        SOURCE_ENDPOINT,
        DESTINATION_ENDPOINT,
        label=TRANSFER_LABEL,
        sync_level="checksum"
    )
    for date in daterange(start, end):
        date = date.strftime("%Y-%m-%d")
        accounting_file = date + '.log'
        tdata.add_item(ACCOUNTING_SOURCE_PATH + accounting_file, ACCOUNTING_DESTINATION_PATH + accounting_file)
        performance_file = date + '.tgz'
        tdata.add_item(PERFORMANCE_SOURCE_PATH + performance_file, PERFORMANCE_DESTINATION_PATH + performance_file)

    print("Transfer Information:")
    pprint.pprint(tdata)
    task = transfer.submit_transfer(tdata)
    save_data_to_file(DATA_FILE, 'task', task.data)
#    print('Transfer has been started from\n  {}:{}\nto\n  {}:{}'.format(
#        SOURCE_ENDPOINT,
#        ACCOUNTING_SOURCE_PATH,
#        DESTINATION_ENDPOINT,
#        ACCOUNTING_DESTINATION_PATH
#    ))

#    url_string = 'https://globus.org/app/transfer?' + \
#        six.moves.urllib.parse.urlencode({
#            'origin_id': SOURCE_ENDPOINT,
#            'origin_path': PERFORMANCE_SOURCE_PATH,
#            'destination_id': DESTINATION_ENDPOINT,
#            'destination_path': PERFORMANCE_DESTINATION_PATH
#        })
#    print('Visit the link below to see the changes:\n{}'.format(url_string))


if __name__ == '__main__':
    main()

