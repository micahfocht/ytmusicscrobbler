FROM python:3.12

LABEL Maintainer="micahfocht"

ENV LASTFM_API_KEY=''
ENV LASTFM_API_SECRET=''
ENV LASTFM_USERNAME=''
ENV LASTFM_PASSWORD=''
ENV SLEEP_TIME=45

EXPOSE 8000/tcp


WORKDIR /app
VOLUME [ "/config" ]

COPY scrobble.py /app/

RUN python3 -m pip install ytmusicapi pylast flask

CMD python3 -u scrobble.py

