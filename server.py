from os import environ
from functools import wraps
import json

import pusher
from flask import Flask, request, Response, render_template
from flask_restful import reqparse, abort, Api, Resource
from twilio.rest import Client

# get environment variables
TWILIO_SID = environ['TWILIO_SID']
TWILIO_TOKEN = environ['TWILIO_TOKEN']
AUTH_USER = environ['BENSPAMSPHONES_USER']
AUTH_PASS = environ['BENSPAMSPHONES_PASS']
PUSHER_APPID = environ['PUSHER_APPID']
PUSHER_KEY = environ['PUSHER_KEY']
PUSHER_SECRET = environ['PUSHER_SECRET']
PUSHER_CLUSTER = environ['PUSHER_CLUSTER']

# set the routes for api endpoints here
CALL_ENDPOINT = '/api/call'
PUSHER_AUTH_ENDPOINT = '/api/pusher_auth'
TWILIO_UPDATE_ENDPOINT = '/api/twilio_update' # NOTE: will have to be appended with channel name

# update event channel name for Pusher
UPDATE_EVENT_NAME = 'BenSpamsPhones:update_event'

# init twilio client
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# init pusher client
pusher_client = pusher.Pusher(
    app_id=PUSHER_APPID,
    key=PUSHER_KEY,
    secret=PUSHER_SECRET,
    cluster=PUSHER_CLUSTER,
    ssl=True
)

# load the protocols
with open('protocols.json') as f:
    protocols = json.load(f)

# init Flask app and API
app = Flask(__name__)
api = Api(app)

# method and decorator for authorization
def check_auth(username, password):
    return username == AUTH_USER and password == AUTH_PASS

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                'Nope\n', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

# endpoint for making calls and getting protocol info
class Caller(Resource):
    # set up the parser
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('protocol', required=True, help='Protocol not specified')
    parser.add_argument('target_number', required=True, help='Target number not specified')
    parser.add_argument('update_callback', required=False)

    @requires_auth
    def get(self):
        protocol_ids = []
        for k, v in protocols.iteritems():
            protocol_ids.append(k)
        return {'protocols': protocol_ids}

    @requires_auth
    def post(self):
        args = self.parser.parse_args()
        protocol_id = args['protocol']
        try:
            protocol = protocols[protocol_id]
        except KeyError:
            abort(400, message='Protocol {} does not exist'.format(protocol_id))
        try:
            params = {
                'url': protocol['callback'],
                'to': args['target_number'],
                'from_': protocol['phone_number'],
                'method': 'GET'
            }
            # try to assign a status callback
            try:
                update_callback = args['update_callback']
                params['status_callback'] = update_callback
                params['status_callback_method'] = 'POST'
                params['status_callback_event'] = ['initiated', 'ringing', 'answered', 'completed']
            except KeyError:
                pass
            
            twilio_client.calls.create(**params)
        except Exception as e:
            abort(500, message=str(e))
        return protocol_id, 200

# endpoint for Pusher authorization
class PusherAuth(Resource):
    # set up the parser
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('channel_name', required=True, help='Channel name not specified')
    parser.add_argument('socket_id', required=True, help='Socket id not specified')

    @requires_auth
    def post(self):
        args = self.parser.parse_args()
        auth = pusher_client.authenticate(
            channel=args['channel_name'],
            socket_id=args['socket_id']
        )
        return auth # FIXME: what happens when auth fails?

# endpoint for Twilio status updates
class TwilioUpdates(Resource):
    # set up the parser
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('CallStatus', required=True, help='Call status not specified')

    def post(self, channel_name):
        args = self.parser.parse_args()
        call_status = args['CallStatus']
        message = 'Your call is {}.'.format(call_status)
        try:
            pusher_client.trigger(channel_name, UPDATE_EVENT_NAME, {'message': message})
        except Exception as e:
            pass # TODO: some better error handling here
        return call_status, 200

# Web interface
@app.route('/')
@requires_auth
def index():
    return render_template(
        'index.html',
        pusher_key=PUSHER_KEY,
        pusher_cluster=PUSHER_CLUSTER,
        call_endpoint=CALL_ENDPOINT,
        pusher_auth_endpoint=PUSHER_AUTH_ENDPOINT,
        twilio_update_endpoint=TWILIO_UPDATE_ENDPOINT,
        update_event_name=UPDATE_EVENT_NAME
    )

# resource routing for the api
api.add_resource(Caller, CALL_ENDPOINT)
api.add_resource(PusherAuth, PUSHER_AUTH_ENDPOINT)
api.add_resource(TwilioUpdates, TWILIO_UPDATE_ENDPOINT + '/<channel_name>')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=False)
