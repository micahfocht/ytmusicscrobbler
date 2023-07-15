# ytmusicscrobbler

Youtube music authentication is handled internally in the container using oauth.
Once the container is running, run the command "cd /config && ytmusicapi oauth" in the container and navigate to the url and sign in. Then go back to the container and press enter. The container will then exit and, assuming restart policy is set to "unless stopped" will restart. It is recommended that you use the "unless stopped" restart policy as youtube's api does not always reply as expected and this can cause an application crash. There is a mechanism to prevent duplicate scrobbles after a container restart.

Last FM requires an API key, available here https://www.last.fm/api/authentication. Last FM authentication relies on the following environment variables

LASTFM_API_KEY

LASTFM_API_SECRET

LASTFM_USERNAME

LASTFM_PASSWORD

Optionally, you can set the TZ environment variable to get correct times in your log output.
