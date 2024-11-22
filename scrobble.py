"""Scrobble Youtube Music listening history to Last.fm"""
import time
import os
import datetime
import logging
import threading
import requests
import click
import pylast
from flask import Flask, request, render_template_string
import ytmusicapi.exceptions
import ytmusicapi.helpers
from ytmusicapi import YTMusic
import ytmusicapi




#Initial path assuming we are in a docker container.
PATH = '/config/'
if not os.path.exists('/.dockerenv'):
    from dotenv import load_dotenv
    load_dotenv()
    PATH = 'config/'

try:
    SLEEP = int(os.environ.get('SLEEP_TIME'))
except TypeError:
    #Sleep time environment variable not set, default to 45 seconds.
    SLEEP = 45

#Flask app if we need to get cookies from the user.
app = Flask(__name__)

# Suppress Flask logging
log = logging.getLogger('werkzeug')
log.disabled = True
def secho(text, file=None, nl=None, err=None, color=None, **styles):# pylint: disable=unused-argument
    """Override logging"""
def echo(text, file=None, nl=None, err=None, color=None, **styles):# pylint: disable=unused-argument
    """Override logging"""
click.echo = echo
click.secho = secho
os.environ['WERKZEUG_RUN_MAIN'] = 'True'

# HTML templates
HOME_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Input</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="card shadow">
            <div class="card-body">
                <h1 class="card-title text-center mb-4">YTMusicScrobbler</h1>
                <form action="/submit" method="post">
                    <div class="mb-3">
                    <h4>YouTube has disabled the previous OAuth method for logging in.</h3>
                    <p>The only available method to interact with YouTube music is now using a browser cookie.<br>Instructions are below to retrieve the cookie needed to work with YouTube Music.</p>
                    <ul class="simple">
                        <li><p>Open a new tab</p></li>
                        <li><p>Open the developer tools (Ctrl-Shift-I or F12) and select the “Network” tab</p></li>
                        <li><p>Go to <a class="reference external" href="https://music.youtube.com">https://music.youtube.com</a> and ensure you are logged in</p></li>
                        <li><p>Find an authenticated POST request. The simplest way is to filter by <code class="docutils literal notranslate"><span class="pre">/browse</span></code> using the search bar of the developer tools.
                        If you don't see the request, try scrolling down a bit or clicking on the library button in the top bar.</p></li>
                        <li><p>Copy the request headers.<br>In Firefox, Right click, Copy Value, Copy Request Headers<br>In Chrome, Select the request, Scroll to request headers, Select the headers and copy</p></li>
                    </ul>
                        <label for="user_input" class="form-label">Please paste your cookie here:</label>
                        <textarea class="form-control" id="user_input" name="user_input" rows="10" placeholder="Type your text here..." required></textarea>
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">Submit</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <!-- Bootstrap JS (optional) -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
BAD_CREDS = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Input</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="card shadow">
            <div class="card-body">
                <h1 class="card-title text-center mb-4">YTMusicScrobbler</h1>
                <form action="/submit" method="post">
                    <div class="mb-3">
                    <h4>An attempt to use the saved credentials failed.  Please update the credentials using the process below.</h3>
                    <ul class="simple">
                        <li><p>Open a new tab</p></li>
                        <li><p>Open the developer tools (Ctrl-Shift-I or F12) and select the “Network” tab</p></li>
                        <li><p>Go to <a class="reference external" href="https://music.youtube.com">https://music.youtube.com</a> and ensure you are logged in</p></li>
                        <li><p>Find an authenticated POST request. The simplest way is to filter by <code class="docutils literal notranslate"><span class="pre">/browse</span></code> using the search bar of the developer tools.
                        If you don't see the request, try scrolling down a bit or clicking on the library button in the top bar.</p></li>
                        <li><p>Copy the request headers.<br>In Firefox, Right click, Copy Value, Copy Response Headers<br>In Chrome, Select the request, Scroll to request headers, Select the headers and copy</p></li>
                    </ul>
                        <label for="user_input" class="form-label">Please paste your cookie here:</label>
                        <textarea class="form-control" id="user_input" name="user_input" rows="10" placeholder="Type your text here..." required></textarea>
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">Submit</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <!-- Bootstrap JS (optional) -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
RESULT_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Result</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="card shadow">
            <div class="card-body">
                <h1 class="card-title text-center mb-4">Your Cookie has been saved</h1>
                <p>You can now close this page.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

