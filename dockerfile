FROM python:3.10

LABEL Maintainer="micahfocht"

ENV LASTFM_API_KEY=''
ENV LASTFM_API_SECRET=''
ENV LASTFM_USERNAME=''
ENV LASTFM_PASSWORD=''

WORKDIR /app
VOLUME [ "/config" ]

COPY scrobble.py /app/
COPY oauth.json /app/

RUN python3 -m pip install ytmusicapi pylast

CMD python3 -u scrobble.py
