import argparse
from multiprocessing import Process
import sys

from flask import (Flask, request, flash, redirect, session, url_for)

import redis
from rq import Connection, Worker

from api.api import api
from api.paropt_manager import ParoptManager
from config import SECRET_KEY, _load_funcx_client, SERVER_DOMAIN, GLOBUS_CLIENT


app = Flask(__name__)
app.register_blueprint(api, url_prefix="/api/v1")

@app.route('/', methods=['GET'])
def home():
    """Display if user is authenticated"""
    return f'Authenticated: {session.get("is_authenticated")}'


# TODO: Consider using @authenticated decorator so don't need to check user.
@app.route('/login', methods=['GET'])
def login():

    """Send the user to Globus Auth."""
    return redirect(url_for('callback'))


@app.route('/callback', methods=['GET'])
def callback():
    """Handles the interaction with Globus Auth."""
    # If we're coming back from Globus Auth in an error state, the error
    # will be in the "error" query string parameter.
    if 'error' in request.args:
        flash("You could not be logged into the portal: " +
              request.args.get('error_description', request.args['error']))
        return redirect(url_for('home'))

    # Set up our Globus Auth/OAuth2 state
    # redirect_uri = url_for('callback', _external=True)
    redirect_uri = f'https://{SERVER_DOMAIN}/callback'
    client = _load_funcx_client()
    client.oauth2_start_flow(redirect_uri, refresh_tokens=False)

    # If there's no "code" query string parameter, we're in this route
    # starting a Globus Auth login flow.
    if 'code' not in request.args:
        additional_authorize_params = (
            {'signup': 1} if request.args.get('signup') else {})

        auth_uri = client.oauth2_get_authorize_url()
        # additional_params=additional_authorize_params)
        return redirect(auth_uri)
    else:
        # If we do have a "code" param, we're coming back from Globus Auth
        # and can start the process of exchanging an auth code for a token.
        code = request.args.get('code')
        tokens = client.oauth2_exchange_code_for_tokens(code)
        id_token = tokens.decode_id_token(client)
        print(id_token)
        session.update(
            tokens=tokens.by_resource_server,
            is_authenticated=True
        )

        return redirect(f'https://{SERVER_DOMAIN}')


@app.route('/logout', methods=['GET'])
def logout():
    """
    - Revoke the tokens with Globus Auth.
    - Destroy the session state.
    - Redirect the user to the Globus Auth logout page.
    """
    client = _load_funcx_client()

    # Revoke the tokens with Globus Auth
    for token, token_type in (
            (token_info[ty], ty)
            # get all of the token info dicts
            for token_info in session['tokens'].values()
            # cross product with the set of token types
            for ty in ('access_token', 'refresh_token')
            # only where the relevant token is actually present
            if token_info[ty] is not None):
        client.oauth2_revoke_token(
            token, additional_params={'token_type_hint': token_type})

    # Destroy the session state
    session.clear()

    redirect_uri = url_for('home', _external=True)

    ga_logout_url = list()
    ga_logout_url.append('https://auth.globus.org/v2/web/logout')
    ga_logout_url.append(f'?client={globus_client}')
    ga_logout_url.append('&redirect_uri={}'.format(redirect_uri))
    ga_logout_url.append(f'&redirect_name=https://{SERVER_DOMAIN}')

    # Redirect the user to the Globus Auth logout page
    return redirect(''.join(ga_logout_url))


app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['REDIS_URL'] = 'redis://redis:6379/0'
app.config['QUEUES'] = ['default']

def startWorker(redis_url, queues):
    redis_connection = redis.from_url(redis_url)
    with Connection(redis_connection):
        worker = Worker(queues)
        worker.work()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run paropt server or workers.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--server', action='store_true', help='run as server')
    group.add_argument('--workers', type=int, help='number of workers to start')
    args = parser.parse_args()

    ParoptManager.start()

    if args.server:
        app.run(debug=True, host="0.0.0.0", port=8080, use_reloader=False, ssl_context='adhoc')
    else:
        if args.workers <= 0:
            print("Error: --workers must be an integer > 0")
            sys.exit(1)
        procs = []
        redis_url = app.config['REDIS_URL']
        for i in range(args.workers):
            procs.append(Process(target=startWorker,
                                 args=(app.config['REDIS_URL'], app.config['QUEUES'])))
            procs[i].start()
        for proc in procs:
            proc.join()