#Kills the flask server if we need to restart
@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Kills the flask server"""
    shutdown_function = request.environ.get('werkzeug.server.shutdown')
    if shutdown_function is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    shutdown_function()
    return "Shutting down..."

@app.route('/')
def home():
    """Loads the startup page to ask for creds"""
    if os.path.exists(PATH+'erroredcreds.json'):
        return render_template_string(BAD_CREDS)
    if not os.path.exists(PATH+'browser.json'):
        return render_template_string(HOME_PAGE)
    return render_template_string(RESULT_PAGE)

@app.route('/submit', methods=['POST'])
def submit():
    """Accepts user submission for cookies"""
    user_input = request.form.get('user_input', '')
    user_input = user_input.replace('\r','')
    ytmusicapi.setup(filepath=PATH+ "browser.json", headers_raw=user_input)
    print("Cookie saved")
    return render_template_string(RESULT_PAGE)

def update_history(ytmusic: YTMusic):
    """Update listening history"""
    try:
        #Get previously played tracks.
        history = ytmusic.get_history()
        return history
    except ytmusicapi.exceptions.YTMusicServerError:
        try:
            time.sleep(90)#Sleep for 90 seconds in case the issue is temporary.
            history = ytmusic.get_history()#try to get history again using same credentials.
            return history
        except ytmusicapi.exceptions.YTMusicServerError:
            if os.path.exists(PATH+'erroredcreds.json'):
                os.remove(PATH+'erroredcreds.json')
            os.rename(PATH+ 'browser.json', PATH+ 'erroredcreds.json')
    except Exception as e:
        print(e)
        raise e
    return history

def login():
    """Login to youtube music"""
    try:
        #Init the youtube music api using the existing config file.
        ytmusic = YTMusic(PATH+ 'browser.json')
        return ytmusic
    except ytmusicapi.exceptions.YTMusicServerError:
        try:
            time.sleep(90)#Sleep for 90 seconds in case the issue is temporary.
            #Init the youtube music api using the existing config file.
            ytmusic = YTMusic(PATH+ 'browser.json')
            return ytmusic
        except ytmusicapi.exceptions.YTMusicServerError as e:
            if os.path.exists(PATH+'erroredcreds.json'):
                os.remove(PATH+'erroredcreds.json')
            os.rename(PATH+ 'browser.json', PATH+ 'erroredcreds.json')
            raise ytmusicapi.exceptions.YTMusicServerError from e
    except Exception as e:
        print(e)
        raise e

def scrobble():
    """Main loop to scrobble songs to last.fm"""
    #Connect to last.fm api using keys and credentials defined in environment variables
    network = pylast.LastFMNetwork(
        api_key=os.environ.get('LASTFM_API_KEY'),
        api_secret=os.environ.get('LASTFM_API_SECRET'),
        username=os.environ.get('LASTFM_USERNAME'),
        password_hash=pylast.md5(os.environ.get('LASTFM_PASSWORD')),
    )
    ytmusic = login()
    history = update_history(ytmusic)
    test = ''
    try:
        with open(PATH+ 'history.txt', 'r',encoding='UTF-8') as file:
            last = file.read()
    except FileNotFoundError:
        last = ''
        print('Unable to load last song from disk.  This is expected for an new install.')
    while True:
        #check if the last song has already been scrobbled.
        if last == history[0]['videoId']:
            pass
        else:#since the last song has not been scrobbled:
            #check that the testing variable is still the last song listened to.
            if test == history[0]['videoId']:
                last = history[0]['videoId']#set the last song scrobbled.
                with open(PATH+ 'history.txt', 'w',encoding='UTF-8') as f:
                    #Theoretically this shouldn't be needed, but youtube's api occasionally doesn't
                    #respond as expected, so this allows us to avoid sending the same track twice.
                    f.write(last)
                #Send the scrobble to last.fm
                network.scrobble(history[0]['artists'][0]['name'],history[0]['title'],
                                 int(time.time()),history[0]['album']['name'])
                #Print the scrobble to the log.
                print('Scrobbling: ' + history[0]['title'] + ' at '
                      + datetime.datetime.now().strftime('%H:%M:%S'), flush=True)
            else:#if the song is different than the testing variable, update the testing variable.
                test = history[0]['videoId']
        time.sleep(SLEEP)#Avoids hitting youtube's api too quickly.
        history = update_history(ytmusic)
if os.path.isfile(PATH+ 'browser.json'):
    scrobble()

else:
    print('Please open a web browser to the web ui of this container.')
    threading.Thread(target=lambda: app.run(host="0.0.0.0"
                                            ,port=8000, debug=True, use_reloader=False)).start()
    while os.path.isfile(PATH+ 'browser.json') is False:
        time.sleep(1)
    scrobble()
    requests.post('http://127.0.0.1:8000/shutdown',timeout=10)
print("An error occured, restarting at:" + datetime.datetime.now().strftime('%H:%M:%S'))
