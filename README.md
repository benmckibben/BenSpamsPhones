# BenSpamsPhones

## Introduction
A while ago, I wanted to familiarize myself with [Twilio](https://www.twilio.com/), so I bought a couple of phone numbers and set them up so that when they are called, a song (a different one for each number) will play. Then, I wanted to work with Twilio's Python library, so I wrote a little script that, when provided a target phone number and a "protocol", calls the target phone number with the Twilio phone number defined by the protocol and plays the song defined by the protocol. Then, I wanted an even easier interface for my tool that allows me to automatically call my friends with the audio to *Shrek Is Love, Shrek Is Life* waiting on the other end of the line. And here we are.

(The rest of the introduction is a little wordy, so you can skip to Setup safely if you'd like.)  

### Motivations
Aside from creating an easy way to annoy people, I had a few things I sought to learn about with this project:
* [Flask](http://flask.pocoo.org/): I've worked with [Django](https://www.djangoproject.com/) before and love it dearly, but Flask seems like a good solution for lightweight web apps, like this one, that don't really need a lot of the extra stuff Django carries around with it. More specifically, I wanted to design a database-less web app without reinventing the wheel with Python's [BaseHTTPServer](https://docs.python.org/2/library/basehttpserver.html), which I have regrettably done multiple times.
* API design: I wanted to build a good API that would be used by the web front-end and could be used with utilities such as [curl](https://curl.haxx.se/). Additionally, I also want to design an Android app for this project, and I feel like learning how to get an app to cooperate with an HTTP API is useful. Thankfully, [Flask-RESTful](https://flask-restful.readthedocs.io/en/0.3.5/) made the API functionality quite simple to implement.
* Asynchronous requests in JavaScript: I never really had to implement these myself, so learning about creating an app that fetches information and submits requests without needing to reload the page was fun.
* Websockets: I wanted to be able to receive updates on the status of my call after I placed it, since Twilio lets you pass a callback URL that will be POSTed to upon a status change of a call. I didn't end up directly working with websockets, but instead I used [Pusher](https://pusher.com/) to do the heavy lifting for me. Additionally, Pusher seems to have good resources for Android compatibility, so I think I made a good choice.

### Problems, Laments, Woes
There are still things about this project I still need to work on, or am generally confused about, or have begrudgingly come to accept. In no particular order, they are:
* Basic HTTP authentication: This app is meant to be single-user. As such, it uses basic HTTP auth and nothing more, with credentials defined by environment variables. I don't think this is terrible for the purposes of this project, but it kinda irks me out.
* No HTTPS: Having it would definitely make the previous point irk me out less. However, I've read that HTTPS should be handled by the actual web server. Maybe if I ever end up deploying this I'll figure that out.
* My use of Pusher: I know this sort of app is what Pusher is used for, but I wish I would've figured out how to use websockets for this. [Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/) seems good for this. Also, I don't think I worked with channels correctly. I'm using private channels to communicate call updates to the client, but I'm not sure that using socket ids to make channel names is good practice. Technical details on this lament will follow.
* Error messages in web front-end:  
  ![error0](http://i.imgur.com/7ylHIOb.png)  
  When a Twilio call raises an exception (i.e. when an invalid phone number is provided), the stringified exception is displayed on the web front-end, which can include weird characters and is generally helpful but a pain to read.
* Android app: I still want to make an Android app that interfaces this API.
* Appearance: The web interface should be prettier.
* On the web interface, pressing Enter while the target number field is in focus should send the request.
* I should have the port number be a command line argument.
* A couple others described by TODOs and FIXMEs in the code.

## Setup
### Dependencies & External Services
Now for the good part. This app runs on Python 2.7; I recommend creating a new [venv](https://virtualenv.pypa.io/en/stable/) to run this in. To install dependencies, run the following:  
`pip install -r requirements.txt`

Next, you'll need accounts on [Twilio](https://www.twilio.com/) and [Pusher](https://pusher.com/). For Twilio, you'll need to load your account with funds in order to purchase phone numbers and make un-watermarked calls. Pusher's free plan should suffice; create a new app using the Pusher dashboard.

### Environment Variables
There are 8 environment variables that you need to set, detailed here:
* `TWILIO_SID`: The "Account SID" found at your [Twilio console](https://www.twilio.com/console).
* `TWILIO_TOKEN`: The "Auth Token" found at your [Twilio console](https://www.twilio.com/console).
* `BENSPAMSPHONES_USER`: The username you want to use for basic HTTP auth.
* `BENSPAMSPHONES_PASS`: The password you want to use for basic HTTP auth.
* `PUSHER_APPID`: Your Pusher app's `app_id`.
* `PUSHER_KEY`: Your Pusher app's `key`.
* `PUSHER_SECRET`: Your Pusher app's `secret`.
* `PUSHER_CLUSTER`: Your Pusher app's `cluster`.

### Protocols
BenSpamsPhones reads its available protocols from a file named `protocols.json`, which should be created and placed in the same location as `server.py`. `example-protocols.json` shows how `protocols.json` should be formatted; the keys are the ids of the protocols, and the values are objects with the following fields:
* `phone_number`: The phone number to call *from* with this protocol. This should be a phone number that you have purchased on Twilio.
* `callback`: The callback URL containing the [TwiML](https://www.twilio.com/docs/api/twiml) you want executed once the call is in-progress. If you're unfamiliar with TwiML, I'd strongly suggest reading the docs for it, as it is incredibly versatile and lets you do so much with your dollar-a-month phone numbers.

## Usage
### Running the server
Fairly simple, provided you've done the aforementioned setup:  
`python server.py`  
The server runs on your machine's IP at port 9001. You can visit the web interface by navigating to http://localhost:9001/ and providing your username and password as defined earlier.

### Web Interface
![interface](http://i.imgur.com/dMlMMxx.png)    
As you can see, this web interface is very simple to use: select a protocol from the dropdown, type the target number, and press the button. Messages will indicate whether the request was successful or not, and ideally live call status updates will appear as well. Here is a breakdown of what is happening when you load the page and submit a call:
1. Pusher is initialized. What this means is a connection to Pusher is made, the socket id is obtained, and a request to bind to a private channel is made, which involves calling the `/api/pusher_auth` endpoint. Once that happens, the message "Connected to live updates!" is shown in the Updates section.

   I'm unsure if constructing a channel name from the socket id is the best practice. The channel name that the client attempts to bind to is simply `'private-' + socket_id.replace('.', '')`. Additionally, I have no idea how Pusher authentication (`pusher_client.authenticate()` in `server.py`) actually works. The combination of this leads me to believe that status updates can be intercepted fairly easily.
2. A request is made to `/api/call` to fetch the protocols list.
3. Once the button is pressed, some client-side validation is done, which currently only entails that the default protocol (before the list is fetched) isn't selected and that the target number field isn't blank.
4. If client-side validation passes, then a POST request is made to `/api/call`, additionally passing along a callback URL that Twilio will POST status updates to. Success or failure messages appear appropriately.

   Here lies another problem. The URL that is called back is `/api/twilio_update/<channel_name>`, where `channel_name` is the name of the channel that the server should send a message to with update info. If someone can obtain the socket id of an active Pusher connection, then I believe they can publish arbitrary messages to the channel.
5. As the status of the call changes, the Updates section is populated with the new information.

### Routes
Here are the valid routes for the app. The routes themselves can be easily changed with the constants `CALL_ENDPOINT`, `PUSHER_AUTH_ENDPOINT`, and `TWILIO_UPDATE_ENDPOINT` in `server.py`, but below are the routes in their default configuration.

* `GET /`: The web interface. Simplest way to use the app.
* `GET /api/call`: Returns a list of available protocols. Example:  
  ``` shell
  $ curl http://localhost:9001/api/call -u "user:pass"
  {"protocols": ["protocol1", "protocol2", "protocol3"]}
  ```
* `POST /api/call`: Places a call. On success, a 200 response is sent with the id of the requested protocol. Parameters:
   * `protocol` (required): The desired protocol to execute. Must exist in the list returned by `GET /api/call`.
   * `target_number` (required): The number to call. Twilio handles number validation and this API will return a 500 error if the number is not valid.
   * `update_callback`: The URL that will be POSTed to by Twilio upon a change in the status of this call. This is used by the web interface to deliver live status updates.
  
  Example:
  ``` shell
  $ curl http://localhost:9001/api/call -u "user:pass" -d "protocol=protocol1&target_number=0000000000" -X POST
  "protocol1"
  ```
* `POST /api/pusher_auth`: Endpoint for Pusher to carry out its [user authentication](https://pusher.com/docs/authenticating_users). Parameters:
   * `channel_name` (required): The name of the Pusher channel the client is trying to bind to.
   * `socket_id` (required): The socket id of the client.
   
   No example provided as this request should be automatically made by Pusher's client libraries.
* `POST /api/twilio_update/<channel_name>`: Endpoint that is POSTed to by Twilio containing call status information and updates. `channel_name` should be the name of the Pusher channel to message with update information. Parameters:
   * `CallStatus` (required): The status of the call represented in the rest of the POST body.
   
   No example provided as this request should be automatically made by Twilio.
   
## Parting Words
For all intents and purposes, this app is working as intended. I don't really want to do much more with it outside of the Android app since it's meant to be a personal tool instead of a public application. The extent to which I'll "deploy" this is running the Flask development server on an EC2 instance and call it a day. For the issues that I've detailed, any and all help is welcome, just fork and pull request!

Yours,  
Ben  
![ben](http://i.imgur.com/waAMAyd.jpg)
