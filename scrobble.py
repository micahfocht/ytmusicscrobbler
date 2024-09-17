from ytmusicapi import YTMusic
import pylast
import time
import os
import datetime
if(os.path.isfile("/config/oauth.json")):
    #Connect to last.fm api using keys and credentials defined in environment variables
    network = pylast.LastFMNetwork(
        api_key=os.environ.get('LASTFM_API_KEY'),
        api_secret=os.environ.get('LASTFM_API_SECRET'),
        username=os.environ.get('LASTFM_USERNAME'),
        password_hash=pylast.md5(os.environ.get('LASTFM_PASSWORD')),
    )
    #Init the youtube music api using the existing config file.
    ytmusic = YTMusic("/config/oauth.json")
    #Get previously played tracks.
    history = ytmusic.get_history()
    test = ''
    try:
        last = open('/config/history.txt', 'r').read()
    except:
        last = ''
        print('unable to load last song from disk.')
    while(True):
        #check if the last song has already been scrobbled.
        if last == history[0]['videoId']:
            pass
        else:#since the last song has not been scrobbled:
            if test == history[0]['videoId']:#check that the testing variable is still the last song listened to.
                last = history[0]['videoId']#set the last song scrobbled.
                f = open('/config/history.txt', 'w')#write the last song to a file.
                f.write(last)#Theoretically this shouldn't be needed, but youtube's api occasionally doesn't respond as expected, so this allows us to avoid sending the same track twice.
                f.close()
                #Send the scrobble to last.fm
                network.scrobble(history[0]['artists'][0]['name'],history[0]['title'],int(time.time()),history[0]['album']['name'])
                #Print the scrobble to the log.
                print('Scrobbling: ' + history[0]['title'] + ' at ' + datetime.datetime.now().strftime("%H:%M:%S"), flush=True)
            else:#if the song is different than the testing variable, update the testing variable.
                test = history[0]['videoId']
        time.sleep(int(os.environ.get('SLEEP_TIME')))# This avoids hitting youtube's api too quickly.
        history = ytmusic.get_history()#get history and loop.

else:
    print('Please run command cd /config && ytmusicapi oauth and follow the instructions inside the container.')
    while(os.path.isfile("/config/oauth.json") == False):
        time.sleep(5)
        print('Please run command "cd /config && ytmusicapi oauth" and follow the instructions inside the container.  -- Waiting for authentication')
    print('Restarting container.')
